# Reuse Windows models on Linux Mint

The Ubuntu service/firewall steps in [the LAN guide](ollama-lan-setup.md) also
apply to standard Ubuntu-based Linux Mint. This page covers moving existing
models instead of downloading them again. It is a recipe, not a tested Mint
installation; no Linux model server was installed during the Windows setup.

For an end-to-end 4B Q4 + 30B Q4 recipe, including installation, loopback or scoped
LAN/firewall setup, residency trials and cleanup, start with the
[Mint setup checklist](linux-mint-4b-30b-setup.md).

## Find the Windows cache

On Windows, models normally live at:

```text
C:\Users\YOUR_WINDOWS_USER\.ollama\models
```

After booting Mint and opening the mounted Windows drive, press **Ctrl+H** in
the file manager to show dot folders. A typical mounted path looks like:

```text
/media/YOUR_LINUX_USER/Windows/Users/YOUR_WINDOWS_USER/.ollama/models
```

The actual mount name may differ. Copy the **models directory**, including both
`blobs` (weights) and `manifests` (model names/metadata). Do not copy just a blob
or the entire `.ollama` folder with its identity keys. There is no model format
conversion merely because the serving OS changes. Install an Ollama version
that supports the cached models, preferably the same or newer compatible release.

## Copy to a Linux-native directory

Use a native Linux filesystem for the live cache, so ownership and boot-time
mounting do not depend on the Windows drive. Reading the mounted source is enough;
do not change its Windows files or ownership. Install Ollama first, then:

```sh
SOURCE_MODELS='/media/YOUR_LINUX_USER/Windows/Users/YOUR_WINDOWS_USER/.ollama/models'
TARGET_MODELS=/var/lib/ollama/models
sudo systemctl stop ollama
sudo install -d -o ollama -g ollama "$TARGET_MODELS"
sudo rsync -rlt --info=progress2 "$SOURCE_MODELS/" "$TARGET_MODELS/"
sudo chown -R ollama:ollama /var/lib/ollama/models
```

Inspect an existing destination before copying into it. No `--delete` is used.
The recursive ownership command targets only the Linux cache, never the Windows
mount. The default Linux service cache is normally elsewhere; set `OLLAMA_MODELS`
explicitly as described in [Ollama's model-storage FAQ](https://docs.ollama.com/faq#where-are-models-stored).

Add this dedicated service override; inspect it first if it already exists:

```sh
sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/local-model-cache.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Apply the LAN/firewall configuration from the companion guide. Then check the
running server's `/api/tags` for both `qwen3.5:4b` and `qwen3-coder:30b`. Missing
tags usually mean missing manifests, a wrong cache path, or service permissions.
Ollama's Linux service user must be able to read/write the chosen cache.

## Overnight use

Dual boot runs one OS at a time: booting Mint stops the Windows server. Verify
Mint's actual address with `ip -br -4 address`; do not assume the Windows IP is
reused. Update the client URL/firewall if it differs. The same `--tier fast` and
`--tier coder` requests work once the Linux API is reachable.

A lighter desktop may leave more available RAM, but the CPU, RAM capacity and
model weights are unchanged. Start with one model/request, 2,048 context and
four threads. Measure rather than assume a speed improvement. If the PC is
dedicated overnight, higher thread counts can be tested under explicit task
authorization. Keeping the API idle does not start an overnight inference job;
the supervising agent still needs bounded tasks, checkpoints and stop criteria.

Model weights belong in the model cache, not this Git repository.
