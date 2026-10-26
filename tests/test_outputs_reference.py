import unittest

from checkmodel import outputs_reference as o
from checkmodel.exposure_reference import STATES, compute_exposure
from checkmodel.macc_reference import _excel_round0
from checkmodel.measures_reference import compute_measures
from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.sensitivity_reference import compute_sensitivity
from config.inputs import INPUTS

DEFAULT = ("Market-based", "Central", "Off")
TOL = next(r.published_value for r in INPUTS if r.id == "Const_MACCRoundTol")


class OutputsReference(unittest.TestCase):
    def test_default_state_matches_modules(self):
        r = o.compute_outputs(INPUTS, *DEFAULT)
        m = compute_measures(INPUTS, DEFAULT[0], DEFAULT[1])
        e = compute_exposure(INPUTS, *DEFAULT)
        s = compute_sensitivity(INPUTS, *DEFAULT)
        b = compute_baseline(model_values(INPUTS))
        self.assertAlmostEqual(r.npv_fin, sum(x.npv for x in m.measures))
        self.assertAlmostEqual(r.npv_incl, s.npv_incl)
        self.assertAlmostEqual(r.abated_sel, sum(x.avg_t_mb for x in m.measures))
        self.assertEqual(r.macc_total,
                         sum(_excel_round0(w) for w in m.chart_widths))
        self.assertAlmostEqual(r.s12_sel, b.s12_mb_t)
        self.assertAlmostEqual(r.share, r.abated_sel / r.s12_sel)
        self.assertAlmostEqual(r.cum_bau_sel, e.scen["NDC"].cum["total_bau"])
        self.assertAlmostEqual(r.cum_avoided_sel, e.scen["NDC"].cum["avoided"])
        self.assertAlmostEqual(r.disc_bau_sel, e.scen["NDC"].disc["total_bau"])
        # documented orders of magnitude
        self.assertAlmostEqual(r.npv_fin, -72399, delta=1)
        self.assertAlmostEqual(r.npv_incl, 2519250, delta=1)
        self.assertEqual(r.macc_total, 3220)

    def test_location_based(self):
        st = ("Location-based", "Central", "Off")
        r = o.compute_outputs(INPUTS, *st)
        m = compute_measures(INPUTS, st[0], st[1])
        b = compute_baseline(model_values(INPUTS))
        self.assertAlmostEqual(r.abated_sel, sum(x.avg_t_lb for x in m.measures))
        self.assertAlmostEqual(r.s12_sel, b.s12_lb_t)

    def test_chart_block(self):
        st = ("Market-based", "Low", "Off")
        r = o.compute_outputs(INPUTS, *st)
        e = compute_exposure(INPUTS, *st)
        self.assertEqual(set(r.chart_block), {"Low", "Central", "High"})
        for tier, key in (("Low", "CP"), ("Central", "NDC"), ("High", "NZ50")):
            c = e.scen[key].cum
            self.assertAlmostEqual(r.chart_block[tier]["cum_bau"], c["total_bau"])
            self.assertAlmostEqual(r.chart_block[tier]["cum_with"], c["total_with"])
            self.assertAlmostEqual(r.chart_block[tier]["cum_avoided"], c["avoided"])
        self.assertLess(r.chart_block["Low"]["cum_bau"], 0)

    def test_all_twelve_states(self):
        res = o.all_states()
        self.assertEqual(set(res), set(STATES))
        self.assertEqual(len(res), 12)
        for st, r in res.items():
            self.assertTrue(all(r.checks.values()), (st, r.checks))
            self.assertEqual(r.chk_master, "OK")
            self.assertEqual(r.chk_fail_count, 0)
            self.assertLessEqual(abs(r.abated_sel - r.macc_total), 6 * TOL, st)

    def test_negative_abatement_reconciles(self):
        # CR-01: Meas_Fleet_EVkWhPerKm = 1.5 makes the fleet abate a negative
        # amount; the MACC leaves it out and the like-for-like check passes.
        ov = {"Meas_Fleet_EVkWhPerKm": 1.5}
        r = o.compute_outputs(INPUTS, *DEFAULT, overrides=ov)
        m = compute_measures(INPUTS, DEFAULT[0], DEFAULT[1], ov)
        fleet = m.by_key("Fleet")
        self.assertLess(fleet.avg_t_sel, 0)
        self.assertFalse(fleet.eligible)
        # the old all-measures comparison would have failed here
        self.assertGreater(abs(r.abated_sel - r.macc_total), 6 * TOL)
        self.assertTrue(r.checks["Dash_TileVsMACC"])
        self.assertEqual(r.chk_master, "OK")
        self.assertEqual(r.chk_fail_count, 0)

    def test_linked_value(self):
        r = o.compute_outputs(INPUTS, *DEFAULT)
        self.assertEqual(o.linked_value("Expo_CumBAU_Sel", DEFAULT), r.cum_bau_sel)
        self.assertEqual(o.linked_value("Sel_Basis", DEFAULT), "Market-based")
        with self.assertRaises(KeyError):
            o.linked_value("Nope", DEFAULT)

    def test_labels_all_states(self):
        for st, r in o.all_states().items():
            basis, scen, ets = st
            lb = r.labels
            self.assertEqual(lb["abated"], "Abated per year, %s basis" % basis)
            self.assertEqual(lb["share"],
                             "Share of Scope 1+2 abated, %s basis" % basis)
            self.assertEqual(lb["npv_incl"],
                             "Including carbon cash savings, %s scenario, %s "
                             "basis" % (scen, basis))
            self.assertEqual(lb["cost"], "Cost of not acting, %s scenario" % scen)
            self.assertEqual(lb["scen_chart"],
                             "Cost of not acting by scenario: BAU vs with "
                             "measures (%s basis, Direct ETS %s)" % (basis, ets))
            self.assertEqual(lb["selectors"], {
                "Sel_Scenario": scen, "Sel_Basis": basis, "Sel_DirectETS": ets})
        r = o.compute_outputs(INPUTS, "Market-based", "Central", "Off")
        self.assertEqual(r.labels["abated"],
                         "Abated per year, Market-based basis")

    def test_no_forbidden_imports(self):
        import re
        with open(o.__file__) as fh:
            src = fh.read()
        code = "\n".join(l for l in src.splitlines()
                         if not l.strip().startswith("#"))
        self.assertIsNone(re.search(r"^\s*(import|from)\s+(xl|qa)\b", code, re.M))


if __name__ == "__main__":
    unittest.main()
