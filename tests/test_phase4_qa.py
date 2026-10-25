"""QA (D-25): in all 12 states (2 bases x 3 scenarios x direct ETS Off/On)
every formula equals the independent reference and every check is TRUE."""
import dataclasses
import hashlib
import io
import unittest

import openpyxl

import build
from checkmodel.exposure_reference import STATES, compute_exposure
from checkmodel.measures_reference import DEFAULT_STATE
from checkmodel.sensitivity_reference import compute_sensitivity
from qa.formula_eval import compare_cached, evaluate_names

CHECKS = ["M_Check_All", "Expo_Check_All", "Sens_Check_All",
          "Carb_Check_ConvYears"]


class TwelveStateQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = build.load_dataset("config")

    def test_twelve_states(self):
        self.assertEqual(len(STATES), 12)

    def test_every_formula_equals_reference_in_each_state(self):
        for basis, scen, direct_ets in STATES:
            with self.subTest(state=(basis, scen, direct_ets)):
                ds = dataclasses.replace(
                    self.base, selector_state=(basis, scen),
                    direct_ets_state=direct_ets)
                data, _ = build.build_bytes("main", ds)
                bad, n = compare_cached(data)
                self.assertEqual(bad, [], (basis, scen, direct_ets, bad[:5]))
                self.assertGreater(n, 1000)
                ref = compute_exposure(ds.inputs, basis, scen, direct_ets)
                sens = compute_sensitivity(ds.inputs, basis, scen,
                                           direct_ets)
                keys = list(ref.scen)
                names = (CHECKS + ["Expo_DiscBAU_Sel", "Expo_DiscAvoided_Sel",
                                   "Sens_PortfolioNPV", "Expo_Avoided_RC"]
                         + ["Expo_PStat1_%s" % k for k in keys]
                         + ["Expo_PStat2_%s" % k for k in keys])
                out = evaluate_names(data, names)
                for c in CHECKS:
                    self.assertIs(out[c], True, c)
                sel = ref.scen[ref.sel_key]
                self.assertAlmostEqual(
                    out["Expo_DiscBAU_Sel"], sel.disc["total_bau"],
                    delta=1e-9 * max(1.0, abs(sel.disc["total_bau"])))
                self.assertAlmostEqual(
                    out["Expo_DiscAvoided_Sel"], sel.disc["avoided"],
                    delta=1e-9 * max(1.0, abs(sel.disc["avoided"])))
                self.assertAlmostEqual(
                    out["Sens_PortfolioNPV"], sens.npv_incl,
                    delta=1e-9 * max(1.0, abs(sens.npv_incl)))
                pre = "Expo_PStat2_" if direct_ets == "On" else "Expo_PStat1_"
                for k in keys:
                    self.assertTrue(all(x == 0 for x in out[pre + k]),
                                    (pre, k))
                self.assertTrue(all(x == 0 for x in out["Expo_Avoided_RC"]))
                if scen == "Low":
                    self.assertLess(sel.disc["pt_bau"], 0.0)

    def test_default_build_is_default_state_and_stable(self):
        self.assertEqual(build.selector_state(self.base), DEFAULT_STATE)
        self.assertEqual(build.direct_ets_state(self.base), "Off")
        d1, _ = build.build_bytes("main", self.base)
        d2, _ = build.build_bytes("main", dataclasses.replace(
            self.base, selector_state=DEFAULT_STATE, direct_ets_state="Off"))
        self.assertEqual(hashlib.sha256(d1).hexdigest(),
                         hashlib.sha256(d2).hexdigest())

    def test_sheet_order(self):
        data, _ = build.build_bytes("main", self.base)
        names = openpyxl.load_workbook(io.BytesIO(data)).sheetnames
        i = names.index
        self.assertLess(i("MACC"), i("Exposure"))
        self.assertLess(i("Exposure"), i("Sensitivity"))
        self.assertLess(i("Sensitivity"), i("Notes"))
        self.assertEqual(tuple(names), build.REAL_ORDER)


if __name__ == "__main__":
    unittest.main()
