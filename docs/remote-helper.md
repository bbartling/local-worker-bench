# A remote agent calling your local helper

Keep the strong model in charge. Its shell tool can call a small Ollama helper
through SSH, receive a short draft, then independently test it. This does not
replace the agent's model provider or change its IDE settings.

## Temporary Windows-to-Linux route

Prerequisites: Windows Ollama with a cached model; a trusted Linux SSH account
with working key authentication and `ss`; Python 3.11+ on Linux. Verify the SSH
host key normally. The Linux host does not need Ollama installed.

On Windows, from this repository:

```powershell
powershell.exe -NoProfile -File scripts/start_windows_tunnel.ps1 -Remote worker@agent-host
```

The explicit command starts an owned hidden Ollama server bound to Windows
loopback, with one parallel request and one loaded model. It opens an SSH reverse
forward bound to Linux loopback port 11435 and checks the remote listener.
It runs for 15 minutes by default (`-DurationSeconds`, maximum one hour), then
stops only its owned SSH/Ollama process trees. Ctrl+C also runs cleanup. No global
Ollama configuration, firewall rules, startup tasks, or public tunnels are added.
An occupied local/remote port causes failure rather than interrupting another job.

Only use a trusted Linux host: other processes on that host can reach the forwarded
native API while it is open. Do not publish or proxy that port. The helper CLI
only uses cached models and generation endpoints; it never pulls/deletes models.

On Linux, verify the route without inference:

```sh
curl --fail http://127.0.0.1:11435/api/version
```

From a copy of this repository, make one explicitly authorized request:

```sh
python3 -m local_worker_bench ask --endpoint http://127.0.0.1:11435 --prompt-file /tmp/task.txt --output /tmp/candidate.json
```

The task file should contain a small redacted excerpt, one clear question and
acceptance criteria. Default model: `qwen3.5:4b`; four threads, 2,048 context,
384 output tokens, thinking off. Output must be a complete JSON object. A candidate
is never executed or accepted automatically. One retry at most, then the strong
model takes over. There is no RAM monitor: keep the large coding model opt-in and
use it only when the serving PC has enough free memory and is available.

Use deterministic scripts for HTTP status, test exits, and exact comparisons.
Delegate small drafts, extraction or test suggestions; retain architecture,
security, numerical acceptance and repository writes with the supervisor. Avoid
whole repositories, credentials and customer data. This can reduce hosted work,
but supervisor prompts, tool results and retries still consume hosted tokens.

## A client without GitHub authentication

Build a single executable Python archive on the Windows side:

```sh
python scripts/build_zipapp.py --output results/local-worker-bench.pyz
python -m local_worker_bench hash results/local-worker-bench.pyz
```

Copy it through SSH to a new `/tmp` path on Linux. Record its hash in the private
handoff. Run `python3 /tmp/local-worker-bench.pyz selftest`, then use `ask` with
the same arguments as above. It needs no installation or external packages.
Do not put credentials in the archive. Temporary copies are disposable; the
source of truth is the Git repository. Reprovision after `/tmp` is purged.

## Verification performed

November 21, 2026: Windows server to Linux agent over a loopback SSH reverse
forward; a four-thread Qwen 4B request returned the expected synthetic verdict;
the CLI exited zero, requested unload, and the server reported zero loaded
models. Direct Windows LAN-port access failed as intended. The temporary route
was shut down afterward. This is a connectivity smoke test, not application QA
or a measure of end-to-end cost savings.
