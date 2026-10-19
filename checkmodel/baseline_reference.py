"""Independent pure-Python reference for the Maison Veritas baseline (plan 02-08).

Reads inputs from config only (model values = published value x conversion
constant) and mirrors the Baseline sheet formulas step by step. Imports only
stdlib and config. No function adds a location-based and a market-based
quantity: Scope 1+2 is returned once per basis.
"""
import dataclasses
from dataclasses import dataclass
from typing import Dict, Sequence

from config.schema import Kind

ELEC_CODES = ("IA", "IB", "IC", "ID", "IE", "IF", "IG")
GAS_CODES = ("I1", "I2", "I3", "I4", "I5", "I6")


def model_values(inputs):
    # type: (Sequence) -> Dict[str, float]
    """Inputs sheet column G: published x conversion constant (scalars only)."""
    by_id = {r.id: r for r in inputs}
    out = {}
    for r in inputs:
        if r.kind != Kind.SCALAR:
            continue
        if r.conversion_ref is None:
            out[r.id] = float(r.published_value)
        else:
            out[r.id] = (float(r.published_value)
                         * float(by_id[r.conversion_ref].published_value))
    return out


def excel_match_approx(x, bounds):
    # type: (float, Sequence[float]) -> int
    """Excel MATCH(x, bounds, 1): 1-based position of last bound <= x."""
    if x < bounds[0]:
        raise ValueError("MATCH #N/A: %r below first bound %r" % (x, bounds[0]))
    pos = 1
    for i, b in enumerate(bounds):
        if b <= x:
            pos = i + 1
    return pos


@dataclass(frozen=True)
class BaselineResult:
    firm_va_meur: float
    firm_turnover_meur: float
    firm_persons: float
    sector_va_meur: float
    ratio_va: float
    ratio_va_c20_only: float
    sector_turnover_meur: float
    ratio_turnover: float
    sector_remainder_mwh: float
    gasoil_share_of_remainder: float
    gas_mwh: float
    elec_mwh: float
    heat_mwh: float
    lpg_mwh: float
    naphtha_mwh: float
    other_mwh: float
    total_mwh: float
    total_mwh_turnover_basis: float
    fuel_mwh: float
    fuel_load_mw: float
    total_load_mw: float
    below_ets1_threshold: str
    elec_band: int
    elec_band_code: str
    elec_price_s1: float
    elec_price_s2: float
    elec_price: float
    elec_price_2026s1: float
    gas_gcv_per_ncv: float
    gas_gj_gcv: float
    gas_band: int
    gas_band_code: str
    gas_price_s1_gcv: float
    gas_price_s2_gcv: float
    gas_price_gcv: float
    gas_price_ncv: float
    gas_price_2026s1_gcv: float
    elec_cost_eur: float
    gas_cost_eur: float
    fleet_km: float
    fleet_litres: float
    fleet_l_per_100km: float
    fleet_mwh: float
    fleet_t: float
    s1_gas_t: float
    s1_lpg_t: float
    s1_naphtha_t: float
    s1_other_t: float
    s1_stationary_t: float
    s1_total_t: float
    s1_excl_naphtha_t: float
    air_sector_t: float
    air_scaled_t: float
    air_gap_t: float
    combustion_share_of_air: float
    s2_elec_lb_t: float
    s2_elec_mb_t: float
    s2_heat_t: float
    s2_lb_t: float
    s2_mb_t: float
    s12_lb_t: float
    s12_mb_t: float
    check_carriers: str
    check_ratio: str


def compute_baseline(v):
    # type: (Dict[str, float]) -> BaselineResult
    """Baseline chain; each step's Excel formula is the expression shown."""
    # Firm size: class total / enterprises (D-02)
    firm_va = v["Base_SBS_C20M_VA"] / v["Base_SBS_C20M_Ent"]
    firm_to = v["Base_SBS_C20M_Turnover"] / v["Base_SBS_C20M_Ent"]
    firm_pers = v["Base_SBS_C20M_Persons"] / v["Base_SBS_C20M_Ent"]
    inc21 = v["Base_NRG_IncludesC21"]
    sector_va = v["Base_SBS_C20_VA"] + v["Base_SBS_C21_VA"] * inc21  # D-39
    ratio = firm_va / sector_va  # D-03
    ratio_c20 = firm_va / v["Base_SBS_C20_VA"]
    sector_to = (v["Base_SBS_C20_Turnover"]
                 + v["Base_SBS_C21_Turnover"] * inc21)
    ratio_to = firm_to / sector_to

    # Energy by carrier, MWh NCV
    remainder = v["Base_NRG_Total"] - (
        v["Base_NRG_Gas"] + v["Base_NRG_Elec"] + v["Base_NRG_Heat"]
        + v["Base_NRG_LPG"] + v["Base_NRG_Naphtha"])
    gasoil_share = v["Base_NRG_GasOil"] / remainder
    gas = v["Base_NRG_Gas"] * ratio
    elec = v["Base_NRG_Elec"] * ratio
    heat = v["Base_NRG_Heat"] * ratio
    lpg = v["Base_NRG_LPG"] * ratio
    naphtha = v["Base_NRG_Naphtha"] * ratio
    other = remainder * ratio
    total = v["Base_NRG_Total"] * ratio
    total_to = v["Base_NRG_Total"] * ratio_to
    fuel = gas + lpg + naphtha + other
    fuel_load = fuel / v["Const_HoursPerYear"]
    total_load = total / v["Const_HoursPerYear"]
    below = ("Below" if fuel_load < v["Carbon_ETS1_ThermalThresholdMW"]
             else "At or above")

    # Electricity band: MATCH(elec_mwh, lowers, 1); CHOOSE for the code
    e_bounds = [v["Price_ElecLower_" + c] for c in ELEC_CODES]
    e_band = excel_match_approx(elec, e_bounds)
    e_code = ELEC_CODES[e_band - 1]
    e_s1 = v["Price_ElecS1_" + e_code]
    e_s2 = v["Price_ElecS2_" + e_code]
    e_price = (e_s1 + e_s2) / 2  # AVERAGE
    e_26 = v["Price_Elec26S1_" + e_code]

    # Gas band on GJ GCV; price converted GCV -> NCV (D-08)
    g_per = v["EF_Gas_NCV"] / v["EF_Gas_GCV"]
    gas_gj = gas * v["Const_GJ_per_MWh"] * g_per
    g_bounds = [v["Price_GasLower_" + c] for c in GAS_CODES]
    g_band = excel_match_approx(gas_gj, g_bounds)
    g_code = GAS_CODES[g_band - 1]
    g_s1 = v["Price_GasS1_" + g_code]
    g_s2 = v["Price_GasS2_" + g_code]
    g_gcv = (g_s1 + g_s2) / 2
    g_ncv = g_gcv * g_per
    g_26 = v["Price_Gas26S1_" + g_code]
    elec_cost = elec * e_price
    gas_cost = gas * g_ncv

    # Fleet (D-10)
    km = v["Base_Fleet_Vehicles"] * v["Base_Fleet_KmPerVehicle"]
    litres = (km * v["Base_Fleet_gCO2PerKm"] / v["Const_g_per_kg"]
              / v["EF_Diesel_l"])
    l100 = litres / km * v["Const_km_per_100km"]
    fleet_mwh = (litres * (v["EF_Diesel_l"] / v["EF_Diesel_NCV"])
                 / v["Const_kWh_per_MWh"])
    fleet_t = litres * v["EF_Diesel_l"] / v["Const_kg_per_t"]

    # Scope 1 (D-11)
    s1_gas = gas * v["EF_Gas_NCV"]
    s1_lpg = lpg * v["EF_LPG_NCV"]
    s1_nap = naphtha * v["EF_Naphtha_NCV"]
    s1_oth = other * v["EF_GasOil_NCV"]
    s1_stat = s1_gas + s1_lpg + s1_nap + s1_oth
    s1_tot = s1_stat + fleet_t
    s1_xn = s1_tot - s1_nap
    air_sector = v["Base_Air_C20_GHG"] + v["Base_Air_C21_GHG"] * inc21
    air_scaled = air_sector * ratio
    air_gap = air_scaled - s1_stat
    comb_share = s1_stat / air_scaled

    # Scope 2 (D-12): separate bases, never mixed
    s2_el_lb = elec * v["EF_GridLB"]
    s2_el_mb = elec * v["EF_ResidualMB"]
    s2_heat = heat * v["EF_HeatProxy"]
    s2_lb = s2_el_lb + s2_heat
    s2_mb = s2_el_mb + s2_heat
    s12_lb = s1_tot + s2_lb
    s12_mb = s1_tot + s2_mb

    carriers_sum = gas + elec + heat + lpg + naphtha + other
    ok_c = (remainder >= 0
            and abs(carriers_sum - total) <= v["Const_CheckTolerance"])
    return BaselineResult(
        firm_va_meur=firm_va, firm_turnover_meur=firm_to, firm_persons=firm_pers,
        sector_va_meur=sector_va, ratio_va=ratio, ratio_va_c20_only=ratio_c20,
        sector_turnover_meur=sector_to, ratio_turnover=ratio_to,
        sector_remainder_mwh=remainder, gasoil_share_of_remainder=gasoil_share,
        gas_mwh=gas, elec_mwh=elec, heat_mwh=heat, lpg_mwh=lpg,
        naphtha_mwh=naphtha, other_mwh=other, total_mwh=total,
        total_mwh_turnover_basis=total_to, fuel_mwh=fuel,
        fuel_load_mw=fuel_load, total_load_mw=total_load,
        below_ets1_threshold=below,
        elec_band=e_band, elec_band_code=e_code, elec_price_s1=e_s1,
        elec_price_s2=e_s2, elec_price=e_price, elec_price_2026s1=e_26,
        gas_gcv_per_ncv=g_per, gas_gj_gcv=gas_gj, gas_band=g_band,
        gas_band_code=g_code, gas_price_s1_gcv=g_s1, gas_price_s2_gcv=g_s2,
        gas_price_gcv=g_gcv, gas_price_ncv=g_ncv, gas_price_2026s1_gcv=g_26,
        elec_cost_eur=elec_cost, gas_cost_eur=gas_cost,
        fleet_km=km, fleet_litres=litres, fleet_l_per_100km=l100,
        fleet_mwh=fleet_mwh, fleet_t=fleet_t,
        s1_gas_t=s1_gas, s1_lpg_t=s1_lpg, s1_naphtha_t=s1_nap,
        s1_other_t=s1_oth, s1_stationary_t=s1_stat, s1_total_t=s1_tot,
        s1_excl_naphtha_t=s1_xn,
        air_sector_t=air_sector, air_scaled_t=air_scaled, air_gap_t=air_gap,
        combustion_share_of_air=comb_share,
        s2_elec_lb_t=s2_el_lb, s2_elec_mb_t=s2_el_mb, s2_heat_t=s2_heat,
        s2_lb_t=s2_lb, s2_mb_t=s2_mb, s12_lb_t=s12_lb, s12_mb_t=s12_mb,
        check_carriers="OK" if ok_c else "ERROR",
        check_ratio="OK" if 0 < ratio <= 1 else "ERROR",
    )
