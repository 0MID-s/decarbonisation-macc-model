"""Tests for the independent sensitivity reference (plan 04-04)."""
import unittest

from checkmodel import sensitivity_reference as sr
from checkmodel.appraisal import npv0
from checkmodel.baseline_reference import model_values
from checkmodel.exposure_reference import STATES
from checkmodel.sensitivity_reference import (RANK_FLIP_OVERRIDE,
                                              TORNADO_DRIVERS, all_states,
                                              compute_sensitivity,
                                              full_recompute_npv,
                                              untested_note_values)
from config.inputs import INPUTS

V = model_values(INPUTS)
MB, CE, OFF = "Market-based", "Central", "Off"
REL = 1e-6


def _s(basis=MB, scen=CE, direct=OFF, **kw):
    return compute_sensitivity(INPUTS, basis, scen, direct, **kw)


def _close(tc, a, b, rel=REL):
    tc.assertLessEqual(abs(a - b), rel * max(1.0, abs(a), abs(b)),
                       "%r vs %r" % (a, b))


def _row(s, driver):
    return [r for r in s.tornado if r.driver_id == driver][0]


class IdentityTests(unittest.TestCase):
    def test_npv_identities(self):
        s = _s()
        _close(self, s.npv_incl, s.npv_fin + s.pv_carbon)
        _close(self, s.pv_carbon, sum(s.pv_carbon_by_measure.values()))
        _close(self, s.pv_carbon,
               s.pv_ets2_gross + s.pv_pt_gross - s.pv_pt_embedded)
        _close(self, s.pv_pt_net, s.pv_pt_gross - s.pv_pt_embedded)
        _close(self, s.npv_fin, sum(s.npv_fin_by_measure.values()))
        for k in s.npv_fin_by_measure:
            _close(self, s.npv_incl_by_measure[k],
                   s.npv_fin_by_measure[k] + s.pv_carbon_by_measure[k])

    def test_expected_magnitudes(self):
        s = _s()
        self.assertAlmostEqual(s.pv_carbon / 1e6, 2.59, delta=0.03)
        self.assertAlmostEqual(s.npv_incl / 1e6, 2.52, delta=0.03)
        self.assertAlmostEqual(s.npv_fin / 1e6, -0.07, delta=0.03)

    def test_pv_energy_excludes_go(self):
        s = _s()
        _close(self, s.pv_energy, s.pv_elec + s.pv_gas + s.pv_diesel)
        self.assertGreater(s.pv_go_cost, 0.0)

    def test_portfolio_cf_matches_npv(self):
        s = _s()
        r = full_recompute_npv  # silence unused
        self.assertTrue(r)
        rate = s.rate_axis[2]
        _close(self, npv0(rate, s.portfolio_cf), s.npv_incl)

    def test_low_scenario_sign_flip(self):
        s = _s(scen="Low")
        for k in ("LED", "VSD", "PV"):
            self.assertLess(s.pv_carbon_by_measure[k], 0.0, k)
        self.assertAlmostEqual(s.pv_carbon / 1e6, 0.60, delta=0.05)


class GridTests(unittest.TestCase):
    def test_axis(self):
        s = _s()
        for a, e in zip(s.grid_axis, (0.6, 0.8, 1.0, 1.2, 1.4)):
            self.assertAlmostEqual(a, e, delta=1e-12)

    def test_centre(self):
        s = _s()
        _close(self, s.grid[2][2], s.npv_incl)

    def test_cell_formula(self):
        s = _s()
        for i, me in enumerate(s.grid_axis):
            for j, mc in enumerate(s.grid_axis):
                exp = (s.npv_incl + (me - 1) * s.pv_energy
                       + (mc - 1) * (s.pv_ets2_gross + s.pv_pt_gross))
                _close(self, s.grid[i][j], exp)

    def test_grid_off_centre_matches_full_recompute(self):
        for direct in ("Off", "On"):
            s = _s(direct=direct)
            ax = s.grid_axis
            for i, j in ((0, 0), (0, 4), (4, 0), (4, 4), (2, 4), (4, 2)):
                got = full_recompute_npv(INPUTS, MB, CE, direct,
                                         energy_mult=ax[i], carbon_mult=ax[j])
                _close(self, s.grid[i][j], got)

    def test_net_scaling_trap_differs(self):
        s = _s()
        wrong = s.npv_incl + 0.4 * s.pv_carbon
        right = full_recompute_npv(INPUTS, MB, CE, OFF, carbon_mult=1.4)
        self.assertGreater(abs(wrong - right), 1.0)
        _close(self, s.grid[2][4], right)


class RateTests(unittest.TestCase):
    def test_centre(self):
        s = _s()
        _close(self, s.rate_npvs[2], s.npv_incl)

    def test_each_rate_matches_recompute(self):
        s = _s()
        self.assertEqual(len(s.rate_axis), 5)
        for r, n in zip(s.rate_axis, s.rate_npvs):
            _close(self, n, full_recompute_npv(INPUTS, MB, CE, OFF, rate=r))


class TornadoTests(unittest.TestCase):
    def test_driver_order(self):
        s = _s()
        self.assertEqual(TORNADO_DRIVERS,
                         ("rate", "elec", "gas", "carbon_level", "capex",
                          "go", "ev", "ptr", "mef", "ets2_delay",
                          "ngfs_route"))
        self.assertEqual(tuple(r.driver_id for r in s.tornado),
                         TORNADO_DRIVERS)

    def _check(self, driver, low_kw, high_kw):
        s = _s()
        row = _row(s, driver)
        lk, hk = dict(low_kw), dict(high_kw)
        _close(self, row.npv_low, full_recompute_npv(
            INPUTS, MB, lk.pop("scenario", CE), OFF, **lk))
        _close(self, row.npv_high, full_recompute_npv(
            INPUTS, MB, hk.pop("scenario", CE), OFF, **hk))
        _close(self, row.swing, abs(row.npv_high - row.npv_low))

    def test_rate(self):
        s = _s()
        d = V["Sens_Torn_RateDelta"]
        self._check("rate", dict(rate=s.rate_axis[2] - d),
                    dict(rate=s.rate_axis[2] + d))

    def test_elec_gas(self):
        p = V["Sens_Torn_ElecPct"]
        self._check("elec", dict(elec_mult=1 - p), dict(elec_mult=1 + p))
        p = V["Sens_Torn_GasPct"]
        self._check("gas", dict(gas_mult=1 - p), dict(gas_mult=1 + p))

    def test_carbon_level(self):
        self._check("carbon_level", dict(scenario="Low"),
                    dict(scenario="High"))

    def test_capex(self):
        p = V["Sens_Torn_CapexPct"]
        self._check("capex", dict(capex_mult=1 - p), dict(capex_mult=1 + p))

    def test_go_ev(self):
        p = V["Sens_Torn_GOPct"]
        b = V["Meas_RC_GOPrice"]
        self._check("go", dict(overrides={"Meas_RC_GOPrice": b * (1 - p)}),
                    dict(overrides={"Meas_RC_GOPrice": b * (1 + p)}))
        p = V["Sens_Torn_EVPct"]
        b = V["Meas_Fleet_EVPremium"]
        self._check("ev", dict(overrides={"Meas_Fleet_EVPremium": b * (1 - p)}),
                    dict(overrides={"Meas_Fleet_EVPremium": b * (1 + p)}))

    def test_ptr_mef(self):
        self._check("ptr", dict(overrides={"Pass_PTR": V["Sens_Torn_PTRLow"]}),
                    dict())
        p = V["Sens_Torn_MEFPct"]
        e = V["Pass_CCGT_Eff"]
        self._check("mef", dict(overrides={"Pass_CCGT_Eff": e / (1 - p)}),
                    dict(overrides={"Pass_CCGT_Eff": e / (1 + p)}))

    def test_ets2_delay_ngfs_route(self):
        self._check("ets2_delay", dict(), dict(overrides={
            "Carbon_ETS2_StartYear": V["Carbon_ETS2_StartYear"]
            + V["Sens_ETS2_StartDelay"]}))
        from checkmodel.carbon_reference import eur_route_factor
        base = eur_route_factor(V, 2010)
        self._check("ngfs_route", dict(), dict(
            ngfs_scale=V["Carbon_NGFS_AltRouteFactor"] / base))

    def test_rank_descending_tie_break(self):
        s = _s()
        sw = [r.swing for r in s.tornado]
        for r in s.tornado:
            exp = (1 + sum(1 for x in sw if x > r.swing)
                   + sum(1 for x in sw[:s.tornado.index(r)] if x == r.swing))
            self.assertEqual(r.rank, exp)
        order = [x for x in s.tornado_order]
        swings = [_row(s, d).swing for d in order]
        self.assertEqual(swings, sorted(swings, reverse=True))
        self.assertEqual(sorted(r.rank for r in s.tornado), list(range(1, 12)))


class RankStabilityTests(unittest.TestCase):
    def test_default_all_same(self):
        s = _s()
        self.assertEqual(len(s.rank_stab), 6)
        for r in s.rank_stab:
            self.assertEqual(r.flag, "Same", r.key)
        order = [r.key for r in sorted(s.rank_stab, key=lambda r: r.rank_base)]
        self.assertEqual(order, ["VSD", "PV", "LED", "RC", "HP", "Fleet"])

    def test_lev_base_matches_phase3(self):
        from checkmodel.measures_reference import compute_measures
        ms = compute_measures(INPUTS, MB, CE)
        for r in _s().rank_stab:
            m = ms.by_key(r.key)
            if m.eligible:
                _close(self, r.lev_base, m.lev)

    def test_lev_at_rate_formula(self):
        from checkmodel.measures_reference import compute_measures
        ms = compute_measures(INPUTS, MB, CE)
        h = V["Sens_Hurdle_2"]
        for r in _s().rank_stab:
            m = ms.by_key(r.key)
            if m.eligible:
                exp = -npv0(h, m.cf_fin) / npv0(h, m.t_sel)
                _close(self, r.lev_r2, exp)
            else:
                self.assertEqual(r.lev_r2, "n/a")

    def test_flip_override_changes(self):
        s = _s(overrides=RANK_FLIP_OVERRIDE)
        self.assertIn("Changed", [r.flag for r in s.rank_stab])


class StateAndNoteTests(unittest.TestCase):
    def test_all_states(self):
        st = all_states()
        self.assertEqual(set(st), set(STATES))
        for s in st.values():
            _close(self, s.npv_incl, s.npv_fin + s.pv_carbon)

    def test_untested_notes(self):
        n = untested_note_values(INPUTS)
        self.assertEqual(set(n), {"led_life_low", "led_life_high",
                                  "vsd_life_low", "vsd_life_high",
                                  "hp_share_low", "hp_share_high"})
        self.assertTrue(all(isinstance(x, float) for x in n.values()))
        self.assertNotEqual(n["led_life_low"], n["led_life_high"])

    def test_no_xl_qa_import(self):
        with open(sr.__file__) as fh:
            src = fh.read()
        for line in src.splitlines():
            self.assertFalse(line.startswith(
                ("from xl", "import xl", "from qa", "import qa")))


if __name__ == "__main__":
    unittest.main()
