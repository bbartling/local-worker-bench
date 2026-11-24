"""Prepare matched cached-model profiles and handwritten baseline/control receipts.

No inference, downloads or generated-code execution. Existing verification
manifests plus current file sizes and GGUF headers are required.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.project_bench import TASKS,packet,render,grade,digest_files
from local_worker_bench.paging import verified_files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--threads',type=int,choices=(4,8),default=4,help='8 requires explicit user authorization; default preserves desktop capacity')
    args=p.parse_args()
    if not args.backend.is_file():raise ValueError('Backend missing')
    args.output.mkdir(parents=True,exist_ok=False)
    config={'backend_executable':str(args.backend.resolve()),'models':{}}
    evidence={'inference_started':False,'controls_are_handwritten':True,'models':{},'tasks':{}}
    for alias,cache in [('qwen38-q4','qwen38-q4'),('coder-next-q4','qwen3-coder-next-q4'),('coder-next-f16','coder-next-f16')]:
        manifest=json.loads((ROOT/'results/model-cache'/cache/'verified-manifest.json').read_text())
        files=verified_files(manifest)
        config['models'][alias]={'files':files,'layer_stream':False,'validate_context':True,
            'capture_partial':True,'memory_fraction':.4,'threads':args.threads,'context':4096,'max_tokens':1024,
            'working_set_gib':4,'reserve_gib':6,'private_limit_gib':6,'request_timeout':5400,'load_timeout':600}
        evidence['models'][alias]={'repo':manifest.get('repo'),'revision':manifest.get('revision'),
            'all_sha256_verified':True,'files':[{k:item[k] for k in ('path','bytes','sha256')} for item in manifest['files']]}
    for task,spec in TASKS.items():
        folder=args.output/task;folder.mkdir()
        (folder/'packet.json').write_text(json.dumps(packet(task),indent=2),encoding='utf-8')
        (folder/'prompt.txt').write_text(render(task),encoding='utf-8')
        evidence['tasks'][task]={'base_revision':digest_files(spec['files'])}
        for label,key in [('baseline','files'),('control','reference')]:
            dest=folder/label;dest.mkdir()
            for name,source in spec[key].items():(dest/name).write_text(source,encoding='utf-8',newline='')
            receipt=grade(task,dest,digest_files(spec[key]))
            (folder/(label+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            evidence['tasks'][task][label]={k:receipt[k] for k in ('passed','total','source_sha256')}
            evidence['tasks'][task][label]['failed_cases']=[case['case'] for case in receipt['failures']]
            if (label=='control' and receipt['failures']) or (label=='baseline' and not receipt['failures']):
                raise ValueError('Expected green control and red baseline')
    (args.output/'api-config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (args.output/'controls.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(evidence['tasks'],indent=2))


if __name__=='__main__':main()
