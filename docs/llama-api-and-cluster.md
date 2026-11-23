> Historical research: retained for reproducibility and AI context. The active tool is single-machine OS paging; start at [the current guide](guide.md). Old paths/settings describe prior experiments. The old cluster PDF was replaced by `reports/os-paging-guide.pdf`.

# Writing about the API and model cluster

## A reusable description

> We are building a local coding-helper experiment using three CPU machines.
> Worker 1 hosts the application API, stores the complete checkpoint on SSD,
> and runs the native inference coordinator plus its own model allocation.
> Workers 2 and 3 provide remote compute through llama.cpp RPC. The client sends
> one request and receives one answer. The gateway prototype and small numerical
> proof exist; a physical three-worker large-model deployment is not yet verified.


## Does llama.cpp handle all our API needs?

It can supply the **model-serving API**, which means we do not need to write a
new token-generation HTTP server. Upstream `llama-server` provides OpenAI-style
`POST /v1/chat/completions`, streaming and structured JSON support; behavior
depends on the model, template and build. See the [official server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

That is different from our project's complete service. The worker 1 gateway handles
entry-point access and forwarding. Ansible provisions machines. Durable
overnight job IDs, job storage, retry policy, worker leases, and reviewed coding
results remain application work. They are not implemented by our gateway today.

Also distinguish **Llama**, a model family, from **llama.cpp**, the inference
software. llama.cpp can execute supported architectures from other families,
including appropriate Qwen models; it is not restricted to Llama weights.

## Three APIs/transports with different contracts

| Interface | Purpose | Repository status |
| --- | --- | --- |
| Worker 1 gateway `/api/chat` | Authenticated Ollama-shaped client entry point | Implemented forwarding prototype; synchronous, plain text, no streaming |
| Worker facade `/api/chat` | Enforce registered profiles, resource observation and receipts | Implemented; starts one owned local native process per request |
| Native `/v1/chat/completions` | Model inference HTTP endpoint behind the facade | Used internally; the worker 1 gateway does not expose `/v1/*` |
| Native ggml RPC | Coordinator-to-remote-device computation | Proposed cluster path; not wired into the current facade configuration |
| Proposed `/jobs/*` | Durable overnight submission, status and results | Not implemented |

The current path is:

```text
client -> worker 1 gateway /api/chat -> local worker facade /api/chat
       -> local llama-server /v1/chat/completions -> response back
```

The cluster extension would keep that client contract but replace the local
execution placement with a verified RPC-aware backend on worker 1:

```text
client -> worker 1 API / inference coordinator
                         <-> native RPC devices on workers 2 and 3
       <- final text, timings and receipt
```

Native RPC is not simply three web servers sending English answers to one
another. It transports numerical computation through the engine. Our educational
layer pipeline illustrates dependencies; it is not a claim that native RPC
always transfers directly from worker 1 to 2 to 3 in that exact order.

## Sliced models: the precise claim

### Installed processes and network calls

All three workers need a compatible native llama.cpp build, compiled for their
own CPU architecture with RPC support. Suggested Linux layout (not deployed):

| Host | Installed executable/services | Data and responsibility |
| --- | --- | --- |
| Worker 1 | `/opt/llama.cpp/bin/llama-server`; Python gateway and facade | Full checkpoint under `/srv/local-worker/models/`; model coordination and a smaller local compute allocation |
| Worker 2 | `/opt/llama.cpp/bin/ggml-rpc-server` | CPU device, assigned live tensors/state; optional RPC disk cache |
| Worker 3 | `/opt/llama.cpp/bin/ggml-rpc-server` | CPU device, assigned live tensors/state; optional RPC disk cache |

```text
Client
  | HTTP POST /api/chat (protected/tunneled)
  v
WORKER 1
  gateway :11434
     | local HTTP POST /api/chat
  facade :11437
     | local HTTP POST /v1/chat/completions
  llama-server :ephemeral  <--- complete GGUF checkpoint on SSD
     | native ggml RPC              | native ggml RPC
     v                              v
WORKER 2                         WORKER 3
  ggml-rpc-server :50052           ggml-rpc-server :50052
     | local kernels                 | local kernels
     v                               v
  CPU / assigned tensors          CPU / assigned tensors
```

Ports above are illustrative. Port 50052 can be reused because each RPC process
is on a different host. Our current facade chooses an ephemeral native HTTP port.
The coordinator will need a verified remote-device placement profile; its current
local-only flags must change deliberately before this becomes a working cluster.
Installing RPC binaries alone does not enable remote execution. RPC is a native
binary protocol, not `/api/chat` or `/v1/chat/completions` on remote workers.
Results return to the coordinator, then through the facade/gateway to the client.
Remote workers need not each run a public inference HTTP server or independently
download the full checkpoint; their buffers and optional caches still need space.

In the current gateway, legacy fields named `controller_inference:false` describe
the HTTP forwarding process. Worker 1 also runs a separate inference process;
those fields do not describe all activity on the physical machine.

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
memory admission and correctness. Ray is optional future orchestration, not an implemented dependency or
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
[Three-worker plan](three-worker-cluster-plan.md) records deployment TODOs and capacity budgets.

## Is this similar to enterprise data-center serving?

Yes at the architecture level: a serving endpoint can coordinate distributed
model execution while the client sees one response. For a concrete documented
example, [vLLM supports tensor/pipeline parallel serving and multi-node execution](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/).
Its distributed runtime can use Ray. This does not mean an enterprise uses
llama.cpp RPC, mpi4py, or our API implementation.

For our design comparison, a production service would also need explicit
availability, access-control, scheduling and observability requirements. Larger
deployments may separate API and compute roles again for those reasons. Our
initial worker 1 deliberately combines them and is a single point of failure.
Three low-RAM CPU PCs are a useful experiment, not a data-center performance
equivalent. Network speed and repeated disk reads still determine practicality.
