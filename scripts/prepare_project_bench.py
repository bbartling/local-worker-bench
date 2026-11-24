"""Prepare matched cached-model profiles and handwritten baseline/control receipts.

No inference, downloads or generated-code execution. Existing verification
manifests plus current file sizes and GGUF headers are required.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.project_bench import TASKS,packet,render,grade,digest_files
from local_worker_bench.paging import verified_files, default_threads
from scripts.plan_gguf_partitions import inspect

MODEL_CACHES={'qwen38-q4':'qwen38-q4','coder-next-q4':'qwen3-coder-next-q4',
    'coder-next-f16':'coder-next-f16','qwen38-f16':'qwen38-f16','qwen38-standard-q4':'qwen38-standard-q4',
    'qwen38-bf16':'qwen38-bf16','coder-next-bf16':'coder-next-bf16'}
MODEL_FORMATS={'qwen38-q4':'UD-Q4','coder-next-q4':'Q4_K_M','qwen38-standard-q4':'Q4_K_M',
    'qwen38-f16':'FP16','coder-next-f16':'FP16','qwen38-bf16':'BF16','coder-next-bf16':'BF16'}


def inspect_format(alias,files):
    """Read headers only, never tensor payloads or inference; do not trust filenames."""
    counts=Counter();names=set();templates=set();architectures=set()
    for file in files:
        header=inspect(Path(file),extra_keys=('tokenizer.chat_template',))
        for tensor in header['tensors']:
            if tensor['name'] in names:raise ValueError('Duplicate tensor across GGUF parts')
            names.add(tensor['name']);counts[tensor['ggml_type']]+=1
        architecture=header['metadata'].get('general.architecture')
        if architecture:architectures.add(architecture)
        template=header['metadata'].get('tokenizer.chat_template')
        if isinstance(template,str):templates.add(hashlib.sha256(template.encode()).hexdigest())
    format=MODEL_FORMATS[alias]
    if format in ('FP16','BF16'):
        expected=1 if format=='FP16' else 30
        if expected not in counts or set(counts)-{0,expected}:
            raise ValueError('Unexpected tensor types for '+format+': '+str(counts))
    elif 12 not in counts:raise ValueError('Expected actual Q4_K tensors')
    if len(architectures)!=1 or len(templates)>1:raise ValueError('Inconsistent split-model metadata')
    return {'declared_format':format,'tensor_type_counts':dict(counts),'tensor_count':len(names),
        'architectures':sorted(architectures),'chat_template_sha256':sorted(templates),
        'weights_loaded':False,'inference_started':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--threads',type=int,default=None,help='Override auto thread count (~66%% of affinity-visible CPUs)')
    p.add_argument('--timeout',type=int,choices=(5400,7200),default=7200,help='End-to-end request deadline; default 120 minutes')
    p.add_argument('--max-tokens',type=int,choices=(1024,2048),default=2048,help='Must match run_project_bench default')
    p.add_argument('--models',nargs='+',choices=MODEL_CACHES,default=['qwen38-q4','coder-next-q4','coder-next-f16'])
    args=p.parse_args()
    thread_choice=default_threads()
    if args.threads is not None:
        thread_choice={**thread_choice,'threads':args.threads,'override':True}
    if not 1<=thread_choice['threads']<=128:raise ValueError('threads must be 1..128')
    if not args.backend.is_file():raise ValueError('Backend missing')
    args.output.mkdir(parents=True,exist_ok=False)
    config={'backend_executable':str(args.backend.resolve()),'models':{}}
    evidence={'inference_started':False,'controls_are_handwritten':True,'thread_selection':thread_choice,'models':{},'tasks':{}}
    for alias in args.models:
        cache=MODEL_CACHES[alias]
        manifest=json.loads((ROOT/'results/model-cache'/cache/'verified-manifest.json').read_text())
        files=verified_files(manifest)
        config['models'][alias]={'files':files,'layer_stream':False,'validate_context':True,
            'capture_partial':True,'memory_fraction':.66,'threads':thread_choice['threads'],'context':4096,'max_tokens':args.max_tokens,
            'working_set_gib':4,'reserve_gib':6,'private_limit_gib':6,'request_timeout':args.timeout,'load_timeout':600}
        evidence['models'][alias]={'repo':manifest.get('repo'),'revision':manifest.get('revision'),
            'all_sha256_verified':True,'files':[{k:item[k] for k in ('path','bytes','sha256')} for item in manifest['files']],
            'format_inspection':inspect_format(alias,files)}
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
