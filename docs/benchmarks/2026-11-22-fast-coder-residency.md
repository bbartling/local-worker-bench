# Keeping the 30B Q4 and 4B Q4 helpers loaded together

**Both models loaded together and answered short requests sequentially.** The
user had closed VS Code and browser windows, raising available RAM to about
22.8 GiB. Available RAM later reached 1.984 GiB, triggering the same two-GiB
reserve guard. The normal one-model configuration was restored afterward.

Windows, i7-9700, 32 GB RAM, CPU inference, Ollama 0.40.16. The temporary loopback
server allowed two loaded models, one parallel request per model and 2,048 context
per model. Generation used four threads and requests were strictly sequential.

| Step | Result |
| --- | --- |
| Preload Qwen3-Coder 30B Q4 | 54.87 seconds |
| Preload Qwen 3.5 4B Q4 while retaining 30B | 12.21 seconds |
| Verify `/api/ps` | Both exact names present, each with 2,048 context |
| Warm 4B request: reply `READY` | Returned `READY`, completed in 1.03 seconds |
| Warm 30B request: reply `READY` | Returned `READY`, completed in 1.03 seconds |
| Peak sampled owned-process RSS | 20.947 GiB, approximate working-set sum |
| Lowest sampled available RAM | 1.984 GiB |
| Full experiment duration | 71.71 seconds, mostly loading |

Both models remained listed after both requests. The guard stopped the test at
the start of the idle observation period, before the planned 120-second hold
completed. This was a protective stop, not an out-of-memory crash. These tiny
readiness replies do not measure coding quality or demonstrate overnight stability.
No simultaneous generation or instrumented UI-latency test was performed.

The guard required four consecutive half-second samples below two GiB available.
Owned-process RSS can include shared pages; it is not an exact unique-memory
total. No work apps were closed by the test, and no generated source was executed.
The temporary server was stopped and the existing LAN API was restored idle with
its original one-loaded-model limit. No firewall or persistent startup settings
were changed.

## Implication for overnight work

A supervisor can route short tasks to 4B and coding drafts to 30B through the
same API. Co-residency saves reload time, but is not required for this workflow:
sequential load/unload uses less RAM. Closing apps helped this pair fit briefly,
but approximately two GiB of remaining headroom is limited room for longer
contexts or additional apps. A quieter OS session or more RAM needs its own
measured qualification before relying on sustained residency.

See the [overnight orchestration outline](../overnight-orchestration.md) for the
distinction between available helper calls and an unattended job runner.
