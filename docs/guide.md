# One computer, OS-managed model paging

The active tool serves bounded local coding drafts. It uses llama.cpp CPU kernels
and read-only GGUF mappings. Windows brings needed weight pages into RAM and can
retain useful pages for reuse. The whole model need not be resident at once.
The correct term here is **paging**, not pagination (which divides documents).

## What a model is, and what gets divided

A checkpoint contains learned numerical arrays, plus metadata needed to execute
the model. A tokenizer maps text to token IDs. The engine computes through model
layers, retains live activations/cache/recurrent state and predicts output tokens.
Qwen3-Coder-Next is a mixture-of-experts model: selected experts do work per token,
but all stored weights still need an access strategy.

The OS manages small memory pages, not independent models. Our planner reports
`ceil(weight_bytes / residency_budget)` only as an illustrative capacity ratio;
it **creates zero physical model slices**. GGUF file parts are storage packaging,
not RAM partitions. No merging of independent mini-model answers occurs.

## Automatic budget

`paging-plan` detects Windows/Linux, physical/available RAM, CPU count and OS page
size. It budgets the smaller of .66 times available RAM, available minus an OS
reserve, and 24 GiB (the current prototype ceiling). Reserve is the larger of
2 GiB or 10% of physical RAM. It refuses budgets below 1 GiB. The API recalculates
at admission, not every token, so another application can still change pressure.

On our 32 GB machine with roughly 15 GiB available, that suggests around 10 GiB
of process working set. It is not allocating 66% of the model or 66% of total RAM.
Monitor private bytes, host RAM and commit too; RSS is not total file-cache cost.
The defaults remain four threads, 2048 context, one worker, bounded output/time,
6 GiB private-memory ceiling and process cleanup after each request. None of
this changes the global Windows pagefile or closes desktop applications.
The .66 value is an upper starting point, not a target to force. The first
Qwen3.8 Q4 smoke hit the reserve at that fraction; a separately recorded .40
trial passed with more headroom (host availability also changed). Preserve the
failed attempt and lower the budget rather than disabling the reserve guard.
New planner-generated profiles also render and tokenize chat before generation,
reserving the requested output allowance plus a 64-token template margin.
Oversized packets fail with HTTP 413 rather than silently consuming output room.
The margin is a conservative admission check, not a universal tokenizer guarantee.

```powershell
python -m local_worker_bench paging-plan --manifest results/model-cache/qwen3-coder-next-q4/verified-manifest.json --backend results/layer-stream-backend/build/bin/Release/llama-server.exe --output results/paging.json
python -m local_worker_bench serve-offload --config results/paging.json --port 11438 --results results/paging-api
```

No model is loaded by planning or starting the API. The manifest must record
completed SHA verification; planning checks current sizes and GGUF headers rather
than rereading 48 GB for every request. Backend build: `scripts/build_paged_backend.py`
uses a pinned llama.cpp source and Windows bulk-prefetch-disable patch. The earlier
`layer-stream-backend` also works with `layer_stream:false`; its explicit eviction
hook stays disabled. Installed Ollama is not modified.

## API and Ollama

```json
{"model":"qwen3-coder-next:q4_K_M","messages":[{"role":"user","content":"Return JSON with source for this bounded task..."}],"stream":false,"think":false,"format":"json","options":{"num_thread":4,"num_ctx":2048,"num_predict":512}}
```

Send that body to `POST http://127.0.0.1:11438/api/chat`. `GET /health`,
`/api/version`, `/api/tags` and `/api/ps` provide read-only status. Unload uses
`POST /api/generate` with `{"model":"REGISTERED_ALIAS","keep_alive":0}`.
The facade starts/stops an owned native process per request; replies include
timings and a `resource_receipt` ID. It refuses tools, images, streaming and
unregistered models. There are no public `/jobs/*` or agent-provider routes.
New planner/campaign profiles set `capture_partial:true`. The public request
still uses `stream:false`, but the facade reads native SSE internally and flushes
`partial.txt` and `events.jsonl` under each resource-receipt directory as content
arrives. A timeout/disconnect retains that prefix and records incomplete status.
Partial text is diagnostic data, not code eligible for grading or application.
The final answer and native timing/usage still use the normal complete response.
The request deadline now includes model loading and preflight; clients receive
a short transport grace so the server can return its timeout receipt.
Supported generation options are `num_thread`, `num_ctx`, `num_predict` and
`temperature:0`. Threads/context must match the profile; only the output allowance
can be reduced per call. Other sampler settings are rejected, not silently ignored.

**We are not writing an inference engine from scratch.** llama.cpp runs the
model; our small API handles profiles, budgets, receipts and lifecycle. The
Ollama-shaped subset keeps existing helper clients useful. This does not make
it stock Ollama, a complete Ollama implementation, or a direct Claude/Codex
provider replacement. Keep the hosted model as supervisor and call the helper.
The supervisor needs a shell on this PC or an authorized private connection.
A cloud container's `127.0.0.1` points to that container, not this computer.
This setup opens no public listener, tunnel or firewall rule.

Stock Ollama supports GGUF imports, but import alone does not install our owned
process budget/watchdog policy. Its scheduler/backend behavior is version-specific;
the current 80B low-residency path is measured through our facade, not stock Ollama.
Future Ollama testing should use an isolated profile and compare actual memory,
quality and cleanup before switching. [Official import documentation](https://github.com/ollama/ollama/blob/main/docs/import.mdx).

## Linux and WSL

Linux has mmap/page cache/reclamation too. File-backed clean weights can be
reread from the GGUF without swap; private runtime memory is a separate concern.
Cgroup v2 budgets charge more than process RSS, including file cache; a Windows
working-set number is not an equivalent Linux limit. The present planner detects
Linux, but the hard limit remains Windows-specific. Non-Windows operation requires
explicit `--monitored-only` and is not qualified as a constrained-memory result.
The planner does not yet incorporate nested/container cgroup headroom.

WSL uses a VM with its own overhead and possible host/guest cache interactions.
This PC currently exposes only Docker's internal WSL distribution. We do not
install a second distro or change WSL limits in the first phase. Next phase:
native Linux or a dedicated user-owned WSL distro, constrained cgroup tests,
same prompts/checks and whole-host measurements. A Windows client may then use
the Linux API through a validated local connection; transport success alone
does not validate model correctness or memory limits.

## Does every model work?

No universal guarantee. The backend must support the architecture, quantization,
tokenizer and chat template. Quantized GGUF mappings help weight capacity; runtime
workspace and live state still need memory. Dense models may reread many more
weights per token than MoE. GPU buffers, multimodal projectors and remote-only
models require different treatment. This study is CPU text-only; disk speed,
context and precision can dominate latency. No 66% heuristic guarantees success.

See [evaluation](evaluation.md) for actual results and pending comparisons,
[agent practice](agent-guide.md) for prompts, and [historical research](../research/README.md)
only when deeper prior experiments are relevant.
