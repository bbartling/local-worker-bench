"""Four loopback CPU nodes, one model stage each, real serialized tensor handoff.

Small pretrained Qwen correctness proof, not an 80B benchmark or four real VMs.
Each node enforces its own Windows working-set limit before importing PyTorch.
"""
import argparse, base64, hashlib, importlib.util, json, os
from pathlib import Path
import secrets, shutil, socket, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
import urllib.request, urllib.error

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from local_worker_bench import memory
from local_worker_bench.runner import worker_lock


def request(endpoint,path,body,token,timeout=180):
    raw=None if body is None else json.dumps(body).encode()
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request(endpoint+path,raw,headers),timeout=timeout) as r:
        data=r.read(4*1024**2+1)
    if len(data)>4*1024**2: raise ValueError('Node reply exceeds 4 MiB.')
    return json.loads(data)


def load_demo():
    spec=importlib.util.spec_from_file_location('sharded_qwen',Path(__file__).with_name('demo.py'))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def node(args):
    token=os.environ.get('LWB_CLUSTER_TOKEN')
    if not token: raise ValueError('Set LWB_CLUSTER_TOKEN for this isolated experiment.')
    limit=memory.set_working_set_limit(os.getpid(),int(args.working_set_gib*memory.GIB))
    folder=args.folder.resolve(); manifest=json.loads((folder/'manifest.json').read_text())
    demo=load_demo(); lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*items): pass
        def reply(self,status,result):
            raw=json.dumps(result).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def authorized(self): return secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
        def do_GET(self):
            if not self.authorized(): self.reply(403,{'error':'Unauthorized'}); return
            self.reply(200,{'stage':args.index,'pid':os.getpid(),'working_set_limit':limit,'model':manifest['model']})
        def do_POST(self):
            if not self.authorized(): self.reply(403,{'error':'Unauthorized'}); return
            if self.path!='/stage': self.reply(404,{'error':'Unknown route'}); return
            if not lock.acquire(blocking=False): self.reply(429,{'error':'Node busy'}); return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4*1024**2: raise ValueError('Use at most 4 MiB.')
                body=json.loads(self.rfile.read(length)); step=body['step']; ids=body['input_ids']
                if type(step) is not int or not 0<=step<manifest['steps']: raise ValueError('Invalid step.')
                if not isinstance(ids,list) or not 1<=len(ids)<=256 or any(type(x) is not int or not 0<=x<151936 for x in ids): raise ValueError('Invalid token IDs.')
                (folder/f'input-{step}.json').write_text(json.dumps(ids))
                if args.index:
                    raw=base64.b64decode(body['state'],validate=True)
                    if len(raw)>2*1024**2: raise ValueError('State exceeds limit.')
                    (folder/f'state-{step}-{args.index-1}.pt').write_bytes(raw)
                stop=threading.Event(); samples=[]
                def observe():
                    while not stop.wait(.05):
                        samples.append(dict(**memory.process_memory(os.getpid()),**memory.available_memory()))
                monitor=threading.Thread(target=observe,daemon=True); monitor.start()
                began=time.monotonic()
                try: demo.stage(SimpleNamespace(folder=str(folder),index=args.index,step=step,threads=1))
                finally: stop.set(); monitor.join(timeout=2)
                result=json.loads((folder/f'result-{step}-{args.index}.json').read_text())
                output=folder/(f'logits-{step}.pt' if args.index==3 else f'state-{step}-{args.index}.pt')
                raw=output.read_bytes()
                result.update(state=base64.b64encode(raw).decode(),state_sha256=hashlib.sha256(raw).hexdigest(),
                    node_pid=os.getpid(),seconds=round(time.monotonic()-began,3),
                    peak_rss_gib=max((s['rss_bytes'] for s in samples),default=0)/memory.GIB,
                    minimum_available_ram_gib=min((s['available_bytes'] for s in samples),default=0)/memory.GIB)
                self.reply(200,result)
            except Exception as e: self.reply(400,{'error':str(e)})
            finally: lock.release()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(json.dumps({'stage':args.index,'endpoint':f'http://127.0.0.1:{server.server_port}','pid':os.getpid(),'quota':limit}),flush=True)
    try: server.serve_forever()
    finally: server.server_close()


def run(args):
    source=args.folder.resolve(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text()); token=secrets.token_hex(24)
    env=os.environ.copy(); env.update(LWB_CLUSTER_TOKEN=token,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONUTF8='1')
    children=[]; logs=[]; nodes=[]; hops=[]; generated=[]; initial=list(manifest['initial_tokens'])
    with worker_lock():
        try:
            for index in range(4):
                folder=output/f'node-{index}'; folder.mkdir()
                shutil.copytree(source/'config',folder/'config')
                for name in ['manifest.json',*[f'reference-{s}.pt' for s in range(manifest['steps'])]]: shutil.copy2(source/name,folder/name)
                # Only this node's own shard is present. Intermediate states must arrive by HTTP.
                target=folder/f'weights-{index}.pt'
                try: os.link(source/target.name,target)
                except OSError: shutil.copy2(source/target.name,target)
                with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
                log=(folder/'node.log').open('w',encoding='utf-8'); logs.append(log)
                command=[sys.executable,str(Path(__file__).resolve()),'node','--folder',str(folder),'--index',str(index),'--port',str(port),'--working-set-gib',str(args.working_set_gib)]
                child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0); children.append(child)
                endpoint=f'http://127.0.0.1:{port}'; deadline=time.monotonic()+30
                while True:
                    if child.poll() is not None: raise RuntimeError('Node exited; inspect node.log.')
                    try: info=request(endpoint,'/health',None,token,2); break
                    except (OSError,ValueError):
                        if time.monotonic()>deadline: raise RuntimeError('Node startup timed out.')
                        time.sleep(.2)
                nodes.append(dict(info,endpoint=endpoint))
            print('Four isolated node folders ready; one thread per node.',flush=True)
            ids=initial
            for step in range(manifest['steps']):
                state=None
                for index,info in enumerate(nodes):
                    body={'step':step,'input_ids':ids}
                    if state is not None: body['state']=state
                    before=time.monotonic(); response=request(info['endpoint'],'/stage',body,token)
                    state=response.pop('state')
                    raw=base64.b64decode(state,validate=True)
                    if hashlib.sha256(raw).hexdigest()!=response['state_sha256']: raise ValueError('Handoff hash mismatch.')
                    (output/f'token-{step}-stage-{index}.pt').write_bytes(raw)
                    response.update(request_json_bytes=len(json.dumps(body).encode()),response_state_bytes=len(raw),wall_seconds=round(time.monotonic()-before,3))
                    hops.append(response); print(json.dumps(response),flush=True)
                token_id=response['next_token']; generated.append(token_id); ids=[*ids,token_id]
            report={'model':manifest['model'],'dtype':manifest['dtype'],'nodes':nodes,'hops':hops,'generated_tokens':generated,
                    'matches_reference':generated==manifest['generated_tokens'],
                    'four_stage_boundaries_match':all(h['boundary_max_abs_error']==0 for h in hops),
                    'simulated_node_physical_budget_gib':8,'worker_working_set_max_gib':args.working_set_gib,
                    'limitations':['Four processes and TCP loopback on one Windows PC, not four 8 GiB VMs.',
                    'OS file cache and total host RAM are shared; this can hide true disk/network costs.',
                    'Small Qwen3-0.6B proof only; no claim that 80B has been partitioned across nodes.',
                    'Each node has one seven-layer group; no KV cache, so prefixes are recomputed.']}
            (output/'report.json').write_text(json.dumps(report,indent=2))
            if not report['matches_reference'] or not report['four_stage_boundaries_match']: raise AssertionError('Cluster result differs from reference.')
        finally:
            for child in children:
                if child.poll() is None:
                    if os.name=='nt': subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
                    else: child.terminate()
                child.wait(timeout=10)
            for log in logs: log.close()
            print('All owned node processes stopped.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('mode',choices=('run','node'))
    p.add_argument('--folder',type=Path,required=True); p.add_argument('--output',type=Path,default=Path('results/cluster-proof'))
    p.add_argument('--working-set-gib',type=float,default=4); p.add_argument('--index',type=int,choices=range(4),default=0); p.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    if not .5<=args.working_set_gib<=4: p.error('Use a worker residency limit between .5 and 4 GiB.')
    (run if args.mode=='run' else node)(args)
