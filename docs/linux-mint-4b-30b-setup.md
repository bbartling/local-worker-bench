# Linux Mint: 4B Q4 + 30B Q4 local helpers

Use this for an Ubuntu-based Linux Mint installation on the same dual-boot PC.
**Locked Mint LAN defaults (validated 2026-11-22):** keep only `qwen3.5:4b` and
`qwen3-coder:30b` in the cache; bind the OptiPlex LAN address on port **11435**;
`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=-1`, four threads, 2,048 context,
one request at a time; preload both after boot. See
[the Mint LAN dual-resident note](benchmarks/2026-11-22-mint-lan-dual-resident.md).

Windows earlier briefly held both before a two-GiB reserve guard stopped the
test. Mint held both with about **5.4 GiB available** after preload (later
samples nearer **4 GiB**, with a little swap). That is **tight / nearly out of
comfortable headroom**, but can still be good enough for **local assistance
orchestrated by an enterprise model**. Watch RAM on the shared desktop; stop
below about 2 GiB available. Do not assume overnight coding quality from
residency alone.

| Role | Ollama tag | Weight size (approx.) |
| --- | --- | --- |
| Small helper | `qwen3.5:4b` | about 3.3 GB, Q4 |
| Coding helper | `qwen3-coder:30b` | about 18 GB, Q4 |

Those are weight-file sizes, not total runtime RAM. A strong Cursor/Codex/Claude
supervisor reviews drafts, runs tests and makes edits. The portable
`local_worker_bench ask` client still unloads after each call unless you use raw
API keep-alive; warm residency is a **server** default on this Mint host.

For a lighter alternative, [4B + 7B Coder Q8](benchmarks/2026-11-22-q8-pair.md)
completed a brief Windows memory trial with 9.32 GiB free. That Q8 tag was
removed from the Mint cache when locking the 4B+30B defaults; restore from the
Windows dual-boot cache if needed. It is not the default `--tier coder` routing.

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
destination. Copying the whole cache may include FP16/Q8 experiments: check
source size and free target disk space first. After the two target tags work,
prune extras so the Mint cache holds only `qwen3.5:4b` and `qwen3-coder:30b`.
Copy only the `models` directory, not Ollama identity keys or private application
files. Leave Windows files alone.

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
Environment="OLLAMA_KEEP_ALIVE=-1"
```

`KEEP_ALIVE=-1` retains loaded models until explicit stop or service exit. Use
`KEEP_ALIVE=0` only when deliberately returning to unload-after-request.

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

Validated home-lab values (replace if DHCP changes): **server
`192.168.204.11`**, **client `192.168.204.16`**, **interface `eno1`**. Prefer a
DHCP reservation. These instructions assume UFW is the firewall manager; inspect
existing rules and preserve required SSH/web access. Do not reset the firewall.

```sh
SERVER_IP=192.168.204.11
CLIENT_IP=192.168.204.16
LAN_IF=eno1
# When UFW has no rules yet, do not use `insert 1` (it fails on an empty set).
sudo ufw allow 22/tcp
sudo ufw allow in on "$LAN_IF" from "$CLIENT_IP" to "$SERVER_IP" port 11435 proto tcp comment 'ollama-lan-client'
sudo ufw deny in on "$LAN_IF" from any to "$SERVER_IP" port 11435 proto tcp comment 'ollama-lan-deny-others'
sudo ufw status numbered
```

List the allow before the deny. If UFW is inactive, allow SSH **before**
`sudo ufw enable`; check your other services too. Enable and verify the rules
before exposing Ollama. Do not blindly add duplicates on reruns.

Put the LAN bind in the dedicated drop-in (models path + dual-resident defaults):

```ini
[Service]
Environment="OLLAMA_HOST=192.168.204.11:11435"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="OLLAMA_CONTEXT_LENGTH=2048"
Environment="OLLAMA_NO_CLOUD=true"
Environment="OLLAMA_DEBUG_LOG_REQUESTS=false"
```

Then:

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

Preload the large model, check memory, then try the small one. Locked Mint
defaults use indefinite keep-alive (`-1`); a ten-minute value is fine for a
bounded first trial:

```sh
curl --noproxy '*' --fail --max-time 600 "$OLLAMA_API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-coder:30b","stream":false,"keep_alive":-1,"options":{"num_ctx":2048,"num_thread":4,"num_predict":8}}'
free -h
```

Continue only if RAM has room for the small model plus the reserve:

```sh
curl --noproxy '*' --fail --max-time 300 "$OLLAMA_API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5:4b","stream":false,"keep_alive":-1,"options":{"num_ctx":2048,"num_thread":4,"num_predict":8}}'
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

On the locked Mint host, server `KEEP_ALIVE=-1` plus boot warmup already retain
the pair; supervisors should still send `keep_alive:-1` on raw `/api/chat` calls
when they want to avoid an unload from a client that defaults to zero. Do not
equate residency with an active coding job. Keep global request serialization:
`OLLAMA_NUM_PARALLEL=1` applies per model, not across them.

Use [this agent handoff](prompts/linux-mint-local-worker-handoff.md). An unattended
queue/restart recovery is not implemented; [the supervisor outline](overnight-orchestration.md)
explains what remains. A hosted supervisor still consumes hosted usage.

## 7. Boot warmup (locked default)

Ollama starts idle. To reload both tags after boot without waiting for the first
Cursor request, enable a oneshot after `ollama.service`:

```sh
sudo tee /usr/local/sbin/ollama-warmup-pair.sh >/dev/null <<'WARM'
#!/usr/bin/env bash
set -euo pipefail
API=http://192.168.204.11:11435
for i in $(seq 1 60); do
  curl -fsS --max-time 2 "$API/api/version" >/dev/null && break
  sleep 2
done
curl -fsS --noproxy '*' --max-time 900 "$API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-coder:30b","prompt":"ping","stream":false,"keep_alive":-1,"options":{"num_ctx":2048,"num_thread":4,"num_predict":8}}' \
  >/dev/null
curl -fsS --noproxy '*' --max-time 300 "$API/api/generate" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5:4b","prompt":"ping","stream":false,"keep_alive":-1,"options":{"num_ctx":2048,"num_thread":4,"num_predict":8}}' \
  >/dev/null
WARM
sudo chmod 755 /usr/local/sbin/ollama-warmup-pair.sh

sudo tee /etc/systemd/system/ollama-warmup-pair.service >/dev/null <<'UNIT'
[Unit]
Description=Preload qwen3-coder:30b and qwen3.5:4b into Ollama
After=ollama.service network-online.target
Wants=ollama.service network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ollama-warmup-pair.sh
RemainAfterExit=yes
TimeoutStartSec=1200
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now ollama.service ollama-warmup-pair.service
```

CPU preload of the 30B can take several minutes. Confirm with `ollama ps` that
both tags show `Until: Forever` (or equivalent) and available RAM stays above
about 2 GiB.

## 8. Unload and stop

With `OLLAMA_HOST` still set to the correct server:

```sh
ollama stop qwen3.5:4b
ollama stop qwen3-coder:30b
ollama ps
sudo systemctl stop ollama-warmup-pair
sudo systemctl stop ollama
```

Inspect enablement with `systemctl is-enabled ollama ollama-warmup-pair`. Disable
the warmup unit if you no longer want boot preload. For ordinary single-model
use, set `MAX_LOADED_MODELS=1` and `KEEP_ALIVE=0` in the dedicated drop-in, then
reload/restart. A reboot into Mint stops the Windows API; a reboot into Windows
stops this Mint service.

## Sources and qualification

Based on [Ollama Linux installation](https://docs.ollama.com/linux),
[Ollama configuration/model storage/keep-alive FAQ](https://docs.ollama.com/faq),
[the generation API](https://docs.ollama.com/api/generate) and
[Ubuntu UFW documentation](https://documentation.ubuntu.com/server/how-to/security/firewalls/).
Mint install, Windows model copy, scoped UFW LAN bind, dual residency, cache
prune to the two default tags, and boot warmup were validated on this dual-boot
OptiPlex on 2026-11-22. Overnight unattended coding quality is still not claimed.
