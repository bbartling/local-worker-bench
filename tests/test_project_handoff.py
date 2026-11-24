import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('project_handoff',Path(__file__).resolve().parents[1]/'scripts/handoff_project_overnight.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class HandoffBoundaryTests(unittest.TestCase):
    def test_does_not_interrupt_inflight_pagination(self):
        trials={str(i):{'task':'pagination','state':'needs_review'} for i in range(3)}
        self.assertTrue(module.pagination_finished({'trials':trials}))
        trials['2']['state']='claimed'
        self.assertFalse(module.pagination_finished({'trials':trials}))
        del trials['2']
        self.assertFalse(module.pagination_finished({'trials':trials}))


if __name__=='__main__':unittest.main()
