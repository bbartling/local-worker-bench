# Mint LAN: 4B Q4 + 30B Q4 locked defaults

**Both models stayed resident on Linux Mint with LAN access from a trusted peer.**
RAM is **tight**: about **5.4 GiB available** right after preload, later samples
near **4.3 GiB available** with a little swap in use (~0.3 GiB). That is enough
headroom to keep trying **local assistance orchestrated by an enterprise
supervisor** (Cursor/Codex/Claude picks `--tier fast` or `--tier coder`), but not
comfortable for a busy shared desktop or long contexts. Stop new inference below
about 2 GiB available. Extra cached tags were removed afterward; boot warmup was
enabled so the pair reloads after reboot.

## Host and peer

| Item | Value |
| --- | --- |
| Server | Linux Mint 22.3, OptiPlex (`ben-OptiPlex-7070`), i7 class, 32 GB RAM, CPU only |
| Server address | `192.168.204.11` on `eno1` |
| Ollama | 0.40.17, systemd user `ollama` |
| API | `http://192.168.204.11:11435` |
| Peer client | `192.168.204.16` (`ben-desktop`), UFW allow only that IPv4 to port 11435 |
| Models path | `/var/lib/ollama/models` (rsync from Windows `Users/ben/.ollama/models`) |

## Locked service defaults

```text
OLLAMA_HOST=192.168.204.11:11435
OLLAMA_MODELS=/var/lib/ollama/models
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=-1
OLLAMA_CONTEXT_LENGTH=2048
OLLAMA_NO_CLOUD=true
```

Drop-ins: `local-worker-lan.conf` and `local-model-cache.conf`. Boot oneshot
`ollama-warmup-pair.service` preloads `qwen3-coder:30b` then `qwen3.5:4b` with
`keep_alive:-1` after `ollama.service` is up.

## Cache after prune

Kept:

- `qwen3.5:4b` (`d8b0f5e9760c`, ~3.3 GB)
- `qwen3-coder:30b` (`06c1097efce0`, ~18 GB)

Removed from the Mint cache (still recoverable from the Windows dual-boot copy):

- `qwen2.5-coder:7b-instruct-q8_0`
- `qwen2.5-coder:7b-instruct-fp16`
- `qwen2.5-coder:0.5b-instruct-fp16`
- `qwen-local-codex:latest`

## Residency check

| Observation | Result |
| --- | --- |
| `ollama ps` | Both tags listed, 2048 context, CPU, Until Forever |
| Approximate in-RAM sizes | 4B ~3.1 GB; 30B ~18 GB |
| Available RAM after both loaded | ~5.4 GiB initially; ~4.3 GiB on a later sample |
| Swap | Idle at first check; ~0.3 GiB used on the later sample |
| Peer `/api/version` and `/api/tags` from `.16` | Succeeded |
| Practical fit | Tight but usable for enterprise-orchestrated local assist; not a free RAM cushion |

UFW note: on an inactive empty firewall, `ufw insert 1` fails; use plain
`ufw allow` / `ufw deny`, allow SSH first, then enable.

## Client routing

From the peer, same endpoint for both tiers with `--allow-lan`:

- `--tier fast` → `qwen3.5:4b`
- `--tier coder` → `qwen3-coder:30b`

The portable `ask` client still sends unload-after-request unless overridden.
Warm switching without reload depends on the server keep-alive and on clients
that do not force `keep_alive:0`.

## Qualification

This records a successful Mint install, model migration, LAN firewall bind,
dual residency, cache prune, and boot-warmup enablement. The machine is
effectively **RAM-bound** with both helpers warm; treat local models as
draft/assist tools under an enterprise supervisor, not as an unsupervised coding
service. It does not claim overnight unattended quality or guaranteed hosted-API
savings. Follow [the Mint setup checklist](../linux-mint-4b-30b-setup.md).
