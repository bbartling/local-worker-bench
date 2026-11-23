# Three-worker CPU cluster: API and coordinator on worker 1

Status: deployment plan, not a deployed or measured physical cluster.
The [80B single-PC disk-backed trials](benchmarks/2026-11-23-sequential-streaming.md)
now provide coding/memory evidence; remote RPC disk backing remains future work.
We have now [measured three local native RPC devices](benchmarks/2026-11-23-local-rpc.md)
on one PC with the cached 4B model. This does not establish physical-node isolation.
This replaces the separate-controller design. There are three computers total.
See [API ownership and model splitting](llama-api-and-cluster.md) for the reusable write-up.

## Placement

```text
Coding assistant / developer
          | authenticated API over a protected connection
          v
Worker 1: gateway + worker API + job records (planned)
          full checkpoint on SSD + native inference coordinator
          local model allocation with extra runtime/OS headroom
          | private native RPC
          +-------------------+
          v                   v
Worker 2: RPC compute   Worker 3: RPC compute
```

Worker 1 downloads and verifies the complete checkpoint to local SSD. Disk
capacity for that checkpoint is different from resident RAM: distributed
placement may avoid keeping all weights resident on worker 1, but loading
transients, coordination buffers, cache and runtime still require measurement.
Keep room for partial downloads, the verified files, backend builds and receipts.
Do not assume three equal layer counts or three equal memory allocations.

Workers 2 and 3 expose compatible compute devices to the coordinator. Native
RPC placement is not manual byte slicing or three independently generated
answers. Tensor caches on remote workers can also consume disk space. File
sharding alone does not distribute execution or guarantee bounded-memory loading.

## API and job ownership

Run the existing authenticated gateway on worker 1, with its fixed upstream
pointing to the loopback worker facade on the same machine:

```sh
python -m local_worker_bench serve-gateway \
  --upstream http://127.0.0.1:11437 \
  --token-file /etc/local-worker/gateway.token
```

The default gateway address is loopback port 11434. Use a client SSH tunnel, or
explicitly configure a private address with protected transport. A Bearer token
does not encrypt plain HTTP. Keep the token outside git with mode 0600.

The gateway only forwards HTTP; a separate native process on the same host
performs inference. Existing response fields `controller_inference:false` and
`inference_on_controller:false` describe the forwarding implementation, not an
assertion that the entire physical host does no inference. They are legacy
names from the earlier topology.

Current subset: `/api/chat`, unload-only `/api/generate`, authenticated read-only
`/api/tags`, `/api/ps`, `/api/version`, and public local `/health`. One active
gateway chat; another gets 429. No streaming, durable queue or automatic retry.
The facade currently launches a single local native process; remote RPC options
and a verified cluster placement profile still need implementation.

For overnight work, add a SQLite ledger on worker 1 with job ID, immutable input
hash, model/backend revisions, state, attempt, receipt ID and timestamps. Large
artifacts stay on worker storage. Proposed states: queued, admitted, running,
needs-review, passed, failed, cancelled. Use leases and heartbeats. Restart an
interrupted generation as a bounded attempt; saved text is not a KV checkpoint.
Preserve first-pass and repair results separately. Worker 1 is a single point
of failure for the API and coordinator in this initial design.

## Ansible rollout TODO

Run Ansible from a Linux worker 1 or a separate developer laptop. That machine
is the Ansible control node as a software role, not an extra inference host.
Inventory `compute_workers` has exactly three hosts; `inference_coordinator`
selects exactly worker 1, which is also in the compute group.

1. Record each host's architecture, physical RAM, available SSD capacity, SSH
   access and network throughput. Assign explicit OS/runtime reserves.
2. Build and verify a pinned compatible CPU/RPC backend on each architecture.
   Configure dedicated users, services and private/tunneled RPC access. Do not
   silently change swap/pagefiles or replay jobs on service restart.
3. On worker 1 only, download and verify the complete checkpoint, register
   profiles, deploy the facade/gateway, and later add durable job tracking.
4. Account for worker 1's extra responsibilities before assigning its model
   share. Add coordinator-only API/model roles with assertions about inventory.
5. Dry-run configuration checks; deploy idle services without launching a job.
   Verify authentication, unavailable-worker behavior and port restrictions.
6. Run a small model across three workers; compare reference results and test
   cancellation, worker loss and cleanup. Only then admit a larger model.
7. Record exact model/backend revisions, loading peaks, resident/private memory,
   disk/network I/O, first-token latency, total runtime and reviewed quality.

Ansible installs/configures services; the native engine owns tensor placement.
Ray is optional future Python job orchestration, not a required dependency or
an automatic model splitter. mpi4py is not used by the current implementation.

## Capacity experiments

Planning budgets in GiB, not measured fit guarantees. All inference state and
workspace must fit along with weights. Worker 1 should start with a smaller
allocation than the other workers; the reductions below are illustrative.

| RAM per host | Worker 1 starting budget | Workers 2 / 3 each | Aggregate budget | Candidate experiment |
| --- | --- | --- | --- | --- |
| 8 GiB | 3 GiB | 4 GiB | 11 GiB | Small resident baseline; explicit disk-backed research for larger weights |
| 16 GiB | 8 GiB | 10 GiB | 28 GiB | 30B Q4 capacity candidate; verify runtime and uneven placement |
| 32 GiB | 20 GiB | 24 GiB | 68 GiB | 80B Q4 capacity candidate; verify loading peaks and state |

Cached 30B Q4 weights are approximately 17.28 GiB; pinned 80B Q4 artifacts total
45.09 GiB. The 8 GiB tier cannot hold either within these budgets. The 16 GiB
tier still needs disk backing for 80B. Native RPC alone does not implement the
proposed bounded-memory layer swapping. Do not advertise these as tested fits.

Start with one active request, four inference threads per worker, fixed small
context and bounded output. Compare identical reviewed tasks with a smaller
resident baseline. Single-host multi-process tests share OS cache and do not
establish physical-cluster performance or low-RAM capacity.

## Acceptance checks

- Worker 1 holds a verified complete checkpoint on SSD; loading peaks respect reserves.
- Only worker 1 runs the application API/coordinator; private RPC is limited to approved peers.
- Model placement leaves extra headroom on worker 1; all three hosts are monitored.
- Unknown models, missing weights and failed workers produce errors without silent fallback.
- Authentication, cancellation, concurrent-request rejection and owned-process cleanup work.
- A worker 1 reboot does not silently duplicate or replay overnight work.
- Three-node correctness is established before claiming larger-model quality or speed.

## Primary references

- [Ansible control and managed nodes](https://docs.ansible.com/projects/ansible/latest/intro_installation.html)
- [llama.cpp RPC](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md)
- [llama.cpp serving](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
