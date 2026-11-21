"""Run offline fixture controls, explicit Ollama trials, or read-only HTTP probes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from . import cases, reference
from .probe import probe
from .runner import run, ask, write_json
from .tasks import TASKS


def bounded(low, high):
    def parse(value):
        result = int(value)
        if not low <= result <= high:
            raise argparse.ArgumentTypeError(f'Use {low} to {high}.')
        return result
    return parse


def selftest():
    results = [cases.check_function(reference.motor_gate, 'motor'),
               cases.check_function(reference.fault_hours, 'elapsed')]
    print(json.dumps({'fixture_controls': results, 'model_called': False}, indent=2))
    return 0 if all(not r['failures'] for r in results) else 1


def check_child(args):
    raw = args.source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.reviewed_sha256:
        raise ValueError('Source differs from the reviewed SHA-256; review the current file.')
    result = cases.execute_reviewed(raw.decode('utf-8'), args.task)
    result.update(source_sha256=digest, code_executed=True)
    print(json.dumps(result, indent=2))
    return 0 if not result['failures'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('selftest', help='95 offline cases against hand-written controls; no inference')
    digest = sub.add_parser('hash', help='SHA-256 of a file; does not execute it')
    digest.add_argument('source', type=Path)
    model = sub.add_parser('run', help='Explicit model calls; never executes generated code')
    model.add_argument('--model', required=True)
    model.add_argument('--endpoint', default='http://127.0.0.1:11434')
    model.add_argument('--tasks', nargs='+', choices=TASKS, default=list(TASKS))
    model.add_argument('--output', type=Path, default=Path('results') / 'trial')
    model.add_argument('--threads', type=bounded(1, 12), default=4)
    model.add_argument('--context', type=bounded(512, 8192), default=2048)
    model.add_argument('--max-tokens', type=bounded(64, 1024), default=640)
    model.add_argument('--timeout', type=bounded(5, 300), default=180)
    model.add_argument('--thinking', choices=('off', 'low', 'medium', 'high'), default='off')
    helper = sub.add_parser('ask', help='One bounded supervised draft; no code execution')
    helper.add_argument('--prompt-file', type=Path, required=True)
    helper.add_argument('--output', type=Path, required=True)
    helper.add_argument('--model', default='qwen3.5:4b')
    helper.add_argument('--endpoint', default='http://127.0.0.1:11434')
    helper.add_argument('--threads', type=bounded(1, 12), default=4)
    helper.add_argument('--context', type=bounded(512, 8192), default=2048)
    helper.add_argument('--max-tokens', type=bounded(64, 1024), default=384)
    helper.add_argument('--timeout', type=bounded(5, 300), default=180)
    helper.add_argument('--thinking', choices=('off', 'low', 'medium', 'high'), default='off')
    for name in ('check', '_check'):
        checker = sub.add_parser(name, help='Execute a manually reviewed candidate (not a sandbox)')
        checker.add_argument('--task', choices=('motor', 'elapsed'), required=True)
        checker.add_argument('--source', type=Path, required=True)
        checker.add_argument('--reviewed-sha256', required=True)
    http = sub.add_parser('probe', help='One read-only GET/HEAD; does not prove browser behavior')
    http.add_argument('--url', required=True)
    http.add_argument('--method', choices=('GET', 'HEAD'), default='GET')
    http.add_argument('--expected', nargs='+', type=int, default=[200])
    http.add_argument('--expect-json', action='store_true', help='Require a JSON object')
    http.add_argument('--expected-id')
    http.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'selftest':
            return selftest()
        if args.command == 'hash':
            print(hashlib.sha256(args.source.read_bytes()).hexdigest())
            return 0
        if args.command == 'ask':
            return ask(args)
        if args.command == 'run':
            if len(set(args.tasks)) != len(args.tasks):
                raise ValueError('Each task may occur only once per run.')
            return run(args)
        if args.command == '_check':
            return check_child(args)
        if args.command == 'check':
            process = subprocess.run([sys.executable, '-m', 'local_worker_bench', '_check',
                '--task', args.task, '--source', str(args.source.resolve()),
                '--reviewed-sha256', args.reviewed_sha256], timeout=15, check=False,
                encoding='utf-8', capture_output=True)
            print(process.stdout, end='')
            if process.stderr:
                print(process.stderr, file=sys.stderr, end='')
            return process.returncode
        spec = {'url': args.url, 'method': args.method, 'expected_statuses': args.expected,
                'expect_json': args.expect_json}
        if args.expected_id is not None:
            spec['expected_id'] = args.expected_id
        result = probe(spec)
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
