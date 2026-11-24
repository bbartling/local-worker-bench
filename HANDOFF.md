# Cursor handoff - local worker research and patch benchmark

## Current instruction: Suite-3 six-format matrix RUNNING

User resumed 24 Nov 2026. Durable dispatcher:
`results/suite3-six-matrix-20261124-run2/` (`scripts/handoff_suite3_six_matrix.py`).
Wave A: coder-next-q4, coder-next-f16, qwen38-standard-q4, qwen38-bf16.
Wave B (hour-sleep until verified): qwen38-f16, coder-next-bf16.
Settings: Suite 3, 120 min, .66 RAM, auto threads (~5), 2048 tokens, prompt v2.
Write `STOP` in that folder to cancel. Do not launch a second matrix.
First attempt folder `...20261124` failed on hours>24; leave as evidence.

Repository: `C:\Users\ben\Documents\local-worker-bench`.
Remote: https://github.com/bbartling/local-worker-bench, default branch **main**.
The user wants changes committed/pushed directly to main, no branches or PRs.
`C:\Users\ben\Documents\open-fdd` was read-only inspiration; do not modify it.
The chat's earlier working directory under Documents/Codex is not this repository.

## Product and boundaries

Single-machine CPU inference with a full GGUF checkpoint on SSD and OS-managed
file-backed paging. No fixed model slices are created. Explicit per-layer eviction
was slower and is historical research; do not restore cluster defaults or the Pi.
The local Ollama-shaped API wraps a pinned llama.cpp worker. It is not Ollama itself.
The hosted supervisor owns planning, review, tests and acceptance. Drafts are data:
no generated tools, test execution, repository edits, merges or automatic acceptance.

Host: Intel i7-9700, **8 physical / 8 logical CPUs**, 32 GiB RAM, no discrete GPU.
Windows is measured. Linux/WSL inference and hard cgroup enforcement remain unqualified.
Do not close work apps or change global pagefile, firewall, providers or Ollama settings.

Native executable: `results/layer-stream-backend/build/bin/Release/llama-server.exe`.
SHA-256: `3244a4871d48be98e74870ce06ab74a6e61e9f690509cc75663cacf1abffba69`.
Upstream source: `94f3af3d09e74a0fb35f703194318d3b4037714a` plus local paging changes.
Runtime results, native binaries and weights are ignored, local files, not in GitHub.

## Model matrix and downloads still running

**Ready-first policy (after explicit inference resume):** run verified aliases
before unfinished downloads. When a later cell’s turn arrives and
`verified-manifest.json` is missing, sleep in **1-hour** poll cycles until
verification completes, STOP, or campaign deadline. Do not start a duplicate
download writer. Check live state with
`python scripts/report_model_readiness.py`.

**New project-patch defaults (do not relabel old runs):** **120-minute**
end-to-end timeout, **~66% of currently available RAM**, **~66% of visible
logical CPUs** as threads (5 on this 8-CPU PC), **2048** output tokens on both
`prepare_project_bench` and `run_project_bench`. Overrides allowed. Historical
matrices used 90 min / .40 RAM / 4 or 8 threads—keep those labeled separately.
Plain-language methods note (not a finished bake-off):
`docs/reports/os-paging-research.pdf`. After unpause: fresh output dir, Wave A
verified models first; accept only all-green Suite 3 + source review.

| Wave | Alias | Role | Gate |
| --- | --- | --- | --- |
| A (ready) | `coder-next-q4` | Qwen-published Q4 | verified |
| A (ready) | `coder-next-f16` | Qwen-published FP16 pair | verified |
| A (ready) | `qwen38-q4` | Unsloth UD-Q4 **appendix** (not standard-Q4 column) | verified |
| A (ready) | `qwen38-bf16` | BF16 feasibility only (prior motor timeout) | verified |
| B (later) | `qwen38-standard-q4` | Standard Q4 control | hour-sleep until verified |
| B (later) | `qwen38-f16` | Matched FP16 for that Q4 | hour-sleep until verified |
| B (later) | `coder-next-bf16` | BF16 side arm | hour-sleep until verified |

| Family / format | Alias | Decimal GB | State at handoff |
| --- | --- | ---: | --- |
| Qwen3.8 standard Q4_K_M | qwen38-standard-q4 | 16.81 | Downloading |
| Qwen3.8 FP16 | qwen38-f16 | 54.66 | Downloading |
| Qwen3.8 BF16 | qwen38-bf16 | 54.66 | Cached and verified |
| Coder-Next Q4_K_M | coder-next-q4 | 48.41 | Cached and verified |
| Coder-Next FP16 | coder-next-f16 | 159.46 | Cached and verified |
| Coder-Next BF16 | coder-next-bf16 | 159.46 | Downloading |
| Extra: Qwen3.8 Unsloth UD Q4 | qwen38-q4 | 16.56 | Cached; keep separate from standard Q4 |

FP16/F16 and BF16 are different formats, not a typo. Auxiliary F32 tensors may
exist; Q4_K_M is mixed quantization. Never relabel BF16 as FP16 or expand Q4 to
manufacture a precision control. Community conversion/base revisions may differ:
this practical comparison is not automatically a pure precision ablation.

The new Qwen3.8 Q4/FP16 pair is prithivMLmods revision
`3ccdd49b1030d9ce891e42e817ece300ae278562`. Coder-Next BF16 is Unsloth revision
`ce09c67b53bc8739eef83fe67b2f5d293c270632`. Coder-Next Q4/FP16 are Qwen-published.
New downloads and 16-bit controls have manifests in `examples/paging/`. Existing
Coder-Next Q4 shard hashes are in its cached verified manifest and prior public
benchmark data; do not confuse its missing example download recipe with missing weights.

Active download identities when last observed:

| Download | PID | Codex terminal session | Cache directory |
| --- | ---: | ---: | --- |
| Qwen3.8 FP16 | 5032 | 55998 | results/model-cache/qwen38-f16 |
| Qwen3.8 standard Q4 | 13208 | 75412 | results/model-cache/qwen38-standard-q4 |
| Coder-Next BF16 | 8084 | 31895 | results/model-cache/coder-next-bf16 |

PIDs may have exited by the time you read this. Inspect CommandLine and the
cache's `download-status.json` before acting; never kill a reused PID or start
duplicate writers. `verified-manifest.json` appears only after full SHA verification.
Do not delete partial files. Codex session handles might not be usable from Cursor;
the underlying Windows processes and files remain observable.

Only if a writer has exited and a download needs resuming, downloads are authorized:

```powershell
python scripts/download_gguf.py --manifest examples/paging/qwen38-f16.download.json --output results/model-cache/qwen38-f16 --max-gb 60 --workers 1
python scripts/download_gguf.py --manifest examples/paging/qwen38-standard-q4.download.json --output results/model-cache/qwen38-standard-q4 --max-gb 20 --workers 1
python scripts/download_gguf.py --manifest examples/paging/coder-next-bf16.download.json --output results/model-cache/coder-next-bf16 --max-gb 165 --workers 3
```

The existing Coder-Next Q4 cache directory is `results/model-cache/qwen3-coder-next-q4`,
despite its shorter API alias. Do not redownload it just because those names differ.
Downloaded models are not automatically loaded. Header inspection is not inference.

## Actual results, without inflated claims

| Experiment | Result |
| --- | --- |
| Prior 80B Q4 compact patch: forced eviction / OS paging | Both 25/25; 1082.810 / 122.896 seconds |
| Later Coder-Next Q4 motor packet | 47/49 first pass; 49/49 after one local repair, reported separately |
| Qwen3.8 UD Q4 / Coder-Next FP16 motor | Both 49/49 first try; 33.0 / 41.8 minutes |
| Qwen3.8 BF16 motor | 90-minute timeout; prefix ungraded |
| Matched Qwen3.8 motor, four / eight threads | Both 49/49; 1978.139 / 1951.473 seconds; identical ASTs and 311 output tokens |
| Harder pagination, Qwen3.8 UD Q4 | 90-minute timeout; 3929-byte prefix ungraded |
| Harder pagination, Coder-Next Q4 | Asked for examples after 321.655 seconds; no patch |
| Harder pagination, Coder-Next FP16 | Complete after 4915.246 seconds; **20/25, rejected** |
| Revised 120-minute / eight-thread round | User-cancelled during first request; no new completed patch or quality score |

Eight threads reduced observed motor wall time by only 1.35% in one historical
pair. Actual residency budgets/cache/desktop activity differed; do not claim a
causal speedup, doubling performance or overall coding equivalence from this.
F16 pagination failed two core success scenarios plus three validation checks.
No harder pagination patch was accepted. No cloud cost savings were measured.

Read `docs/evaluation.md`, `docs/benchmarks/project-patches.md` and public data:
`2026-11-24-project-patches.json`, `2026-11-24-motor-threads.json`,
`2026-11-24-review-pause.json` under `docs/benchmarks/data/`.

## Code and test design to critique first

`local_worker_bench/project_bench.py` holds three synthetic projects: pagination,
telemetry duration and two-file SI export. Frozen suites contain 25/26/23 cases.
Handwritten controls pass all; broken baselines score 3/25, 4/26 and 2/23.
These are **three tasks**, not 74 independent projects. Offline unit-test totals
are another number entirely, not model grades.

Important calibration: an intentionally wrong pager that always raises ValueError
passes **20/25** negative-heavy cases and fails all five success scenarios. The
all-cases-plus-supervisor gate rejects it, but the fraction is misleading. Some
exceptions can pass for the wrong reason without reaching the intended API response.
This is now explicitly tested and documented; frozen grading cases were not changed.

See `docs/review-request.md` for the critique brief and source index. Review strong
valid scenarios, negative-case provenance, mutation controls, strict types, realistic
multi-file work, acceptance/ranking, prompt decomposition and resource confounds.
The existing 17-case real-loopback HTTP fixture in `examples/patch-project/` has
not been qualified with a local model. No production Open-FDD fix was attempted.

Keep old cases/results frozen. If critique changes contracts or checks, create a
new suite version, new prompt hashes and fresh results for every compared model.
V2 currently means a revised prompt with examples, not revised grading cases.

`check_project_patch.py` verifies the reviewed bundle hash and uses a 15-second
subprocess/AST screen. **It is not a security sandbox** and inherits host permissions.
Read every generated file before execution. CI executes only handwritten controls,
never model candidates. `publish_project_results.py` requires matching source,
grade and explicit supervisor review before counting accepted tasks. Preserve
first pass/one local repair/supervisor rewrite separately; never call a rewrite
a local success. At most one targeted repair for a bounded task, then take over.

## Resource defaults: requested, not yet implemented

The user's latest implementation request is portable, overridable defaults:

- RAM: about **66% of currently available RAM**, with existing reserve/commit/private
  guards. `paging-plan` already defaults to .66; project benchmarks still hardcode .40.
- CPU: about **66% of affinity-visible logical CPUs**, rounded to a whole thread,
  minimum one and no more than exposed CPUs. Proposed rule selects five on this
  eight-thread PC and eight on a 12-thread PC. This is not a count of idle cores
  and not a hard CPU-utilization cap. Allow explicit thread/fraction overrides.

This auto-CPU change was discussed but **not coded** before the user requested
handoff. Cursor should finish it offline while keeping inference paused. Current
preparation/runner choose four/eight explicitly, API profiles cap at eight, and
older CLI helpers have their own limits. Update those coherently for larger hosts,
preserve historical profiles and add deterministic 1/2/8/12/large-CPU tests.
Record detected capacity, selected threads, fraction and override provenance.
Do not silently reinterpret old four/eight-thread or .40-budget results.

The RAM planner currently clamps to .10-.66, reserves max(2 GiB, 10% physical),
and has a 24 GiB prototype working-set ceiling. Windows working-set RSS is not
whole-host cache/commit. Do not remove safety guards to make a test pass.

## Runtime disposition and resumption

Stopped: overnight dispatcher 9724, matrix 6680, precision extension 10388.
No benchmark llama-server process or inference/campaign lock remained after stop.
Unrelated Ollama/idle helper services were not killed. Old STOP markers and claims
are retained in:

- `results/project-patches-20261124-managed`: completed reference pagination round.
- `results/project-overnight-20261124`: matched motor8 and cancelled revised matrix.
- `results/qwen38-precision-extension-20261124`: cancelled, never inferred new pair.

There is **no queued BF16 inference extension**. BF16 aliases/header checks are
prepared, and its missing Coder-Next weights are downloading. Download completion
does not authorize inference. INFERENCE_PAUSED protects benchmark scripts, not
the entire OS or every possible raw API client; respect the user's instruction.

After critique and explicit user resumption: implement agreed fixes/versioning,
verify all models/metadata, choose resource policy, remove the repository pause
marker deliberately, and create a **fresh** finite run. Do not erase old STOPs or
replay claimed jobs. Test all conditions with identical cases/prompt/limits and
retain failures, context refusals, truncation, memory guards and timing. Hosted
automatic wakeup/review/merge is not implemented; deterministic dispatchers only draft.

## Validation, report and delivery

Last offline check: **109 unit tests passed**, plus handwritten fixture selftest.
Before pushing code, run:

```powershell
python -m unittest discover -s tests -v
python -m local_worker_bench selftest
git diff --check
```

Human-facing research note (Typst, ≤6 pages): `docs/reports/os-paging-research.pdf`
from `docs/reports/typst/main.typ` (`typst compile ...`). The older illustrated
PDF `docs/reports/os-paging-guide.pdf` (ReportLab, `scripts/build_paging_report.py`)
remains for agent context; prefer the Typst note for people. Do not hand over an
overflowing report. Refresh actual findings, not pending-model scores.

Finish the critique/resource-default work offline, keep commits/pushes small and
honest, and wait for the user before spending more inference time. Full continuation
history and exact local paths are in `docs/checkpoint.md`; newer pause notes override
older active-campaign sections.
