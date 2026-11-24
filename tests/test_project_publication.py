import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from local_worker_bench.project_bench import packet,render,digest_files,TASKS

spec=importlib.util.spec_from_file_location('project_publication',Path(__file__).resolve().parents[1]/'scripts/publish_project_results.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PublicationTests(unittest.TestCase):
    def setup_trial(self,folder):
        root=Path(folder);trial=root/'pagination--fixture';trial.mkdir()
        import hashlib
        prompt=render('pagination')
        record={'model':'fixture','task':'pagination','state':'needs_review',
            'base_revision':packet('pagination')['base_revision'],
            'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
        (root/'campaign.json').write_text(json.dumps({'trials':{trial.name:record}}))
        (trial/'prompt.txt').write_text(prompt)
        (trial/'packet.json').write_text(json.dumps(packet('pagination')))
        (trial/'candidate.json').write_text(json.dumps({'status':'needs_review','seconds':2,'answer':{'files':TASKS['pagination']['reference']}}))
        return trial,record

    def test_complete_ungraded_draft_is_never_published_as_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            self.setup_trial(folder)
            result=module.publish(Path(folder))
            self.assertEqual(result['summary']['fixture']['accepted_tasks'],0)
            self.assertEqual(result['summary']['fixture']['graded_tasks'],0)

    def test_grade_for_different_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            trial,record=self.setup_trial(folder)
            record['source_sha256']=digest_files(TASKS['pagination']['reference'])
            (Path(folder)/'campaign.json').write_text(json.dumps({'trials':{trial.name:record}}))
            (trial/'grade.json').write_text(json.dumps({'source_sha256':'wrong','passed':25,'total':25,'code_executed':True}))
            with self.assertRaisesRegex(ValueError,'mismatch'):module.publish(Path(folder))


    def test_green_grade_without_explicit_acceptance_stays_unaccepted(self):
        with tempfile.TemporaryDirectory() as folder:
            trial,record=self.setup_trial(folder)
            files=TASKS['pagination']['reference'];record['source_sha256']=digest_files(files)
            (Path(folder)/'campaign.json').write_text(json.dumps({'trials':{trial.name:record}}))
            (trial/'candidate').mkdir()
            for name,source in files.items():(trial/'candidate'/name).write_bytes(source.encode('utf-8'))
            (trial/'grade.json').write_text(json.dumps({'source_sha256':record['source_sha256'],'passed':25,'total':25,'code_executed':True}))
            result=module.publish(Path(folder))
            self.assertEqual(result['summary']['fixture']['graded_tasks'],1)
            self.assertEqual(result['summary']['fixture']['accepted_tasks'],0)
            (trial/'review.json').write_text(json.dumps({'source_sha256':record['source_sha256'],'decision':'accept'}))
            self.assertEqual(module.publish(Path(folder))['summary']['fixture']['accepted_tasks'],1)


if __name__=='__main__':unittest.main()
