# Paging evaluation: measurements and a fair next comparison

## Completed before the refactor

One i7-9700 / 32 GB Windows PC, four CPU threads, 2048 context. Native CPU
Qwen3-Coder-Next Q4_K_M, 48.41 GB checkpoint, with a 4 GiB process working-set cap.
All candidates were inspected before hash-gated checks. These are synthetic
function fixtures, not autonomous repository tasks.

| Matched compact patch | Request wall | Grade | Generation tokens/s |
| --- | ---: | ---: | ---: |
| Explicit per-layer eviction | 1082.810 s | 25/25 | 0.0303 |
| OS-managed Windows paging | 122.896 s | 25/25 | 0.7942 |

Both produced identical source. OS paging was 8.81 times faster overall in this
single paired trial. Neither measurement held all model weights resident. No
cold-cache flush occurred; process RSS excludes some shared OS cache use.

| OS-paged 80B task | Grade | Request wall |
| --- | ---: | ---: |
| Motor-state function | 47/49 | 375.384 s |
| Elapsed-time function | 40/46 | 711.886 s |
| Total, first pass | 87/95 | Separate compact patch excluded |
| Motor after one supervised local repair | 49/49 | 233.143 s client round trip |

Historical 30B scored 88/95 with an extra system instruction and different
conditions. It prevents claiming "80B always wins"; it is not a controlled speed
ranking. The repair fixed mixed False/None evidence after the supervisor supplied
the failures. That demonstrates a review loop, not general autonomous reliability.

Full prior prompts, sources, failures, native timing, resource samples and hashes:
`benchmarks/data/2026-11-23-streaming-coding.json`. Prior failed API smoke is
retained there too: expected-layer logging was missing, the API failed closed,
then passed after verbosity was enabled. Explicit eviction is now research only.

## New model/precision matrix

The existing 80B Q4 **is already Qwen3-Coder-Next**; it is not a third independent
model. Qwen3.8-27B is a newer general model to compare on coding tasks.

| Candidate | Publisher / format | Download bytes | Status |
| --- | --- | ---: | --- |
| Coder-Next Q4_K_M | Qwen GGUF, four parts | 48,410,992,032 | Verified; prior graded results above |
| Coder-Next F16 | Qwen GGUF, four parts | 159,458,215,744 | Download initiated; no precision grade yet |
| Qwen3.8-27B UD-Q4_K_M | Unsloth community GGUF | 16,564,259,744 | Download initiated; no grade yet |
| Qwen3.8-27B BF16 | Unsloth community GGUF, two parts | 54,657,735,616 | Download initiated; no grade yet |

Download manifests under `examples/paging/` pin repository revisions, sizes and
SHA-256. Verify all parts before load. BF16 and IEEE FP16 are different 16-bit
formats; label them accurately. UD-Q4_K_M is not identical quantization policy to
Qwen's Q4_K_M. Inspect actual tensor types before claiming uniform precision.
Text-only trials omit the optional vision projector. No conversion from Q4 back
to FP16 can recover the original precision; download the genuine 16-bit weights.

## Trial sequence and acceptance

1. Existing Q4: test the .66 available-RAM budget and structured task packets.
2. Once verified, Qwen3.8 Q4: smoke, compact patch, motor and elapsed contracts.
3. Compare F16/BF16 using the same contract, output budget and backend revision.
   Stop on incompatible model, load/generation timeout or resource guard; record
   failure rather than silently increasing limits or switching models.
4. Add real disposable single-file patch tasks with independent regression tests,
   then a bounded one-repair cycle. No auto-apply or generated code in CI.
5. Linux/WSL qualification is a later phase with explicit cgroup/whole-host data.

`scripts/paging_benchmark.py --style packet|baseline` saves serial, unexecuted
candidates and a SQLite review ledger. The packet adds explicit edge-case hints;
compare information content honestly. The script never grades its own source.
Keep `patch` 25 cases separate from `motor` 49 and `elapsed` 46.

Record startup, prompt time, generation time/tokens, whole-request wall, output
truncation, prompt/candidate SHA, peak RSS/private bytes, available RAM/commit,
budget and worker cleanup. Also record competing downloads: concurrent disk I/O
confounds speed. Separate smoke, first-pass, repair and supervisor-rewritten
answers. Publish every attempted condition, not only successes. Multiple repeats
and whole-host/physical-I/O measurements are needed before declaring a sweet spot.

Model sources: [Qwen Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF),
[Qwen3.8 upstream](https://huggingface.co/Qwen/Qwen3.8-27B),
[community GGUFs](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).
The current continuation state is in [checkpoint.md](checkpoint.md).
