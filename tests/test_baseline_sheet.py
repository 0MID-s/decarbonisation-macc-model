"""Baseline sheet tests: formulas, cached values vs reference, LB/MB rule."""
import io
import unittest

import openpyxl
import xlsxwriter

import build
from checkmodel.baseline_reference import compute_baseline, model_values
from config.build_config import BUILD
from qa.lint import LintError, lint_or_raise
from qa.scan import scan_or_raise
from xl.cells import CellWriter
from xl.sheets.baseline import build_baseline
from xl.sheets.inputs import build_inputs
from xl.sheets.lists import build_lists
from xl.sheets.sources import build_sources
from xl.styles import Styles

NAME_TO_FIELD = {
    "BL_FirmVA": "firm_va_meur", "BL_SectorVA": "sector_va_meur",
    "BL_RatioVA": "ratio_va", "BL_RatioTurnover": "ratio_turnover",
    "BL_Gas_MWh": "gas_mwh", "BL_Elec_MWh": "elec_mwh",
    "BL_Heat_MWh": "heat_mwh", "BL_LPG_MWh": "lpg_mwh",
    "BL_Naphtha_MWh": "naphtha_mwh", "BL_Other_MWh": "other_mwh",
    "BL_Total_MWh": "total_mwh", "BL_FuelLoadMW": "fuel_load_mw",
    "BL_ElecBand": "elec_band", "BL_ElecPrice": "elec_price",
    "BL_GasGCVperNCV": "gas_gcv_per_ncv", "BL_GasGJ_GCV": "gas_gj_gcv",
    "BL_GasBand": "gas_band", "BL_GasPriceNCV": "gas_price_ncv",
    "BL_Fleet_MWh": "fleet_mwh", "BL_Fleet_t": "fleet_t",
    "BL_Scope1Stationary": "s1_stationary_t", "BL_Scope1": "s1_total_t",
    "BL_S2_LB": "s2_lb_t", "BL_S2_MB": "s2_mb_t",
    "BL_S12_LB": "s12_lb_t", "BL_S12_MB": "s12_mb_t",
}
RANGE_NAMES = ("Rng_ElecLower", "Rng_ElecS1", "Rng_ElecS2", "Rng_Elec26S1",
               "Rng_GasLower", "Rng_GasS1", "Rng_GasS2", "Rng_Gas26S1")


def _local_build(extra=()):
    """Task 1 local builder: Inputs, Sources, Lists, then Baseline."""
    dataset = build.load_dataset("config")
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, build.OPTIONS)
    styles = Styles(wb)
    cells = CellWriter(wb)
    inputs = build_inputs(wb, styles, cells, dataset, BUILD)
    build_sources(wb, styles, cells, dataset, BUILD)
    build_lists(wb, styles, cells, dataset, BUILD)
    build_baseline(wb, styles, cells, dataset, BUILD, inputs)
    for e in extra:
        e(wb, styles, cells)
    wb.close()
    data = buf.getvalue()
    for rec in cells.registry:
        lint_or_raise(rec.text, rec.sheet, cells.tags)
    scan_or_raise(data)
    return data, cells


class BaselineSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.cells = _local_build()
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        cls.wbv = openpyxl.load_workbook(io.BytesIO(cls.data), data_only=True)
        cls.ws = cls.wb["Baseline"]
        cls.wsv = cls.wbv["Baseline"]
        cls.ref = compute_baseline(
            model_values(build.load_dataset("config").inputs))

    def _cell(self, name, wb):
        ref = self.cells.names[name]
        sheet, addr = ref[1:].split("!")
        return wb[sheet][addr.replace("$", "")]

    def test_title_and_note(self):
        self.assertIn("reference year 2024", self.ws["B2"].value)
        self.assertIn("net calorific value (NCV)", self.ws["B3"].value)

    def test_names_defined(self):
        for n in tuple(NAME_TO_FIELD) + RANGE_NAMES:
            self.assertIn(n, self.cells.names)

    def test_band_formulas_exact(self):
        self.assertEqual(self._cell("BL_ElecBand", self.wb).value,
                         "=MATCH(BL_Elec_MWh,Rng_ElecLower,1)")
        self.assertEqual(self._cell("BL_GasBand", self.wb).value,
                         "=MATCH(BL_GasGJ_GCV,Rng_GasLower,1)")
        self.assertEqual(self._cell("BL_ElecPrice", self.wb).value[:9],
                         "=AVERAGE(")

    def test_cached_values_match_reference(self):
        for name, field in NAME_TO_FIELD.items():
            got = self._cell(name, self.wbv).value
            want = getattr(self.ref, field)
            self.assertAlmostEqual(got, want, delta=abs(want) * 1e-12,
                                   msg=name)

    def test_every_formula_has_cached_value(self):
        for row in self.ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    self.assertIsNotNone(self.wsv[c.coordinate].value,
                                         c.coordinate)

    def test_scope2_columns_adjacent(self):
        lb = self.cells.names["BL_S2_LB"]
        mb = self.cells.names["BL_S2_MB"]
        self.assertTrue(lb.startswith("=Baseline!$D$"))
        self.assertTrue(mb.startswith("=Baseline!$E$"))
        self.assertEqual(lb.split("$")[-1], mb.split("$")[-1])

    def test_lb_mb_tags(self):
        t = self.cells.tags
        for n, tag in (("EF_GridLB", "LB"), ("BL_S2_LB", "LB"),
                       ("BL_S12_LB", "LB"), ("EF_ResidualMB", "MB"),
                       ("BL_S2_MB", "MB"), ("BL_S12_MB", "MB")):
            self.assertEqual(t.tags_for(n, "Baseline"), frozenset([tag]), n)

    def test_no_formula_adds_lb_and_mb(self):
        for row in self.ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith("="):
                    self.assertFalse("S2_LB" in v and "S2_MB" in v)

    def test_lb_plus_mb_negative(self):
        def bad(wb, styles, cells):
            ws = wb.get_worksheet_by_name("Baseline")
            cells.formula(ws, 150, 3, "=BL_S2_LB+BL_S2_MB",
                          styles.get("calc", "tco2e"), value=0.0)
        with self.assertRaises(LintError):
            _local_build((bad,))

    def test_text_statements(self):
        texts = [c.value for row in self.ws.iter_rows() for c in row
                 if isinstance(c.value, str)]
        joined = " ".join(texts)
        for needle in ("Excluded: no official sector-level Scope 3",
                       "dominated by large petrochemical",
                       "Analyst assumption", "lower bound on rated thermal",
                       "memo only: energy balance covers C20 + C21",
                       "never added"):
            self.assertIn(needle, joined)

    def test_checks_ok(self):
        vals = [c.value for row in self.wsv.iter_rows() for c in row
                if c.value in ("OK", "ERROR")]
        self.assertEqual(vals, ["OK", "OK"])


if __name__ == "__main__":
    unittest.main()
