"""Read GGUF headers and propose 3 contiguous weight groups; no inference.

Does not rewrite weights or configure llama.cpp. Spans include tensor padding;
they are serialized storage estimates, not runtime-memory requirements.
"""
import argparse
import json
from pathlib import Path
import re
import struct


def take(handle,fmt):
    size=struct.calcsize('<'+fmt);raw=handle.read(size)
    if len(raw)!=size:raise ValueError('Truncated GGUF header')
    return struct.unpack('<'+fmt,raw)[0]


def string(handle):
    size=take(handle,'Q')
    if size>2**20:raise ValueError('Header string exceeds 1 MiB')
    raw=handle.read(size)
    if len(raw)!=size:raise ValueError('Truncated string')
    return raw.decode('utf-8')


def value(handle,kind,retain=False):
    formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
    if kind in formats:return take(handle,formats[kind])
    if kind==8:return string(handle)
    if kind==9:
        subtype=take(handle,'I');count=take(handle,'Q')
        if count>10**7:raise ValueError('Oversized metadata array')
        if subtype in formats:handle.seek(struct.calcsize('<'+formats[subtype])*count,1)
        else:
            for _ in range(count):value(handle,subtype)
        return None
    raise ValueError('Unsupported GGUF metadata type')


def inspect(path,extra_keys=()):
    with path.open('rb') as f:
        if f.read(4)!=b'GGUF' or take(f,'I') not in (2,3):raise ValueError('Expected GGUF v2/v3')
        count=take(f,'Q');metadata_count=take(f,'Q');alignment=32;metadata={}
        if count>10**6 or metadata_count>10**6:raise ValueError('Oversized tensor/metadata count')
        for _ in range(metadata_count):
            key=string(f);item=value(f,take(f,'I'))
            if key=='general.alignment':alignment=item
            if key in ('general.architecture','general.name') or key in extra_keys or key.endswith('.block_count'):metadata[key]=item
        tensors=[]
        for _ in range(count):
            name=string(f);ndim=take(f,'I')
            if not 1<=ndim<=8:raise ValueError('Invalid dimension count')
            dims=[take(f,'Q') for _ in range(ndim)];kind=take(f,'I');offset=take(f,'Q')
            tensors.append(dict(name=name,shape=dims,ggml_type=kind,offset=offset))
        if type(alignment) is not int or alignment<=0 or alignment>2**20:raise ValueError('Invalid alignment')
        start=(f.tell()+alignment-1)//alignment*alignment
    size=path.stat().st_size;tensors.sort(key=lambda t:t['offset'])
    for i,item in enumerate(tensors):
        end=tensors[i+1]['offset'] if i+1<len(tensors) else size-start
        if not 0<=item['offset']<=end<=size-start:raise ValueError('Invalid tensor span')
        item['serialized_span_bytes']=end-item['offset'];item.pop('offset')
    return dict(file=path.name,file_bytes=size,data_offset=start,metadata=metadata,tensors=tensors)


def plan(files):
    layers={};embedding=0;tail=0;names=set()
    for file in files:
        for item in file['tensors']:
            name=item['name']
            if name in names:raise ValueError('Duplicate tensor across splits')
            names.add(name);match=re.match(r'blk\.(\d+)\.',name);size=item['serialized_span_bytes']
            if match:layers[int(match.group(1))]=layers.get(int(match.group(1)),0)+size
            elif name.startswith('token_embd.'):embedding+=size
            else:tail+=size
    n=len(layers)
    if n<3 or sorted(layers)!=list(range(n)):raise ValueError('Expected >=3 contiguous decoder blocks')
    prefix=[0]
    for i in range(n):prefix.append(prefix[-1]+layers[i])
    candidates=[]
    for cut1 in range(1,n-1):
        for cut2 in range(cut1+1,n):
            sizes=[embedding+prefix[cut1],prefix[cut2]-prefix[cut1],tail+prefix[n]-prefix[cut2]]
            candidates.append((max(sizes),max(sizes)-min(sizes),cut1,cut2,sizes))
    _,_,a,b,sizes=min(candidates)
    return {'plan_only':True,'inference_started':False,'physical_cluster_tested':False,
        'total_artifact_bytes':sum(f['file_bytes'] for f in files),
        'total_tensor_span_bytes':embedding+tail+prefix[-1],
        'block_count':n,'cut_after_zero_based_layers':[a-1,b-1],
        'groups':[{'worker':i+1,'layers':[lo,hi-1],'serialized_span_bytes':size,'weights_gib':size/2**30}
            for i,(lo,hi,size) in enumerate(zip([0,a,b],[a,b,n],sizes))],
        'planning_budget_checks':[{'physical_gib_per_host':ram,'inference_budgets_gib':budgets,
            'serialized_weights_within_budgets':all(size<=budget*2**30 for size,budget in zip(sizes,budgets)),
            'runtime_fit_verified':False} for ram,budgets in [(8,[3,4,4]),(16,[8,10,10]),(32,[20,24,24])]],
        'per_layer_span_bytes':layers,'embedding_span_bytes':embedding,'other_output_span_bytes':tail,
        'largest_tensor':max((t for f in files for t in f['tensors']),key=lambda t:t['serialized_span_bytes']),
        'caveats':['Contiguous 3-way storage balance only; not actual native device assignment.',
        'Embedding assigned to worker 1; all non-block non-embedding tensors assigned to worker 3.',
        'Runtime/cache/workspace/OS reserves are extra; worker 1 needs extra coordination space.',
        'Does not provide file-backed RPC allocations or make 80B resident in 32 GiB.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--files',nargs='+',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Refuse to overwrite a plan')
    result=plan([inspect(path) for path in args.files]);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result['groups'],indent=2))
