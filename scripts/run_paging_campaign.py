"""Explicit finite download-gated drafting campaign; never executes or accepts code.

Owns its loopback API. One claim per model, smoke before coding, no retries.
Interrupted claimed models require supervisor disposition instead of replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.offload_api import Manager,handler_for,read_config
from local_worker_bench.paging import verified_files
from local_worker_bench.runner import api,worker_lock

MODELS=('qwen38-q4','qwen38-bf16','coder-next-f16')


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--port',type=int,default=11438);p.add_argument('--wait-hours',type=float,default=48)
    args=p.parse_args()
    if not .1<=args.wait_hours<=48:raise ValueError('Finite campaign: .1 through 48 hours')
    if not args.backend.is_file():raise ValueError('Backend missing')
    args.output.mkdir(parents=True,exist_ok=True);state_path=args.output/'campaign.json'
    stop_path=args.output/'STOP'
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        'started_epoch':time.time(),'deadline_epoch':time.time()+args.wait_hours*3600,
        'models':{name:{'state':'waiting_for_verified_download'} for name in MODELS},
        'generated_code_executed':False,'automatic_acceptance':False}
    if 'backend_executable_sha256' not in state:
        state['backend_executable_sha256']=hashlib.sha256(args.backend.read_bytes()).hexdigest()
        try:state['source_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        except (OSError,subprocess.CalledProcessError):state['source_revision']=None
    save(state_path,state);profiles={}
    for name in MODELS:
        manifest=json.loads((ROOT/'examples/paging'/f'{name}.download.json').read_text())
        profiles[name]={'files':[str((ROOT/'results/model-cache'/name/item['path']).resolve()) for item in manifest['files']],
            'layer_stream':False,'validate_context':True,'memory_fraction':.66,
            'threads':4,'context':2048,'max_tokens':1024,'working_set_gib':4,'reserve_gib':6,
            'private_limit_gib':6,'request_timeout':1800,'load_timeout':180}
    config_path=args.output/'api-config.json'
    save(config_path,{'backend_executable':str(args.backend.resolve()),'models':profiles})
    manager=Manager(read_config(config_path.resolve()),args.output/'api-receipts')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(manager));server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();child=None
    endpoint=f'http://127.0.0.1:{args.port}'
    print(json.dumps({'campaign':str(state_path),'endpoint':endpoint,'waiting_for_verified_downloads':True}),flush=True)
    try:
        while time.time()<state['deadline_epoch'] and not stop_path.exists():
            waiting=[name for name in MODELS if state['models'][name]['state']=='waiting_for_verified_download']
            if not waiting:break
            progressed=False
            for name in waiting:
                if stop_path.exists() or time.time()>=state['deadline_epoch']:break
                record=state['models'][name];manifest_path=ROOT/'results/model-cache'/name/'verified-manifest.json'
                if not manifest_path.exists():continue
                # Persist claim before any model work. Never replay a claimed job.
                record.update(state='claimed',started_epoch=time.time());save(state_path,state);progressed=True
                try:
                    manifest=json.loads(manifest_path.read_text());files=verified_files(manifest)
                    if files!=profiles[name]['files']:raise ValueError('Verified paths differ from registered files')
                    smoke_body={'model':name,'messages':[{'role':'user','content':'Reply exactly READY.'}],
                        'stream':False,'think':False,'options':{'num_thread':4,'num_ctx':2048,'num_predict':8}}
                    with worker_lock():response=api(endpoint,'/api/chat',smoke_body,
                        min(1800,max(1,state['deadline_epoch']-time.time())))
                    save(args.output/(name+'.smoke.json'),response)
                    if response.get('message',{}).get('content')!='READY':raise ValueError('Smoke did not return exactly READY')
                    output=args.output/(name+'-packet')
                    command=[sys.executable,str(ROOT/'scripts/paging_benchmark.py'),'--endpoint',endpoint,
                        '--model',name,'--style','packet','--output',str(output.resolve())]
                    with (args.output/(name+'.client.log')).open('w',encoding='utf-8') as log:
                        child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                        while child.poll() is None:
                            if stop_path.exists():raise TimeoutError('Campaign stop requested')
                            if time.time()>=state['deadline_epoch']:raise TimeoutError('Campaign deadline reached')
                            time.sleep(1)
                        if child.returncode:raise RuntimeError('Candidate trial incomplete; inspect client and API receipts')
                    record.update(state='needs_review',output=output.name)
                except Exception as e:
                    record.update(state='needs_supervisor',error=str(e))
                finally:
                    if child is not None and child.poll() is None:child.terminate();child.wait(timeout=10)
                    child=None
                    if manager.active:manager.cancel.set();manager.finished.wait(timeout=10)
                    record['finished_epoch']=time.time();save(state_path,state)
                    print(json.dumps({'model':name,**record}),flush=True)
            if not progressed:time.sleep(30)
        state['finished_epoch']=time.time();save(state_path,state)
    finally:
        if child is not None and child.poll() is None:child.terminate();child.wait(timeout=10)
        manager.shutdown();server.shutdown();server.server_close();thread.join(timeout=5)
    return 0


if __name__=='__main__':
    with worker_lock('paging-campaign.lock'):raise SystemExit(main())
