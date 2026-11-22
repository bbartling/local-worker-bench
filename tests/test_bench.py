"""All fixtures are synthetic. No Ollama process, download, or inference."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

from local_worker_bench import cases, cli, probe, reference, runner
from local_worker_bench.tasks import EXPECTED_FAILED, TASKS


class FixtureTests(unittest.TestCase):
    def test_all_95_controls(self):
        for name, count in [('motor', 49), ('elapsed', 46)]:
            fn = reference.motor_gate if name == 'motor' else reference.fault_hours
            result = cases.check_function(fn, name)
            self.assertEqual((result['passed'], result['total']), (count, count))

    def test_rejects_broken_functions(self):
        self.assertTrue(cases.check_function(lambda *a: 'ACTIVE', 'motor')['failures'])
        self.assertTrue(cases.check_function(lambda *a: (0., 0.), 'elapsed')['failures'])

    def test_io_filter(self):
        for source in ['import os', 'def motor_gate(*a):\n    return open("bad")',
                       'print("top level")']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                cases.inspect_source(source)

    def test_http_verdict_is_exact(self):
        good = {'failed_ids': EXPECTED_FAILED, 'full_three_way_pass': False}
        self.assertTrue(runner.http_pass(good))
        for bad in [None, [], {}, dict(good, full_three_way_pass=0),
                    dict(good, failed_ids=EXPECTED_FAILED[:-1])]:
            self.assertFalse(runner.http_pass(bad))

    def test_check_requires_exact_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'reviewed.py'
            source.write_text(inspect.getsource(reference.motor_gate), encoding='utf-8')
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(['check', '--task', 'motor', '--source', str(source),
                                           '--reviewed-sha256', sha]), 0)
                source.write_text(source.read_text(encoding='utf-8') + '\n', encoding='utf-8')
                self.assertEqual(cli.main(['check', '--task', 'motor', '--source', str(source),
                                           '--reviewed-sha256', sha]), 1)

    def test_hash_and_help(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'text.txt'
            source.write_text('sample', encoding='utf-8')
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cli.main(['hash', str(source)]), 0)
            self.assertEqual(out.getvalue().strip(), hashlib.sha256(b'sample').hexdigest())

    def test_candidate_timeout(self):
        with patch.object(cli.subprocess, 'run', side_effect=subprocess.TimeoutExpired('check', 15)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['check', '--task', 'motor', '--source', 'x.py',
                                       '--reviewed-sha256', '0' * 64]), 1)

    def test_lan_requires_opt_in_and_rejects_public_or_dns_targets(self):
        for host in ['10.1.2.3', '172.16.0.2', '172.31.255.2', '192.168.1.10']:
            endpoint = 'http://' + host + ':11435'
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    runner.endpoint_url(endpoint)
                self.assertEqual(runner.endpoint_url(endpoint, True), endpoint)
        for endpoint in ['http://8.8.8.8', 'http://172.32.0.2', 'http://169.254.1.1',
                         'http://example.com', 'http://192.168.1.10:99999',
                         'http://u:p@192.168.1.10', 'http://192.168.1.10/api',
                         'https://192.168.1.10']:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                runner.endpoint_url(endpoint, True)

    def test_supervisor_selects_tier_without_model_inference(self):
        for tier, model, tokens, timeout in [('fast', 'qwen3.5:4b', 384, 180),
                                           ('coder', 'qwen3-coder:30b', 640, 300)]:
            with self.subTest(tier=tier), patch.object(cli, 'ask', return_value=0) as helper:
                result = cli.main(['ask', '--tier', tier, '--prompt-file', 'synthetic.txt',
                                   '--output', 'candidate.json', '--endpoint',
                                   'http://192.168.1.10:11435', '--allow-lan'])
                self.assertEqual(result, 0)
                selected = helper.call_args.args[0]
                self.assertEqual((selected.model, selected.max_tokens, selected.timeout),
                                 (model, tokens, timeout))
                self.assertEqual(selected.threads, 4)
                self.assertTrue(selected.allow_lan)

    def test_default_tier_is_fast_and_overrides_are_preserved(self):
        with patch.object(cli, 'ask', return_value=0) as helper:
            cli.main(['ask', '--prompt-file', 'synthetic.txt', '--output', 'candidate.json'])
            self.assertEqual(helper.call_args.args[0].model, 'qwen3.5:4b')
            cli.main(['ask', '--tier', 'coder', '--max-tokens', '128', '--timeout', '60',
                      '--prompt-file', 'synthetic.txt', '--output', 'candidate.json'])
            self.assertEqual(helper.call_args.args[0].max_tokens, 128)
            self.assertEqual(helper.call_args.args[0].timeout, 60)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(['ask', '--tier', 'coder', '--model', 'test:tiny',
                      '--prompt-file', 'synthetic.txt', '--output', 'candidate.json'])

    def test_archive_checker_is_portable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'client.pyz'
            builder = Path(__file__).resolve().parents[1] / 'scripts/build_zipapp.py'
            subprocess.run([sys.executable, str(builder), '--output', str(archive)],
                           check=True, capture_output=True, text=True, timeout=15)
            source = root / 'reviewed.py'
            source.write_bytes(inspect.getsource(reference.motor_gate).encode('utf-8'))
            result = subprocess.run([sys.executable, str(archive), 'check', '--task', 'motor',
                '--source', str(source), '--reviewed-sha256', hashlib.sha256(source.read_bytes()).hexdigest()],
                cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['passed'], 49)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.calls = []
        self.mode = 'normal'
        self.task = 'http'
        self.api_patch = patch.object(runner, 'api', side_effect=self.api)
        self.api_patch.start()
        self.home_patch = patch.object(runner.Path, 'home', return_value=self.folder)
        self.home_patch.start()

    def tearDown(self):
        self.api_patch.stop()
        self.home_patch.stop()
        self.temp.cleanup()

    def api(self, endpoint, path, body=None, timeout=30):
        self.calls.append((path, body))
        if path == '/api/tags':
            return {'models': [] if self.mode == 'missing' else [{'name': 'test:tiny', 'digest': 'synthetic'}]}
        if path == '/api/generate':
            if self.mode == 'unload_error':
                raise OSError('unload failed')
            return {'done': True}
        self.assertEqual(body['options']['num_thread'], 4)
        self.assertEqual(body['keep_alive'], 0)
        self.assertFalse(body['stream'])
        if self.mode == 'network':
            raise urllib.error.URLError('synthetic timeout')
        if self.task in ('motor', 'elapsed'):
            content = json.dumps({'source': '# synthetic draft; never executed\n'})
        elif self.task == 'import':
            content = json.dumps({'root_cause': 'synthetic', 'minimal_fix': 'review me'})
        else:
            content = json.dumps({'failed_ids': EXPECTED_FAILED, 'full_three_way_pass': False})
        if self.mode == 'wrong_http':
            content = '{}'
        if self.mode == 'bad_json':
            content = '{broken'
        return {'done': True, 'done_reason': 'length' if self.mode == 'length' else 'stop',
                'message': {'content': content, 'thinking': 'must not persist'}}

    def trial(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return cli.main(['run', '--model', 'test:tiny', '--tasks', self.task,
                             '--output', str(self.folder / 'out')])

    def report(self):
        return json.loads((self.folder / 'out/report.json').read_text(encoding='utf-8'))

    def test_normal_http(self):
        self.assertEqual(self.trial(), 0)
        result = self.report()
        self.assertTrue(result['generation_complete'])
        self.assertTrue(result['results'][0]['passed'])
        self.assertFalse(result['code_executed'])
        self.assertEqual(self.calls[-1][0], '/api/generate')
        self.assertNotIn('must not persist', json.dumps(result))

    def test_coding_only_writes_source(self):
        self.task = 'motor'
        self.assertEqual(self.trial(), 0)
        self.assertEqual(self.report()['results'][0]['status'], 'needs_review')
        self.assertTrue((self.folder / 'out/motor.py').exists())
        self.assertFalse(self.report()['code_executed'])
        self.assertEqual(self.report()['results'][0]['source_sha256'],
                         hashlib.sha256((self.folder / 'out/motor.py').read_bytes()).hexdigest())
        self.assertEqual(self.report()['results'][0]['prompt_sha256'],
                         hashlib.sha256((self.folder / 'out/motor.prompt.txt').read_bytes()).hexdigest())

    def test_timeout_stops_remaining_tasks(self):
        self.mode = 'network'
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(['run', '--model', 'test:tiny', '--tasks', 'http', 'motor',
                             '--output', str(self.folder / 'out')])
        self.assertEqual(code, 1)
        self.assertEqual(len(self.report()['results']), 1)
        self.assertFalse(self.report()['generation_complete'])
        self.assertEqual([p for p, _ in self.calls], ['/api/tags', '/api/chat', '/api/generate'])

    def helper(self, prompt='Return a small synthetic JSON candidate.'):
        source = self.folder / 'prompt.txt'
        source.write_text(prompt, encoding='utf-8')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return cli.main(['ask', '--model', 'test:tiny', '--prompt-file', str(source),
                             '--output', str(self.folder / 'candidate.json')])

    def test_helper_candidate_never_executed_and_unloads(self):
        self.assertEqual(self.helper(), 0)
        result = json.loads((self.folder / 'candidate.json').read_text(encoding='utf-8'))
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['code_executed'])
        self.assertTrue(result['unload_requested'])
        self.assertEqual(self.calls[-1][0], '/api/generate')

    def test_helper_prompt_limit_and_existing_output(self):
        self.assertEqual(self.helper('x' * 12001), 1)
        self.assertFalse(self.calls)
        self.assertEqual(self.helper(), 0)
        original = (self.folder / 'candidate.json').read_bytes()
        self.assertEqual(self.helper(), 1)
        self.assertEqual(original, (self.folder / 'candidate.json').read_bytes())

    def test_helper_timeout_and_truncation_fail(self):
        for mode in ['network', 'length', 'bad_json', 'unload_error']:
            with self.subTest(mode=mode):
                self.mode = mode
                self.assertEqual(self.helper(), 1)
                self.assertEqual(self.calls[-1][0], '/api/generate')
                (self.folder / 'candidate.json').unlink()

    def test_incomplete_and_failed_requests_unload(self):
        for mode in ['length', 'bad_json', 'network']:
            with self.subTest(mode=mode):
                self.mode = mode
                # Each trial intentionally has a fresh output directory.
                out = self.folder / mode
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = cli.main(['run', '--model', 'test:tiny', '--tasks', self.task, '--output', str(out)])
                self.assertEqual(code, 1)
                report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
                self.assertFalse(report['generation_complete'])
                self.assertTrue(report['unload_requested'])

    def test_missing_model_never_calls_inference(self):
        self.mode = 'missing'
        self.assertEqual(self.trial(), 1)
        self.assertEqual([path for path, _ in self.calls], ['/api/tags'])

    def test_wrong_verdict_nonzero(self):
        self.mode = 'wrong_http'
        self.assertEqual(self.trial(), 1)
        self.assertFalse(self.report()['results'][0]['passed'])

    def test_unload_error_nonzero(self):
        self.mode = 'unload_error'
        self.assertEqual(self.trial(), 1)
        self.assertFalse(self.report()['unload_requested'])

    def test_existing_output_untouched(self):
        self.assertEqual(self.trial(), 0)
        original = (self.folder / 'out/report.json').read_bytes()
        self.assertEqual(self.trial(), 1)
        self.assertEqual(original, (self.folder / 'out/report.json').read_bytes())

    def test_lock_serializes_and_releases(self):
        with runner.worker_lock():
            with self.assertRaises(ValueError):
                with runner.worker_lock():
                    self.fail('nested worker admitted')
        with runner.worker_lock():
            pass

    def test_rejects_nonlocal_endpoint(self):
        for endpoint in ['https://example.com', 'http://localhost/redirect',
                         'http://user:pass@localhost', 'http://localhost?target=x']:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                runner.endpoint_url(endpoint)


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                status, body = {
                    '/healthy': (200, b'{"ok":true,"id":"A"}'),
                    '/unauthorized': (401, b'{"detail":"required"}'),
                    '/redirect': (302, b''),
                    '/soft_error': (200, b'{"ok":false}'),
                    '/array': (200, b'[]'),
                    '/html': (200, b'<html>login</html>'),
                    '/large': (200, b'x' * (1048576 + 1)),
                }[self.path]
                self.send_response(status)
                self.send_header('Location', '/healthy')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def get(self, path, **kw):
        return probe.probe(dict(url=self.base + path, expect_json=True, **kw))

    def test_real_http_status_json_and_id(self):
        self.assertTrue(self.get('/healthy', expected_id='A')['passed'])
        self.assertFalse(self.get('/healthy', expected_id='B')['passed'])
        self.assertTrue(self.get('/unauthorized', expected_statuses=[401])['passed'])
        for path in ['/soft_error', '/array', '/html', '/large']:
            with self.subTest(path=path):
                self.assertFalse(self.get(path)['passed'])

    def test_redirect_is_not_followed(self):
        result = self.get('/redirect')
        self.assertEqual(result['status'], 302)
        self.assertFalse(result['passed'])
        self.assertFalse(result['browser_tested'])

    def test_head(self):
        self.assertTrue(probe.probe({'url': self.base + '/healthy', 'method': 'HEAD'})['passed'])

    def test_network_failure(self):
        with patch.object(probe.urllib.request.OpenerDirector, 'open', side_effect=urllib.error.URLError('offline')):
            result = self.get('/healthy')
        self.assertFalse(result['passed'])
        self.assertEqual(result['errors'], ['network'])

    def test_methods_and_credentials_refused(self):
        for spec in [dict(url=self.base, method='POST'), dict(url='file:///etc/passwd'),
                     dict(url='http://user:pass@localhost'), dict(url=self.base, expected_statuses=[True])]:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                probe.probe(spec)


if __name__ == '__main__':
    unittest.main()
