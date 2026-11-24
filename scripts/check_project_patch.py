"""Execute manually reviewed synthetic project files in a bounded subprocess.

Not a sandbox. Review every returned file before supplying its bundle hash.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_worker_bench.project_bench import TASKS,grade


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=TASKS,required=True)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--reviewed-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.child:
        result=grade(args.task,args.folder,args.reviewed_sha256)
        print(json.dumps(result,indent=2));return 0
    if args.output.exists():raise ValueError('Preserve prior grade; choose a new output')
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child','--task',args.task,
        '--folder',str(args.folder.resolve()),'--reviewed-sha256',args.reviewed_sha256,
        '--output',str(args.output.resolve())],capture_output=True,text=True,timeout=15)
    if result.returncode:raise ValueError('Checker failed: '+result.stderr[-2000:])
    receipt=json.loads(result.stdout)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(receipt,indent=2))
    return 0 if not receipt['failures'] else 1


if __name__=='__main__':raise SystemExit(main())
