"""Checks sheet tests (plan 05-03): inventory, deliberate break, selector, gate."""
import io
import re
import unittest
from unittest import mock

import openpyxl

import build
from qa.formula_eval import compare_cached, evaluate_names

AGG = {"M_Check_All", "Expo_Check_All", "Sens_Check_All"}
CHECK_RE = re.compile(r"^(M|Carb|BL|Expo|Sens)_Check_")
ALLOWED = re.compile(
    r"^=(IFERROR\([A-Za-z0-9_]+,FALSE\)|IFERROR\([A-Za-z0-9_]+=\"OK\",FALSE\)"
    r"|IFERROR\(ISNUMBER\(MATCH\([A-Za-z_]+,[A-Za-z_]+,0\)\),FALSE\)"
    r"|IFERROR\(ABS\(Dash_AbatedSel-MACC_TotalAbatement\)<=COUNT\(MACC_Chart_Width\)"
    r"\*Const_MACCRoundTol,FALSE\)|IFERROR\(AND\(Dash_Share>=0,Dash_Share<=1\),FALSE\)"
    r"|IFERROR\(OR\(Dash_AbatedSel=M_Total_tLB,Dash_AbatedSel=M_Total_tMB\),FALSE\)"
    r"|AND\(.*\)|COUNTIF\(.*,FALSE\)|SUM\(.*\)|IF\(AND\(.*\),\"OK\",\"ERROR\"\))$")


class ChecksSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = build.load_dataset("config")
        cls.data, _ = build.build_bytes("main", cls.ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        cls.ws = cls.wb["Checks"]

    def _addr(self, name):
        sheet, addr = self.wb.defined_names[name].attr_text.split("!")
        return sheet, addr.replace("$", "")

    def _status_formulas(self):
        out = []
        for row in self.ws.iter_rows(min_col=4, max_col=4):
            c = row[0]
            if isinstance(c.value, str) and c.value.startswith("=IFERROR("):
                out.append(c.value)
        return out

    def test_sheet_before_notes(self):
        names = self.wb.sheetnames
        self.assertLess(names.index("Checks"), names.index("Notes"))

    def test_inventory_complete_once(self):
        forms = self._status_formulas()
        expected = [n for n in self.wb.defined_names
                    if CHECK_RE.match(n) and n not in AGG]
        self.assertGreaterEqual(len(expected), 56)
        for n in expected:
            hits = [f for f in forms
                    if re.search(r"IFERROR\(%s[,=]" % re.escape(n), f)]
            self.assertEqual(len(hits), 1, n)
        for f in forms:
            self.assertNotIn("_Check_All", f)

    def test_formula_shapes_only(self):
        for row in self.ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    self.assertRegex(c.value, ALLOWED, c.coordinate)

    def test_default_ok_and_cached(self):
        got = evaluate_names(self.data, ["Chk_Master", "Chk_FailCount"])
        self.assertEqual(got, {"Chk_Master": "OK", "Chk_FailCount": 0})
        bad, _ = compare_cached(self.data)
        self.assertEqual(bad, [])

    def test_deliberate_break(self):
        sheet, addr = self._addr("Meas_PV_Size")
        got = evaluate_names(self.data, ["Chk_Master", "Chk_FailCount"],
                             overrides={(sheet, addr): 100000.0})
        self.assertEqual(got["Chk_Master"], "ERROR")
        self.assertGreaterEqual(got["Chk_FailCount"], 1)

    def test_invalid_selector(self):
        sheet, addr = self._addr("Sel_Basis")
        got = evaluate_names(self.data, ["Chk_Master", "Chk_Sel_Basis"],
                             overrides={(sheet, addr): "Foo"},
                             tolerate_errors=True)
        self.assertEqual(got["Chk_Master"], "ERROR")
        self.assertIs(got["Chk_Sel_Basis"], False)

    def test_dashboard_checks(self):
        names = ["Chk_TileVsMACC", "Chk_ShareInRange", "Chk_BasisExact"]
        for n in names:
            self.assertIn(n, self.wb.defined_names)
        got = evaluate_names(self.data, names)
        self.assertEqual(got, {n: True for n in names})
        # the group 6 Boolean row sits before the text row
        sheet, addr = self._addr("Chk_BasisExact")
        row = int(re.sub(r"\D", "", addr))
        self.assertEqual(self.ws["D%d" % (row + 1)].value, "Enforced at build")

    def test_tile_vs_macc_fails_at_zero_tolerance(self):
        sheet, addr = self._addr("Const_MACCRoundTol")
        got = evaluate_names(self.data, ["Chk_TileVsMACC"],
                             overrides={(sheet, addr): 0.0})
        self.assertIs(got["Chk_TileVsMACC"], False)

    def test_group6_text_row(self):
        hit = [c for row in self.ws.iter_rows(min_col=4, max_col=4)
               for c in row if c.value == "Enforced at build"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0].data_type, "s")

    def test_gate(self):
        with mock.patch.object(build, "evaluate_names",
                               return_value={"Chk_Master": "ERROR"}):
            with self.assertRaises(build.BuildGateError):
                build.build_bytes("main", self.ds)
            with mock.patch("sys.stderr"):
                self.assertEqual(
                    build.main(["--out", "/dev/null/x.xlsx"]), 6)


if __name__ == "__main__":
    unittest.main()
