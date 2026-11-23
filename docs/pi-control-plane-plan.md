# Raspberry Pi control plane: no inference

Status: deployment plan, not a deployed or measured physical cluster.
The Pi is an additional controller, outside the three compute-node RAM budgets.
See [API ownership and model splitting](llama-api-and-cluster.md) for a reusable
write-up distinguishing native llama.cpp serving from our gateway and future jobs.

## Placement

```text
Coding assistant / developer
          | authenticated request
          v
Raspberry Pi: API gateway + job records + Ansible over SSH
          | fixed upstream (prefer an SSH tunnel)
          v
Worker 1: inference coordinator + its model partition
          | private RPC / activation transfers
          +-------------------+
          v                   v
Worker 2: partition     Worker 3: partition
```

The Pi never loads weights, tokenizes prompts, runs tensor operations, or
participates in the inference graph. Even sampling and model scheduling inside
the inference engine belong on worker 1. If the workers are unavailable, the Pi
returns an error; there is no local-model fallback. Its RAM is not pooled into
the model capacity calculation.

Use a 64-bit Linux installation. A Pi with 2–4 GB RAM is a reasonable starting
target for this lightweight role, subject to measurement; no Pi capacity or
throughput result has been established here. Prefer reliable storage for job
records and wired networking. Avoid writing large prompt/output logs to an SD
card. Keep model downloads and caches on the compute workers' local SSDs.

## API and job ownership

The repository's `serve-gateway` command is a small HTTP forwarding prototype:

```sh
python -m local_worker_bench serve-gateway \
  --upstream http://127.0.0.1:11447 \
  --token-file /etc/local-worker/gateway.token
```

Port 11447 represents an SSH local forward to worker 1's loopback API. The
gateway defaults to loopback as well: access it through a client SSH tunnel,
or explicitly configure a private address and a protected LAN/VPN. Bearer
authentication alone does not encrypt HTTP. Store the token outside git with
mode 0600. Do not put it in command-line arguments.

Implemented subset: authenticated `/api/chat`, unload via `/api/generate`, and
read-only `/api/tags`, `/api/ps`, `/api/version`; unauthenticated `/health`
reports the gateway role. This is not a full Ollama replacement. Streaming,
durable queued jobs, and deployment services still need implementation and
tests. The prototype permits one chat at a time and rejects another with 429.

For overnight work, add a SQLite job ledger on the Pi, with job ID, immutable
input hash, model/backend revision, state, attempt number, worker receipt ID,
and timestamps. Keep large artifacts on a worker and record their hashes and
locations. Accept a job quickly, then expose status/results by ID; do not rely
on one HTTP connection surviving all night. Suggested states:
queued, admitted, running, needs-review, passed, failed, cancelled.
Use leases/heartbeats to distinguish a failed worker from a slow request.
After an interrupted generation, restart a bounded attempt; saved text is not
a resumable KV cache. Preserve first-pass and repair attempts separately.

## Ansible rollout TODO

Ansible runs on the Pi. Use disjoint inventory groups `controllers` and
`compute_workers`; mark worker 1 as `inference_coordinator`. Never target an
inference role at `all`. Add assertions that the controller is not in the
compute group and that the compute group has exactly three members.

1. Inventory actual hosts, CPU architectures, RAM, free SSD space, SSH users,
   and network throughput. Choose explicit per-worker memory reserves.
2. Controller role: Python, Ansible, gateway code, secret-file permissions,
   SSH keys/known hosts, job ledger, and service definitions. No Ollama,
   PyTorch, inference executable, model download, or model directory on Pi.
3. Compute role: build a pinned CPU backend for each machine's architecture,
   verify artifact hashes, install only the required model data, configure
   dedicated users and service limits, and expose RPC only over restricted
   private connections. No automatic OS swap/pagefile changes.
4. Coordinator role on worker 1: model placement, memory admission, API,
   request timeout, one active inference job, cancellation and receipts.
   Budget its extra coordination/runtime memory before assigning layers.
5. Add SSH tunnel and gateway services with restart limits. A reboot may
   restore idle services, but must not silently replay an inference job.
6. Dry-run inventory and Ansible checks, then deploy controller only. Verify
   a missing worker produces an error with no controller inference process.
7. Deploy workers; test a small model and node-loss/cancellation behavior.
   Only then admit a larger model. Record exact engine/model revisions,
   memory peaks, disk I/O, time to first token, total time and reviewed scores.

Ansible provisions and starts services; it does not split a model. The native
inference backend or explicit layer-streaming implementation owns that work.
Ray can be an optional Python job-dispatch layer later, but it is not required
on the Pi and does not make ordinary model code distributed automatically.

## Three-worker capacity experiments

These are planning budgets, not measured fit guarantees. RAM figures below
are GiB; runtime, KV/state caches, imbalanced layers and coordinator overhead
must fit inside the inference budget, not just the weight files.

| Physical RAM per worker | Initial inference budget per worker | Total budget | Initial experiment |
| --- | --- | --- | --- |
| 8 GiB | 4 GiB | 12 GiB | Small resident control, then explicit disk-backed partition streaming |
| 16 GiB | 10 GiB | 30 GiB | 30B Q4 candidate, validate placement/runtime headroom |
| 32 GiB | 24 GiB | 72 GiB | 80B Q4 candidate, validate placement/runtime headroom |

Our artifact sizes are approximately 17.28 GiB for the cached 30B Q4 and
45.09 GiB for the pinned 80B Q4 download. Thus three 8 GiB machines do not
make either model resident within the proposed budget. Three 16 GiB machines
still require disk backing for the 80B candidate. Merely splitting GGUF files
or enabling RPC does not establish bounded-memory disk offload.

Start with one request and four CPU threads per worker, a fixed small context,
and explicit output limits. Compare identical coding tasks and reviewed tests
against the smaller resident baseline. Increase model size only when its
measured quality improvement justifies its latency and failure rate.
Local multi-process tests share a host's OS and cache; they do not establish
performance or memory behavior on three independent low-RAM computers.

## Acceptance checks for the Pi

- Inventory and service definitions place every inference service on workers.
- No model files or inference dependencies are installed on the controller.
- Unreachable workers fail closed; no process or model starts on the Pi.
- Authentication, concurrency rejection and cancellation are verified.
- Job state survives a Pi reboot without duplicate automatic execution.
- Controller memory/storage use stays bounded while workers run overnight.

## Primary references

- [Ansible control and managed nodes](https://docs.ansible.com/projects/ansible/latest/intro_installation.html)
- [llama.cpp RPC setup and limitations](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md)
- [llama.cpp server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
