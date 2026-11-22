# Experimental CPU offload tools

These tools are opt-in research prototypes. The Pi placement and three-worker
deployment TODO are in [the control-plane plan](pi-control-plane-plan.md).
No physical three-machine cluster or large-model quality improvement is claimed.

## Contents

- `scripts/download_gguf.py`: explicit public download with pinned file sizes,
  resumable partial files and SHA-256 verification. Never inference.
- `examples/offload/qwen3-coder-next-q4.download.json`: official 80B Q4 split
  artifacts, about 48.41 decimal GB. Split files alone do not distribute inference.
- `scripts/build_paged_backend.py`: pinned llama.cpp Windows CPU/RPC build;
  a small experimental patch disables bulk mmap prefetch when requested.
  Build provenance and binaries go under ignored `results/`.
- `serve-offload`: loopback Ollama API subset; one owned native worker per
  request, resource receipts, timeout, cancellation and process cleanup.
- `serve-gateway`: lightweight authenticated forwarding for a Pi; never loads
  weights or launches inference. See the control-plane plan for its limitations.
- `examples/sharded-qwen/demo.py`: four sequential layer groups of Qwen3-0.6B,
  independently loaded and released, compared against an unpartitioned reference.
- `examples/sharded-qwen/cluster_demo.py`: four local TCP processes with isolated
  weight folders and explicit activation handoffs. This predates the requested
  three-worker deployment and still uses four stages.
- `examples/sharded-qwen/plan_27b.py`: arithmetic weight/I/O estimates only.

## Offload configuration

Create a local JSON configuration under `results/`, using paths to an already
built backend and already downloaded GGUF files. Register every split in order:

```json
{
  "backend_executable": "C:/path/to/llama-server.exe",
  "models": {
    "my-coder": {
      "files": ["C:/path/to/model.gguf"],
      "threads": 4,
      "context": 2048,
      "max_tokens": 640,
      "working_set_gib": 4,
      "reserve_gib": 6,
      "load_timeout": 180,
      "request_timeout": 600
    }
  }
}
```

```sh
python -m local_worker_bench serve-offload --config results/offload-config.json
```

Starting the API does not start inference. An explicit `/api/chat` request does.
The native binary must support the command flags used by this prototype; arbitrary
older llama.cpp/Ollama binaries are not assumed compatible. `/api/generate` only
supports unload, not generation. Streaming and tools are unsupported.

Windows mode sets a hard process working-set maximum, while a watchdog watches
host memory, process residency and private memory. This is not a physical-RAM VM
or a limit on shared OS file cache. Linux requires explicit `--monitored-only`;
that mode does not establish a hard memory cap. The special backend patch is
needed to request avoiding Windows bulk mmap prefetch; a request flag alone does
not prove the loaded binary includes it. Read the receipt and backend log.

## Small-model proof

Install the dependencies from `examples/sharded-qwen/requirements.txt` in an
isolated environment, then consult each script's `--help`. Explicit preparation
downloads the pinned public small checkpoint and creates local tensor artifacts.
Only use locally generated, trusted tensor files. FP32/FP64 expand BF16 source
weights; they do not restore information absent from those weights. Internal
normalization/rotary operations can still use FP32. The proof recomputes prefixes
and does not implement a production KV-cache protocol.

Observed local four-process FP64 proof matched all eight stage boundaries and
both greedy reference tokens exactly. This establishes small-model numerical
handoff correctness, not coding quality or large-model performance. Local native
30B experiments also exposed a loader-memory failure with the bundled backend;
a rebuilt backend completed bounded requests under a 4 GiB working-set cap.
These preliminary observations are not a completed 80B benchmark. Raw receipts
and generated candidates remain ignored under `results/`; review candidates
before execution and report first-pass versus repaired scores separately.

Do not schedule unattended inference merely by installing these tools. Admit
each requested experiment explicitly; use one worker at a time and retain the
user's desktop-memory reserve. Model weights, credentials and private logs must
never be committed.
