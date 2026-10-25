"""Independent pure-Python model of the six measures, the electricity stack
and the MACC table (plan 03-06).

Stdlib + config + checkmodel only. Never imports xl or qa. Source of every
cached value on the Measures and MACC sheets and the QA-02 comparison.

Conventions: year 0 = 2026 (initial capex, undiscounted); operating flows
2027-2055. Money rows: + = benefit to the firm. Physical deltas: + = more
purchased (dElec, dGas in MWh NCV; dDiesel in litres). Location-based and
market-based tonnes are separate lists and are never added.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union

from checkmodel import appraisal as ap
from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.carbon_reference import SCENARIOS, carbon_paths
from checkmodel.macc_reference import _excel_round0, input_ranks_eligible
from checkmodel.rates_reference import discount_rate_real, restate_eur2025
from config.build_config import BUILD
from config.inputs import INPUTS
from config.measures_catalog import MEASURES

# Copies of xl.sheets.lists values (a test asserts equality).
BASES = ("Location-based", "Market-based")
SCENARIOS_UI = ("Low", "Central", "High")
DEFAULT_STATE = ("Market-based", "Central")
ONOFF = ("Off", "On")
DEFAULT_DIRECT_ETS = "Off"

Cost = Union[float, str]


@dataclass(frozen=True)
class StackResult:
    s0: Tuple[float, ...]
    s1: Tuple[float, ...]
    s2: Tuple[float, ...]
    s3: Tuple[float, ...]
    s4: Tuple[float, ...]
    s5: Tuple[float, ...]
    gas_after: Tuple[float, ...]
    diesel_after: Tuple[float, ...]
    covered: Tuple[float, ...]
    cap_nonneg: bool
    cap_elec_reductions: bool
    cap_pv_le_s4: bool
    cap_covered_le_s5: bool
    cap_gas: bool
    cap_diesel: bool
    caps_ok: bool


@dataclass(frozen=True)
class MeasureResult:
    key: str
    name: str
    capex: float
    full_capex: Optional[float]
    indirect_diff: float
    life: int
    om_benefit: float
    subsidy_frac: float
    res_frac: float
    replacement_years: Tuple[int, ...]
    units: Optional[float]
    sizing: Dict[str, float]
    d_elec: Tuple[float, ...]
    d_gas: Tuple[float, ...]
    d_diesel: Tuple[float, ...]
    covered: Tuple[float, ...]
    capex_row: Tuple[float, ...]
    subsidy_row: Tuple[float, ...]
    residual_row: Tuple[float, ...]
    om_row: Tuple[float, ...]
    e_elec: Tuple[float, ...]
    e_gas: Tuple[float, ...]
    e_diesel: Tuple[float, ...]
    t_lb: Tuple[float, ...]
    t_mb: Tuple[float, ...]
    t_sel: Tuple[float, ...]
    cf_fin: Tuple[float, ...]
    carbon_value: Tuple[float, ...]
    cf_incl: Tuple[float, ...]
    npv: float
    npv_memo: float
    pv_subsidy: float
    npv_pre_sub: float
    npv_incl_carbon: float
    npv_full_capex: Optional[float]
    irr: Union[float, str]
    sign_changes: int
    multi_flag: str
    pay_simple: Union[float, str]
    pay_disc: Union[float, str]
    pv_t_lb: float
    pv_t_mb: float
    pv_t_sel: float
    avg_t_lb: float
    avg_t_mb: float
    avg_t_sel: float
    eligible: bool
    lev: Cost
    break_even: Cost
    lev_pre_sub: Cost
    annuity: float
    annuity_ok: bool


@dataclass(frozen=True)
class MeasuresResult:
    basis: str
    scenario: str
    years: Tuple[int, ...]
    op: Tuple[int, ...]
    df: Tuple[float, ...]
    price_idx: Tuple[float, ...]
    f_lb: Tuple[float, ...]
    f_mb: Tuple[float, ...]
    f_sel: Tuple[float, ...]
    carbon: Tuple[float, ...]
    rate: float
    diesel_exvat: float
    ref_price: float
    low_share: float
    measures: Tuple[MeasureResult, ...]
    stack: StackResult
    ranks: Tuple[int, ...]
    sorted_keys: Tuple[str, ...]
    chart_widths: Tuple[int, ...]
    tiers: Tuple[str, ...]

    def by_key(self, key):
        # type: (str) -> MeasureResult
        for m in self.measures:
            if m.key == key:
                return m
        raise KeyError(key)


def _tup(xs):
    # type: (Sequence[float]) -> Tuple[float, ...]
    return tuple(xs)


def compute_measures(inputs, basis, scenario, overrides=None):
    # type: (Sequence, str, str, Optional[Dict[str, float]]) -> MeasuresResult
    if basis not in BASES:
        raise ValueError("unknown basis %r" % (basis,))
    if scenario not in SCENARIOS_UI:
        raise ValueError("unknown scenario %r" % (scenario,))
    v = dict(model_values(inputs))
    if overrides:
        v.update(overrides)
    bl = compute_baseline(v)
    years = tuple(BUILD.timeline_years)
    ny = len(years)
    last = ny - 1
    rng = range(ny)
    kwh = v["Const_kWh_per_MWh"]

    r = discount_rate_real(v)
    op = [1 if n >= 1 else 0 for n in rng]
    df = [1.0 / (1.0 + r) ** n for n in rng]
    pidx = [(1.0 + v["Price_RealEscalation"]) ** n for n in rng]
    f_lb = [v["EF_GridLB"] * (1.0 + v["EF_GridLB_Change"]) ** n for n in rng]
    f_mb = [v["EF_ResidualMB"] * (1.0 + v["EF_ResidualMB_Change"]) ** n
            for n in rng]
    f_sel = f_lb if basis == BASES[0] else f_mb
    scen_key = [k for k, tier, _ in SCENARIOS if tier == scenario][0]
    carbon = list(carbon_paths(inputs)[scen_key][2])
    diesel_exvat = v["Price_DieselBE_WithTax"] / (1.0 + v["Price_DieselBE_VAT"])
    ref_price = ap.levelised_price(carbon, df, op)

    zeros = [0.0] * ny
    e_ncv = v["EF_Gas_NCV"]
    diesel_t_per_l = v["EF_Diesel_l"] / v["Const_kg_per_t"]

    # ---- sizing ------------------------------------------------------
    sizing = {}  # type: Dict[str, Dict[str, float]]
    spec = {}  # type: Dict[str, dict]

    # LED and VSD
    for key, share, cov, rate_, per_unit_save, zm_capex, cx_year in (
            ("LED", "Meas_LED_LightingShare", "Meas_LED_Coverage",
             "Meas_LED_SavingRate", "Meas_LED_ZMSaving", "Meas_LED_ZMCapex",
             2023),
            ("VSD", "Meas_VSD_MotorShare", "Meas_VSD_Coverage",
             "Meas_VSD_SavingRate", "Meas_VSD_Saving", "Meas_VSD_ZMCapex",
             2023)):
        kwh_saved = (bl.elec_mwh * kwh * v[share] * v[cov] * v[rate_])
        units = kwh_saved / v[per_unit_save]
        capex = units * restate_eur2025(v, zm_capex, cx_year)
        sizing[key] = {"kwh_saved": kwh_saved, "units": units}
        spec[key] = dict(
            capex=capex, full=None, indirect=0.0, life=int(v["Meas_%s_Life" % key]),
            om=0.0, units=units,
            d_elec=[-kwh_saved / kwh * o for o in op],
            d_gas=zeros, d_diesel=zeros)

    # Heat pump
    low_share = v["Meas_HP_HeatLowPJ"] / (
        v["Meas_HP_HeatHighPJ"] + v["Meas_HP_HeatMedPJ"]
        + v["Meas_HP_HeatLowPJ"])
    heat = bl.gas_mwh * v["Meas_Boiler_Eff"] * low_share
    kw = heat / v["Meas_HP_FullLoadHours"] * v["Const_kW_per_MW"]
    hp_capex = kw * (v["Meas_HP_Capex_HT"] - v["Meas_Boiler_Capex"])
    hp_full = kw * v["Meas_HP_Capex_HT"]
    hp_ind = kw * (v["Meas_HP_IndirectCapex_HT"]
                   - v["Meas_Boiler_IndirectCapex"])
    hp_om = -(kw * (v["Meas_HP_FixOM_HT"] - v["Meas_Boiler_FixOM"])
              + heat * (v["Meas_HP_VarOM_HT"] - v["Meas_Boiler_VarOM"]))
    sizing["HP"] = {"heat_mwh": heat, "kw": kw, "low_share": low_share}
    spec["HP"] = dict(
        capex=hp_capex, full=hp_full, indirect=hp_ind,
        life=int(v["Meas_HP_Life_HT"]), om=hp_om, units=None,
        d_elec=[heat / v["Meas_HP_COP_HT"] * o for o in op],
        d_gas=[-heat / v["Meas_Boiler_Eff"] * o for o in op],
        d_diesel=zeros)

    # Fleet
    veh = v["Base_Fleet_Vehicles"]
    fl_capex = veh * (v["Meas_Fleet_EVPremium"] + v["Meas_Fleet_ChargerCapex"])
    fl_full = veh * (v["Meas_Fleet_DieselVanPrice"] + v["Meas_Fleet_EVPremium"]
                     + v["Meas_Fleet_ChargerCapex"])
    sizing["Fleet"] = {"vehicles": veh, "km": bl.fleet_km,
                       "litres": bl.fleet_litres}
    spec["Fleet"] = dict(
        capex=fl_capex, full=fl_full, indirect=0.0,
        life=int(v["Meas_Fleet_Life"]),
        om=bl.fleet_km * v["Meas_Fleet_MaintSaving"], units=None,
        d_elec=[bl.fleet_km * v["Meas_Fleet_EVkWhPerKm"] / kwh * o for o in op],
        d_gas=zeros, d_diesel=[-bl.fleet_litres * o for o in op])

    # PV
    size = v["Meas_PV_Size"]
    pv_out = [size * v["Meas_PV_YieldTilt10"] / kwh
              * (1.0 - v["Meas_PV_Degradation"]) ** (n - 1) * op[n]
              for n in rng]
    sizing["PV"] = {
        "size_kwp": size, "roof_area_m2": size * v["Meas_PV_RoofArea"],
        "peak_ok": float(size / v["Const_kW_per_MW"]
                         <= bl.elec_mwh / v["Const_HoursPerYear"])}
    spec["PV"] = dict(
        capex=size * restate_eur2025(v, "Meas_PV_CapexDEA", 2020),
        full=None, indirect=0.0, life=int(v["Meas_PV_Life"]),
        om=-size * restate_eur2025(v, "Meas_PV_FixOMDEA", 2020), units=None,
        d_elec=[-x for x in pv_out], d_gas=zeros, d_diesel=zeros)

    # ---- stack -------------------------------------------------------
    s0 = [bl.elec_mwh] * ny
    s1 = [a + b for a, b in zip(s0, spec["LED"]["d_elec"])]
    s2 = [a + b for a, b in zip(s1, spec["VSD"]["d_elec"])]
    s3 = [a + b for a, b in zip(s2, spec["HP"]["d_elec"])]
    s4 = [a + b for a, b in zip(s3, spec["Fleet"]["d_elec"])]
    s5 = [a + b for a, b in zip(s4, spec["PV"]["d_elec"])]
    gas_after = [bl.gas_mwh + d for d in spec["HP"]["d_gas"]]
    diesel_after = [bl.fleet_litres + d for d in spec["Fleet"]["d_diesel"]]
    covered = [s5[n] * op[n] for n in rng]
    spec["RC"] = dict(capex=0.0, full=None, indirect=0.0,
                      life=int(v["Meas_RC_Term"]), om=0.0, units=None,
                      d_elec=zeros, d_gas=zeros, d_diesel=zeros)
    sizing["RC"] = {"covered_year1_mwh": covered[1]}

    tol = 1e-9
    nonneg = all(x >= -tol for row in (s0, s1, s2, s3, s4, s5, gas_after,
                                       diesel_after) for x in row)
    elec_red = all(
        -(spec["LED"]["d_elec"][n] + spec["VSD"]["d_elec"][n]
          + spec["PV"]["d_elec"][n]) <= s0[n] + tol for n in rng)
    pv_le = all(pv_out[n] <= s4[n] + tol for n in rng)
    cov_le = all(covered[n] <= s5[n] + tol for n in rng)
    gas_ok = all(-spec["HP"]["d_gas"][n] <= bl.gas_mwh + tol for n in rng)
    dsl_ok = all(-spec["Fleet"]["d_diesel"][n] <= bl.fleet_litres + tol
                 for n in rng)
    stack = StackResult(
        _tup(s0), _tup(s1), _tup(s2), _tup(s3), _tup(s4), _tup(s5),
        _tup(gas_after), _tup(diesel_after), _tup(covered),
        nonneg, elec_red, pv_le, cov_le, gas_ok, dsl_ok,
        all((nonneg, elec_red, pv_le, cov_le, gas_ok, dsl_ok)))

    # ---- per-measure blocks -----------------------------------------
    results = []
    for ms in MEASURES:
        key = ms.key
        sp = spec[key]
        capex = sp["capex"]
        life = sp["life"]
        sub = v["Meas_%s_Subsidy" % key]
        cov = covered if key == "RC" else zeros
        init = [1 if n == 0 else 0 for n in rng]
        repl = ap.replacement_flags(ny, life)
        res_frac = ap.residual_fraction(last, life)
        capex_row = [-capex * (init[n] + repl[n]) for n in rng]
        subsidy_row = [sub * capex * init[n] for n in rng]
        residual_row = [capex * res_frac if n == last else 0.0 for n in rng]
        om_row = [sp["om"] * op[n] for n in rng]
        d_e, d_g, d_d = sp["d_elec"], sp["d_gas"], sp["d_diesel"]
        go = v["Meas_RC_GOPrice"] / v["Const_MWh_per_GO"]
        e_elec = [-(d_e[n] * bl.elec_price + cov[n] * go) * pidx[n]
                  for n in rng]
        e_gas = [-d_g[n] * bl.gas_price_ncv * pidx[n] for n in rng]
        e_dsl = [-d_d[n] * diesel_exvat * pidx[n] for n in rng]
        t_lb = [-(d_e[n] * f_lb[n] + d_g[n] * e_ncv + d_d[n] * diesel_t_per_l)
                for n in rng]
        t_mb = [-(d_e[n] * f_mb[n] + d_g[n] * e_ncv + d_d[n] * diesel_t_per_l)
                + cov[n] * f_mb[n] for n in rng]
        t_sel = t_lb if basis == BASES[0] else t_mb
        cf = [capex_row[n] + subsidy_row[n] + residual_row[n] + om_row[n]
              + e_elec[n] + e_gas[n] + e_dsl[n] for n in rng]
        cval = [t_sel[n] * carbon[n] for n in rng]
        cf_incl = [cf[n] + cval[n] for n in rng]

        npv = ap.npv0(r, cf)
        npv_memo = cf[0] + ap.excel_npv(r, cf[1:])
        pv_sub = ap.npv0(r, subsidy_row)
        npv_pre = npv - pv_sub
        full = sp["full"]
        if full is None:
            npv_full = None
        else:
            k = (sum(df[n] * (init[n] + repl[n]) for n in rng)
                 - res_frac * df[last] - sub)
            npv_full = npv - (full - capex) * k
        pv_lb = ap.npv0(r, t_lb)
        pv_mb = ap.npv0(r, t_mb)
        pv_sel = pv_lb if basis == BASES[0] else pv_mb
        n_op = float(sum(op))
        avg_lb, avg_mb = sum(t_lb) / n_op, sum(t_mb) / n_op
        avg_sel = avg_lb if basis == BASES[0] else avg_mb
        eligible = pv_sel > 0
        lev = ap.levelised(npv, pv_sel)
        lev_pre = ap.levelised(npv_pre, pv_sel)
        avg_net = sum(om_row[n] + e_elec[n] + e_gas[n] + e_dsl[n]
                      for n in rng) / n_op
        if eligible and avg_sel > 0 and life > 0:
            ann = ap.annuity_cost(capex, r, life, avg_net, avg_sel)
            ok = abs(ann - lev_pre) <= (
                v["Const_AnnuityTolAbs"]
                + v["Const_AnnuityTolRel"] * abs(lev_pre))
        else:
            ann, ok = 0.0, True
        repl_years = tuple(years[n] for n in rng if repl[n])
        results.append(MeasureResult(
            key=key, name=ms.name, capex=capex, full_capex=full,
            indirect_diff=sp["indirect"], life=life, om_benefit=sp["om"],
            subsidy_frac=sub, res_frac=res_frac, replacement_years=repl_years,
            units=sp["units"], sizing=sizing[key],
            d_elec=_tup(d_e), d_gas=_tup(d_g), d_diesel=_tup(d_d),
            covered=_tup(cov), capex_row=_tup(capex_row),
            subsidy_row=_tup(subsidy_row), residual_row=_tup(residual_row),
            om_row=_tup(om_row), e_elec=_tup(e_elec), e_gas=_tup(e_gas),
            e_diesel=_tup(e_dsl), t_lb=_tup(t_lb), t_mb=_tup(t_mb),
            t_sel=_tup(t_sel), cf_fin=_tup(cf), carbon_value=_tup(cval),
            cf_incl=_tup(cf_incl), npv=npv, npv_memo=npv_memo,
            pv_subsidy=pv_sub, npv_pre_sub=npv_pre, npv_incl_carbon=
            ap.npv0(r, cf_incl), npv_full_capex=npv_full,
            irr=ap.irr_text(cf), sign_changes=ap.sign_changes(cf),
            multi_flag=ap.multiple_sign_flag(cf),
            pay_simple=ap.payback(cf),
            pay_disc=ap.payback([c * d for c, d in zip(cf, df)]),
            pv_t_lb=pv_lb, pv_t_mb=pv_mb, pv_t_sel=pv_sel,
            avg_t_lb=avg_lb, avg_t_mb=avg_mb, avg_t_sel=avg_sel,
            eligible=eligible, lev=lev, break_even=ap.break_even(npv, pv_sel),
            lev_pre_sub=lev_pre, annuity=ann, annuity_ok=ok))

    # ---- MACC table --------------------------------------------------
    rows = [(m.name, m.avg_t_sel, m.lev if m.eligible else 0.0, m.eligible)
            for m in results]
    ranks = input_ranks_eligible(rows)
    sorted_keys = [None] * len(results)
    for m, rk in zip(results, ranks):
        sorted_keys[rk - 1] = m.key
    widths = tuple(_excel_round0(m.avg_t_sel) if m.eligible else 0
                   for m in results)
    tiers = []
    for m in results:
        if not m.eligible:
            tiers.append("Later")
        elif m.lev < 0:
            tiers.append("Do first")
        elif m.lev <= ref_price:
            tiers.append("Next")
        else:
            tiers.append("Later")

    return MeasuresResult(
        basis=basis, scenario=scenario, years=years, op=_tup(op), df=_tup(df),
        price_idx=_tup(pidx), f_lb=_tup(f_lb), f_mb=_tup(f_mb),
        f_sel=_tup(f_sel), carbon=_tup(carbon), rate=r,
        diesel_exvat=diesel_exvat, ref_price=ref_price, low_share=low_share,
        measures=tuple(results), stack=stack, ranks=tuple(ranks),
        sorted_keys=tuple(sorted_keys), chart_widths=widths,
        tiers=tuple(tiers))


def macc_table(res):
    # type: (MeasuresResult) -> List[Tuple[str, float, Cost, bool, str]]
    """(name, width, cost, eligible, tier) in sorted (MACC) order."""
    out = []
    for k in res.sorted_keys:
        i = [m.key for m in res.measures].index(k)
        m = res.measures[i]
        out.append((m.name, m.avg_t_sel, m.lev, m.eligible, res.tiers[i]))
    return out


def all_states(inputs=INPUTS):
    # type: (Sequence) -> Dict[Tuple[str, str], MeasuresResult]
    return {(b, s): compute_measures(inputs, b, s)
            for b in BASES for s in SCENARIOS_UI}
