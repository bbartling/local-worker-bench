"""Inspect a durable job or record a supervisor's hash-gated test decision."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_worker_bench.delegation import JobStore
from scripts.export_rpc_results import read_json


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True);p.add_argument('--job',required=True)
    p.add_argument('--decision',choices=('accept','takeover'));p.add_argument('--source',type=Path)
    p.add_argument('--grade',type=Path);p.add_argument('--reviewed-sha256');p.add_argument('--current-revision')
    args=p.parse_args()
    if not args.db.is_file():raise ValueError('Job database missing')
    store=JobStore(args.db)
    try:
        if args.decision:
            if not all((args.source,args.grade,args.reviewed_sha256,args.current_revision)):
                raise ValueError('Decision requires source, grade, reviewed hash and current revision')
            store.decide(args.job,args.source,args.reviewed_sha256,read_json(args.grade),args.decision=='accept',args.current_revision)
        print(json.dumps(store.get(args.job),indent=2))
    finally:store.close()
