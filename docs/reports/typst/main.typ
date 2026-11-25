// ≤6 page methods + results-ready conclusion
// typst compile docs/reports/typst/main.typ docs/reports/os-paging-research.pdf

#set document(
  title: "Optimizing Local Coding on Ordinary CPUs with OS-Paged Models",
  author: "local-worker-bench",
  date: datetime(year: 2026, month: 11, day: 24),
)
#set page(paper: "us-letter", margin: (x: 0.72in, y: 0.68in), numbering: "1")
#set text(font: "New Computer Modern", size: 10pt)
#set par(justify: true, leading: 0.64em)
#set heading(numbering: "1.")
#show heading.where(level: 1): it => { set text(size: 11.5pt); v(0.48em); it; v(0.2em) }
#show heading.where(level: 2): it => { set text(size: 10.5pt); v(0.32em); it; v(0.1em) }
#show figure.caption: set text(size: 8.2pt)
#set table(stroke: 0.4pt + luma(160), inset: 5pt)

#align(center)[
  #text(size: 13.2pt, weight: "bold")[
    Optimizing Local Coding on Ordinary CPUs:\
    OS Paging for Long Patch Cycles
  ]
  #v(0.25em)
  #text(size: 9.2pt)[Enterprise supervision · Open-FDD as a typical biweekly engineering vehicle]
  #v(0.1em)
  #text(size: 8pt, fill: luma(70))[25 November 2026 · Suite‑3 graded · winner Qwen3.8 standard Q4]
]

#v(0.3em)
#block(width: 100%, inset: 7pt, stroke: 0.7pt + luma(40), fill: luma(247))[
  #text(weight: "bold", size: 8.8pt)[How to read this.]
  #text(size: 8.8pt)[
    Methods first; conclusion names the *only Suite‑3 accept so far* and the trade-offs.
    Twelve cells never produced a complete draft (desktop RAM / commit guards). Case fractions alone never crown a format.
  ]
]

#v(0.25em)
#text(weight: "bold")[Abstract.]
Local coding models are good enough that the real question is how to run a *large* one on a normal desktop *without a GPU* for slow, real patch cycles—the kind that fit Open-FDD’s biweekly release rhythm.
An enterprise (hosted) model plans and critiques; a local model drafts overnight on CPU.
The bottleneck is model size versus RAM.
We use OS *memory paging* (4 KiB pages) over memory-mapped GGUF files in llama.cpp so the whole checkpoint need not sit in RAM.
We compare Q4 (compressed), FP16, and BF16 artifacts for Qwen3.8 and Coder-Next, and we will declare a winner only from *accepted patches* versus wall time and file size.

= Local coding on ordinary hardware

Hosted models are strong planners; local models are strong overnight drafters.
Pattern: enterprise orchestrates → local CPU drafts → review every file → independent tests → accept or one repair → never auto-merge.
Open Fault Detection and Diagnostics (*Open-FDD*) is ordinary Python engineering (analytics, paging helpers, units, tests)—not a full-stack web app—so it is a fair stand-in.
Why not use long, slow local cycles between *biweekly Open-FDD releases*? A patch that takes a night still fits a two-week train if the enterprise model only wakes to critique.

#figure(
  image("figures/fig-supervised-paging.jpg", width: 88%),
  caption: [Enterprise model orchestrates; local llama.cpp worker pages GGUF weights from SSD into a bounded RAM working set.],
)

== Why log tokens per Open-FDD patch cycle?

Yes—this is the right paper evidence for “does local routing help?”
Open-FDD already ships on a roughly *biweekly* cadence; each release is a long supervised patch cycle.
A Claude-only floor for *5.0.21* (17–20 Nov 2026, incomplete early merges) already shows the shape of the cost:

#figure(
  table(
    columns: (1.6fr, 1.2fr, 1.6fr),
    align: (left, right, left),
    [*Meter (Claude only)*], [*Amount*], [*Read*],
    [Model replies], [2 803], [Steps in the window],
    [Cache reads], [~1.39 B], [~99.5% of raw tokens—context re-read],
    [Cache writes], [~4.6 M], [Session growth],
    [Output], [~1.9 M], [Code, comments, PR text],
    [Uncached input], [~6 k], [Tiny vs cache],
    [Weighted cost-equivalent], [~$158$ M], [Dominated by cache reads (~139 M weighted)],
  ),
  caption: [Open-FDD 5.0.21 Claude floor (`token_ledger.py peek`). Not Codex/Grok. Pre–17 Nov work missing—treat as a lower bound.],
)

The lesson for 5.0.22+: keep context small (fresh sessions, subagents, less CI re-check in one thread).
For *5.0.23*, when drafts can be *routed to this local worker*, log both sides of the same cycle: enterprise ledger (plan/critique) *and* local `prompt_eval_count` / `eval_count` from API receipts (already recorded per draft).
Paper claim to test—not assert yet: overnight local paging trades wall time for fewer enterprise cache re-reads on mechanical edits, while Claude still owns acceptance.

= Paging: models larger than RAM

Coding checkpoints here are ~17–160 GB; this PC has 32 GiB RAM.
*Memory paging* moves fixed-size pages between disk and RAM (Wikipedia: Memory paging / Virtual memory).
On Atlas (1962) this was a “one-level store” (Kilburn et al.).
Today: map GGUF on SSD; Windows pages 4 KiB units; we budget ~⅔ of *free* RAM and ~⅔ of CPU threads (5 here), with a *120 min* request deadline.
Paging ≠ API pagination.

#figure(
  image("figures/chart-model-vs-ram.png", width: 93%),
  caption: [Model file size vs 32 GiB RAM and ~10 GiB working-set budget. Larger files must page.],
)

#figure(
  table(
    columns: (1.35fr, 0.85fr, 1.0fr, 1.3fr),
    [*Artifact*], [*Size*], [*÷ 4 KiB*], [*Note*],
    [OS page], [4 KiB], [1], [Movement grain],
    [Working set (auto)], [~$10$ GiB], [~$2.6$M], [~⅔ of free RAM],
    [Qwen3.8 Q4], [~16.8 GB], [~$4.1$M], [Smallest Qwen cell],
    [Qwen3.8 FP16/BF16], [~54.7 GB], [~$13$M], [16-bit pair],
    [Coder-Next Q4], [~48.4 GB], [~$12$M], [Compressed 80B-class],
    [Coder-Next FP16/BF16], [~159 GB], [~$39$M], [Heaviest paging],
  ),
  caption: [Size vs OS page. FP16 and BF16 are different 16-bit layouts; Q4 is quantized/compressed.],
)

*Glossary (short):* GGUF = on-disk model box; tensor = number grid; llama.cpp = engine we run; Ollama = separate app we do not modify; PyTorch = only in tiny historical demos, not this coding path; Q4 ≈ compressed weights; FP16/BF16 ≈ fuller 16-bit storage (“bfloat” is BF16, not a typo for FP16).

= What we measure

Six cells: Qwen3.8 and Coder-Next × Q4, FP16, BF16. Suite‑3 synthetic Open-FDD-inspired tasks. Primary score = *accepted tasks* after review (not raw case fractions). Secondary = wall time and size (efficiency).

#figure(
  image("figures/chart-pilot-results.png", width: 92%),
  caption: [Early pilots only: easy motors can pass; one BF16 motor timed out; first hard pagination round accepted 0/3.],
)

#figure(
  image("figures/chart-efficiency-size-time.png", width: 94%),
  caption: [Efficiency sketch: disk size vs wall minutes. Dashed line = 120 min deadline. Winner kept on disk: Qwen3.8 standard Q4.],
)

*Graded Suite‑3 six-format matrix (run2):* 18 cells. Six complete drafts reviewed + hash-gated; twelve stopped incomplete (HTTP 503 free-RAM or commit-reserve guards—not format crowns).

#figure(
  table(
    columns: (1.5fr, 1.1fr, 0.9fr, 1.4fr),
    align: (left, left, right, left),
    [*Cell (task · model)*], [*Suite‑3*], [*Min*], [*Disposition*],
    [telemetry · Qwen3.8 Q4], [28/28], [46], [*accept*],
    [telemetry · Coder FP16], [24/28], [61], [needs\_supervisor],
    [telemetry · Coder Q4], [23/28], [11], [needs\_supervisor],
    [pagination · Coder FP16], [25/33], [52], [needs\_supervisor],
    [pagination · Qwen3.8 Q4], [25/33], [73], [needs\_supervisor],
    [pagination · Coder Q4], [17/33], [13], [needs\_supervisor],
    [export · all four Wave A], [—], [—], [incomplete / 503],
    [Wave B · FP16/BF16 ×3], [—], [—], [incomplete / commit],
  ),
  caption: [Suite‑3 grades after source review. Accept requires full task score + matching review hash. Incomplete cells are resource stops, not “BF16 failed the suite.”],
)

= Conclusion — winner and trade-offs

1. *Did it work?* Yes, narrowly: *one* Suite‑3 accept—`telemetry` drafted by *Qwen3.8 standard Q4* (~16.8 GB, ~46 min, 28/28 cases).
2. *Who won quality?* On accepted tasks: Qwen3.8 Q4 only. Near-misses (25/33 pagination, 24/28 telemetry on Coder FP16) are not accepts. No export or Wave‑B draft completed.
3. *Q4 vs FP16 vs BF16?* Same-family evidence is incomplete. Q4 produced the sole accept and the fastest complete drafts. FP16 completed some drafts but bought *no* extra accept. BF16 cells hit commit/RAM guards before a gradeable bundle—do not read that as “BF16 is worse at coding.”
4. *Best trade-off?* *Efficient winner for this pilot:* Qwen3.8 standard Q4—accepted telemetry, smallest disk among the six artifacts, and mid-range wall time. Coder FP16 is a slower near-miss, not a quality crown. Heavy 16-bit files remain useful *only if* later retries finish under a quieter desktop commit budget.

For Open-FDD biweekly cycles: enterprise orchestration + OS-paged Q4 overnight drafts are already a credible overnight lane for *bounded* helpers; hard pagination/export still need one supervisor repair or a quieter retry wave—not a format swap alone.
Post-matrix quiet retries: Qwen Q4 export/pagination often *timed out mid-JSON* under load; Coder-Next Q4 finished an export draft in ~8 min (25/28) and one targeted repair reached 27/28 (still not accept—int-subclass check). A supervisor rewrite of the Qwen Q4 pagination near-miss reaches 33/33 and proves Suite‑3 is solvable—*supervisor rewrites are not local-model accepts*.

#v(0.4em)
#text(size: 8.2pt, weight: "bold")[References]
#set text(size: 7.7pt)
Wikipedia: “Memory paging”; “Virtual memory”; “Atlas (computer)” (accessed 2026-11-24). \
T. Kilburn, R. B. Payne, D. J. Howarth, “The Atlas Supervisor” (1962). \
Project: `docs/guide.md`, `HANDOFF.md`, `local_worker_bench/paging.py`.
