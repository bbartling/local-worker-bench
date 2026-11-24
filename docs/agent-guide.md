# Hosted supervisor, bounded local coding

The hosted agent owns the project. The local model drafts one small function or
replacement block, returns data, and never gets shell authority. A slow draft
can be useful overnight; slow work is not automatically useful work. Measure
accepted output and review effort, not just tokens generated locally.

## Prompt packet

Start from `examples/paging/task.packet.json`. Specify:

1. One concrete edit, pinned source revision and repository-relative allowed files.
2. The exact relevant excerpt, dependencies and function signature.
3. Acceptance criteria including invalid inputs, edge cases and return types.
4. Non-goals, output schema and a clear request for missing context when needed.

Prefer one function or decision block. Split work needing more than three files;
keep architecture, auth/security, ambiguous diagnosis and integration with the
supervisor. `validate_packet` rejects missing/oversized context and unsafe paths;
it cannot prove the task is well specified. A character limit is not a tokenizer.
Keep the packet comfortably below the context window and reserve output space.

```powershell
python scripts/draft_job.py --packet examples/paging/task.packet.json --model qwen3-coder-next:q4_K_M --output results/my-job
```

Replace the example source revision before project use. The endpoint defaults to
loopback port 11438 and must already be running. One authorized invocation makes
one bounded call, saves the prompt and candidate, unloads, and stops at review.
It never applies source or runs tests.
Default output is 512 tokens; use `--max-tokens` from 64 through 1024 when the
registered server permits it. Smaller edits need less output and leave more
context room. The native profile also disables context shifting.

`jobs.sqlite` records queued -> drafting -> needs_review (or needs_context/failed).
A missing-context reply stops without creating source or being counted as an
accepted patch. `JobStore` can inspect state and record a decision with
matching source/check hashes and the same base revision. A claimed job cannot be
automatically replayed after a crash. Preserve it for supervisor disposition.

## Review and repair

Inspect the actual source/diff before execution. Confirm allowed files, stale
revision, imports/I/O, contract and dependency assumptions. Run independent tests
in a disposable copy only after review. The existing `check` is hash-gated with
a timeout/AST filter; it is not a security sandbox. Test receipts must match the
candidate bytes. Never run untrusted generated candidates in CI.

Inspect a saved job with `python scripts/review_job.py --db results/my-job/jobs.sqlite --job JOB_ID`.
After source review and independent checks, the same command accepts a decision
with `--decision accept --source results/my-job/candidate.py --grade CHECK.json
--reviewed-sha256 SHA --current-revision REV`. Use `takeover` for a failed
candidate. These commands record decisions; they do not merge or execute source.

Use at most one corrective local retry: send the failing input, expected/actual
result and the smallest relevant block. Preserve first pass and repair separately.
If the supervisor rewrites the answer, label that contribution honestly. Stop for
missing context, output truncation, timeout, resource guard or repeated failure.
Do not blame every miss on prompting; the model can fail a complete contract too.

## Test the delegation, not only the model

Compare baseline and structured packets on the same model, backend, memory budget,
output allowance and thinking policy. Preserve prompt hashes and all failures.
Separate task-size experiments from added hints: naming a known failing case
changes the information supplied, not merely formatting. Broad versus decomposed
tasks also have different coordination/review costs. Randomize/repeat trials when
making performance claims; one improved answer does not establish causality.

Grade the supervisor on packet completeness, smallest useful scope, allowed-file
compliance, missing-context handling, independent test choice, retry restraint and
acceptance correctness. Grade local code on the separate fixtures. Report first
pass, after one repair, supervisor takeover, rejected/truncated and needs-context
outcomes. An HTTP 200 or plausible answer is not acceptance evidence.

## Overnight and quota checkpoints

Persist task IDs, source revision, hashes, backend/model revision, budgets,
candidate, timing, test receipt and next action. A deterministic dispatcher can
wait without calling the hosted model every few seconds. Wake the supervisor at
review checkpoints; never automatically merge a local draft. The current SQLite
ledger provides durable checkpoints, not a full unattended multi-day scheduler.
Campaign leases, automatic handoff, hosted-session recovery and `/jobs/*` remain
future work. Local API calls default to a 30-minute bound. Explicit slow-model
profiles and clients can use up to six hours per request; RAM guards, finite
output and cancellation remain active. Increase the deadline only as a recorded
experiment, not an automatic retry. Long calls do not keep a hosted agent alive.

An explicitly launched `scripts/run_paging_campaign.py` can wait up to 48 hours
for the three pinned new-model downloads, own a loopback API, run smoke and
bounded serial drafting once per model, then stop at review. It never executes
candidate code. Campaign state is persisted before claims, and claimed work is
not replayed on restart. This is a finite drafting campaign, not hosted critique
or unattended patch acceptance. No model work starts merely from downloading.
Create `STOP` in its output directory to request cancellation and prevent new
claims; normal shutdown stops owned workers. After a hard process kill, inspect
API/native processes and the ledger before restarting rather than deleting locks.
Use `--models` for a selected subset and `--memory-fraction` to lower the budget.
Use a new output directory when changing campaign settings; resume refuses changed
model selections, budgets or timeouts. It waits for existing local worker leases
before claiming another model. A stale lease needs supervisor inspection.

The currently authorized retest is one identical motor packet per new model,
90 minutes end to end, 1024 output tokens, four threads, .40 RAM fraction and
unchanged reserve/private-memory guards. Native partial text is saved during
generation. Each model receives one attempt, then the cohort stops; there is no
automatic retry or higher timeout if none completes. A complete JSON source is
only a readiness result; the hosted supervisor still inspects and grades it.
`scripts/handoff_long_retest.py` preserves/caps the already-running legacy request
at 90 minutes, then stops that older campaign and starts the new cohort. It does
not interrupt a long request immediately just to upgrade its capture mechanism.

If usage limits are observable, inspect them at milestones. On less than 10%
remaining, commit a checkpoint with exact running download/job IDs and restart
commands before stopping dependent work. A saved file cannot renew quotas or
guarantee the app wakes. Downloads can finish independently; no inference should
silently resume after a pause. The latest phase checkpoint is `docs/checkpoint.md`.

Hosted drafting tokens may be avoided, but planning, critique and retries still
cost hosted usage. Record provider usage when available and compare cost per
accepted patch with an all-cloud baseline. No cloud-cost savings were measured
in the initial lab. Source sent for hosted review still leaves the local machine.
