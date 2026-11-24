import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.run_paging_campaign import main
from local_worker_bench.runner import worker_lock


class CampaignTests(unittest.TestCase):
    def setUp(self):
        # These tests use fake workers and intentionally exercise lifecycle while
        # the real repository remains paused; pause integration is tested separately.
        guard=patch('scripts.run_paging_campaign.require_benchmark_enabled')
        guard.start();self.addCleanup(guard.stop)

    def test_busy_worker_waits_without_claiming_then_honors_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);leases=root/'.cache/local-worker-bench';leases.mkdir(parents=True)
            (leases/'inference.lock').write_text('synthetic worker')
            args=['campaign','--backend',sys.executable,'--output',directory,'--port','0','--models','qwen38-q4']
            with patch.object(sys,'argv',args),patch('local_worker_bench.runner.Path.home',return_value=root), \
                    patch('scripts.run_paging_campaign.subprocess.check_output',return_value='synthetic'), \
                    patch('scripts.run_paging_campaign.time.sleep',side_effect=lambda _: (root/'STOP').touch()), \
                    patch('local_worker_bench.offload_api.subprocess.Popen') as spawn:
                self.assertEqual(main(),0)
            spawn.assert_not_called();state=json.loads((root/'campaign.json').read_text())
            self.assertTrue(state['waiting_for_worker'])
            self.assertEqual(state['models']['qwen38-q4']['state'],'waiting_for_verified_download')

    def test_campaign_settings_cannot_change_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'STOP').touch()
            args=['campaign','--backend',sys.executable,'--output',directory,'--port','0',
                '--models','qwen38-bf16','coder-next-f16','--memory-fraction','.4']
            with patch.object(sys,'argv',args),patch('scripts.run_paging_campaign.subprocess.check_output',return_value='synthetic'):
                self.assertEqual(main(),0)
            state=json.loads((root/'campaign.json').read_text())
            self.assertEqual(set(state['models']),{'qwen38-bf16','coder-next-f16'})
            with patch.object(sys,'argv',args+['--memory-fraction','.5']),self.assertRaisesRegex(ValueError,'settings changed'):
                main()

    def test_campaign_lock_excludes_other_campaigns_but_allows_client_lease(self):
        with tempfile.TemporaryDirectory() as directory,patch('local_worker_bench.runner.Path.home',return_value=Path(directory)):
            with worker_lock('paging-campaign.lock'):
                with self.assertRaises(ValueError):
                    with worker_lock('paging-campaign.lock'):self.fail('Duplicate campaign admitted')
                with worker_lock():pass

    def test_stop_checkpoint_starts_no_worker_and_preserves_waiting_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'STOP').touch()
            with patch.object(sys,'argv',['campaign','--backend',sys.executable,'--output',directory,'--port','0','--wait-hours','.1']), \
                    patch('scripts.run_paging_campaign.subprocess.check_output',return_value='synthetic-revision'), \
                    patch('local_worker_bench.offload_api.subprocess.Popen') as spawn:
                self.assertEqual(main(),0)
            spawn.assert_not_called()
            state=json.loads((root/'campaign.json').read_text())
            self.assertFalse(state['generated_code_executed'])
            self.assertTrue(all(r['state']=='waiting_for_verified_download' for r in state['models'].values()))
