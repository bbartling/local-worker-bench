# Linux Mint: 4B Q4 + 30B Q4 local helpers

Use this for an Ubuntu-based Linux Mint installation on the same dual-boot PC.
Mint may leave more RAM available than Windows, but this pair has **not** been
tested on Mint. Windows briefly held both models before its two-GiB memory
reserve guard stopped the test. Do not assume overnight stability or speed.

| Role | Ollama tag | Existing Windows weight size |
| --- | --- | --- |
| Small helper | `qwen3.5:4b` | about 3.3 GB, Q4 |
| Coding helper | `qwen3-coder:30b` | about 18.6 GB, Q4 |

Those are weight-file sizes, not total runtime RAM. Start with 2,048 context,
four inference threads and one request at a time across both models. A strong
Cursor/Codex/Claude supervisor reviews drafts, runs tests and makes edits.

For a lighter alternative, [4B + 7B Coder Q8](benchmarks/2026-11-22-q8-pair.md)
completed a brief Windows memory trial with 9.32 GiB free. Its coder tag is
`qwen2.5-coder:7b-instruct-q8_0`; it is a different recipe, not the default
`--tier coder` routing. It has not been tested on Mint or qualified for coding.

## 1. Install Ollama and get these notes

On the Mint terminal:

```sh
sudo apt update
sudo apt install curl git python3 rsync ufw
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
less /tmp/ollama-install.sh
sh /tmp/ollama-install.sh
ollama --version
sudo systemctl stop ollama
systemctl show ollama -p User
sudo systemctl cat ollama
```

The official installer creates the service. Confirm its user is `ollama`; do not
serve inference as root. Inspect any existing service configuration before
changing it. No GPU driver is needed for this CPU-only experiment.

The notes are in the **private** `bbartling/local-worker-bench` repository. Open
it in your signed-in GitHub browser or clone with your existing GitHub credentials.
For a fresh Linux GitHub CLI login, if needed:

```sh
sudo apt install gh
gh auth login
BENCH_ROOT=$(mktemp -d -t local-worker-bench.XXXXXX)
gh repo clone bbartling/local-worker-bench "$BENCH_ROOT"
cd "$BENCH_ROOT"
python3 -m local_worker_bench selftest
```

The last command is offline: expected 49 motor + 46 elapsed-time controls passing.
It does not run Ollama. The clone is temporary; the GitHub notes persist.

## 2. Reuse the Windows models, or download just these two

In Mint's file manager, mount the Windows drive and press **Ctrl+H** to show
hidden folders. The source is Windows `Users/ben/.ollama/models`, containing
both `blobs` and `manifests`. The mount point is machine-specific.

Follow [the model-cache copy guide](linux-mint-model-migration.md) to copy into
`/var/lib/ollama/models` on the Linux filesystem. Inspect the destination first.
That guide uses `rsync` without deletion and changes ownership only on the Linux
destination. Copying the whole cache also copies the FP16 experiments: check
source size and free target disk space first. Copy only the `models` directory,
not Ollama identity keys or private application files. Leave Windows files alone.

Alternatively skip copying and download only the two named models after starting
the service in step 3. Do not run a second `ollama serve` alongside the service.

## 3. Start on loopback first

If Cursor and Ollama will both run on Mint, loopback is all you need. **No inbound
firewall exception or tunnel is needed for this mode.** Port 11435 matches these
notes; the Ollama CLI's usual default is 11434, so set its host explicitly.

Inspect existing drop-ins with `systemctl cat ollama`. Create the directory, then
open this dedicated file; if it exists, review its contents before editing:

```sh
sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
sudo install -d -o ollama -g ollama /var/lib/ollama/models
sudoedit /etc/systemd/system/ollama.service.d/local-worker-mint.conf
```

Put these settings in it. The models path matches the cache-copy guide; it can
also hold fresh downloads if you chose not to copy.

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11435"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
Environment="OLLAMA_NO_CLOUD=1"
Environment="OLLAMA_DEBUG_LOG_REQUESTS=false"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_CONTEXT_LENGTH=2048"
Environment="OLLAMA_KEEP_ALIVE=0"
```

```sh
sudo systemctl daemon-reload
sudo systemctl restart ollama
systemctl show ollama -p Environment
sudo ss -ltnp 'sport = :11435'
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_API=http://127.0.0.1:11435
curl --noproxy '*' --fail --max-time 5 "$OLLAMA_API/api/version"
ollama list
```

Confirm the effective settings and listener. Old drop-ins can override new
settings; reconcile conflicting lines instead of assuming a filename wins.
Starting the service alone does not load a model. If the tags were not copied:

```sh
ollama pull qwen3.5:4b
ollama pull qwen3-coder:30b
```

Downloads need internet and free disk; they do not start inference. Record the
installed Ollama version. Windows measurements used version 0.40.16; an older
Mint install might not support the same cached model formats.

## 4. Optional LAN access from one trusted peer

Skip this section for a Cursor agent on this same Mint PC. For a remote agent,
inspect Mint's actual address and interface; dual boot may obtain a different IP:

```sh
ip -br -4 address
sudo ufw status numbered
```

The example below uses **server 192.168.1.10**, **client 192.168.1.20** and
**interface enp3s0**. Replace all three. Do not paste example values unchanged.
These instructions assume UFW is the firewall manager; inspect existing rules
and preserve required SSH/web access. Do not reset the firewall.

```sh
SERVER_IP=192.168.1.10
CLIENT_IP=192.168.1.20
LAN_IF=enp3s0
sudo ufw insert 1 allow in on "$LAN_IF" from "$CLIENT_IP" to "$SERVER_IP" port 11435 proto tcp
sudo ufw insert 2 deny in on "$LAN_IF" from any to "$SERVER_IP" port 11435 proto tcp
sudo ufw status numbered
```

The allow must precede the deny. If UFW is inactive, allow any SSH access you
depend on **before** `sudo ufw enable`; check your other services too. Enable and
verify the rules before exposing Ollama. Do not blindly add duplicates on reruns.

Edit only `OLLAMA_HOST` in the Mint drop-in to the actual `SERVER_IP:11435`, then:

```sh
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo ss -ltnp 'sport = :11435'
export OLLAMA_HOST="$SERVER_IP:11435"
export OLLAMA_API="http://$SERVER_IP:11435"
```

Verify the listener binds that address, not `0.0.0.0` or IPv6 wildcard. On the
approved peer, test `/api/version` and `/api/tags` at that actual IP. Native LAN
HTTP here has no added login or encryption; keep it between trusted machines.
No public HTTPS tunnel, router port-forward, or Cursor provider change is needed.
For any other reachable interfaces, keep loopback mode or scope their firewall
access too. Do not add a broad allow for port 11435.

## 5. Try the pair while watching memory

This section starts local inference/loading **only when you run it**. In another
terminal, watch available RAM and swap activity:

```sh
watch -n 2 free -h
# Separately if desired: vmstat 2
```

Below 2 GiB available, stop new inference and unload. Persistent swapping is a
reason to use one model at a time. These shell examples do **not** install an
automatic memory guard. Do not leave the first trial unattended.

Preload the large model, check memory, then try the small one. A ten-minute
keep-alive bounds this first residency experiment:

```sh
curl --noproxy '*' --fail --max-time 300 "$OLLAMA_API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-coder:30b","stream":false,"keep_alive":"10m","options":{"num_ctx":2048,"num_thread":4}}'
free -h
```

Continue only if RAM has room for the small model plus the reserve:

```sh
curl --noproxy '*' --fail --max-time 300 "$OLLAMA_API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5:4b","stream":false,"keep_alive":"10m","options":{"num_ctx":2048,"num_thread":4}}'
ollama ps
free -h
```

`ollama ps` must list **both** tags for simultaneous residency. If one disappears,
Ollama evicted it; model swapping is not evidence both fit. A timeout can leave
server work running: do not pile on retries. If the desktop becomes memory-bound,
`sudo systemctl stop ollama` stops this model service without closing other apps.

## 6. Give the supervising agent real tasks

For the ordinary, lower-memory recipe, use the repository client:

```sh
python3 -m local_worker_bench ask --endpoint "$OLLAMA_API" --tier fast --response-format text --prompt-file /tmp/small-task.txt --output /tmp/fast-first.json
python3 -m local_worker_bench ask --endpoint "$OLLAMA_API" --tier coder --response-format text --prompt-file /tmp/code-task.txt --output /tmp/coder-first.json
```

Create those bounded UTF-8 prompt files first and choose new output filenames for
each retry. For LAN endpoints also pass `--allow-lan`. Read the JSON receipt's
`content`; it is a draft, never executable authority. **This client unloads after
each request**, even if you preloaded the pair. That is the default, useful when
RAM is tight, and is separate from the warm-residency experiment.

To deliberately retain both, the supervisor can use native sequential `/api/chat`
requests instead. Example for the small helper:

```sh
curl --noproxy '*' --fail --max-time 300 "$OLLAMA_API/api/chat" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5:4b","stream":false,"think":false,"keep_alive":"10m","messages":[{"role":"user","content":"List three edge cases for a UTC timestamp parser. Be concise."}],"options":{"num_thread":4,"num_ctx":2048,"num_predict":384,"temperature":0}}'
```

Use `qwen3-coder:30b` for a bounded coding draft, typically at most 768 output
tokens initially. Save each request/reply and check `done`, `done_reason`, actual
content and real tests. `done_reason: length` is an incomplete draft. Never execute
the raw response. Keep credentials and whole repositories out of model prompts.

After observing stable RAM under real requests, the supervisor may explicitly
choose `keep_alive:-1` in **both models'** requests to retain them until unloading
or server exit. Do not equate residency with an active coding job. Keep global
request serialization: `OLLAMA_NUM_PARALLEL=1` applies per model, not across them.

Use [this agent handoff](prompts/linux-mint-local-worker-handoff.md). An unattended
queue/restart recovery is not implemented; [the supervisor outline](overnight-orchestration.md)
explains what remains. A hosted supervisor still consumes hosted usage.

## 7. Unload and stop

With `OLLAMA_HOST` still set to the correct server:

```sh
ollama stop qwen3.5:4b
ollama stop qwen3-coder:30b
ollama ps
sudo systemctl stop ollama
```

The Linux installer may enable startup at boot. Inspect with `systemctl is-enabled
ollama`; use `sudo systemctl disable ollama` if you want manual starts only, then
`sudo systemctl start ollama` when ready. No model deletion is needed.

If keeping the service for ordinary single-model use, change `MAX_LOADED_MODELS`
to 1 and keep `KEEP_ALIVE=0` in the dedicated drop-in, then reload/restart. Check
existing drop-ins rather than deleting unrelated configuration. A reboot into
Mint stops the Windows API; a reboot into Windows stops this Mint service.

## Sources and qualification

Based on [Ollama Linux installation](https://docs.ollama.com/linux),
[Ollama configuration/model storage/keep-alive FAQ](https://docs.ollama.com/faq),
[the generation API](https://docs.ollama.com/api/generate) and
[Ubuntu UFW documentation](https://documentation.ubuntu.com/server/how-to/security/firewalls/).
These are instructions for a future Mint setup, not a claim that Mint installation,
firewall isolation, two-model stability or overnight coding has been tested here.
