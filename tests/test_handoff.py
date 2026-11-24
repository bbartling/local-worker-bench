import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock,patch
from scripts.handoff_long_retest import main


class HandoffTests(unittest.TestCase):
    def test_completed_legacy_request_hands_off_to_one_90_minute_cohort(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);legacy=root/'legacy';candidate=legacy/'qwen38-bf16-packet/patch.candidate.json'
            candidate.parent.mkdir(parents=True);candidate.write_text(json.dumps({'status':'needs_review'}))
            output=root/'retest';child=MagicMock(pid=123,returncode=0);child.poll.side_effect=[None,0]
            args=['handoff','--legacy',str(legacy),'--request-id','a'*32,'--legacy-deadline',str(time.time()+30),
                '--output',str(output),'--backend',sys.executable]
            with patch.object(sys,'argv',args),patch('scripts.handoff_long_retest.Path.home',return_value=root), \
                    patch('scripts.handoff_long_retest.subprocess.Popen',return_value=child) as spawn, \
                    patch('scripts.handoff_long_retest.time.sleep'),patch('scripts.handoff_long_retest.api') as api:
                self.assertEqual(main(),0)
            api.assert_not_called();self.assertTrue((legacy/'STOP').exists())
            command=spawn.call_args.args[0]
            self.assertEqual(command[command.index('--request-timeout')+1],'5400')
            self.assertEqual(command[command.index('--tasks')+1],'motor')
            start=command.index('--models')+1
            self.assertEqual(command[start:start+3],['qwen38-q4','qwen38-bf16','coder-next-f16'])
            self.assertEqual(json.loads((output/'handoff.json').read_text())['state'],'finished')
