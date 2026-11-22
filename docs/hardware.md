# Buying capacity for a supervised coding helper

Checked November 21, 2026. Choose the model and useful context first, then size
GPU memory for its weights, runtime overhead, and KV cache. System RAM helps
CPU offload and desktop stability; it does not become fast GPU VRAM.

| Goal | Practical direction |
| --- | --- |
| Short extraction and tiny drafts | Keep the existing CPU helper first; a modest GPU can improve latency |
| Cached Qwen3-Coder 30B at Q4 | Target 24 GB VRAM for weights plus modest context; measure actual fit |
| Low-power stock office PC | Check exact chassis, slot clearance, PSU and connectors before choosing a card |
| Long contexts or large non-quantized models | Budget substantially more memory; do not infer fit from parameter count alone |

The official [Qwen3-Coder 30B package](https://ollama.com/library/qwen3-coder:30b)
is approximately 19 GB at Q4_K_M. A 16 GB GPU cannot hold that entire weight set;
CPU offload can work but speed must be measured. Its 3.3B active parameters do
not reduce the stored 30.5B weight set to a 3.3B model.

[Devstral Small 2 in Ollama](https://ollama.com/library/devstral-small-2) is roughly
15 GB before runtime/KV overhead. Do not promise comfortable long-context use
on 16 GB. [Mistral's deployment guidance](https://docs.mistral.ai/vibe/code/cli/offline-models)
recommends a 24 GB GPU for 4-bit Devstral Small 2 at 32k context.

Four-bit quantization is a sensible starting point, followed by task-specific
tests. More precision is not automatically the best use of money. As a rough
weight-only calculation, a 30.5B model at FP16/BF16 needs 61 billion bytes,
about 56.8 GiB, before KV cache, runtime and OS. A 64 GB RAM PC has little room
left and still uses CPU speed if the model is not on a GPU.

For a Dell OptiPlex 7070, inspect the installed DIMMs. Four occupied 8 GB slots
mean reaching 64 GB requires replacing the modules with a supported set, rather
than adding two sticks. Dell's [7070 Tower memory statement](https://dl.dell.com/manuals/all-products/esuprt_desktop/esuprt_optiplex_desktop/optiplex-7070-desktop_reference-guide7_en-us.pdf)
lists configurations through 64 GB. Exact form factor and compatibility matter.

A used 24 GB RTX 3090 is a candidate for the larger helper, conditional on total
build cost and a tested card. [NVIDIA's reference requirements](https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/rtx-3090-3090ti/)
list 350 W graphics power and a 750 W system PSU for the 3090; partner cards vary.
It is not an assumed drop-in upgrade for an office-PC PSU or chassis. Compare a
complete newer system before spending heavily on an old replacement motherboard.

One checked retailer [lists a 5060 Ti 16 GB at $789.99, in-store only](https://www.microcenter.com/product/694811/pny-nvidia-geforce-rtx-5060-ti-overclocked-dual-fan-16gb-gddr7-pcie-50-graphics-card).
This is a displayed asking price, not a verified available local deal. At that
price it is a poor capacity match for the 19 GB Qwen package. No used-card sold
median was independently established for these notes; do not reuse old quotes
as a current purchase recommendation.

The existing narrow tests favored a small Qwen helper for extraction and the
larger Coder for reviewed functions. They do not establish autonomous enterprise
coding ability. Keep the stronger supervisor and deterministic acceptance tests.

The [November 22 FP16 follow-up](benchmarks/2026-11-22-fp16.md) ran the 0.5B and
7B FP16 coders on this CPU. The larger model fit with about 4.2 GiB available,
but needed a plain-Python corrective request to pass the motor cases and generated
about 1.7 tokens/s. Higher precision did not establish a better default helper.
