"""Hash-gated checker for a manually inspected patch candidate; not a sandbox."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_worker_bench.cases import inspect_source
from local_worker_bench.patch_task import grade


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--reviewed-sha256',required=True)
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    if not args.child:
        child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source.resolve()),
            '--reviewed-sha256',args.reviewed_sha256,'--child'],capture_output=True,text=True,timeout=15)
        print(child.stdout,end='');print(child.stderr,end='',file=sys.stderr);raise SystemExit(child.returncode)
    raw=args.source.read_bytes()
    if len(raw)>12000 or hashlib.sha256(raw).hexdigest()!=args.reviewed_sha256:raise ValueError('Source differs from reviewed bytes or exceeds limit')
    tree=inspect_source(raw.decode('utf-8'))
    namespace={'__builtins__':{'type':type,'int':int,'bool':bool,'isinstance':isinstance}}
    exec(compile(tree,'<reviewed-patch>','exec'),namespace)
    result=grade(namespace['is_success']);result.update(source_sha256=args.reviewed_sha256,code_executed=True)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed']==result['total'] else 1)
