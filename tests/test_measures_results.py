"""Measures results tests (plan 03-08): NPV, IRR, payback, abatement cost,
checks and the summary band, against the reference model in all six selector
states."""
import io
import unittest

import openpyxl

import build
from checkmodel import appraisal as ap
from checkmodel.measures_reference import BASES, SCENARIOS_UI, compute_measures
from config.inputs import INPUTS
from config.measures_catalog import MEASURES
from qa.formula_eval import evaluate_names

KEYS = [m.key for m in MEASURES]
REL = 1e-9


def _same(got, want):
    if isinstance(want, str) or isinstance(got, str):
        return (got or "") == (want or "")
    return abs(got - want) <= REL * max(1.0, abs(want))


class MeasuresResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ds = build.load_dataset("config")
        cls.data, cls.registry = build.build_bytes("main", ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        cls.wbv = openpyxl.load_workbook(io.BytesIO(cls.data), data_only=True)
        cls.ref = compute_measures(INPUTS, "Market-based", "Central")

    def _addr(self, name):
        sheet, a = self.wb.defined_names[name].attr_text.split("!")
        return sheet, a.replace("$", "")

    def _cached(self, name):
        sheet, a = self._addr(name)
        return self.wbv[sheet][a].value

    def _formula(self, name):
        sheet, a = self._addr(name)
        return self.wb[sheet][a].value

    @staticmethod
    def _want(m):
        return {
            "NPV": m.npv, "NPVMemo": m.npv_memo, "NPVPreSub": m.npv_pre_sub,
            "NPVCarbon": m.npv_incl_carbon, "IRR": m.irr,
            "IRRFlag": m.multi_flag, "PaySimple": m.pay_simple,
            "PayDisc": m.pay_disc, "PVtLB": m.pv_t_lb, "PVtMB": m.pv_t_mb,
            "PVtSel": m.pv_t_sel, "AvgtLB": m.avg_t_lb, "AvgtMB": m.avg_t_mb,
            "AvgtSel": m.avg_t_sel, "LevCost": m.lev,
            "BreakEven": m.break_even, "Eligible": 1 if m.eligible else 0,
            "NPVFullCapex": ("n/a (no counterfactual purchase)"
                             if m.npv_full_capex is None
                             else m.npv_full_capex),
        }

    def test_cached_equal_reference(self):
        for m in self.ref.measures:
            for item, want in self._want(m).items():
                name = "M_%s_%s" % (m.key, item)
                with self.subTest(name=name):
                    self.assertTrue(_same(self._cached(name), want),
                                    (name, self._cached(name), want))

    def test_all_checks_true(self):
        names = [n for n in self.wb.defined_names if n.startswith("M_Check_")]
        self.assertGreaterEqual(len(names), 37)
        for n in names:
            with self.subTest(name=n):
                self.assertIs(self._cached(n), True)
        for key in KEYS:
            for suffix in ("NPVMemo", "BreakEven", "Annuity", "NPVatZero",
                           "NPVatIRR"):
                self.assertIn("M_Check_%s_%s" % (key, suffix), names)

    def test_formula_text(self):
        for key in KEYS:
            npv = self._formula("M_%s_NPV" % key)
            self.assertTrue(npv.startswith("=SUMPRODUCT("), npv)
            self.assertIn(",M_DF)", npv)
            memo = self._formula("M_%s_NPVMemo" % key)
            self.assertIn("+NPV(Rate_DiscountReal,$O$", memo)
            irr = self._formula("M_%s_IRR" % key)
            self.assertIn("IFERROR(IRR(", irr)
            for txt in (ap.NA_NO_OUTLAY, ap.NA_NEVER_PAYS, ap.NA_NO_SOLUTION):
                self.assertIn(txt, irr)
            lev = self._formula("M_%s_LevCost" % key)
            self.assertIn(ap.NA_NO_ABATEMENT, lev)

    def test_multiple_sign_flag_and_hp_memo(self):
        self.assertEqual(self.ref.by_key("LED").multi_flag, ap.MULTI_SIGN)
        self.assertIsInstance(self._cached("M_HP_NPVFullCapex"), float)
        self.assertIsInstance(self._cached("M_Fleet_NPVFullCapex"), float)

    def test_summary_and_portfolio(self):
        self.assertIs(self._cached("M_Check_All"), True)
        self.assertTrue(_same(self._cached("M_Portfolio_NPV"),
                              sum(m.npv for m in self.ref.measures)))
        self.assertTrue(_same(self._cached("M_Total_tLB"),
                              sum(m.avg_t_lb for m in self.ref.measures)))
        self.assertTrue(_same(self._cached("M_Total_tMB"),
                              sum(m.avg_t_mb for m in self.ref.measures)))
        self.assertIn("M_Check_LED_Annuity", self._formula("M_Check_All"))

    def test_six_selector_states(self):
        items = ("LevCost", "BreakEven", "NPV", "NPVCarbon", "AvgtSel", "IRR",
                 "PaySimple", "PayDisc", "Eligible")
        names = ["M_%s_%s" % (k, i) for k in KEYS for i in items]
        names += ["M_Check_All"]
        for basis in BASES:
            for scen in SCENARIOS_UI:
                ref = compute_measures(INPUTS, basis, scen)
                out = evaluate_names(self.data, names, overrides={
                    ("Inputs", "G8"): scen, ("Inputs", "G9"): basis})
                self.assertIs(out["M_Check_All"], True, (basis, scen))
                for m in ref.measures:
                    want = self._want(m)
                    for i in items:
                        n = "M_%s_%s" % (m.key, i)
                        with self.subTest(state=(basis, scen), name=n):
                            self.assertTrue(_same(out[n], want[i]),
                                            (n, out[n], want[i]))
        lb = evaluate_names(self.data, ["M_RC_LevCost"], overrides={
            ("Inputs", "G9"): "Location-based"})
        self.assertEqual(lb["M_RC_LevCost"], ap.NA_NO_ABATEMENT)
        mb = evaluate_names(self.data, ["M_RC_LevCost"], overrides={
            ("Inputs", "G9"): "Market-based"})
        self.assertGreater(mb["M_RC_LevCost"], 0)

    def test_subsidy_override(self):
        sheet, addr = self._addr("Meas_PV_Subsidy")
        out = evaluate_names(
            self.data, ["M_PV_NPV", "M_PV_NPVPreSub", "M_PV_Capex"],
            overrides={(sheet, addr): 0.3})
        self.assertAlmostEqual(
            out["M_PV_NPV"] - out["M_PV_NPVPreSub"], 0.3 * out["M_PV_Capex"],
            delta=1e-6 * abs(out["M_PV_Capex"]))

    def test_scenario_moves_carbon_lens_only(self):
        names = ["M_PV_NPV", "M_PV_LevCost", "M_PV_NPVCarbon"]
        lo = evaluate_names(self.data, names,
                            overrides={("Inputs", "G8"): "Low"})
        hi = evaluate_names(self.data, names,
                            overrides={("Inputs", "G8"): "High"})
        self.assertEqual(lo["M_PV_NPV"], hi["M_PV_NPV"])
        self.assertEqual(lo["M_PV_LevCost"], hi["M_PV_LevCost"])
        self.assertNotEqual(lo["M_PV_NPVCarbon"], hi["M_PV_NPVCarbon"])


if __name__ == "__main__":
    unittest.main()
