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
  #text(size: 8pt, fill: luma(70))[24 November 2026 · Suite‑3 matrix in progress]
]

#v(0.3em)
#block(width: 100%, inset: 7pt, stroke: 0.7pt + luma(40), fill: luma(247))[
  #text(weight: "bold", size: 8.8pt)[How to read this.]
  #text(size: 8.8pt)[
    High-level methods now; *winner and trade-offs in the conclusion once Suite‑3 finishes*.
    Live cells below are wall-clock only until graded. No format is crowned yet.
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
  caption: [Efficiency sketch: disk size vs wall minutes. Live Suite‑3 pagination drafts are ungraded; dashed line = 120 min deadline.],
)

*Live Wave A (ungraded drafts):* Coder-Next Q4 pagination ~12.6 min; Coder-Next FP16 ~52 min; Qwen3.8 standard Q4 in flight. Wave B waits on remaining FP16/BF16 downloads (hour polls).

= Conclusion — winner rules (fill when Suite‑3 completes)

If the matrix finishes in time, the conclusion must answer four questions in plain language:

1. *Did it work?* At least one accepted Suite‑3 project patch under enterprise review, or an honest “not yet.”
2. *Who won quality?* Most *accepted tasks* (first pass, then after one repair). Ties: fewer critical refusals/timeouts.
3. *Q4 vs FP16 vs BF16?* Same-family pairs only. Q4 = quantized/smaller; FP16/BF16 = fuller 16-bit files (BF16 ≠ FP16). Report whether 16-bit bought any accepted-task gain worth the extra hours of paging.
4. *Best trade-off?* The efficient winner minimizes wall time and disk size among models that still *accept*. A fast refusal is not a win. A huge FP16 that barely beats Q4 on quality but costs 4× time is not “best value.”

*Provisional (not a crown):* smaller Q4 files draft faster in early and live wall clocks; 16-bit files are slower under paging; easy motors saturated; hard patches remain the real test for Open-FDD-style biweekly cycles.
*When graded:* replace this paragraph with the named winner, a one-row trade-off table (accepts / minutes / GB), and an updated efficiency chart.

Until then: enterprise orchestration + OS-paged local drafts remain a credible way to spend nights between Open-FDD releases—if Suite‑3 accepts prove it.

#v(0.4em)
#text(size: 8.2pt, weight: "bold")[References]
#set text(size: 7.7pt)
Wikipedia: “Memory paging”; “Virtual memory”; “Atlas (computer)” (accessed 2026-11-24). \
T. Kilburn, R. B. Payne, D. J. Howarth, “The Atlas Supervisor” (1962). \
Project: `docs/guide.md`, `HANDOFF.md`, `local_worker_bench/paging.py`.
