"""Independent pure-Python model of the carbon cost exposure (plan 04-03).

Stdlib + config + checkmodel only. Never imports xl or qa. Source of every
cached value on the Exposure sheets and of the QA comparison.

Economics (written from first principles, not from sheet formulas):
  * ETS1 price path = market-anchored blend: the observed 2025 EUA average
    fades into the NGFS scenario path by the convergence year.
  * ETS2 price is zero before the start year; in the start year it equals the
    stability price (EUR 2025); it then blends into the NGFS path.
  * Stationary fuel pays ETS2 (the fuel supplier is regulated) unless the
    direct-ETS1 toggle is On, in which case it pays ETS1 net of free
    allocation instead. Never both. Fleet diesel always pays ETS2.
  * Electricity: the marginal plant (gas CCGT) sets the power price, so a
    fraction PTR of its carbon cost passes through. The EUA already embedded
    in the 2025 price is subtracted, so the pass-through is a change versus
    the price the baseline already paid and can be negative.
  * ICP lens: Scope 1 + Scope 2 on the selected basis x internal carbon
    price. A decision lens only; never added to a cash total.
Year 0 = 2026. Money rows are costs: positive = the firm pays.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.carbon_reference import SCENARIOS, carbon_paths
from checkmodel.measures_reference import (BASES, ONOFF, SCENARIOS_UI,
                                           compute_measures)
from checkmodel.rates_reference import restate_eur2025
from config.build_config import BUILD
from config.inputs import INPUTS
from config.measures_catalog import MEASURE_KEYS

STATES = tuple((b, s, d) for b in BASES for s in SCENARIOS_UI
               for d in ONOFF)  # type: Tuple[Tuple[str, str, str], ...]

_TOL = 1e-6


def _tup(xs):
    # type: (Sequence[float]) -> Tuple[float, ...]
    return tuple(xs)


def blended_path(anchor_val, anchor_year, conv_year, ngfs, years,
                 start_year=None):
    # type: (float, float, float, Sequence[float], Sequence[int], Optional[float]) -> Tuple[float, ...]
    """Linear fade from anchor_val (at anchor_year) into the ngfs path
    (reached at conv_year). 0.0 before start_year when given."""
    out = []
    span = max(conv_year - anchor_year, 1)
    for y, g in zip(years, ngfs):
        if start_year is not None and y < start_year:
            out.append(0.0)
            continue
        w = min(1.0, max(0.0, (y - anchor_year) / span))
        out.append((1.0 - w) * anchor_val + w * g)
    return _tup(out)


def _weights(anchor_year, conv_year, years, start_year=None):
    span = max(conv_year - anchor_year, 1)
    out = []
    for y in years:
        if start_year is not None and y < start_year:
            out.append(0.0)
        else:
            out.append(min(1.0, max(0.0, (y - anchor_year) / span)))
    return _tup(out)


@dataclass(frozen=True)
class ScenarioExposure:
    key: str
    ets1: Tuple[float, ...]
    ets2: Tuple[float, ...]
    p_stat1: Tuple[float, ...]
    p_stat2: Tuple[float, ...]
    bau_ets2: Tuple[float, ...]
    bau_dir: Tuple[float, ...]
    bau_pt: Tuple[float, ...]
    bau_total: Tuple[float, ...]
    with_ets2: Tuple[float, ...]
    with_dir: Tuple[float, ...]
    with_pt: Tuple[float, ...]
    with_total: Tuple[float, ...]
    avoided: Tuple[float, ...]
    cum: Dict[str, float]
    disc: Dict[str, float]


@dataclass(frozen=True)
class ExposureResult:
    basis: str
    scenario: str
    direct_ets: str
    years: Tuple[int, ...]
    df: Tuple[float, ...]
    window: Tuple[int, ...]
    w_ets1: Tuple[float, ...]
    w_ets2: Tuple[float, ...]
    mef: float
    embedded_eua: float
    t_stat_bau: Tuple[float, ...]
    t_fleet_bau: Tuple[float, ...]
    elec_bau: Tuple[float, ...]
    t_stat_with: Tuple[float, ...]
    t_fleet_with: Tuple[float, ...]
    elec_with: Tuple[float, ...]
    scen: Dict[str, ScenarioExposure]
    sel_key: str
    measure_avoided: Dict[str, Tuple[float, ...]]
    measure_disc_avoided: Dict[str, float]
    bridge: Tuple[Tuple[str, float, float], ...]
    icp_t_bau: Tuple[float, ...]
    icp_t_with: Tuple[float, ...]
    icp_bau: Tuple[float, ...]
    icp_with: Tuple[float, ...]
    icp_avoided: Tuple[float, ...]
    icp_disc_bau: float
    icp_disc_with: float
    icp_disc_avoided: float
    icp_memo_ngfs: Tuple[float, ...]
    checks: Dict[str, bool]


def _wsum(window, weights, row):
    return sum(w * d * x for w, d, x in zip(window, weights, row))


def compute_exposure(inputs, basis, scenario, direct_ets, overrides=None,
                     carbon_mult=1.0, ngfs_scale=1.0):
    # type: (Sequence, str, str, str, Optional[Dict[str, float]], float, float) -> ExposureResult
    if direct_ets not in ONOFF:
        raise ValueError("unknown direct_ets %r" % (direct_ets,))
    v = dict(model_values(inputs))
    if overrides:
        v.update(overrides)
    ms = compute_measures(inputs, basis, scenario, overrides)
    bl = compute_baseline(v)
    years = tuple(BUILD.timeline_years)
    ny = len(years)
    rng = range(ny)
    df = ms.df
    last = v["Expo_LastYear"]
    window = tuple(1 if y <= last else 0 for y in years)
    ones = (1.0,) * ny

    anchor_y = v["Carbon_EUA_AnchorYear"]
    c1, c2 = v["Carbon_ETS1_ConvYear"], v["Carbon_ETS2_ConvYear"]
    start2 = v["Carbon_ETS2_StartYear"]
    stab = restate_eur2025(v, "Carbon_ETS2_StabPrice", 2020)
    eua0 = v["Carbon_EUA_Avg2025"]
    mef = v["EF_Gas_NCV"] / v["Pass_CCGT_Eff"]
    ptr = v["Pass_PTR"]
    fa = v["Carbon_DirectETS_FreeAlloc"]
    embedded = eua0

    w1 = _weights(anchor_y, c1, years)
    w2 = _weights(start2, c2, years, start_year=start2)

    # ---- tonnes ------------------------------------------------------
    st = ms.stack
    sc_g, sc_l = v["Carbon_ETS2_Scope_Gas"], v["Carbon_ETS2_Scope_LPG"]
    sc_n, sc_o = v["Carbon_ETS2_Scope_Naphtha"], v["Carbon_ETS2_Scope_OtherFuels"]
    sc_f = v["Carbon_ETS2_Scope_FleetDiesel"]
    diesel_t_per_l = v["EF_Diesel_l"] / v["Const_kg_per_t"]
    fixed_stat = (bl.lpg_mwh * v["EF_LPG_NCV"] * sc_l
                  + bl.naphtha_mwh * v["EF_Naphtha_NCV"] * sc_n
                  + bl.other_mwh * v["EF_GasOil_NCV"] * sc_o)
    gas_unit = v["EF_Gas_NCV"] * sc_g
    t_stat_bau = [bl.gas_mwh * gas_unit + fixed_stat] * ny
    t_fleet_bau = [bl.fleet_litres * diesel_t_per_l * sc_f] * ny
    elec_bau = list(st.s0)
    t_stat_with = [st.gas_after[n] * gas_unit + fixed_stat for n in rng]
    t_fleet_with = [st.diesel_after[n] * diesel_t_per_l * sc_f for n in rng]
    elec_with = list(st.s5)

    # ---- scenarios ---------------------------------------------------
    ngfs_all = carbon_paths(inputs)
    scen = {}  # type: Dict[str, ScenarioExposure]
    for key, _tier, _label in SCENARIOS:
        ng = [x * ngfs_scale * carbon_mult for x in ngfs_all[key][2]]
        ets1 = blended_path(eua0 * carbon_mult, anchor_y, c1, ng, years)
        ets2 = blended_path(stab * carbon_mult, start2, c2, ng, years,
                            start_year=start2)
        if direct_ets == "On":
            p1 = _tup(p * (1.0 - fa) for p in ets1)
            p2 = _tup(0.0 for _ in rng)
        else:
            p1 = _tup(0.0 for _ in rng)
            p2 = ets2

        def chan(t_stat, t_fleet, elec):
            e2 = _tup(t_stat[n] * p2[n] + t_fleet[n] * ets2[n] for n in rng)
            d = _tup(t_stat[n] * p1[n] for n in rng)
            p = _tup(elec[n] * mef * ptr * (ets1[n] - embedded) for n in rng)
            tot = _tup(e2[n] + d[n] + p[n] for n in rng)
            return e2, d, p, tot

        b2, bd, bp, bt = chan(t_stat_bau, t_fleet_bau, elec_bau)
        w2c, wd, wp, wt = chan(t_stat_with, t_fleet_with, elec_with)
        av = _tup(bt[n] - wt[n] for n in rng)
        rows = {"ets2_bau": b2, "dir_bau": bd, "pt_bau": bp, "total_bau": bt,
                "ets2_with": w2c, "dir_with": wd, "pt_with": wp,
                "total_with": wt, "avoided": av}
        cum = {k: sum(w * x for w, x in zip(window, r))
               for k, r in rows.items()}
        disc = {k: _wsum(window, df, r) for k, r in rows.items()}
        scen[key] = ScenarioExposure(
            key=key, ets1=ets1, ets2=ets2, p_stat1=p1, p_stat2=p2,
            bau_ets2=b2, bau_dir=bd, bau_pt=bp, bau_total=bt,
            with_ets2=w2c, with_dir=wd, with_pt=wp, with_total=wt,
            avoided=av, cum=cum, disc=disc)

    sel_key = [k for k, tier, _ in SCENARIOS if tier == scenario][0]
    sel = scen[sel_key]

    # ---- per-measure avoided cash carbon cost (selected scenario) ----
    mavoid = {}  # type: Dict[str, Tuple[float, ...]]
    mdisc = {}  # type: Dict[str, float]
    for m in ms.measures:
        row = _tup(
            -(m.d_gas[n] * gas_unit * (sel.p_stat1[n] + sel.p_stat2[n])
              + m.d_diesel[n] * diesel_t_per_l * sc_f * sel.ets2[n]
              + m.d_elec[n] * mef * ptr * (sel.ets1[n] - embedded))
            for n in rng)
        mavoid[m.key] = row
        mdisc[m.key] = _wsum(window, df, row)

    bridge = [("BAU", 0.0, sel.disc["total_bau"])]
    run = sel.disc["total_bau"]
    for m in ms.measures:
        end = run - mdisc[m.key]
        bridge.append((m.name, run, end))
        run = end
    bridge.append(("After acting", 0.0, sel.disc["total_with"]))

    # ---- ICP lens ----------------------------------------------------
    f_sel = ms.f_sel
    icp_bau_t = _tup(bl.s1_total_t + bl.s2_heat_t + bl.elec_mwh * f_sel[n]
                     for n in rng)
    icp_with_t = _tup(icp_bau_t[n] - sum(m.t_sel[n] for m in ms.measures)
                      for n in rng)
    level = v["Carbon_ICP_Level"]
    icp_bau = _tup(t * level for t in icp_bau_t)
    icp_with = _tup(t * level for t in icp_with_t)
    icp_av = _tup(icp_bau[n] - icp_with[n] for n in rng)
    memo = _tup(ngfs_all[sel_key][2])

    # ---- checks ------------------------------------------------------
    checks = {}
    checks["ets_exclusive"] = all(
        sum(a * b for a, b in zip(s.p_stat1, s.p_stat2)) == 0.0
        for s in scen.values())
    checks["bridge_sums"] = all(
        abs(sum(mavoid[k][n] for k in MEASURE_KEYS) - sel.avoided[n]) <= _TOL
        for n in rng)
    checks["contract_zero"] = all(x == 0.0 for x in mavoid["RC"])
    checks["bridge_end"] = abs(bridge[-2][2] - bridge[-1][2]) <= _TOL
    checks["ets2_zero_pre_start"] = all(
        s.ets2[n] == 0.0 for s in scen.values() for n in rng
        if years[n] < start2)
    checks["icp_separate"] = all(
        abs(s.bau_total[n] - (s.bau_ets2[n] + s.bau_dir[n] + s.bau_pt[n]))
        <= _TOL and abs(s.with_total[n] - (s.with_ets2[n] + s.with_dir[n]
                                           + s.with_pt[n])) <= _TOL
        for s in scen.values() for n in rng)

    return ExposureResult(
        basis=basis, scenario=scenario, direct_ets=direct_ets, years=years,
        df=df, window=window, w_ets1=w1, w_ets2=w2, mef=mef,
        embedded_eua=embedded, t_stat_bau=_tup(t_stat_bau),
        t_fleet_bau=_tup(t_fleet_bau), elec_bau=_tup(elec_bau),
        t_stat_with=_tup(t_stat_with), t_fleet_with=_tup(t_fleet_with),
        elec_with=_tup(elec_with), scen=scen, sel_key=sel_key,
        measure_avoided=mavoid, measure_disc_avoided=mdisc,
        bridge=tuple(bridge), icp_t_bau=icp_bau_t, icp_t_with=icp_with_t,
        icp_bau=icp_bau, icp_with=icp_with, icp_avoided=icp_av,
        icp_disc_bau=_wsum(window, df, icp_bau),
        icp_disc_with=_wsum(window, df, icp_with),
        icp_disc_avoided=_wsum(window, df, icp_av), icp_memo_ngfs=memo,
        checks=checks)


def all_states(inputs=INPUTS):
    # type: (Sequence) -> Dict[Tuple[str, str, str], ExposureResult]
    return {s: compute_exposure(inputs, *s) for s in STATES}
