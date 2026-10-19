"""Independent baseline reference model tests (plan 02-08).

Expectations come from the 02-RESEARCH worked example (computed independently
of the workbook). Figures are model values: MWh NCV, EUR/MWh, tCO2e.
"""
import ast
import dataclasses
import os
import unittest

from checkmodel import baseline_reference as br
from checkmodel.baseline_reference import (
    BaselineResult, compute_baseline, excel_match_approx, model_values)
from config.inputs import INPUTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "checkmodel", "baseline_reference.py")


def _b(v=None):
    return compute_baseline(v if v is not None else model_values(INPUTS))


class TestBaselineReference(unittest.TestCase):
    def test_firm_and_ratio(self):
        b = _b()
        self.assertAlmostEqual(b.firm_va_meur, 23.058909, delta=1e-6)
        self.assertAlmostEqual(b.sector_va_meur, 25831.28, delta=1e-6)
        self.assertAlmostEqual(b.ratio_va, 0.000892673886, delta=1e-9 * 0.00089)
        self.assertAlmostEqual(b.ratio_va_c20_only, 0.002587568, delta=1e-8)

    def test_energy_by_carrier(self):
        b = _b()
        for name, exp in (("gas_mwh", 15501.749), ("elec_mwh", 12016.015),
                          ("heat_mwh", 1991.357), ("lpg_mwh", 2816.071),
                          ("naphtha_mwh", 7280.524), ("other_mwh", 594.326),
                          ("total_mwh", 40200.043)):
            self.assertAlmostEqual(getattr(b, name), exp, delta=0.01, msg=name)
        self.assertAlmostEqual(b.sector_remainder_mwh,
                               2396.814 * 277.7777777777778, delta=0.5)
        self.assertAlmostEqual(b.gasoil_share_of_remainder, 0.477217, delta=1e-6)

    def test_loads_and_threshold(self):
        b = _b()
        self.assertAlmostEqual(b.fuel_mwh, 26192.671, delta=0.01)
        self.assertAlmostEqual(b.fuel_load_mw, 2.990031, delta=1e-6)
        self.assertAlmostEqual(b.total_load_mw, 4.589046, delta=1e-6)
        self.assertEqual(b.below_ets1_threshold, "Below")

    def test_bands_and_prices(self):
        b = _b()
        self.assertEqual(b.elec_band, 4)
        self.assertEqual(b.elec_band_code, "ID")
        self.assertAlmostEqual(b.elec_price, 161.5, delta=1e-9)
        self.assertAlmostEqual(b.gas_gcv_per_ncv, 1.107948, delta=1e-6)
        self.assertAlmostEqual(b.gas_gj_gcv, 61830.476, delta=0.01)
        self.assertEqual(b.gas_band, 3)
        self.assertEqual(b.gas_band_code, "I3")
        self.assertAlmostEqual(b.gas_price_gcv, 49.3, delta=1e-9)
        self.assertAlmostEqual(b.gas_price_ncv, 54.621836, delta=1e-6)
        self.assertAlmostEqual(b.elec_cost_eur, b.elec_mwh * b.elec_price)
        self.assertAlmostEqual(b.gas_cost_eur, b.gas_mwh * b.gas_price_ncv)

    def test_fleet(self):
        b = _b()
        self.assertAlmostEqual(b.fleet_km, 250000, delta=1e-6)
        self.assertAlmostEqual(b.fleet_litres, 17892.117, delta=0.01)
        self.assertAlmostEqual(b.fleet_l_per_100km, 7.156847, delta=1e-5)
        self.assertAlmostEqual(b.fleet_mwh, 177.304, delta=0.01)
        self.assertAlmostEqual(b.fleet_t, 46.225, delta=0.01)

    def test_scope1(self):
        b = _b()
        self.assertAlmostEqual(b.s1_gas_t, 3131.198, delta=0.01)
        self.assertAlmostEqual(b.s1_lpg_t, 648.598, delta=0.01)
        self.assertAlmostEqual(b.s1_naphtha_t, 1812.195, delta=0.01)
        self.assertAlmostEqual(b.s1_other_t, 162.180, delta=0.01)
        self.assertAlmostEqual(b.s1_stationary_t, 5754.171, delta=0.01)
        self.assertAlmostEqual(b.s1_total_t, b.s1_stationary_t + b.fleet_t)
        self.assertAlmostEqual(b.s1_excl_naphtha_t,
                               b.s1_total_t - b.s1_naphtha_t)

    def test_air_accounts(self):
        b = _b()
        self.assertAlmostEqual(b.air_sector_t, 9412721.84, delta=0.01)
        self.assertAlmostEqual(b.air_scaled_t, 8402.491, delta=0.01)
        self.assertAlmostEqual(b.air_gap_t, b.air_scaled_t - b.s1_stationary_t)
        self.assertAlmostEqual(b.combustion_share_of_air, 0.684817, delta=1e-6)

    def test_scope2_separate_bases(self):
        b = _b()
        self.assertAlmostEqual(b.s2_elec_lb_t, 1850.466, delta=0.01)
        self.assertAlmostEqual(b.s2_elec_mb_t, 2054.859, delta=0.01)
        self.assertAlmostEqual(b.s2_heat_t, 349.065, delta=0.01)
        self.assertAlmostEqual(b.s2_lb_t, b.s2_elec_lb_t + b.s2_heat_t)
        self.assertAlmostEqual(b.s2_mb_t, b.s2_elec_mb_t + b.s2_heat_t)
        self.assertAlmostEqual(b.s12_lb_t, b.s1_total_t + b.s2_lb_t)
        self.assertAlmostEqual(b.s12_mb_t, b.s1_total_t + b.s2_mb_t)

    def test_checks_ok(self):
        b = _b()
        self.assertEqual(b.check_carriers, "OK")
        self.assertEqual(b.check_ratio, "OK")

    def test_excel_match_approx(self):
        bounds = [0, 20, 500]
        self.assertEqual(excel_match_approx(0, bounds), 1)
        self.assertEqual(excel_match_approx(20, bounds), 2)
        self.assertEqual(excel_match_approx(499.9, bounds), 2)
        self.assertEqual(excel_match_approx(1e9, bounds), 3)
        with self.assertRaises(ValueError):
            excel_match_approx(-1, bounds)

    def test_c21_flag_off(self):
        v = dict(model_values(INPUTS))
        base = _b(v)
        v["Base_NRG_IncludesC21"] = 0.0
        b = _b(v)
        self.assertAlmostEqual(b.ratio_va, b.ratio_va_c20_only)
        self.assertAlmostEqual(b.gas_mwh / base.gas_mwh, 2.9, delta=0.05)

    def test_remainder_absorbs_and_negative_errors(self):
        v = dict(model_values(INPUTS))
        base = _b(v)
        v["Base_NRG_Total"] += 1
        b = _b(v)
        self.assertEqual(b.check_carriers, "OK")
        self.assertGreater(b.other_mwh, base.other_mwh)
        v = dict(model_values(INPUTS))
        v["Base_NRG_Gas"] = v["Base_NRG_Total"] + 1
        self.assertEqual(_b(v).check_carriers, "ERROR")

    def test_model_values_conversion(self):
        v = model_values(INPUTS)
        self.assertAlmostEqual(v["Base_NRG_Gas"], 62515.885 * 277.7777777777778,
                               delta=0.01)
        self.assertAlmostEqual(v["Const_HoursPerYear"], 8760.0)
        self.assertNotIn("Fin_HICP_EA_2010_series", v)

    def test_no_lb_mb_sum(self):
        for f in dataclasses.fields(BaselineResult):
            n = f.name
            self.assertFalse("lb" in n.split("_") and "mb" in n.split("_"), n)
        with open(SRC) as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                names = [n.id for n in ast.walk(node) if isinstance(n, ast.Name)]
                names += [n.attr for n in ast.walk(node)
                          if isinstance(n, ast.Attribute)]
                txt = " ".join(names).lower()
                self.assertFalse("_lb" in txt and "_mb" in txt, txt)

    def test_imports_stdlib_and_config_only(self):
        with open(SRC) as fh:
            tree = ast.parse(fh.read())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.add(node.module.split(".")[0])
        self.assertLessEqual(mods, {"math", "typing", "dataclasses", "config"})


if __name__ == "__main__":
    unittest.main()
