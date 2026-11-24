# Open-FDD-inspired project patch benchmark

Synthetic projects inspired by Open-FDD's API pagination, telemetry and SI-unit
contracts. Open-FDD is read-only inspiration: no source, customer data, deployed
service, credentials or application configuration is copied or changed.

| Task | Project edit | Independent checks |
| --- | --- | --- |
| Pagination | Replace a token-only pager with token/offset support | Server caps, totals, filters, duplicate IDs, repeated tokens, early empty pages, malformed terminal metadata, bounded calls |
| Telemetry | Repair fault/coverage duration | Unknown evidence, left-state intervals, gaps, unsorted rows, last duplicate wins, invalid overwritten data, finite strict numeric validation |
| Export | Coordinate units.py and report.py | SI conversion, exact input types, missing values, error propagation, no mutation on failure, output shape, actual delegation to the conversion helper |

The canonical broken fixtures and separately handwritten control patches are in
`local_worker_bench/project_bench.py`. Controls establish that fixed tests can
pass; broken baselines establish that the tasks detect actual faults. Models
receive only the broken sources and contract, not controls or test code.
Tests are fixed before inference. They are withheld from the request, not secret:
this public repository contains them. This is not a contamination-resistant benchmark.

| Task | Broken baseline | Handwritten control |
| --- | ---: | ---: |
| Pagination | 3/25 | 25/25 |
| Telemetry | 4/26 | 26/26 |
| Two-file export | 2/23 | 23/23 |

Preparation evidence is in `data/2026-11-24-project-controls.json`.

## Matched first-pass matrix

Three cached models: Qwen3.8 Q4, Coder-Next Q4 and Coder-Next F16. All use the
same task prompt, four CPU threads, 4096 context, 1024 output tokens, .40 of
available RAM, unchanged reserve/private guards and partial capture. The larger
context accommodates project contracts; do not compare its timings directly
with the earlier 2048-context motor trial as a precision-only experiment.
Requests have a 90-minute end-to-end deadline and 30 seconds transport grace.
The finite nine-request cohort has a 16-hour campaign deadline. Task-major
ordering reduces long delays before seeing each model on the first task; no
randomized repeated trials or cold-cache reset is claimed.

```powershell
python scripts/prepare_project_bench.py --backend results/layer-stream-backend/build/bin/Release/llama-server.exe --output results/PROJECT_SETUP
python scripts/run_project_bench.py --config results/PROJECT_SETUP/api-config.json --output results/PROJECT_RUN --models qwen38-q4 coder-next-q4 coder-next-f16
```

Preparation requires the three prior verified cached-model manifests; it checks
current sizes and GGUF headers without rehashing hundreds of GB on each launch.
It runs only handwritten baseline/control code and starts no inference.

`scripts/run_project_bench.py` owns a loopback API and serializes drafts. It
persists a claim before each request, refuses an existing output directory,
never replays jobs, never executes generated code, never repairs automatically,
and stops at review. Every supplied file must be in the exact allowed set.
A STOP file in its output directory cancels the owned worker and prevents new
requests. Context refusal, output truncation and resource failures remain failures
of that attempt, with reasons retained; they are not silently rerun with more RAM.

## Review and score

The supervisor reads every complete returned file, checks the source revision,
allowed paths, imports and behavior, and obtains the bundle hash from campaign.json.
Only then run, for example:

```powershell
python scripts/check_project_patch.py --task pagination --folder results/PROJECT_RUN/pagination--MODEL/candidate --reviewed-sha256 REVIEWED_BUNDLE_HASH --output results/PROJECT_RUN/pagination--MODEL/grade.json
```

The checker confirms that exact bundle, applies AST screening and runs fixed tests
in a 15-second subprocess. This is not a security sandbox. The two-file integration
test replaces report.to_si temporarily to verify the helper is actually called.
CI runs only handwritten controls/baselines, never generated candidates or inference.

Report all-checks-passed per task, individual cases, time, prompt/output tokens,
resource use and hosted review separately. A task passing 25 correlated cases
still counts as one task. No supervisor-written code counts as model success.
Before publication, write review.json alongside grade.json with the reviewed
source_sha256, decision (accept or needs_supervisor) and reason. A green test
grade without matching explicit supervisor acceptance is never an accepted task.
Contract issues found by review outside the frozen tests are recorded separately;
do not alter the frozen suite mid-matrix or hide those issues behind a green score.
At most one targeted local repair may follow an inspected failure in a separate
attempt with original source/failures preserved; this first-pass cohort performs
none. A larger-task versus decomposed-task supervisor study remains a separate
experiment rather than changing the prompt partway through this comparison.

## Status

Harness prepared; model results will be added after complete-source review and
independent grading. No real Open-FDD patch or autonomous production result is claimed.

### Separate thread-count follow-up

The user asked whether four threads underuses the eight-core i7-9700. Four is
the desktop-sharing default, not a hardware limit. An explicitly configured
eight-thread profile is now supported; requests cannot override a profile's
thread count. Preparation and campaign accept --threads 8. Keep the first matrix
at four, then repeat an identical completed task with the same model, RAM fraction,
context and output cap at eight. Record correctness again: changing execution
settings can change a draft. Cache state, available RAM and run order still limit
causal speed claims; report prompt and generation throughput separately. More
threads cannot remove SSD/page-fault stalls and may affect desktop responsiveness.
