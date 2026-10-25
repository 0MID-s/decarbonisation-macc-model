"""Exposure sheet part 1 tests (plan 04-05): channel rows vs the reference."""
import io
import unittest

import openpyxl

import build
from checkmodel.exposure_reference import compute_exposure
from checkmodel.measures_reference import DEFAULT_DIRECT_ETS, DEFAULT_STATE
from qa.formula_eval import compare_cached, evaluate_names
from xl.layout import TIMELINE_FIRST_COL, TIMELINE_LAST_COL

KEYS = ("CP", "NDC", "NZ50")
MKEYS = ("LED", "VSD", "HP", "Fleet", "PV", "RC")
REL = 1e-9


class ExposureSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ds = build.load_dataset("config")
        cls.ds = ds
        cls.data, _ = build.build_bytes("main", ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        cls.wbv = openpyxl.load_workbook(io.BytesIO(cls.data), data_only=True)
        cls.ref = compute_exposure(ds.inputs, DEFAULT_STATE[0],
                                   DEFAULT_STATE[1], DEFAULT_DIRECT_ETS)

    def _row(self, wb, name):
        sheet, addr = self.wb.defined_names[name].attr_text.split("!")
        r = wb[sheet][addr.replace("$", "").split(":")[0]].row
        return [wb[sheet].cell(row=r, column=c + 1).value
                for c in range(TIMELINE_FIRST_COL, TIMELINE_LAST_COL + 1)]

    def _close(self, name, want):
        got = self._row(self.wbv, name)
        self.assertEqual(len(got), len(want), name)
        for g, x in zip(got, want):
            self.assertLessEqual(abs(g - x), REL * max(1.0, abs(x)), name)

    def test_names_and_cached_values(self):
        r = self.ref
        self._close("Expo_BAU_tStat", r.t_stat_bau)
        self._close("Expo_With_tStat", r.t_stat_with)
        self._close("Expo_With_tFleet", r.t_fleet_with)
        self._close("Expo_With_ElecMWh", r.elec_with)
        for key in KEYS:
            s = r.scen[key]
            self._close("Expo_PETS1_" + key, s.ets1)
            self._close("Expo_PETS2_" + key, s.ets2)
            self._close("Expo_PStat1_" + key, s.p_stat1)
            self._close("Expo_PStat2_" + key, s.p_stat2)
            for case, parts in (("BAU", (s.bau_ets2, s.bau_dir, s.bau_pt,
                                         s.bau_total)),
                                ("With", (s.with_ets2, s.with_dir, s.with_pt,
                                          s.with_total))):
                for nm, vals in zip(("ETS2", "DirETS", "PT", "Total"), parts):
                    self._close("Expo_%s_%s_%s" % (case, nm, key), vals)
            self._close("Expo_Avoided_" + key, s.avoided)

    def test_compare_cached_no_mismatch(self):
        bad, n = compare_cached(self.data)
        self.assertEqual(bad, [], bad[:5])
        self.assertGreater(n, 0)

    def test_ets2_zero_before_start(self):
        for key in KEYS:
            for case in ("BAU", "With"):
                vals = self._row(self.wbv, "Expo_%s_ETS2_%s" % (case, key))
                self.assertEqual(vals[0], 0)
                self.assertEqual(vals[1], 0)
            self.assertEqual(self._row(self.wbv, "Expo_PETS2_" + key)[:2],
                             [0, 0])

    def test_toggle_on(self):
        sheet, ref_ = self.wb.defined_names["Sel_DirectETS"].attr_text.split("!")
        names = ["Expo_PStat2_NDC", "Expo_PStat1_NDC", "Path_ETS1_NDC",
                 "Expo_BAU_Total_NDC", "Expo_With_Total_NDC",
                 "Expo_BAU_ETS2_NDC", "Expo_BAU_DirETS_NDC"]
        out = evaluate_names(self.data, names,
                             overrides={(sheet, ref_): "On"})
        self.assertTrue(all(x == 0 for x in out["Expo_PStat2_NDC"]))
        for g, w in zip(out["Expo_PStat1_NDC"], out["Path_ETS1_NDC"]):
            self.assertAlmostEqual(g, w, delta=1e-9)  # free allocation 0
        on = compute_exposure(self.ds.inputs, DEFAULT_STATE[0],
                              DEFAULT_STATE[1], "On").scen["NDC"]
        for nm, want in (("Expo_BAU_Total_NDC", on.bau_total),
                         ("Expo_With_Total_NDC", on.with_total),
                         ("Expo_BAU_DirETS_NDC", on.bau_dir)):
            for g, x in zip(out[nm], want):
                self.assertLessEqual(abs(g - x), REL * max(1.0, abs(x)), nm)
        # ETS2 on fleet diesel remains, stationary part is gone
        for g, x in zip(out["Expo_BAU_ETS2_NDC"], on.bau_ets2):
            self.assertLessEqual(abs(g - x), REL * max(1.0, abs(x)))

    def _target(self, name):
        sheet, ref_ = self.wb.defined_names[name].attr_text.split("!")
        return sheet, ref_.replace("$", "")

    def test_headlines_match_reference(self):
        out = evaluate_names(self.data, [
            "Expo_CumBAU_Sel", "Expo_CumWith_Sel", "Expo_DiscBAU_Sel",
            "Expo_DiscWith_Sel", "Expo_DiscAvoided_Sel",
            "Expo_DiscAvoided_CP", "Expo_CumAvoided_NZ50"])
        sel = self.ref.scen[self.ref.sel_key]
        for nm, want in (("Expo_CumBAU_Sel", sel.cum["total_bau"]),
                         ("Expo_CumWith_Sel", sel.cum["total_with"]),
                         ("Expo_DiscBAU_Sel", sel.disc["total_bau"]),
                         ("Expo_DiscWith_Sel", sel.disc["total_with"]),
                         ("Expo_DiscAvoided_Sel", sel.disc["avoided"]),
                         ("Expo_DiscAvoided_CP",
                          self.ref.scen["CP"].disc["avoided"]),
                         ("Expo_CumAvoided_NZ50",
                          self.ref.scen["NZ50"].cum["avoided"])):
            self.assertLessEqual(abs(out[nm] - want),
                                 REL * max(1.0, abs(want)), nm)

    def test_choose_follows_scenario_override(self):
        for tier, key in (("Low", "CP"), ("High", "NZ50")):
            out = evaluate_names(
                self.data, ["Expo_DiscBAU_Sel", "Expo_DiscBAU_" + key],
                overrides={self._target("Sel_Scenario"): tier})
            self.assertAlmostEqual(out["Expo_DiscBAU_Sel"],
                                   out["Expo_DiscBAU_" + key], delta=1e-6)

    def test_icp_values_and_toggle_independence(self):
        names = ["Expo_ICP_DiscBAU", "Expo_ICP_DiscWith",
                 "Expo_ICP_DiscAvoided"]
        base = evaluate_names(self.data, names)
        self.assertAlmostEqual(base["Expo_ICP_DiscBAU"],
                               self.ref.icp_disc_bau, delta=1e-6)
        self.assertAlmostEqual(base["Expo_ICP_DiscAvoided"],
                               self.ref.icp_disc_avoided, delta=1e-6)
        on = evaluate_names(self.data, names, overrides={
            self._target("Sel_DirectETS"): "On"})
        for n in names:
            self.assertAlmostEqual(base[n], on[n], delta=1e-9)

    def test_icp_follows_edited_grid_factor_change(self):
        """WR-01: the ICP lens must use the per-year factor, so editing the
        grid-factor change inputs moves the sheet and the reference alike."""
        chg = {"EF_GridLB_Change": -0.02, "EF_ResidualMB_Change": -0.03}
        names = ["Expo_ICP_DiscBAU", "Expo_ICP_DiscWith"]
        ov = {self._target(k): x for k, x in chg.items()}
        out = evaluate_names(self.data, names, overrides=ov)
        ref = compute_exposure(self.ds.inputs, DEFAULT_STATE[0],
                               DEFAULT_STATE[1], DEFAULT_DIRECT_ETS,
                               overrides=chg)
        self.assertAlmostEqual(out["Expo_ICP_DiscBAU"], ref.icp_disc_bau,
                               delta=1e-6)
        self.assertAlmostEqual(out["Expo_ICP_DiscWith"], ref.icp_disc_with,
                               delta=1e-6)
        self.assertNotAlmostEqual(ref.icp_disc_bau, self.ref.icp_disc_bau,
                                  delta=1.0)

    def test_direct_ets_branch_moves_stationary_price(self):
        """WR-04: fails if the Off/On branch of the stationary price rows is
        edited (the in-sheet exclusivity check cannot catch that)."""
        names = ["Expo_PStat1_NDC", "Expo_PStat2_NDC", "Expo_PETS1_NDC",
                 "Expo_PETS2_NDC", "Expo_PreStart"]
        off = evaluate_names(self.data, names)
        on = evaluate_names(self.data, names, overrides={
            self._target("Sel_DirectETS"): "On"})
        self.assertTrue(all(x == 0 for x in off["Expo_PStat1_NDC"]))
        self.assertTrue(all(x == 0 for x in on["Expo_PStat2_NDC"]))
        self.assertEqual(off["Expo_PStat2_NDC"], off["Expo_PETS2_NDC"])
        self.assertEqual(on["Expo_PStat1_NDC"], on["Expo_PETS1_NDC"])
        self.assertTrue(any(x > 0 for x in off["Expo_PStat2_NDC"]))
        self.assertTrue(any(x > 0 for x in on["Expo_PStat1_NDC"]))

    def test_icp_independent_of_scenario(self):
        """WR-04: the internal carbon price lens does not move with the
        scenario selector (it is a lens, not a cash channel)."""
        names = ["Expo_ICP_DiscBAU", "Expo_ICP_DiscWith"]
        base = evaluate_names(self.data, names)
        hi = evaluate_names(self.data, names, overrides={
            self._target("Sel_Scenario"): "High"})
        for n in names:
            self.assertAlmostEqual(base[n], hi[n], delta=1e-9)

    def test_checks_true_default_and_on(self):
        names = ["Expo_Check_All", "Expo_Check_ETS2ZeroBeforeStart",
                 "Expo_Check_ETSExclusive", "Expo_Check_CashIsChannels",
                 "Expo_Check_ConvYears"]
        for ov in (None, {self._target("Sel_DirectETS"): "On"}):
            out = evaluate_names(self.data, names, overrides=ov)
            for n in names:
                self.assertIs(out[n], True, (n, ov))

    def test_toggle_cbam_text_present(self):
        txt = " ".join(c.value for row in self.wb["Exposure"].iter_rows()
                       for c in row if isinstance(c.value, str)
                       and not c.value.startswith("="))
        self.assertIn("Management lens: not a cash cost", txt)
        self.assertIn("20 MW rated thermal input", txt)
        self.assertIn("as of 2026-10-25", txt)

    def test_notes_present(self):
        txt = " ".join(c.value for row in self.wb["Exposure"].iter_rows()
                       for c in row if isinstance(c.value, str)
                       and not c.value.startswith("="))
        self.assertIn("is negative", txt)
        self.assertIn("Never added to the internal carbon price", txt)

    # ---- plan 04-07: per-measure attribution and bridge ------------------
    def test_measure_avoided_match_reference(self):
        for k in MKEYS:
            self._close("Expo_Avoided_" + k, self.ref.measure_avoided[k])
        out = evaluate_names(self.data, ["Expo_DiscAvoided_" + k
                                         for k in MKEYS])
        for k in MKEYS:
            want = self.ref.measure_disc_avoided[k]
            self.assertLessEqual(abs(out["Expo_DiscAvoided_" + k] - want),
                                 REL * max(1.0, abs(want)), k)
        self.assertEqual(self._row(self.wbv, "Expo_Avoided_RC"), [0] * 30)

    def test_bridge_checks_states(self):
        names = ["Expo_Check_BridgeSums", "Expo_Check_ContractZero",
                 "Expo_Check_MeasuresReconcile", "Expo_Check_All"]
        for ov in (None, {self._target("Sel_Scenario"): "Low"},
                   {self._target("Sel_DirectETS"): "On"}):
            out = evaluate_names(self.data, names, overrides=ov)
            for n in names:
                self.assertIs(out[n], True, (n, ov))

    def _bridge(self, ov=None):
        names = ["Expo_Br_Start", "Expo_Br_End", "Expo_Br_BasePos",
                 "Expo_Br_BaseNeg", "Expo_Br_TotalPos", "Expo_Br_TotalNeg",
                 "Expo_Br_SavePos", "Expo_Br_SaveNeg", "Expo_Br_IncPos",
                 "Expo_Br_IncNeg", "Expo_Br_Value"]
        return evaluate_names(self.data, names, overrides=ov)

    def _check_bridge(self, out):
        n = len(out["Expo_Br_Start"])
        self.assertEqual(n, 8)
        for i in range(n):
            a, b = out["Expo_Br_Start"][i], out["Expo_Br_End"][i]
            pos = (out["Expo_Br_TotalPos"][i] + out["Expo_Br_SavePos"][i]
                   + out["Expo_Br_IncPos"][i])
            neg = (out["Expo_Br_TotalNeg"][i] + out["Expo_Br_SaveNeg"][i]
                   + out["Expo_Br_IncNeg"][i])
            bp, bn = out["Expo_Br_BasePos"][i], out["Expo_Br_BaseNeg"][i]
            # visible extent above and below zero reproduces [min, max]
            self.assertAlmostEqual(bp + pos, max(0.0, a, b), delta=1e-9)
            self.assertAlmostEqual(bn + neg, min(0.0, a, b), delta=1e-9)
            self.assertAlmostEqual(pos - neg, abs(b - a), delta=1e-9)
            self.assertGreaterEqual(pos, -1e-12)
            self.assertLessEqual(neg, 1e-12)
        return n

    def test_bridge_default_matches_reference(self):
        out = self._bridge()
        self._check_bridge(out)
        for i, (_lab, a, b) in enumerate(self.ref.bridge):
            self.assertAlmostEqual(out["Expo_Br_End"][i],
                                   b * 0.001, delta=1e-9 * max(1, abs(b)))
        self.assertEqual(out["Expo_Br_Start"][0], 0)
        self.assertEqual(out["Expo_Br_Start"][7], 0)
        self.assertAlmostEqual(out["Expo_Br_End"][6],
                               out["Expo_Br_Start"][6], delta=1e-12)
        self.assertAlmostEqual(out["Expo_Br_End"][6], out["Expo_Br_End"][7],
                               delta=1e-6)

    def test_bridge_low_zero_crossing(self):
        out = self._bridge({self._target("Sel_Scenario"): "Low"})
        self._check_bridge(out)
        ends = out["Expo_Br_End"]
        starts = out["Expo_Br_Start"]
        crossing = any(min(a, b) < 0 < max(a, b)
                       for a, b in zip(starts, ends))
        negative = any(max(a, b) < 0 for a, b in zip(starts, ends))
        self.assertTrue(crossing or negative)

    def test_bridge_title_and_notes(self):
        out = evaluate_names(self.data, ["Expo_BridgeTitle"])
        self.assertIn("Central scenario", out["Expo_BridgeTitle"])
        self.assertIn("Market-based basis", out["Expo_BridgeTitle"])
        self.assertIn("direct ETS1 Off", out["Expo_BridgeTitle"])
        txt = " ".join(c.value for row in self.wb["Exposure"].iter_rows()
                       for c in row if isinstance(c.value, str)
                       and not c.value.startswith("="))
        self.assertIn("Contract: zero cash saving", txt)
        self.assertIn("the bar is the net", txt)


if __name__ == "__main__":
    unittest.main()
