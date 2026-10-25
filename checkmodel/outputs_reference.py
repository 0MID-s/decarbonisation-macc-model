"""Reference values for the Dashboard and Checks sheets (plan 05-02).

Stdlib + config + checkmodel only. Never imports xl or qa. Delegates every
number to the existing independent reference modules (measures, exposure,
sensitivity, baseline, macc); no economics are recomputed here.

Scenario keys follow the Exposure column order D, E, F:
Low = CP (Current Policies), Central = NDC, High = NZ50 (Net Zero 2050).
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple

from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.exposure_reference import STATES, compute_exposure
from checkmodel.macc_reference import _excel_round0
from checkmodel.measures_reference import compute_measures
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


def compute_outputs(inputs, basis, scenario, direct_ets):
    meas = compute_measures(inputs, basis, scenario)
    expo = compute_exposure(inputs, basis, scenario, direct_ets)
    sens = compute_sensitivity(inputs, basis, scenario, direct_ets)
    base = compute_baseline(model_values(inputs))
    tol = float(next(r.published_value for r in inputs if r.id == _TOL_ID))

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

    checks = {"BL_Check_Carriers": base.check_carriers == "OK",
              "BL_Check_Ratio": base.check_ratio == "OK",
              "M_StackCaps": bool(meas.stack.caps_ok)}
    for m in meas.measures:
        checks["M_Annuity_" + m.key] = bool(m.annuity_ok)
    for k, v in expo.checks.items():
        checks["Expo_" + k] = bool(v)
    n_meas = len(meas.measures)
    checks["Dash_TileVsMACC"] = abs(abated - macc_total) <= n_meas * tol

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


def all_states(inputs=INPUTS):
    # type: (...) -> Dict[Tuple[str, str, str], OutputsResult]
    return {s: compute_outputs(inputs, *s) for s in STATES}


def linked_value(name, state, inputs=INPUTS):
    """Reference value of a defined name the Dashboard links to."""
    res = compute_outputs(inputs, *state)
    if name not in res.named:
        raise KeyError(name)
    return res.named[name]
