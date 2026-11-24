"""One explicit handoff: finish legacy pagination, matched motor8, overnight v2.

No replay or generated execution. STOP in output cancels the owned stage and
prevents subsequent stages. Existing legacy attempts remain in their own folder.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.offload_api import Manager,handler_for,read_config
from local_worker_bench.runner import worker_lock


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(path)


def pagination_finished(state):
    trials=[v for v in state.get('trials',{}).values() if v.get('task')=='pagination']
    return len(trials)==3 and all(v.get('state')!='claimed' for v in trials)


def motor8(args):
    """Same saved motor prompt/settings as prior Qwen3.8 Q4, except threads=8."""
    folder=args.output/'motor8';folder.mkdir()
    config=json.loads(args.config.read_text())
    profile=dict(config['models']['qwen38-q4']);profile.update(context=2048,max_tokens=1024,threads=8,request_timeout=5400)
    config['models']={'qwen38-q4':profile}
    path=folder/'api-config.json';save(path,config)
    manager=Manager(read_config(path.resolve()),folder/'api-receipts')
    server=ThreadingHTTPServer(('127.0.0.1',11440),handler_for(manager));server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();child=None
    prompt=args.motor_prompt.read_bytes().decode('utf-8').replace('\r\n','\n')
    (folder/'prompt.txt').write_text(prompt,encoding='utf-8',newline='')
    save(folder/'experiment.json',{'model':'qwen38-q4','threads':8,'context':2048,'output_tokens':1024,
        'timeout':5400,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
        'control':'docs/benchmarks/data/2026-11-23-retest90.json','generated_code_executed':False,
        'limitations':'Historical four-thread control: cache, available RAM and desktop activity not controlled.'})
    try:
        command=[sys.executable,'-m','local_worker_bench','ask','--endpoint','http://127.0.0.1:11440',
            '--model','qwen38-q4','--prompt-file',str((folder/'prompt.txt').resolve()),'--output',str((folder/'candidate.json').resolve()),
            '--threads','8','--context','2048','--max-tokens','1024','--timeout','5430','--thinking','off']
        with (folder/'client.log').open('w') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
            while child.poll() is None:
                if (args.output/'STOP').exists():manager.cancel.set()
                time.sleep(1)
        target=folder/'candidate.json'
        if target.exists():
            response=json.loads(target.read_text());source=response.get('answer',{}).get('source')
            if response.get('status')=='needs_review' and isinstance(source,str) and source.strip():
                (folder/'motor.py').write_bytes(source.encode())
        return child.returncode
    finally:
        manager.shutdown();server.shutdown();server.server_close();thread.join(timeout=5)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--motor-prompt',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);record=args.output/'handoff.json'
    state={'state':'waiting_for_legacy_pagination','started_epoch':time.time(),
        'new_profile':{'threads':8,'request_timeout':7200,'output_tokens':2048,'prompt_version':2},
        'generated_code_executed':False}
    save(record,state);end=time.time()+7200
    while time.time()<end:
        if (args.output/'STOP').exists():
            (args.legacy/'STOP').touch();state['state']='cancelled';save(record,state);return 0
        legacy=json.loads((args.legacy/'campaign.json').read_text())
        if pagination_finished(legacy):break
        time.sleep(1)
    else:raise TimeoutError('Legacy pagination did not reach its finite boundary; no new run started')
    (args.legacy/'STOP').touch();state['state']='waiting_for_legacy_shutdown';save(record,state)
    lease=Path.home()/'.cache/local-worker-bench/paging-campaign.lock'
    end=time.time()+120
    while lease.exists() and time.time()<end:time.sleep(1)
    if lease.exists():raise RuntimeError('Legacy lease still owned; refusing competing inference')
    if (args.output/'STOP').exists():return 0
    state['state']='matched_motor8';save(record,state)
    with worker_lock('paging-campaign.lock'):state['motor_exit_code']=motor8(args)
    save(record,state)
    if (args.output/'STOP').exists():state['state']='cancelled';save(record,state);return 0
    state['state']='overnight_v2_running';save(record,state)
    command=[sys.executable,'-u',str(ROOT/'scripts/run_project_bench.py'),'--config',str(args.config.resolve()),
        '--output',str((args.output/'matrix').resolve()),'--models','qwen38-q4','coder-next-q4','coder-next-f16',
        '--threads','8','--timeout','7200','--max-tokens','2048','--prompt-version','2','--hours','24']
    with (args.output/'matrix.out.log').open('w') as out,(args.output/'matrix.err.log').open('w') as err:
        child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        state['matrix_pid']=child.pid;save(record,state)
        while child.poll() is None:
            if (args.output/'STOP').exists() and (args.output/'matrix').exists():(args.output/'matrix/STOP').touch()
            time.sleep(1)
        state.update(state='finished',matrix_exit_code=child.returncode,finished_epoch=time.time());save(record,state)
    return child.returncode


if __name__=='__main__':raise SystemExit(main())
