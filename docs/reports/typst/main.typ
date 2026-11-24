// Local Worker Bench — research note (human-readable, ≤6 pages)
// Compile: typst compile docs/reports/typst/main.typ docs/reports/os-paging-research.pdf

#set document(
  title: "Local Worker Bench: OS-Paged CPU Drafting for Supervised Patch Cycles",
  author: "local-worker-bench",
  date: datetime(year: 2026, month: 11, day: 24),
)
#set page(
  paper: "us-letter",
  margin: (top: 0.75in, bottom: 0.7in, left: 0.75in, right: 0.75in),
  numbering: "1",
)
#set text(font: "New Computer Modern", size: 10pt)
#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.")
#show heading.where(level: 1): it => {
  set text(size: 11.5pt)
  v(0.55em)
  it
  v(0.25em)
}
#show heading.where(level: 2): it => {
  set text(size: 10.5pt)
  v(0.4em)
  it
  v(0.15em)
}
#show figure.caption: set text(size: 8.5pt)
#set table(stroke: 0.4pt + luma(160), inset: 5pt)
#show raw.where(block: true): set text(size: 7.8pt)

#align(center)[
  #text(size: 14pt, weight: "bold")[
    Local Worker Bench: OS-Paged CPU Drafting for Supervised Patch Cycles
  ]
  #v(0.35em)
  #text(size: 9.5pt)[
    Single-machine GGUF inference under Windows paging · Hosted orchestration · Open-FDD-oriented software engineering
  ]
  #v(0.2em)
  #text(size: 8.5pt, fill: luma(70))[24 November 2026 · Inference paused for suite critique; downloads may continue]
]

#v(0.4em)
#text(weight: "bold")[Abstract.]
This note describes a hobby research tool that asks whether ordinary CPU machines can draft useful code patches overnight while an enterprise (hosted) model plans, critiques, and accepts work. Model files live on disk as GGUF “shipping boxes”; a pinned llama.cpp worker maps them; Windows pages pieces into RAM as needed. We compare three storage styles—compressed *Q4*, fuller *FP16*, and sibling *BF16*—in plain language below. The product is _not_ a second Ollama and _not_ a PyTorch training stack. Measured best results so far are strong on small synthetic functions and weak on harder project patches (zero accepted pagination repairs). Slow runs (hours to days) are acceptable by design. Open-FDD remains untouched inspiration for future disposable patch cycles.

= Motivation

Open-FDD is a real Python engineering project (analytics, NF paging, units, tests). Patch cycles there are already slow: diagnose, change a few modules, run tests, review. The bet is that a _local_ coding model on a desktop without a GPU can sit inside that loop as a drafter, while Claude/Codex/Grok-class models remain the supervisor: they own the task contract, read every generated file, run independent checks, and never treat a local draft as authority.

Local generation at ~0.2–6 s/token is fine. A patch that takes all night and survives critique is still cheaper in attention than endless hosted token burn for mechanical edits—_if_ acceptance quality holds. That quality claim is unproven for repository-scale work; this bench is the measurement apparatus.

= What the software is (and is not)

== Custom code in this repository

The active product is single-machine OS-managed paging with a hosted-supervisor workflow:

- `local_worker_bench/paging.py` — host snapshot (RAM, CPUs, page size) and an admission budget: min(0.66 × currently available RAM, available − OS reserve, 24 GiB ceiling). Reserve is max(2 GiB, 10% physical). The planner reports `ceil(weight_bytes / budget)` only as an illustration; it creates *zero* physical model slices.
- `local_worker_bench/offload_api.py` — loopback HTTP facade shaped like a small Ollama subset (`/api/chat`, tags, health, unload). Starts/stops an *owned* llama-server process per request; refuses tools/images/streaming; temperature 0; records resource receipts and optional SSE partial capture.
- `local_worker_bench/native_stream.py` + `scripts/build_paged_backend.py` — pinned llama.cpp build with a Windows bulk-prefetch-disable patch so the OS can page mapped weights instead of forcing bulk residency.
- `local_worker_bench/project_bench.py` — synthetic Open-FDD-_inspired_ tasks (pagination, telemetry duration, two-file SI export) with broken baselines, handwritten controls, contracts, and frozen offline graders.
- Campaign/publish scripts (`prepare_project_bench.py`, `run_project_bench.py`, `check_project_patch.py`, `publish_project_results.py`) — finite serial drafting, persistent claims before each call, no automatic repair/merge, hash-gated grading only after supervisor review of every returned file.
- Durable job ledgers (SQLite) stop at `needs_review`; a claimed `drafting` job is never silently replayed after a crash.

Historical cluster/LAN/PyTorch sharding demos remain under `docs/` and `examples/` as research only; they are not the active runtime. The illustrated ReportLab PDF (`os-paging-guide.pdf`) was built for agent context; *this* Typst note is the human-facing research summary.

== Ollama, GGUF, llama.cpp, PyTorch, tensors

#figure(
  table(
    columns: (1.15fr, 2.85fr),
    align: (left, left),
    [*Term*], [*Role here*],
    [GGUF], [The “shipping box” for a model on disk: numbers + instructions for how to run it, often split across a few large files.],
    [llama.cpp], [The engine that actually reads that box on a normal CPU. This project uses a pinned build of it; we are not inventing a new brain from scratch.],
    [Ollama], [A popular app people use to run local models. This PC may have it installed; *we leave it alone*. Our tool speaks a small, similar web API so helpers can talk to *our* worker instead.],
    [PyTorch], [A research/training toolkit. Tiny old demos used it. The big coding runs here do *not* load PyTorch for the 27B/80B path.],
    [Tensor], [Just a grid of numbers (like a spreadsheet the computer multiplies). Model “weights” are tensors. Paging moves chunks of those numbers between disk and RAM—it does not create separate little models.],
  ),
  caption: [Vocabulary for readers who are not ML engineers.],
)

== Q4, FP16, and BF16 — what the formats mean (plain language)

A trained model is mostly a huge pile of numbers. Those numbers can be stored more or less precisely, the way a photo can be a tiny JPEG or a giant raw file. *Same picture family, different file size and fidelity.* There is no “FP15” or “BP16” here—the three labels we compare are *Q4*, *FP16*, and *BF16*.

#figure(
  table(
    columns: (0.7fr, 1.1fr, 2.2fr),
    align: (left, left, left),
    [*Label*], [*Everyday analogy*], [*What it means for this hobby test*],
    [Q4], [A compressed photo / zip of the cookbook], [Roughly *4-bit* packed numbers (often a mix like Q4\_K\_M). Much *smaller on disk* (tens of GB instead of 100+). Usually faster to move through limited RAM. May lose a little “sharpness” versus a fuller copy—we measure whether that still drafts useful patches.],
    [FP16], [A high-quality 16-bit photo], [*Float16*: about 16 bits per weight. Much *larger* files (e.g. ~55 GB or ~159 GB here). More precise storage; on a 32 GB PC it *must* lean on disk paging, so drafts can take a long time.],
    [BF16], [Another 16-bit photo style, slightly different film], [*BFloat16*: also ~16 bits, but a different numeric layout than FP16 (think “different film stock,” not a typo). Same ballpark size as FP16. Not automatically “better”—we treat it as its own artifact, often from a different publisher.],
  ),
  caption: [Precision formats for non-specialists. Bigger files are not automatically smarter in practice.],
)

*Why compare them?* The open question is practical: on an ordinary office PC, does the smaller Q4 draft still get *accepted* after a careful review, or does a larger 16-bit file earn enough extra quality to justify hours of paging? Speed is secondary; overnight is fine. *What we must not claim yet:* that “BF16 beats Q4” in the abstract. Files can come from different publishers, with different recipes and chat templates. We rank *pinned downloads under a declared RAM/thread/time policy*, and we keep Unsloth “UD” Q4 labeled as an *extra* build—not the same as the standard Q4 control.

Mixture-of-experts models (e.g. Coder-Next) still store all expert cookbooks on disk; each token only “opens” some of them, but the computer still needs a strategy to page that large shelf.

= OS memory paging (the core idea)

On a 32 GiB Windows desktop (Intel i7-9700, eight logical CPUs, no discrete GPU for this path), an 80B FP16 file (~159 GB) cannot be fully resident. The engine memory-maps GGUF weights. When a layer’s parameters are touched, the OS faults pages from SSD into RAM and may keep hot pages. Cold pages can be reclaimed under pressure. Process working-set caps and private-byte guards stop the *owned* worker if the host is endangered; they are *not* a claim that RSS equals total cache/commit cost, and they do not change the global pagefile or close desktop apps.

Earlier research compared explicit per-layer eviction against OS paging on a compact patch: identical accepted source, OS paging ~8.8× faster wall time in one paired trial (≈123 s vs ≈1083 s). The active tool therefore uses OS paging (`layer_stream:false`), not fixed model slices and not a Pi/cluster path. Matched motor trials at four vs eight threads differed by only ~1.35% wall time with identical ASTs—evidence that, once paging-bound, adding software threads is a weak lever.

== How much of the computer should this use? (plain language)

Think of the PC as a shared kitchen while you still browse, Slack, and work.

*RAM (memory).* The model file on disk can be larger than physical RAM. We never try to shove the whole file into memory. Instead we allow the worker a *working set*: roughly *two-thirds of the RAM that is free right now*, after keeping a safety reserve for Windows and your other apps (at least 2 GiB or 10% of the machine). On this 32 GiB desktop with about 15 GiB free, that lands near *10 GiB* for the worker—not “66% of the model” and not “66% of all RAM in the box.” If free RAM changes, the next request re-plans. Older published trials often used a stricter *40%* setting; new runs default to the *66%* auto policy. Either way, the OS can still page the rest of the weights from SSD.

*CPU threads.* “Threads” are how many CPU lanes the math kernels may use at once. Auto mode picks about *two-thirds of the logical CPUs you can see*—on this eight-lane PC that is *five* threads (you can override). More threads do *not* magically make a paged 80B model twice as fast: measured four-vs-eight trials on the same motor task differed by only about 1%. Disk paging dominates.

*Time.* Patch drafts are allowed to be slow. The intended project-patch deadline is *120 minutes end-to-end* per request (including load). Hitting the clock is recorded as “no complete patch,” not as a fake score of 0/25. Overnight and multi-day queues are fine; the enterprise model can sleep between reviews.

#figure(
  table(
    columns: (1.15fr, 1.1fr, 1.75fr),
    align: (left, left, left),
    [*Knob*], [*Auto default (new)*], [*In one sentence*],
    [RAM budget], [~66% of *currently free* RAM], [Leave headroom for the desktop; page the rest from disk],
    [CPU threads], [~66% of logical CPUs (5 here)], [Use most lanes, not all; paging still sets the pace],
    [Request timeout], [120 minutes], [Slow is OK; unfinished work is not graded as wrong code],
    [Historical note], [Often 40% RAM, 4 or 8 threads, 90 min], [Keep old results labeled; do not mix with new autos],
  ),
  caption: [Resource story for non-specialists. Overrides remain available.],
)

= Testing design

== Synthetic project patches

Three tasks (not 74 projects): (1) token/offset pager, (2) fault/coverage durations, (3) `units.py` + `report.py` SI export. Models see only broken sources + contract; tests are withheld from the prompt but public in-repo (not contamination-resistant). Handwritten controls pass all cases; broken baselines fail. Acceptance requires: complete files, supervisor source review, matching hashes, *all* checks green, explicit `review.json` accept. Supervisor rewrites never count as local success. At most one targeted local repair, then take over.

An always-raising pager scores 20/25 on the first suite (negative-heavy). Independent review by SOL, Grok, and Claude further showed many plausible wrong patches scoring 25/25, 26/26, or 23/23—for example: token pages that drop filters and `pageSize`; `totalCount=True` accepted via `int()`; empty-string ids; `max_pages=1.0`; Fahrenheit rounded to whole degrees; `to_si(False)` becoming `0.0`. The scripted fake server returns the next canned page by call count, so unchecked request fields are free to be wrong. Suite hardening (version 3, mutant CI, request logs, suite hash in grades) is underway offline; *do not* reinterpret old fractions as contract proof. Rank by accepted tasks, not case fractions. Keep dispositions separate: timeout, `needs_context`, rejected, accepted, cancelled.

== What “best results” means today

#figure(
  table(
    columns: (1.6fr, 0.9fr, 1.5fr),
    align: (left, left, left),
    [*Experiment*], [*Best outcome*], [*Interpretation*],
    [Compact patch, OS paging vs eviction], [25/25 both; OS ~123 s vs ~1083 s], [Paging strategy win (one pair)],
    [Motor function, Qwen3.8 UD-Q4 / Coder-Next F16], [49/49 first pass (~33–42 min)], [Saturated easy packet; not a format crown],
    [Coder-Next Q4 motor], [47/49 then 49/49 after one repair], [Repair loop works; account separately],
    [Qwen3.8 BF16 motor], [90 min timeout; 137 B prefix], [Infeasible under that deadline/budget],
    [Project pagination (Q4 / Q4 / F16)], [*0/3 accepted*], [Timeout / needs\_context / 20/25 reject],
    [4 vs 8 threads (matched motor)], [~1.35% wall difference], [Threads ≠ lever when paging-bound],
  ),
  caption: [Honest leaderboard. No Open-FDD production patch has been attempted.],
)

Primary metric for the hobby product: *accepted patches after critique*. Secondary: wall time and resource receipts. Speed rankings with concurrent downloads or changing available RAM are confounded.

= Intended Open-FDD patch cycle

#align(center)[
  #block(width: 95%)[
    #set text(size: 8.5pt)
    *Enterprise model* (plan, contract, review, accept) \
    → bounded packet (allowed files, non-goals, deadline) \
    → *local GGUF worker* on ordinary CPU (draft overnight) \
    → hash + human/AI read of every file \
    → independent tests in disposable copy \
    → accept / one repair / supervisor takeover \
    → never auto-merge; never treat drafts as shell authority
  ]
]

Transferable pieces already exist: pinned revision, allowed paths, review-before-execute, failure retention, `needs_context`, owned-worker cleanup. Not yet transferred: real git diffs, multi-module Open-FDD builds, sandboxed execution, measured hosted-token savings. First real trial should be a disposable worktree with that repo’s own tests—not a rescore of synthetic pagination.

= Limitations and next measurements

Format columns (Q4 / FP16 / BF16) mix publishers and templates; only same-publisher pairs are precision comparisons. FP16 vs BF16 is expensive and likely low-signal. Uniform 0.40 budgets handicap models that nearly fit in RAM. Public tests can leak into training data. The checker’s AST screen and 15 s timeout are not a security sandbox.

While large GGUF downloads finish (standard Q4 / FP16 / Coder-Next BF16 still in progress at writing), offline work continues: mutation-qualified Suite 3, suite hashes in grades, coherent resource defaults, and this Typst note. Download completion must not auto-start inference. Resume only on explicit user request after suite review. A first disposable Open-FDD trial should use that repository’s own tests in a throwaway worktree, with fake NF servers only—never customer data or live credentials.

= Conclusion

Local Worker Bench is a careful apparatus for *supervised* local drafting under OS paging—not an autonomous coding agent and not a claim that quantized 80B models already fix Open-FDD. Best measured wins are OS paging over explicit eviction, and perfect scores on small motor packets. Harder project patches have not yet produced an accepted first repair. The engineering thesis remains worth overnight compute: keep enterprise models in charge; let ordinary CPU machines draft slowly; accept only what independent critique and tests can defend.
)
