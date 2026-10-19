"""Rates reference and sheet tests (D-01 guard)."""
import io
import unittest

import openpyxl

import build
from checkmodel.baseline_reference import model_values
from checkmodel.rates_reference import (
    EXEMPT_PREFIXES, eur2025_conversions, hicp_ratio, restate_eur2025)
from config.schema import Kind


class RatesReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = build.load_dataset("config")
        cls.v = model_values(cls.ds.inputs)

    def test_ratio_and_restatements(self):
        self.assertAlmostEqual(hicp_ratio(self.v, 2020), 128.75 / 105.06,
                               places=9)
        self.assertAlmostEqual(
            restate_eur2025(self.v, "Carbon_ETS2_StabPrice", 2020),
            45 * 128.75 / 105.06, delta=1e-4)
        self.assertAlmostEqual(
            restate_eur2025(self.v, "Meas_PV_CapexDEA", 2020),
            self.v["Meas_PV_CapexDEA"] * 128.75 / 105.06, delta=1e-9)
        self.assertAlmostEqual(
            restate_eur2025(self.v, "Meas_PV_CapexDEA", 2020), 780.02,
            delta=0.1)

    def test_conversions_contents(self):
        got = dict(eur2025_conversions(self.ds.inputs))
        for k in ("Meas_PV_CapexDEA", "Meas_PV_FixOMDEA",
                  "Carbon_ETS2_StabPrice"):
            self.assertEqual(got[k], 2020)

    def test_d01_guard_every_euro_input_converted_or_exempt(self):
        conv = dict(eur2025_conversions(self.ds.inputs))
        for r in self.ds.inputs:
            pb = r.price_basis
            if (r.kind != Kind.SCALAR or r.section == "Constants"
                    or pb.currency != "EUR" or pb.year >= 2025):
                continue
            self.assertTrue(r.id in conv or r.id.startswith(EXEMPT_PREFIXES),
                            r.id)

    def test_missing_hicp_raises(self):
        with self.assertRaises(ValueError):
            hicp_ratio(self.v, 1999)


class RatesSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ds = build.load_dataset("config")
        data, _ = build.build_bytes("main", ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(data))
        cls.wbv = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        cls.ds = ds
        cls.v = model_values(ds.inputs)

    def _addr(self, wb, name):
        sheet, addr = self.wb.defined_names[name].attr_text.split("!")
        return wb[sheet][addr.replace("$", "")]

    def test_ratio_names_and_formulas(self):
        c = self._addr(self.wb, "Rate_HICP_2025_2020")
        self.assertEqual(c.value, "=Fin_HICP_EA_2025/Fin_HICP_EA_2020")

    def test_every_conversion_has_name_formula_value(self):
        for iid, y in eur2025_conversions(self.ds.inputs):
            n = iid + "_EUR2025"
            self.assertEqual(self._addr(self.wb, n).value,
                             "=%s*Rate_HICP_2025_%d" % (iid, y))
            self.assertAlmostEqual(
                self._addr(self.wbv, n).value,
                restate_eur2025(self.v, iid, y), delta=1e-9)

    def test_ets2_stab_price(self):
        got = self._addr(self.wbv, "Carbon_ETS2_StabPrice_EUR2025").value
        self.assertAlmostEqual(got, 55.15, places=2)


if __name__ == "__main__":
    unittest.main()
