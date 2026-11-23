"""Attach this pilot's inspected motor repair and context probe to public evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_rpc_results import read_json


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--repair',type=Path,required=True)
    p.add_argument('--receipts',type=Path,required=True);p.add_argument('--context-probe',type=Path,required=True)
    args=p.parse_args();data=read_json(args.data)
    if 'supervised_repair' in data:raise ValueError('Already attached; preserve evidence')
    folder=args.repair;candidate=read_json(folder/'candidate.json');grade=read_json(folder/'motor.repaired.check.json')
    raw=(folder/'motor.repaired.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grade['source_sha256']:raise ValueError('Reviewed repair changed')
    first=next(t for r in data['runs'] for t in r['tasks'] if t['task']=='motor')
    receipt=read_json(args.receipts/candidate['resource_receipt']/'receipt.json')
    if receipt['status']!='completed' or not receipt['worker_exited']:raise ValueError('Repair request incomplete')
    data['supervised_repair']={'task':'motor','first_pass_grade':first['grade'],
        'base_source_sha256':first['grade']['source_sha256'],'prompt':(folder/'prompt.txt').read_text(encoding='utf-8').strip(),
        'prompt_sha256':candidate['prompt_sha256'],'model_answer':candidate['answer'],
        'repaired_source':raw.decode('utf-8'),'grade':grade,'client_seconds':candidate['seconds'],
        'resources':{k:receipt.get(k) for k in ('status','seconds','load_seconds','summary','usage','timings','context_admission','worker_exited')},
        'method':'Supervisor reviewed the local replacement block and applied it to the pinned disposable candidate; no supervisor rewrite; full source inspected before hash-gated checks.'}
    data['context_overflow_probe']=read_json(args.context_probe)
    args.data.write_text(json.dumps(data,indent=2),encoding='utf-8');print('Attached reviewed repair and real context rejection')
