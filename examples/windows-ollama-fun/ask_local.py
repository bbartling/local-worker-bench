"""One supervised draft request to the already-running Ollama API. No code execution."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

MODELS = {'fast': 'qwen3.5:4b', 'medium': 'qwen2.5-coder:7b-instruct-fp16'}
ENDPOINT = 'http://192.168.204.11:11435'


def available_gib():
    if os.name != 'nt':
        raise RuntimeError('This experiment client checks Windows RAM; run it on the Windows host.')
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ('total', 'available', 'page_total',
            'page_available', 'virtual_total', 'virtual_available', 'extended')]
    info = Memory()
    info.length = ctypes.sizeof(info)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info)):
        raise OSError('Cannot read Windows available physical RAM')
    return info.available / 1024**3


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tier', choices=MODELS, required=True)
    p.add_argument('--prompt-file', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-output', type=int)
    args = p.parse_args()
    prompt = args.prompt_file.read_text(encoding='utf-8-sig')
    # Character cap is only an early check. Keep excerpts small for the 2,048-token context.
    if not prompt.strip() or len(prompt) > 6000:
        p.error('Use a nonempty bounded prompt, at most 6,000 characters.')
    limit = args.max_output if args.max_output is not None else (384 if args.tier == 'fast' else 768)
    if not 1 <= limit <= 1024:
        p.error('--max-output must be 1 through 1024; split larger work into functions.')
    if args.output.exists():
        p.error('Output receipt exists; use a new name to preserve first-pass evidence.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock = Path.home() / '.cache' / 'local-worker-bench' / 'inference.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        p.error(f'Another worker owns {lock}. Wait; verify its PID before removing a stale lock.')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'pid': os.getpid(), 'purpose': 'Cursor warm-pair experiment'}, f)
        free = available_gib()
        if free < 2:
            raise RuntimeError(f'Only {free:.2f} GiB available; stop and free RAM before requesting inference.')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def call(path, body=None):
            request = urllib.request.Request(ENDPOINT + path,
                data=json.dumps(body).encode('utf-8') if body is not None else None,
                headers={'Content-Type': 'application/json'})
            with opener.open(request, timeout=600) as response:
                value = json.load(response)
            if value.get('error'):
                raise RuntimeError(str(value['error']))
            return value

        model = MODELS[args.tier]
        cached = {m['name'] for m in call('/api/tags')['models']}
        if model not in cached:
            raise RuntimeError('Required model is not cached. No automatic downloads.')
        resident = {m['name'] for m in call('/api/ps')['models']}
        if resident - set(MODELS.values()):
            raise RuntimeError('Another model is resident. Refusing to evict an unrelated job.')
        if not set(MODELS.values()).issubset(resident):
            raise RuntimeError('Both experiment models must already be loaded. Read setup-status.json; do not auto-load.')
        began = time.monotonic()
        reply = call('/api/chat', {'model': model, 'stream': False, 'think': False,
            'keep_alive': -1,
            'messages': [{'role': 'system', 'content':
                'Return only the requested draft or answer. You cannot run tests or tools. Do not claim execution.'},
                {'role': 'user', 'content': prompt}],
            'options': {'num_thread': 4, 'num_ctx': 2048, 'num_predict': limit, 'temperature': 0}})
        content = reply.get('message', {}).get('content', '')
        inventory = call('/api/ps')
        both = set(MODELS.values()).issubset({m['name'] for m in inventory['models']})
        complete = bool(reply.get('done')) and reply.get('done_reason') != 'length' and bool(content.strip())
        receipt = {'model': model, 'tier': args.tier, 'endpoint': ENDPOINT,
            'seconds': round(time.monotonic() - began, 2),
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'threads': 4, 'context': 2048, 'max_output': limit, 'keep_alive': -1,
            'free_before_gib': round(free, 3), 'free_after_gib': round(available_gib(), 3),
            'complete': complete, 'both_resident_after': both, 'reply': reply}
        args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'receipt': str(args.output.resolve()), 'model': model,
                          'complete': complete, 'both_resident_after': both,
                          'seconds': receipt['seconds']}, ensure_ascii=False))
        return 0 if complete and both and receipt['free_after_gib'] >= 2 else 2
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f'Local request failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
