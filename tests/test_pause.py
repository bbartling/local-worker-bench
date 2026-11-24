from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

from local_worker_bench.pause import require_benchmark_enabled


class PauseTests(unittest.TestCase):
    def test_marker_blocks_benchmark_without_starting_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            require_benchmark_enabled(folder)
            (Path(folder)/'INFERENCE_PAUSED').write_text('user pause')
            with self.assertRaisesRegex(ValueError,'paused'):
                require_benchmark_enabled(folder)

    def test_project_entrypoint_refuses_before_config_read_or_output_claim(self):
        from scripts import run_project_bench
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'INFERENCE_PAUSED').write_text('explicit user pause')
            args=['bench','--config',str(root/'missing.json'),'--output',str(root/'out'),'--models','fixture']
            with patch.object(run_project_bench,'ROOT',root),patch.object(sys,'argv',args), \
                    patch.object(run_project_bench,'Manager') as manager, \
                    patch.object(run_project_bench.subprocess,'Popen') as spawn:
                with self.assertRaisesRegex(ValueError,'paused'):run_project_bench.main()
            manager.assert_not_called();spawn.assert_not_called()
            self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
