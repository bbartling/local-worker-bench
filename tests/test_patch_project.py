"""Exercise only handwritten controls, never model-generated source in CI."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

FIXTURE=Path(__file__).resolve().parents[1]/'examples/patch-project'


class PatchProjectControls(unittest.TestCase):
    def test_broken_fixture_is_red_and_handwritten_control_is_green(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'project';shutil.copytree(FIXTURE,target)
            command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-v']
            bad=subprocess.run(command,cwd=target,capture_output=True,text=True,timeout=20)
            self.assertNotEqual(bad.returncode,0);self.assertIn('Ran 17 tests',bad.stderr)
            path=target/'client.py';source=path.read_text()
            old='    return status == 200 and bool(payload)'
            replacement='''    if type(expected_id) is not str or not expected_id:
        raise ValueError("expected_id must be a nonempty exact str")
    return (type(status) is int and status == 200 and isinstance(payload, dict)
            and payload.get("ok") is True and type(payload.get("id")) is str
            and payload["id"] == expected_id)'''
            self.assertEqual(source.count(old),1);path.write_text(source.replace(old,replacement))
            good=subprocess.run(command,cwd=target,capture_output=True,text=True,timeout=20)
            self.assertEqual(good.returncode,0,good.stderr);self.assertIn('Ran 17 tests',good.stderr)
