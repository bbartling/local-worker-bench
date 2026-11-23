"""Explanatory PDF pages derived from the repository's actual demo code.

Imported only by the ReportLab report builder. No PyTorch import or inference.
"""
from reportlab.platypus import Flowable, Spacer
from reportlab.lib import colors


class SequenceDiagram(Flowable):
    def __init__(self,lanes,events):
        super().__init__(); self.lanes=lanes; self.events=events
        self.width=480; self.height=55+len(events)*25

    def draw(self):
        c=self.canv; n=len(self.lanes); step=480/n
        xs=[step*(i+.5) for i in range(n)]; top=self.height-25
        for x,label in zip(xs,self.lanes):
            c.setFillColor(colors.HexColor('#EDF5F7'));c.setStrokeColor(colors.HexColor('#087F8C'))
            c.roundRect(x-step*.46,top-10,step*.92,28,4,fill=1)
            c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica-Bold',8)
            c.drawCentredString(x,top+1,label)
            c.setStrokeColor(colors.HexColor('#C5D6DE'));c.line(x,top-10,x,20)
        for i,(start,end,label,phase) in enumerate(self.events):
            y=top-30-i*25; x1=xs[start]; x2=xs[end]
            color=colors.HexColor('#3263A8' if phase=='load' else '#087F8C')
            c.setStrokeColor(color);c.setFillColor(color);c.line(x1,y,x2,y)
            sign=1 if x2>x1 else -1
            c.line(x2,y,x2-sign*5,y+3);c.line(x2,y,x2-sign*5,y-3)
            c.setFont('Helvetica',7.8);c.drawCentredString((x1+x2)/2,y+7,label)


class LayerCuts(Flowable):
    def __init__(self):super().__init__();self.width=480;self.height=95
    def draw(self):
        c=self.canv
        for group in range(4):
            x=group*120
            c.setFillColor(colors.HexColor(['#D4E9EF','#BDE0DC','#DCE6F8','#E2DDF0'][group]))
            c.setStrokeColor(colors.white);c.rect(x,35,118,35,fill=1)
            c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica-Bold',9)
            c.drawCentredString(x+59,55,f'Stage {group}')
            c.setFont('Helvetica',9);c.drawCentredString(x+59,41,f'layers {group*7}-{group*7+6}')
            if group<3:
                c.setStrokeColor(colors.HexColor('#087F8C'));c.setDash(3,2);c.line(x+119,20,x+119,82);c.setDash()
        c.setFont('Helvetica',8);c.drawString(0,8,'Zero-based layer indices. Cuts follow layers 6, 13 and 20; not byte offsets.')


class TensorGrid(Flowable):
    def __init__(self):super().__init__();self.width=480;self.height=105
    def draw(self):
        c=self.canv;c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica-Bold',9)
        c.drawString(0,90,'Toy activation tensor: 1 request x 3 tokens x 4 features')
        for row in range(3):
            c.setFont('Helvetica',8);c.drawString(0,62-row*22,f'Token {row}')
            for col in range(4):
                x=65+col*65;y=54-row*22
                c.setFillColor(colors.HexColor('#EDF5F7'));c.setStrokeColor(colors.HexColor('#087F8C'));c.rect(x,y,60,20,fill=1)
                c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica',8)
                c.drawCentredString(x+30,y+6,f'{(row*4+col+1)/10:.1f}')
        c.setFont('Helvetica',8);c.drawString(340,55,'Shape: [1, 3, 4]');c.drawString(340,38,'dtype: float32');c.drawString(340,21,'device: CPU')


def append_pages(story,page,p,h,code,table,note):
    page(13,'Tensors and PyTorch, explained','A tensor is a shaped collection of numbers. PyTorch is software that stores and computes with those numbers.')
    story.append(TensorGrid())
    p('Think of a spreadsheet extended to more dimensions. A scalar is one number; a vector is a list; a matrix is a table. A tensor generalizes these shapes. The dtype specifies the number representation, and the device says where its storage and computation live [9].')
    table(['Tensor in our demo','Meaning and illustrative shape'],[
        ('input_ids: integers','Token IDs, not character codes: [batch, sequence]. The demo uses one request, so batch=1.'),
        ('weights: floating point','Learned arrays used by embedding, decoder and output layers. They stay with the assigned stage; they are not a new prompt.'),
        ('hidden: floating point','Intermediate activations: [1, sequence_length, 1024] for our Qwen3-0.6B configuration. These cross stage boundaries.'),
        ('logits: floating point','Scores for possible next tokens: [1, 151936] in this demo. argmax selects one integer token ID.')],[130,350])
    h('When our code uses PyTorch')
    p('demo.py uses torch to load weights, build modules, multiply arrays, save tensors and compare outputs. Transformers supplies Qwen layer definitions and the tokenizer. torch.inference_mode() avoids training/autograd bookkeeping; this experiment does not train or update weights. The native llama.cpp route instead runs C/C++ ggml tensors and kernels; its inference does not require Python PyTorch.')
    note('Raw activation storage example: [1, 128, 1024] contains 131,072 values. FP32 uses 512 KiB; FP64 uses 1 MiB, before input IDs, serialization, HTTP and base64 overhead. These are arithmetic examples, not measured network payload sizes.')
    p('[9] <link href="https://docs.pytorch.org/tutorials/beginner/basics/tensorqs_tutorial.html" color="#087F8C">PyTorch: Tensors</link>. Toy numbers above illustrate shape; they are not model activations.','SmallX')

    page(14,'Where our cutting lines come from','The Python proof contains an explicit rule. The native engine has a separate placement algorithm.')
    h('Current Python proof: examples/sharded-qwen/demo.py')
    code('n = model.config.num_hidden_layers\ngroups = [list(range(i*n//4, (i+1)*n//4))\n          for i in range(4)]')
    story.append(LayerCuts())
    p('prepare() reads n from the loaded model configuration, partitions the layer indices, selects matching entries from state_dict(), and writes weights-0.pt through weights-3.pt. For the tested 28-layer model, the integer formula makes four seven-layer groups. The first group also gets the embedding; the final group gets normalization and the output head. Tied embedding/head weights are deliberately duplicated in storage.')
    p('manifest.json records groups, sizes, dtype and revision. stage() builds only the assigned Qwen layers, loads that shard and compares its boundary output with the full-model reference. prepare() first loads the complete small model and computes a reference; it is not a low-RAM preparation path for an arbitrarily large checkpoint.')
    h('Proposed native route: llama.cpp C++, not a Python cutter')
    p('At the pinned backend revision, src/llama-model.cpp builds normalized split points from explicit proportions or device free-memory reports, then assigns layers to devices. The host input layer and output placement receive separate handling. This is load-time placement, not rewriting an 80B model into four Python files. See [10] for the exact implementation.')
    note('The demo still hardcodes four stages, including index==3 for the last stage. A three-worker adaptation needs deliberate code and verification. It is not enough to edit the divisor. The current offload facade is also local-only; it does not yet pass a remote RPC placement profile.')
    p('[10] <link href="https://github.com/ggml-org/llama.cpp/blob/94f3af3d09e74a0fb35f703194318d3b4037714a/src/llama-model.cpp#L1783-L1842" color="#087F8C">Pinned llama.cpp layer-placement implementation</link>. Proportions are not exact per-process hard memory quotas.','SmallX')

    page(15,'What the Python demo transfers','Actual implemented path: the coordinator relays every stage boundary. All four stage servers currently run on one PC.')
    story.append(SequenceDiagram(['Coordinator','Stage 0','Stage 1','Stage 3*'],[
        (0,1,'POST /stage: step + input_ids','run'),
        (1,0,'state: hidden + IDs, base64 .pt','run'),
        (0,2,'POST /stage: previous state + IDs','run'),
        (2,0,'new hidden state + SHA-256','run'),
        (0,3,'After stage 2*: final stage request','run'),
        (3,0,'logits .pt + next_token + checks','run')]))
    p('*Stage 2 has the same request/reply pattern as stage 1 and is omitted here to keep the drawing readable. The arrows show application messages, not native ggml RPC commands. Nodes bind to 127.0.0.1 with separate ports and per-run Bearer authentication.')
    table(['Code location','Exactly what it does'],[
        ('cluster_demo.py run()','Creates four isolated node folders and processes. Each gets only its own weight shard, plus config, manifest and reference data. Loops over nodes in stage order.'),
        ('cluster_demo.py request()','Sends JSON over HTTP. The state field is base64-encoded bytes of a locally generated PyTorch .pt file, not a list of English words.'),
        ('node() / Handler.do_POST()','Validates /stage input, decodes incoming state to disk, calls demo.stage(), then returns serialized output, digest, checks and measurements.'),
        ('Coordinator after reply','Verifies the response bytes against the supplied digest, saves them, and forwards state in the next request. After stage 3, appends next_token and repeats.')],[145,335])
    note('This is a correctness proof with disk round trips and base64 overhead. It sends full-prefix state because there is no KV cache. A digest detects mismatch against the supplied value; it is not authentication or proof that untrusted tensor data is safe. Use trusted local artifacts only.')

    page(16,'Native RPC: loading versus generation','Proposed three-machine route. We have inspected the native source, but have not measured this physical cluster.')
    story.append(SequenceDiagram(['Worker 1 / llama-server','Worker 2 / RPC','Worker 3 / RPC'],[
        (0,1,'Discover devices / memory','load'),
        (0,2,'Discover devices / memory','load'),
        (0,1,'Allocate + upload assigned weights','load'),
        (0,2,'Allocate + upload assigned weights','load'),
        (0,1,'Input tensors + graph execution','run'),
        (1,0,'Completion / required tensor results','run'),
        (0,2,'Dependent tensors + graph execution','run'),
        (2,0,'Completion / required tensor results','run')]))
    p('<b>Blue = setup/load.</b> Worker 1 opens the checkpoint and establishes assigned remote buffers. <b>Teal = inference work.</b> Numerical inputs and graph operations execute where the engine places them. This is a conceptual coordinator-mediated example, not a captured packet trace or an invariant command ordering.')
    h('What is inside the transport?')
    p('The native ggml RPC code defines operations for device discovery, buffer allocation, tensor writes/reads and graph execution. It carries tensor metadata and raw data through its binary transport. It does not call our /stage route, serialize torch.save() files, or send base64 JSON. There is no PyTorch requirement on this execution path.')
    p('The engine/scheduler determines necessary copies and buffer reuse. Do not assume every weight travels on every token, every worker sees the whole prompt as text, or workers 2 and 3 always talk directly. Exact traffic depends on placement, caching, graph and backend version. Packet/engine logs and byte counters are a future validation task.')
    p('Each decode step depends on the prior token/state. Sampling and text decoding return the final answer through worker 1. Our current facade stops its owned native process after each request, so future cluster mode must explicitly define remote-buffer cleanup and whether weights remain cached.')
    p('Source map: pinned <link href="https://github.com/ggml-org/llama.cpp/blob/94f3af3d09e74a0fb35f703194318d3b4037714a/ggml/src/ggml-rpc/ggml-rpc.cpp" color="#087F8C">ggml-rpc.cpp</link>; this diagram is explanatory, not a completed cluster benchmark.','SmallX')

    page(17,'From source files to one answer','A checklist for following the implementation without confusing its two execution paths.')
    table(['File / function','Role and when it runs'],[
        ('demo.py: prepare()','Preparation: loads the small source model, chooses four boundaries, writes weight shards and full-model reference outputs.'),
        ('demo.py: stage()','Inference: constructs one stage with PyTorch, loads its weights, consumes IDs/hidden state and emits new state or logits.'),
        ('demo.py: run()','Sequential local process proof. Every stage runs in a fresh child process; state passes through local files.'),
        ('cluster_demo.py: run() / node()','Four loopback servers; coordinator relays .pt state via HTTP. Not three physical devices and not native ggml RPC.'),
        ('offload_api.py: Manager._chat()','Application facade: validates/adopts fixed profile, starts owned llama-server, observes resources, calls native HTTP and writes receipts.'),
        ('gateway.py: make_handler()','Authenticated application HTTP forwarding. No tensors or PyTorch; same physical worker 1 can host native inference separately.'),
        ('Native llama-model.cpp / ggml-rpc.cpp','Native model placement and binary remote-device operations. These C++ files belong to the pinned backend, not Python shard preparation.')],[165,315])
    h('What a three-worker implementation must add')
    p('Choose one execution path. For native RPC, enumerate devices, reserve worker 1 overhead, register explicit remote placement, inspect actual layer assignments and measure each host. For a custom Python pipeline, generalize all four-stage assumptions, design cache ownership and transport, and re-run boundary/logit comparisons. These are different engineering tasks.')
    p('A robust record should include model/config hash, layer ownership, actual weight bytes per host, dtype, context, token position, shape, transferred bytes and first-pass quality. Exercise cancellation and missing-worker failures. Never call the three-node cluster verified just because the single-host four-stage reference passed.')
    note('Memory release is also path-specific: demo.py fresh stage processes exit; the HTTP nodes persist and allocators/OS cache may retain memory; the native facade owns one worker process per request. None of these facts alone proves strict total physical-RAM bounds on three computers.')


class TimingBars(Flowable):
    def __init__(self,items):
        super().__init__();self.items=items;self.width=480;self.height=25+len(items)*23
    def draw(self):
        c=self.canv;maximum=max(value for _,value in self.items)
        for i,(label,value) in enumerate(self.items):
            y=self.height-23-i*23
            c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica',8)
            c.drawString(0,y+4,label)
            c.setFillColor(colors.HexColor('#087F8C'));c.rect(145,y,270*value/maximum,14,fill=1,stroke=0)
            c.setFillColor(colors.HexColor('#132C42'));c.drawString(420,y+4,f'{value:.1f}s')


def append_practice_results(story,page,p,h,code,table,note,root):
    import json
    evidence=json.loads((root/'docs/benchmarks/data/2026-11-23-4b-local-rpc.json').read_text(encoding='utf-8'))
    runs=[run for run in evidence['runs'] if any(t['task']!='smoke' for t in run['tasks'])]
    def label(run):
        return 'RPC 3 x 1t' if run['mode']=='rpc' else ('Single 1t' if run['thread_budget'].startswith('1 ') else 'Single 4t')
    page(18,'Measured 4B coding practice','23 November 2026: real native RPC on this PC. First-pass quality and execution cost are separate results.')
    rows=[];bars=[]
    for run in runs:
        for task in run['tasks']:
            grade=task.get('grade',{})
            rows.append([label(run),task['task'],f"{grade.get('passed','?')}/{grade.get('total','?')}",
                f"{task['seconds']:.1f}s",f"{task['timings']['predicted_per_second']:.2f}"])
            bars.append((label(run)+' / '+task['task'],task['seconds']))
    table(['Configuration','Task','Tests','Wall time','Gen tok/s'],rows,[105,75,75,105,120])
    story.append(TimingBars(bars))
    p('Same cached Qwen3.5 4B, same synthetic task prompts, 2048 context, up to 1024 output tokens, JSON format, greedy/non-thinking generation. A run loads once and serves its tasks in order. Code was inspected before the independent hash-gated checker. No repairs are folded into first-pass scores.')
    note('Three RPC CPU devices completed real graph work, but the host and OS cache are shared. This is not three physical 8 GiB machines. A score counts narrow fixtures, including invalid-input cases; it is not an autonomous coding qualification.')
    p('The one-thread single-process motor control produced exactly the same source hash as RPC, at the same 34/49 score. RPC took 14.3% longer. This supports a threading/numerical explanation for the four-thread text difference on this case, not universal equivalence. Timing gaps are not pure network-overhead measurements.')
    p('Historical 30B first pass: motor 49/49, elapsed 39/46 (88/95). These stronger grades come from saved source, reviewed and checked now; its separate cold-load timings are not a controlled speed comparison.')
    p('Full synthetic prompts, candidates, test failures, hashes, timings, placement and resource samples: <link href="https://github.com/bbartling/local-worker-bench/blob/main/docs/benchmarks/data/2026-11-23-4b-local-rpc.json" color="#087F8C">public benchmark evidence</link>. See the companion benchmark for load/memory details.','SmallX')

    plan=json.loads((root/'docs/benchmarks/data/2026-11-23-80b-partition-plan.json').read_text(encoding='utf-8'))
    page(19,'80B: real weight sizes, not a fit claim','The full 48.41 decimal-GB checkpoint is downloaded. Header inspection can plan cuts without loading tensor data.')
    table(['Proposed group','Decoder layers','Weight spans'],[
        [f"Worker {g['worker']}",f"{g['layers'][0]}-{g['layers'][1]}",f"{g['weights_gib']:.2f} GiB"] for g in plan['groups']],[130,160,190])
    p('scripts/plan_gguf_partitions.py inspects the four GGUF headers, groups tensor spans by decoder block, assigns embedding to the first group and remaining output tensors to the last, then searches contiguous three-way cuts minimizing the largest serialized group. It reads metadata, not full tensor payloads, and does not rewrite the model.')
    h('Why 48.41 / 3 is not a memory budget')
    p('The division gives about 16.14 decimal GB of storage per group on average. Actual groups above differ and include padding. Runtime buffers, caches, OS space and coordinator overhead are extra. Three simulated nodes on this PC still share only 32 GiB physical RAM; they do not create additional capacity.')
    table(['Physical RAM per host','Proposed inference budgets','Weight-only result'],[
        [f"{r['physical_gib_per_host']} GiB",' / '.join(str(v) for v in r['inference_budgets_gib'])+' GiB',
            'Within budgets; runtime unverified' if r['serialized_weights_within_budgets'] else 'Exceeds budgets'] for r in plan['planning_budget_checks']],[130,160,190])
    note('This earlier RPC practice did not launch 80B inference. Later pages document actual 80B CPU stream/paged trials, admitted only with an explicit verified large-model manifest. The RPC mode retains its small-file guard and ordinary heap allocation. Closing apps cannot make 45.09 GiB of weights fully resident in a 32 GiB host.')
    h('Next milestone')
    p('Either validate resident RPC on three higher-memory computers, or build and verify explicit disk-backed execution with measured global memory, I/O and cleanup. Passing small-model plumbing and coding tests is necessary evidence, not proof that a larger hybrid MoE model will fit or improve quality.')
