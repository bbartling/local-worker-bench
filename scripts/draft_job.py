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


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--endpoint',default='http://127.0.0.1:11438')
    args=p.parse_args();packet=json.loads(args.packet.read_text(encoding='utf-8'))
    prompt=render_packet(packet);args.output.mkdir(parents=True,exist_ok=False)
    store=JobStore(args.output/'jobs.sqlite');job_id=store.submit(packet);store.claim(job_id)
    try:
        prompt_path=args.output/'prompt.txt';prompt_path.write_text(prompt,encoding='utf-8')
        candidate_path=args.output/'candidate.json'
        result=ask(SimpleNamespace(endpoint=args.endpoint,model=args.model,tier=None,allow_lan=False,
            prompt_file=prompt_path,output=candidate_path,threads=4,context=2048,max_tokens=1024,
            timeout=1800,thinking='off',response_format='json'))
        candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
        source=candidate.get('answer',{}).get('source')
        if result or not isinstance(source,str):raise ValueError('No complete source candidate; inspect response')
        raw=source.encode();(args.output/'candidate.py').write_bytes(raw)
        store.finish(job_id,{'candidate_sha256':hashlib.sha256(raw).hexdigest(),
            'resource_receipt':candidate.get('resource_receipt'),'seconds':candidate['seconds']})
        print(json.dumps(store.get(job_id),indent=2))
    except BaseException as e:
        store.finish(job_id,{'error':str(e)},'failed');raise
    finally:store.close()
