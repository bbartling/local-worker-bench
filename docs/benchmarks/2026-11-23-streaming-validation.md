# Resident-layer streaming: initial validation

Completed follow-up: [80B coding grades, timing and supervised repair](2026-11-23-sequential-streaming.md).

23 November 2026. One Windows i7-9700 / approximately 32 GiB PC; four CPU
threads, 2048 context. Native quantized GGUF execution, not PyTorch conversion.

| Model / request | Mode | Request seconds | Result |
| --- | --- | ---: | --- |
| Cached 4B smoke | Explicit layer eviction | 14.816 | Exactly READY; all 32 layers observed |
| Cached 4B compact HTTP patch | Mmap control, no eviction hook | 5.756 | 24/25 reviewed cases |
| Same 4B compact HTTP patch | Explicit layer eviction | 134.525 | Same source hash and 24/25 |
| 80B Q4 smoke | Explicit layer eviction | 51.270 | Exactly READY; all 48 layers observed |

The 4B patch candidates have identical SHA-256
`e954f31d45fa9a935775233efc6bfdaabe32e7c88f399edac302e847c0f68c41`.
Their remaining mistake is accepting an int subclass; the specification required
exact Python int. This validates the tested answer's preservation, not perfect
model reasoning or general numerical equivalence across every request.

The 4B patch's sampled process peak RSS was about 0.771 GiB with explicit
eviction versus 2.742 GiB for its control. The eviction trace recorded 11,928
accepted eviction requests, zero unexpected errors, and 35,767 resident sample
observations before eviction versus zero afterward. Samples repeat across
weights and steps; these are not unique pages, physical SSD bytes or total
system RAM savings. Virtual mappings, live inference state and OS file cache
remain. All four completed runs stopped their owned processes.

The 80B coding task is a separate trial; successful READY output does not count
as a coding grade. The completed 80B smoke already shows that the full downloaded
checkpoint can perform bounded native inference through this resident-page
policy on this PC. It does not establish three-host 8 GiB isolation or make
the RPC heap allocation path disk-backed.

- [Implementation and reproduction guide](../sequential-layer-streaming.md)
- [Public validation evidence](data/2026-11-23-streaming-validation.json)
- [Compressed complete residency trace](data/2026-11-23-streaming-validation.events.jsonl.gz)

The data includes startup, prompt/generation timings, resource samples, candidates,
hashes, test failures and backend provenance. The backend uses a separate private
build; installed Ollama and OS pagefile policy are unchanged. No forced cold-cache
flush occurred. This is one trial per condition, not a statistical benchmark.
