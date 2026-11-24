import os
import unittest
from unittest.mock import patch

from local_worker_bench.paging import plan, default_threads, affinity_cpus


class PagingPlanTests(unittest.TestCase):
    def snapshot(self,available=16,total=32):
        return {'available_bytes':available*2**30,'total_bytes':total*2**30}

    def test_budget_uses_available_not_total_and_does_not_slice(self):
        result=plan(self.snapshot(),48*2**30)
        self.assertAlmostEqual(result['working_set_bytes']/2**30,10.56,places=5)
        self.assertEqual(result['equivalent_budget_chunks'],5)
        self.assertEqual(result['physical_model_slices_created'],0)

    def test_reserve_wins_on_small_hosts(self):
        self.assertEqual(plan(self.snapshot(3,8),8*2**30)['working_set_bytes'],2**30)
        with self.assertRaises(ValueError):plan(self.snapshot(2,8),8*2**30)

    def test_invalid_fractions_rejected(self):
        for value in (True,float('nan'),float('inf'),.67,0,-1):
            with self.subTest(value=value),self.assertRaises(ValueError):plan(self.snapshot(),100,value)

    def test_default_threads_from_visible_cpus(self):
        for visible, expected in ((1, 1), (2, 1), (8, 5), (12, 8), (24, 16)):
            with self.subTest(visible=visible), patch.object(os, 'cpu_count', return_value=visible), \
                    patch('local_worker_bench.paging.affinity_cpus', return_value=visible):
                picked = default_threads()['threads']
                self.assertEqual(picked, expected)
        self.assertGreaterEqual(affinity_cpus(), 1)
