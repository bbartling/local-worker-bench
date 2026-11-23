# Paging tool continuation checkpoint

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
