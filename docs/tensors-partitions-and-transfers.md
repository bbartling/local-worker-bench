# Tensors, cutting lines and transfers

The [PDF report](reports/local-ai-cluster-explained.pdf), pages 13-17, includes
tensor illustrations, exact four-stage cuts, and sequence diagrams for both
execution paths. Editable appendix: [cluster_report_appendix.py](../scripts/cluster_report_appendix.py).
Building the report does not import PyTorch or start inference.

## Which Python file cuts our model?

[demo.py](../examples/sharded-qwen/demo.py), `prepare()`, reads the layer count
and computes `range(i*n//4, (i+1)*n//4)` for each of four groups. For the tested
Qwen3-0.6B configuration, n=28: layers 0-6, 7-13, 14-20 and 21-27. It selects
matching state-dictionary entries and writes `weights-0.pt` through `weights-3.pt`.
The first stage includes embedding; the last includes final normalization/head.
Tied embedding/head weights are deliberately duplicated. `manifest.json` records
the groups. This rule balances layer counts, not exact bytes or runtime peaks.

Preparation first loads the complete small model and computes reference outputs;
it is not an arbitrary-size low-memory converter. `stage()` constructs the
assigned PyTorch modules on the meta device, loads CPU weights, and computes in
inference mode. Every stage is compared with the reference boundary. The last
stage compares logits and selects the next token using argmax.

Four-stage assumptions exist beyond the formula: last-stage tests use index 3
and loops/parser choices use four. Three-worker adaptation is still required.

## What is a tensor here?

A tensor is an array of numbers with a shape, dtype and device. In our demo:

- `input_ids`: integer token IDs, shape `[1, sequence_length]`.
- `hidden`: intermediate activations, shape `[1, sequence_length, 1024]`.
- `logits`: next-token vocabulary scores, shape `[1, 151936]`.
- Weights: learned arrays belonging to the stage's modules.

PyTorch stores and computes these arrays; Transformers supplies the Qwen modules
and tokenizer. There is no training or weight update. The native llama.cpp path
uses ggml C/C++ tensors instead of PyTorch for inference.

## Implemented Python HTTP proof

[cluster_demo.py](../examples/sharded-qwen/cluster_demo.py), `run()`, starts four
loopback node processes with isolated weight folders. Its coordinator sends
`POST /stage` with `step`, `input_ids` and (after stage 0) `state`.

```text
coordinator -> stage 0: input IDs
coordinator <- stage 0: hidden + IDs in base64-encoded .pt bytes
coordinator -> stage 1: forwards the received state
coordinator <- stage 1: updated hidden state
coordinator -> stage 2 -> coordinator -> stage 3
coordinator <- stage 3: logits bytes + next_token + checks
```

`node()` decodes the state into a local file, calls `demo.stage()`, then serializes
the output and includes a SHA-256 digest. The coordinator checks the returned
bytes against that digest and saves/relays them. The digest is not authentication
or proof of safe untrusted deserialization. Use trusted local artifacts only.
The proof has no KV cache: every output token recomputes the entire prefix.
It is HTTP/TCP with JSON/base64, not native ggml RPC, and not four physical hosts.

## Proposed native RPC path

[offload_api.py](../local_worker_bench/offload_api.py), `Manager._chat()`, currently
starts a local-only llama-server. Its native `/v1/chat/completions` request does
not invoke `demo.py` or PyTorch. Remote placement must be added and verified.

At our pinned backend revision, `src/llama-model.cpp` determines layer placement
from normalized explicit split proportions or device free-memory reports. The
input layer and output placement receive separate handling. These are load-time
assignments, not cuts at arbitrary GGUF byte offsets or exact memory quotas.

Native `ggml/src/ggml-rpc/ggml-rpc.cpp` implements binary operations for discovery,
buffers, tensor data and graph execution. Worker 1 coordinates worker 2/3 devices.
Loading assigned weights and transferring runtime activations are different
phases. Exact commands, routing, reuse and copies depend on the graph/scheduler;
the report's native arrows are conceptual, not packet traces. There is no
torch.save/base64/POST-stage protocol on this path.

Measure actual per-host placement, startup peaks, traffic, cache/state ownership,
cleanup, failure handling and coding quality before claiming a verified cluster.

Source revision: `94f3af3d09e74a0fb35f703194318d3b4037714a`.
See [pinned layer placement](https://github.com/ggml-org/llama.cpp/blob/94f3af3d09e74a0fb35f703194318d3b4037714a/src/llama-model.cpp)
and [pinned RPC implementation](https://github.com/ggml-org/llama.cpp/blob/94f3af3d09e74a0fb35f703194318d3b4037714a/ggml/src/ggml-rpc/ggml-rpc.cpp).
