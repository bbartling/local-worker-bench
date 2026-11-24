"""Finish/cap one legacy request, then launch one finite 90-minute retest cohort.

Never executes generated code. Only the explicitly named legacy campaign gets
a STOP marker; its own normal cleanup stops its worker.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.runner import api


def save(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy',type=Path,required=True);p.add_argument('--request-id',required=True)
    p.add_argument('--legacy-deadline',type=float,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--backend',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);record=args.output/'handoff.json'
    if not math.isfinite(args.legacy_deadline) or args.legacy_deadline>time.time()+5400:
        raise ValueError('Legacy boundary must be finite and no more than 90 minutes away')
    state={'legacy_request':args.request_id,'legacy_deadline':args.legacy_deadline,
        'state':'waiting_for_current_request','new_request_timeout':5400,'no_generated_execution':True}
    with record.open('x',encoding='utf-8') as stream:json.dump(state,stream,indent=2)
    candidate=args.legacy/'qwen38-bf16-packet/patch.candidate.json'
    while time.time()<args.legacy_deadline:
        if (args.output/'STOP').exists():
            (args.legacy/'STOP').touch();state['state']='cancelled';save(record,state);return 0
        if candidate.exists():
            try:result=json.loads(candidate.read_text());state['legacy_candidate_status']=result.get('status');break
            except (OSError,ValueError):pass
        try:
            active=api('http://127.0.0.1:11439','/api/ps',timeout=3).get('models',[])
            if active and active[0].get('request_id')!=args.request_id:
                state['legacy_request_changed']=True;break
        except (OSError,ValueError):
            state['legacy_api_unavailable']=True;break
        time.sleep(5)
    state['handoff_reason']='request completed/boundary observed' if time.time()<args.legacy_deadline else '90-minute legacy boundary reached'
    (args.legacy/'STOP').touch();state['state']='stopping_legacy_campaign';save(record,state)
    end=time.time()+60
    while time.time()<end:
        if (args.output/'STOP').exists():state['state']='cancelled';save(record,state);return 0
        if not (Path.home()/'.cache/local-worker-bench/paging-campaign.lock').exists():break
        time.sleep(1)
    else:raise RuntimeError('Legacy campaign did not release lease; no competing campaign started')
    command=[sys.executable,'-u',str(ROOT/'scripts/run_paging_campaign.py'),'--backend',str(args.backend.resolve()),
        '--output',str((args.output/'cohort').resolve()),'--port','11439','--wait-hours','48',
        '--models','qwen38-q4','qwen38-bf16','coder-next-f16','--memory-fraction','.40',
        '--request-timeout','5400','--load-timeout','600','--tasks','motor']
    state['state']='retest_cohort_running';state['started_epoch']=time.time();save(record,state)
    (args.output/'cohort').mkdir(parents=True,exist_ok=True)
    with (args.output/'cohort.out.log').open('w',encoding='utf-8') as out,(args.output/'cohort.err.log').open('w',encoding='utf-8') as err:
        child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        state['cohort_pid']=child.pid;save(record,state)
        while child.poll() is None:
            if (args.output/'STOP').exists():(args.output/'cohort/STOP').touch()
            time.sleep(1)
        code=child.returncode
    state['state']='finished';state['cohort_exit_code']=code;state['finished_epoch']=time.time();save(record,state)
    return code


if __name__=='__main__':raise SystemExit(main())
