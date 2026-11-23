"""Rebuild the illustrated, high-level cluster report; no model calls.

Requires reportlab. Run from the repository root. PDF output is committed;
temporary rendered previews belong under ignored results/.
"""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, Flowable

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/historical-cluster-report.pdf'
NAVY=colors.HexColor('#132C42'); TEAL=colors.HexColor('#087F8C'); LIGHT=colors.HexColor('#EDF5F7')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleX',fontName='Helvetica-Bold',fontSize=27,leading=31,textColor=NAVY,spaceAfter=18))
styles.add(ParagraphStyle(name='Deck',fontSize=12,leading=17,textColor=NAVY,spaceAfter=14))
styles.add(ParagraphStyle(name='BodyX',fontSize=10,leading=14.3,spaceAfter=9))
styles.add(ParagraphStyle(name='SmallX',fontSize=8.3,leading=11,spaceAfter=6))
styles.add(ParagraphStyle(name='CodeX',fontName='Courier',fontSize=8.1,leading=11,backColor=LIGHT,borderPadding=9,spaceAfter=12))
styles['Heading2'].textColor=TEAL
styles['Heading2'].fontSize=14
styles['Heading2'].spaceBefore=10
story=[]

def p(text,style='BodyX'): story.append(Paragraph(text,styles[style]))
def h(text): p(text,'Heading2')
def code(text): story.append(Preformatted(text.replace('\n+','\n'),styles['CodeX']))
def table(headers,rows,widths):
    data=[[Paragraph(escape(str(v)),styles['SmallX']) for v in row] for row in [headers,*rows]]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D5DFE5')),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([t,Spacer(1,10)])
def page(k,title,deck):
    if story: story.append(PageBreak())
    p(f'FIELD GUIDE  /  {k:02d}','SmallX'); p(title,'TitleX'); p(deck,'Deck')
def note(text):
    t=Table([[Paragraph(text,styles['BodyX'])]],colWidths=[480]);t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.5,TEAL),
        ('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    story.extend([t,Spacer(1,12)])

class HopDiagram(Flowable):
    def __init__(self): super().__init__();self.width=480;self.height=225
    def draw(self):
        c=self.canv
        def box(x,y,w,title,sub):
            c.setFillColor(LIGHT);c.setStrokeColor(TEAL);c.roundRect(x,y,w,44,5,fill=1)
            c.setFillColor(NAVY);c.setFont('Helvetica-Bold',9);c.drawCentredString(x+w/2,y+27,title)
            c.setFont('Helvetica',8);c.drawCentredString(x+w/2,y+12,sub)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(TEAL);c.line(x1,y1,x2,y2)
            c.line(x2,y2,x2-4,y2+5);c.line(x2,y2,x2+4,y2+5)
        box(125,180,230,'CLIENT / CODING ASSISTANT','HTTP POST /api/chat; protected connection')
        box(20,105,440,'WORKER 1: API + CHECKPOINT SSD + LOCAL COMPUTE','gateway :11434 -> facade :11437 -> llama-server :ephemeral')
        arrow(240,180,240,149)
        box(0,25,215,'WORKER 2: ggml-rpc-server','RPC :50052 -> local CPU / assigned tensors')
        box(265,25,215,'WORKER 3: ggml-rpc-server','RPC :50052 -> local CPU / assigned tensors')
        c.setStrokeColor(TEAL);c.line(240,105,240,85);c.line(107,85,372,85)
        arrow(107,85,107,69);arrow(372,85,372,69)
        c.setFillColor(NAVY);c.setFont('Helvetica',8)
        c.drawString(0,9,'Private ggml RPC links; response returns through worker 1. Proposed topology.')

page(1,'Local AI, spread across\nsmall computers','A practical guide to models, memory, APIs and an overnight coding cluster.')
p('Prepared for Ben | Updated 23 November 2026 | local-worker-bench','SmallX')
note('<b>The design:</b> three CPU workers, with worker 1 hosting the application API, complete checkpoint on SSD, inference coordinator and local compute. Workers 2 and 3 expose native RPC compute. No separate controller computer is required.')
story.append(HopDiagram())
h('What this report helps you decide')
p('What a model contains; how its computation can be divided; what memory and disk offload really mean; which libraries do which jobs; what our API accepts; and what happens at every request hop.')
p('<b>Status:</b> measured work includes a small four-process numerical proof, native loopback RPC practice and actual 80B disk-backed coding on one PC. Pages 20-25 cover those new results and hosted-model supervision. A physical three-worker cluster and durable overnight queue remain proposed. Illustrative examples are not measured responses.')
p('Repository: <link href="https://github.com/bbartling/local-worker-bench" color="#087F8C">github.com/bbartling/local-worker-bench</link>','SmallX')

page(2,'What a model actually is','A model is a learned numerical program, plus the instructions needed to run it.')
table(['Part','Plain-English job'],[
('Weights / parameters','Learned numbers that encode patterns. 30B means roughly 30 billion parameters, not 30 GB of RAM.'),
('Architecture','The arrangement of layers and operations: attention, feed-forward blocks, experts, normalization and sometimes recurrent state.'),
('Tokenizer + chat template','Convert messages into token IDs and the exact conversation format expected by that model.'),
('Inference engine','Executes the architecture using weights on a CPU/GPU. Also manages buffers, caches and sampling.'),
('Runtime state','Intermediate activations, attention KV caches or recurrent state, and temporary workspace. This is extra memory beyond the weights.')],[125,355])
h('How one answer is produced')
p('<b>Prefill:</b> the worker processes the prompt and builds useful state. <b>Decode:</b> it predicts one next token, adds that token to the sequence, then repeats until a stop condition or output limit. Tokens can be words, word fragments or punctuation.')
h('Size and precision are different knobs')
p('Ideal weight storage is parameter count multiplied by bytes per parameter: BF16/FP16 use 2 bytes, FP32 uses 4, FP64 uses 8. A 4-bit representation starts around half a byte per parameter, but scales, metadata and mixed-precision tensors add overhead. Actual files are the better sizing input.')
p('Quantization trades numerical fidelity for smaller storage and often lower memory bandwidth. Expanding BF16 weights to FP64 does not recover lost training information. For this project, good quantization plus a stronger model is a hypothesis to test, not a guaranteed quality win.')
note('<b>MoE:</b> a mixture-of-experts model uses only selected experts for each token. Qwen3-Coder-Next has 80B total parameters and about 3B active [1]. The inactive weights still need storage and an access strategy; it is not simply a 3B-sized download.')

page(3,'How slicing and stitching works','We divide numerical work and preserve its dependencies. We do not glue together independently generated answers.')
table(['Technique','What is divided','Fit for this project'],[
('File sharding','A checkpoint is packaged into several files.','Useful for downloads; does not by itself split execution or reduce peak RAM.'),
('Layer / pipeline split','Early layers run on A, middle layers on B, final layers on C. Activations cross the network.','A clear CPU-cluster experiment. One sequence still depends on each stage in order.'),
('Tensor parallelism','One operation is divided across devices with frequent synchronization.','Possible with supporting engines; ordinary Ethernet may make communication very expensive.'),
('Disk / layer offload','Weights are brought into RAM as needed, computed, and released or evicted.','Can exceed resident RAM, but repeated SSD reads and cache behavior may dominate runtime.'),
('Data parallelism','Each machine has a complete model and handles separate jobs.','Good throughput; does not make one oversized model fit.')],[105,180,195])
h('What must be preserved')
p('All stages must use the same checkpoint, compatible kernels and quantization, correct layer ordering, token positions, attention masks and cache state. Residual connections, tied embeddings and output heads need correct ownership. Arbitrary equal-sized byte cuts are not runnable partitions.')
h('What moves between nodes?')
p('In a layer pipeline, a boundary carries arrays of intermediate numbers, with shape, dtype, request ID, token position and cache references. These are not English summaries. The final output head produces vocabulary scores; the coordinator samples a token and continues.')
p('In native RPC, the engine can send lower-level tensor operations and buffers instead of our simple stage-shaped messages. The backend owns the graph; Ansible and Ray do not infer that graph automatically. llama.cpp exposes remote CPU devices through its experimental RPC backend [2].')
note('Exact small-model boundary matches are useful correctness evidence. Quantization, different kernels and sampling can change numerical results; evaluate correctness tolerances and actual task quality separately.')

page(4,'One request, every hop','Illustrative three-stage flow. The current production-shaped facade still drives one local native process per request.')
table(['Hop','Owner','What happens'],[
('1. Submit','Client -> worker 1 gateway','Send authenticated JSON: model alias, plain-text messages, output budget and format.'),
('2. Admit','Gateway -> local facade','Gateway checks access and forwards locally. The facade validates registration and budgets before native inference.'),
('3. Prepare','Worker 1','Apply chat template, tokenize text, allocate state and load/admit required weight partitions.'),
('4. Stage A','Worker 1','Embedding and early blocks transform the prompt/token. Send boundary activations to worker 2.'),
('5. Stage B','Worker 2','Middle blocks consume activations using their own weights and state; forward results.'),
('6. Stage C','Worker 3','Final blocks and output head produce token scores. Send scores or selected result back to coordinator.'),
('7. Repeat','Worker 1 + workers','Choose the next token. Repeat the ordered stages until stop or token limit. Keep state consistent.'),
('8. Return','Worker 1 -> client','Decode final text, attach timing/receipt ID, stop owned process as configured; The local gateway forwards the answer.'),
('9. Review','Supervisor / deterministic checks','Validate JSON, inspect candidate code, then run approved tests. Save first-pass and repair scores separately.')],[70,110,300])
h('Saving work overnight')
p('A proposed durable job API would accept a request and return a job ID immediately. Worker 1 would record state and heartbeats while workers store larger artifacts. A dropped connection need not lose a job. This queue is not implemented yet; today the call is synchronous.')
p('The small demo saves intermediate tensors for verification, recomputes prefixes and has no production KV-cache protocol. Persisting activation files is not enough to resume arbitrary token generation after a crash. Weight unloading must not discard live state that a later step requires.')

page(5,'A generic API request','Use a client-side SSH tunnel to the worker 1 gateway, or a deliberately protected private network.')
p('<b>Illustrative request:</b> the alias must already exist on the compute worker. Nothing is automatically downloaded. The token below comes from the client environment, not from source control.')
code('curl http://127.0.0.1:11434/api/chat \\\n+  -H "Authorization: Bearer $LWB_API_TOKEN" \\\n+  -H "Content-Type: application/json" \\\n+  -d \'{\n+    "model": "my-coder",\n+    "messages": [{"role": "user",\n+      "content": "Return JSON with source for add(a,b)."}],\n+    "stream": false,\n+    "think": false,\n+    "format": "json",\n+    "options": {"num_thread": 4, "num_ctx": 2048,\n+                "num_predict": 256}\n+  }\'')
p('The shell example uses POSIX syntax. In Python, send the same object with urllib.request or requests. The repository client reads LWB_API_TOKEN to set the Bearer header. Never send secrets as part of the model prompt.')
h('Illustrative successful response - shortened')
code(json.dumps({
    'model':'my-coder',
    'message':{'role':'assistant','content':json.dumps({'source':'def add(a,b): return a+b'})},
    'done':True,'done_reason':'stop','resource_receipt':'example-receipt-id',
    'code_executed':False,'controller_inference':False},indent=2))
p('message.content is text; in JSON mode, parse that text as JSON before inspecting source. A syntactically valid answer is not proof that the code is correct. A length stop means the output budget was reached, and our benchmark treats truncation as failure.')
note('The API hides inference placement from the client. That abstraction does not mean the current single-worker engine already supports the proposed three-node partitioned execution.')

page(6,'Routes and request parameters','The repository implements an Ollama-shaped subset, not the entire Ollama API [3].')
table(['Route','Current worker 1 gateway behavior'],[
('GET /health','Public local gateway health. Legacy inference_on_controller=false describes the gateway process, not the host, which also runs inference.'),
('GET /api/tags','Authenticated; lists ready registered models from the worker.'),
('GET /api/ps','Authenticated; reports the worker active model/process, not a cluster-wide scheduler.'),
('GET /api/version','Authenticated; forwards worker version/status.'),
('POST /api/chat','Authenticated, synchronous, stream:false. One active gateway chat; concurrent chat gets 429.'),
('POST /api/generate','Unload only: {"model":"my-coder","keep_alive":0}. Not a generation endpoint.'),
('/v1/* and /jobs/*','Not exposed by the gateway. Worker has GET /v1/models; durable jobs remain proposed.')],[135,345])
table(['Field','Actual worker contract'],[
('model','Known registered alias only; no automatic model escalation.'),
('messages','1-20 system/user/assistant messages; role + text content only; <=12,000 characters total.'),
('stream / think','Both must be false when supplied. Tools and images are unsupported.'),
('format','Absent, "json", or a JSON-schema object; translates to native response_format.'),
('options.num_thread','Must match profile; profile permits 1-4, default 4.'),
('options.num_ctx','Must match profile; profile permits 512-8192, default 2048.'),
('options.num_predict','Integer 1 through the registered maximum, which is <=1024.'),
('Other accepted options','temperature / presence_penalty / repeat_penalty / seed names are accepted, but not passed through as tunable controls. Current native request forces temperature=0, presence_penalty=0; repeat/seed are ignored.')],[135,345])
p('HTTP bodies are bounded at 1 MiB. Native responses are bounded at 2 MiB. Profile settings, not request parameters, own memory limits, reserve, timeouts and weight paths. Unsupported options are rejected; this is intentionally narrower than a general serving engine.','SmallX')

page(7,'Hardware: where the model fits','Slow is acceptable, but available address space is not the same as usable physical RAM.')
table(['3 compute nodes','Worker 1 + 2 + 3 budget','Candidate experiment'],[
('8 GiB each','3 + 4 + 4 / 11 GiB total','Smaller resident baseline; explicit disk-backed partition streaming for larger weights.'),
('16 GiB each','8 + 10 + 10 / 28 GiB total','30B Q4 candidate with measured runtime/cache headroom. 80B Q4 still needs disk backing.'),
('32 GiB each','20 + 24 + 24 / 68 GiB total','80B Q4 capacity candidate; not a measured fit guarantee or speed promise.')],[100,150,230])
p('These are conservative starting budgets in GiB, not measured resource limits for those machines. Worker 1 may need a smaller partition because it also coordinates inference. Advertised hardware GB and binary GiB differ. Worker 1 needs extra headroom; there is no fourth controller.')
h('Use real artifact sizes')
p('The cached 30B Q4 file is about <b>17.28 GiB</b>. The pinned 80B Q4 download totals about <b>45.09 GiB</b>. Weight fit alone ignores activations, cache, workspace, runtime and OS reserve. Dividing a weight total by three is only a lower-level planning estimate; layer and expert sizes can be uneven.')
h('Disk offload is possible; repeated I/O is the cost')
p('As a deliberately simple lower-bound example, reading 45.09 GiB at a sustained 0.5 GiB/s costs about 90 seconds before computation or network time. A dense full-weight reread per token would repeat that cost. MoE expert selection and useful caching change the bytes read, so this arithmetic is not an 80B token-speed prediction.')
h('Why simulation can mislead')
p('Four processes on this 32 GiB PC share the OS file cache and storage. A 4 GiB process working-set cap does not turn the host into an 8 GiB machine. Windows residency limits do not cap total system file cache or private commit. Our Linux monitored-only mode has no hard RAM cap.')
note('The practical sweet spot is the model with the best reviewed coding results within a tolerable completion time and failure rate. Parameter count alone cannot establish it. Compare the same tasks, context and output budget across models and hardware.')

page(8,'Libraries and deployment roles','Keep infrastructure, scheduling and tensor execution separate.')
table(['Component','Role and limitation'],[
('Ansible on worker 1/laptop','Inventory, SSH provisioning, pinned builds, services and health checks. Does not split a model graph [4].'),
('worker 1 gateway: Python stdlib','HTTP forwarding, Bearer authentication, fixed upstream, one active chat. No ML dependency or local fallback.'),
('llama.cpp / ggml RPC','CPU GGUF execution and remote devices. Version/architecture support must be checked. RPC is experimental; keep it private/tunneled [2].'),
('PyTorch + Transformers','Our small numerical proof loads explicit layer groups and hands off tensors. Architecture-specific code, not a universal splitter.'),
('safetensors + psutil','Checkpoint tensor format and process/host measurements in the demo. Only trusted local artifacts should enter the custom handoff path.'),
('Hugging Face Accelerate','Can place/offload compatible modules across local devices/CPU/disk. Not an automatic multi-machine low-RAM cluster engine [5].'),
('Ray, optional','Python actors/tasks can supervise jobs or explicit stages. It does not discover a correct partition or reduce model memory by itself [6]. Not installed by our plan.')],[135,345])
h('Ansible rollout order')
p('<b>1.</b> Inventory exactly three compute workers; worker 1 is also coordinator. <b>2.</b> Run Ansible from worker 1 or a developer laptop. <b>3.</b> Build compatible pinned backends on every host. <b>4.</b> Download and verify the full checkpoint on worker 1 SSD, then deploy the gateway/facade there. <b>5.</b> Configure private native RPC links and smaller worker 1 placement. <b>6.</b> Verify small-model correctness, cancellation and worker loss before larger experiments.')
p('Use one inference job initially and four threads per worker. Do not silently change swap/pagefile settings. A local service restart must not silently replay an overnight job. TLS/VPN/SSH provides transport protection; a Bearer token over plain HTTP does not encrypt prompts.')
note('The repo contains a deployment plan, not finished Ansible roles or a Ray cluster launcher. The current gateway has no durable queue, automatic retry, checkpoint recovery or cluster-wide resource scheduler.')

page(9,'Can every model do this?','Many open models can be distributed in principle. Support is specific to the architecture, engine and hardware.')
table(['Model situation','What to expect'],[
('Standard decoder Transformer','Layer boundaries are often natural split points, but attention masks, positions, tied tensors and KV caches must remain correct.'),
('MoE or hybrid/recurrent model','Expert routing and recurrent/attention state add placement and memory complexity. Support cannot be assumed from a similar model name.'),
('Vision / audio / multimodal','Additional encoders, projectors, preprocessing and input formats need support. Our plain-text API does not accept these inputs.'),
('Quantized checkpoint','Engine must understand both the architecture and exact quantization format. A GGUF extension alone is not a compatibility guarantee.'),
('Hosted proprietary model','No local checkpoint means we cannot partition its weights. We can route API calls to it, which is a different operation.')],[140,340])
h('Evidence we have versus work still ahead')
p('<b>Verified engineering checks:</b> 63 repository tests passed, plus 95 deterministic fixture controls. These offline checks do not establish that a model solved 95 tasks. Gateway tests use a fake upstream, including unavailable-worker behavior.')
p('<b>Small-model proof:</b> Qwen3-0.6B split over four local TCP processes matched eight FP64 stage boundaries and two greedy token results against its reference. It is not a three-physical-node or coding-quality result.')
p('<b>Bounded 30B run:</b> the rebuilt single-worker backend completed HTTP, motor, elapsed and import generations with four threads / 2048 context. HTTP matched the verdict; reviewed motor scored 49/49 and elapsed 39/46 first pass. Import is ungraded. A prior bundled-backend load failed the desktop reserve; that failure matters.')
p('<b>Later measured results:</b> pages 18-25 cover small-model native RPC practice, then actual 80B single-PC disk-backed coding grades. A physical three-node memory/speed result, durable overnight jobs and a universal model slicer remain unestablished. The larger model did not win every fixture.')
note('For coding delegation, the stronger assistant remains supervisor: give bounded context, require a candidate, inspect it, run independent checks, and preserve failed first attempts. A valid HTTP 200 or fluent explanation is not a correct patch.')

page(10,'Reference and quick-start map','Read the architecture first; treat prototypes as experiments with explicit acceptance criteria.')
h('Repository entry points')
for label,path in [('Worker roles, rollout and RAM scenarios','docs/three-worker-cluster-plan.md'),('Experimental tool usage and caveats','docs/offload-experiments.md'),('Gateway implementation','local_worker_bench/gateway.py'),('Worker API and resource receipts','local_worker_bench/offload_api.py'),('Small-model four-process proof','examples/sharded-qwen/cluster_demo.py'),('Pinned model-download manifest','examples/offload/qwen3-coder-next-q4.download.json')]:
    url='https://github.com/bbartling/local-worker-bench/blob/main/'+path
    p(f'<b>{label}</b><br/><link href="{url}" color="#087F8C">{path}</link>','SmallX')
h('Primary sources checked for this report')
sources=[
('1. Qwen3-Coder-Next model card','https://huggingface.co/Qwen/Qwen3-Coder-Next'),
('2. llama.cpp RPC documentation','https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md'),
('3. Ollama chat API; upstream reference, not our full contract','https://docs.ollama.com/api/chat'),
('4. Ansible installation and node roles','https://docs.ansible.com/projects/ansible/latest/intro_installation.html'),
('5. Accelerate: loading big models into memory','https://huggingface.co/docs/accelerate/concept_guides/big_model_inference'),
('6. Ray actors','https://docs.ray.io/en/latest/ray-core/actors.html')]
for label,url in sources:p(f'<b>{label}</b><br/><link href="{url}" color="#087F8C">{escape(url)}</link>','SmallX')
h('Useful next milestone')
p('Deploy the API and native coordinator on worker 1 with the full checkpoint on SSD. Measure loading peaks and reserve extra headroom there. Then verify a small model across three real workers before comparing larger coders on reviewed tasks.')
p('Report source is scripts/build_cluster_report.py. This document describes the code at the time of writing; subsequent API changes should trigger a report rebuild. Illustrative JSON and topology are explanations, not benchmark receipts.','SmallX')

page(11,'Who owns the API?','llama.cpp serves the model. Our surrounding service still owns the workflow.')
note('<b>Yes for inference serving; not everything:</b> llama-server can provide the model HTTP API. The worker 1 gateway, deployment automation and proposed durable overnight jobs are separate responsibilities. Llama is a model family; llama.cpp is software that also supports other compatible model families.')
table(['Layer','What we actually use or propose'],[
('Client-facing API','Our worker 1 gateway exposes an authenticated Ollama-shaped /api/chat subset. It does not expose native /v1/* routes.'),
('Worker facade','Our /api/chat validates profiles and budgets, then starts one local native process and records resource receipts.'),
('Native serving','llama-server provides /v1/chat/completions internally. Upstream also supports streaming and structured JSON, subject to model/build support [7]. Our facade does not enable every upstream feature.'),
('Native distributed work','ggml RPC is the proposed remote-device transport. It is not wired into the current facade configuration, and is not a generic HTTP chat protocol.'),
('Overnight application','Durable /jobs routes, leases, retries, recovery and a quality-review ledger remain implementation work.')],[130,350])
h('Do we use mpi4py?')
p('No. The educational proof uses HTTP/TCP between Python processes; the planned native inference path uses ggml RPC. mpi4py could transport arrays for another custom pipeline, but would not automatically partition the model or manage its cache/state. Ray is optional future job orchestration, not an installed splitter. Neither is required to make an HTTP model request.')
h('Write this accurately')
p('One compatible model can have computation placed across multiple workers, with one client request and one final answer. A split checkpoint is not itself a cluster deployment. Our layer-by-layer illustration explains dependencies; actual native RPC communication need not follow a direct worker-1-to-2-to-3 topology. Worker 1 hosts both the API and local inference, with a smaller model allocation.')
p('Reusable write-up: <link href="https://github.com/bbartling/local-worker-bench/blob/main/docs/llama-api-and-cluster.md" color="#087F8C">docs/llama-api-and-cluster.md</link>','SmallX')
p('[7] Native server reference: <link href="https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md" color="#087F8C">llama.cpp/tools/server/README.md</link>. Upstream capabilities are not a promise that our pinned prototype exposes them.','SmallX')

page(12,'Installed software and call paths','Three computers. HTTP reaches worker 1; native RPC reaches the remote compute devices.')
table(['Host','Install and role'],[
('Worker 1','Compatible llama.cpp build: llama-server. Python gateway/facade. Complete checkpoint on SSD. Local inference plus cluster coordination.'),
('Worker 2','Compatible llama.cpp build: ggml-rpc-server. Local CPU kernels and assigned tensors/state. Optional transfer cache on SSD.'),
('Worker 3','Compatible llama.cpp build: ggml-rpc-server. Same remote-compute role; no separate public chat API required.')],[100,380])
code('CLIENT\n  | HTTP POST /api/chat (protected/tunneled)\nWORKER 1: gateway :11434\n  | local HTTP POST /api/chat\nWORKER 1: facade :11437\n  | local HTTP POST /v1/chat/completions\nWORKER 1: llama-server :ephemeral + checkpoint SSD\n  | native ggml RPC             | native ggml RPC\nWORKER 2                     WORKER 3\n  ggml-rpc-server :50052        ggml-rpc-server :50052\n  CPU / assigned tensors       CPU / assigned tensors')
p('Example install path: /opt/llama.cpp/bin/ on Linux, built for each host architecture with RPC support. Example checkpoint location: /srv/local-worker/models/ on worker 1. Ports are illustrative; remote RPC must be private/tunneled. This topology remains proposed: the current facade is local-only and needs a verified RPC placement profile.')
h('Do enterprise data centers do something similar?')
p('Yes in the architectural sense: one serving endpoint can coordinate distributed model work. vLLM documents tensor/pipeline parallel serving and multi-node execution, including Ray as a distributed runtime [8]. That does not mean enterprise systems use our code or llama.cpp RPC.')
p('Our comparison also needs reliability and operational requirements: scheduling, access controls, monitoring and failure recovery. Larger systems may separate those roles again. Here worker 1 intentionally combines them and is a single point of failure. Three low-RAM CPU hosts are an experiment, not a data-center performance equivalent.')
p('[8] <link href="https://docs.vllm.ai/en/latest/serving/parallelism_scaling/" color="#087F8C">vLLM: Parallelism and Scaling</link>.','SmallX')

from cluster_report_appendix import append_pages, append_practice_results
append_pages(story,page,p,h,code,table,note)
append_practice_results(story,page,p,h,code,table,note,ROOT)
from streaming_report_appendix import append as append_streaming
append_streaming(story,page,p,h,code,table,note,ROOT)

def footer(canvas,doc):
    canvas.setStrokeColor(TEAL);canvas.line(54,42,558,42)
    canvas.setFont('Helvetica',8);canvas.setFillColor(NAVY)
    canvas.drawString(54,29,'LOCAL WORKER BENCH  |  UPDATED 23 NOV 2026  |  EXPERIMENTAL DESIGN')
    canvas.drawRightString(558,29,str(doc.page))

if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUT),pagesize=(612,792),rightMargin=54,leftMargin=54,topMargin=45,bottomMargin=57,
        title='Local AI Cluster Explained',author='Local Worker Bench',subject='Three CPU workers, model serving and API request flow')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT)
