import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from local_worker_bench.project_bench import (
    TASKS, SUITE_VERSION, SUITE_V1_TOTALS, grade, digest_files, validate_files, render, packet, tests_v1, suite_sha256,
)


def _pager_mutants():
    pager = TASKS['pagination']['reference']['pager.py']
    duration = TASKS['telemetry']['reference']['duration.py']
    units = TASKS['export']['reference']['units.py']
    report = TASKS['export']['reference']['report.py']
    return [
        ('bool_total_coerced', 'pagination', {'pager.py': pager.replace(
            "if type(value) is not int or value < 0 or (total is not None and value != total):",
            "if isinstance(value, bool):\n                value = int(value)\n            if type(value) is not int or value < 0 or (total is not None and value != total):")
        }),
        ('page_size_only_with_filters', 'pagination', {'pager.py': pager.replace(
            "response = fetch(dict(query, pageSize=100, pageOffset=len(rows)))",
            "response = fetch(dict(query, pageSize=(100 if filters else 1), pageOffset=len(rows)))")
        }),
        ('reject_exact_max_pages_fit', 'pagination', {'pager.py': pager.replace(
            "for _ in range(max_pages):",
            "for i in range(max_pages):").replace(
            "            return rows",
            "            if i == max_pages - 1:\n                raise ValueError('exact fit')\n            return rows")
        }),
        ('allow_empty_id', 'pagination', {'pager.py': pager.replace(
            "or not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:",
            "or not isinstance(row.get('id'), str) or row['id'] in ids:")
        }),
        ('accept_integral_float_cap', 'pagination', {'pager.py': pager.replace(
            "if type(max_pages) is not int or max_pages < 1:",
            "if type(max_pages) is float and max_pages.is_integer():\n        max_pages = int(max_pages)\n    if type(max_pages) is not int or max_pages < 1:")
        }),
        ('accept_state_zero', 'telemetry', {'duration.py': duration.replace(
            "if state is not None and type(state) is not bool:",
            "if state is not None and type(state) is not bool and state != 0:")
        }),
        ('accept_false_value', 'export', {
            'units.py': units.replace(
                "if type(value) not in (int, float) or not math.isfinite(value):",
                "if value is False:\n        value = 0\n    elif type(value) not in (int, float) or not math.isfinite(value):"),
            'report.py': report,
        }),
        ('abs_kpa', 'export', {
            'units.py': units.replace(
                "return float(value * 1000 if unit == 'kPa' else value)",
                "return float(abs(value) * 1000 if unit == 'kPa' else value)"),
            'report.py': report,
        }),
    ]


class ProjectBenchTests(unittest.TestCase):
    def run_files(self, task, files, suite_version=SUITE_VERSION):
        with tempfile.TemporaryDirectory() as folder:
            for name, source in files.items():
                (Path(folder) / name).write_text(source, encoding='utf-8', newline='')
            return grade(task, folder, digest_files(files), suite_version=suite_version)

    def test_handwritten_controls_pass_all_suite3_cases(self):
        for task, spec in TASKS.items():
            with self.subTest(task=task):
                result = self.run_files(task, spec['reference'])
                self.assertEqual(result['failures'], [])
                self.assertEqual(result['suite_version'], SUITE_VERSION)
                self.assertEqual(result['suite_sha256'], suite_sha256())
                self.assertGreaterEqual(result['total'], 20)

    def test_frozen_v1_suite_unchanged(self):
        for task, spec in TASKS.items():
            with self.subTest(task=task), tempfile.TemporaryDirectory() as folder:
                for name, source in spec['reference'].items():
                    (Path(folder) / name).write_text(source, encoding='utf-8', newline='')
                result = grade(task, folder, digest_files(spec['reference']), suite_version=1)
                self.assertEqual(result['total'], SUITE_V1_TOTALS[task])
                self.assertEqual(result['failures'], [])

    def test_every_baseline_is_red(self):
        for task, spec in TASKS.items():
            with self.subTest(task=task):
                result = self.run_files(task, spec['files'])
                self.assertGreater(len(result['failures']), 0)

    def test_always_raise_pager_demonstrates_why_fraction_is_not_acceptance(self):
        files = {'pager.py': 'def read_all(fetch, filters=None, max_pages=20):\n    raise ValueError("deliberately wrong control")\n'}
        v1 = self.run_files('pagination', files, suite_version=1)
        self.assertEqual(v1['passed'], 20)
        self.assertEqual(v1['total'], 25)
        v3 = self.run_files('pagination', files)
        self.assertLess(v3['passed'], v3['total'])

    def test_mutant_corpus_scores_below_total(self):
        for label, task, files in _pager_mutants():
            with self.subTest(mutant=label):
                result = self.run_files(task, files)
                self.assertLess(result['passed'], result['total'], msg=label)

    def test_candidate_schema_and_import_scope(self):
        for files in ({'../pager.py': 'pass'}, {'pager.py': 'import os'}, {'pager.py': 'open("secret")'}, {'pager.py': 'x.__class__'}):
            with self.assertRaises(ValueError):
                validate_files('pagination', files)

    def test_changed_bytes_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'pager.py').write_text('raise AssertionError("must not execute")')
            with self.assertRaisesRegex(ValueError, 'changed since review'):
                grade('pagination', folder, '0' * 64)

    def test_review_hash_preserves_crlf_candidate_bytes(self):
        files = {name: source.replace('\n', '\r\n') for name, source in TASKS['telemetry']['reference'].items()}
        result = self.run_files('telemetry', files)
        self.assertEqual(result['failures'], [])
        self.assertEqual(result['source_sha256'], digest_files(files))

    def test_prompt_contains_only_broken_sources_and_contract(self):
        for task, spec in TASKS.items():
            text = render(task)
            self.assertLess(len(text), 6000)
            self.assertNotIn('reference', json.loads(text[text.index('{'):]))
            for source in spec['files'].values():
                self.assertIn(source, json.loads(text[text.index('{'):])['excerpt'])

    def test_original_prompt_stays_pinned_and_revised_prompt_keeps_fixture(self):
        self.assertEqual(hashlib.sha256(render('pagination').encode()).hexdigest(),
                         '05344a8db00315f0965267a0de2830e03cab13fa03d860f1e2c0f0f43febc96f')
        for task in TASKS:
            revised = render(task, 2)
            spec = json.loads(revised[revised.index('{'):])
            self.assertEqual(spec['base_revision'], packet(task)['base_revision'])
            self.assertEqual(spec['acceptance'], packet(task)['acceptance'])
            self.assertTrue(spec['examples'])


if __name__ == '__main__':
    unittest.main()