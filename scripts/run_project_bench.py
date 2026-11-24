"""Explicit finite synthetic patch drafting matrix. Never executes model code.

Own loopback API, serial requests (default ~66% of visible CPUs, 120 min, .66 RAM),
fixed output folder, no replay, no automatic repairs or acceptance.
STOP cancels only this campaign's worker.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.offload_api import Manager,handler_for,read_config
from local_worker_bench.paging import default_threads
from local_worker_bench.project_bench import TASKS,packet,render,validate_files,digest_files
from local_worker_bench.runner import worker_lock
from local_worker_bench.pause import require_benchmark_enabled


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--models',nargs='+',required=True);p.add_argument('--tasks',nargs='+',choices=TASKS,default=list(TASKS))
    p.add_argument('--port',type=int,default=11440);p.add_argument('--timeout',type=int,default=7200,help='Default 120 minutes end-to-end')
    p.add_argument('--threads',type=int,default=None,help='Default: ~66%% of visible logical CPUs')
    p.add_argument('--memory-fraction',type=float,default=.66,help='Fraction of currently available RAM')
    p.add_argument('--max-tokens',type=int,choices=(1024,2048),default=2048)
    p.add_argument('--prompt-version',type=int,choices=(1,2),default=2)
    p.add_argument('--hours',type=float,default=16)
    args=p.parse_args()
    require_benchmark_enabled(ROOT)
    thread_info=default_threads()
    if args.threads is None:
        args.threads=thread_info['threads']
    if not 5<=args.timeout<=7200 or not .1<=args.hours<=24:raise ValueError('Finite deadlines required')
    if isinstance(args.memory_fraction,bool) or not .1<=args.memory_fraction<=.66:raise ValueError('memory fraction .10 through .66 required')
    if not 1<=args.threads<=128:raise ValueError('threads must be 1..128')
    if len(set(args.models))!=len(args.models) or len(set(args.tasks))!=len(args.tasks):raise ValueError('No repeated trials in one cohort')
    if any(not re.fullmatch(r'[a-z0-9_-]{1,64}',model) for model in args.models):raise ValueError('Use path-safe model aliases')
    config=read_config(args.config.resolve())
    for model in args.models:
        profile=config['models'][model]
        if profile['threads']!=args.threads or profile['context']!=4096 or profile['max_tokens']!=args.max_tokens or profile['memory_fraction']!=args.memory_fraction or not profile['capture_partial']:
            raise ValueError('Use matched configured threads / 4096 context / configured output / RAM fraction / capture profiles')
        if profile['request_timeout']!=args.timeout:raise ValueError('Client and server deadline must match')
    args.output.mkdir(parents=True,exist_ok=False)
    state={'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'started_epoch':time.time(),'deadline_epoch':time.time()+args.hours*3600,
        'request_timeout':args.timeout,'context':4096,'output_tokens':args.max_tokens,'threads':args.threads,
        'thread_selection':thread_info if args.threads==thread_info['threads'] else {'threads':args.threads,'override':True},
        'prompt_version':args.prompt_version,
        'memory_fraction':args.memory_fraction,'suite_version':3,'trials':{},'generated_code_executed':False,'automatic_repairs':False,
        'config_sha256':hashlib.sha256(args.config.read_bytes()).hexdigest(),
        'backend_sha256':hashlib.sha256(Path(config['backend_executable']).read_bytes()).hexdigest()}
    save(args.output/'campaign.json',state)
    manager=Manager(config,args.output/'api-receipts')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(manager));server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();child=None
    try:
        # Task-major ordering gives each model the same task before changing tasks.
        for task in args.tasks:
            for model in args.models:
                if (args.output/'STOP').exists() or time.time()>=state['deadline_epoch']:return 0
                trial=args.output/(task+'--'+model);trial.mkdir()
                prompt=render(task,args.prompt_version);(trial/'prompt.txt').write_text(prompt,encoding='utf-8')
                save(trial/'packet.json',json.loads(prompt[prompt.index('{'):]))
                record={'state':'claimed','started_epoch':time.time(),'task':task,'model':model,
                    'base_revision':packet(task)['base_revision'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
                state['trials'][trial.name]=record;save(args.output/'campaign.json',state)
                try:
                    command=[sys.executable,'-m','local_worker_bench','ask','--endpoint',f'http://127.0.0.1:{args.port}',
                        '--model',model,'--prompt-file',str((trial/'prompt.txt').resolve()),'--output',str((trial/'candidate.json').resolve()),
                        '--threads',str(args.threads),'--context','4096','--max-tokens',str(args.max_tokens),'--timeout',str(args.timeout+30),'--thinking','off']
                    with (trial/'client.log').open('w',encoding='utf-8') as log:
                        child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
                        while child.poll() is None:
                            if (args.output/'STOP').exists() or time.time()>=state['deadline_epoch']:
                                manager.cancel.set();manager.finished.wait(timeout=10)
                                raise TimeoutError('Campaign stopped/deadline')
                            time.sleep(1)
                        if child.returncode:raise ValueError('Incomplete candidate; inspect receipts')
                    response=json.loads((trial/'candidate.json').read_text(encoding='utf-8'))
                    if response.get('status')!='needs_review':raise ValueError('No complete response')
                    answer=response['answer']
                    if answer.get('needs_context'):
                        record.update(state='needs_context',question=answer['needs_context'])
                    else:
                        files=validate_files(task,answer.get('files'))
                        folder=trial/'candidate';folder.mkdir()
                        for name,source in files.items():(folder/name).write_text(source,encoding='utf-8',newline='')
                        record.update(state='needs_review',source_sha256=digest_files(files),seconds=response['seconds'])
                except Exception as error:
                    record.update(state='needs_supervisor',error=str(error))
                finally:
                    if manager.active:manager.cancel.set();manager.finished.wait(timeout=10)
                    if child is not None and child.poll() is None:
                        child.terminate();child.wait(timeout=10)
                        # Terminated clients cannot clean their lease: only remove this exact dead owner.
                        lease=Path.home()/'.cache/local-worker-bench/inference.lock'
                        if lease.exists() and lease.read_text().strip()==str(child.pid):lease.unlink()
                    child=None;record['finished_epoch']=time.time();save(args.output/'campaign.json',state)
                    print(json.dumps(record),flush=True)
    finally:
        if child is not None and child.poll() is None:child.terminate();child.wait(timeout=10)
        manager.shutdown();server.shutdown();server.server_close();thread.join(timeout=5)
        state['finished_epoch']=time.time();save(args.output/'campaign.json',state)
    return 0


if __name__=='__main__':
    with worker_lock('paging-campaign.lock'):raise SystemExit(main())
