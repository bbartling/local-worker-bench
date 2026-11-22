"""Real Qwen3-0.6B, four sequential disk-backed stages, each in a fresh CPU process.

Uses pretrained BF16 source weights expanded to FP32 or FP64. This is not a
27B run, multi-machine parallelism, or a guarantee of fully FP64 arithmetic:
upstream Qwen RMSNorm/RoPE deliberately perform some internal work in FP32.
"""
import argparse, json, os, pathlib, subprocess, sys, time

MODEL='Qwen/Qwen3-0.6B'

_configured=False

def setup(threads=4):
    global _configured
    import torch
    if not _configured:
        torch.set_num_threads(threads); torch.set_num_interop_threads(1); _configured=True
    return torch

def prepare(args):
    torch=setup(args.threads)
    import psutil, urllib.request
    from transformers import AutoModelForCausalLM, AutoTokenizer
    folder=pathlib.Path(args.folder); folder.mkdir(parents=True,exist_ok=True)
    dtype=getattr(torch,args.dtype)
    required=(0.7e9*torch.tensor([],dtype=dtype).element_size()*2+2e9)
    if psutil.virtual_memory().available<required:
        raise RuntimeError('Insufficient available RAM for the small reference-model comparison.')
    metadata=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{MODEL}',timeout=20))
    revision=metadata['sha']
    print(f'Preparing {MODEL} at pinned revision {revision} in {args.dtype}',flush=True)
    cache=folder.parent/'hf-cache'
    tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=revision,cache_dir=cache,trust_remote_code=False,token=False)
    model=AutoModelForCausalLM.from_pretrained(MODEL,revision=revision,cache_dir=cache,
        dtype=dtype,attn_implementation='eager',trust_remote_code=False,token=False).eval()
    model.config.save_pretrained(folder/'config')
    n=model.config.num_hidden_layers
    groups=[list(range(i*n//4,(i+1)*n//4)) for i in range(4)]
    state=model.state_dict()
    sizes=[]
    for i,group in enumerate(groups):
        part={}
        if i==0: part['embed.weight']=state['model.embed_tokens.weight']
        for layer in group:
            prefix=f'model.layers.{layer}.'
            part.update({k.removeprefix('model.'):v for k,v in state.items() if k.startswith(prefix)})
        if i==3:
            part['norm.weight']=state['model.norm.weight']; part['head.weight']=state['lm_head.weight']
        path=folder/f'weights-{i}.pt'; torch.save(part,path); sizes.append(path.stat().st_size)
        print(f'Shard {i}: layers {group[0]}..{group[-1]}, {sizes[-1]/2**20:.1f} MiB',flush=True)
    text=tokenizer.apply_chat_template([{'role':'user','content':args.prompt}],
        tokenize=False,add_generation_prompt=True,enable_thinking=False)
    tokens=tokenizer(text,return_tensors='pt')['input_ids']
    initial=tokens[0].tolist(); generated=[]; boundaries={}; handles=[]
    for i,g in enumerate(groups):
        def capture(module,inputs,output,index=i): boundaries[str(index)]=output.detach().clone()
        handles.append(model.model.layers[g[-1]].register_forward_hook(capture))
    with torch.inference_mode():
        for step in range(args.tokens):
            logits=model(input_ids=tokens,use_cache=False,logits_to_keep=1).logits[:,-1,:].detach()
            token=int(logits.argmax(-1).item()); generated.append(token)
            torch.save({'logits':logits,'boundaries':dict(boundaries)},folder/f'reference-{step}.pt')
            tokens=torch.cat((tokens,torch.tensor([[token]],dtype=torch.long)),dim=1)
    for handle in handles: handle.remove()
    manifest={'model':MODEL,'revision':revision,'dtype':args.dtype,'groups':groups,
        'parameter_dtypes':sorted({str(p.dtype) for p in model.parameters()}),
        'initial_tokens':initial,'generated_tokens':generated,'reference_text':tokenizer.decode(generated),
        'steps':args.tokens,'shard_bytes':sizes,'source_checkpoint_dtype':'bfloat16',
        'precision_note':'Weights/matmuls use requested dtype; upstream RMSNorm/RoPE retain FP32 internal operations.',
        'algorithm':'No KV cache: recompute the complete prefix each token for a simple reproducible correctness proof.',
        'storage_note':'Tied embedding/head weights are deliberately duplicated in first/last shard.'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Reference output:',repr(manifest['reference_text']),flush=True)

def stage(args):
    torch=setup(args.threads)
    import psutil
    from torch import nn
    from transformers import Qwen3Config
    from transformers.models.qwen3.modeling_qwen3 import Qwen3DecoderLayer,Qwen3RMSNorm,Qwen3RotaryEmbedding
    from transformers.masking_utils import create_causal_mask
    folder=pathlib.Path(args.folder); manifest=json.loads((folder/'manifest.json').read_text())
    if psutil.virtual_memory().available<(folder/f'weights-{args.index}.pt').stat().st_size+4*2**30:
        raise RuntimeError('Not enough available RAM for this shard plus a 4 GiB desktop/runtime reserve.')
    cfg=Qwen3Config.from_pretrained(folder/'config'); cfg._attn_implementation='eager'
    group=manifest['groups'][args.index]
    class Part(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers=nn.ModuleDict({str(i):Qwen3DecoderLayer(cfg,i) for i in group})
            if args.index==0: self.embed=nn.Embedding(cfg.vocab_size,cfg.hidden_size)
            if args.index==3:
                self.norm=Qwen3RMSNorm(cfg.hidden_size,eps=cfg.rms_norm_eps)
                self.head=nn.Linear(cfg.hidden_size,cfg.vocab_size,bias=False)
    with torch.device('meta'): part=Part()
    weights=torch.load(folder/f'weights-{args.index}.pt',map_location='cpu',weights_only=True)
    part.load_state_dict(weights,assign=True,strict=True); part.eval(); del weights
    with torch.inference_mode():
        if args.index==0:
            ids=torch.tensor([json.loads((folder/f'input-{args.step}.json').read_text())],dtype=torch.long)
            hidden=part.embed(ids)
        else:
            previous=torch.load(folder/f'state-{args.step}-{args.index-1}.pt',weights_only=True)
            ids=previous['input_ids']; hidden=previous['hidden']; del previous
        positions=torch.arange(hidden.shape[1]).unsqueeze(0)
        mask=create_causal_mask(config=cfg,inputs_embeds=hidden,attention_mask=None,cache=None,position_ids=positions)
        rotary=Qwen3RotaryEmbedding(cfg); embeddings=rotary(hidden,positions)
        for layer in part.layers.values():
            hidden=layer(hidden,attention_mask=mask,position_embeddings=embeddings,
                         position_ids=positions,cache=None,use_cache=False)
        reference=torch.load(folder/f'reference-{args.step}.pt',weights_only=True)
        error=(hidden-reference['boundaries'][str(args.index)]).abs().max().item()
        tolerance=1e-5 if manifest['dtype']=='float32' else 1e-10
        if error>tolerance: raise AssertionError(f'Stage boundary mismatch: {error}')
        result={'step':args.step,'stage':args.index,'layers':group,'boundary_max_abs_error':error,
                'hidden_dtype':str(hidden.dtype),'parameter_dtypes':sorted({str(p.dtype) for p in part.parameters()})}
        if args.index==3:
            logits=part.head(part.norm(hidden[:,-1:,:]))[:,-1,:]
            result.update(next_token=int(logits.argmax(-1).item()),
                          logits_max_abs_error=(logits-reference['logits']).abs().max().item())
            if result['logits_max_abs_error']>tolerance: raise AssertionError('Final logits mismatch')
            torch.save({'logits':logits},folder/f'logits-{args.step}.pt')
        else:
            torch.save({'hidden':hidden,'input_ids':ids},folder/f'state-{args.step}-{args.index}.pt')
        (folder/f'result-{args.step}-{args.index}.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result),flush=True)
    # Process exit releases the stage's weights. The OS may retain file-cache pages.

def launch(command,folder,label):
    import psutil
    env=os.environ.copy(); env.update(OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',HF_HUB_DISABLE_TELEMETRY='1')
    env['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
    env['HF_HOME']=str(folder.parent/'hf-cache')
    env.pop('HF_TOKEN',None); env.pop('HUGGING_FACE_HUB_TOKEN',None)
    started=time.monotonic(); peak=0; minimum=psutil.virtual_memory().available
    logpath=folder/f'{label}.log'
    with logpath.open('w',encoding='utf-8') as log:
        child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        proc=psutil.Process(child.pid)
        while child.poll() is None:
            try:
                tree=[proc,*proc.children(recursive=True)]
                rss=0
                for member in tree:
                    try: rss+=member.memory_info().rss
                    except psutil.Error: pass
                peak=max(peak,rss)
            except psutil.Error: pass
            minimum=min(minimum,psutil.virtual_memory().available); time.sleep(.2)
        if child.returncode:
            print(logpath.read_text(encoding='utf-8',errors='replace')[-10000:])
            raise RuntimeError(f'{label} failed: {child.returncode}')
    measured={'label':label,'pid':child.pid,'seconds':round(time.monotonic()-started,2),
              'peak_process_tree_rss_gib':round(peak/2**30,3),'minimum_available_ram_gib':round(minimum/2**30,3),
              'process_exited':True}
    print(json.dumps(measured),flush=True); return measured

def run(args):
    folder=pathlib.Path(args.folder).resolve(); folder.mkdir(parents=True,exist_ok=True)
    script=str(pathlib.Path(__file__).resolve()); base=[sys.executable,script]
    metrics=[]
    if args.reprepare or not (folder/'manifest.json').exists():
        metrics.append(launch(base+['prepare','--folder',str(folder),'--dtype',args.dtype,'--tokens',str(args.tokens),'--prompt',args.prompt],folder,'prepare'))
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest['dtype']!=args.dtype: raise ValueError('Use a separate folder for each dtype.')
    tokens=list(manifest['initial_tokens']); generated=[]; results=[]
    for step in range(manifest['steps']):
        (folder/f'input-{step}.json').write_text(json.dumps(tokens))
        for index in range(4):
            metrics.append(launch(base+['stage','--folder',str(folder),'--step',str(step),'--index',str(index)],folder,f'step-{step}-stage-{index}'))
            results.append(json.loads((folder/f'result-{step}-{index}.json').read_text()))
        token=results[-1]['next_token']; generated.append(token); tokens.append(token)
    report={'manifest':manifest,'generated_tokens':generated,'same_greedy_tokens':generated==manifest['generated_tokens'],
            'stage_results':results,'process_measurements':metrics,
            'all_boundaries_verified':all(r['boundary_max_abs_error']<=(1e-5 if args.dtype=='float32' else 1e-10) for r in results),
            'limitations':['Small real Qwen3-0.6B, not Qwen3.8-27B.','Sequential processes, not four parallel devices.',
                           'No KV cache; full prefix is recomputed for each token.','No forced OS file-cache eviction; cached disk reads may be much faster than a too-large model.',
                           'Peak RSS is sampled every 0.2 seconds, not an exact allocator high-water mark.']}
    (folder/'report.json').write_text(json.dumps(report,indent=2))
    if not report['same_greedy_tokens']: raise AssertionError('Greedy token sequence differs')
    print('VERIFIED: all four stage boundaries and final logits match reference; process exited after each stage.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('mode',choices=('run','prepare','stage'))
    p.add_argument('--folder',required=True); p.add_argument('--dtype',choices=('float32','float64'),default='float32')
    p.add_argument('--tokens',type=int,choices=range(1,5),default=2)
    p.add_argument('--threads',type=int,choices=range(1,5),default=4)
    p.add_argument('--reprepare',action='store_true',help='Rebuild shards/reference from the cached source checkpoint.')
    p.add_argument('--prompt',default='Reply with one word: what is the capital of France?')
    p.add_argument('--step',type=int,default=0); p.add_argument('--index',type=int,choices=range(4),default=0)
    args=p.parse_args(); {'run':run,'prepare':prepare,'stage':stage}[args.mode](args)
