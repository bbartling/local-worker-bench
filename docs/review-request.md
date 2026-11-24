# Independent review: are these patch tests meaningful?

**Inference is paused at the user's request. Downloads may continue.** Do not
start models, smoke calls, servers or campaigns. Offline code inspection and
handwritten-control checks are allowed. INFERENCE_PAUSED blocks benchmark entry
points; only explicit user resumption permits more model work.

## Goal and planned comparison

Can a hosted supervisor delegate bounded coding, inspect the draft, independently
test it and accept useful patches with little intervention? Overnight runtime is
acceptable. Production patch reliability and hosted token/cost savings are unproven.

Planned profile: i7-9700, eight physical/logical cores, 32 GiB Windows, one worker,
eight threads, 4096 context, 2048 output tokens, 120 minutes end to end, .40 of
available RAM and separate resource guards. This is not hardware-isolated testing.

| Family | Q4 | FP16 | BF16 |
| --- | --- | --- | --- |
| Qwen3.8-27B | Standard prithivMLmods build downloading | Same publisher/revision downloading | Unsloth cached |
| Coder-Next 80B | Qwen cached | Qwen cached | Unsloth downloading |

The earlier Unsloth UD Q4 is additional evidence, not the standard Q4 control.
BF16 and FP16 differ. Conversion publishers/revisions differ too; nominal format
alone cannot establish causality. Manifests pin sizes, revisions and SHA-256.
Preparation reads real GGUF tensor types, split consistency and template hashes
without loading weight payloads or inference.

## Review these sources

- `local_worker_bench/project_bench.py`: broken projects, handwritten controls,
  contracts, versioned prompts, AST screening and frozen model-grading cases.
- `scripts/check_project_patch.py`: reviewed bundle hash and 15-second checker
  subprocess. This is not an OS sandbox.
- `scripts/run_project_bench.py`: finite serial drafting, persistent pre-call
  claims, no automatic repairs, generated execution or acceptance.
- `scripts/publish_project_results.py`: candidate/grade/review hash matching;
  green case scores alone never imply acceptance; cancellations are excluded.
- `scripts/prepare_project_bench.py`, `queue_precision_extension.py`,
  `handoff_project_overnight.py`: format checks and lifecycle.
- `local_worker_bench/offload_api.py`, `native_stream.py`: resource/deadline guards,
  partial capture, final completion validation and owned-worker cleanup.
- `tests/test_project_bench.py`, `test_project_publication.py`, `test_pause.py`,
  `test_precision_extension.py`: offline harness checks.
- `docs/benchmarks/project-patches.md` and its linked evidence snapshots.
- `examples/patch-project/`: a separate 17-case HTTP fixture, not model-qualified.

Fixtures are synthetic inspiration from Open-FDD. Its real repository, deployed
services, customer data and credentials were not copied or changed.

## Actual outcomes

| Experiment | Result |
| --- | --- |
| Short motor function | Qwen3.8 UD Q4 and Coder-Next F16 each passed 49/49 unchanged |
| Qwen3.8 motor, four/eight threads | 1978.139/1951.473 s; both 49/49, 311 tokens, identical ASTs; only 1.35% lower wall |
| Pagination, Qwen3.8 UD Q4 | 90-minute timeout; prefix ungraded |
| Pagination, Coder-Next Q4 | Asked for examples in 321.655 s; no patch/score |
| Pagination, Coder-Next F16 | Complete in 4915.246 s; 20/25 checks; rejected |
| Revised 120-minute round | User cancelled during first request; no new completed patch/quality result |

F16 failed both offset success scenarios and three validation checks. The revised
attempt was cancelled, not timed out. Historical/revised conditions remain separate.
Evidence is in `benchmarks/data/2026-11-24-project-patches.json`,
`2026-11-24-motor-threads.json` and `2026-11-24-review-pause.json`.
Frozen suites have 25 pagination, 26 telemetry and 23 export cases: **three tasks,
not 74 projects**. Offline unit-test totals are another number, not model scores.

## Known concerns

1. **Negative-heavy scoring:** a deliberately wrong pager that always raises
   ValueError passes 20/25 frozen cases while failing all five success scenarios.
   The all-checks-plus-supervisor gate rejects it, but the fraction is misleading.
   Some invalid cases can pass for the wrong reason: only exception class is checked,
   not whether the intended response/interaction was reached.
2. **Coverage:** examine exact-int subclasses, token/offset transitions, empty
   tokens/pages, totals, duplicates, validation before fetch, mutation and numeric
   edges. Are difficult valid inputs sufficiently represented?
3. **Scope:** mostly function replacements and one two-file task. No real-repository
   diagnosis, correct git diff, build integration or long autonomous cycle is proven.
4. **Delegation confounds:** V2 adds examples, concise-code guidance, threads, time
   and output together. Improvements cannot be attributed to one change. Was the
   original needs-context refusal reasonable? Is missing context handled correctly?
5. **Timing:** changing absolute RAM budgets, OS cache, downloads, run order and
   desktop activity; one trial per condition, no randomized repeats/cold-cache reset.
   RSS is not total cache/host use. More threads did not double measured throughput.
6. **Execution trust:** AST screening and a timeout are not a sandbox. The subprocess
   inherits host permissions. Check imports/namespaces, review-before-execution,
   source hashes, cancellation and manual acceptance boundaries.
7. **Public tests:** cases are withheld from prompts but public; this is not
   contamination resistant. Passing handwritten controls does not prove coverage.
8. **Formats:** FP16/BF16 can have F32 auxiliaries; Q4_K_M is mixed quantization.
   Check strict header gates for false rejection/mislabeled formats, base/conversion
   revisions, templates and CPU backend compatibility before quality comparisons.

## Requested critique

Return findings with file/line, severity and a concrete counterexample. Prioritize
false positives, missing success paths, ambiguous contracts, unfair comparisons,
unsafe assumptions and scoring. Propose a minimal next suite version, adversarial
or mutation controls, and acceptance/ranking policy. Suggest one realistic disposable
project patch and a larger-task versus decomposed-delegation comparison. Separate
must-fix items from optional expansion.

**Do not edit frozen grading cases retroactively or reinterpret old outcomes.**
Revised suites need a new version with all model conditions using the same cases.
Do not run inference or modify real Open-FDD. The user will review the critique
before deciding when to resume.
