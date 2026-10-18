"""Tests for the single write wrapper."""
import datetime
import io
import unittest

import xlsxwriter

from qa.lint import LintError
from xl.cells import CellWriter, UnsafeCellError


def make():
    wb = xlsxwriter.Workbook(io.BytesIO(), {
        "in_memory": True, "strings_to_formulas": False,
        "strings_to_urls": False, "strings_to_numbers": False})
    ws = wb.add_worksheet("Calc")
    return wb, ws, CellWriter(wb)


class TextTests(unittest.TestCase):
    def test_injection_rejected(self):
        wb, ws, cw = make()
        for s in ["=1+1", "+1", "-5", "@x", "\tX", "\rX"]:
            with self.subTest(s=s):
                with self.assertRaises(UnsafeCellError):
                    cw.text(ws, 0, 0, s)

    def test_control_and_length(self):
        wb, ws, cw = make()
        with self.assertRaises(UnsafeCellError):
            cw.text(ws, 0, 0, "a\x01b")
        with self.assertRaises(UnsafeCellError):
            cw.text(ws, 0, 0, "x" * 32768)
        cw.text(ws, 0, 0, "line1\nline2")

    def test_ok(self):
        wb, ws, cw = make()
        cw.text(ws, 0, 0, "– dash")
        cw.text(ws, 1, 0, "Sourced")


class NumberDateTests(unittest.TestCase):
    def test_numbers(self):
        wb, ws, cw = make()
        cw.number(ws, 0, 0, 1.5)
        for bad in [float("nan"), float("inf"), True]:
            with self.subTest(bad=bad):
                with self.assertRaises(UnsafeCellError):
                    cw.number(ws, 0, 0, bad)

    def test_date(self):
        wb, ws, cw = make()
        fmt = wb.add_format({"num_format": "yyyy-mm-dd"})
        cw.date(ws, 0, 0, datetime.date(2026, 1, 1), fmt)


class FormulaTests(unittest.TestCase):
    def test_value_required(self):
        wb, ws, cw = make()
        with self.assertRaises(TypeError):
            cw.formula(ws, 0, 0, "=A1", None)

    def test_lint_blocks_and_registry(self):
        wb, ws, cw = make()
        with self.assertRaises(LintError):
            cw.formula(ws, 0, 0, "=A1*1000", None, value=0)
        self.assertEqual(cw.registry, ())
        cw.formula(ws, 1, 2, "=A1*Rate_Disc", None, value=0.5)
        self.assertEqual(len(cw.registry), 1)
        rec = cw.registry[0]
        self.assertEqual((rec.sheet, rec.row, rec.col, rec.text),
                         ("Calc", 1, 2, "=A1*Rate_Disc"))

    def test_lb_mb_via_tags(self):
        wb, ws, cw = make()
        cw.tag("Calc", 19, 5, 19, 5, "LB")
        cw.tag("Calc", 20, 5, 20, 5, "MB")
        with self.assertRaises(LintError):
            cw.formula(ws, 0, 0, "=F20+F21", None, value=0)
        cw.formula(ws, 0, 0, "=CHOOSE(Idx,F20,F21)", None, value=0)
        with self.assertRaises(UnsafeCellError):
            cw.tag("Calc", 0, 0, 0, 0, "XX")


class LinkNameValidationTests(unittest.TestCase):
    def test_link(self):
        wb, ws, cw = make()
        with self.assertRaises(UnsafeCellError):
            cw.link(ws, 0, 0, "https://evil.example/")
        cw.link(ws, 0, 0, "https://ec.europa.eu/eurostat/", string="Eurostat")
        with self.assertRaises(UnsafeCellError):
            cw.link(ws, 1, 0, "https://ec.europa.eu/eurostat/", string="=bad")

    def test_define_name(self):
        wb, ws, cw = make()
        with self.assertRaises(UnsafeCellError):
            cw.define_name("ETS2", "=Inputs!$D$5")
        with self.assertRaises(UnsafeCellError):
            cw.define_name("Ok_Name", "Inputs!$D$5")
        with self.assertRaises(UnsafeCellError):
            cw.define_name("Ok_Name", "=[x.xlsx]S!$D$5")
        cw.define_name("Const_None", "=Inputs!$G$9")
        self.assertEqual(cw.names["Const_None"], "=Inputs!$G$9")
        cw.tag_name("Const_None", "LB")
        self.assertEqual(cw.tags.tags_for("Const_None", "X"), frozenset(["LB"]))

    def test_validation(self):
        wb, ws, cw = make()
        cw.validation(ws, 0, 0, 0, 0, {"validate": "list", "source": ["Low", "High"]})
        cw.validation(ws, 1, 0, 1, 0, {"validate": "list", "source": "=Lists!$A$2:$A$4"})
        with self.assertRaises(UnsafeCellError):
            cw.validation(ws, 2, 0, 2, 0, {"validate": "list", "source": ["=x", "y"]})
        with self.assertRaises(UnsafeCellError):
            cw.validation(ws, 2, 0, 2, 0, {"validate": "list", "source": "Lists!$A$2"})
        with self.assertRaises(UnsafeCellError):
            cw.validation(ws, 2, 0, 2, 0, {"validate": "list", "source": "=[x]S!A1"})

    def test_blank(self):
        wb, ws, cw = make()
        cw.blank(ws, 0, 0, wb.add_format({"bold": True}))


if __name__ == "__main__":
    unittest.main()
