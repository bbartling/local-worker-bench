# Keeping the 4B and 7B helpers loaded together

**Both models loaded together successfully in a brief trial.** Available RAM
then reached **1.93 GiB**, triggering the trial's two-GiB reserve guard. The user
reported no noticeable slowdown in VS Code or other apps. The normal one-model
configuration was restored afterward; sustained dual-residency use is untested.

## Conditions and observed results

Windows, i7-9700, 32 GB RAM, CPU inference, Ollama 0.40.16. About 19.8 GiB was
available before the trial. A dedicated, temporary loopback server allowed two
loaded models, one parallel request per model, and 2,048 context per model.
Generation requests were sequential and used four threads.

| Step | Result |
| --- | --- |
| Preload Qwen2.5-Coder 7B FP16 | 43.30 seconds |
| Preload Qwen 3.5 4B Q4 while retaining 7B | 12.24 seconds |
| Verify `/api/ps` | Both exact model names present, each with 2,048 context |
| Short warm 4B request | Completed in 1.03 seconds; both models still listed |
| Begin short 7B request | Stopped when the RAM reserve guard triggered |
| Peak sampled owned-process RSS | 17.773 GiB, approximate working-set sum |
| Lowest sampled available physical RAM | 1.930 GiB |
| Human observation | No noticeable slowdown reported |

The full experiment lasted 60.74 seconds, mostly loading time. Both models were
verified together only near the end. The planned 120-second observation window
was **not completed**, and no simultaneous two-model generation test occurred.

The guard sampled memory every half second and stopped after four consecutive
samples below two GiB available. This was a protective stop, not a model/server
crash or an out-of-memory failure. RSS can include shared pages; the figure above
is not an exact unique-physical-memory total. No instrumented UI-latency or
paging test was performed.

## Practical interpretation

Two model files fitting in the cache does not imply comfortable resident RAM.
These two can coexist with the current short contexts, but the measured desktop
had little headroom for additional apps or longer contexts. That supports retaining
one-model-at-a-time operation as the shared desktop default. More RAM would give
resident models and work apps more margin; it would not directly increase CPU
generation throughput.

The temporary server and its owned processes were stopped, all test models were
unloaded, and the existing LAN API was restarted idle with its original
`OLLAMA_MAX_LOADED_MODELS=1` configuration. No firewall changes, work-app closures,
automatic startup changes, or persistent dual-model setting were made.

Ollama documents multiple-model loading, queueing/eviction under memory pressure,
and per-request `keep_alive` in its [concurrency and residency FAQ](https://docs.ollama.com/faq).
The trial used explicit ten-minute keep-alives while testing, followed by cleanup;
it did not rely on the normal helper's immediate-unload behavior.
