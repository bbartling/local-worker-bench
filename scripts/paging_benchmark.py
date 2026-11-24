"""Explicit serial prompt trials. Writes unexecuted candidates; supervisor grades later."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_worker_bench.runner import ask
from local_worker_bench.tasks import TASKS
from local_worker_bench.patch_task import PROMPT
from local_worker_bench.delegation import JobStore,render_packet
from local_worker_bench.pause import require_benchmark_enabled


def packet(task):
    return {'task':'Implement only the requested '+task+' function. Return complete source, no tests.',
        'base_revision':'synthetic-fixtures-v1','allowed_files':[task+'.py'],
        'excerpt':PROMPT if task=='patch' else TASKS[task],
        'acceptance':(['Only exact Python int, never bool or int subclasses; 200 through 299 inclusive succeeds; all other values return False.'] if task=='patch' else
            ['Validate all selected elements before deciding; any True is ACTIVE; only a nonempty all-False selection is INACTIVE; False with None is UNKNOWN.'] if task=='motor' else
            ['Reject bool and non-finite numeric gap/timestamps; validate every row even with fewer than two samples; preserve duplicate/sort/gap and coverage requirements.']),
        'non_goals':['No filesystem, network, imports beyond math, tool calls, repository refactor or claims about test execution.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint',default='http://127.0.0.1:11438');p.add_argument('--model',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--style',choices=('baseline','packet'),default='packet')
    p.add_argument('--tasks',nargs='+',choices=('patch','motor','elapsed'),default=['patch','motor','elapsed'])
    p.add_argument('--timeout',type=int,default=1800);args=p.parse_args()
    require_benchmark_enabled(Path(__file__).resolve().parents[1])
    args.output.mkdir(parents=True,exist_ok=False);store=JobStore(args.output/'jobs.sqlite')
    try:
        for task in args.tasks:
            spec=packet(task);job_id=store.submit(spec);store.claim(job_id)
            prompt=render_packet(spec) if args.style=='packet' else PROMPT if task=='patch' else TASKS[task]
            prompt_path=args.output/(task+'.prompt.txt');prompt_path.write_text(prompt,encoding='utf-8')
            target=args.output/(task+'.candidate.json')
            ok=ask(SimpleNamespace(endpoint=args.endpoint,model=args.model,tier=None,allow_lan=False,
                prompt_file=prompt_path,output=target,threads=4,context=2048,max_tokens=1024,
                timeout=args.timeout,thinking='off',response_format='json'))==0
            result=json.loads(target.read_text(encoding='utf-8'))
            source=result.get('answer',{}).get('source')
            missing=result.get('answer',{}).get('needs_context')
            if ok and isinstance(missing,str) and missing.strip():
                store.finish(job_id,{'needs_context':missing,'candidate_file':target.name},'needs_context')
                print(json.dumps({'job':job_id,'state':'needs_context'}),flush=True);break
            if ok and isinstance(source,str) and source.strip():
                raw=source.encode();(args.output/(task+'.py')).write_bytes(raw)
                receipt={'candidate_sha256':hashlib.sha256(raw).hexdigest(),'resource_receipt':result.get('resource_receipt'),
                    'candidate_file':target.name,'style':args.style,'task':task,'model':args.model,'seconds':result['seconds']}
                store.finish(job_id,receipt);print(json.dumps({'job':job_id,**receipt,'state':'needs_review'}),flush=True)
            else:
                store.finish(job_id,{'candidate_file':target.name,'error':result.get('error','Missing source')},'failed')
                raise RuntimeError('Incomplete candidate; no automatic retry')
    finally:store.close()
