"""Formula evaluator tests (plan 02-14)."""
import io
import unittest

import openpyxl
import xlsxwriter

import build
from qa.formula_eval import (
    SUPPORTED_FUNCTIONS, FormulaEvalError, FormulaEvaluator, compare_cached)


def _wb(fill):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    fill(wb)
    wb.close()
    return openpyxl.load_workbook(io.BytesIO(buf.getvalue()))


def _basic(wb):
    s = wb.add_worksheet("Sheet1")
    o = wb.add_worksheet("Other")
    s.write("A1", 2)
    s.write("B1", 3)
    s.write_formula("C1", "=A1+B1")
    s.write_formula("D1", "=Other!$B$2")
    s.write_formula("E1", "=Cell_A1*2")
    s.write_formula("F1", "=SUM(Rng_L)")
    s.write_formula("G1", '=IF(1<2,"OK","ERROR")')
    s.write_formula("H1", "=IF(1<>2,1,0)+IF(2>=2,1,0)+IF(2<=1,1,0)")
    s.write_formula("I1", "=MATCH(5,Other!A1:A4,1)")
    s.write_formula("J1", "=MATCH(0,Other!A1:A4,1)")
    s.write_formula("K1", "=INDEX(Other!A1:A4,3)")
    s.write_formula("L1", "=CHOOSE(2,10,20,30)")
    s.write_formula("M1", "=FOO(1)")
    s.write_formula("N1", "=_xlfn.XLOOKUP(1,2,3)")
    s.write_formula("O1", "=P1")
    s.write_formula("P1", "=O1")
    s.write_formula("Q1", "=2^2")
    s.write_formula("R1", "=A1__x")
    s.write_row("A2", [1, 2, 3])
    o.write("B2", 7)
    o.write_column("A1", [1, 4, 6, 9])
    wb.define_name("Cell_A1", "=Sheet1!$A$1")
    wb.define_name("Rng_L", "=Sheet1!$A$2:$C$2")


class EvaluatorUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb = _wb(_basic)

    def ev(self, overrides=None):
        return FormulaEvaluator(self.wb, overrides)

    def test_basic_and_cross_sheet_and_names(self):
        e = self.ev()
        self.assertEqual(e.value("Sheet1", "C1"), 5)
        self.assertEqual(e.value("Sheet1", "D1"), 7)
        self.assertEqual(e.value("Sheet1", "E1"), 4)
        self.assertEqual(e.value("Sheet1", "F1"), 6)
        self.assertEqual(e.name_target("Rng_L"), ("Sheet1", "A2:C2"))

    def test_if_and_comparisons(self):
        e = self.ev()
        self.assertEqual(e.value("Sheet1", "G1"), "OK")
        self.assertEqual(e.value("Sheet1", "H1"), 2)

    def test_match_index_choose(self):
        e = self.ev()
        self.assertEqual(e.value("Sheet1", "I1"), 2)
        self.assertEqual(e.value("Sheet1", "K1"), 6)
        self.assertEqual(e.value("Sheet1", "L1"), 20)
        with self.assertRaises(FormulaEvalError):
            e.value("Sheet1", "J1")

    def test_overrides(self):
        e = self.ev({("Sheet1", "A1"): 10})
        self.assertEqual(e.value("Sheet1", "C1"), 13)
        e = self.ev({("Sheet1", "C1"): 99})
        self.assertEqual(e.value("Sheet1", "C1"), 99)

    def test_rejections(self):
        for coord in ("M1", "N1", "Q1", "R1"):
            with self.assertRaises(FormulaEvalError, msg=coord):
                self.ev().value("Sheet1", coord)

    def test_cycle(self):
        with self.assertRaises(FormulaEvalError):
            self.ev().value("Sheet1", "O1")

    def test_whitelist(self):
        self.assertIn("MATCH", SUPPORTED_FUNCTIONS)
        self.assertNotIn("EVAL", SUPPORTED_FUNCTIONS)


class WorkbookFormulas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ds = build.load_dataset("config")
        cls.data, _ = build.build_bytes("main", ds)
        cls.fx = build.build_bytes("main", build.load_dataset("fixtures"))[0]

    def test_config_matches_cached(self):
        bad, n = compare_cached(self.data)
        self.assertGreaterEqual(n, 800)
        self.assertEqual(bad, [], "\n".join(bad[:10]))

    def test_fixtures_matches_cached(self):
        bad, n = compare_cached(self.fx)
        self.assertEqual(bad, [], "\n".join(bad[:10]))

    def test_mutation_changes_dependents(self):
        wf = openpyxl.load_workbook(io.BytesIO(self.data))
        sheet, ref = FormulaEvaluator(wf).name_target("Fin_FX_USDperEUR_2010")
        cell = ref.split(":")[0]
        want = openpyxl.load_workbook(io.BytesIO(self.data), data_only=True)[sheet][cell].value
        self.assertIsInstance(want, (int, float))
        # the override beats the cell's own formula: dependents must move
        bad, _ = compare_cached(self.data, overrides={(sheet, cell): want * 1.5})
        self.assertTrue(any("Carbon!" in b for b in bad), bad[:5])
