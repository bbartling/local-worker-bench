"""One explicitly authorized local draft with a durable needs-review checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_worker_bench.delegation import JobStore,render_packet
from local_worker_bench.runner import ask
from local_worker_bench.pause import require_benchmark_enabled


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--endpoint',default='http://127.0.0.1:11438')
    p.add_argument('--max-tokens',type=int,choices=range(64,1025),default=512)
    p.add_argument('--timeout',type=int,default=1800)
    args=p.parse_args();require_benchmark_enabled(Path(__file__).resolve().parents[1])
    packet=json.loads(args.packet.read_text(encoding='utf-8'))
    if not 5<=args.timeout<=21600:raise ValueError('Timeout must be 5 through 21600 seconds')
    prompt=render_packet(packet);args.output.mkdir(parents=True,exist_ok=False)
    store=JobStore(args.output/'jobs.sqlite');job_id=store.submit(packet);store.claim(job_id)
    try:
        prompt_path=args.output/'prompt.txt';prompt_path.write_text(prompt,encoding='utf-8')
        candidate_path=args.output/'candidate.json'
        result=ask(SimpleNamespace(endpoint=args.endpoint,model=args.model,tier=None,allow_lan=False,
            prompt_file=prompt_path,output=candidate_path,threads=4,context=2048,max_tokens=args.max_tokens,
            timeout=args.timeout,thinking='off',response_format='json'))
        candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
        source=candidate.get('answer',{}).get('source');missing=candidate.get('answer',{}).get('needs_context')
        if result:raise ValueError('Incomplete response; inspect candidate receipt')
        if isinstance(missing,str) and missing.strip():
            store.finish(job_id,{'needs_context':missing,'resource_receipt':candidate.get('resource_receipt')},'needs_context')
        else:
            if not isinstance(source,str):raise ValueError('No complete source candidate; inspect response')
            raw=source.encode();(args.output/'candidate.py').write_bytes(raw)
            store.finish(job_id,{'candidate_sha256':hashlib.sha256(raw).hexdigest(),
                'resource_receipt':candidate.get('resource_receipt'),'seconds':candidate['seconds']})
        print(json.dumps(store.get(job_id),indent=2))
    except BaseException as e:
        if store.get(job_id)['state']=='drafting':store.finish(job_id,{'error':str(e)},'failed')
        raise
    finally:store.close()
