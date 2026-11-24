"""Finite, explicit download-gated extension; same revised tasks, no execution.

Waits for the active matrix to close its API/lease and both new verification
manifests. Cancellation of the parent pipeline prevents later inference.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_worker_bench.paging import verified_files
from scripts.plan_gguf_partitions import inspect


def inspect_pair(cache):
    result={};shapes={}
    for model in ('qwen38-standard-q4','qwen38-f16'):
        manifest=json.loads((cache/model/'verified-manifest.json').read_text())
        files=verified_files(manifest)
        if len(files)!=1:raise ValueError('Expected pinned single-file precision artifacts')
        header=inspect(Path(files[0]),extra_keys=('tokenizer.chat_template','general.file_type'))
        counts=Counter(t['ggml_type'] for t in header['tensors'])
        if model=='qwen38-f16' and (1 not in counts or set(counts)-{0,1}):
            raise ValueError('FP16 artifact contains unexpected tensor types: '+str(counts))
        if model=='qwen38-standard-q4' and 12 not in counts:raise ValueError('Expected actual Q4_K tensors')
        template=header['metadata'].pop('tokenizer.chat_template',None)
        result[model]={'metadata':header['metadata'],'tensor_type_counts':dict(counts),
            'tensor_count':len(header['tensors']),'file_bytes':header['file_bytes'],
            'chat_template_sha256':hashlib.sha256(template.encode()).hexdigest() if isinstance(template,str) else None,
            'download':{key:manifest[key] for key in ('repo','revision','all_sha256_verified')}}
        shapes[model]={t['name']:t['shape'] for t in header['tensors']}
    if shapes['qwen38-f16']!=shapes['qwen38-standard-q4']:
        raise ValueError('Tensor names/shapes differ between the selected precision pair')
    result['same_tensor_names_and_shapes']=True
    result['same_chat_template']=result['qwen38-f16']['chat_template_sha256']==result['qwen38-standard-q4']['chat_template_sha256']
    result['inference_started']=False
    return result


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(path)


def ready(legacy,cache):
    if not (legacy/'campaign.json').exists():return False
    state=json.loads((legacy/'campaign.json').read_text())
    if 'finished_epoch' not in state:return False
    for model in ('qwen38-standard-q4','qwen38-f16'):
        path=cache/model/'verified-manifest.json'
        if not path.exists() or json.loads(path.read_text()).get('all_sha256_verified') is not True:return False
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy',type=Path,required=True);p.add_argument('--backend',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--wait-hours',type=float,default=24)
    args=p.parse_args()
    if not .1<=args.wait_hours<=24:raise ValueError('Finite wait .1 through 24 hours')
    args.output.mkdir(parents=True,exist_ok=False);record=args.output/'handoff.json'
    state={'state':'waiting_for_parent_and_verified_models','started_epoch':time.time(),
        'wait_deadline_epoch':time.time()+args.wait_hours*3600,'models':['qwen38-standard-q4','qwen38-f16'],
        'threads':8,'request_timeout':7200,'output_tokens':2048,'context':4096,'prompt_version':2,
        'generated_code_executed':False,'automatic_acceptance':False}
    save(record,state)
    def cancelled():return any(p.exists() for p in (args.output/'STOP',args.legacy/'STOP',args.legacy.parent/'STOP'))
    while time.time()<state['wait_deadline_epoch']:
        if cancelled():state['state']='cancelled';save(record,state);return 0
        if ready(args.legacy,ROOT/'results/model-cache'):
            if not (Path.home()/'.cache/local-worker-bench/paging-campaign.lock').exists():break
        time.sleep(5)
    else:state['state']='wait_deadline';save(record,state);return 0
    save(args.output/'precision-inspection.json',inspect_pair(ROOT/'results/model-cache'))
    setup=args.output/'setup'
    command=[sys.executable,str(ROOT/'scripts/prepare_project_bench.py'),'--backend',str(args.backend.resolve()),
        '--output',str(setup.resolve()),'--threads','8','--timeout','7200','--max-tokens','2048',
        '--models','qwen38-standard-q4','qwen38-f16']
    with (args.output/'prepare.log').open('w') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    if result.returncode:raise RuntimeError('Preparation refused; inspect log, no inference started')
    if cancelled():state['state']='cancelled';save(record,state);return 0
    command=[sys.executable,'-u',str(ROOT/'scripts/run_project_bench.py'),'--config',str((setup/'api-config.json').resolve()),
        '--output',str((args.output/'matrix').resolve()),'--models','qwen38-standard-q4','qwen38-f16',
        '--threads','8','--timeout','7200','--max-tokens','2048','--prompt-version','2','--hours','24']
    with (args.output/'matrix.out.log').open('w') as out,(args.output/'matrix.err.log').open('w') as err:
        child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        state.update(state='precision_extension_running',matrix_pid=child.pid);save(record,state)
        while child.poll() is None:
            if cancelled() and (args.output/'matrix').exists():(args.output/'matrix/STOP').touch()
            time.sleep(1)
        state.update(state='finished',matrix_exit_code=child.returncode,finished_epoch=time.time());save(record,state)
    return child.returncode


if __name__=='__main__':raise SystemExit(main())
