"""Export synthetic streaming trials and compressed residency traces; no inference."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_rpc_results import read_json


def export(folder):
    raw=read_json(folder/'report.json')
    result={key:raw.get(key) for key in ('mode','started_utc','model_bytes','model_parts','context','max_tokens',
        'thread_budget','load_seconds','seconds','status','error','all_owned_processes_exited','requested_tasks')}
    command=next(p['command'] for p in raw['processes'] if p['label']=='coordinator')
    name=Path(command[command.index('--model')+1]).name
    if name.startswith('sha256-a9d0a3e1d8c91732'):
        model='qwen3.5:4b'
    elif name.startswith('Qwen3-Coder-Next-Q4_K_M-00001'):
        model='qwen3-coder-next:q4_K_M'
    else:raise ValueError('Unrecognized model artifact; add explicit provenance before export')
    result.update(run=folder.name,model=model,artifact_name=name,tasks=[],code_executed_by_generation=False)
    samples=raw['samples'];result['resource_samples']=samples
    result['minimum_available_ram_gib']=min((s['available_bytes'] for s in samples),default=0)/2**30
    result['peak_process_rss_gib']=max((p['rss_bytes'] for s in samples for p in s['processes']),default=0)/2**30
    result['peak_private_gib']=max((p['private_bytes'] for s in samples for p in s['processes']),default=0)/2**30
    result['process_limits']=[{'label':p['label'],'limit':p['limit']} for p in raw['processes']]
    for task in raw['tasks']:
        item=dict(task);response=read_json(folder/(task['task']+'.response.json'))
        item['candidate_text']=response['choices'][0]['message']['content']
        item['prompt']=(folder/(task['task']+'.prompt.txt')).read_text(encoding='utf-8')
        check=folder/(task['task']+'.check.json')
        if check.exists():
            grade=read_json(check)
            if hashlib.sha256((folder/(task['task']+'.py')).read_bytes()).hexdigest()!=grade['source_sha256']:raise ValueError('Reviewed source changed')
            item['grade']=grade;item['review_status']='source inspected and hash-gated checker executed'
        elif task['task']=='smoke':item['grade']={'expected':'READY','actual':item['candidate_text'],'passed':item['candidate_text']=='READY','coding_score':False}
        result['tasks'].append(item)
    streaming=raw.get('streaming');events=[]
    if streaming:
        events=streaming['events'];result['streaming']={k:v for k,v in streaming.items() if k!='events'}
        result['streaming']['trace_events']=len(events)
        result['streaming']['weight_span_eviction_bytes_sum']=sum(e['weight_span_bytes'] for e in events)
        result['streaming']['weight_span_note']='Repeated virtual weight ranges submitted for eviction, NOT bytes physically read from SSD.'
        result['streaming']['largest_rss_drop_bytes']=max((e['rss_before']-e['rss_after'] for e in events),default=0)
        result['streaming']['peak_callback_rss_gib']=max((max(e['rss_before'],e['rss_after']) for e in events),default=0)/2**30
    return result,events


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',nargs='+',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--provenance',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Refuse to overwrite evidence')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    trace=args.output.with_suffix('.events.jsonl.gz')
    if trace.exists():raise ValueError('Refuse to overwrite event trace')
    runs=[]
    with trace.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as compressed:
        for folder in args.runs:
            result,events=export(folder);runs.append(result)
            for event in events:compressed.write((json.dumps({'run':folder.name,**event})+'\n').encode())
    output={'schema_version':1,'synthetic_only':True,
        'hardware':'One Windows PC, Intel i7-9700, approximately 32 GiB RAM, CPU only',
        'backend_provenance':read_json(args.provenance),'resident_trace_file':trace.name,
        'resident_trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),
        'limitations':['Virtual mappings remain; this is resident-page eviction, not explicit tensor deletion/unmapping.',
            'Native attention/recurrent state stays allocated; OS standby/file cache is shared.',
            'No isolated 8 GiB VM or physical multi-host result; no measured physical SSD byte count.'],
        'runs':runs}
    args.output.write_text(json.dumps(output,indent=2),encoding='utf-8');print(args.output)
