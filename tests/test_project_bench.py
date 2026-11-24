import json
from pathlib import Path
import tempfile
import unittest

from local_worker_bench.project_bench import TASKS,grade,digest_files,validate_files,render


class ProjectBenchTests(unittest.TestCase):
    def run_files(self,task,files):
        with tempfile.TemporaryDirectory() as folder:
            for name,source in files.items():
                (Path(folder)/name).write_text(source,encoding='utf-8',newline='')
            return grade(task,folder,digest_files(files))

    def test_handwritten_controls_pass_all_fixed_cases(self):
        for task,spec in TASKS.items():
            with self.subTest(task=task):
                result=self.run_files(task,spec['reference'])
                self.assertEqual(result['failures'],[])
                self.assertGreaterEqual(result['total'],20)

    def test_every_baseline_is_red(self):
        for task,spec in TASKS.items():
            with self.subTest(task=task):
                result=self.run_files(task,spec['files'])
                self.assertGreater(len(result['failures']),0)

    def test_candidate_schema_and_import_scope(self):
        for files in ({'../pager.py':'pass'},{'pager.py':'import os'}, {'pager.py':'open("secret")'},{'pager.py':'x.__class__'}):
            with self.assertRaises(ValueError):validate_files('pagination',files)

    def test_changed_bytes_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'pager.py').write_text('raise AssertionError("must not execute")')
            with self.assertRaisesRegex(ValueError,'changed since review'):
                grade('pagination',folder,'0'*64)

    def test_prompt_contains_only_broken_sources_and_contract(self):
        for task,spec in TASKS.items():
            text=render(task)
            self.assertLess(len(text),6000)
            self.assertNotIn('reference',json.loads(text[text.index('{'):]))
            for source in spec['files'].values():self.assertIn(source,json.loads(text[text.index('{'):])['excerpt'])


if __name__=='__main__':unittest.main()
