"""Durable Suite-3 six-format matrix: Wave A now, Wave B after hour-sleep downloads.

Does not execute generated code or accept patches. STOP in --output cancels.
Requires INFERENCE_PAUSED absent (explicit user resume).
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_worker_bench.model_readiness import wait_until_verified
from local_worker_bench.pause import require_benchmark_enabled

# Fair crown: 2 families x Q4 / FP16 / BF16. UD Q4 is not in this table.
WAVE_A = ('coder-next-q4', 'coder-next-f16', 'qwen38-standard-q4', 'qwen38-bf16')
WAVE_B = ('qwen38-f16', 'coder-next-bf16')


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temp.replace(path)


def cancelled(output):
    return (output / 'STOP').exists() or (ROOT / 'INFERENCE_PAUSED').exists()


def run(cmd, log_path, timeout=None):
    with log_path.open('w', encoding='utf-8') as log:
        return subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)


def prepare_and_run(backend, output, models, wave_name, port, poll_seconds, wave_hours, state):
    setup = output / f'{wave_name}-setup'
    matrix = output / f'{wave_name}-matrix'
    state['state'] = f'preparing_{wave_name}'
    state['models'] = list(models)
    save(output / 'handoff.json', state)
    if setup.exists():
        raise RuntimeError('Setup folder already exists: ' + str(setup))
    prep = [
        sys.executable, str(ROOT / 'scripts/prepare_project_bench.py'),
        '--backend', str(backend), '--output', str(setup),
        '--timeout', '7200', '--max-tokens', '2048',
        '--models', *models,
    ]
    if run(prep, output / f'{wave_name}-prepare.log', timeout=600).returncode:
        raise RuntimeError(wave_name + ' prepare failed; see log')
    if cancelled(output):
        state['state'] = 'cancelled'
        save(output / 'handoff.json', state)
        return 0
    state['state'] = f'running_{wave_name}'
    save(output / 'handoff.json', state)
    campaign = [
        sys.executable, '-u', str(ROOT / 'scripts/run_project_bench.py'),
        '--config', str(setup / 'api-config.json'),
        '--output', str(matrix),
        '--models', *models,
        '--timeout', '7200', '--max-tokens', '2048',
        '--memory-fraction', '.66',
        '--prompt-version', '2',
        '--port', str(port),
        '--hours', str(wave_hours),
    ]
    with (output / f'{wave_name}-matrix.out.log').open('w', encoding='utf-8') as out, \
            (output / f'{wave_name}-matrix.err.log').open('w', encoding='utf-8') as err:
        child = subprocess.Popen(
            campaign, cwd=ROOT, stdout=out, stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        state['matrix_pid'] = child.pid
        save(output / 'handoff.json', state)
        while child.poll() is None:
            if cancelled(output) and matrix.exists():
                (matrix / 'STOP').touch()
            time.sleep(30)
        state[f'{wave_name}_exit'] = child.returncode
        state.pop('matrix_pid', None)
        save(output / 'handoff.json', state)
        return child.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--port-a', type=int, default=11441)
    p.add_argument('--port-b', type=int, default=11442)
    p.add_argument('--poll-seconds', type=int, default=3600)
    p.add_argument('--wave-hours', type=float, default=48, help='Campaign wall ceiling per wave (max 72)')
    p.add_argument('--wait-hours', type=float, default=168)
    args = p.parse_args()
    require_benchmark_enabled(ROOT)
    if not 60 <= args.poll_seconds <= 3600:
        raise ValueError('poll-seconds 60..3600')
    if not args.backend.is_file():
        raise ValueError('Backend missing')
    args.output.mkdir(parents=True, exist_ok=False)
    deadline = time.time() + args.wait_hours * 3600
    state = {
        'state': 'starting',
        'started_epoch': time.time(),
        'deadline_epoch': deadline,
        'wave_a': list(WAVE_A),
        'wave_b': list(WAVE_B),
        'suite_version': 3,
        'request_timeout': 7200,
        'max_tokens': 2048,
        'memory_fraction': 0.66,
        'poll_seconds': args.poll_seconds,
        'note': 'Download I/O may contend with Wave A timing; disclose in publication.',
        'generated_code_executed': False,
        'automatic_acceptance': False,
    }
    save(args.output / 'handoff.json', state)

    # Ensure Wave A verified (should already be); hour-sleep if not.
    for model in WAVE_A:
        if cancelled(args.output):
            state['state'] = 'cancelled'
            save(args.output / 'handoff.json', state)
            return 0
        state['state'] = 'waiting_for_' + model
        save(args.output / 'handoff.json', state)
        if not wait_until_verified(
            ROOT, model, poll_seconds=args.poll_seconds, deadline_epoch=deadline,
            stop_paths=(args.output / 'STOP', ROOT / 'INFERENCE_PAUSED'),
        ):
            state['state'] = 'cancelled' if cancelled(args.output) else 'wait_deadline'
            save(args.output / 'handoff.json', state)
            return 0

    code_a = prepare_and_run(
        args.backend.resolve(), args.output, WAVE_A, 'waveA',
        args.port_a, args.poll_seconds, args.wave_hours, state,
    )
    if cancelled(args.output):
        state['state'] = 'cancelled'
        save(args.output / 'handoff.json', state)
        return 0

    for model in WAVE_B:
        if cancelled(args.output):
            state['state'] = 'cancelled'
            save(args.output / 'handoff.json', state)
            return 0
        state['state'] = 'waiting_for_' + model
        save(args.output / 'handoff.json', state)
        if not wait_until_verified(
            ROOT, model, poll_seconds=args.poll_seconds, deadline_epoch=deadline,
            stop_paths=(args.output / 'STOP', ROOT / 'INFERENCE_PAUSED'),
        ):
            state['state'] = 'cancelled' if cancelled(args.output) else 'wait_deadline'
            save(args.output / 'handoff.json', state)
            return code_a or 1

    code_b = prepare_and_run(
        args.backend.resolve(), args.output, WAVE_B, 'waveB',
        args.port_b, args.poll_seconds, args.wave_hours, state,
    )
    state.update(state='finished', finished_epoch=time.time(), waveA_exit=code_a, waveB_exit=code_b)
    save(args.output / 'handoff.json', state)
    return code_a or code_b


if __name__ == '__main__':
    raise SystemExit(main())
