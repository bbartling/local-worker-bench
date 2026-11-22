"""Weight-memory/I/O scenarios for the official Qwen3.8-27B checkpoint.
No inference, tensor allocation, model downloads, or measured-speed claims.
"""
import argparse, json, math
from pathlib import Path

PARAMETERS=27781427952
HIDDEN=5120
VOCAB=248320
REVISION='37561816e66b5b9153b1b64c10968c18c1e6f4a0'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--budget-gib',type=float,default=8)
    p.add_argument('--output')
    a=p.parse_args()
    if a.budget_gib<=0: p.error('budget must be positive')
    rows=[]
    for dtype,size in [('BF16_or_FP16',2),('FP32',4),('FP64',8)]:
        total=PARAMETERS*size
        embedding=HIDDEN*VOCAB*size
        rows.append({'dtype':dtype,'weight_bytes':total,'weights_decimal_gb':round(total/1e9,2),
            'weights_gib':round(total/2**30,2),'four_equal_chunks_gib':round(total/4/2**30,2),
            'ideal_minimum_chunks_for_budget':math.ceil(total/(a.budget_gib*2**30)),
            'one_embedding_or_head_tensor_gib':round(embedding/2**30,2),
            'embedding_exceeds_chunk_budget':embedding>a.budget_gib*2**30,
            'seconds_per_decode_token_if_all_weights_read_from_disk':
                {f'{speed}_decimal_GB_per_second':round(total/(speed*1e9),1) for speed in [.5,2,5]}})
    report={'model':'Qwen/Qwen3.8-27B','source_revision':REVISION,'total_checkpoint_parameters':PARAMETERS,
        'checkpoint_dtype':'BF16','text_decoder_layers':64,'chunk_weight_budget_gib':a.budget_gib,'scenarios':rows,
        'caveats':['Arithmetic scenarios, not a benchmark or a completed 27B implementation.',
        'Count includes the full official multimodal checkpoint; a text-only runtime may omit some tensors.',
        'Weights only: runtime, activations, attention/recurrent caches, conversion temporaries, and OS need more RAM.',
        'Ideal chunk counts ignore layer boundaries and indivisible tensors. FP64 embedding/head needs tiling at an 8 GiB budget.',
        'I/O times assume reading the entire weight set for every new token, no useful file cache, and no compute/network cost.',
        'Each token depends on all stages; saved intermediate states do not remove the next token\'s full-model pass.',
        'Expanding BF16 or quantized weights does not reconstruct additional original weight information.',
        'FP64 storage does not guarantee all Qwen3.8 kernels support or execute FP64 arithmetic.'],
        'sources':['https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json',
                   'https://huggingface.co/api/models/Qwen/Qwen3.8-27B']}
    encoded=json.dumps(report,indent=2)
    if a.output: Path(a.output).write_text(encoded,encoding='utf-8')
    print(encoded)

if __name__=='__main__': main()
