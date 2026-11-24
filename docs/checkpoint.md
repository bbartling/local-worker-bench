# Paging tool continuation checkpoint

## Newest request: actual Qwen3.8 FP16 plus standard-Q4 control

User requested both families compared at Q4 and FP16; downloading was explicitly
authorized now. Cached Qwen3.8 BF16 is distinct and is not relabeled FP16.
Two pinned prithivMLmods artifacts started concurrently with active inference:
- qwen38-f16: PID 5032, managed session 55998, 54,657,733,952 bytes.
- qwen38-standard-q4: PID 13208, session 75412, 16,810,714,432 bytes.
Both revision 3ccdd49b1030d9ce891e42e817ece300ae278562. Manifests are committed
under examples/paging/; raw cache/status under results/model-cache/<alias>/.
Runtime launch metadata: results/paging-background/qwen38-precision-downloads.json.
Do not start duplicate writers, delete partials or treat download start as verified.

Prepare/extension scripts support these new aliases. The planned queued extension
waits for the active overnight matrix to finish AND both verification manifests,
inspects real tensor types/shapes/templates, then runs only the new two aliases
on identical v2 tasks at eight threads/120 minutes/2048 output/4096 context/.40 RAM.
Coder-Next Q4/F16 results in the preceding matrix supply the other half of the
four-way comparison. Existing UD Q4 remains extra, BF16 separate. Download I/O
contention must be disclosed in timing. Extension dispatcher is already launched:
PID 10388, managed session 56162, output results/qwen38-precision-extension-20261124,
state waiting_for_parent_and_verified_models. It waits at most 24 hours for the
parent matrix and both verified downloads, then runs a separate finite matrix.
Do not start another dispatcher. STOP there, or cancellation of the parent pipeline,
prevents queued inference while downloads remain independent. Source at launch:
5a3996c. Latest checks: 104 offline tests + selftest pass. PDF refreshed and visually
verified, eight pages; it records actual failures and the pending precision pair.

## Latest steering: overnight 120-minute / eight-thread follow-up

User explicitly accepts 120-minute requests and wants supervised overnight patch
cycling. Keep the active four-thread F16 pagination attempt under its original
90-minute/1024-token settings, then stop the remaining original queue. The
original nine-request plan is superseded, not falsely reported complete.
The three pagination reference attempts remain preserved, including Qwen3.8 Q4
timeout and Coder-Next Q4 needs-context. Any new old-queue task caught in handoff
is supervisor cancellation, not a model correctness failure.

New dispatcher scripts/handoff_project_overnight.py will wait for that boundary,
then run one matched eight-thread Qwen3.8 Q4 motor trial (saved identical prompt,
2048 context, 1024 output, .40 RAM, 5400 sec). After that, a fresh profile-v2
matrix uses eight threads, 4096 context, 2048 output, 7200 sec, .40 RAM, all
three models/tasks, 24-hour campaign ceiling. Prompt v2 adds worked examples
to address the earlier refusal, not test code. Frozen tests/contracts unchanged.
This is a revised profile/delegation comparison, not a thread-only ablation.

Prepared config: results/project-patch-overnight-setup-20261124/api-config.json.
Motor prompt: results/retest90-20261123/cohort/qwen38-q4-packet/motor.prompt.txt
(SHA e8e4dbe0029c80e6d5522f74773c74e524a72b8169aa50ef52889c852ae7c9c4).
Dispatcher is already launched once, PID 9724, managed exec session 24007,
output results/project-overnight-20261124. It is waiting_for_legacy_pagination.
Do not launch another dispatcher. Motor output will be motor8/ and the new
matrix matrix/ beneath that folder. STOP in the dispatcher folder cancels its
active/waiting stage and prevents subsequent stages. Preserve all old evidence.
No generated-source execution. Source revision at launch: 6c3a33b.

Boundary observed: F16 pagination completed in 4915.246 s with bundle hash
e711530e74b161f1afbff9c6fb73d70e3209125101cea0edfee06aeef09de511.
Supervisor read the entire callback-only file, hash-graded it: 20/25, rejected.
Grade and review.json are beside the original candidate. Five frozen failures:
offset caps, token/offset transition, token after total, boolean/float max_pages.
Coder-Next Q4 asked for clarification in 321.655 s; no source to grade.
All three original pagination attempts accepted 0/3. A just-claimed old telemetry
task was cancelled by the handoff and excluded from model attempts. Original
cohort finished.

Matched motor8 completed: 1951.473 s, 311 output tokens, supervisor inspected
complete function and hash-graded unchanged source 49/49. Raw source SHA:
832b074478ae06e6aade21b121a2be96a4b6ab1e367874466b6b502e2888be0b.
Same prompt and same source AST as four-thread control (1978.139 s, 49/49).
Only 1.35% lower wall time; no near-2x benefit observed, host/cache/budget differ.
Public evidence: benchmarks/data/2026-11-24-motor-threads.json.

Dispatcher state is now overnight_v2_running, matrix PID 6680, output
results/project-overnight-20261124/matrix, source revision ca429e5. First revised
pagination--qwen38-q4 claimed; eight threads, 7200 sec, 2048 output, prompt v2.
Parent dispatcher remains PID 9724, session 24007. Do not launch competing jobs.

## New authorized work: Open-FDD-inspired project patches

User requested going ahead with more sophisticated patching and regular commits
and pushes. Open-FDD remains untouched. Three synthetic tasks (pagination,
telemetry duration and two-file SI export) now have fixed tests, intentionally
broken baselines and handwritten passing controls. See benchmarks/project-patches.md.
The first-pass matrix is Qwen3.8 Q4, Coder-Next Q4 and Coder-Next F16, serial,
four threads, 4096 context, 1024 output, .40 RAM, 90 minutes per request. No
automatic source execution or repairs. Inspect and hash-grade complete files
before accepting any result. Runtime details will be recorded after launch.

Live run: results/project-patches-20261124-managed, controller PID 25976,
managed exec session 64725, loopback port 11440. First task pagination--qwen38-q4
claimed. Config: results/project-patch-setup-20261124/api-config.json. Inspect
campaign.json, candidate.json, API partial/receipt files and grade.json; do not
relaunch or delete active leases. Write STOP in this run folder to cancel.
The first hidden launch results/project-patches-20261124 ended with controller
PID 23100 and client 21916 absent, no Python error log, native worker 25828
orphaned. Supervisor confirmed identity, stopped that worker and removed only
those dead-owner locks, preserved an infrastructure-interruption disposition,
then explicitly launched the unchanged replacement cohort in the managed session.
No complete candidate from that interrupted attempt was graded or counted.

Thread follow-up requested: user asked about using more than four threads.
Preserve the active four-thread matrix; afterward run a matched eight-thread
trial on a completed task/model. Explicit --threads 8 setup and campaign flags
are implemented; ordinary profiles still default to four. Do not run this
concurrently with the matrix or change its active profile.

First matrix outcome: Qwen3.8 Q4 pagination timed out after 5401.227 seconds,
3929 bytes retained, no complete candidate and no coding grade. Owned worker
exited; peak RSS 6.58 GiB, minimum available RAM 7.60 GiB. Coder-Next Q4
pagination is now claimed. Public snapshot: benchmarks/data/2026-11-24-project-patches.json.
Eight-thread setup is ready at results/project-patch-setup8-20261124/api-config.json;
no eight-thread inference has started. Latest offline checks: 98 tests + selftest pass.

## Completed after the three-hour wait

The handoff and finite cohort are finished. No further inference is scheduled.
Qwen3.8 Q4 returned its motor source in 1978.139 s and Coder-Next F16 in
2508.905 s. The supervisor inspected both complete functions and independently
hash-graded their unchanged source: **49/49 first pass each**, no repairs.
Qwen3.8 BF16 reached its 5400-second deadline (5401.615 s client wall); its
137-byte incomplete prefix is retained and ungraded. All owned native workers
exited. All three downloads, including 159.46 GB F16, are verified.

The old legacy BF16 patch request was capped at its 90-minute boundary. Its
terminated client left inference.lock with PID 28448; that process was confirmed
absent before this exact stale lease was removed. The new cohort then proceeded.
Do not replay the completed cohort or extend BF16 automatically to 120 minutes.
The user considered that option; two models completed within 90 minutes already.
Next useful evidence is matched repeated trials or a bounded real-project patch,
not another unrestricted timeout increase. Public evidence is in
benchmarks/data/2026-11-23-retest90.json and evaluation.md. Earlier active-state
notes below are retained as history and are superseded by this completion note.

## Active instruction: bounded 90-minute retest with partial capture

User authorized one longer retest and continued testing of the new models, with
no further timeout escalation if none can complete. The readiness gate is the
same motor packet for Qwen3.8 Q4, Qwen3.8 BF16 and Coder-Next F16, in that order.
Each gets 5400 seconds end to end, 1024 output tokens, four threads and the same
.40 available-RAM fraction and reserve/private guards. Startup may use up to
600 seconds of that total. The client has 30 seconds of transport grace.

New profiles capture native SSE into partial.txt and events.jsonl per API receipt,
while the public API still returns a non-streamed completed response. Every
content delta is flushed. EOF, timeout and disconnect retain an ungraded prefix;
completion requires a final finish marker and DONE. Failed API replies now carry
receipt IDs through the helper client. Do not grade or apply partial source.

The old Qwen3.8 Q4 motor attempt generated 279 tokens at about .16 tokens/s but
lost its text because it used buffered transport. Its 1800-second result remains
ungraded. The compact patch remains 25/25. Qwen3.8 BF16 is now fully verified and
its legacy first patch request is already running. The F16 download resumed
successfully after an incomplete partial response; all parts must verify first.

Handoff controller (explicitly launched once): results/retest90-20261123/handoff.json.
It waits for the legacy BF16 patch response, or its original start plus 90 minutes,
then writes STOP to results/paging-precision40-20261123 and waits for that campaign
lease to release. The new cohort is results/retest90-20261123/cohort, API port 11439.
The older 6-hour campaign must not continue into further tasks after handoff.
No claimed jobs or failed attempts are overwritten or automatically replayed.

The new cohort uses --request-timeout 5400 --load-timeout 600 --tasks motor with
all three new-model aliases. It generates candidates only and ends after the
finite cohort. completed_model_count means complete source responses, not passed
independent tests. If none completes it records stopped_without_completions:true
and further_timeout_escalation:false, stops its API, and performs no more attempts.
If candidates complete, the hosted supervisor must review and hash-grade them.

Cancellation: create results/retest90-20261123/STOP for the handoff controller, or
results/retest90-20261123/cohort/STOP once the cohort is running. Its normal stop
also cancels the owned request. Downloads are independent. Runtime controller PID
is recorded in results/paging-background/retest90-process.json. Inspect these
files before starting any competing API or inference.

The in-flight legacy request cannot be retroactively switched to SSE capture.
It is allowed to finish, or is capped at the new 90-minute boundary; metrics and
its final answer if available are preserved. Any later legacy task interrupted
for the handoff is a supervisor cancellation, not a model quality failure.

---

## Latest follow-up: Qwen3.8 Q4 is verified and tested

- Qwen3.8 Q4 download is complete and SHA-verified. First .66-budget smoke failed
  the unchanged desktop-RAM guard; the owned worker exited. Preserve that failure.
- A separately supervised .40-budget smoke passed. The compact coding packet
  passed 25/25 in 284.918 seconds, with the identical source hash as Coder-Next.
- Motor/elapsed drafts are still running in results/qwen38-q4-packet40-20261123;
  do not grade incomplete responses or execute new source without inspection.
  The manual API is port 11438, config results/qwen38-q4-conservative-config.json,
  receipts results/qwen38-q4-conservative-api. Its in-flight calls retain their
  original 1800-second limit; new code does not extend a running process.
- Original results/paging-matrix-20261123 has STOP set and its API exited. Its Q4
  needs_supervisor entry must not be replayed or relabeled as a coding failure.
- New published snapshots: qwen38-admission.json and qwen38-firstpatch.json under
  docs/benchmarks/data; the latter explicitly contains only the compact grade.
- examples/patch-project is a staged toy project, not a graded model patch yet:
  17 tests, 10 failing in the red baseline, all passing with a handwritten control.
- 80 offline tests pass after selected-model/conservative-budget/long-timeout
  campaign support and the disposable project fixture were added.

The two large 16-bit downloads remain active and unverified at this snapshot
(roughly 83/159 GB Coder-Next F16 and 34/55 GB Qwen3.8 BF16). Exact live status
is in their download-status.json, not these rounded historical values.

The next explicitly authorized precision campaign uses a new ledger and port,
so it does not restart the failed Q4 claim or compete with its running client:

```powershell
python -u scripts/run_paging_campaign.py --backend results/layer-stream-backend/build/bin/Release/llama-server.exe --output results/paging-precision40-20261123 --port 11439 --wait-hours 48 --models qwen38-bf16 coder-next-f16 --memory-fraction .40 --request-timeout 21600
```

It waits for verified artifacts AND the existing local worker lease, then runs
one model at a time. Six-hour calls are an explicit slow-precision experiment;
output/context/RAM guards remain bounded and unchanged. All drafts stop for
hosted source review and grading, not automatic execution or acceptance. Status:
results/paging-precision40-20261123/campaign.json. Cancellation marker:
results/paging-precision40-20261123/STOP. Runtime PID/log paths are recorded under
results/paging-background. This does not stop the independent Q4 run on 11438;
its documented /api/generate unload route can cancel that request when asked.

Next supervisor: inspect and grade the Q4 motor/elapsed sources when complete,
record any timeout as ungraded, then use the HTTP patch packet on a disposable
copy. Review 16-bit outputs only after verification, inference and source review.
Do not call the partial first-patch snapshot a complete model ranking.

---

23 November 2026. Active direction: one computer, OS-managed paging, hosted
supervisor, bounded local drafting. Cluster features are historical research.

## Phase 1 completed

- Hardware detection and an admission budget up to .66 of available RAM, with
  reserve, recalculated before each request. Windows hard working-set control.
- New-profile context preflight with output room and no context shifting; the
  real API rejected an oversized prompt before generation and cleaned up.
- Durable SQLite draft/review/needs-context checkpoints, no claimed-job replay,
  source/revision/check-hash acceptance gates and one-repair supervision policy.
- Slim README, project SVG and real CI badge. Old cluster PDF removed; active
  report is eight pages, built by scripts/build_paging_report.py.
- Fresh Q4 trial: motor 47/49, elapsed 46/46 = 93/95 first pass; one targeted
  local repair made motor 49/49 and the repaired total 95/95. Compact patch 25/25
  is separate. Concurrent downloads and changed prompts/budgets limit comparisons.
- The first motor job remains needs_supervisor; its failed result was not accepted.
  Patch and elapsed receipts were accepted after source inspection and checks.
- New evidence: docs/benchmarks/data/2026-11-23-paging-packets.json.

The manually run API and inference workers were stopped after review. A separate
finite campaign below owns its own loopback API and waits for verified new files.
It saves drafts only, never executes candidate code or accepts/merges patches.

## Background downloads and finite campaign

Downloads were resumed as hidden processes with logs under
`results/paging-background/`; `processes.json` records the current download PIDs.
Each model output has download-status.json. Only a completed verified-manifest.json
with all_sha256_verified:true admits a model. No new-model inference had run at
this checkpoint: downloads were incomplete.

| Manifest | Output directory | Explicit budget |
| --- | --- | ---: |
| examples/paging/coder-next-f16.download.json | results/model-cache/coder-next-f16 | 165 decimal GB |
| examples/paging/qwen38-q4.download.json | results/model-cache/qwen38-q4 | 18 decimal GB |
| examples/paging/qwen38-bf16.download.json | results/model-cache/qwen38-bf16 | 58 decimal GB |

The explicitly authorized continuation command is:

```powershell
python -u scripts/run_paging_campaign.py --backend results/layer-stream-backend/build/bin/Release/llama-server.exe --output results/paging-matrix-20261123 --port 11438 --wait-hours 48
```

It owns the loopback API, claims each verified model once, performs smoke then
bounded serial task-packet drafting with four threads, and stops at review or
failure. No automatic retries or merges. Check `results/paging-matrix-20261123/campaign.json`,
model client logs, API receipts and candidate SQLite ledgers. Incomplete/claimed
work requires supervisor disposition, not silent replay. The runtime PID is
recorded in `results/paging-background/campaign-process.json` after launch.

To request campaign cancellation, create `results/paging-matrix-20261123/STOP`.
That prevents new claims and stops an active owned request on the next poll.
Downloads are independent; stopping the campaign does not delete or stop them.
After a hard process kill, inspect owned processes and locks before restarting.
Do not launch duplicate writers or a competing API on port 11438.

Resumable download commands, only if their existing processes have stopped:

```powershell
python -u scripts/download_gguf.py --manifest examples/paging/coder-next-f16.download.json --output results/model-cache/coder-next-f16 --max-gb 165 --workers 3
python -u scripts/download_gguf.py --manifest examples/paging/qwen38-q4.download.json --output results/model-cache/qwen38-q4 --max-gb 18 --workers 1
python -u scripts/download_gguf.py --manifest examples/paging/qwen38-bf16.download.json --output results/model-cache/qwen38-bf16 --max-gb 58 --workers 2
```

## Next supervisor gates

1. Review new-model candidates before any execution. Hash-grade source and retain
   incompatible loads, context failures, timeouts and RAM rejections. Update the
   evidence/guide after grading; downloading or drafting is not a quality pass.
2. Compare F16/BF16 versus Q4 with actual tensor types and matched prompts. The
   existing 80B Q4 is already Coder-Next. Qwen3.8 uses community UD quantization;
   BF16 is not IEEE FP16. No new precision grades exist at this checkpoint.
3. Run a matched baseline/packet ablation and disposable real project patches,
   with one local repair maximum and separate supervisor contribution accounting.
4. Linux/WSL qualification later. Only Docker internal WSL currently exists;
   no user distro, cgroup limits or global WSL settings were changed. Linux
   offline CI is not a Linux inference qualification.

Quota remained healthy at the last check. If the five-hour remaining amount
falls below 10%, update this checkpoint, commit and stop dependent hosted work.
No automatic quota-renewal wakeup or continuous hosted supervision is configured.
The finite local campaign can only save work for later review.

An initial launcher attempt stopped before model work because its new lock name
was missing from the lock whitelist; that was fixed and regression-tested.
