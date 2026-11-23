"""One explicit bounded CPU inference job: single process or 3 local RPC nodes.

No downloads, generated-code execution, persistent services, or global settings.
Windows process working-set caps are NOT physical 8 GiB machine isolation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench import memory
from local_worker_bench.runner import api, worker_lock
from local_worker_bench.tasks import TASKS
from local_worker_bench.streaming import summarize, verified
from local_worker_bench.patch_task import PROMPT as PATCH_PROMPT


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


def command_plan(backend,model,mode,ports,port,single_threads=4):
    common=[str(backend/'llama-server.exe'),'--model',str(model),'--alias','local-demo',
        '--host','127.0.0.1','--port',str(port),'--threads','1' if mode=='rpc' else str(single_threads),
        '--threads-batch','1' if mode=='rpc' else str(single_threads),'--ctx-size','2048','--parallel','1',
        '--no-warmup','--no-repack','--cache-ram','0','--fit','off','--load-mode','mmap',
        '--lazy-mode','on','--log-verbosity','5']
    if mode=='rpc':
        common+=['--rpc',','.join(f'127.0.0.1:{p}' for p in ports),'--gpu-layers','99',
            '--split-mode','layer','--tensor-split','1,1,1']
    else:common+=['--device','none','--gpu-layers','0']
    nodes=[[str(backend/'ggml-rpc-server.exe'),'--host','127.0.0.1','--port',str(p),
        '--threads','1','--device','CPU'] for p in ports] if mode=='rpc' else []
    return nodes,common


def run(args):
    if os.name!='nt':raise ValueError('This first harness requires Windows hard working-set controls.')
    backend=args.backend_dir.resolve();model=args.model_file.resolve();out=args.output.resolve()
    admitted_files=[model]
    if not model.is_file():raise ValueError('Cached model file is missing')
    if args.large_manifest is not None:
        if args.mode not in ('stream','paged'):raise ValueError('Large admission requires explicit CPU stream or paged mode')
        manifest=json.loads(args.large_manifest.read_text(encoding='utf-8'))
        if manifest.get('all_sha256_verified') is not True:raise ValueError('Require the completed downloader verification record')
        admitted_files=[Path(item['local_path']).resolve() for item in manifest['files']]
        if not admitted_files or admitted_files[0]!=model:raise ValueError('First GGUF must match the verified manifest')
        for path,item in zip(admitted_files,manifest['files']):
            if not path.is_file() or path.stat().st_size!=item['bytes']:raise ValueError('Verified artifact size changed')
            with path.open('rb') as f:
                if f.read(4)!=b'GGUF':raise ValueError('Expected GGUF split')
    elif model.stat().st_size>6*memory.GIB:
        raise ValueError('Practice harness admits <=6 GiB; larger streaming requires an explicit verified --large-manifest')
    with model.open('rb') as f:
        if f.read(4)!=b'GGUF':raise ValueError('Expected a cached GGUF file.')
    executables=['llama-server.exe']+(['ggml-rpc-server.exe'] if args.mode=='rpc' else [])
    if not all((backend/n).is_file() for n in executables):
        raise ValueError('Build the pinned native CPU/RPC backend first.')
    if memory.available_memory()['available_bytes']<10*memory.GIB:raise ValueError('Need at least 10 GiB available before this practice run.')
    out.mkdir(parents=True,exist_ok=False)
    report={'mode':args.mode,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'model_bytes':sum(path.stat().st_size for path in admitted_files),'model_parts':len(admitted_files),
        'context':2048,'max_tokens':args.max_tokens,
        'request_timeout':args.request_timeout,
        'requested_tasks':list(args.tasks),
        'thread_budget':'4 aggregate: 1 coordinator + 1 per RPC node' if args.mode=='rpc' else f'{args.single_threads} native threads',
        'code_executed':False,'tasks':[],'processes':[],'samples':[],
        'limitations':['Same host and shared OS cache; not physical 8 GiB machine isolation.',
        'RPC: 4 GiB cap per remote process, 3 GiB coordinator; CPU-only modes: one 4 GiB process cap.',
        'Equal RPC split proportions are placement inputs, not exact byte quotas.',
        'Windows working-set caps do not cap total private commit or OS file cache.',
        'stream: explicit layer eviction; paged/single: OS-managed mmap without explicit layer eviction.']}
    children=[];logs=[];monitor=None;stop=threading.Event();failed=threading.Event();errors=[]
    env={k:v for k,v in os.environ.items() if not k.startswith('LLAMA_ARG_')}
    threads='1' if args.mode=='rpc' else str(args.single_threads)
    env.update(LWB_DISABLE_MMAP_PREFETCH='1',OMP_NUM_THREADS=threads,
        MKL_NUM_THREADS=threads,OPENBLAS_NUM_THREADS=threads,GGML_RPC_DEBUG='1')
    env['LWB_LAYER_STREAM']='1' if args.mode=='stream' else '0'
    began=time.monotonic()
    def spawn(command,label,cap):
        log=(out/f'{label}.log').open('w',encoding='utf-8');logs.append(log)
        proc=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        children.append(proc)
        entry={'label':label,'pid':proc.pid,'command':command,'limit':memory.set_working_set_limit(proc.pid,int(cap*memory.GIB))}
        report['processes'].append(entry);return proc
    def observe():
        while not stop.wait(.25):
            try:
                sample={'seconds':round(time.monotonic()-began,3),**memory.available_memory(),'processes':[]}
                for proc,entry in zip(children,report['processes']):
                    if proc.poll() is not None:raise RuntimeError(entry['label']+' exited unexpectedly')
                    state=dict(label=entry['label'],**memory.process_memory(proc.pid));sample['processes'].append(state)
                    if state['private_bytes']>6*memory.GIB:raise RuntimeError('Private memory guard exceeded')
                report['samples'].append(sample)
                if sample['available_bytes']<6*memory.GIB:raise RuntimeError('Desktop free-RAM reserve crossed')
                if sample['available_commit_bytes'] is not None and sample['available_commit_bytes']<memory.GIB:raise RuntimeError('Commit reserve crossed')
            except Exception as error:
                errors.append(str(error));failed.set()
                for proc in children:
                    if proc.poll() is None:proc.terminate()
                return
    def guard():
        if failed.is_set():raise RuntimeError('; '.join(errors))
    def request(body,timeout):
        channel=queue.Queue()
        def send():
            try:channel.put((True,api(endpoint,'/v1/chat/completions',body,timeout=timeout)))
            except Exception as error:channel.put((False,error))
        threading.Thread(target=send,daemon=True).start();deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            guard()
            try:
                good,value=channel.get(timeout=.25)
                if good:return value
                raise value
            except queue.Empty:pass
        raise TimeoutError('Bounded generation timeout')
    with worker_lock():
        try:
            ports=[free_port() for _ in range(3)] if args.mode=='rpc' else []
            port=free_port();node_commands,server_command=command_plan(backend,model,args.mode,ports,port,args.single_threads)
            for i,command in enumerate(node_commands):spawn(command,f'rpc-{i}',4)
            for p in ports:
                deadline=time.monotonic()+15
                while True:
                    try:
                        with socket.create_connection(('127.0.0.1',p),timeout=.5):break
                    except OSError:
                        if time.monotonic()>deadline:raise TimeoutError('RPC startup timeout')
                        time.sleep(.1)
            spawn(server_command,'coordinator',3 if args.mode=='rpc' else 4)
            monitor=threading.Thread(target=observe,daemon=True);monitor.start()
            endpoint=f'http://127.0.0.1:{port}';deadline=time.monotonic()+180
            while True:
                guard()
                try:
                    if api(endpoint,'/health',timeout=.5).get('status')=='ok':break
                except (OSError,ValueError):pass
                if time.monotonic()>deadline:raise TimeoutError('Model load timed out')
                time.sleep(.25)
            report['load_seconds']=round(time.monotonic()-began,3)
            print(json.dumps({'ready':True,'mode':args.mode,'load_seconds':report['load_seconds']}),flush=True)
            for task in args.tasks:
                prompt='Reply exactly READY.' if task=='smoke' else PATCH_PROMPT if task=='patch' else TASKS[task]
                (out/f'{task}.prompt.txt').write_text(prompt,encoding='utf-8')
                body={'model':'local-demo','messages':[{'role':'user','content':prompt}],
                    'max_tokens':8 if task=='smoke' else args.max_tokens,'temperature':0,'stream':False,
                    'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False}}
                if task!='smoke':body['response_format']={'type':'json_object'}
                started=time.monotonic();response=request(body,args.request_timeout)
                (out/f'{task}.response.json').write_text(json.dumps(response,indent=2),encoding='utf-8')
                choice=response['choices'][0];content=choice['message']['content']
                item={'task':task,'seconds':round(time.monotonic()-started,3),
                    'finish_reason':choice.get('finish_reason'),'usage':response.get('usage'),
                    'timings':response.get('timings'),'review_status':'not-reviewed','prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
                if task in ('motor','elapsed','patch') and choice.get('finish_reason')=='stop':
                    candidate=json.loads(content)
                    if not isinstance(candidate.get('source'),str):raise ValueError('Missing complete source')
                    raw=candidate['source'].encode();(out/f'{task}.py').write_bytes(raw)
                    item['source_sha256']=hashlib.sha256(raw).hexdigest()
                report['tasks'].append(item);print(json.dumps(item),flush=True)
                if choice.get('finish_reason')!='stop':raise RuntimeError('Truncated generation; not a quality pass')
            report['status']='completed'
        except Exception as error:
            report.update(status='error',error=str(error));raise
        finally:
            stop.set()
            if monitor is not None:monitor.join(timeout=2)
            for proc in reversed(children):
                if proc.poll() is None:proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            for log in logs:log.close()
            if args.mode=='stream':
                report['streaming']=summarize((out/'coordinator.log').read_text(errors='replace'))
                if report.get('status')=='completed' and not verified(report['streaming']):
                    report.update(status='error',error='Streaming callback did not confirm successful eviction requests')
            report['all_owned_processes_exited']=all(proc.poll() is not None for proc in children)
            report['seconds']=round(time.monotonic()-began,3)
            (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if report.get('status')!='completed':raise RuntimeError(report.get('error','Incomplete run'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-dir',type=Path,required=True);parser.add_argument('--model-file',type=Path,required=True)
    parser.add_argument('--mode',choices=('single','rpc','stream','paged'),required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tasks',nargs='+',choices=('smoke','motor','elapsed','patch'),default=['smoke'])
    parser.add_argument('--max-tokens',type=int,choices=range(64,1025),default=1024)
    parser.add_argument('--single-threads',type=int,choices=(1,4),default=4,help='Optional single-process threading control; RPC nodes remain 1 thread each')
    parser.add_argument('--large-manifest',type=Path,help='Explicit admission of verified split GGUF in CPU stream/paged modes only')
    parser.add_argument('--request-timeout',type=int,choices=range(60,1801),default=600)
    run(parser.parse_args())
