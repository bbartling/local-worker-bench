# An overnight supervisor with local helpers

A shell-capable Codex or Claude supervisor can select the existing API model for
each bounded task. The current client already supports `ask --tier fast` (4B Q4)
and `ask --tier coder` (30B Q4). The supervisor remains responsible for planning,
review, repository edits and acceptance. Local helpers return drafts only.

A useful sequence is:

1. Define the task, allowed files, source revision and deterministic checks.
2. Use 4B for short extraction or organizing supplied evidence, where useful.
3. Use 30B for a bounded coding draft with the relevant excerpt and contract.
4. Review the draft, apply approved edits, run the real checks and inspect the diff.
5. Save the outcome/checkpoint. Allow one corrective retry, then escalate or stop.

The supervisor should choose directly between helpers; every job need not pass
through both. Tests and exit/status evidence decide acceptance. A model's own
statement that it passed is not a test receipt. Keep secrets and whole repositories
out of prompts, and keep excerpts small enough for the configured token context.

## Available now versus a durable runner

Available: explicit API calls, two routing tiers, bounded requests, JSON/text draft
receipts, source hashes, manual code review and deterministic synthetic checks.
The normal server allows one resident model and the client unloads after a call.

Not implemented: an unattended coding queue, automatic task pickup, restart/reboot
recovery, overnight scheduling, or a shared multi-agent dispatcher. Model weights
staying in RAM do not preserve job progress; the orchestrator must persist inputs,
drafts, checks and source revisions outside model context.

For a durable setup, give one dispatcher ownership of the queue and repository
branch. Persist stage receipts, cap attempts/runtime, stop on unresolved failures,
and checkpoint when the hosted supervisor reaches its usage limit. Codex and
Claude can share work through that queue rather than independently racing on files.
Local inference avoids hosted charges for those model tokens, but supervision,
review and retries still consume hosted usage; savings have not been measured.

## Residency and CPU budget

Keep generation sequential on this eight-thread CPU. With two models resident,
`OLLAMA_NUM_PARALLEL=1` is a per-model limit, not a global cross-model semaphore;
the dispatcher must serialize its requests. Four threads remain the measured
shared-desktop default. An idle-machine thread change needs its own comparison.

[Both 4B and 30B were briefly resident](benchmarks/2026-11-22-fast-coder-residency.md),
but the RAM reserve guard ended the test before a sustained hold. Current launch
and client defaults deliberately remain one resident model with immediate unload.
An opt-in warm overnight mode would need explicit server residency/keep-alive
settings, resource monitoring and cleanup; it is not enabled by this guide.

Batching related work on one model can reduce switches. On-demand loading remains
a workable approach when RAM is tight. A long night allows more wall-clock time;
it does not correct a bad draft or make a short readiness test a coding qualification.
