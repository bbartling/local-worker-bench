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

The managed cohort is running. Qwen3.8 Q4's pagination request reached its
90-minute deadline (5401.227 s client wall) without a complete patch. Its 3929-byte
prefix is preserved and ungraded; peak process RSS was 6.58 GiB and minimum host
available RAM was 7.60 GiB. Coder-Next Q4 is next. No patch has been accepted yet.
The live publication snapshot is data/2026-11-24-project-patches.json; future
requests remain pending rather than receiving invented grades.

An earlier hidden launch lost its controller/client without a Python error log;
its orphan worker was identified and stopped, and the ungraded interruption was
preserved locally before an explicitly supervised replacement launch. Do not count
that infrastructure interruption as an additional model correctness failure.
No real Open-FDD patch or autonomous production result is claimed.

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

### Authorized overnight profile, revised prompt

The user subsequently authorized a 120-minute deadline for overnight patch cycling.
Finish the active F16 pagination request under its original settings, then stop
the remaining original queue. Preserve the three-model pagination reference round,
including timeout and needs-context outcomes. If the old loop claims a subsequent
task during handoff, its cancellation is a supervisor policy change, not a coding
failure. The original nine-task matrix is therefore superseded, not completed.

`scripts/handoff_project_overnight.py` first repeats the prior successful Qwen3.8
Q4 motor prompt with eight threads: same saved prompt hash, 2048 context, 1024
output, .40 RAM and 90-minute deadline. This isolates the configured thread change
from deliberate prompt/output/deadline changes; uncontrolled host/cache state still
prevents a rigorous causal speed claim. Source must be reviewed and graded again.

It then launches a fresh three-model/three-task round: eight threads, 4096 context,
2048 output, 120-minute end-to-end request deadline, unchanged RAM guards, and a
24-hour campaign deadline. Profile v2 includes compact worked examples and asks
for concise code. All models receive identical revised packets, using the same
broken sources, contracts and frozen tests. Clarification is informed by the
earlier needs-context reply. This is a follow-up profile/delegation experiment,
not a pristine first-pass result or a thread-only/precision-only comparison.
Default profiles remain four threads; longer outputs require explicit registration.

The dispatcher, motor request and new matrix only save drafts. The hosted
supervisor still owns inspection, tests, any one targeted repair and acceptance.
No generated tests, source execution or unattended patch acceptance is added.
STOP in the dispatcher's output prevents further stages and cancels its active
stage. The old and new outputs are separate and no claimed job is replayed.
