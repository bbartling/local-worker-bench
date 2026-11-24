"""Which GGUF aliases are verified vs still downloading. No inference."""
from pathlib import Path
import json
import time

# Cache directory name under results/model-cache (may differ from API alias).
MODEL_CACHES = {
    'qwen38-q4': 'qwen38-q4',
    'qwen38-standard-q4': 'qwen38-standard-q4',
    'qwen38-f16': 'qwen38-f16',
    'qwen38-bf16': 'qwen38-bf16',
    'coder-next-q4': 'qwen3-coder-next-q4',
    'coder-next-f16': 'coder-next-f16',
    'coder-next-bf16': 'coder-next-bf16',
}

# Test ready artifacts first; unfinished downloads later (hour sleep when due).
WAVE_READY_FIRST = (
    'coder-next-q4',      # Qwen-published Q4; pair with F16
    'coder-next-f16',     # Qwen-published FP16
    'qwen38-q4',          # Unsloth UD-Q4 appendix (not the standard-Q4 column)
    'qwen38-bf16',        # verified; prior motor timed out — feasibility probe only
)
WAVE_AFTER_DOWNLOAD = (
    'qwen38-standard-q4', # prithivMLmods standard Q4 control
    'qwen38-f16',         # matched FP16 for that Q4
    'coder-next-bf16',    # Unsloth BF16 side arm
)


def cache_root(repo: Path) -> Path:
    return Path(repo) / 'results' / 'model-cache'


def status(repo: Path, alias: str) -> dict:
    if alias not in MODEL_CACHES:
        raise ValueError('Unknown model alias: ' + alias)
    folder = cache_root(repo) / MODEL_CACHES[alias]
    out = {'alias': alias, 'cache': MODEL_CACHES[alias], 'verified': False, 'pct': None}
    status_path = folder / 'download-status.json'
    verified_path = folder / 'verified-manifest.json'
    if status_path.is_file():
        raw = json.loads(status_path.read_text(encoding='utf-8'))
        total = raw.get('total_bytes') or 0
        done = raw.get('completed_bytes') or 0
        out['completed_bytes'] = done
        out['total_bytes'] = total
        out['pct'] = round(100.0 * done / total, 1) if total else None
        out['errors'] = list(raw.get('errors') or [])
    if verified_path.is_file():
        manifest = json.loads(verified_path.read_text(encoding='utf-8'))
        out['verified'] = manifest.get('all_sha256_verified') is True
        out['repo'] = manifest.get('repo')
        out['revision'] = manifest.get('revision')
    return out


def partition(repo: Path, aliases=None) -> dict:
    aliases = list(aliases) if aliases is not None else list(WAVE_READY_FIRST) + list(WAVE_AFTER_DOWNLOAD)
    ready, waiting = [], []
    for alias in aliases:
        item = status(repo, alias)
        (ready if item['verified'] else waiting).append(item)
    return {'ready': ready, 'waiting': waiting, 'order': aliases}


def wait_until_verified(repo: Path, alias: str, *, poll_seconds=3600, deadline_epoch=None,
                        stop_paths=(), on_poll=None) -> bool:
    """Block until verified-manifest exists. Hour-long polls by default. Returns False on stop/deadline."""
    if poll_seconds < 1:
        raise ValueError('poll_seconds must be >= 1')
    while True:
        if any(Path(p).exists() for p in stop_paths):
            return False
        if deadline_epoch is not None and time.time() >= deadline_epoch:
            return False
        if status(repo, alias)['verified']:
            return True
        if on_poll:
            on_poll(alias, status(repo, alias))
        # Sleep in one long cycle; wake early only via process kill / next iteration checks after sleep.
        remaining = poll_seconds
        if deadline_epoch is not None:
            remaining = min(remaining, max(0, deadline_epoch - time.time()))
        if remaining <= 0:
            return False
        time.sleep(remaining)
