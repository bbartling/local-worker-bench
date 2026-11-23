# Historical research, not active features

The active tool uses one computer and OS-managed paging. These records preserve
what was actually tried, including failures; they are not setup instructions for
the current machine. Model cleanup removed the old Ollama 4B/30B caches.

- `docs/benchmarks/2026-11-23-sequential-streaming.md`: measured 80B Windows
  paging versus explicit eviction; full synthetic evidence remains linked there.
- `docs/benchmarks/2026-11-23-local-rpc.md`: small-model loopback RPC trials;
  no physical three-host 8 GiB qualification.
- `docs/three-worker-cluster-plan.md` and `docs/tensors-partitions-and-transfers.md`:
  prior topology, transport and tensor explanations, retained for AI research.
- `scripts/rpc_cluster_demo.py`, `scripts/plan_gguf_partitions.py`: prior
  research/reproduction code, outside the active paging workflow. No cluster
  service is started by the current CLI.
- `cluster/`: old PDF sources. The old PDF was removed; rebuilding historical
  material writes only to ignored results, never the active report.

Do not copy old paths, warm-model policies or proposed cluster claims into new
results. Current instructions are in the root AGENTS.md and docs/agent-guide.md.
