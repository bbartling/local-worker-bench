# Local Worker Bench: coding-agent context

## Active inference pause - 24 November 2026

The user paused local model testing pending another model's critique of the test
design. Downloads and offline code/handwritten-control checks may continue.
Do not start inference, smoke calls, benchmarks or queued model work until the
user explicitly resumes. Current inference campaigns/dispatchers have stopped;
preserve STOP markers and claimed/cancelled evidence. Read docs/review-request.md
and docs/checkpoint.md before any continuation. This pause does not authorize
stopping unrelated user applications or changing global Ollama settings.

## Project context

The active product is **single-machine OS-managed paging**, not a cluster.
Read `docs/guide.md`, `docs/agent-guide.md`, and `docs/evaluation.md` first.
Historical cluster/LAN evidence is indexed in `research/README.md`; do not
restore those defaults or use them as current machine configuration.

Use synthetic fixtures. Never commit weights, credentials, application data or
private logs. Raw receipts/downloads stay under ignored `results/`. Published
benchmark evidence must retain failures and source hashes and remove private paths.

Reading context does not authorize inference. An explicit current-task request
does; respect any later pause. Four CPU threads, one inference worker at a time.
Do not change global Ollama/pagefile/firewall settings or close work applications.
Model downloads may run concurrently when authorized; disclose I/O contention
in benchmark timing and record hashes before inference.

Use `paging-plan` to detect host RAM and create a model profile. A maximum .66
fraction applies to currently available RAM, with a separate reserve. The API
replans before each admitted request and stops the owned process on guard failure.
OS pages are not fixed model slices. RSS excludes some cache/commit costs.
Linux planning is portable; hard Linux cgroup enforcement and WSL inference
are not yet qualified. Never relabel Windows timings as Linux results.

The hosted supervisor owns planning, edits, test selection, security and final
acceptance. Local outputs are draft data, never shell/tool authority. Pin source
revision, limit allowed files, provide one clear contract and non-goals. Review
source before any hash-gated checker. AST checks/timeouts are not a sandbox.
Allow at most one targeted repair, then take over or checkpoint. Do not count
a supervisor rewrite as local-model success or assume every failure is a prompt bug.

Durable jobs stop at `needs_review`. Never replay a `drafting` job automatically
after a crash; its execution may have happened. A saved checkpoint does not keep
a hosted agent alive or renew its quota. No unattended merge loop is implemented.

Before pushing main: `python -m unittest discover -s tests -v` and
`python -m local_worker_bench selftest`. Render and visually inspect changed PDF
pages; the active report must remain at most ten pages. CI is offline only.
