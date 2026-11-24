# Paging tool continuation checkpoint

## New authorized work: Open-FDD-inspired project patches

User requested going ahead with more sophisticated patching and regular commits
and pushes. Open-FDD remains untouched. Three synthetic tasks (pagination,
telemetry duration and two-file SI export) now have fixed tests, intentionally
broken baselines and handwritten passing controls. See benchmarks/project-patches.md.
The first-pass matrix is Qwen3.8 Q4, Coder-Next Q4 and Coder-Next F16, serial,
four threads, 4096 context, 1024 output, .40 RAM, 90 minutes per request. No
automatic source execution or repairs. Inspect and hash-grade complete files
before accepting any result. Runtime details will be recorded after launch.

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
