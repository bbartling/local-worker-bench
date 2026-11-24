// Local Worker Bench — research note (human-readable, ≤6 pages)
// Compile: typst compile docs/reports/typst/main.typ docs/reports/os-paging-research.pdf
// STATUS: methods / apparatus paper. The matched Q4·FP16·BF16 project-patch matrix has NOT been run yet.

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

#align(center)[
  #text(size: 14pt, weight: "bold")[
    Local Worker Bench: OS-Paged CPU Drafting for Supervised Patch Cycles
  ]
  #v(0.35em)
  #text(size: 9.5pt)[
    Methods note · What the tool is · What we have _not_ finished measuring yet
  ]
  #v(0.2em)
  #text(size: 8.5pt, fill: luma(70))[24 November 2026 · Inference paused · Downloads may continue]
]

#v(0.35em)
#block(width: 100%, inset: 8pt, stroke: 0.8pt + luma(40), fill: luma(245))[
  #text(weight: "bold")[Read this first — study status.]
  This paper explains the *idea* and the *machinery*. It is *not* a finished bake-off of Q4 vs FP16 vs BF16 on hard patches, and it is *not* a report that Open-FDD was fixed by a local model.
  #v(0.25em)
  *Not done yet:* the matched six-format project-patch matrix under Suite 3 (120 min, auto RAM/threads); any real Open-FDD repository patch; crowning a “best” local format.
  #v(0.15em)
  *Done offline:* harness, Suite 3 graders, resource defaults, downloads in progress, early *pilot* runs on easier packets (kept below as background only).
]

#v(0.35em)
#text(weight: "bold")[Abstract.]
Local Worker Bench is a hobby apparatus: can an ordinary CPU desktop draft code overnight while an enterprise (hosted) model plans, critiques, and accepts? Model files sit on disk as GGUF packages; a pinned llama.cpp worker maps them; Windows pages pieces into RAM. We *plan* to compare three storage styles—compressed *Q4*, fuller *FP16*, and sibling *BF16*—once downloads finish and the user resumes inference. This note teaches those ideas in plain language. Early pilots exist; the decisive comparison does *not* yet.

= Motivation

Open-FDD is a real Python engineering project. Patch cycles there are already slow. The bet is that a *local* coding model can draft, while Claude/Codex/Grok-class models stay supervisor: they own the contract, read every generated file, run independent checks, and never treat a local draft as authority. Slow generation (hours) is acceptable *if* accepted quality holds. That quality claim for repository-scale work is *unproven*; this bench is how we intend to measure it later.

= What the software is (and is not)

== Custom code in this repository

- `paging.py` — looks at free RAM and CPUs; budgets about two-thirds of *currently free* RAM (with a safety reserve). Creates *zero* fixed model slices.
- `offload_api.py` — small web API (Ollama-_shaped_, not Ollama). Starts/stops one owned worker per request; records receipts; refuses tools/images/streaming.
- Pinned llama.cpp build — maps GGUF files so Windows can page weights from SSD.
- `project_bench.py` — synthetic Open-FDD-_inspired_ tasks (pager, telemetry, SI export) with contracts and offline graders (Suite 3 after a review found Suite 1 too easy to fake).
- Campaign scripts — serial drafts only; no auto-merge; human/AI review before any grade counts as accept.

We are *not* writing a new neural engine, *not* training models, and *not* modifying installed Ollama.

== Ollama, GGUF, llama.cpp, PyTorch, tensors

#figure(
  table(
    columns: (1.15fr, 2.85fr),
    align: (left, left),
    [*Term*], [*Plain meaning*],
    [GGUF], [The “shipping box” for a model on disk.],
    [llama.cpp], [The engine that opens that box on a normal CPU.],
    [Ollama], [A popular local-model app. We leave it alone; our API only *looks* a bit like it.],
    [PyTorch], [A research toolkit. Not used for the big coding path here.],
    [Tensor], [A grid of numbers. “Weights” are tensors. Paging moves chunks between disk and RAM.],
  ),
  caption: [Vocabulary for non-specialists.],
)

== Q4, FP16, and BF16 — plain language

A model is mostly a huge pile of numbers. Store them densely or loosely—like a tiny JPEG vs a huge raw photo. Labels here are *Q4*, *FP16*, and *BF16* (not “FP15” / “BP16”).

#figure(
  table(
    columns: (0.7fr, 1.1fr, 2.2fr),
    align: (left, left, left),
    [*Label*], [*Everyday analogy*], [*What we will measure later*],
    [Q4], [Compressed cookbook], [Smaller file (tens of GB). May be “good enough” for drafts—or not. Unknown until Suite 3 matrix runs.],
    [FP16], [High-quality 16-bit photo], [Much larger (~55 or ~159 GB). More precise storage; heavy paging on a 32 GB PC.],
    [BF16], [Different 16-bit film stock], [Also ~16-bit, different layout than FP16. Own artifact; not automatically better.],
  ),
  caption: [Formats we *intend* to compare. No winner has been crowned.],
)

*Open question (not answered yet):* on this office PC, does Q4 still get *accepted* after review, or does a 16-bit file earn enough quality to justify hours of paging? We must not claim “BF16 beats Q4” from early, unmatched pilots.

= OS memory paging (the core idea)

On a 32 GiB PC, a ~159 GB file cannot sit fully in RAM. The engine maps the file; Windows brings pages in when touched and can drop cold ones. Guards stop the worker if the desktop is endangered. We do *not* change the global pagefile or close your apps.

One early paired trial found OS paging much faster than an older “kick layers out by hand” approach on a tiny patch. That is why the active tool uses OS paging. It does *not* mean the hard Open-FDD problem is solved.

== How much of the computer? (plain language)

Think of a shared kitchen while you still browse and work.

*RAM.* Allow about *two-thirds of the RAM that is free right now*, after a reserve for Windows. Example: ~15 GiB free → ~10 GiB working set—not “66% of the model.” The rest pages from disk.

*Threads.* About *two-thirds of CPU lanes* (five on this eight-lane PC). More threads barely helped in one early motor trial (~1%); disk paging dominates.

*Time.* Intended project-patch deadline: *120 minutes* per request. Timeout means “no complete patch,” not a fake failing score. Overnight queues are fine once inference resumes.

= Testing design (apparatus, not finished scoreboard)

Three synthetic tasks (not 74 projects). Models see broken code + contract; tests are hidden from the prompt but public in-repo. Accept only if: complete files, supervisor read, hashes match, all Suite 3 checks green, explicit accept. Rank by *accepted tasks*, not raw fractions.

Suite 1 was too easy to fake (wrong patches could look green). Offline Suite 3 + mutant checks address that *before* the next model matrix. No Suite 3 model grades exist yet—inference is paused.

= Early pilots only (not the format crown)

These numbers are *background*. They used older settings (often 90 min, 40% RAM, Suite 1). They are *not* the planned Q4/FP16/BF16 Suite 3 comparison.

#figure(
  table(
    columns: (1.55fr, 2.45fr),
    align: (left, left),
    [*Early pilot*], [*What it showed (limited)*],
    [OS paging vs hand eviction (tiny patch)], [Same answer; paging much faster in one pair.],
    [Easy “motor” function], [Some models scored 49/49; that packet is near ceiling—not a format winner.],
    [Harder pagination project task], [*0 accepted* among three attempts (timeout / ask for examples / incomplete checks).],
    [4 vs 8 CPU threads], [Almost no speed gain when paging-bound.],
  ),
  caption: [Pilots only. Full matrix and Open-FDD patches = future work.],
)

= Intended Open-FDD cycle (future)

Enterprise model plans → local GGUF drafts overnight → review every file → independent tests in a disposable copy → accept / one repair / supervisor takeover. Never auto-merge. *No production Open-FDD patch has been attempted.*

= What happens next

1. Finish downloads (standard Q4, FP16, Coder-Next BF16 still in progress at writing).
2. User explicitly removes the inference pause.
3. Run *Wave A* (already verified models) first; hour-sleep until Wave B downloads verify.
4. Same Suite 3, 120 min, auto RAM/threads for every cell that shares a table.
5. Refresh this paper with *those* results—or with honest failures. Until then, treat this PDF as a methods primer, not a results paper.

= Conclusion

Local Worker Bench is scaffolding for supervised local drafting under OS paging. The story for non-specialists is simple: big model files on disk, Windows shares memory, Q4 is the compressed cookbook and FP16/BF16 are fuller copies, an enterprise model stays in charge, and slow overnight drafts are allowed. *We have not yet run the comparison that would say which cookbook wins for Open-FDD-like patches.* Early pilots are encouraging on easy tasks and unsuccessful on a harder pager—nothing more.
)
