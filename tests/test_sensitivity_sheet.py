"""Sensitivity sheet part 1 tests (plan 04-08)."""
import io
import unittest

import openpyxl

import build
from checkmodel.measures_reference import DEFAULT_DIRECT_ETS, DEFAULT_STATE
from checkmodel.sensitivity_reference import (RANK_FLIP_OVERRIDE,
                                              TORNADO_DRIVERS,
                                              compute_sensitivity,
                                              full_recompute_npv)
from qa.formula_eval import compare_cached, evaluate_names

CHECKS = ["Sens_Check_Reconcile", "Sens_Check_CarbonPV",
          "Sens_Check_GridCentre", "Sens_Check_RateCentre",
          "Sens_Check_Torn", "Sens_Check_LevBase", "Sens_Check_All"]
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
                   {self._target("Sel_DirectETS"): "On"},
                   {self._target("Sel_Basis"): "Location-based"}):
            out = evaluate_names(self.data, CHECKS, overrides=ov)
            for n in CHECKS:
                self.assertIs(out[n], True, (n, ov))

    def test_notes_present(self):
        txt = " ".join(c.value for row in self.wb["Sensitivity"].iter_rows()
                       for c in row if isinstance(c.value, str)
                       and not c.value.startswith("="))
        self.assertIn("must not be scaled", txt)
        self.assertIn("leaves carbon out on purpose", txt)


class TornadoAndRankStability(SensitivitySheet):
    """Plan 04-09: tornado table, sort, chart inputs and rank stability."""

    def _table(self, ov=None):
        ws = self.wb["Sensitivity"]
        first = None
        for row in ws.iter_rows(min_col=2, max_col=2):
            if row[0].value == "Driver" and first is None:
                first = row[0].row + 1
        out = evaluate_names(
            self.data, ["Sens_Torn_Ranks", "Sens_TornDown", "Sens_TornUp"],
            overrides=ov)
        return first, out

    def _cells(self, col, n=11):
        ws = self.wb["Sensitivity"]
        first, _ = self._table()
        return first, [ws["%s%d" % (col, first + i)].value for i in range(n)]

    def test_tornado_matches_reference(self):
        # evaluate every table cell through the formula evaluator
        from qa.formula_eval import FormulaEvaluator
        ev = FormulaEvaluator(self.wb, None)
        first, _ = self._cells("B")
        for i, t in enumerate(self.ref.tornado):
            r = first + i
            self._close(ev.value("Sensitivity", "G%d" % r), t.npv_low,
                        t.driver_id + " low")
            self._close(ev.value("Sensitivity", "H%d" % r), t.npv_high,
                        t.driver_id + " high")
            self._close(ev.value("Sensitivity", "I%d" % r), t.swing,
                        t.driver_id + " swing")
            self.assertEqual(ev.value("Sensitivity", "J%d" % r), t.rank)

    def test_sorted_order_and_values(self):
        _, out = self._table()
        order = sorted(self.ref.tornado, key=lambda x: x.rank)
        base = self.ref.npv_incl
        for i, t in enumerate(order):
            self._close(out["Sens_TornDown"][i],
                        min(t.npv_low, t.npv_high) - base, "down")
            self._close(out["Sens_TornUp"][i],
                        max(t.npv_low, t.npv_high) - base, "up")
        sw = [t.swing for t in order]
        self.assertEqual(sw, sorted(sw, reverse=True))

    def test_workbook_npvs_equal_full_recompute(self):
        from qa.formula_eval import FormulaEvaluator
        ev = FormulaEvaluator(self.wb, None)
        first, _ = self._cells("B")
        idx = {d: first + i for i, d in enumerate(TORNADO_DRIVERS)}
        a = (self.ds.inputs, DEFAULT_STATE[0], DEFAULT_STATE[1],
             DEFAULT_DIRECT_ETS)
        v = {t.driver_id: t for t in self.ref.tornado}
        cases = [
            ("capex", "G", dict(capex_mult=1.0 - 0.2)),
            ("capex", "H", dict(capex_mult=1.0 + 0.2)),
            ("ptr", "G", dict(overrides={"Pass_PTR": v["ptr"].low_input})),
            ("ets2_delay", "H", dict(overrides={
                "Carbon_ETS2_StartYear": v["ets2_delay"].high_input})),
            ("ngfs_route", "H", dict(ngfs_scale=v["ngfs_route"].high_input)),
        ]
        for did, col, kw in cases:
            got = ev.value("Sensitivity", "%s%d" % (col, idx[did]))
            want = full_recompute_npv(*a, **kw)
            self.assertLessEqual(abs(got - want), 1e-6 * max(1.0, abs(want)),
                                 (did, col, got, want))

    def test_chart_xml(self):
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(self.data))
        xmls = [z.read(n).decode("utf-8") for n in z.namelist()
                if n.startswith("xl/charts/chart")]
        hit = [x for x in xmls if '<c:barDir val="bar"/>' in x]
        self.assertEqual(len(hit), 1)
        x = hit[0]
        self.assertIn('<c:overlap val="100"/>', x)
        self.assertIn('<c:orientation val="maxMin"/>', x)
        self.assertNotIn("<c:max ", x)
        self.assertNotIn("<c:min ", x)
        self.assertNotIn("<c:dateAx>", x)

    def test_not_tested_note(self):
        txt = " ".join(c.value for row in self.wb["Sensitivity"].iter_rows()
                       for c in row if isinstance(c.value, str))
        self.assertIn("Not tested in-sheet", txt)

    def _flags(self, ov=None):
        out = evaluate_names(self.data, ["Sens_RankStab_Flags",
                                         "Sens_RankStab_AnyChanged"],
                             overrides=ov)
        return out

    def test_rank_stab_default_unchanged(self):
        out = self._flags()
        self.assertEqual(out["Sens_RankStab_AnyChanged"], 0)
        self.assertTrue(all(f == "Same" for f in out["Sens_RankStab_Flags"]))
        want = ["Same" if (r.rank_r1 == r.rank_base) else "Changed"
                for r in self.ref.rank_stab]
        self.assertEqual(want, ["Same"] * len(want))

    def test_rank_flip_override_shows_changed(self):
        (name, val), = RANK_FLIP_OVERRIDE.items()
        ov = {self._target(name): val}
        out = self._flags(ov)
        self.assertGreaterEqual(out["Sens_RankStab_AnyChanged"], 1)
        ref = compute_sensitivity(
            self.ds.inputs, DEFAULT_STATE[0], DEFAULT_STATE[1],
            DEFAULT_DIRECT_ETS, overrides=RANK_FLIP_OVERRIDE)
        want = []
        for r in ref.rank_stab:
            want += ["Same" if x == r.rank_base else "Changed"
                     for x in (r.rank_r1, r.rank_r2, r.rank_r3)]
        self.assertEqual(out["Sens_RankStab_Flags"], want)
        chk = evaluate_names(self.data, ["Sens_Check_All"], overrides=ov)
        self.assertIs(chk["Sens_Check_All"], True)

    def test_location_based_contract_ranked_last(self):
        ov = {self._target("Sel_Basis"): "Location-based"}
        out = evaluate_names(self.data, ["Sens_RankStab_Flags",
                                         "Sens_Check_All"], overrides=ov)
        self.assertIs(out["Sens_Check_All"], True)
        ws = self.wb["Sensitivity"]
        from qa.formula_eval import FormulaEvaluator
        ev = FormulaEvaluator(self.wb, ov)
        row = [c.row for c in ws["B"] if c.value == "Measure"][-1] + 1
        n = len(self.ref.rank_stab)
        rc = row + n - 1
        for col in "IJKL":
            self.assertEqual(ev.value("Sensitivity", "%s%d" % (col, rc)), n)


if __name__ == "__main__":
    unittest.main()
