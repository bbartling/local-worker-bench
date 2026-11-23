import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.run_paging_campaign import main
from local_worker_bench.runner import worker_lock


class CampaignTests(unittest.TestCase):
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
