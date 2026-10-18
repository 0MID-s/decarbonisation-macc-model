"""Tests for the style factory (xl/styles.py) and layout grid (xl/layout.py)."""
import io
import unittest
import zipfile

import xlsxwriter

from xl import layout
from config.build_config import BUILD
from xl.styles import (
    NUM_FORMATS, OKABE_ITO, PALETTE, ROLES, TAB_COLOURS, SheetKind, Styles,
    apply_check_format,
)


def new_workbook():
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {
        "in_memory": True, "strings_to_formulas": False, "strings_to_urls": False,
        "default_format_properties": {"font_name": "Arial", "font_size": 10},
    })
    return wb, buf


def hexc(c):
    return "#" + c._rgb_hex_value().upper()


def close_and_read(wb, buf):
    wb.close()
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


class StylesTests(unittest.TestCase):
    def setUp(self):
        self.wb, self.buf = new_workbook()
        self.st = Styles(self.wb)

    def test_input(self):
        f = self.st.get("input")
        self.assertEqual(hexc(f.font_color), "#0000FF")
        self.assertEqual(hexc(f.bg_color), "#FFF2CC")
        self.assertEqual(f.locked, 0)
        self.assertEqual(f.font_name, "Arial")
        self.assertEqual(f.font_size, 10)

    def test_selector(self):
        f = self.st.get("selector")
        self.assertEqual(hexc(f.font_color), "#0000FF")
        self.assertEqual(hexc(f.bg_color), "#FFF2CC")
        for side in (f.left, f.right, f.top, f.bottom):
            self.assertEqual(side, 2)

    def test_other_roles(self):
        self.assertEqual(hexc(self.st.get("link").font_color), "#008000")
        self.assertEqual(hexc(self.st.get("calc").font_color), "#000000")
        self.assertEqual(hexc(self.st.get("status_assumption").bg_color), "#FCE4D6")
        t = self.st.get("title")
        self.assertEqual((t.font_name, t.font_size, t.bold), ("Arial", 14, 1))
        self.assertEqual(hexc(t.font_color), "#FFFFFF")
        self.assertEqual(hexc(t.bg_color), "#1F3864")
        s = self.st.get("section")
        self.assertEqual(s.bold, 1)
        self.assertEqual(hexc(s.bg_color), "#D9D9D9")

    def test_num_formats(self):
        self.assertEqual(self.st.get("calc", "eur").num_format, '#,##0;(#,##0);"–"')
        self.assertEqual(self.st.get("input", "price4").num_format, "0.0000")
        self.assertEqual(self.st.get("calc", "year").num_format, "0")

    def test_unknown_raises(self):
        with self.assertRaises(KeyError):
            self.st.get("x")
        with self.assertRaises(KeyError):
            self.st.get("calc", "nope")

    def test_cache(self):
        self.assertIs(self.st.get("calc", "eur"), self.st.get("calc", "eur"))

    def test_all_roles_build(self):
        for r in ROLES:
            self.st.get(r)

    def test_constants(self):
        for k in SheetKind:
            self.assertIn(k, TAB_COLOURS)
        self.assertEqual(len(OKABE_ITO), 8)
        self.assertEqual(len(set(OKABE_ITO)), 8)
        self.assertEqual(PALETTE["title_fill"], "#1F3864")

    def test_styles_xml(self):
        ws = self.wb.add_worksheet("S")
        for i, r in enumerate(("input", "link", "title")):
            ws.write_blank(i, 1, None, self.st.get(r))
        apply_check_format(ws, self.st, 0, 0, 5, 0)
        z = close_and_read(self.wb, self.buf)
        xml = z.read("xl/styles.xml").decode("utf-8")
        for token in ("FF0000FF", "FFFFF2CC", "FF008000", "FF1F3864", "Arial"):
            self.assertIn(token, xml)
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertEqual(sheet.count("<cfRule"), 2)


class LayoutTests(unittest.TestCase):
    def test_columns(self):
        self.assertEqual(layout.col_for_year(2026), 13)
        self.assertEqual(layout.col_for_year(2055), 42)
        self.assertEqual(layout.col_letter(13), "N")
        self.assertEqual(layout.col_letter(42), "AQ")
        for y in (2025, 2056):
            with self.assertRaises(ValueError):
                layout.col_for_year(y)
        for y in BUILD.timeline_years:
            self.assertEqual(layout.year_for_col(layout.col_for_year(y)), y)
        with self.assertRaises(ValueError):
            layout.year_for_col(12)

    def test_timeline_single_source(self):
        # WR-09: Inputs and the shared grid derive the timeline from BUILD.
        import inspect

        import build
        from xl.sheets import inputs
        self.assertEqual(layout.TIMELINE_LAST_COL,
                         layout.col_for_year(BUILD.timeline_end))
        self.assertEqual(inputs.LAST_COL, layout.TIMELINE_LAST_COL)
        self.assertNotIn("cfg", inspect.signature(build.build_bytes).parameters)

    def test_footer(self):
        self.assertIn("&CIllustrative", layout.FOOTER)

    def test_setup_sheet(self):
        wb, buf = new_workbook()
        a = wb.add_worksheet("Calc")
        b = wb.add_worksheet("Inputs")
        layout.setup_sheet(a, SheetKind.CALC, freeze_row=4, freeze_col=3)
        layout.setup_sheet(b, SheetKind.INPUTS, freeze_row=5, freeze_col=2)
        z = close_and_read(wb, buf)
        calc = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        inp = z.read("xl/worksheets/sheet2.xml").decode("utf-8")
        for x in (calc, inp):
            self.assertIn('showGridLines="0"', x)
            self.assertIn('orientation="landscape"', x)
            self.assertIn('paperSize="9"', x)
            self.assertIn('fitToPage="1"', x)  # fitToWidth=1 is the OOXML default, omitted
            self.assertIn('fitToHeight="0"', x)
            self.assertIn("<pane", x)
            self.assertIn("Illustrative model, fictitious company, real public data", x)
        self.assertIn('xSplit="3"', calc)
        self.assertIn('ySplit="4"', calc)
        self.assertIn('rgb="FFFFC000"', inp)
        self.assertNotIn("tabColor", calc)
        self.assertIn("_xlnm.Print_Titles", z.read("xl/workbook.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
