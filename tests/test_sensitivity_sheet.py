"""Sensitivity sheet part 1 tests (plan 04-08)."""
import io
import unittest

import openpyxl

import build
from checkmodel.measures_reference import DEFAULT_DIRECT_ETS, DEFAULT_STATE
from checkmodel.sensitivity_reference import (compute_sensitivity,
                                              full_recompute_npv)
from qa.formula_eval import compare_cached, evaluate_names

CHECKS = ["Sens_Check_Reconcile", "Sens_Check_CarbonPV",
          "Sens_Check_GridCentre", "Sens_Check_RateCentre",
          "Sens_Check_All"]
REL = 1e-9


class SensitivitySheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ds = build.load_dataset("config")
        cls.ds = ds
        cls.data, _ = build.build_bytes("main", ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        cls.ref = compute_sensitivity(ds.inputs, DEFAULT_STATE[0],
                                      DEFAULT_STATE[1], DEFAULT_DIRECT_ETS)

    def _target(self, name):
        sheet, ref_ = self.wb.defined_names[name].attr_text.split("!")
        return sheet, ref_.replace("$", "")

    def _close(self, got, want, label):
        self.assertLessEqual(abs(got - want), REL * max(1.0, abs(want)),
                             label)

    def test_names_exist(self):
        for n in ("Sens_PortfolioNPV", "Sens_PortfolioNPV_Fin",
                  "Sens_PVCarbon", "Sens_PV_ETS2Gross", "Sens_PV_PTGross",
                  "Sens_PV_PTEmbedded", "Sens_Grid", "Sens_GridCentre",
                  "Sens_Rate_3", "Sens_RateNPV_3", "Sens_PortfolioCF"):
            self.assertIn(n, self.wb.defined_names)

    def test_values_match_reference(self):
        r = self.ref
        names = ["Sens_PortfolioNPV", "Sens_PortfolioNPV_Fin",
                 "Sens_PVCarbon", "Sens_PV_Elec", "Sens_PV_Gas",
                 "Sens_PV_Diesel", "Sens_PV_Energy", "Sens_PV_GO",
                 "Sens_PV_ETS2Gross", "Sens_PV_PTGross",
                 "Sens_PV_PTEmbedded", "Sens_PV_PTNet"]
        out = evaluate_names(self.data, names)
        for n, want in zip(names, (
                r.npv_incl, r.npv_fin, r.pv_carbon, r.pv_elec, r.pv_gas,
                r.pv_diesel, r.pv_energy, r.pv_go, r.pv_ets2_gross,
                r.pv_pt_gross, r.pv_pt_embedded, r.pv_pt_net)):
            self._close(out[n], want, n)
        rate = evaluate_names(self.data, ["Sens_RateNPV_%d" % i
                                          for i in range(1, 6)])
        for i, want in enumerate(r.rate_npvs):
            self._close(rate["Sens_RateNPV_%d" % (i + 1)], want, "rate")

    def test_compare_cached_no_mismatch(self):
        bad, n = compare_cached(self.data)
        self.assertEqual(bad, [], bad[:5])
        self.assertGreater(n, 0)

    def test_grid_matches_reference(self):
        out = evaluate_names(self.data, ["Sens_Grid"])["Sens_Grid"]
        for i in range(5):
            for j in range(5):
                self._close(out[i * 5 + j], self.ref.grid[i][j], (i, j))

    def test_grid_corners_match_full_recompute(self):
        out = evaluate_names(self.data, ["Sens_Grid"])["Sens_Grid"]
        ax = self.ref.grid_axis
        for i, j in ((0, 0), (0, 4), (4, 0), (4, 4), (2, 4)):
            want = full_recompute_npv(
                self.ds.inputs, DEFAULT_STATE[0], DEFAULT_STATE[1],
                DEFAULT_DIRECT_ETS, energy_mult=ax[i], carbon_mult=ax[j])
            self.assertLessEqual(abs(out[i * 5 + j] - want),
                                 1e-6 * max(1.0, abs(want)), (i, j))

    def test_centres_equal_base(self):
        out = evaluate_names(self.data, ["Sens_GridCentre",
                                         "Sens_PortfolioNPV",
                                         "Sens_RateNPV_3"])
        self._close(out["Sens_GridCentre"], out["Sens_PortfolioNPV"], "grid")
        self._close(out["Sens_RateNPV_3"], out["Sens_PortfolioNPV"], "rate")

    def test_checks_true_in_states(self):
        for ov in (None, {self._target("Sel_Scenario"): "Low"},
                   {self._target("Sel_DirectETS"): "On"}):
            out = evaluate_names(self.data, CHECKS, overrides=ov)
            for n in CHECKS:
                self.assertIs(out[n], True, (n, ov))

    def test_notes_present(self):
        txt = " ".join(c.value for row in self.wb["Sensitivity"].iter_rows()
                       for c in row if isinstance(c.value, str)
                       and not c.value.startswith("="))
        self.assertIn("must not be scaled", txt)
        self.assertIn("leaves carbon out on purpose", txt)


if __name__ == "__main__":
    unittest.main()
