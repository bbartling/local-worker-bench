import json
import unittest
from local_worker_bench.streaming import summarize, verified
from local_worker_bench.patch_task import grade


class StreamingReceiptTests(unittest.TestCase):
    def event(self,**overrides):
        row=dict(layer=0,final=False,eviction_requests=3,unexpected_errors=0,
            resident_samples_before=9,resident_samples_after=0)
        row.update(overrides);return 'print_info: n_layer = 1\nLWB_STREAM '+json.dumps(row)+'\n'

    def test_requires_residency_evidence_not_just_a_flag(self):
        self.assertFalse(verified(summarize('Backend enabled flag\n')))
        self.assertFalse(verified(summarize(self.event(resident_samples_before=0))))
        self.assertTrue(verified(summarize(self.event())))

    def test_preserves_layer_ids_and_final_stage(self):
        result=summarize(self.event(layer=3)+self.event(layer=0)+self.event(layer=-1,final=True))
        self.assertEqual(result['decoder_layers_observed'],[0,3])
        self.assertEqual(result['sampled_resident_before'],27)
        self.assertEqual(result['eviction_requests'],9)

    def test_unexpected_os_error_fails_verification(self):
        self.assertFalse(verified(summarize(self.event(unexpected_errors=1))))

    def test_patch_controls_include_boundaries_and_exact_type(self):
        self.assertEqual(grade(lambda status:type(status) is int and 200<=status<=299)['passed'],25)
        self.assertLess(grade(bool)['passed'],25)
        self.assertLess(grade(lambda status:isinstance(status,int) and 200<=status<=299)['passed'],25)
