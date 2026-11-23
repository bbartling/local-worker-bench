"""Measured disk-backed inference appendix. Requires completed public evidence."""
import json
from reportlab.platypus import Flowable
from reportlab.lib import colors
from cluster_report_appendix import TimingBars, SequenceDiagram


class ResidentFlow(Flowable):
    def __init__(self):super().__init__();self.width=480;self.height=165
    def draw(self):
        c=self.canv
        def box(x,y,w,title,sub):
            c.setFillColor(colors.HexColor('#EDF5F7'));c.setStrokeColor(colors.HexColor('#087F8C'))
            c.roundRect(x,y,w,42,4,fill=1);c.setFillColor(colors.HexColor('#132C42'))
            c.setFont('Helvetica-Bold',8);c.drawCentredString(x+w/2,y+26,title)
            c.setFont('Helvetica',7.5);c.drawCentredString(x+w/2,y+12,sub)
        def right(x1,x2,y):
            c.setStrokeColor(colors.HexColor('#087F8C'));c.line(x1,y,x2,y);c.line(x2,y,x2-4,y+3);c.line(x2,y,x2-4,y-3)
        box(0,105,140,'SSD: ORIGINAL GGUF','File mapping stays valid')
        box(170,105,140,'CPU: LAYER i','Page in required weights')
        box(340,105,140,'AFTER l_out-i','Evict mapped weight pages')
        right(140,170,126);right(310,340,126)
        box(135,25,210,'LIVE RUNTIME STATE','Activations + KV/recurrent state retained')
        c.setStrokeColor(colors.HexColor('#087F8C'));c.line(240,105,240,67)
        c.setFillColor(colors.HexColor('#132C42'));c.setFont('Helvetica',8)
        c.drawString(0,4,'Continue with layer i+1. Output head selects a token; decoder passes repeat.')


def append(story,page,p,h,code,table,note,root):
    data=json.loads((root/'docs/benchmarks/data/2026-11-23-streaming-coding.json').read_text(encoding='utf-8'))
    runs=data['runs']
    page(20,'A model larger than this PC','Actual CPU inference from a 45.09 GiB checkpoint on this approximately 32 GiB Windows host.')
    story.append(ResidentFlow())
    p('Think of SSD as a reference library and RAM as a small workbench. Both methods bring needed weight pages to the workbench. Our explicit policy clears them after each layer; Windows paging can keep useful pages for reuse. Both use the same complete checkpoint and preserve live inference state. We do not stitch together independent mini-model answers.')
    table(['Policy','Who controls residency?'],[
        ('stream / "sliced"','Our code clears mapped weight pages after each layer. Lower observed process RAM, but clearing can discard reusable pages and adds overhead. The original files stay mapped.'),
        ('paged / Windows','Windows chooses which mapped pages to keep or replace within the working-set cap. Useful pages can remain for reuse; the whole model still does not fit in RAM.'),
        ('Both','Four threads, fixed 2048 context, 4 GiB process working-set cap, host free-RAM/commit/private-memory guards, bounded requests and owned-process cleanup.')],[95,385])
    h('Why the model architecture matters')
    p('Qwen3-Coder-Next has 80B total parameters and roughly 3B active per token. Selected experts need not touch every expert weight on every decode step. Storage is still 45.09 GiB; active computation and process residency are different quantities. A dense 80B model may have very different disk costs.')
    note('Python orchestrates the trial and checks receipts. Native C/C++ ggml executes tensors and maintains KV/recurrent state; this path does not use PyTorch inference. Shared OS file cache remains outside the process-RSS measurement. No three-host or isolated 8 GiB result is claimed.')
    p('Implementation: <link href="https://github.com/bbartling/local-worker-bench/blob/main/native/lwb_layer_stream_windows.h" color="#087F8C">native/lwb_layer_stream_windows.h</link>. Microsoft documents working-set removal for unlocked pages with ERROR_NOT_LOCKED; unexpected errors fail verification.','SmallX')

    page(21,'Same patch, different memory policies','A compact HTTP-status repair, graded on 25 hand-derived cases. First pass only.')
    rows=[];bars=[]
    for run in runs:
        for task in run['tasks']:
            if task['task']!='patch':continue
            model='80B' if 'next' in run['model'] else '4B'
            policy={'stream':'Layer eviction','paged':'OS paging','single':'Resident control'}[run['mode']]
            grade=task.get('grade',{})
            peak=max(run['peak_process_rss_gib'],run.get('streaming',{}).get('peak_callback_rss_gib',0))
            rows.append([model,policy,f"{grade.get('passed','?')}/25",f"{task['seconds']:.1f}s",f'{peak:.2f} GiB'])
            bars.append((model+' / '+policy,task['seconds']))
    table(['Model','Policy','Tests','Request wall','Run peak RSS'],rows,[45,130,65,115,125])
    story.append(TimingBars(bars))
    p('The broken function used bool(status). The required repair accepts only exact Python ints in 200-299; invalid types and int subclasses return False. The 4B answer used isinstance and missed the subclass case. The 80B answer used type(status) is int and passed it. This is one narrow contract edge, not a general intelligence scale.')
    p('For each model, the streamed and comparison patch sources had identical hashes. The 80B forced-eviction request took 1082.810 seconds; OS paging took 122.896 seconds, about 8.8 times faster. Generation rates differ further because prefill is separate. Run peaks include loading/all tasks in that run and exclude shared OS cache; they are not isolated task RAM.')
    note('The forced-eviction policy validates capacity and answer preservation on the tested patch, but is costly. The OS-managed paging control is the more practical measured policy on this PC. Cache warmth, run order and other host activity were not controlled statistically.')

    page(22,'Broader coding comparison','The compact patch is not enough. Keep its score separate from the 95 motor/elapsed fixtures.')
    previous=json.loads((root/'docs/benchmarks/data/2026-11-23-4b-local-rpc.json').read_text(encoding='utf-8'))
    rows=[]
    for label,run in [('4B single 4t',next(r for r in previous['runs'] if 'single-coding' in r['run'])),
                      ('4B RPC 3 x 1t',next(r for r in previous['runs'] if 'three-coding' in r['run'])),
                      ('30B historical',previous['historical_runs'][0])]:
        grades={t['task']:t.get('grade') for t in run['tasks']}
        m=grades['motor'];e=grades['elapsed']
        rows.append([label,f"{m['passed']}/49",f"{e['passed']}/46",f"{m['passed']+e['passed']}/95"])
    paged=next(r for r in runs if r['mode']=='paged' and 'next' in r['model'])
    grades={t['task']:t.get('grade') for t in paged['tasks']}
    m=grades.get('motor');e=grades.get('elapsed')
    rows.append(['80B OS paging',f"{m['passed']}/49" if m else 'Not graded',f"{e['passed']}/46" if e else 'Not graded',
        f"{m['passed']+e['passed']}/95" if m and e else 'Partial'])
    table(['Configuration','Motor','Elapsed','First-pass total'],rows,[150,100,100,130])
    timing=[]
    for task in paged['tasks']:
        if task['task'] in ('motor','elapsed'):
            timing.append([task['task'],f"{task['seconds']:.1f}s",str(task['usage']['completion_tokens']),f"{task['timings']['predicted_per_second']:.3f}"])
    if timing:table(['80B task','Request wall','Output tokens','Generation tok/s'],timing,[100,125,125,130])
    p('These are synthetic bounded function drafts. The model received requirements and returned source; a supervisor inspected the source before hash-gated checks. No repairs are included. Historical 30B trial conditions differ; its timing is not a controlled model-speed comparison. A fixture total includes correlated input-validation cases and cannot rank autonomous repository engineering.')
    note('The broader 80B result above belongs to OS-managed mmap paging, not the much slower explicit per-layer-eviction policy. The latter was graded on the separate 25-case patch. Preserve that distinction when writing about the experiment.')
    p('Full evidence includes prompts, answers, source hashes, every failed case, startup/prompt/generation times, resource samples and cleanup. The compressed trace contains repeated resident-page observations; it is not a unique-page count or a physical SSD byte counter.','SmallX')

    page(23,'Use the experiment through our API','The client request stays ordinary JSON. Memory policy belongs to the registered server profile.')
    code('Profile settings (selected fields):\n  "layer_stream": true,\n  "threads": 4, "context": 2048,\n  "working_set_gib": 4, "private_limit_gib": 6,\n  "reserve_gib": 6, "request_timeout": 1200')
    p('Point backend_executable at the isolated layer-stream build and register all required GGUF parts. layer_stream:true selects explicit eviction and requires verified callback evidence. false keeps mmap and the working-set limit but delegates paging to Windows. It does not make all weights resident. The example registration uses separate aliases so policy is an explicit supervisor choice.')
    code('POST /api/chat\n{\n  "model": "coder80-paged",\n  "messages": [{"role":"user",\n                "content":"Return a compact code draft."}],\n  "stream": false, "think": false,\n  "options": {"num_predict":128}\n}')
    p('serve-offload listens on loopback. The existing authenticated gateway can front it. The model result carries a resource receipt ID; a requested streaming mode with missing/invalid layer evidence fails closed. Starting the API does not start inference, download models, execute candidates or change installed Ollama.')
    probe=data.get('api_probe')
    if probe:p(f"<b>Actual API smoke:</b> {probe['response_text']}; verified layer trace: {probe['streaming_verified']}; owned worker stopped: {probe['worker_exited']}. An earlier attempt failed closed because default logging omitted the expected layer count. Streaming profiles now request verbosity 5; both receipts are retained.")
    h('What remains untested')
    p('Real 8 GiB machines, networked disk-backed RPC allocation, long repository patch workflows, other architectures and security isolation. The native RPC heap path is unchanged by this single-process policy. More RAM or a different model can change the tradeoff; a smaller model may still be preferable for easy tasks.')
    p('Guide and API example: <link href="https://github.com/bbartling/local-worker-bench/blob/main/docs/sequential-layer-streaming.md" color="#087F8C">docs/sequential-layer-streaming.md</link>. Measured evidence: <link href="https://github.com/bbartling/local-worker-bench/blob/main/docs/benchmarks/data/2026-11-23-streaming-coding.json" color="#087F8C">streaming-coding.json</link>.','SmallX')

    page(24,'Hosted supervisor, local worker','Keep Codex or Claude as planner and reviewer. Delegate bounded drafting through a shell/API helper.')
    story.append(SequenceDiagram(['Hosted supervisor','Local worker API','Approved checks'],[
        (0,1,'Small task + excerpts + criteria','run'),
        (1,0,'Candidate + timing/resource receipt','run'),
        (0,2,'After source review: run fixed tests','run'),
        (2,0,'Actual exit status / failing cases','run'),
        (0,1,'One targeted corrective critique','run'),
        (1,0,'Revised candidate, no tool execution','run'),
        (0,2,'Review and rerun approved checks','run'),
        (2,0,'Accept / escalate / checkpoint','run')]))
    p('The local model returns source/diff data, not authority to execute commands or merge changes. The supervisor inspects each candidate, then uses independent deterministic checks. Small context packets keep the local window bounded; the hosted model retains repository-level planning. Cloud calls happen at review checkpoints, not at every slow local token.')
    h('Ollama integrations are a different option')
    p('Ollama documents direct Codex CLI and Claude Code launches. Those connect the agent to an Ollama model as its own engine; our hybrid keeps the hosted engine and calls a local helper selectively. Our /api/chat subset has no tools/streaming and is not a tested Responses/Messages agent-provider replacement. Our patched native backend is not automatically installed into stock Ollama.')
    note('Our measured local context is 2048 tokens. Ollama integration guides recommend much larger coding-agent context windows. A model supporting long context does not prove this low-memory configuration can afford it. The current bounded helper route is the appropriate tested interface.')
    p('Primary references: <link href="https://docs.ollama.com/integrations/codex" color="#087F8C">Ollama + Codex CLI</link>; <link href="https://docs.ollama.com/integrations/claude-code" color="#087F8C">Ollama + Claude Code</link>; <link href="https://developers.openai.com/codex/skills" color="#087F8C">Codex skills</link>; <link href="https://code.claude.com/docs/en/skills" color="#087F8C">Claude skills</link>.','SmallX')

    page(25,'Overnight work and honest savings','Several days of useful work means resumable bounded jobs, not one endless HTTP call or repair loop.')
    table(['Persist outside model context','Why it matters'],[
        ('Job/attempt ID + source revision','Reject stale patches if the repository changed while a slow draft was running.'),
        ('Input/candidate hashes + model/backend','Reproduce what the helper saw and which actual source was graded.'),
        ('Allowed files + approved test commands','The local draft does not choose unrestricted shell actions or edit main directly.'),
        ('Runtime/attempt/context/output budgets','A long campaign still has finite steps, cancellation and resource limits.'),
        ('Critique + checks + next action','On quota loss or restart, stop at needs-review rather than silently accepting or replaying work.')],[190,290])
    p('A deterministic dispatcher should own the durable queue, wait without burning model tokens, and wake the hosted reviewer on a candidate or failure. One integrator owns repository changes. Durable leases, reboot recovery and a job-status API are still proposed; the current client saves bounded requests and receipts. This experiment does not create an unattended schedule.')
    repair=data.get('supervised_repair')
    if repair:
        grade=repair['grade']
        p(f"<b>Actual supervised retry:</b> the 80B motor draft first scored 47/49. The supervisor identified the mixed False/None bug, requested only a replacement decision block, inspected it, applied it to a pinned disposable candidate and reran checks: {grade['passed']}/{grade['total']}. First-pass and repair scores remain separate.")
    h('Measure cost per accepted patch')
    p('Compare an all-cloud baseline with hosted planning + critique + retries + integration in the hybrid workflow, at the same acceptance bar. Record provider-reported usage where available, local latency/resources, acceptance rate and review effort. Subscription quotas and API invoices differ; cloud savings were not measured in this lab. Weak local drafts can cost more to review.')
    note('“Always critiquing” means every proposed change gets review. It does not require a cloud model to watch continuously. Local generation avoids hosted drafting tokens, but review still uses hosted context and receives whatever approved code/diff is sent. Keep secrets out of both paths.')
    p('Detailed design and copyable instructions: <link href="https://github.com/bbartling/local-worker-bench/blob/main/docs/cloud-supervisor-local-worker.md" color="#087F8C">docs/cloud-supervisor-local-worker.md</link>.','SmallX')
