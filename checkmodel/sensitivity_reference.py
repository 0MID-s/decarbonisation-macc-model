"""Independent pure-Python model of the Sensitivity sheet (plan 04-04).

Stdlib + config + checkmodel only. Never imports xl or qa.

Two independent paths:
  1. compute_sensitivity: the closed-form helper values the sheet shows
     (a base NPV plus linear helper PVs, so no model re-run per cell).
  2. full_recompute_npv: re-runs the Phase 3 and Phase 4 reference models
     with the changed input and returns the full NPV. Tests prove every
     closed form equals this, off-centre as well as at the centre.

Key point (RESEARCH Pitfall 1): the carbon term is NOT linear in the
carbon price level as a whole. The electricity pass-through is
mef x PTR x (EUA price - embedded EUA), and the embedded EUA is a fixed
2025 figure. Scaling the carbon price scales only the GROSS part, so the
grid uses gross helper PVs and leaves the embedded part unscaled.

All NPVs are over the full horizon 2026-2055 (year 0 undiscounted), money
rows are benefits to the firm (+).
"""
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

from checkmodel.appraisal import levelised, npv0
from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.carbon_reference import carbon_paths, eur_route_factor
from checkmodel.exposure_reference import (STATES, blended_path,
                                           compute_exposure)
from checkmodel.macc_reference import input_ranks_eligible
from checkmodel.measures_reference import compute_measures
from checkmodel.rates_reference import restate_eur2025
from config.inputs import INPUTS

TORNADO_DRIVERS = ("rate", "elec", "gas", "carbon_level", "capex", "go", "ev",
                   "ptr", "mef", "ets2_delay", "ngfs_route")

_LABELS = {
    "rate": "Discount rate", "elec": "Electricity price",
    "gas": "Gas price", "carbon_level": "Carbon price scenario (Low/High)",
    "capex": "Capex", "go": "Guarantee-of-origin price",
    "ev": "EV price premium", "ptr": "Electricity pass-through rate",
    "mef": "Marginal emission factor", "ets2_delay": "ETS2 start delay",
    "ngfs_route": "NGFS currency conversion route"}

# Hurdle-rate override that makes the rank-stability test show "Changed"
# (0.12 = lowest value scanned that flips: LED rank 3 to 4, RC rank 4 to 3).
RANK_FLIP_OVERRIDE = {"Sens_Hurdle_3": 0.12}  # type: Dict[str, float]

Num = Union[float, str]


@dataclass(frozen=True)
class TornadoRow:
    driver_id: str
    label: str
    low_input: object
    high_input: object
    npv_low: float
    npv_high: float
    swing: float
    rank: int


@dataclass(frozen=True)
class RankStabRow:
    key: str
    lev_base: Num
    lev_r1: Num
    lev_r2: Num
    lev_r3: Num
    rank_base: int
    rank_r1: int
    rank_r2: int
    rank_r3: int
    flag: str


@dataclass(frozen=True)
class SensitivityResult:
    basis: str
    scenario: str
    direct_ets: str
    rate: float
    npv_fin_by_measure: Dict[str, float]
    pv_carbon_by_measure: Dict[str, float]
    npv_incl_by_measure: Dict[str, float]
    npv_fin: float
    pv_carbon: float
    npv_incl: float
    elec_saved: Tuple[float, ...]
    gas_saved: Tuple[float, ...]
    diesel_saved: Tuple[float, ...]
    covered_sum: Tuple[float, ...]
    t_stat_saved: Tuple[float, ...]
    t_fleet_saved: Tuple[float, ...]
    portfolio_cf: Tuple[float, ...]
    pv_elec: float
    pv_gas: float
    pv_diesel: float
    pv_go: float
    pv_energy: float
    pv_ets2_gross: float
    pv_pt_gross: float
    pv_pt_embedded: float
    pv_pt_net: float
    pv_pt_net_unit: float
    pv_capex: float
    pv_ev: float
    pv_go_cost: float
    grid_axis: Tuple[float, ...]
    grid: Tuple[Tuple[float, ...], ...]
    rate_axis: Tuple[float, ...]
    rate_npvs: Tuple[float, ...]
    tornado: Tuple[TornadoRow, ...]
    tornado_order: Tuple[str, ...]
    rank_stab: Tuple[RankStabRow, ...]
    # per-year helper rows behind the ETS2-delay and NGFS-route tornado bars
    delay_w: Tuple[float, ...] = ()
    delay_p: Tuple[float, ...] = ()
    delay_dstat: Tuple[float, ...] = ()
    delay_dfleet: Tuple[float, ...] = ()
    route_ratio: float = 1.0
    route_d1: Tuple[float, ...] = ()
    route_d2: Tuple[float, ...] = ()
    route_dstat: Tuple[float, ...] = ()
    hurdles: Tuple[float, ...] = ()


def _pv(df, row):
    return sum(d * x for d, x in zip(df, row))


def _merge(overrides, extra):
    out = dict(overrides or {})
    out.update(extra)
    return out


def full_recompute_npv(inputs, basis, scenario, direct_ets, energy_mult=1.0,
                       carbon_mult=1.0, rate=None, overrides=None,
                       ngfs_scale=1.0, capex_mult=1.0, elec_mult=1.0,
                       gas_mult=1.0, diesel_mult=1.0):
    # type: (Sequence, str, str, str, float, float, Optional[float], Optional[Dict[str, float]], float, float, float, float, float) -> float
    """Independent path: re-run both reference models and add them up.

    Energy prices scale through the Inputs price cells of the selected
    band (average of S1 and S2 scales linearly); capex scales through the
    capex inputs; the real discount rate through the cost-of-capital input.
    """
    v = dict(model_values(inputs))
    if overrides:
        v.update(overrides)
    ov = dict(overrides or {})
    bl = compute_baseline(v)
    em, gm = energy_mult * elec_mult, energy_mult * gas_mult
    if em != 1.0:
        for s in ("S1", "S2"):
            k = "Price_Elec%s_%s" % (s, bl.elec_band_code)
            ov[k] = v[k] * em
    if gm != 1.0:
        for s in ("S1", "S2"):
            k = "Price_Gas%s_%s" % (s, bl.gas_band_code)
            ov[k] = v[k] * gm
    dm = energy_mult * diesel_mult
    if dm != 1.0:
        ov["Price_DieselBE_WithTax"] = v["Price_DieselBE_WithTax"] * dm
    if capex_mult != 1.0:
        c = capex_mult
        for k in ("Meas_LED_ZMCapex", "Meas_VSD_ZMCapex", "Meas_PV_CapexDEA",
                  "Meas_Fleet_EVPremium", "Meas_Fleet_ChargerCapex"):
            ov[k] = v[k] * c
        # heat pump capex is the difference to the boiler it replaces
        ov["Meas_HP_Capex_HT"] = (v["Meas_Boiler_Capex"]
                                  + c * (v["Meas_HP_Capex_HT"]
                                         - v["Meas_Boiler_Capex"]))
    if rate is not None:
        infl = v["Fin_InflationLongRun"]
        ov["Fin_CoC_ChemSpecialty"] = (1.0 + rate) * (1.0 + infl) - 1.0
    ms = compute_measures(inputs, basis, scenario, ov)
    ex = compute_exposure(inputs, basis, scenario, direct_ets, ov,
                          carbon_mult=carbon_mult, ngfs_scale=ngfs_scale)
    npv = sum(m.npv for m in ms.measures)
    for m in ms.measures:
        npv += _pv(ms.df, ex.measure_avoided[m.key])
    return npv


def compute_sensitivity(inputs, basis, scenario, direct_ets, overrides=None):
    # type: (Sequence, str, str, str, Optional[Dict[str, float]]) -> SensitivityResult
    v = dict(model_values(inputs))
    if overrides:
        v.update(overrides)
    ms = compute_measures(inputs, basis, scenario, overrides)
    ex = compute_exposure(inputs, basis, scenario, direct_ets, overrides)
    bl = compute_baseline(v)
    df, r = ms.df, ms.rate
    ny = len(df)
    rng = range(ny)
    keys = [m.key for m in ms.measures]
    sel = ex.scen[ex.sel_key]

    npv_fin_m = {m.key: m.npv for m in ms.measures}
    pv_c_m = {m.key: _pv(df, ex.measure_avoided[m.key]) for m in ms.measures}
    npv_incl_m = {k: npv_fin_m[k] + pv_c_m[k] for k in keys}
    npv_fin = sum(npv_fin_m.values())
    pv_carbon = sum(pv_c_m.values())
    npv_incl = npv_fin + pv_carbon

    cf = tuple(sum(m.cf_fin[n] for m in ms.measures)
               + sum(ex.measure_avoided[k][n] for k in keys) for n in rng)

    # ---- physical savings rows ---------------------------------------
    elec_saved = tuple(ex.elec_bau[n] - ex.elec_with[n] for n in rng)
    gas_saved = tuple(-sum(m.d_gas[n] for m in ms.measures) for n in rng)
    dsl_saved = tuple(-sum(m.d_diesel[n] for m in ms.measures) for n in rng)
    cov = tuple(sum(m.covered[n] for m in ms.measures) for n in rng)
    ts = tuple(ex.t_stat_bau[n] - ex.t_stat_with[n] for n in rng)
    tf = tuple(ex.t_fleet_bau[n] - ex.t_fleet_with[n] for n in rng)

    pidx = ms.price_idx
    go = v["Meas_RC_GOPrice"] / v["Const_MWh_per_GO"]
    pv_elec = _pv(df, [elec_saved[n] * bl.elec_price * pidx[n] for n in rng])
    pv_gas = _pv(df, [gas_saved[n] * bl.gas_price_ncv * pidx[n] for n in rng])
    pv_dsl = _pv(df, [dsl_saved[n] * ms.diesel_exvat * pidx[n] for n in rng])
    pv_go = _pv(df, [cov[n] * go * pidx[n] for n in rng])
    pv_energy = pv_elec + pv_gas + pv_dsl

    # ---- gross carbon helper PVs -------------------------------------
    pv_ets2_gross = _pv(df, [ts[n] * (sel.p_stat1[n] + sel.p_stat2[n])
                             + tf[n] * sel.ets2[n] for n in rng])
    ptr = v["Pass_PTR"]
    pv_pt_gross = ex.mef * ptr * _pv(df, [elec_saved[n] * sel.ets1[n]
                                          for n in rng])
    pv_pt_emb = ex.mef * ptr * ex.embedded_eua * _pv(df, elec_saved)
    pv_pt_net = pv_pt_gross - pv_pt_emb
    # net pass-through PV per unit of pass-through rate (no division by ptr)
    pv_pt_net_unit = ex.mef * (_pv(df, [elec_saved[n] * sel.ets1[n]
                                        for n in rng])
                               - ex.embedded_eua * _pv(df, elec_saved))

    # ---- capex / EV helpers ------------------------------------------
    def kfac(m):
        if m.capex == 0.0:
            return 0.0
        rows = [a + b + c for a, b, c in
                zip(m.capex_row, m.subsidy_row, m.residual_row)]
        return -_pv(df, rows) / m.capex

    pv_capex = sum(m.capex * kfac(m) for m in ms.measures)
    pv_ev = (v["Base_Fleet_Vehicles"] * v["Meas_Fleet_EVPremium"]
             * kfac(ms.by_key("Fleet")))

    # ---- grid and rate strip -----------------------------------------
    step = v["Sens_GridStep"]
    axis = tuple(1.0 + i * step for i in (-2, -1, 0, 1, 2))
    gross = pv_ets2_gross + pv_pt_gross
    grid = tuple(tuple(npv_incl + (me - 1.0) * pv_energy + (mc - 1.0) * gross
                       for mc in axis) for me in axis)
    rstep = v["Sens_RateStep"]
    raxis = tuple(r + i * rstep for i in (-2, -1, 0, 1, 2))
    rnpvs = tuple(npv0(x, cf) for x in raxis)

    # ---- tornado -----------------------------------------------------
    def pct(k):
        return v[k]

    d_rate = v["Sens_Torn_RateDelta"]
    raw = {}
    raw["rate"] = (r - d_rate, r + d_rate, npv0(r - d_rate, cf),
                   npv0(r + d_rate, cf))
    p = pct("Sens_Torn_ElecPct")
    raw["elec"] = (-p, p, npv_incl - p * pv_elec, npv_incl + p * pv_elec)
    p = pct("Sens_Torn_GasPct")
    raw["gas"] = (-p, p, npv_incl - p * pv_gas, npv_incl + p * pv_gas)
    lo_ex = compute_exposure(inputs, basis, "Low", direct_ets, overrides)
    hi_ex = compute_exposure(inputs, basis, "High", direct_ets, overrides)
    raw["carbon_level"] = (
        "Low", "High",
        npv_fin + _pv(df, lo_ex.scen[lo_ex.sel_key].avoided),
        npv_fin + _pv(df, hi_ex.scen[hi_ex.sel_key].avoided))
    p = pct("Sens_Torn_CapexPct")
    raw["capex"] = (-p, p, npv_incl + p * pv_capex, npv_incl - p * pv_capex)
    p = pct("Sens_Torn_GOPct")
    raw["go"] = (-p, p, npv_incl + p * pv_go, npv_incl - p * pv_go)
    p = pct("Sens_Torn_EVPct")
    raw["ev"] = (-p, p, npv_incl + p * pv_ev, npv_incl - p * pv_ev)
    plow = pct("Sens_Torn_PTRLow")
    raw["ptr"] = (plow, ptr, npv_incl + (plow - ptr) * pv_pt_net_unit,
                  npv_incl)
    p = pct("Sens_Torn_MEFPct")
    raw["mef"] = (-p, p, npv_incl - p * pv_pt_net, npv_incl + p * pv_pt_net)

    # ETS2 delay: rebuild only the ETS2 price path with the later start
    ng = carbon_paths(inputs)[ex.sel_key][2]
    start2 = v["Carbon_ETS2_StartYear"]
    delay = v["Sens_ETS2_StartDelay"]
    stab = restate_eur2025(v, "Carbon_ETS2_StabPrice", 2020)
    alt2 = blended_path(stab, start2 + delay, v["Carbon_ETS2_ConvYear"], ng,
                        ex.years, start_year=start2 + delay)
    on = direct_ets == "On"
    d_ets2 = [alt2[n] - sel.ets2[n] for n in rng]
    s0 = start2 + delay
    dl_w = [min(1.0, max(0.0, (ex.years[n] - s0)
                         / max(v["Carbon_ETS2_ConvYear"] - s0, 1.0)))
            for n in rng]
    dl_p = [0.0 if ex.years[n] < s0 else (1.0 - dl_w[n]) * stab
            + dl_w[n] * ng[n] for n in rng]
    dl_stat = [(0.0 if on else dl_p[n]) - sel.p_stat2[n] for n in rng]
    dl_fleet = [dl_p[n] - sel.ets2[n] for n in rng]
    d_term = _pv(df, [(tf[n] + (0.0 if on else ts[n])) * d_ets2[n]
                      for n in rng])
    raw["ets2_delay"] = (start2, start2 + delay, npv_incl, npv_incl + d_term)

    # NGFS route: price = (1-w) anchor + w * scale * ngfs, so d = (s-1) w ngfs
    by_id = {x.id: x for x in inputs}
    unit_year = by_id["Carbon_NGFS_CP"].price_basis.year
    base_route = eur_route_factor(v, unit_year)
    s = v["Carbon_NGFS_AltRouteFactor"] / base_route
    d1 = [(s - 1.0) * ex.w_ets1[n] * ng[n] for n in rng]
    d2 = [(s - 1.0) * ex.w_ets2[n] * ng[n] for n in rng]
    fa = v["Carbon_DirectETS_FreeAlloc"]
    d_route = _pv(df, [
        ts[n] * (d1[n] * (1.0 - fa) if on else d2[n]) + tf[n] * d2[n]
        + ex.mef * ptr * elec_saved[n] * d1[n] for n in rng])
    raw["ngfs_route"] = (1.0, s, npv_incl, npv_incl + d_route)

    rt_d1, rt_d2 = d1, d2
    rt_stat = [d1[n] * (1.0 - fa) if on else d2[n] for n in rng]

    swings = [abs(raw[d][3] - raw[d][2]) for d in TORNADO_DRIVERS]
    rows = []
    for i, d in enumerate(TORNADO_DRIVERS):
        sw = swings[i]
        rank = (1 + sum(1 for x in swings if x > sw)
                + sum(1 for x in swings[:i] if x == sw))
        lo, hi, nl, nh = raw[d]
        rows.append(TornadoRow(d, _LABELS[d], lo, hi, nl, nh, sw, rank))
    order = tuple(x.driver_id for x in sorted(rows, key=lambda x: x.rank))

    # ---- rank stability ----------------------------------------------
    hurdles = [v["Sens_Hurdle_1"], v["Sens_Hurdle_2"], v["Sens_Hurdle_3"]]

    def lev_at(m, h):
        if not m.eligible:
            return "n/a"
        v_t = npv0(h, m.t_sel)
        if v_t <= 0:
            return "n/a"
        return levelised(npv0(h, m.cf_fin), v_t)

    def ranks_for(levs):
        tab = [(m.name, m.avg_t_sel, lv if m.eligible else 0.0, m.eligible)
               for m, lv in zip(ms.measures, levs)]
        return input_ranks_eligible(tab)

    base_levs = [m.lev for m in ms.measures]
    lev_h = [[lev_at(m, h) for m in ms.measures] for h in hurdles]
    rk_base = ranks_for(base_levs)
    rk_h = [ranks_for(lv) for lv in lev_h]
    stab = []
    for i, m in enumerate(ms.measures):
        same = all(rk_h[j][i] == rk_base[i] for j in range(3))
        stab.append(RankStabRow(
            m.key, base_levs[i] if m.eligible else "n/a",
            lev_h[0][i], lev_h[1][i], lev_h[2][i], rk_base[i],
            rk_h[0][i], rk_h[1][i], rk_h[2][i],
            "Same" if same else "Changed"))

    return SensitivityResult(
        basis=basis, scenario=scenario, direct_ets=direct_ets, rate=r,
        npv_fin_by_measure=npv_fin_m, pv_carbon_by_measure=pv_c_m,
        npv_incl_by_measure=npv_incl_m, npv_fin=npv_fin,
        pv_carbon=pv_carbon, npv_incl=npv_incl, elec_saved=elec_saved,
        gas_saved=gas_saved, diesel_saved=dsl_saved, covered_sum=cov,
        t_stat_saved=ts, t_fleet_saved=tf, portfolio_cf=cf, pv_elec=pv_elec,
        pv_gas=pv_gas, pv_diesel=pv_dsl, pv_go=pv_go, pv_energy=pv_energy,
        pv_ets2_gross=pv_ets2_gross, pv_pt_gross=pv_pt_gross,
        pv_pt_embedded=pv_pt_emb, pv_pt_net=pv_pt_net,
        pv_pt_net_unit=pv_pt_net_unit, pv_capex=pv_capex,
        pv_ev=pv_ev, pv_go_cost=pv_go, grid_axis=axis, grid=grid,
        rate_axis=raxis, rate_npvs=rnpvs, tornado=tuple(rows),
        tornado_order=order, rank_stab=tuple(stab),
        delay_w=tuple(dl_w), delay_p=tuple(dl_p), delay_dstat=tuple(dl_stat),
        delay_dfleet=tuple(dl_fleet), route_ratio=s, route_d1=tuple(rt_d1),
        route_d2=tuple(rt_d2), route_dstat=tuple(rt_stat),
        hurdles=tuple(hurdles))


def untested_note_values(inputs, basis="Market-based", scenario="Central",
                         direct_ets="Off"):
    # type: (Sequence, str, str, str) -> Dict[str, float]
    """Portfolio NPV change (incl. carbon) for the note-only sensitivities."""
    v = model_values(inputs)
    base = full_recompute_npv(inputs, basis, scenario, direct_ets)
    lp, hs = v["Sens_Note_LifePct"], v["Sens_Note_HPShareDelta"]
    out = {}
    for tag, key in (("led", "Meas_LED_Life"), ("vsd", "Meas_VSD_Life")):
        for side, f in (("low", 1.0 - lp), ("high", 1.0 + lp)):
            n = full_recompute_npv(inputs, basis, scenario, direct_ets,
                                   overrides={key: v[key] * f})
            out["%s_life_%s" % (tag, side)] = float(n - base)
    hi_med = v["Meas_HP_HeatHighPJ"] + v["Meas_HP_HeatMedPJ"]
    share = v["Meas_HP_HeatLowPJ"] / (hi_med + v["Meas_HP_HeatLowPJ"])
    for side, sgn in (("low", -1.0), ("high", 1.0)):
        s2 = share + sgn * hs
        low_pj = s2 * hi_med / (1.0 - s2)
        n = full_recompute_npv(inputs, basis, scenario, direct_ets,
                               overrides={"Meas_HP_HeatLowPJ": low_pj})
        out["hp_share_%s" % side] = float(n - base)
    return out


def all_states(inputs=INPUTS):
    # type: (Sequence) -> Dict[Tuple[str, str, str], SensitivityResult]
    return {s: compute_sensitivity(inputs, *s) for s in STATES}
