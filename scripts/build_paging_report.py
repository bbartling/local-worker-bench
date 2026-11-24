"""Build the current eight-page single-machine guide. No inference or downloads."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,Flowable,Preformatted

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reports/os-paging-guide.pdf'
NAVY=colors.HexColor('#132C42');TEAL=colors.HexColor('#087F8C');LIGHT=colors.HexColor('#EDF5F7')
styles=getSampleStyleSheet()
for name,size,leading,font,color in [('TitleP',26,30,'Helvetica-Bold',NAVY),('DeckP',12,17,'Helvetica',NAVY),
        ('BodyP',10,14,'Helvetica',colors.black),('SmallP',8,11,'Helvetica',NAVY),('HeadP',14,18,'Helvetica-Bold',TEAL),
        ('CodeP',8,11,'Courier',NAVY)]:
    styles.add(ParagraphStyle(name=name,fontName=font,fontSize=size,leading=leading,textColor=color,spaceAfter=10))
story=[]
def p(text,style='BodyP'):story.append(Paragraph(text,styles[style]))
def h(text):p(text,'HeadP')
def page(n,title,deck):
    if story:story.append(PageBreak())
    p('LOCAL WORKER BENCH / '+str(n).zfill(2),'SmallP');p(title,'TitleP');p(deck,'DeckP')
def table(headers,rows,widths):
    data=[[Paragraph(escape(str(v)),styles['SmallP']) for v in row] for row in [headers,*rows]]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#ccdce2')),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([t,Spacer(1,12)])
def note(text):
    t=Table([[Paragraph(text,styles['BodyP'])]],colWidths=[480]);t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.6,TEAL),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,12)])
def code(text):story.append(Preformatted(text,styles['CodeP']))


class Flow(Flowable):
    def __init__(self,labels,subtitles,loop=False):super().__init__();self.width=480;self.height=125;self.labels=labels;self.subtitles=subtitles;self.loop=loop
    def draw(self):
        c=self.canv
        for i,(label,sub) in enumerate(zip(self.labels,self.subtitles)):
            x=i*165;c.setFillColor(LIGHT);c.setStrokeColor(TEAL);c.roundRect(x,45,150,65,6,fill=1)
            c.setFillColor(NAVY);c.setFont('Helvetica-Bold',10);c.drawCentredString(x+75,85,label)
            c.setFont('Helvetica',8);c.drawCentredString(x+75,65,sub)
            if i<2:
                c.setStrokeColor(TEAL);c.line(x+151,78,x+164,78);c.line(x+164,78,x+160,81);c.line(x+164,78,x+160,75)
        if self.loop:
            c.setStrokeColor(TEAL);c.lines([(405,45,405,20),(405,20,75,20),(75,20,75,43),(75,43,72,39),(75,43,78,39)])
            c.setFillColor(TEAL);c.setFont('Helvetica',8);c.drawCentredString(240,6,'Repeat only within explicit task, runtime and review budgets')


class Weights(Flowable):
    def __init__(self):super().__init__();self.width=480;self.height=145
    def draw(self):
        c=self.canv
        for i in range(6):
            c.setFillColor(TEAL if i%2 else NAVY);c.roundRect(10+i*27,35,22,80,3,fill=1,stroke=0)
        c.setFillColor(NAVY);c.setFont('Helvetica-Bold',10);c.drawString(10,125,'MODEL ON SSD')
        c.setFont('Helvetica',8);c.drawString(10,17,'Layers contain learned numerical arrays')
        c.setStrokeColor(TEAL);c.line(200,75,265,75);c.line(265,75,260,79);c.line(265,75,260,71)
        c.setFillColor(LIGHT);c.roundRect(280,35,190,80,6,fill=1,stroke=0)
        c.setFillColor(TEAL)
        for i in range(3):c.roundRect(290+i*30,67,24,30,3,fill=1,stroke=0)
        c.setFillColor(NAVY);c.setFont('Helvetica-Bold',10);c.drawString(280,125,'SMALL RAM WORKBENCH')
        c.setFont('Helvetica',8);c.drawString(290,49,'Needed pages + live inference state')


page(1,'Big model. Small workbench.','One computer, CPU inference and operating-system paging. Prepared for Ben, 24 November 2026.')
story.append(Weights())
h('What is a model?')
p('A model is a numerical program: learned weight arrays plus an architecture that tells the engine how to compute with them. A tokenizer turns text into token IDs. The CPU computes through layers, retains live state and predicts successive output tokens.')
p('The SSD stores the complete checkpoint. RAM holds the pages and runtime state needed now. Qwen3-Coder-Next has 80B total parameters but selected experts do work per token. Storage size, active computation and resident memory are different quantities.')
note('<b>Measured:</b> real 80B Q4 coding on this 32 GB i7-9700 Windows PC. The checkpoint is 48.41 decimal GB / 45.09 GiB. A bigger model can run without every weight being resident together, but its draft can still be wrong.')
h('What this tool does')
p('A local API controls a native llama.cpp worker, memory budgets and receipts. The hosted enterprise model remains planner, reviewer and final decision maker. This guide focuses only on single-machine OS paging; earlier cluster research is archived separately.')
p('Repository: github.com/bbartling/local-worker-bench','SmallP')

page(2,'Paging, not fixed slices','The operating system chooses which mapped weight pages remain in RAM.')
story.append(Flow(['GGUF ON SSD','OS PAGE CACHE','CPU + LIVE STATE'],['Complete checkpoint','Reuse or reclaim pages','Predict the next token']))
p('Think of SSD as a library and RAM as a small desk. OS-managed paging keeps useful pages on the desk and replaces them when needed. Clean file-backed pages can be reread from the model. Live activations and attention/recurrent state remain a separate memory requirement.')
table(['Question','Answer'],[
    ('How many model slices?','Zero fixed model slices are created. The OS manages small pages; our Windows host reports 4096 bytes per page.'),
    ('What are the four GGUF parts?','Storage packaging for one model, not four RAM partitions or independent mini-models.'),
    ('Why did explicit slicing lose?','Our earlier callback forced eviction after each layer. It reduced observed process residency but discarded reusable pages and added overhead.'),
    ('Is paging the Windows pagefile?','File-backed model paging and private-memory swap/pagefile backing are different mechanisms. We do not change global pagefile policy.')],[135,345])
note('Our matched patch took about 18 minutes with forced per-layer eviction and 2 minutes with Windows paging. Same 80B Q4, identical code, 25/25 checks. This is one paired observation, not a universal speed ratio.')

page(3,'A budget for this computer','Automatically detect the host; use a conservative starting point, then measure.')
code('budget = min(0.66 * currently_available_RAM,\n             available_RAM - OS_reserve,\n             24 GiB prototype ceiling)\nreserve = max(2 GiB, 10% of physical RAM)')
p('The planner detects Windows/Linux, installed and available memory, CPU count and page size. The API replans at each request admission. It does not assume 66% of total RAM is free, nor allocate 66% of the model. Another application can still change pressure during generation.')
p('New profiles also render/tokenize chat before generation, reserving the requested output plus a 64-token template margin. Oversized task packets are refused instead of silently consuming answer space. This admission check still needs model-specific validation.')
table(['Illustrative available RAM','66% before reserve/ceiling checks'],[('6 GiB','3.96 GiB'),('12 GiB','7.92 GiB'),('24 GiB','15.84 GiB')],[230,250])
p('For a 45.09 GiB checkpoint and 10 GiB residency budget, five budget-sized portions are an explanatory ratio only. They are not actual cutting lines. The OS can retain or reclaim different pages as execution proceeds.')
h('Guard more than process RSS')
p('Four threads by default, one worker and fixed context/output keep work bounded. Eight threads are explicitly authorized for the overnight comparison. The watchdog monitors available host RAM, commit, private bytes and observed working set, then stops its owned process on failure. Completed requests unload. Shared file cache still costs memory.')
note('A 66% heuristic is not a capacity guarantee. Start with a small smoke request. No application closing, global swap/pagefile tuning or automatic model escalation occurs. Hard limit behavior differs across operating systems.')

page(4,'API: a familiar local request','The request stays small. Memory policy belongs to the registered server profile.')
story.append(Flow(['HOSTED AGENT','LOCAL API :11438','LLAMA.CPP CPU'],['Bounded task packet','Budgets + receipts','Mapped GGUF weights']))
code('POST /api/chat\n{"model":"qwen3-coder-next:q4_K_M",\n "messages":[{"role":"user", "content":"Small task..."}],\n "stream":false, "think":false, "format":"json",\n "options":{"num_thread":4,"num_ctx":2048,\n            "num_predict":512}}')
p('GET /health, /api/version, /api/tags and /api/ps provide status. The reply includes timing and a resource-receipt ID. The facade owns one native process per request and stops it afterward. No downloads, generated execution or edits happen merely because the API starts.')
h('Can Ollama still be underneath?')
p('Stock Ollama supports GGUF imports, but importing a model does not install our process-budget/watchdog policy. Our tested low-residency path uses llama.cpp behind an Ollama-shaped API subset. We are not writing a new inference engine. Existing helper clients can use the subset, but it is not complete Ollama or a direct agent-provider replacement.')
note('Current subset: text chat, registered models, no streaming/tools/images. Keep the hosted agent in charge and invoke this helper explicitly. Stock Ollama low-memory parity remains a separate version-specific experiment.')
p('Setup and commands: docs/guide.md. Official GGUF import reference: github.com/ollama/ollama/blob/main/docs/import.mdx','SmallP')

page(5,'Delegate small. Review every change.','Slow overnight drafting is useful only when acceptance and review effort justify it.')
story.append(Flow(['HOSTED SUPERVISOR','LOCAL DRAFT','INDEPENDENT CHECKS'],['Scope + pinned source','Returns data only','After source inspection'],loop=True))
table(['Task packet','What the supervisor supplies'],[
    ('One bounded change','Exact function/block, signature, relevant excerpt and dependencies.'),
    ('Pinned scope','Source revision, allowed files, explicit non-goals.'),
    ('Acceptance contract','Return types, invalid inputs, edge cases and expected behavior.'),
    ('Output and budget','JSON source, short output, fixed context/time; ask for missing context.'),
    ('Review checkpoint','Inspect actual source, run independent tests, accept or one targeted repair.')],[140,340])
p('The helper never chooses shell commands, executes tests, changes providers or merges code. Its confident text is not evidence. The supervisor owns architecture, security, integration and final acceptance. Keep secrets and whole repositories out of small task packets.')
p('Example: repair is_success(status), requiring exact Python int 200-299 and rejecting bool, float and int subclasses. Specify those edges rather than saying only "fix HTTP status handling". Prompt quality and model capability both matter.')
note('Preserve first pass, local repair and supervisor rewrite separately. A supervisor rewrite is not a local-model success. Stop after one failed corrective retry rather than letting a repair loop expand indefinitely.')

page(6,'Evidence before enthusiasm','Synthetic coding results, not a claim of autonomous project engineering.')
table(['Measured condition','Quality','Request wall'],[
    ('80B Q4 / forced layer eviction','Compact patch: 25/25','1082.810 s'),
    ('80B Q4 / Windows OS paging','Same patch: 25/25','122.896 s'),
    ('80B Q4 / OS paging','Motor: 47/49','375.384 s'),
    ('80B Q4 / OS paging','Elapsed: 40/46','711.886 s'),
    ('One supervised local motor repair','49/49 after 47/49','233.143 s client')],[240,125,115])
p('These prior measurements used a 4 GiB process cap, four CPU threads and 2048 context. The broader first-pass total was 87/95; the separate compact patch is not included. Historical 30B scored 88/95 under different prompt conditions, so bigger did not automatically win.')
p('The earlier .66-budget campaign tested explicit task packets while weights downloaded. Its timings have competing I/O and are not a clean speed comparison. Structured packets also added edge-case information; improvements cannot be attributed solely to formatting.')
new=ROOT/'docs/benchmarks/data/2026-11-23-paging-packets.json'
if new.exists():
    d=json.loads(new.read_text());rows=[]
    for run in d['runs']:
        for task in run['tasks']:
            g=task.get('grade',{});score=f"{g['passed']}/{g['total']}" if g else 'Not graded'
            rows.append([task['task'],score,f"{task['seconds']:.1f} s"])
    if rows:table(['New packet task','Reviewed grade','Client wall'],rows,[240,125,115])
    repair=d.get('supervised_repair')
    if repair:p(f"<b>Fresh supervised repair:</b> motor {repair['first_pass_grade']['passed']}/49 became {repair['grade']['passed']}/49 after one local block replacement and independent checks. Broader total: 93/95 first pass, 95/95 after repair. The compact patch stays separate.")
else:p('Fresh packet grades are pending. Downloaded, running, generated and independently graded are distinct milestones; no pending model receives a quality score.')
h('What each receipt should preserve')
p('Prompt/candidate hashes, model/backend revision, startup and prompt/generation time, output tokens, truncation, memory budget, resource peaks, failed cases and worker cleanup. Test the supervisor too: scope, contract completeness, missing context, retry limits and correct acceptance.')
p('Full retained evidence and limitations: docs/evaluation.md and docs/benchmarks/data/. CI tests hand-written controls and lifecycle code, never untrusted generated candidates.','SmallP')

page(7,'Models and precision: compare fairly','The existing 80B Q4 is Qwen3-Coder-Next, not a separate third model.')
table(['Candidate','Weight storage','Current evidence'],[
    ('Coder-Next Q4_K_M / Qwen','48.41 GB','Verified; measured coding above'),
    ('Coder-Next F16 / Qwen','159.46 GB','Verified; motor 49/49'),
    ('Qwen3.8-27B UD-Q4_K_M / Unsloth','16.56 GB','Verified; motor 49/49'),
    ('Qwen3.8 standard Q4 / prithivMLmods','16.81 GB','Downloading; not graded'),
    ('Qwen3.8 FP16 / prithivMLmods','54.66 GB','Downloading; not graded')],[235,100,145])
p('Q4 uses compressed block quantization; FP16 and BF16 are distinct 16-bit floating formats. Cached BF16 is not our requested FP16 control. The new Qwen3.8 standard-Q4/FP16 pair is pinned to one publisher revision; UD Q4 remains separate. More precision can increase paging without improving accepted patches. Expanding Q4 to 16-bit cannot recover lost precision.')
h('Passing a function is not passing a project')
p('The motor task passed 49/49 first try for Qwen3.8 Q4 in 33 minutes and Coder-Next F16 in 42 minutes. BF16 timed out at 90 minutes. The harder pagination patch then produced no accepted first patch:')
table(['Four-thread pagination','Result','Request wall'],[
    ('Qwen3.8 Q4','Timeout; ungraded','90.0 min'),
    ('Coder-Next Q4','Asked for examples; no patch','5.4 min'),
    ('Coder-Next F16','20/25 checks; rejected','81.9 min')],[195,200,85])
p('These are fixed synthetic projects inspired by Open-FDD, not changes to that application. Frozen checks cover offset/token paging, telemetry gaps and a two-file SI export. Sources are inspected before execution. Preserve missing-context replies, timeouts and failures; do not rank by completion alone.')
note('No model is universally compatible. Architecture, tokenizer, chat template, quantization, workspace and live state must be supported. Dense models may reread far more weights per token than selected-expert MoE. This is CPU text-only work, not a guarantee for GPU or multimodal models.')
p('Sources on Hugging Face: Qwen/Qwen3-Coder-Next-GGUF; Qwen/Qwen3.8-27B; unsloth/Qwen3.8-27B-GGUF; prithivMLmods/Qwen3.8-27B-GGUF. Exact revisions, sizes and hashes: examples/paging/*.download.json. Download status is not success.','SmallP')

page(8,'Portable idea, measured rollout','Windows measured. Linux qualification and automatic hosted review remain future work.')
table(['Platform / component','What exists and what needs validation'],[
    ('Windows native','Measured CPU mmap paging. Automatic admission planner, working-set cap, watchdog and owned-worker cleanup.'),
    ('Linux','mmap/page cache offers the same basic idea. Planner detects Linux; hard cgroup enforcement is not wired in. Explicit monitored-only mode is not a memory-isolation result.'),
    ('WSL','Adds a VM and host/guest accounting. This PC only has Docker internal WSL. A dedicated test distro is a later phase; no global WSL settings changed.'),
    ('Durable work','SQLite records queued, drafting and needs-review/failed. A claimed job is never automatically replayed; acceptance checks candidate hash and source revision.')],[125,355])
p('Linux cgroups account for charged cache and anonymous memory differently from a Windows working-set cap. Linux needs separate constrained tests. File-backed paging is distinct from swap; WSL is not assumed faster.')
h('Several days means checkpoints, not an endless call')
p('Each request has a finite timeout and stops for review. Save source revision, packet, candidate, tests, model/backend and next action. A deterministic dispatcher can wait without cloud polling. Hosted-session wakeup, leases, reboot recovery and automatic review handoff are not implemented. Never auto-merge drafts.')
p('The explicit dispatcher preserves the reference round, runs a matched thread check, then launches three models on three patch tasks one at a time. The revised profile uses eight threads, 4096 context, up to 2048 output tokens, 120 minutes per request and a 24-hour campaign ceiling. All models get the same worked examples and unchanged tests. A STOP file cancels its stage; drafts are never auto-executed or accepted.')
p('The matched Qwen3.8 Q4 motor check passed 49/49 at both thread counts: 33.0 minutes with four, 32.5 with eight. That is only 1.35% lower wall time in one historical pair. Cache, available RAM and actual residency budgets differed. Eight cores do not imply twice the inference speed. Native partial text is saved continuously; incomplete prefixes remain ungraded.')
p('At low observable quota, commit a checkpoint. A saved file cannot renew usage or keep a hosted agent alive. Current jobs: docs/checkpoint.md.')
note('Measure hosted cost per accepted patch, including planning, critique and retries. Cloud savings are a hypothesis, not a measured result here. Slow CPU work is acceptable when its accepted output is worthwhile; persistent wrong output is not progress.')
p('Primary Linux reference: docs.kernel.org/admin-guide/cgroup-v2.html. Active notes: docs/guide.md, docs/agent-guide.md and docs/evaluation.md. Historical cluster material is research context only.','SmallP')


def footer(canvas,doc):
    canvas.setStrokeColor(TEAL);canvas.line(54,42,558,42);canvas.setFillColor(NAVY);canvas.setFont('Helvetica',8)
    canvas.drawString(54,29,'LOCAL WORKER BENCH | OS PAGING | 24 NOV 2026');canvas.drawRightString(558,29,str(doc.page))


if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(OUT),pagesize=(612,792),leftMargin=54,rightMargin=54,topMargin=45,bottomMargin=57,
        title='Local Worker Bench: OS Paging',author='Local Worker Bench').build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT)
