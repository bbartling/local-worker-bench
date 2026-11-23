# Sequential resident-layer streaming on this Windows PC

Completed measurements: [80B coding, memory policies and supervised repair](benchmarks/2026-11-23-sequential-streaming.md).

This experiment uses the cached quantized GGUF files directly. It does not
convert them to FP32/PyTorch, allocate all weights as private RAM, or create a
second 45 GiB weight copy. The native llama.cpp engine keeps the model's virtual
file mappings and attention/recurrent state; an opt-in callback changes when
weight pages remain in this process's working set.

This is **resident-page eviction**, not torch module deletion or unmapping the
model. OS standby/file cache can retain pages. Process RSS is not total physical
memory attributable to the model, and this is not isolated 8 GiB hardware.

## What happens for each logical decoder slice

```text
Original GGUF files on SSD (read-only, still virtually mapped)
                | page in weights as native CPU operations need them
                v
Native decoder layer i + existing activations / cache / recurrent state
                | compute finishes; backend synchronizes
                v
Callback at l_out-i
  inspect only model weight tensors named blk.i.*
  require their storage to be file-mapped (MEM_MAPPED)
  sample weight-page residency with QueryWorkingSetEx
  call VirtualUnlock on those mapped weight ranges
  sample residency and process RSS again; append trace record
                |
                v
Layer i+1 receives the activation; live runtime state remains allocated
                |
                v
Output head -> next token -> repeat decoder passes until stop/output limit
```

The final `result_output` callback also targets non-block model weights such as
the embedding/output head. The implementation touches no global OS policy and
does not flush another application's cache. It preserves the native engine's
hybrid-state handling instead of writing a new Qwen3Next recurrent implementation.

Microsoft documents that `VirtualUnlock` on unlocked pages removes them from
the process working set while returning FALSE with `ERROR_NOT_LOCKED`. That is
the expected result here, not an unexpected OS error. We also record sampled
residency reductions, rather than trusting a flag alone. See
[the Windows API reference](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualunlock).
Sampling first/middle/last pages per weight is not an exhaustive proof about
every page or the OS's remaining cache.
The prototype reports a failed residency query as zero observations rather
than a separate query-error field; future instrumentation should distinguish
those cases. The retained RSS changes provide additional evidence for these
trials, but the sampled counters are not a formal memory-isolation proof.

## Source map

- [Native callback](../native/lwb_layer_stream_windows.h): synchronization
  boundary targets, mapped-weight selection, eviction requests, residency/RSS trace.
- [Isolated backend builder](../scripts/build_layer_stream_backend.py): reuses
  verified pinned sources, verifies the context patch site and builds separately
  from the earlier baseline. It patches scheduler callback selection in
  `llama-context.cpp`; it does not modify installed Ollama.
- [Bounded harness](../scripts/rpc_cluster_demo.py): one explicit CPU job,
  fixed context/budgets, process working-set cap, host/private/commit watchdog,
  timeouts, saved candidates and owned-process cleanup.
- [Receipt checks](../local_worker_bench/streaming.py): require every advertised
  decoder layer to appear, actual eviction requests, sampled residency reduction
  and no unexpected errors before claiming a verified streaming run.
- [Patch fixture](../local_worker_bench/patch_task.py) and
  [hash-gated checker](../scripts/grade_patch.py): a compact synthetic HTTP-status
  repair with 25 independent cases. Generated code must be inspected first.
- [Public evidence exporter](../scripts/export_streaming_results.py): synthetic
  responses, grades, timings and samples, plus a compressed full residency trace.

Only CPU mmap execution is tested. The earlier three-device RPC experiment is
a different path: its remote allocations are not made file-backed by this hook.
Not all architectures expose compatible graph boundary names. A completed
generation without verified layer coverage is rejected as a streaming result.

## Build and run

Prerequisites: Windows x64, the previously fetched verified backend tree,
Visual Studio 18 2026 C++ tools/CMake, Python 3.11+. Four compile/runtime threads
are the shared default. Building does not invoke a model.

```powershell
python scripts/build_layer_stream_backend.py --cmake 'C:/path/to/cmake.exe'

python scripts/rpc_cluster_demo.py --mode stream --backend-dir results/layer-stream-backend/build/bin/Release --model-file C:/path/to/cached-4b.gguf --tasks smoke --output results/my-stream-smoke

python scripts/rpc_cluster_demo.py --mode stream --backend-dir results/layer-stream-backend/build/bin/Release --model-file C:/path/to/cached-4b.gguf --tasks patch --max-tokens 128 --output results/my-stream-patch
```

For the completed, verified 80B download, supply the first split plus explicit
`--large-manifest results/model-cache/qwen3-coder-next-q4/verified-manifest.json`.
Without that admission record the harness refuses model files over 6 GiB. The
manifest records prior SHA verification; the harness checks current file sizes
and GGUF headers, not a fresh 48 GB hash scan on every request.

`--mode paged` uses the same CPU mmap backend and working-set cap but disables
the explicit per-layer eviction hook. It is an OS-managed paging control,
not a claim that the full 80B weights fit resident. Large manifests are allowed
only for these explicit CPU stream/paged modes, never the RPC practice mode.

Keep outputs separate and record first-pass grades; do not select only good
answers. Load/startup and per-request times are different. No forced cold-cache
flush is performed, so repeated runs can benefit from OS caches.

## API integration

The existing `serve-offload` API accepts a registered model profile with
`"layer_stream": true`. Point `backend_executable` at the new isolated build;
keep its normal file list, CPU thread/context/output budgets and RAM reserve.
Set `private_limit_gib` explicitly (the trials use 6 GiB) for either policy.
The [example registration](../examples/offload/layer-stream-api.example.json)
shows streamed 4B and OS-paged 80B aliases; replace its placeholder weight paths
before use. Starting the API does not start inference.
The request remains the same plain-text `/api/chat` subset. Clients cannot
silently override the server-side streaming policy or download another model.

The child process receives `LWB_LAYER_STREAM=1` only for that registered profile.
A supposedly completed request fails with HTTP 502 if its receipt does not
verify the layer eviction trace. Profiles default to false, preserving the
existing API contract. This is experimental local serving, not a background
overnight scheduler or global model-provider change.

## What counts as success

1. The small model completes and preserves its baseline answer/grade on the
   same patch prompt, with verified resident-page eviction and process cleanup.
2. The large model can load and complete bounded inference without crossing
   host memory/commit/private guards. A smoke response alone is not coding quality.
3. Inspect and grade the large model on the same task, record actual latency,
   and compare OS-managed paging where useful. Report a timeout or invalid
   answer as a failed attempt, never as a quality pass.

Slicing changes capacity and execution cost. The larger model is only “better”
to the extent that independently reviewed tasks show it. A 25-case compact patch
does not establish broad superiority or replace the separate 95-case motor/
elapsed benchmark. Full tensor spans submitted for eviction are not measured
SSD read bytes; hard-vs-soft faults and physical I/O need separate instrumentation.
