# Writing about the API and model cluster

## A reusable description

> We are building a local coding-helper experiment with a Raspberry Pi as the
> API/control plane and three CPU machines as inference workers. llama.cpp is
> the proposed native model-serving engine. Its RPC backend can use remote
> compute devices for supported models, allowing one model's work to span
> several machines. The client still makes one request and receives one answer.
> This is experimental: our repository has a small four-process numerical proof
> and a single-worker API prototype, not a verified three-machine large-model
> deployment. The Pi never loads weights or performs inference.

## Does llama.cpp handle all our API needs?

It can supply the **model-serving API**, which means we do not need to write a
new token-generation HTTP server. Upstream `llama-server` provides OpenAI-style
`POST /v1/chat/completions`, streaming and structured JSON support; behavior
depends on the model, template and build. See the [official server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

That is different from our project's complete service. The Pi gateway handles
entry-point access and forwarding. Ansible provisions machines. Durable
overnight job IDs, job storage, retry policy, worker leases, and reviewed coding
results remain application work. They are not implemented by our gateway today.

Also distinguish **Llama**, a model family, from **llama.cpp**, the inference
software. llama.cpp can execute supported architectures from other families,
including appropriate Qwen models; it is not restricted to Llama weights.

## Three APIs/transports with different contracts

| Interface | Purpose | Repository status |
| --- | --- | --- |
| Pi `/api/chat` | Authenticated Ollama-shaped client entry point | Implemented forwarding prototype; synchronous, plain text, no streaming |
| Worker facade `/api/chat` | Enforce registered profiles, resource observation and receipts | Implemented; starts one owned local native process per request |
| Native `/v1/chat/completions` | Model inference HTTP endpoint behind the facade | Used internally; the Pi gateway does not expose `/v1/*` |
| Native ggml RPC | Coordinator-to-remote-device computation | Proposed cluster path; not wired into the current facade configuration |
| Proposed `/jobs/*` | Durable overnight submission, status and results | Not implemented |

The current path is:

```text
client -> Pi /api/chat -> worker facade /api/chat
       -> local llama-server /v1/chat/completions -> response back
```

The cluster extension would keep that client contract but replace the local
execution placement with a verified RPC-aware backend on worker 1:

```text
client -> Pi -> worker 1 API / inference coordinator
                         <-> native RPC devices on workers 2 and 3
       <- Pi <- final text, timings and receipt
```

Native RPC is not simply three web servers sending English answers to one
another. It transports numerical computation through the engine. Our educational
layer pipeline illustrates dependencies; it is not a claim that native RPC
always transfers directly from worker 1 to 2 to 3 in that exact order.

## Sliced models: the precise claim

The [upstream RPC guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md)
describes remote CPU devices and weight/cache distribution, with configurable
placement. This supports the idea of executing one compatible model across
multiple machines. The coordinator reads the checkpoint and arranges placement;
we do not manually cut arbitrary bytes into independently runnable mini-models.

A multi-file GGUF is packaging, not a machine assignment. Distributed execution
still needs supported operators, compatible builds, enough per-node memory,
and correct runtime state. Stock RPC's disk cache reduces repeated tensor
transfers during loading; it does not establish bounded-memory layer swapping.
The upstream RPC implementation is experimental and must remain on restricted
private/tunneled connections.

## Do we use mpi4py or Ray?

No mpi4py dependency or MPI ranks are used. The small Python proof uses HTTP/TCP;
the planned native cluster uses ggml RPC. mpi4py could carry arrays in another
custom implementation, but we would still own partitioning, cache/state handling,
memory admission and correctness. The Pi would remain outside the inference
ranks. Ray is optional future orchestration, not an implemented dependency or
automatic model splitter. Neither library is necessary just to call a native
model-serving API.

## What to say about compatibility and hardware

Say **supported model/build/hardware combination**, not “every model.” Open
weights, an understood architecture and a supported quantization format are
prerequisites. Hybrid, recurrent, expert and multimodal models need specific
support. A hosted model with no available checkpoint cannot be partitioned here.

Three 8 GiB workers are not equivalent to a single unrestricted 24 GiB machine.
Each worker needs its own runtime and OS reserve, and the coordinator needs extra
space. Larger resident models may fit across 16 or 32 GiB workers, but our actual
capacity and reviewed quality must be measured. Slow operation does not remove
memory limits or guarantee a better coding result.

For request examples and the exact current parameter limits, use the
[PDF report](reports/local-ai-cluster-explained.pdf) and
[experimental API notes](offload-experiments.md). The
[Pi plan](pi-control-plane-plan.md) records deployment TODOs and capacity budgets.
