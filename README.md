# Local Worker Bench

Small, repeatable tests for a supervised local AI helper. Python 3.11+;
standard library only. Works on Windows and Linux. No installation step.

## Start here

Cluster planning: [Raspberry Pi control plane, with no inference](docs/pi-control-plane-plan.md).

Read the illustrated [local AI cluster report (PDF)](docs/reports/local-ai-cluster-explained.pdf)
for model basics, partitioning, API examples, request hops and hardware scenarios.
Its editable source is [scripts/build_cluster_report.py](scripts/build_cluster_report.py)
(requires ReportLab; rebuilding does not invoke a model).

From this repository, run:

```sh
python -m local_worker_bench selftest
```

This checks 95 hand-derived cases against hand-written controls: 49 motor-proof
cases and 46 elapsed-time cases. It runs offline and never calls a model.

## Try a model

Start Ollama yourself with a model already cached, then run:

```sh
python -m local_worker_bench run --model qwen3.5:4b --output results/qwen-first
```

Four synthetic tasks run serially:

| Task | What it checks | How it is scored |
| --- | --- | --- |
| `http` | Status codes, JSON shape, IDs, misleading logs, embedded instructions | Exact expected verdict |
| `motor` | Supply fan / pump OR proof, unknown states, strict input validation | 49 cases after source review |
| `elapsed` | Fault and covered hours, gaps, duplicates, unknown states | 46 cases after source review |
| `import` | Portable helper import in a clean export | Human review |

Use `--tasks http` for a short trial. Defaults: four threads, 2,048 context tokens,
640 output tokens, temperature zero, thinking off, 180 seconds per request.
Use `--endpoint http://127.0.0.1:11435` for a server on another local port.
`--thinking low` supports models that require a named thinking level; support
depends on the model. See the [Ollama chat API](https://docs.ollama.com/api/chat).

The runner never starts Ollama, downloads/deletes a model, or executes a candidate.
It requests immediate unload per call and again on exit, using the
[Ollama generate API](https://docs.ollama.com/api/generate). Configure a dedicated
server with `OLLAMA_NUM_PARALLEL=1` if other clients also use Ollama. The tool's
lock serializes its own runs only. After a crash, check for an active run before
removing the lock at `~/.cache/local-worker-bench/inference.lock`.

Choose a model that fits available RAM. This portable runner has request timeouts
but no RAM admission or CPU-load monitor. It does not close apps or kill servers.

Results include prompts, final answers, source hashes, timing and model digest in
the chosen directory. Raw reasoning is omitted. Existing directories are refused
so a repair cannot overwrite first-pass evidence. Truncated answers fail.
Exit zero means requests finished and the HTTP verdict passed; coding and import
answers still need review. There is no automatic overall "model passed" claim.

## Review a coding answer

Read the generated `.py` file first. After reviewing it, compute its SHA-256:

```sh
python -m local_worker_bench hash results/qwen-first/motor.py
python -m local_worker_bench check --task motor --source results/qwen-first/motor.py --reviewed-sha256 PASTE_THE_HASH
```

`check` refuses changed source and runs the reviewed file in a child process with
a 15-second timeout. Its AST filter is an extra check, **not a security sandbox**.
Only run code you trust with your machine's permissions; use a disposable isolated
environment for untrusted code. Keep a correction in a new output directory and
report both the first and repaired scores. These are small helper tests, not
production control algorithms or a general coding leaderboard.

## Check an HTTP endpoint

```sh
python -m local_worker_bench probe --url http://127.0.0.1:8000/health --expected 200 --expect-json
```

GET/HEAD only. Redirects stay visible. An expected 401 can pass; an unexpected
redirect, malformed/non-object JSON, `ok:false`, or mismatched `--expected-id`
fails. Response bodies are capped at 1 MiB and excerpts at 2,000 characters.
Output can contain endpoint data: inspect it before sharing. HTTP checks do not
prove browser clicks, plots, or layout. Authentication is intentionally left to
the application's approved client.

## Use it as another agent's helper

`ask` accepts one bounded prompt file and saves a JSON candidate for review.
A Linux agent can reach a Windows or Ubuntu Ollama server directly over a scoped
private LAN connection. See [Windows/Ubuntu LAN setup](docs/ollama-lan-setup.md)
for firewall/startup commands and `--tier fast|coder` model routing.
For dual boot, [reuse the Windows models in Linux Mint](docs/linux-mint-model-migration.md).
For the full 4B Q4 + 30B Q4 recipe, use the [Mint setup checklist](docs/linux-mint-4b-30b-setup.md)
and [supervising-agent handoff](docs/prompts/linux-mint-local-worker-handoff.md).
The earlier [Windows 4B + 7B FP16 lab handoff and client](examples/windows-ollama-fun/README.md)
are archived separately; they retain Windows-specific paths and are not the Mint recipe.
An [optional SSH tunnel](docs/remote-helper.md) is also available. Neither route
needs a public URL or IDE model-provider change. Keep the strong model responsible
for verification and writes.
For models that struggle with JSON-wrapped source, `ask --response-format text`
explicitly requests plain text. Its JSON receipt stores the draft in `content`;
it never executes or accepts that draft, and JSON failures never silently fall
back to text. See the [CPU/FP16 comparison](docs/benchmarks/2026-11-22-fp16.md).
The [dual-residency trial](docs/benchmarks/2026-11-22-dual-residency.md) records
what happened when the 4B and 7B models were kept loaded together on 32 GB RAM.
The [4B + 30B trial](docs/benchmarks/2026-11-22-fast-coder-residency.md) and
[overnight supervisor outline](docs/overnight-orchestration.md) cover the coding
pair and what remains to build for unattended work.
The [4B + 7B Q8 memory trial](docs/benchmarks/2026-11-22-q8-pair.md) completed a
two-minute residency observation with 9.32 GiB free, a lighter alternative to FP16.
For GPU/RAM tradeoffs, see the short [hardware notes](docs/hardware.md).

## Development

```sh
python -m unittest discover -s tests -v
```

GitHub Actions runs offline tests on Windows/Linux with Python 3.11/3.14. Its fake
HTTP services are loopback fixtures; it never calls Ollama or executes model drafts.
The repository contains synthetic fixtures, not private application test data.
