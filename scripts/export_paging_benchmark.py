"""Publish reviewed synthetic paging trials without local paths or process IDs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_rpc_results import read_json


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',nargs='+',type=Path,required=True);p.add_argument('--receipts',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--provenance',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('Preserve prior evidence; use a new output path')
    data={'synthetic_only':True,'downloads_running_concurrently':True,'backend_provenance':read_json(args.provenance),
        'limitations':['One Windows host; shared cache; competing downloads; no controlled repeated speed claim.',
            'Structured prompts add explicit edge hints, not just formatting. No hosted-cost measurement.',
            'Prior native harness used different system/message context; this is not a controlled prompt ablation.'],
        'runs':[]}
    for folder in args.runs:
        run={'name':folder.name,'tasks':[]}
        for path in sorted(folder.glob('*.candidate.json')):
            task=path.name.split('.')[0];candidate=read_json(path)
            item={'task':task,'prompt':(folder/(task+'.prompt.txt')).read_text(encoding='utf-8'),
                **{key:candidate.get(key) for key in ('model','status','seconds','prompt_sha256','answer','timing','resource_receipt','unload_requested','error')}}
            check=folder/(task+'.check.json')
            if check.exists():
                grade=read_json(check)
                if hashlib.sha256((folder/(task+'.py')).read_bytes()).hexdigest()!=grade['source_sha256']:raise ValueError('Reviewed source changed')
                item['grade']=grade
                item['review_status']='Source inspected before hash-gated independent checks'
            receipt_path=args.receipts/str(candidate.get('resource_receipt'))/'receipt.json'
            if receipt_path.exists():
                receipt=read_json(receipt_path)
                item['resources']={key:receipt.get(key) for key in ('status','load_seconds','seconds','worker_exited','summary','usage','timings','working_set_limit','context_admission')}
                profile=receipt['profile']
                item['budget']={key:profile.get(key) for key in ('threads','context','working_set_gib','reserve_gib','private_limit_gib','memory_fraction','validate_context','admission_plan')}
                item['resources']['peak_private_gib']=max((s['private_bytes'] for s in receipt['samples']),default=0)/2**30
            run['tasks'].append(item)
        if not run['tasks']:raise ValueError('No completed candidates')
        data['runs'].append(run)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2),encoding='utf-8');print(args.output)
