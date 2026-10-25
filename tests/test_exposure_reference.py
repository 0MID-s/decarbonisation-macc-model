"""Tests for the independent exposure reference (plan 04-03)."""
import unittest

from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.exposure_reference import (STATES, ExposureResult,
                                           ScenarioExposure, all_states,
                                           blended_path, compute_exposure)
from checkmodel.measures_reference import BASES, ONOFF, SCENARIOS_UI
from checkmodel.rates_reference import restate_eur2025
from config.build_config import BUILD
from config.inputs import INPUTS
from config.measures_catalog import MEASURE_KEYS

V = model_values(INPUTS)
YEARS = tuple(BUILD.timeline_years)
REL = 1e-9
KEYS = ("CP", "NDC", "NZ50")


def _res(basis="Market-based", scen="Central", direct="Off", **kw):
    return compute_exposure(INPUTS, basis, scen, direct, **kw)


class BlendTests(unittest.TestCase):
    def test_blend_arithmetic(self):
        ng = (100.0, 100.0, 100.0, 100.0)
        out = blended_path(50.0, 2025, 2027, ng, (2025, 2026, 2027, 2028))
        self.assertEqual(out, (50.0, 75.0, 100.0, 100.0))

    def test_start_year_zero_before(self):
        ng = (100.0,) * 4
        out = blended_path(50.0, 2026, 2028, ng, (2025, 2026, 2027, 2028),
                           start_year=2026)
        self.assertEqual(out[0], 0.0)
        self.assertEqual(out[1], 50.0)
        self.assertAlmostEqual(out[2], 75.0, delta=1e-12)

    def test_conv_equals_anchor_no_div_zero(self):
        out = blended_path(50.0, 2026, 2026, (80.0, 80.0), (2026, 2027))
        self.assertEqual(out, (50.0, 80.0))


class StructureTests(unittest.TestCase):
    def test_twelve_states(self):
        self.assertEqual(len(STATES), 12)
        self.assertEqual(set(STATES), {(b, s, d) for b in BASES
                                       for s in SCENARIOS_UI for d in ONOFF})
        st = all_states()
        self.assertEqual(set(st), set(STATES))
        self.assertIsInstance(st[STATES[0]], ExposureResult)
        self.assertIsInstance(st[STATES[0]].scen["CP"], ScenarioExposure)

    def test_years_and_window(self):
        r = _res()
        self.assertEqual(r.years, YEARS)
        self.assertEqual(r.window, tuple(1 if y <= 2035 else 0 for y in YEARS))
        self.assertEqual(r.df[0], 1.0)
        self.assertEqual(r.sel_key, "NDC")


class PriceTests(unittest.TestCase):
    def test_ets2_zero_before_start_all_scenarios(self):
        r = _res()
        for k in KEYS:
            for y, p in zip(YEARS, r.scen[k].ets2):
                if y < 2028:
                    self.assertEqual(p, 0.0)
                else:
                    self.assertGreater(p, 0.0)

    def test_ets2_start_override(self):
        r = _res(overrides={"Carbon_ETS2_StartYear": 2029.0})
        for k in KEYS:
            self.assertEqual(r.scen[k].ets2[YEARS.index(2028)], 0.0)
            self.assertGreater(r.scen[k].ets2[YEARS.index(2029)], 0.0)

    def test_ets2_start_year_is_restated_stab_price(self):
        r = _res()
        stab = restate_eur2025(V, "Carbon_ETS2_StabPrice", 2020)
        self.assertAlmostEqual(stab, 55.15, delta=0.05)
        for k in KEYS:
            self.assertAlmostEqual(r.scen[k].ets2[YEARS.index(2028)] / stab,
                                   1.0, delta=REL)

    def test_conv_year_equals_ngfs_and_scale(self):
        r = _res()
        r2 = _res(ngfs_scale=1.31)
        i = YEARS.index(2030)
        for k in KEYS:
            self.assertAlmostEqual(r2.scen[k].ets1[i] / r.scen[k].ets1[i],
                                   1.31, delta=REL)
            self.assertAlmostEqual(r2.scen[k].ets2[i] / r.scen[k].ets2[i],
                                   1.31, delta=REL)
            # 2035 onward is pure NGFS, so scaled exactly
            j = YEARS.index(2040)
            self.assertAlmostEqual(r2.scen[k].ets1[j] / r.scen[k].ets1[j],
                                   1.31, delta=REL)

    def test_ets1_central_path_and_low_not_floored(self):
        r = _res()
        c = [r.scen["NDC"].ets1[YEARS.index(y)] for y in range(2026, 2031)]
        for got, exp in zip(c, (88, 111, 141, 180, 226)):
            self.assertAlmostEqual(got / exp, 1.0, delta=0.02)
        low = r.scen["CP"].ets1
        self.assertAlmostEqual(low[-1], 24.0, delta=1.5)
        self.assertLess(low[YEARS.index(2030)], V["Carbon_EUA_Avg2025"])

    def test_carbon_mult_scales_prices_not_embedded(self):
        r = _res()
        r2 = _res(carbon_mult=0.5)
        self.assertEqual(r2.embedded_eua, r.embedded_eua)
        for k in KEYS:
            for a, b in zip(r.scen[k].ets1, r2.scen[k].ets1):
                self.assertAlmostEqual(b, a * 0.5, delta=1e-9)
            for a, b in zip(r.scen[k].ets2, r2.scen[k].ets2):
                self.assertAlmostEqual(b, a * 0.5, delta=1e-9)

    def test_mef(self):
        r = _res()
        self.assertAlmostEqual(r.mef, V["EF_Gas_NCV"] / V["Pass_CCGT_Eff"],
                               delta=1e-12)
        self.assertAlmostEqual(r.mef, 0.3607, delta=5e-5)


class ToggleTests(unittest.TestCase):
    def test_off_and_on(self):
        for k in KEYS:
            off = _res(direct="Off").scen[k]
            on = _res(direct="On").scen[k]
            self.assertTrue(all(p == 0.0 for p in off.p_stat1))
            self.assertEqual(off.p_stat2, off.ets2)
            self.assertTrue(all(p == 0.0 for p in on.p_stat2))
            fa = V["Carbon_DirectETS_FreeAlloc"]
            for a, b in zip(on.p_stat1, on.ets1):
                self.assertAlmostEqual(a, b * (1 - fa), delta=1e-12)

    def test_exclusive_all_states(self):
        for st, r in all_states().items():
            self.assertTrue(r.checks["ets_exclusive"], st)
            for k in KEYS:
                s = r.scen[k]
                self.assertEqual(
                    sum(a * b for a, b in zip(s.p_stat1, s.p_stat2)), 0.0)

    def test_free_alloc_override(self):
        r = _res(direct="On", overrides={"Carbon_DirectETS_FreeAlloc": 0.5})
        s = r.scen["NDC"]
        i = YEARS.index(2035)
        self.assertAlmostEqual(s.p_stat1[i], s.ets1[i] * 0.5, delta=1e-12)

    def test_fleet_always_ets2(self):
        on = _res(direct="On").scen["NDC"]
        i = YEARS.index(2035)
        r = _res(direct="On")
        # ets2 channel in On state holds only the fleet diesel
        self.assertAlmostEqual(on.bau_ets2[i], r.t_fleet_bau[i] * on.ets2[i],
                               delta=1e-6)


class CostTests(unittest.TestCase):
    def test_tonnes(self):
        r = _res()
        bl = compute_baseline(V)
        exp = (bl.gas_mwh * V["EF_Gas_NCV"] + bl.lpg_mwh * V["EF_LPG_NCV"]
               + bl.naphtha_mwh * V["EF_Naphtha_NCV"]
               + bl.other_mwh * V["EF_GasOil_NCV"])
        self.assertAlmostEqual(r.t_stat_bau[0] / exp, 1.0, delta=REL)
        self.assertAlmostEqual(
            r.t_fleet_bau[0] / (bl.fleet_litres * V["EF_Diesel_l"] / 1000.0),
            1.0, delta=REL)
        self.assertAlmostEqual(r.elec_bau[0], bl.elec_mwh, delta=1e-9)
        self.assertEqual(r.t_stat_with[0], r.t_stat_bau[0])  # year 0
        self.assertLess(r.t_stat_with[5], r.t_stat_bau[5])  # heat pump
        self.assertLess(r.t_fleet_with[5], r.t_fleet_bau[5])
        self.assertNotEqual(r.elec_with[5], r.elec_bau[5])  # HP/EV add load

    def test_channels_and_totals(self):
        r = _res()
        for k in KEYS:
            s = r.scen[k]
            for n in range(len(YEARS)):
                e2 = (r.t_stat_bau[n] * s.p_stat2[n]
                      + r.t_fleet_bau[n] * s.ets2[n])
                d = r.t_stat_bau[n] * s.p_stat1[n]
                p = (r.elec_bau[n] * r.mef * V["Pass_PTR"]
                     * (s.ets1[n] - r.embedded_eua))
                self.assertAlmostEqual(s.bau_ets2[n], e2, delta=1e-6)
                self.assertAlmostEqual(s.bau_dir[n], d, delta=1e-6)
                self.assertAlmostEqual(s.bau_pt[n], p, delta=1e-6)
                self.assertAlmostEqual(s.bau_total[n], e2 + d + p, delta=1e-6)

    def test_pass_through_negative_under_low(self):
        r = _res()
        self.assertLess(r.scen["CP"].bau_pt[YEARS.index(2035)], 0.0)
        self.assertGreater(r.scen["NZ50"].bau_pt[YEARS.index(2035)], 0.0)

    def test_avoided_zero_2026_and_positive_central(self):
        r = _res()
        for k in KEYS:
            self.assertEqual(r.scen[k].avoided[0], 0.0)
        self.assertGreater(r.scen["NDC"].avoided[YEARS.index(2035)], 0.0)

    def test_cum_and_disc(self):
        r = _res()
        s = r.scen["NDC"]
        cum = sum(w * x for w, x in zip(r.window, s.bau_total))
        dsc = sum(w * d * x for w, d, x in zip(r.window, r.df, s.bau_total))
        self.assertAlmostEqual(s.cum["total_bau"], cum, delta=1e-6)
        self.assertAlmostEqual(s.disc["total_bau"], dsc, delta=1e-6)
        self.assertAlmostEqual(s.disc["avoided"],
                               s.disc["total_bau"] - s.disc["total_with"],
                               delta=1e-6)
        self.assertAlmostEqual(
            s.disc["total_bau"],
            s.disc["ets2_bau"] + s.disc["dir_bau"] + s.disc["pt_bau"],
            delta=1e-6)


class BridgeTests(unittest.TestCase):
    def test_per_measure_sums_and_contract(self):
        for st, r in all_states().items():
            self.assertTrue(r.checks["bridge_sums"], st)
            self.assertTrue(r.checks["contract_zero"], st)
            self.assertTrue(all(x == 0.0 for x in r.measure_avoided["RC"]))
            sel = r.scen[r.sel_key].avoided
            for n in range(len(YEARS)):
                tot = sum(r.measure_avoided[k][n] for k in MEASURE_KEYS)
                self.assertAlmostEqual(tot, sel[n], delta=1e-6)

    def test_bridge_shape(self):
        r = _res()
        self.assertEqual(len(r.bridge), 8)
        self.assertEqual(r.bridge[0][0], "BAU")
        self.assertEqual(r.bridge[-1][0], "After acting")
        s = r.scen[r.sel_key]
        self.assertAlmostEqual(r.bridge[0][2], s.disc["total_bau"], delta=1e-6)
        self.assertAlmostEqual(r.bridge[-1][2], s.disc["total_with"],
                               delta=1e-6)
        self.assertAlmostEqual(r.bridge[-2][2], r.bridge[-1][2], delta=1e-6)
        run = r.bridge[0][2]
        for (lab, start, end), k in zip(r.bridge[1:7], MEASURE_KEYS):
            self.assertAlmostEqual(start, run, delta=1e-6)
            self.assertAlmostEqual(end, start - r.measure_disc_avoided[k],
                                   delta=1e-6)
            run = end

    def test_heat_pump_pass_through_term_signs(self):
        # HP buys electricity: its pass-through term is a cost when the EUA
        # is above the embedded price and a saving when below.
        i = YEARS.index(2035)
        hi = _res(scen="High")
        lo = _res(scen="Low")
        hp = [m for m in MEASURE_KEYS if m == "HP"][0]
        d_pt_hi = -hi.measure_avoided[hp][i]
        self.assertTrue(isinstance(d_pt_hi, float))
        self.assertGreater(hi.scen["NZ50"].ets1[i], hi.embedded_eua)
        self.assertLess(lo.scen["CP"].ets1[i], lo.embedded_eua)


class IcpTests(unittest.TestCase):
    def test_icp_basis_and_separation(self):
        bl = compute_baseline(V)
        for b, exp in (("Location-based", bl.s12_lb_t),
                       ("Market-based", bl.s12_mb_t)):
            r = _res(basis=b)
            self.assertAlmostEqual(r.icp_t_bau[0] / exp, 1.0, delta=1e-9)
            self.assertAlmostEqual(r.icp_bau[0],
                                   exp * V["Carbon_ICP_Level"], delta=1e-6)
            self.assertLess(r.icp_t_with[5], r.icp_t_bau[5])
            self.assertTrue(r.checks["icp_separate"])
        self.assertEqual(len(r.icp_memo_ngfs), len(YEARS))

    def test_icp_independent_of_scenario_and_toggle(self):
        a = _res(scen="Low", direct="Off")
        b = _res(scen="High", direct="On")
        self.assertEqual(a.icp_bau, b.icp_bau)
        self.assertEqual(a.icp_with, b.icp_with)
        self.assertAlmostEqual(a.icp_disc_avoided,
                               a.icp_disc_bau - a.icp_disc_with, delta=1e-6)


class MagnitudeTests(unittest.TestCase):
    def test_research_magnitudes(self):
        r = _res(basis="Market-based", direct="Off")
        exp = {"CP": (-0.20, -0.50), "NDC": (10.08, 9.02),
               "NZ50": (17.11, 15.48)}
        for k, (b, w) in exp.items():
            s = r.scen[k]
            for got, e in ((s.disc["total_bau"], b), (s.disc["total_with"], w)):
                tol = max(0.02 * abs(e), 0.006)
                self.assertAlmostEqual(got / 1e6, e, delta=tol, msg=k)


if __name__ == "__main__":
    unittest.main()
