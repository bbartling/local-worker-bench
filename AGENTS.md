# Local Worker Bench: coding-agent context

## Pilot closed - 25 November 2026

Suite-3 six-format matrix finished and graded. **Winner kept on disk:**
`qwen38-standard-q4` (Qwen3.8-27B Q4_K_M). Other GGUF caches were deleted to
free space. Paper: `docs/reports/os-paging-research.pdf`.

Do not relaunch the full matrix or re-download deleted formats unless the user
explicitly asks. One inference worker at a time. Do not change pagefile/firewall
or kill unrelated apps. Raw receipts stay under ignored `results/`.

## Fire up the winner in stock Ollama

Two stacks exist on this PC — do not mix them in one session:

| Stack | What it is | When to use |
| --- | --- | --- |
| **Stock Ollama** | App + tag `qwen38-standard-q4` | Day-to-day chat / Cursor “local model” / quick drafts |
| **local-worker-bench API** | Owned `llama-server` + RAM guards | Benchmarks / Suite-3 / budgeted overnight drafts |

### First-time import (only if `ollama list` lacks the tag)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\import_winner_to_ollama.ps1
ollama list
```

Requires verified GGUF at
`results\model-cache\qwen38-standard-q4\Qwen3.8-27B.Q4_K_M.gguf`.

### Start Ollama and load the model

1. Launch **Ollama** from the Start menu (tray icon / `ollama serve` if needed).
2. Confirm the tag: `ollama list` → `qwen38-standard-q4`.
3. Load + chat in a terminal (keeps weights warm while the window is open):

```powershell
ollama run qwen38-standard-q4
```

Or one-shot without an interactive REPL:

```powershell
ollama run qwen38-standard-q4 "Summarize this contract in three bullets: ..."
```

HTTP (default `http://127.0.0.1:11434`):

```powershell
curl http://127.0.0.1:11434/api/generate -d "{\"model\":\"qwen38-standard-q4\",\"prompt\":\"Say ready\",\"stream\":false}"
```

Unload when done (frees RAM/commit for browsers): Ctrl+D / exit the `ollama run`
session, or `ollama stop qwen38-standard-q4`.

### Best use of the application (hosted + local)

- **Hosted model (Cursor/Claude/Grok) owns:** plan, file picks, security, tests,
  accept/reject, merges. Local output is **draft data only** — never shell/tool
  authority and never auto-merge.
- **Local Q4 is good for:** one bounded function/file, overnight mechanical
  edits, Suite-3-style contracts with clear allowed files and non-goals.
- **Keep the desktop quiet:** aim for **≥10 GB free RAM** and healthy commit
  headroom; close extra browsers before long runs. One inference worker only
  (do not stack Ollama chat + bench `llama-server` + another big model).
- **Prompt shape:** one clear contract, pinned revision, allowed files only,
  ask `needs_context` instead of guessing. Prefer JSON/`files` maps for patch
  drafts. At most **one** targeted repair, then supervisor takeover.
- **Review before trust:** read every returned file; run hash-gated checks only
  after review. Case fractions alone are not acceptance.
- **Bench path (not stock Ollama):** see `docs/agent-guide.md` and
  `python -m local_worker_bench` / `scripts/draft_job.py` with a running owned
  API — that path has .66 RAM guards the stock app does not.

## Project context

The active product is **single-machine OS-managed paging**, not a cluster.
Read `docs/guide.md`, `docs/agent-guide.md`, and `docs/evaluation.md` first.
Historical cluster/LAN evidence is indexed in `research/README.md`; do not
restore those defaults or use them as current machine configuration.

Use synthetic fixtures. Never commit weights, credentials, application data or
private logs. Published benchmark evidence must retain failures and source hashes
and remove private paths.

Reading context does not authorize inference. An explicit current-task request
does; respect any later pause. Four CPU threads, one inference worker at a time.
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
