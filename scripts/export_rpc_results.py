"""Publish synthetic benchmark evidence without host paths, PIDs or private logs.

Reads completed local receipts; never starts inference or executes candidates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def read_json(path):
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))


def export(folder):
    raw=read_json(folder/'report.json')
    command=next(p['command'] for p in raw['processes'] if p['label']=='coordinator')
    artifact=Path(command[command.index('--model')+1]).name
    if artifact!='sha256-a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50':
        raise ValueError('This exporter labels only the known cached Qwen3.5 4B artifact; update provenance for other models')
    result={key:raw.get(key) for key in ('mode','started_utc','model_bytes','context','max_tokens','thread_budget',
        'limitations','load_seconds','seconds','status','error','all_owned_processes_exited')}
    result.update(run=folder.name,model='qwen3.5:4b',code_executed_by_generation=False,
        model_cache_key=artifact,sampler='temperature=0; non-thinking; cache_prompt=false',tasks=[])
    result['processes']=[{'label':p['label'],'limit':p['limit']} for p in raw['processes']]
    samples=raw['samples'];result['samples']=samples
    result['minimum_available_ram_gib']=min((s['available_bytes'] for s in samples),default=0)/2**30
    result['peak_aggregate_process_rss_gib']=max((sum(p['rss_bytes'] for p in s['processes']) for s in samples),default=0)/2**30
    result['per_process_peak_rss_gib']={p['label']:max((v['rss_bytes'] for s in samples for v in s['processes'] if v['label']==p['label']),default=0)/2**30 for p in raw['processes']}
    log=(folder/'coordinator.log').read_text(errors='replace')
    result['layer_assignments']=[{'layer':int(layer),'device':device.rstrip(','),
        'kind':'output placement slot' if int(layer)==32 else 'decoder block'}
        for layer,device in re.findall(r'load_tensors: layer\s+(\d+) assigned to device (\S+)',log)]
    result['rpc_logged_graph_compute_events']={f'rpc-{i}':len(re.findall(r'\[graph_compute\]',(folder/f'rpc-{i}.log').read_text(errors='replace'))) for i in range(3)} if raw['mode']=='rpc' else {}
    result['rpc_log_count_note']='Logged graph_compute events only; reused graph execution is not fully logged at this verbosity. Not a total RPC-call or token count.'
    for task in raw['tasks']:
        item=dict(task)
        response=read_json(folder/(task['task']+'.response.json'))
        item['candidate_text']=response['choices'][0]['message']['content']
        item['prompt']=(folder/(task['task']+'.prompt.txt')).read_text(encoding='utf-8')
        check=folder/(task['task']+'.check.json')
        if check.is_file():
            grade=read_json(check);source=(folder/(task['task']+'.py')).read_bytes()
            if hashlib.sha256(source).hexdigest()!=grade['source_sha256']:raise ValueError('Reviewed source changed')
            item['review_status']='source inspected, hash-gated checker executed'
            item['grade']=grade
        elif task['task']=='smoke':
            item['grade']={'expected':'READY','actual':item['candidate_text'],'passed':item['candidate_text']=='READY','coding_score':False}
        result['tasks'].append(item)
    return result


def historical(folder):
    raw=read_json(folder/'report.json')
    result={key:raw.get(key) for key in ('model','model_digest','threads','context','max_tokens','thinking','temperature')}
    result.update(run=folder.name,trial_date='2026-11-22',tasks=[],
        comparability='Historical 30B trial; same synthetic prompt text, different model/tokenizer and facade. Each task includes a fresh native load; timing is not a controlled speed comparison.')
    for task in raw['results']:
        item={key:task.get(key) for key in ('task','prompt_sha256','source_sha256','seconds','timing','done_reason')}
        item['candidate_text']=task['content'];item['prompt']=(folder/(task['task']+'.prompt.txt')).read_text(encoding='utf-8')
        check=folder/(task['task']+'.check.json')
        if check.is_file():
            grade=read_json(check)
            if hashlib.sha256((folder/(task['task']+'.py')).read_bytes()).hexdigest()!=grade['source_sha256']:raise ValueError('Historical reviewed source changed')
            item['grade']=grade
        elif task['task']=='http':item['http_verdict_passed']=task.get('passed')
        else:item['review_status']='not graded'
        result['tasks'].append(item)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',nargs='+',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--historical-folder',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Refuse to overwrite published evidence')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'schema_version':1,'synthetic_only':True,
        'hardware':'One Windows PC, Intel i7-9700, approximately 32 GiB RAM, CPU only',
        'backend_revision':'94f3af3d09e74a0fb35f703194318d3b4037714a',
        'backend_patch':'Opt-in bulk mmap prefetch disable',
        'backend_executable_sha256':'328551db778619f616d5da943e86a38ede9b87aa8e149e9393521f164d832cd6',
        'runs':[export(folder) for folder in args.runs],
        'historical_runs':[historical(args.historical_folder)] if args.historical_folder else []},indent=2),encoding='utf-8')
    print(args.output)
