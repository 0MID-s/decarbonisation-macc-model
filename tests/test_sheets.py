"""Sheet builder tests: build into memory, read back with openpyxl (never save)."""
import datetime
import io
import types
import unittest

import openpyxl
import xlsxwriter

from config.build_config import BUILD
from tests.fixtures.synthetic import (
    SYNTHETIC_INPUTS, SYNTHETIC_MEASURES, SYNTHETIC_SOURCES)
from xl.cells import CellWriter
from xl.sheets.cover import FICTITIOUS_NOTE, LEGEND_MEANINGS, build_cover
from xl.sheets.inputs import INPUT_COLUMNS, build_inputs
from xl.sheets.lists import build_lists
from xl.sheets.sources import build_sources
from xl.styles import Styles

OPTIONS = {"in_memory": True, "strings_to_formulas": False,
           "strings_to_urls": False, "strings_to_numbers": False}


def _dataset(synthetic=True, sources=SYNTHETIC_SOURCES):
    return types.SimpleNamespace(
        name="t", sources=tuple(sources), inputs=SYNTHETIC_INPUTS,
        measures=SYNTHETIC_MEASURES, synthetic=synthetic)


def _build(builders, dataset):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, OPTIONS)
    styles = Styles(wb)
    cells = CellWriter(wb)
    layouts = [b(wb, styles, cells, dataset, BUILD) for b in builders]
    wb.close()
    data = buf.getvalue()
    return (openpyxl.load_workbook(io.BytesIO(data)),
            openpyxl.load_workbook(io.BytesIO(data), data_only=True),
            layouts)


def _inputs_cover_first(dataset):
    # Time_FirstYear name is defined inside build_inputs
    return _build([build_inputs, build_sources], dataset)


class InputsSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb, cls.wbv, cls.layouts = _inputs_cover_first(_dataset())
        cls.ws = cls.wb["Inputs"]
        cls.wsv = cls.wbv["Inputs"]
        cls.layout = cls.layouts[0]

    def test_header(self):
        got = tuple(self.ws.cell(11, 2 + i).value for i in range(11))
        self.assertEqual(got, INPUT_COLUMNS)
        self.assertEqual(self.wsv["N11"].value, 2026)
        self.assertEqual(self.wsv["AQ11"].value, 2055)
        self.assertEqual(self.ws["N11"].value, "=Time_FirstYear")

    def test_record_rows_complete(self):
        self.assertEqual(len(self.layout.record_rows), len(SYNTHETIC_INPUTS))
        for rid, row in self.layout.record_rows:
            R = row + 1
            for col in "BCEHIJKL":
                self.assertTrue(self.ws["%s%d" % (col, R)].value,
                                "%s empty on %s" % (col, rid))
            self.assertIn(self.ws["K%d" % R].value,
                          ("Sourced", "Analyst assumption"))

    def test_assumption_fill_and_input_style(self):
        by_id = dict(self.layout.record_rows)
        r = by_id["Finance_SynthWacc"] + 1
        self.assertEqual(self.ws["K%d" % r].value, "Analyst assumption")
        self.assertTrue(self.ws["K%d" % r].fill.fgColor.rgb.endswith("FCE4D6"))
        self.assertTrue(self.ws["L%d" % r].value)
        d = self.ws["D%d" % r]
        self.assertTrue(d.font.color.rgb.endswith("0000FF"))
        self.assertTrue(d.fill.fgColor.rgb.endswith("FFF2CC"))

    def test_model_value_formulas(self):
        by_id = dict(self.layout.record_rows)
        r = by_id["Baseline_SynthGasMWh"] + 1
        self.assertEqual(self.ws["G%d" % r].value, "=D%d*F%d" % (r, r))
        self.assertEqual(self.wsv["G%d" % r].value, 12500.0)
        c = by_id["Const_None"] + 1
        self.assertEqual(self.ws["G%d" % c].value, "=D%d" % c)
        self.assertTrue(self.ws["F%d" % r].value.startswith("=G"))

    def test_series_rows(self):
        by_id = dict(self.layout.record_rows)
        pub = by_id["CarbonPrice_SynthCentral"] + 1
        mrow = dict(self.layout.series_model_rows)["CarbonPrice_SynthCentral"] + 1
        self.assertEqual(mrow, pub + 1)
        self.assertEqual(self.ws["N%d" % mrow].value, "=N%d*$F$%d" % (pub, pub))
        self.assertEqual(self.wsv["O%d" % mrow].value, 65.0)
        self.assertEqual(self.ws["N%d" % pub].value, 60.0)
        self.assertTrue(self.ws["B%d" % pub].value)

    def test_legend_and_banner(self):
        texts = [self.ws.cell(5, c).value for c in range(2, 10)]
        self.assertEqual(texts[0], "Colour key:")
        self.assertIn("Analyst assumption", texts)
        self.assertIn("SYNTHETIC", self.ws["B4"].value)

    def test_defined_names(self):
        self.assertIn("Time_FirstYear", self.wb.defined_names)

    def test_sources_plain_urls(self):
        ws = self.wb["Sources"]
        got = tuple(ws.cell(5, 2 + i).value for i in range(7))
        self.assertEqual(got[0], "Source ID")
        self.assertEqual(got[3], "URL")
        for r in (6, 7):
            self.assertTrue(ws.cell(r, 5).value.startswith("https://"))
            self.assertIsNone(ws.cell(r, 5).hyperlink)
        self.assertIsInstance(ws.cell(6, 7).value, datetime.datetime)

    def test_sources_empty_message(self):
        wb, _, _ = _build([build_sources], _dataset(False, ()))
        self.assertIn("No sources registered yet", wb["Sources"]["B6"].value)

    def test_no_banner_for_config(self):
        wb, _, _ = _build([build_inputs], _dataset(False))
        self.assertNotIn("SYNTHETIC", str(wb["Inputs"]["B4"].value))


class ListsCover(unittest.TestCase):
    def test_lists(self):
        wb, _, _ = _build([build_lists], _dataset())
        ws = wb["Lists"]
        self.assertEqual([ws.cell(r, 2).value for r in (6, 7, 8)],
                         ["Low", "Central", "High"])
        self.assertEqual([ws.cell(r, 4).value for r in (6, 7)],
                         ["Location-based", "Market-based"])
        self.assertEqual(wb.defined_names["List_Scenario"].attr_text,
                         "Lists!$B$6:$B$8")
        self.assertEqual(wb.defined_names["List_Basis"].attr_text,
                         "Lists!$D$6:$D$7")
        self.assertIn("SYNTHETIC", ws["B4"].value)

    def _cover(self, dataset, names):
        def b(wb, styles, cells, ds, cfg):
            return build_cover(wb, styles, cells, ds, cfg, names)
        return _build([b], dataset)[0]["Cover"]

    def test_cover(self):
        names = ["Cover", "Inputs", "Sources", "Lists"]
        ws = self._cover(_dataset(), names)
        self.assertEqual(ws["B5"].value, FICTITIOUS_NOTE)
        self.assertEqual([ws.cell(r, 3).value for r in range(7, 14)],
                         [m for _, m in LEGEND_MEANINGS])
        self.assertEqual([ws.cell(r, 2).value for r in range(17, 21)], names)
        for r, n in zip(range(17, 21), names):
            hl = ws.cell(r, 2).hyperlink
            self.assertIsNotNone(hl, n)
            self.assertEqual(hl.location, "%s!A1" % n)
        self.assertEqual(ws["B16"].value, "Contents")
        flat = [c.value for row in ws.iter_rows() for c in row]
        self.assertIn(BUILD.version, flat)
        self.assertIn("Build date", flat)
        self.assertIn("SYNTHETIC", ws["B4"].value)

    def test_cover_no_banner(self):
        ws = self._cover(_dataset(False), ["Cover"])
        self.assertNotIn("SYNTHETIC", str(ws["B4"].value))


if __name__ == "__main__":
    unittest.main()
