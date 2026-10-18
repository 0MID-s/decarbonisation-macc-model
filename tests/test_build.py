"""End-to-end build tests: exit codes, fail-closed behaviour, sheet order."""
import contextlib
import dataclasses
import io
import os
import tempfile
import unittest
from unittest import mock

import openpyxl

import build
from config.schema import Status
from qa.lint import LintError
from qa.readback import ReadbackError
from qa.scan import ScanError, scan_xlsx_bytes


def _quiet_main(argv):
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        return build.main(argv)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, *p):
        return os.path.join(self.tmp.name, *p)

    def test_config_build(self):
        out = self.path("c.xlsx")
        self.assertEqual(_quiet_main(["--dataset", "config", "--out", out]), 0)
        self.assertTrue(os.path.exists(out))

    def test_fixtures_build(self):
        out = self.path("f.xlsx")
        self.assertEqual(_quiet_main(["--dataset", "fixtures", "--out", out]), 0)
        self.assertTrue(os.path.exists(out))

    def test_placeholder_blocks_and_writes_nothing(self):
        ds = build.load_dataset("fixtures")
        bad = dataclasses.replace(ds.inputs[3], status=Status.PLACEHOLDER)
        ds = dataclasses.replace(ds, inputs=ds.inputs[:3] + (bad,) + ds.inputs[4:])
        out = self.path("p.xlsx")
        with mock.patch.object(build, "load_dataset", return_value=ds):
            self.assertEqual(_quiet_main(["--out", out]), 2)
        self.assertFalse(os.path.exists(out))

    def test_lint_failure(self):
        def extra(wb, styles, cells):
            ws = wb.add_worksheet("Bad")
            cells.formula(ws, 0, 0, "=A1*1000", None, value=0)
        with self.assertRaises(LintError):
            build.build_bytes("main", build.load_dataset("fixtures"),
                              extra_builders=[extra])

    def test_scan_failure_on_bypass(self):
        def extra(wb, styles, cells):
            wb.add_worksheet("Raw").write_string(0, 0, "=1+1")
        with self.assertRaises(ScanError):
            build.build_bytes("main", build.load_dataset("fixtures"),
                              extra_builders=[extra])

    def test_readback_catches_unregistered_formula(self):
        def extra(wb, styles, cells):
            wb.add_worksheet("Raw").write_formula(0, 0, "=1+1", None, 2)
        with self.assertRaises(ReadbackError) as cm:
            build.build_bytes("main", build.load_dataset("fixtures"),
                              extra_builders=[extra])
        self.assertTrue(any("not in registry" in p for p in cm.exception.problems))

    def test_main_workbook_clean_and_ordered(self):
        data, _ = build.build_bytes("main", build.load_dataset("config"))
        self.assertEqual(scan_xlsx_bytes(data), [])
        wb = openpyxl.load_workbook(io.BytesIO(data))
        self.assertEqual(wb.sheetnames, ["Cover", "Inputs", "Sources", "Lists"])

    def test_creates_missing_output_directories(self):
        out = self.path("missing", "nested", "out.xlsx")
        self.assertEqual(_quiet_main(["--dataset", "fixtures", "--out", out]), 0)
        self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
