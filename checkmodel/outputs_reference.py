"""Reference values for the Dashboard and Checks sheets (plan 05-02).

Stdlib + config + checkmodel only. Never imports xl or qa. Delegates every
number to the existing independent reference modules (measures, exposure,
sensitivity, baseline, macc); no economics are recomputed here.

Scenario keys follow the Exposure column order D, E, F:
Low = CP (Current Policies), Central = NDC, High = NZ50 (Net Zero 2050).
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple

from checkmodel import appraisal as ap
from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.carbon_reference import carbon_paths
from checkmodel.exposure_reference import STATES, compute_exposure
from checkmodel.macc_reference import _excel_round0
from checkmodel.measures_reference import (BASES, ONOFF, SCENARIOS_UI,
                                           compute_measures)
from checkmodel.sensitivity_reference import compute_sensitivity
from config.inputs import INPUTS

_SCEN_KEYS = (("Low", "CP"), ("Central", "NDC"), ("High", "NZ50"))
_TOL_ID = "Const_MACCRoundTol"


@dataclass(frozen=True)
class OutputsResult:
    npv_fin: float
    npv_incl: float
    abated_sel: float
    macc_total: int
    s12_sel: float
    share: float
    cum_bau_sel: float
    cum_with_sel: float
    cum_avoided_sel: float
    disc_bau_sel: float
    disc_avoided_sel: float
    chart_block: Dict[str, Dict[str, float]]
    checks: Dict[str, bool]
    chk_master: str
    chk_fail_count: int
    labels: Dict[str, object] = field(default_factory=dict)
    # named values behind linked_value()
    named: Dict[str, object] = field(default_factory=dict)


def compute_outputs(inputs, basis, scenario, direct_ets, overrides=None):
    """Dashboard/Checks reference values; overrides maps input IDs to values
    (as in compute_measures), for what-if states such as negative abatement."""
    meas = compute_measures(inputs, basis, scenario, overrides)
    expo = compute_exposure(inputs, basis, scenario, direct_ets, overrides)
    sens = compute_sensitivity(inputs, basis, scenario, direct_ets, overrides)
    mv = dict(model_values(inputs))
    if overrides:
        mv.update(overrides)
    base = compute_baseline(mv)
    tol = float(mv.get(_TOL_ID, next(r.published_value for r in inputs
                                     if r.id == _TOL_ID)))

    t_lb = sum(m.avg_t_lb for m in meas.measures)
    t_mb = sum(m.avg_t_mb for m in meas.measures)
    mb = basis == "Market-based"
    abated = t_mb if mb else t_lb
    s12 = base.s12_mb_t if mb else base.s12_lb_t
    macc_total = sum(_excel_round0(w) for w in meas.chart_widths)

    sel = expo.scen[expo.sel_key]
    chart = {}
    for tier, key in _SCEN_KEYS:
        c = expo.scen[key].cum
        chart[tier] = {"cum_bau": c["total_bau"], "cum_with": c["total_with"],
                       "cum_avoided": c["avoided"]}

    checks = check_inventory(inputs, mv, meas, expo, sens, base, basis,
                             scenario, direct_ets, abated, t_lb, t_mb, s12,
                             macc_total, tol)

    named = {
        "M_Portfolio_NPV": sens.npv_fin,
        "Sens_PortfolioNPV": sens.npv_incl,
        "M_Total_tLB": t_lb, "M_Total_tMB": t_mb,
        "BL_Scope1": base.s1_total_t, "BL_S2_LB": base.s2_lb_t,
        "BL_S2_MB": base.s2_mb_t, "BL_S12_LB": base.s12_lb_t,
        "BL_S12_MB": base.s12_mb_t,
        "Expo_CumBAU_Sel": sel.cum["total_bau"],
        "Expo_CumWith_Sel": sel.cum["total_with"],
        "Expo_CumAvoided_Sel": sel.cum["avoided"],
        "Expo_DiscBAU_Sel": sel.disc["total_bau"],
        "Expo_DiscAvoided_Sel": sel.disc["avoided"],
        "MACC_TotalAbatement": macc_total,
        "Sel_Scenario": scenario, "Sel_Basis": basis,
        "Sel_DirectETS": direct_ets,
        "BL_Total_MWh": base.total_mwh,
        "Dash_AbatedSel": abated,
        "M_HP_AvgtSel": next(m.avg_t_sel for m in meas.measures
                             if m.key == "HP"),
        "Carbon_ICP_Level": float(next(
            r.published_value for r in inputs if r.id == "Carbon_ICP_Level")),
        "Sens_RankStab_AnyChanged": int(any(
            r.flag != "Same" for r in sens.rank_stab)),
    }
    named["Expo_ICP_Level"] = named["Carbon_ICP_Level"]
    for m in meas.measures:
        named["M_%s_Capex" % m.key] = m.capex
    for key in ("CP", "NDC", "NZ50"):
        c = expo.scen[key].cum
        named["Expo_CumBAU_" + key] = c["total_bau"]
        named["Expo_CumWith_" + key] = c["total_with"]
        named["Expo_CumAvoided_" + key] = c["avoided"]
    # Sens_PortfolioNPV is the carbon-inclusive NPV, M_Portfolio_NPV the
    # financial one; sens.npv_fin equals the Measures portfolio NPV.
    named["M_Portfolio_NPV"] = sum(m.npv for m in meas.measures)

    labels = {
        "abated": "Abated per year, %s basis" % basis,
        "share": "Share of Scope 1+2 abated, %s basis" % basis,
        "npv_incl": "Including carbon cash savings, %s scenario, %s basis"
                    % (scenario, basis),
        "cost": "Cost of not acting, %s scenario" % scenario,
        # the cumulative tiles sum the exposure window only (CR-02)
        "cost_window": "Cash carbon cost %d to %d (exposure window), "
                       "undiscounted, real EUR 2025" % (
                           expo.years[0], int(mv["Expo_LastYear"])),
        "scen_chart": "Cost of not acting by scenario: BAU vs with measures "
                      "(%s basis, Direct ETS %s)" % (basis, direct_ets),
        "selectors": {"Sel_Scenario": scenario, "Sel_Basis": basis,
                      "Sel_DirectETS": direct_ets},
    }
    fails = sum(1 for v in checks.values() if not v)
    return OutputsResult(
        npv_fin=named["M_Portfolio_NPV"], npv_incl=sens.npv_incl,
        abated_sel=abated, macc_total=macc_total, s12_sel=s12,
        share=abated / s12 if s12 else 0.0,
        cum_bau_sel=sel.cum["total_bau"], cum_with_sel=sel.cum["total_with"],
        cum_avoided_sel=sel.cum["avoided"], disc_bau_sel=sel.disc["total_bau"],
        disc_avoided_sel=sel.disc["avoided"], chart_block=chart,
        checks=checks, chk_master="OK" if fails == 0 else "ERROR",
        chk_fail_count=fails, labels=labels, named=named)


_MKEYS = ("LED", "VSD", "HP", "PV", "Fleet", "RC")
_STACK = (("M_Check_StackNonNeg", "cap_nonneg"),
          ("M_Check_ElecReductionsCap", "cap_elec_reductions"),
          ("M_Check_PVSelfConsumed", "cap_pv_le_s4"),
          ("M_Check_ContractCap", "cap_covered_le_s5"),
          ("M_Check_GasCap", "cap_gas"),
          ("M_Check_DieselCap", "cap_diesel"))


def check_inventory(inputs, mv, meas, expo, sens, base, basis, scenario,
                    direct_ets, abated, t_lb, t_mb, s12, macc_total,
                    round_tol):
    """Reference value of every status row on the Checks sheet (WR-01).

    Keyed by the workbook name each row links to (or defines, for Chk_*).
    Each value restates the owner-sheet formula on the reference model's own
    numbers, so the Checks sheet caches these instead of literals, and the
    master flag and fail count derive from them.
    """
    tol_m = float(mv["Const_CheckTolMoney"])
    tol = float(mv["Const_CheckTolerance"])
    tol_irr = float(mv["Const_IRRCheckTolMoney"])
    c = {}
    # group 1: stack caps, PV peak, baseline, carbon anchors and conv. years
    for name, attr in _STACK:
        c[name] = bool(getattr(meas.stack, attr))
    c["M_Check_PVPeakBelowLoad"] = bool(meas.by_key("PV").sizing["peak_ok"])
    c["BL_Check_Carriers"] = base.check_carriers == "OK"
    c["BL_Check_Ratio"] = base.check_ratio == "OK"
    first_year = expo.years[0]
    for key, (ays, _avs, _ann) in carbon_paths(inputs).items():
        c["Carb_Check_Anchors_" + key] = bool(
            all(a < b for a, b in zip(ays, ays[1:])) and ays[0] < first_year)
    conv_ok = bool(mv["Carbon_ETS1_ConvYear"] >= mv["Carbon_EUA_AnchorYear"]
                   and mv["Carbon_ETS2_ConvYear"]
                   >= mv["Carbon_ETS2_StartYear"])
    c["Carb_Check_ConvYears"] = conv_ok
    # groups 2, 3 and 5: per-measure appraisal checks
    for m in meas.measures:
        k = m.key
        cf = list(m.cf_fin)
        c["M_Check_%s_NPVMemo" % k] = abs(m.npv - m.npv_memo) <= tol_m
        c["M_Check_%s_NPVatZero" % k] = (
            abs(cf[0] + sum(cf[1:]) - sum(cf)) <= tol_m)
        c["M_Check_%s_NPVatIRR" % k] = (
            abs(ap.npv0(m.irr, cf)) <= tol_irr
            if isinstance(m.irr, float) else True)
        c["M_Check_%s_Annuity" % k] = bool(m.annuity_ok) if m.eligible \
            else True
        c["M_Check_%s_BreakEven" % k] = (
            abs(m.lev - m.break_even) <= tol
            if isinstance(m.lev, float) else True)
    # group 4: sensitivity
    sel = expo.scen[expo.sel_key]
    base_npv = sens.npv_incl
    avoided_pv = sum(a * d * o for a, d, o in zip(sel.avoided, meas.df,
                                                  meas.op))
    c["Sens_Check_Reconcile"] = abs(
        base_npv - (sum(m.npv for m in meas.measures) + avoided_pv)) <= tol_m
    c["Sens_Check_CarbonPV"] = abs(sens.pv_carbon - (
        sens.pv_ets2_gross + sens.pv_pt_gross - sens.pv_pt_embedded)) <= tol_m
    mid = len(sens.grid) // 2
    c["Sens_Check_GridCentre"] = abs(
        sens.grid[mid][len(sens.grid[mid]) // 2] - base_npv) <= tol_m
    c["Sens_Check_RateCentre"] = abs(
        sens.rate_npvs[len(sens.rate_npvs) // 2] - base_npv) <= tol_m

    def _z(x):
        return 0.0 if abs(x) <= tol_m else x
    ranks = [t.rank for t in sens.tornado]
    downs = [_z(min(t.npv_low, t.npv_high) - base_npv) for t in sens.tornado]
    ups = [_z(max(t.npv_low, t.npv_high) - base_npv) for t in sens.tornado]
    n_t = len(ranks)
    c["Sens_Check_Torn"] = bool(
        max(ranks) == n_t and sum(ranks) == n_t * (n_t + 1) // 2
        and max(downs) <= 0 and min(ups) >= 0)
    lev_ok = True
    for rs in sens.rank_stab:
        m = meas.by_key(rs.key)
        if m.eligible and isinstance(rs.lev_base, float) \
                and isinstance(m.lev, float):
            lev_ok = lev_ok and abs(rs.lev_base - m.lev) <= tol_m
    c["Sens_Check_LevBase"] = bool(lev_ok)
    # group 5 and 6: Dashboard-dependent checks (defined on Checks).
    # Like for like (CR-01): the MACC leaves out measures with no abatement,
    # so its width total is compared with the eligible measures only, and the
    # tile (net sum of all six, negatives included) with the per-measure sum.
    elig_t = sum(m.avg_t_sel for m in meas.measures if m.eligible)
    c["Chk_TileVsMACC"] = bool(
        abs(elig_t - macc_total) <= len(meas.measures) * round_tol
        and abs(sum(m.avg_t_sel for m in meas.measures) - abated) <= tol)
    share = abated / s12 if s12 else 0.0
    c["Chk_ShareInRange"] = 0.0 <= share <= 1.0
    c["Chk_BasisExact"] = abated == t_lb or abated == t_mb
    # group 7: exposure integrity
    scen = list(expo.scen.values())
    start2 = mv["Carbon_ETS2_StartYear"]
    pre = [1 if y < start2 else 0 for y in expo.years]
    c["Expo_Check_ETS2ZeroBeforeStart"] = all(
        sum(x * p for x, p in zip(s.ets2, pre)) == 0 for s in scen)
    c["Expo_Check_ETSExclusive"] = all(
        sum(x * y for x, y in zip(s.p_stat1, s.p_stat2)) == 0 for s in scen)
    c["Expo_Check_CashIsChannels"] = all(
        abs(sum(tot) - sum(e2) - sum(dr) - sum(pt)) <= tol_m
        for s in scen
        for tot, e2, dr, pt in ((s.bau_total, s.bau_ets2, s.bau_dir,
                                 s.bau_pt),
                                (s.with_total, s.with_ets2, s.with_dir,
                                 s.with_pt)))
    c["Expo_Check_ConvYears"] = conv_ok
    diff = [sum(expo.measure_avoided[k][n] for k in _MKEYS) - sel.avoided[n]
            for n in range(len(expo.years))]
    diff = [d if abs(d) > tol_m else 0.0 for d in diff]
    c["Expo_Check_MeasuresReconcile"] = sum(d * d for d in diff) <= tol_m
    c["Expo_Check_ContractZero"] = sum(
        x * x for x in expo.measure_avoided["RC"]) <= tol_m
    c["Expo_Check_BridgeSums"] = abs(
        sel.disc["total_bau"]
        - sum(expo.measure_disc_avoided[k] for k in _MKEYS)
        - sel.disc["total_with"]) <= tol_m
    # group 8: selector validity
    c["Chk_Sel_Scenario"] = scenario in SCENARIOS_UI
    c["Chk_Sel_Basis"] = basis in BASES
    c["Chk_Sel_DirectETS"] = direct_ets in ONOFF
    return dict((k, bool(v)) for k, v in c.items())


def all_states(inputs=INPUTS):
    # type: (...) -> Dict[Tuple[str, str, str], OutputsResult]
    return {s: compute_outputs(inputs, *s) for s in STATES}


def linked_value(name, state, inputs=INPUTS):
    """Reference value of a defined name the Dashboard links to."""
    res = compute_outputs(inputs, *state)
    if name not in res.named:
        raise KeyError(name)
    return res.named[name]
