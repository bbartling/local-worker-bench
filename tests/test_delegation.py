import hashlib
from pathlib import Path
import tempfile
import unittest
from local_worker_bench.delegation import JobStore,render_packet,validate_packet


class DelegationTests(unittest.TestCase):
    def packet(self):
        return dict(task='One function',base_revision='abc',allowed_files=['x.py'],excerpt='def x(): pass',
            acceptance=['Returns a bool'],non_goals=['No I/O'])

    def test_incomplete_and_oversized_packets_refused(self):
        for packet in ({},dict(self.packet(),excerpt='x'*10000),dict(self.packet(),allowed_files=['../x.py'])):
            with self.assertRaises(ValueError):validate_packet(packet)
        self.assertIn('needs_context',render_packet(self.packet()))

    def test_claim_persists_and_cannot_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'jobs.sqlite';store=JobStore(path);job=store.submit(self.packet());store.claim(job);store.close()
            store=JobStore(path)
            self.assertEqual(store.get(job)['state'],'drafting')
            with self.assertRaises(ValueError):store.claim(job)
            store.finish(job,{'error':'cancelled'},'failed');store.close()

    def test_acceptance_requires_same_candidate_revision_and_passing_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'candidate.py';source.write_bytes(b'def x(): return True\n')
            sha=hashlib.sha256(source.read_bytes()).hexdigest();store=JobStore(root/'jobs.sqlite')
            job=store.submit(self.packet());store.claim(job);store.finish(job,{'candidate_sha256':sha})
            grade=dict(source_sha256=sha,passed=1,total=1,code_executed=True)
            with self.assertRaises(ValueError):store.decide(job,source,sha,grade,True,'different')
            with self.assertRaises(ValueError):store.decide(job,source,sha,dict(grade,passed=0),True,'abc')
            store.decide(job,source,sha,grade,True,'abc');self.assertEqual(store.get(job)['state'],'accepted');store.close()
