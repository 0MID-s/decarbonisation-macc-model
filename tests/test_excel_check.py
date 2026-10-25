"""Excel harness unit tests: no Excel, no osascript."""
import os
import re
import unittest

import build
from tools import excel_check as ec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Harness(unittest.TestCase):
    def test_states_and_selectors(self):
        self.assertEqual(len(ec.STATES), 12)
        self.assertEqual(ec.SELECTOR_CELLS["direct_ets"], "G10")
        self.assertEqual(ec.SELECTOR_CELLS["scenario"], "G8")
        self.assertEqual(ec.SELECTOR_CELLS["basis"], "G9")

    def test_compare_tolerance(self):
        m, e = ec.compare({"a!A1": 100.0}, {"a!A1": 100.0 * (1 + 5e-8)})
        self.assertEqual((m, e), ([], []))
        m, e = ec.compare({"a!A1": 100.0}, {"a!A1": 100.0 * (1 + 1e-6)})
        self.assertEqual(len(m), 1)

    def test_compare_near_zero(self):
        m, _ = ec.compare({"a!A1": 0.0}, {"a!A1": 5e-10})
        self.assertEqual(m, [])
        m, _ = ec.compare({"a!A1": 0.0}, {"a!A1": 1e-6})
        self.assertEqual(len(m), 1)

    def test_compare_text_and_errors(self):
        m, e = ec.compare({"a!A1": "Same"}, {"a!A1": "Same"})
        self.assertEqual((m, e), ([], []))
        m, e = ec.compare({"a!A1": "Same"}, {"a!A1": "Diff"})
        self.assertEqual(len(m), 1)
        m, e = ec.compare({"a!A1": 1.0}, {"a!A1": "#DIV/0!"})
        self.assertEqual((m, len(e)), ([], 1))
        m, e = ec.compare({"a!A1": True}, {"a!A1": False})
        self.assertEqual(len(m), 1)

    def test_check_dir_refusals(self):
        with self.assertRaises(ValueError):
            ec.make_check_dir("dist/../elsewhere")
        with self.assertRaises(ValueError):
            ec.make_check_dir("data_raw")
        with self.assertRaises(ValueError):
            ec.make_check_dir("dist/data_raw/x")
        with self.assertRaises(ValueError):
            ec.make_check_dir("/tmp")

    def test_formula_cells_default_build(self):
        data, _ = build.build_bytes("main", build.load_dataset("config"))
        cells = ec.formula_cells(data)
        self.assertGreater(len(cells), 1000)
        sheets = {s for s, _ in cells}
        self.assertIn("Exposure", sheets)
        self.assertIn("Sensitivity", sheets)

    def test_js_safety(self):
        with open(os.path.join(ROOT, "tools", "excel_recalc.js")) as fh:
            js = fh.read()
        self.assertIn('Application("Microsoft Excel")', js)
        self.assertIsNone(re.search(r"saveas|\.save\(|doShellScript", js, re.I))
        self.assertIn('saving: "no"', js)
        # WR-05/WR-06: selector addresses come from argv, and the opened
        # workbook is located explicitly rather than via activeWorkbook
        self.assertNotIn("activeWorkbook", js)
        self.assertNotIn("G10", js)
        self.assertIn("findOpened", js)
        self.assertIn("finally", js)
        with open(os.path.join(ROOT, "tools", "excel_close.js")) as fh:
            close_js = fh.read()
        self.assertIsNone(re.search(r"saveas|\.save\(|doShellScript",
                                    close_js, re.I))
        self.assertIn('saving: "no"', close_js)

    def test_selector_cells_resolved_from_names(self):
        data, _ = build.build_bytes("main", build.load_dataset("config"))
        self.assertEqual(ec.selector_cells(data), ec.SELECTOR_CELLS)

    def test_zero_matches_empty_only_for_blank_formulas(self):
        m, _ = ec.compare({"a!A1": ""}, {"a!A1": 0})
        self.assertEqual(len(m), 1)
        m, _ = ec.compare({"a!A1": ""}, {"a!A1": 0}, blank_ok={"a!A1"})
        self.assertEqual(m, [])
        m, _ = ec.compare({"a!A1": ""}, {"a!A1": ""})
        self.assertEqual(m, [])
        m, _ = ec.compare({"a!A1": ""}, {"a!A1": "text"},
                          blank_ok={"a!A1"})
        self.assertEqual(len(m), 1)

    def test_blank_formula_cells_detected(self):
        data, _ = build.build_bytes("main", build.load_dataset("config"))
        keys = ec.blank_formula_cells(data)
        formulas = set("%s!%s" % c for c in ec.formula_cells(data))
        self.assertTrue(keys <= formulas)

    def test_timeout_marks_state_failed_and_continues(self):
        import subprocess
        from unittest import mock
        calls = []

        def fake(state, base=None):
            calls.append(state)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("osascript", 1)
            return 10, [], []
        with mock.patch.object(ec, "run_state", fake), \
                mock.patch.object(ec, "STATES", ec.STATES[:2]), \
                mock.patch("build.load_dataset", lambda *_: None), \
                mock.patch("sys.stdout"):
            rc = ec.main()
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
