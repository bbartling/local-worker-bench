# Cursor handoff - local worker research and patch benchmark

## Current instruction: Suite-3 pilot CLOSED — keep winner only

**Winner:** `qwen38-standard-q4` (Qwen3.8-27B standard Q4_K_M,
prithivMLmods rev `3ccdd49b…`, ~15.7 GB GGUF under
`results/model-cache/qwen38-standard-q4/`). Sole Suite-3 accept: telemetry 28/28.
Paper: `docs/reports/os-paging-research.pdf`.

**Cleanup (25 Nov 2026):** non-winner GGUF caches removed from
`results/model-cache/` (Coder-Next Q4/F16/BF16, Qwen FP16/BF16, Unsloth UD-Q4).
Stock Ollama import: `pwsh scripts/import_winner_to_ollama.ps1` → tag
`qwen38-standard-q4`. 2h wake loop stopped. Do not re-download deleted formats
unless the user explicitly asks.

Repository: `C:\Users\ben\Documents\local-worker-bench`.
Remote: https://github.com/bbartling/local-worker-bench, default branch **main**.
User wants changes committed/pushed directly to main when requested.

## Product and boundaries

Single-machine CPU inference with a full GGUF on SSD and OS-managed paging.
The local Ollama-shaped API wraps a pinned llama.cpp worker; stock Ollama is a
separate app (winner tag above). Hosted supervisor owns planning, review, tests
and acceptance. Drafts are data only.

Host: Intel i7-9700, 8 logical CPUs, 32 GiB RAM, no discrete GPU. Windows measured.
One worker at a time. Defaults for new project-patch work: 120 min, .66 RAM,
~66% threads (5), 2048 output tokens, Suite 3.

Native executable: `results/layer-stream-backend/build/bin/Release/llama-server.exe`.
Runtime results, native binaries and weights are gitignored.

## Evidence pointers

- Matrix: `results/suite3-six-matrix-20261124-run2/` (graded; 1 accept / 5 near-miss / 12 incomplete).
- Quiet export near-miss: Coder Q4 reached 27/28 after repair (not accept).
- Tick notes: `results/suite3-six-matrix-20261124-run2/TICK-NOTES.md`.

Reading this handoff does not authorize new inference or downloads.
