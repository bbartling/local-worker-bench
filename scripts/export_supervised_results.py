"""Attach reviewed synthetic API/repair receipts to public evidence; no inference.

Does not execute candidates. The supervisor must inspect and hash-gate the
repair before running this exporter. Raw local paths and process commands stay
in ignored results directories.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_rpc_results import read_json
from local_worker_bench.streaming import verified


def receipt_summary(receipt):
    return {key:receipt.get(key) for key in
            ('id','model','status','load_seconds','seconds','worker_exited','summary','usage','timings')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--repair-dir',type=Path,required=True)
    parser.add_argument('--api-response',type=Path,required=True)
    parser.add_argument('--receipts-dir',type=Path,required=True)
    parser.add_argument('--failed-api-receipt',type=Path)
    args=parser.parse_args();data=read_json(args.evidence)
    if 'api_probe' in data or 'supervised_repair' in data:raise ValueError('Already exported; preserve evidence')
    folder=args.repair_dir;candidate=read_json(folder/'candidate-1.json')
    grade=read_json(folder/'motor.repaired.check.json')
    raw=(folder/'motor.repaired.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grade['source_sha256']:raise ValueError('Reviewed repair changed')
    base=next(t for r in data['runs'] if r['mode']=='paged' for t in r['tasks'] if t['task']=='motor')
    receipt=read_json(args.receipts_dir/candidate['resource_receipt']/'receipt.json')
    if candidate.get('status')!='needs_review' or receipt['status']!='completed':raise ValueError('Incomplete retry')
    data['supervised_repair']={
        'task':'motor','first_pass_grade':base['grade'],'base_source_sha256':base['source_sha256'],
        'prompt':(folder/'task.txt').read_text(encoding='utf-8'),
        'prompt_file_sha256':hashlib.sha256((folder/'task.txt').read_bytes()).hexdigest(),
        'prompt_sha256':candidate['prompt_sha256'],
        'answer':candidate['answer'],'repaired_source':raw.decode('utf-8'),'grade':grade,
        'receipt':receipt_summary(receipt),'client_seconds':candidate.get('seconds'),
        'review':'Supervisor inspected replacement and full source, applied only the final decision block to the pinned candidate, then ran the hash-gated independent checker.',
        'cloud_usage_measured':False}
    probe=read_json(args.api_response)
    receipt=read_json(args.receipts_dir/probe['resource_receipt']/'receipt.json')
    stream=receipt.get('streaming',{})
    if receipt['status']!='completed' or not verified(stream):raise ValueError('API stream probe unverified')
    data['api_probe']={'response_text':probe['message']['content'],
        'request':{'model':'qwen3.5:4b','messages':[{'role':'user','content':'Reply exactly READY.'}],
            'stream':False,'think':False,'options':{'num_thread':4,'num_ctx':2048,'num_predict':8}},
        'streaming_verified':True,'worker_exited':receipt['worker_exited'],
        'receipt':receipt_summary(receipt),'streaming':{k:v for k,v in stream.items() if k!='events'},
        'coding_score':False}
    if args.failed_api_receipt:
        failed=read_json(args.failed_api_receipt)
        data['api_probe_initial_failure']={**receipt_summary(failed),'error':failed.get('error'),
            'streaming':{k:v for k,v in failed.get('streaming',{}).items() if k!='events'},
            'resolution':'Enable native verbosity 5 for streaming profiles so the expected decoder layer count is logged. Preserve fail-closed validation.'}
    args.evidence.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'exported':True,'repair_grade':grade,'api_probe':data['api_probe']}))
