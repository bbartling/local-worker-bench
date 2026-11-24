import unittest
from pathlib import Path
from unittest import mock

from local_worker_bench.model_readiness import WAVE_AFTER_DOWNLOAD, WAVE_READY_FIRST, partition, status


class ModelReadinessTests(unittest.TestCase):
    def test_wave_order_puts_downloads_after_ready_aliases(self):
        self.assertIn('coder-next-q4', WAVE_READY_FIRST)
        self.assertIn('qwen38-standard-q4', WAVE_AFTER_DOWNLOAD)
        self.assertNotIn('qwen38-standard-q4', WAVE_READY_FIRST)

    def test_partition_uses_verified_manifest(self):
        repo = Path('C:/fake-repo')
        def fake_status(root, alias):
            return {'alias': alias, 'verified': alias in ('coder-next-q4', 'coder-next-f16'), 'pct': 100 if alias.startswith('coder') else 10}
        with mock.patch('local_worker_bench.model_readiness.status', side_effect=fake_status):
            report = partition(repo, ['coder-next-q4', 'qwen38-f16', 'coder-next-f16'])
        self.assertEqual([x['alias'] for x in report['ready']], ['coder-next-q4', 'coder-next-f16'])
        self.assertEqual([x['alias'] for x in report['waiting']], ['qwen38-f16'])


if __name__ == '__main__':
    unittest.main()
