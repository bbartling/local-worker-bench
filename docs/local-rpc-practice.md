# Practice one coding job across three local RPC CPU nodes

This is an explicit Windows-only practice harness for the cached Qwen3.5 4B.
It starts three loopback `ggml-rpc-server` processes plus one `llama-server`
coordinator, submits bounded synthetic tasks, writes evidence, and stops every
owned process. It does not download, register or delete models, edit Ollama
settings, apply generated code or keep a background benchmark running.

## What “three nodes” means here

Logical worker 1 includes the coordinator plus RPC node 0. Workers 2 and 3 are
RPC nodes 1 and 2. All four processes share this Windows host and file cache.
The native engine really places tensors on three RPC CPU devices; this is not
three complete model replicas. Each RPC CPU has one inference thread and the
coordinator has one; the single-process comparison uses four threads.

This is not three physical 8 GiB machines. RPC working sets are capped at 4 GiB
each; coordinator at 3 GiB. The single-process mode has a 4 GiB cap. Watchdogs
abort below 6 GiB host free RAM or 1 GiB remaining commit, or above 6 GiB private
memory per process. These do not cap total OS cache or establish VM isolation.
The harness admits model files up to 6 GiB and requires 10 GiB free before start.

## Run only when a local inference job is wanted

Use the pinned backend produced by `scripts/build_paged_backend.py`. Supply the
path of an existing, trusted cached GGUF; an Ollama blob can be a GGUF even when
its filename has no extension. The commands below require Windows PowerShell,
Python 3.11+, and the already-built CPU/RPC binaries. They use no Python ML stack.

```powershell
$backend = 'results/paged-backend/build/bin/Release'
$model = 'C:/path/to/already-cached-4b.gguf'

# Short infrastructure proof first. Each output folder must be new.
python scripts/rpc_cluster_demo.py --backend-dir $backend --model-file $model --mode rpc --tasks smoke --output results/my-rpc-smoke

# Serial comparisons: same tasks, context and output limit.
python scripts/rpc_cluster_demo.py --backend-dir $backend --model-file $model --mode single --tasks motor elapsed --output results/my-single
python scripts/rpc_cluster_demo.py --backend-dir $backend --model-file $model --mode rpc --tasks motor elapsed --output results/my-rpc
```

Both modes use 2048 context, 1024 maximum output tokens, temperature zero,
thinking disabled, JSON output for coding tasks, and disabled prompt caching.
Weights stay loaded between the two tasks in one run. Context/output settings
are fixed for this practice run. Generation is bounded at 600 seconds per task,
loading at 180 seconds. Truncation is a failure, not a reviewed candidate.

Read `motor.py` / `elapsed.py` before using the hash-gated `check` command from
the README. Keep checker JSON next to the candidate as `motor.check.json` or
`elapsed.check.json`. Never execute unreviewed candidate source. No generated
source is executed by this harness or in CI.

## What to compare

- Load/startup wall time, task wall time, native prompt and generation timings.
- Token counts and reported tokens/second, which can differ with output length.
- Per-process peak RSS, peak aggregate sampled RSS and minimum free host RAM.
- Actual decoder/output placement from native logs and logged RPC graph-compute
  events. Reused graph work is not fully logged at this verbosity; these counts
  are not total RPC calls or output tokens.
- Reviewed first-pass motor score (49 cases) and elapsed score (46 cases),
  failure details and exact source hashes. Do not merge repairs into first-pass.
- Cleanup: all owned processes must exit, including on a bounded failure.

Native debug logging is enabled for placement evidence in both modes and can
affect timing. The configurations differ in thread placement and graph
partitioning; timing differences are not a pure measurement of network overhead.
This is one trial, not a statistical benchmark or claim about real Ethernet.

`scripts/export_rpc_results.py` exports synthetic prompts, candidate text,
grades, timing and resource samples without host paths, process IDs or raw logs.
Raw receipts stay under ignored `results/`; reviewed public evidence belongs in
`docs/benchmarks/`. The exporter is intentionally specific to this 4B model and
its 32 decoder blocks; assignment slot 32 refers to output placement.
Peak aggregate RSS sums sampled process working sets and can double-count shared
pages. Neither that sum nor minimum host free RAM is isolated model RAM usage.

## Preparing for 80B

`scripts/plan_gguf_partitions.py` reads GGUF headers without loading tensor data
or running inference. It proposes a contiguous three-way storage balance:

```powershell
$parts = Get-ChildItem results/model-cache/qwen3-coder-next-q4 -Recurse -Filter *.gguf | Sort-Object Name | ForEach-Object { $_.FullName }
python scripts/plan_gguf_partitions.py --files $parts --output results/my-80b-plan.json
```

The measured directory plan is layers 0-15, 16-31, 32-47: about 15.19, 14.51,
15.39 GiB of serialized tensor spans, including padding. This is a storage plan,
not native execution placement or an 80B inference success. Runtime/OS space is
extra. Three 8 GiB machines cannot hold it resident; three 16 GiB machines leave
very little headroom even before coordination. Three 32 GiB machines are a more
plausible resident target, still requiring validation. This 32 GiB PC needs
explicit disk-backed research for 80B, not just more RPC processes or closed apps.
