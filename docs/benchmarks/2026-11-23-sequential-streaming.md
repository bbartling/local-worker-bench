# Coding from a checkpoint larger than RAM

23 November 2026. Actual measurements on one Windows i7-9700, approximately
32 GiB RAM, CPU only. Four inference threads, one native worker at a time,
2048-token context. All six harness runs completed and stopped their owned
processes. Model outputs were inspected before independent hash-gated checks.

The 4B experiment preserved its control answer under explicit layer eviction.
We then ran the downloaded Qwen3-Coder-Next 80B Q4_K_M checkpoint: four GGUF
files totaling 48,410,992,032 bytes (48.41 decimal GB / 45.09 GiB).
It generated real code on this PC without making all weights resident.

## Matched compact patch

Repair `is_success(status)` so only exact Python ints from 200 through 299
produce True. The same user prompt and 25 independent cases were used.

| Model / memory policy | Grade | Request wall | Load/startup | Run peak process RSS |
| --- | ---: | ---: | ---: | ---: |
| 4B mmap control | 24/25 | 5.756 s | 15.289 s | 2.742 GiB |
| 4B explicit layer eviction | 24/25 | 134.525 s | 15.650 s | 0.771 GiB |
| 80B explicit layer eviction | 25/25 | 1,082.810 s | 4.110 s | 0.901 GiB |
| 80B OS-managed paging | 25/25 | 122.896 s | 4.913 s | 4.000 GiB |

For each model the paired source hashes were identical. The 4B draft used
`isinstance(status, int)` and incorrectly accepted an int subclass. The 80B
draft used `type(status) is int`. This one contract edge is evidence of a
better answer on this task, not a general intelligence ranking.

The 80B forced-eviction request was **8.81 times slower** than OS paging.
Reported generation throughput was 0.0303 versus 0.7942 tokens/s. Startup,
prompt evaluation and generation are recorded separately; request wall includes
prompt processing. Both conditions share OS caches, and there was no cold-cache
flush or repeated randomized trial. The 80B paged run's peak RSS spans all three
coding requests, not an individually isolated patch measurement.

## Broader first-pass grades

The broader tasks are bounded synthetic motor-state and elapsed-time functions.
Their fixture totals include correlated validation cases, not 95 independent
repository tasks. Scores below exclude repairs.

| Configuration | Motor | Elapsed | Total |
| --- | ---: | ---: | ---: |
| 4B single process, four threads | 42/49 | 28/46 | 70/95 |
| 4B three native RPC workers on this PC | 34/49 | 28/46 | 62/95 |
| 30B historical local run | 49/49 | 39/46 | 88/95 |
| 80B OS-managed paging, four threads | 47/49 | 40/46 | 87/95 |

Historical 30B has an additional system instruction; it is not an exactly
controlled prompt/speed comparison. See the [earlier RPC benchmark](2026-11-23-local-rpc.md)
for that provenance and the single-thread control. Numerical execution settings
can change generated answers; placement alone is not an established quality loss.

| 80B paged task | Request wall | Output tokens | Reported generation tokens/s |
| --- | ---: | ---: | ---: |
| Compact patch | 122.896 s | 29 | 0.794 |
| Motor | 375.384 s | 306 | 1.176 |
| Elapsed | 711.886 s | 701 | 1.197 |

Motor confused mixed `[False, None]` with fully false evidence. Elapsed missed
boolean/non-finite gap and non-finite timestamp rejection. The 80B run therefore
still needs a strong reviewer. Its whole three-task run took 1,215.925 seconds,
including startup and cleanup. These broader grades belong to **OS-managed
paging**, not the forced-eviction mode graded on the compact patch.

## One supervised repair through the API

The separate supervised motor retry passed **49/49** after the hosted reviewer
identified the two failures and requested only a replacement decision block.
It used the actual `ask` client and OS-paged 80B API profile: 243 prompt tokens,
51 output tokens, 233.143 seconds client wall, 5.484 seconds startup,
171.033 seconds prompt evaluation and 55.598 seconds generation. The supervisor
inspected the block, applied it to the pinned disposable source and reviewed
the full result before hash-gated checks. This narrow integration demonstration
does not change the first-pass 87/95 total or repair the elapsed task. All-cloud
cost and hosted token usage were not measured.

## What the memory result establishes

The explicit C++ callback synchronized after decoder outputs and evicted mapped
weight pages. The 80B patch observed all 48 decoder layers, 25,017 eviction
requests, zero unexpected OS errors, and 63,888 repeated resident sample
observations before eviction versus zero afterward. This is sampled evidence,
not a scan of every page. Virtual mappings and live KV/recurrent state remain.

The paged broader run had approximately 4.000 GiB sampled peak process RSS,
1.001 GiB peak private bytes, and at least 11.016 GiB host RAM available.
The configured working-set cap was 4 GiB; sampling can slightly overshoot it.
Process RSS excludes shared OS file-cache/standby usage. This is **not** proof
that an isolated 8 GiB computer would behave the same way. Actual physical SSD
reads, hard faults and energy were not measured. Qwen's selected-expert MoE
architecture matters; a dense 80B model could reread much more data per token.

Prefer OS-managed paging for further bounded work on this PC based on this
trial. Explicit eviction is useful as a residency experiment, but aggressively
discarding reusable pages imposes substantial overhead. The existing RPC heap
allocator is unchanged: this is not yet disk-backed inference across three hosts.

## Reproduce and supervise

The actual 4B streaming API smoke returned exactly `READY` in 30.636 seconds
including startup and cleanup; all 32 layer IDs and reduced residency were
verified, and its worker exited. An initial API attempt returned HTTP 502
because default native logging omitted the expected layer count, despite
successful eviction events. The facade now requests verbosity 5 for streaming
profiles. A regression assertion covers that setting; the failed receipt is
retained alongside the successful repeat. Smoke remains separate from coding.

All 63 repository tests and the 95 handwritten fixture controls passed after
the fix. These engineering checks run without inference and do not increase
the model's quality score. The experimental API was stopped after the trial.

- [Build, memory semantics and command examples](../sequential-layer-streaming.md)
- [Hosted supervisor and local worker workflow](../cloud-supervisor-local-worker.md)
- [Full sanitized evidence](data/2026-11-23-streaming-coding.json)
- [Complete compressed residency events](data/2026-11-23-streaming-coding.events.jsonl.gz)

The evidence retains prompts, candidates, source hashes, failed cases, native
timings, resource samples, backend provenance and cleanup. Raw private paths,
logs and weights remain outside Git. Smoke responses are labeled smoke, not
coding grades. The API smoke and one supervised motor repair are recorded
separately from these first-pass trials in the same evidence file.

The next useful cluster test is this same task contract on real 3 x 8/16/32 GiB
hosts, measuring total host memory and physical I/O. A durable overnight queue,
reboot recovery and cloud-cost accounting are still future work. Slow drafting
is viable only when accepted patches justify latency and review effort.
