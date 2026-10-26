"""Tests for checkmodel.measures_reference (plan 03-06).

Sizing scalars are recomputed here with explicit arithmetic from the model
values, independently of the module internals.
"""
import unittest

from checkmodel import appraisal as ap
from checkmodel import measures_reference as mr
from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.rates_reference import discount_rate_real, restate_eur2025
from config.inputs import INPUTS
from xl.sheets import lists

V = model_values(INPUTS)
BL = compute_baseline(V)
STATES = [(b, s) for b in mr.BASES for s in mr.SCENARIOS_UI]
CACHE = {}


def res(basis, scen):
    if (basis, scen) not in CACHE:
        CACHE[(basis, scen)] = mr.compute_measures(INPUTS, basis, scen)
    return CACHE[(basis, scen)]


def rel(tc, a, b, tol=1e-9):
    tc.assertAlmostEqual(a, b, delta=tol * max(1.0, abs(b)))


class Constants(unittest.TestCase):
    def test_lists_match(self):
        self.assertEqual(mr.BASES, lists.BASES)
        self.assertEqual(mr.SCENARIOS_UI, lists.SCENARIOS)
        self.assertEqual(mr.DEFAULT_STATE, ("Market-based", "Central"))

    def test_bad_state(self):
        with self.assertRaises(ValueError):
            mr.compute_measures(INPUTS, "X", "Central")
        with self.assertRaises(ValueError):
            mr.compute_measures(INPUTS, "Market-based", "X")


class Sizing(unittest.TestCase):
    def setUp(self):
        self.r = res(*mr.DEFAULT_STATE)

    def test_led(self):
        kwh = BL.elec_mwh * 1000 * 0.06 * 0.5 * 0.5
        units = kwh / V["Meas_LED_ZMSaving"]
        capex = units * V["Meas_LED_ZMCapex"] * (
            V["Fin_HICP_EA_2025"] / V["Fin_HICP_EA_2023"])
        m = self.r.by_key("LED")
        rel(self, m.capex, capex)
        rel(self, m.d_elec[1], -kwh / 1000)
        self.assertEqual(m.d_elec[0], 0.0)
        self.assertEqual(m.life, 15)

    def test_vsd(self):
        kwh = BL.elec_mwh * 1000 * 0.10 * 0.5 * 0.15
        units = kwh / V["Meas_VSD_Saving"]
        capex = units * V["Meas_VSD_ZMCapex"] * (
            V["Fin_HICP_EA_2025"] / V["Fin_HICP_EA_2023"])
        m = self.r.by_key("VSD")
        rel(self, m.capex, capex)
        rel(self, m.d_elec[5], -kwh / 1000)

    def test_hp(self):
        low = 21.0 / (25.3 + 12.5 + 21.0)
        heat = BL.gas_mwh * 0.939 * low
        kw = heat / 8000.0 * 1000
        m = self.r.by_key("HP")
        rel(self, m.capex, kw * (1200.0 - 90.0))
        rel(self, m.full_capex, kw * 1200.0)
        rel(self, m.d_gas[1], -heat / 0.939)
        rel(self, m.d_elec[1], heat / 2.7)
        om = -(kw * (2.494 - 2.0) + heat * (3.6 - 1.23))
        rel(self, m.om_benefit, om)
        self.assertAlmostEqual(m.indirect_diff, 0.0, places=9)
        self.assertEqual(m.life, 20)

    def test_fleet(self):
        m = self.r.by_key("Fleet")
        rel(self, m.capex, 10 * (15000.0 + 2000.0))
        rel(self, m.full_capex, 10 * (35000.0 + 15000.0 + 2000.0))
        rel(self, m.om_benefit, BL.fleet_km * 0.03)
        rel(self, m.d_diesel[1], -BL.fleet_litres)
        rel(self, m.d_elec[1], BL.fleet_km * 0.25 / 1000)
        self.assertEqual(m.life, 8)

    def test_pv(self):
        m = self.r.by_key("PV")
        f = V["Fin_HICP_EA_2025"] / V["Fin_HICP_EA_2020"]
        rel(self, m.capex, 1000 * V["Meas_PV_CapexDEA"] * f)
        rel(self, m.om_benefit, -1000 * V["Meas_PV_FixOMDEA"] * f)
        rel(self, m.d_elec[1], -1000 * 942.09 / 1000)
        rel(self, m.d_elec[2], -1000 * 942.09 / 1000 * 0.997)
        rel(self, m.sizing["roof_area_m2"], 4479.0)
        self.assertEqual(m.sizing["peak_ok"], 1.0)

    def test_rc(self):
        m = self.r.by_key("RC")
        self.assertEqual(m.capex, 0.0)
        s5 = self.r.stack.s5
        self.assertAlmostEqual(m.covered[1], s5[1], places=9)
        self.assertEqual(m.covered[0], 0.0)

    def test_residual_and_replacements(self):
        r = self.r
        for k, frac in (("LED", 1 / 15.0), ("VSD", 1 / 15.0),
                        ("PV", 11 / 40.0), ("HP", 11 / 20.0),
                        ("Fleet", 3 / 8.0)):
            self.assertAlmostEqual(r.by_key(k).res_frac, frac, places=12)
        self.assertEqual(r.by_key("LED").replacement_years, (2041,))
        self.assertEqual(r.by_key("VSD").replacement_years, (2041,))
        self.assertEqual(r.by_key("Fleet").replacement_years,
                         (2034, 2042, 2050))
        self.assertEqual(r.by_key("HP").replacement_years, (2046,))
        self.assertEqual(r.by_key("PV").replacement_years, ())

    def test_timing(self):
        m = self.r.by_key("LED")
        self.assertAlmostEqual(m.capex_row[0], -m.capex, places=9)
        self.assertEqual(m.years_ok if hasattr(m, "years_ok") else True, True)
        self.assertEqual(self.r.years[0], 2026)
        self.assertEqual(self.r.years[-1], 2055)
        self.assertAlmostEqual(m.residual_row[-1], m.capex / 15.0, places=9)
        self.assertEqual(sum(1 for x in m.residual_row if x), 1)

    def test_rates(self):
        rel(self, self.r.rate, discount_rate_real(V))
        rel(self, self.r.diesel_exvat, 1.65859 / 1.21)
        for scen, lo, hi in (("Low", 24.4, 24.4), ("Central", 216.4, 216.4),
                             ("High", 536.0, 536.0)):
            p = res("Market-based", scen).ref_price
            self.assertTrue(0.9 * lo < p < 1.1 * hi, (scen, p))


class Invariants(unittest.TestCase):
    def test_all_states(self):
        for st in STATES:
            r = res(*st)
            rc = r.by_key("RC")
            self.assertTrue(all(x == 0 for x in rc.t_lb), st)
            self.assertGreater(rc.avg_t_mb, 0)
            self.assertTrue(r.stack.caps_ok, st)
            for m in r.measures:
                self.assertEqual(m.break_even, m.lev)
                self.assertAlmostEqual(m.npv, m.npv_memo, delta=1e-6)
                self.assertAlmostEqual(ap.npv0(0.0, m.cf_fin), sum(m.cf_fin),
                                       delta=1e-6)
                if isinstance(m.irr, float):
                    self.assertLess(abs(ap.npv0(m.irr, m.cf_fin)),
                                    1e-6 * max(1.0, m.capex))
            # electricity market-based tonnes are additive
            for n in range(1, 30):
                tot = sum(-m.d_elec[n] * r.f_mb[n] + m.covered[n] * r.f_mb[n]
                          for m in r.measures)
                self.assertAlmostEqual(tot, r.stack.s0[n] * r.f_mb[n],
                                       delta=1e-6)

    def test_basis_and_scenario_dependence(self):
        for b in mr.BASES:
            lev = [tuple(m.lev for m in res(b, s).measures)
                   for s in mr.SCENARIOS_UI]
            self.assertEqual(lev[0], lev[1])
            self.assertEqual(lev[1], lev[2])
        # financial NPV identical across all six states
        for i, m0 in enumerate(res(*STATES[0]).measures):
            for st in STATES:
                self.assertAlmostEqual(res(*st).measures[i].npv, m0.npv,
                                       delta=1e-6)
                self.assertEqual(res(*st).measures[i].irr, m0.irr)
        # basis changes the levelised cost of at least one measure
        a = [m.lev for m in res("Location-based", "Central").measures]
        b = [m.lev for m in res("Market-based", "Central").measures]
        self.assertNotEqual(a, b)

    def test_tiers_move_with_scenario(self):
        t = {s: res("Market-based", s).tiers for s in mr.SCENARIOS_UI}
        self.assertNotEqual(t["Low"], t["High"])
        self.assertEqual(res("Location-based", "Central").tiers[
            [m.key for m in res("Location-based", "Central").measures
             ].index("RC")], "Later")

    def test_subsidy_override(self):
        base = mr.compute_measures(INPUTS, "Market-based", "Central")
        sub = mr.compute_measures(INPUTS, "Market-based", "Central",
                                  {"Meas_PV_Subsidy": 0.3})
        m = sub.by_key("PV")
        self.assertAlmostEqual(m.npv - m.npv_pre_sub, 0.3 * m.capex,
                               delta=1e-6)
        self.assertAlmostEqual(m.npv_pre_sub, base.by_key("PV").npv,
                               delta=1e-6)

    def test_full_capex_memo(self):
        r = res(*mr.DEFAULT_STATE)
        for k in ("HP", "Fleet"):
            m = r.by_key(k)
            self.assertLess(m.npv_full_capex, m.npv)
        for k in ("LED", "VSD", "PV", "RC"):
            self.assertIsNone(r.by_key(k).npv_full_capex)

    def test_signs(self):
        r = res(*mr.DEFAULT_STATE)
        self.assertGreater(r.by_key("LED").npv, 0)
        self.assertGreater(r.by_key("VSD").npv, 0)
        self.assertGreater(r.by_key("PV").npv, 0)
        self.assertLess(r.by_key("HP").npv, 0)
        self.assertLess(r.by_key("Fleet").npv, 0)
        self.assertGreater(r.by_key("HP").lev, 0)

    def test_macc_table(self):
        r = res(*mr.DEFAULT_STATE)
        self.assertEqual(sorted(r.ranks), list(range(1, 7)))
        rows = mr.macc_table(r)
        costs = [x[2] for x in rows if x[3]]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(len(rows), 6)

    def test_eligibility_never_gives_negative_width(self):
        # WR-03: a fast-rising LB grid factor once made the heat pump (PV of
        # tonnes > 0, average tonnes < 0) and the fleet eligible with
        # negative chart widths. Eligibility now needs both > 0.
        for x in (0.08, 0.10):
            r = mr.compute_measures(INPUTS, "Location-based", "Central",
                                    overrides={"EF_GridLB_Change": x})
            self.assertTrue(all(w >= 0 for w in r.chart_widths), (x, r.chart_widths))
            for m in r.measures:
                self.assertEqual(m.eligible,
                                 m.pv_t_sel > 0 and m.avg_t_sel > 0, (x, m.key))
            self.assertFalse(r.by_key("HP" if x == 0.08 else "Fleet").eligible)


if __name__ == "__main__":
    unittest.main()
