> Historical research: retained for reproducibility and AI context. The active tool is single-machine OS paging; start at [the current guide](guide.md). Old paths/settings describe prior experiments. The old cluster PDF was replaced by `reports/os-paging-guide.pdf`.

# Ollama over a private LAN: Windows or Ubuntu

An agent sends HTTP requests directly to the computer running Ollama. No SSH
tunnel or IDE provider change is needed. The agent selects the model in each
request; Ollama loads it. Keep one loaded model/request and unload after each
task on a shared desktop.

Examples use **server `192.168.1.10`**, **client `192.168.1.20`**, port **11435**.
Replace both addresses and the network interface with yours. Prefer DHCP
reservations so addresses stay stable. Bind the specific LAN address, not every
interface. These instructions add no public tunnel or router port-forwarding.
Native HTTP here has no added authentication or encryption; use it only between
trusted machines and scope the firewall to the approved client.

## Windows server

Install [Ollama for Windows](https://ollama.com/download/windows) and obtain this
repository. From its root, inspect the adapter and network profile:

```powershell
Get-NetIPAddress -AddressFamily IPv4
Get-NetConnectionProfile
```

The selected adapter must already be Private. In **Administrator PowerShell**,
install the narrowly scoped rules:

```powershell
./scripts/configure_windows_lan_firewall.ps1 -LocalAddress 192.168.1.10 -PeerAddress 192.168.1.20
```

The script allows this executable/port/client on the Private interface, blocks
other IPv4 sources for that executable/port/interface, and blocks the port on
Public/Domain profiles. Only its three named rules are managed. No other firewall
rules are removed. See [Microsoft's firewall command documentation](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule).

Back in **ordinary, non-administrator PowerShell**, start the server:

```powershell
./scripts/windows_lan_server.ps1 -Action Start -LocalAddress 192.168.1.10
./scripts/windows_lan_server.ps1 -Action Status
```

The hidden process binds only that address. Settings are process-local:
`OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_KEEP_ALIVE=0`,
`OLLAMA_CONTEXT_LENGTH=2048`, cloud disabled. Starting/status never loads a model.
State/logs live in `%LOCALAPPDATA%/LocalWorkerBench`; requests are not debug-logged.
It stays running idle until stopped or the Windows session ends. There is no
automatic reboot/logon startup; rerun Start afterward. A busy port is refused.

### Optional two-model residency experiment

Only when the user explicitly requests a warm pair, stop the idle owned server
and opt in to two resident models and indefinite keep-alive:

```powershell
./scripts/windows_lan_server.ps1 -Action Stop
./scripts/windows_lan_server.ps1 -Action Start -LocalAddress 192.168.1.10 -MaxLoadedModels 2 -KeepAlive '-1'
```

This starts the server only; it does not preload weights or start generation.
The ordinary defaults remain one loaded model and keep-alive zero. State/status
records both requested settings. They are process-local, not machine-wide.
Requests with `keep_alive:0` still unload their selected model; the existing
`ask` client deliberately does this, so a warm experiment needs a different
explicit request lifecycle. Do not silently change the ordinary worker's policy.

Two resident models do not imply two simultaneous requests: serialize requests
across both, with four threads and bounded context. The launcher itself does
not monitor RAM. Check available memory before and between requests; stop new
inference and unload when the shared desktop lacks headroom. A November 22
attempt to retain 4B Q4 plus 7B FP16 was stopped by its separate two-GiB reserve
monitor at 1.41 GiB free. Residency has not been qualified for unattended work.

After the experiment, stop and Start again without those optional arguments to
restore the ordinary configuration. No firewall change is needed.

Download models if not already cached (downloads do not run inference):

```powershell
$env:OLLAMA_HOST = '192.168.1.10:11435'
ollama pull qwen3.5:4b
# Optional larger coding model; plan RAM/VRAM before using it.
ollama pull qwen3-coder:30b
```

Stop the owned process tree as the ordinary user:

```powershell
./scripts/windows_lan_server.ps1 -Action Stop
```

To remove only the managed firewall rules, use Administrator PowerShell:

```powershell
./scripts/configure_windows_lan_firewall.ps1 -LocalAddress 192.168.1.10 -PeerAddress 192.168.1.20 -Remove
```

## Ubuntu / Linux Mint server

For the **locked Mint OptiPlex defaults** (4B + 30B dual-resident on
`192.168.204.11:11435`, UFW scoped to `192.168.204.16`, boot warmup), follow
[the Mint 4B+30B checklist](linux-mint-4b-30b-setup.md) and
[the 2026-11-22 validation note](benchmarks/2026-11-22-mint-lan-dual-resident.md).
The Ubuntu snippet below remains the generic one-model / unload-after-request
LAN recipe; Mint intentionally opts into `MAX_LOADED_MODELS=2` and
`KEEP_ALIVE=-1`.

For an existing Windows cache, see [copying models into Mint](linux-mint-model-migration.md)
before downloading the weights again.

Follow the [official Linux installation instructions](https://docs.ollama.com/linux).
If using the installer, download and inspect it before running it:

```sh
curl -fsSL https://ollama.com/install.sh -o /tmp/install-ollama.sh
less /tmp/install-ollama.sh
sh /tmp/install-ollama.sh
```

Use the installer's `ollama` system service, running as its unprivileged `ollama`
user. Do not run the inference service as root. Check your address/interface:

```sh
ip -br -4 address
systemctl show ollama -p User
```

Set your real values, then scope the firewall **before** exposing the listener:

```sh
SERVER_IP=192.168.1.10
CLIENT_IP=192.168.1.20
LAN_IF=enp3s0
sudo ufw status numbered
sudo ufw insert 1 allow in on "$LAN_IF" from "$CLIENT_IP" to "$SERVER_IP" port 11435 proto tcp
sudo ufw insert 2 deny in on "$LAN_IF" from any to "$SERVER_IP" port 11435 proto tcp
```

The allow precedes the deny. Inspect existing rules; keep required SSH/web-service
access before enabling UFW on an existing machine. Do not reset its firewall.
If UFW is not active, configure required service access and then `sudo ufw enable`.
See [Ubuntu's firewall guide](https://ubuntu.com/server/docs/how-to/security/firewalls/).
These UFW commands assume the server uses UFW, not another firewall manager.

Create a dedicated systemd override without replacing the vendor service:

```sh
sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/local-worker-lan.conf >/dev/null <<EOF
[Unit]
Wants=network-online.target
After=network-online.target
[Service]
Environment="OLLAMA_HOST=$SERVER_IP:11435"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=0"
Environment="OLLAMA_CONTEXT_LENGTH=2048"
Environment="OLLAMA_NO_CLOUD=true"
Environment="OLLAMA_DEBUG_LOG_REQUESTS=false"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo systemctl status ollama --no-pager
ss -ltn 'sport = :11435'
```

Inspect an existing override before replacing the same filename. Confirm the
listener shows your chosen address, not `0.0.0.0` or `[::]`. To cache the models:

```sh
OLLAMA_HOST="$SERVER_IP:11435" ollama pull qwen3.5:4b
# Optional, larger download; no inference:
OLLAMA_HOST="$SERVER_IP:11435" ollama pull qwen3-coder:30b
```

The system service can start at boot; check its enablement with
`systemctl is-enabled ollama`. Stop it with `sudo systemctl stop ollama`.
If both the agent and Ollama run on this Ubuntu machine, use loopback binding
instead and skip LAN exposure/firewall changes altogether.

## Agent client and model routing

From the approved client, verify connectivity without inference:

```sh
curl --fail --max-time 3 http://192.168.1.10:11435/api/version
curl --fail --max-time 3 http://192.168.1.10:11435/api/tags
```

Run the Python client from this repository, or use its `.pyz` archive:

```sh
python3 -m local_worker_bench ask --endpoint http://192.168.1.10:11435 --allow-lan --tier fast --prompt-file /tmp/task.txt --output /tmp/fast-candidate.json
python3 -m local_worker_bench ask --endpoint http://192.168.1.10:11435 --allow-lan --tier coder --prompt-file /tmp/coding-task.txt --output /tmp/coder-candidate.json
```

`--tier fast` selects `qwen3.5:4b`: short extraction and simple drafts; 384 output
tokens and 180-second timeout. `--tier coder` selects `qwen3-coder:30b`: bounded
coding drafts; 640 output tokens and 300-second timeout. Both default to four
threads, 2,048 context, JSON output, thinking off and immediate unload. Override
the token/timeout budgets explicitly if needed. `--model` and `--tier` are mutually
exclusive. Both tiers use the same URL; no server restart is needed to switch.

`ask --response-format text` explicitly omits Ollama's JSON-format constraint.
The saved receipt remains JSON, with unstructured model output in `content`.
This is useful for supervised code drafts from models that struggle with JSON
source strings. Output may still include Markdown/prose; inspect it before any
execution. There is no automatic format fallback, source extraction or acceptance.

The **supervisor chooses** the tier. There is no automatic escalation, execution
of generated code, model download, or acceptance of a candidate. The portable
remote client has no server-RAM admission check: confirm serving-machine headroom
before choosing Coder. A 32 GB shared desktop can be too busy for its 19 GB weights.
Allow at most one corrective retry; keep security/numerical acceptance and writes
with the strong supervisor. See [hardware sizing](hardware.md).

For raw API clients, change the `model` field between the two exact tags and use
`stream:false`, `keep_alive:0`, and explicit `options.num_thread/num_ctx/num_predict`.
The [Ollama API](https://docs.ollama.com/api/chat) documents these fields.

## Check memory and diagnose failures

On Windows:

```powershell
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name,Id,@{n='RAM_MiB';e={[math]::Round($_.WorkingSet64/1MB)}}
./scripts/windows_lan_server.ps1 -Action Status
```

On Ubuntu:

```sh
free -h
ps -eo pid,comm,rss --sort=-rss | head -16
journalctl -u ollama -n 40 --no-pager
```

Process working sets/RSS can include shared pages; their sum is not exact total
physical use. Check available memory as well. Do not close work apps automatically.
For connection failures, verify the listener, current IP, profile/firewall and
client source IP. For slow responses, reduce model/context and inspect CPU/RAM;
do not silently increase parallel requests. A timeout or truncated draft is a
failure, not application qualification. Never send credentials in prompts/logs.

Windows LAN connectivity was exercised on November 22, 2026. The Ubuntu section
is a setup recipe based on the linked upstream documentation; it has not been
installed or live-qualified by this project. CI tests the portable Python client
on Windows and Linux using synthetic fixtures, without local inference.
