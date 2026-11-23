# Working on this tool

Use synthetic fixtures only. Never commit application credentials, private logs,
model weights, or customer data. Keep generated results under ignored `results/`.

Model calls require an explicit user request for the current task. Use four
threads by default and one local worker at a time. The portable `ask` client
unloads afterward; the locked Mint OptiPlex host may keep `qwen3.5:4b` and
`qwen3-coder:30b` warm (`MAX_LOADED_MODELS=2`, `KEEP_ALIVE=-1`) per
`docs/linux-mint-4b-30b-setup.md`. Never start background inference, pull/delete
models, or alter the user's Ollama settings unless the current task explicitly
asks for that.

Review generated source before `check`; its AST filter and child-process timeout
are not a security sandbox. Do not run untrusted candidates in GitHub Actions.

Run `python -m unittest discover -s tests -v` and
`python -m local_worker_bench selftest` before pushing. Keep first-pass and repaired
results separate. Passing these narrow fixtures does not qualify an application.

## Context for future coding agents

Read the README's Start here links before working on model offload or routing.
`docs/sequential-layer-streaming.md` explains both measured Windows policies:
explicit mapped-weight eviction and OS-managed paging. Neither cuts the model
into independent mini-models. Its Linux section covers mmap/page cache, swap,
cgroup accounting and the unimplemented Linux eviction port. Linux and physical
three-host disk-backed performance remain unmeasured; do not reuse Windows
working-set numbers as equivalent Linux limits or isolated 8 GiB fit claims.

`docs/benchmarks/2026-11-23-sequential-streaming.md` and its linked JSON preserve
80B timings, first-pass grades, a separate supervised repair and API receipts.
`docs/cloud-supervisor-local-worker.md` describes keeping the hosted model in
charge of bounded local drafting, source review and independent checks. Durable
overnight orchestration and measured cloud savings remain future work.
`docs/reports/local-ai-cluster-explained.pdf` is the illustrated guide; rebuild
from `scripts/build_cluster_report.py` and visually verify changed pages.
These references provide context, not authorization to start inference.
