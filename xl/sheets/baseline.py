"""Baseline sheet: firm size -> scaling -> energy -> Scope 1 and 2 (plan 02-09).

Every cell is a live formula on named Inputs; cached values come from the
independent reference model (checkmodel.baseline_reference.compute_baseline).
Location-based (column D) and market-based (column E) Scope 2 are never added.
"""
from dataclasses import dataclass
from typing import Tuple

from checkmodel.baseline_reference import compute_baseline, model_values
from xl.layout import LABEL_COL, UNIT_COL, setup_sheet
from xl.sheets.common import write_title_band
from xl.styles import SheetKind, apply_check_format

LB_COL = 3
MB_COL = 4
NOTE_COL = 5
LAST_COL = 11
COLS = "ABCDEFGHIJKL"

ELEC_BLOCKS = (("Rng_ElecLower", "Price_ElecLower_", "IA", "IG"),
               ("Rng_ElecS1", "Price_ElecS1_", "IA", "IG"),
               ("Rng_ElecS2", "Price_ElecS2_", "IA", "IG"),
               ("Rng_Elec26S1", "Price_Elec26S1_", "IA", "IG"))
GAS_BLOCKS = (("Rng_GasLower", "Price_GasLower_", "I1", "I6"),
              ("Rng_GasS1", "Price_GasS1_", "I1", "I6"),
              ("Rng_GasS2", "Price_GasS2_", "I1", "I6"),
              ("Rng_Gas26S1", "Price_Gas26S1_", "I1", "I6"))
ELEC_CODES = ("IA", "IB", "IC", "ID", "IE", "IF", "IG")
GAS_CODES = ("I1", "I2", "I3", "I4", "I5", "I6")

SCOPE3_TEXT = (
    "Excluded: no official sector-level Scope 3 intensity for Belgian "
    "chemicals was found; Eurostat footprints are by final-demand product, not "
    "firm Scope 3, and no synthetic figure is used (D-13). A firm inventory "
    "would need purchased goods and transport activity data.")
LIMIT_D06 = (
    "Limitation (D-06): the Belgian C20 + C21 average is dominated by large "
    "petrochemical and pharmaceutical sites, so a medium household-products "
    "firm's derived energy intensity is probably overstated; no unsourced "
    "size adjustment is applied.")
LIMIT_NAPHTHA = (
    "Limitation: naphtha is a sector-specific petrochemical fuel and is "
    "not addressable by the Phase 3 measures; it is kept so the baseline "
    "follows the energy balance (D-06).")


@dataclass(frozen=True)
class BaselineLayout:
    rows: Tuple[Tuple[str, int], ...]  # (key, zero-based row)
    lb_col: int = LB_COL
    mb_col: int = MB_COL


def _band_range(inputs_layout, prefix, first, last, codes):
    rows = dict(inputs_layout.record_rows)
    idx = [rows[prefix + c] for c in codes[codes.index(first):
                                          codes.index(last) + 1]]
    if idx != list(range(idx[0], idx[0] + len(idx))):
        raise ValueError("band block %s is not on consecutive Inputs rows"
                         % prefix)
    return "=Inputs!$G$%d:$G$%d" % (idx[0] + 1, idx[-1] + 1)


def _wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word) if cur else word
    if cur:
        lines.append(cur)
    return lines


class _Sheet(object):
    def __init__(self, ws, cells, styles):
        self.ws, self.cells, self.styles = ws, cells, styles
        self.r = 4  # header row index; incremented before use
        self.keys = []
        self.ex = {}  # key -> excel row number

    def next(self, key=None):
        self.r += 1
        if key:
            self.keys.append((key, self.r))
            self.ex[key] = self.r + 1
        return self.r

    def section(self, title, d=None, e=None):
        self.r += 1
        sec = self.styles.get("section")
        self.cells.text(self.ws, self.r, LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            self.cells.blank(self.ws, self.r, c, sec)
        if d:
            self.cells.text(self.ws, self.r, LB_COL, d, sec)
        if e:
            self.cells.text(self.ws, self.r, MB_COL, e, sec)

    def label(self, r, label, unit, note=None):
        self.cells.text(self.ws, r, LABEL_COL, label, self.styles.get("label"))
        if unit:
            self.cells.text(self.ws, r, UNIT_COL, unit, self.styles.get("unit"))
        if note:
            self.cells.text(self.ws, r, NOTE_COL, note, self.styles.get("note"))

    def f(self, r, col, formula, value, num, link=False, name=None):
        role = "link" if link else "calc"
        self.cells.formula(self.ws, r, col, formula,
                           self.styles.get(role, num), value=value)
        if name:
            cells = self.cells
            cells.define_name(name, "=Baseline!$%s$%d" % (COLS[col], r + 1))

    def line(self, label, unit, formula, value, num, *, key=None, name=None,
             link=False, note=None):
        r = self.next(key)
        self.label(r, label, unit, note)
        self.f(r, LB_COL, formula, value, num, link, name)
        return r + 1

    def line2(self, label, unit, d, e, num, *, key=None, dname=None,
              ename=None, dlink=False, note=None):
        """d and e are (formula, value) pairs; E is the firm column."""
        r = self.next(key)
        self.label(r, label, unit, note)
        self.f(r, LB_COL, d[0], d[1], num, dlink, dname)
        self.f(r, MB_COL, e[0], e[1], num, False, ename)
        return r + 1

    def text_block(self, text, role="note"):
        for part in _wrap(text, 120):
            r = self.next()
            self.cells.text(self.ws, r, LABEL_COL, part, self.styles.get(role))


def build_baseline(wb, styles, cells, dataset, cfg, inputs_layout):
    v = model_values(dataset.inputs)
    x = compute_baseline(v)
    ws = wb.add_worksheet("Baseline")
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=4)
    write_title_band(
        cells, styles, ws, "Baseline",
        "Maison Veritas baseline derived from Belgian NACE C20 Eurostat "
        "statistics, reference year 2024",
        "Units on every row; MWh on a net calorific value (NCV) basis; tCO2e; "
        "EUR 2025", LAST_COL)
    hdr = styles.get("header")
    for c, t in ((LABEL_COL, "Item"), (UNIT_COL, "Unit"), (LB_COL, "Value"),
                 (MB_COL, "Firm / MB"), (NOTE_COL, "Basis / note")):
        cells.text(ws, 4, c, t, hdr)

    for name, prefix, a, b in ELEC_BLOCKS:
        cells.define_name(name, _band_range(inputs_layout, prefix, a, b,
                                            ELEC_CODES))
    for name, prefix, a, b in GAS_BLOCKS:
        cells.define_name(name, _band_range(inputs_layout, prefix, a, b,
                                            GAS_CODES))

    s = _Sheet(ws, cells, styles)
    L = s.line

    # 1 Firm size
    s.section("Firm size (Eurostat SBS, NACE C20, 50-249 persons, 2024)")
    ent = L("Enterprises in size class", "enterprises", "=Base_SBS_C20M_Ent",
            v["Base_SBS_C20M_Ent"], "count", link=True)
    ppl = L("Persons employed in size class", "persons",
            "=Base_SBS_C20M_Persons", v["Base_SBS_C20M_Persons"], "count",
            link=True)
    va = L("Value added in size class", "EUR m", "=Base_SBS_C20M_VA",
           v["Base_SBS_C20M_VA"], "eur_m", link=True)
    to = L("Turnover in size class", "EUR m", "=Base_SBS_C20M_Turnover",
           v["Base_SBS_C20M_Turnover"], "eur_m", link=True)
    L("Firm value added", "EUR m", "=D%d/D%d" % (va, ent), x.firm_va_meur,
      "dec2", name="BL_FirmVA", note="class total / enterprises (D-02)")
    L("Firm turnover", "EUR m", "=D%d/D%d" % (to, ent), x.firm_turnover_meur,
      "dec2", key="firm_to")
    L("Persons per enterprise", "persons", "=D%d/D%d" % (ppl, ent),
      x.firm_persons, "dec2")

    # 2 Scaling
    s.section("Scaling ratio (value added, D-03)")
    L("Sector value added (C20 + C21)", "EUR m",
      "=Base_SBS_C20_VA+Base_SBS_C21_VA*Base_NRG_IncludesC21", x.sector_va_meur,
      "eur_m", name="BL_SectorVA",
      note="energy balance covers C20 + C21 (D-39)")
    L("Scaling ratio, firm / sector (value added)", "factor",
      "=BL_FirmVA/BL_SectorVA", x.ratio_va, "dec5", name="BL_RatioVA")
    L("Memo: C20-only ratio", "factor", "=BL_FirmVA/Base_SBS_C20_VA",
      x.ratio_va_c20_only, "dec5",
      note="memo only: energy balance covers C20 + C21 (D-39)")
    sto = L("Memo: sector turnover (C20 + C21)", "EUR m",
            "=Base_SBS_C20_Turnover+Base_SBS_C21_Turnover*Base_NRG_IncludesC21",
            x.sector_turnover_meur, "eur_m")
    L("Memo: turnover-based ratio", "factor",
      "=D%d/D%d" % (s.ex["firm_to"], sto), x.ratio_turnover, "dec5",
      name="BL_RatioTurnover", note="memo cross-check only (D-03)")

    # 3 Energy by carrier
    s.section("Energy by carrier (nrg_bal_c, final energy use, MWh NCV)",
              "Sector", "Firm")
    carriers = (
        ("Natural gas", "Base_NRG_Gas", x.gas_mwh, "BL_Gas_MWh", None),
        ("Electricity", "Base_NRG_Elec", x.elec_mwh, "BL_Elec_MWh", None),
        ("Derived heat", "Base_NRG_Heat", x.heat_mwh, "BL_Heat_MWh", None),
        ("LPG", "Base_NRG_LPG", x.lpg_mwh, "BL_LPG_MWh", None),
        ("Naphtha", "Base_NRG_Naphtha", x.naphtha_mwh, "BL_Naphtha_MWh",
         "sector-specific petrochemical fuel, not addressable by the Phase 3 "
         "measures; kept per D-06"),
    )
    for label, nm, firm, bl, note in carriers:
        r = s.next()
        s.label(r, label, "MWh", note)
        s.f(r, LB_COL, "=" + nm, v[nm], "mwh", True)
        s.f(r, MB_COL, "=D%d*BL_RatioVA" % (r + 1), firm, "mwh", False, bl)
    rem = s.next("rem")
    s.label(rem, "Other fuels (remainder)", "MWh",
            "total less listed carriers")
    s.f(rem, LB_COL, "=Base_NRG_Total-(Base_NRG_Gas+Base_NRG_Elec+Base_NRG_Heat"
        "+Base_NRG_LPG+Base_NRG_Naphtha)", x.sector_remainder_mwh, "mwh")
    s.f(rem, MB_COL, "=D%d*BL_RatioVA" % (rem + 1), x.other_mwh, "mwh", False,
        "BL_Other_MWh")
    L("Gas oil as share of remainder", "factor",
      "=Base_NRG_GasOil/D%d" % (rem + 1), x.gasoil_share_of_remainder, "dec3",
      note="remainder is treated as gas oil for emissions (D-11)")
    tot = s.next("tot")
    s.label(tot, "Total final energy use", "MWh")
    s.f(tot, LB_COL, "=Base_NRG_Total", v["Base_NRG_Total"], "mwh", True)
    s.f(tot, MB_COL, "=D%d*BL_RatioVA" % (tot + 1), x.total_mwh, "mwh", False,
        "BL_Total_MWh")
    L("Memo: total using turnover ratio", "MWh",
      "=Base_NRG_Total*BL_RatioTurnover", x.total_mwh_turnover_basis, "mwh",
      note="memo cross-check, not an alternative input (D-39)")

    # 4 Sanity
    s.section("Sanity: average thermal load (D-07)")
    fuel = L("Firm fuel use (gas, LPG, naphtha, other)", "MWh",
             "=BL_Gas_MWh+BL_LPG_MWh+BL_Naphtha_MWh+BL_Other_MWh", x.fuel_mwh,
             "mwh", key="fuel")
    L("Average fuel load", "MW", "=D%d/Const_HoursPerYear" % fuel,
      x.fuel_load_mw, "dec2", name="BL_FuelLoadMW")
    L("Average total load", "MW", "=BL_Total_MWh/Const_HoursPerYear",
      x.total_load_mw, "dec2")
    L("EU ETS1 combustion threshold", "MW", "=Carbon_ETS1_ThermalThresholdMW",
      v["Carbon_ETS1_ThermalThresholdMW"], "dec2", link=True)
    L("Average fuel load versus threshold", "text",
      '=IF(BL_FuelLoadMW<Carbon_ETS1_ThermalThresholdMW,"Below","At or above")',
      x.below_ets1_threshold, "general",
      note="average load is a lower bound on rated thermal input, not proof")

    # 5 Prices
    s.section("Energy prices (Eurostat X_VAT, 2025 average, D-21)")
    eb = L("Electricity band index", "index",
           "=MATCH(BL_Elec_MWh,Rng_ElecLower,1)", x.elec_band, "int",
           name="BL_ElecBand", note="largest band lower bound not above "
           "annual consumption")
    L("Electricity band code", "code",
      '=CHOOSE(BL_ElecBand,"IA","IB","IC","ID","IE","IF","IG")',
      x.elec_band_code, "general")
    e1 = L("Electricity price 2025-S1", "EUR/MWh",
           "=INDEX(Rng_ElecS1,BL_ElecBand)", x.elec_price_s1, "eur2")
    e2 = L("Electricity price 2025-S2", "EUR/MWh",
           "=INDEX(Rng_ElecS2,BL_ElecBand)", x.elec_price_s2, "eur2")
    L("Electricity price, 2025 average", "EUR/MWh",
      "=AVERAGE(D%d,D%d)" % (e1, e2), x.elec_price, "eur2",
      name="BL_ElecPrice")
    L("Context: electricity price 2026-S1", "EUR/MWh",
      "=INDEX(Rng_Elec26S1,BL_ElecBand)", x.elec_price_2026s1, "eur2",
      note="context only, not used")
    L("Gas GCV per NCV", "factor", "=EF_Gas_NCV/EF_Gas_GCV", x.gas_gcv_per_ncv,
      "dec5", name="BL_GasGCVperNCV",
      note="DESNZ factor ratio converts GCV to NCV (D-08)")
    L("Gas consumption on a GCV basis", "GJ",
      "=BL_Gas_MWh*Const_GJ_per_MWh*BL_GasGCVperNCV", x.gas_gj_gcv, "count",
      name="BL_GasGJ_GCV")
    L("Gas band index", "index", "=MATCH(BL_GasGJ_GCV,Rng_GasLower,1)",
      x.gas_band, "int", name="BL_GasBand")
    L("Gas band code", "code",
      '=CHOOSE(BL_GasBand,"I1","I2","I3","I4","I5","I6")', x.gas_band_code,
      "general")
    g1 = L("Gas price 2025-S1 (GCV)", "EUR/MWh",
           "=INDEX(Rng_GasS1,BL_GasBand)", x.gas_price_s1_gcv, "eur2")
    g2 = L("Gas price 2025-S2 (GCV)", "EUR/MWh",
           "=INDEX(Rng_GasS2,BL_GasBand)", x.gas_price_s2_gcv, "eur2")
    ga = L("Gas price, 2025 average (GCV)", "EUR/MWh",
           "=AVERAGE(D%d,D%d)" % (g1, g2), x.gas_price_gcv, "eur2")
    L("Gas price, 2025 average (NCV)", "EUR/MWh",
      "=D%d*BL_GasGCVperNCV" % ga, x.gas_price_ncv, "eur2",
      name="BL_GasPriceNCV")
    L("Context: gas price 2026-S1 (GCV)", "EUR/MWh",
      "=INDEX(Rng_Gas26S1,BL_GasBand)", x.gas_price_2026s1_gcv, "eur2",
      note="context only, not used")
    L("Annual electricity cost (context)", "EUR 2025",
      "=BL_Elec_MWh*BL_ElecPrice", x.elec_cost_eur, "eur")
    L("Annual gas cost (context)", "EUR 2025",
      "=BL_Gas_MWh*BL_GasPriceNCV", x.gas_cost_eur, "eur")

    # 6 Fleet
    s.section("Fleet block (Analyst assumption for vehicle count and distance, D-10)")
    nv = L("Vehicles (analyst assumption)", "vehicles", "=Base_Fleet_Vehicles",
           v["Base_Fleet_Vehicles"], "count", link=True)
    kv = L("Distance per vehicle (analyst assumption)", "km/yr",
           "=Base_Fleet_KmPerVehicle", v["Base_Fleet_KmPerVehicle"], "count",
           link=True)
    gk = L("Fleet CO2 per km (EEA new vans 2024)", "gCO2/km",
           "=Base_Fleet_gCO2PerKm", v["Base_Fleet_gCO2PerKm"], "dec2",
           link=True)
    km = L("Fleet distance", "km/yr", "=Base_Fleet_Vehicles*"
           "Base_Fleet_KmPerVehicle", x.fleet_km, "count", name="BL_Fleet_km")
    lit = L("Diesel use", "l/yr",
            "=D%d*Base_Fleet_gCO2PerKm/Const_g_per_kg/EF_Diesel_l" % km,
            x.fleet_litres, "count", name="BL_Fleet_Litres")
    L("Implied consumption", "l/100 km",
      "=D%d/D%d*Const_km_per_100km" % (lit, km), x.fleet_l_per_100km, "dec2")
    L("Fleet diesel energy", "MWh",
      "=D%d*(EF_Diesel_l/EF_Diesel_NCV)/Const_kWh_per_MWh" % lit,
      x.fleet_mwh, "mwh", name="BL_Fleet_MWh")
    L("Fleet emissions", "tCO2e",
      "=D%d*EF_Diesel_l/Const_kg_per_t" % lit, x.fleet_t, "tco2e",
      name="BL_Fleet_t")
    del nv, kv, gk

    # 7 Scope 1
    s.section("Scope 1 (combustion only, DESNZ net CV factors, D-11)")
    a = L("Natural gas", "tCO2e", "=BL_Gas_MWh*EF_Gas_NCV", x.s1_gas_t,
          "tco2e")
    b = L("LPG", "tCO2e", "=BL_LPG_MWh*EF_LPG_NCV", x.s1_lpg_t, "tco2e")
    c = L("Naphtha", "tCO2e", "=BL_Naphtha_MWh*EF_Naphtha_NCV", x.s1_naphtha_t,
          "tco2e", note="flagged: petrochemical fuel, not addressable (D-06)")
    d = L("Other fuels (gas oil proxy)", "tCO2e", "=BL_Other_MWh*EF_GasOil_NCV",
          x.s1_other_t, "tco2e")
    L("Stationary combustion", "tCO2e", "=SUM(D%d:D%d)" % (a, d),
      x.s1_stationary_t, "tco2e", name="BL_Scope1Stationary")
    L("Fleet", "tCO2e", "=BL_Fleet_t", x.fleet_t, "tco2e")
    L("Scope 1 total", "tCO2e", "=BL_Scope1Stationary+BL_Fleet_t",
      x.s1_total_t, "tco2e", name="BL_Scope1")
    L("Memo: Scope 1 excluding naphtha", "tCO2e", "=BL_Scope1-D%d" % c,
      x.s1_excl_naphtha_t, "tco2e")
    del b

    # 8 Cross-check
    s.section("Cross-check: Eurostat air emissions accounts "
              "(env_ac_ainah_r2, GHG)")
    sec = L("Sector GHG (C20 + C21)", "tCO2e",
            "=Base_Air_C20_GHG+Base_Air_C21_GHG*Base_NRG_IncludesC21",
            x.air_sector_t, "tco2e")
    sc = L("Scaled to firm (same value-added ratio)", "tCO2e",
           "=D%d*BL_RatioVA" % sec, x.air_scaled_t, "tco2e")
    L("Gap: scaled accounts less stationary combustion", "tCO2e",
      "=D%d-BL_Scope1Stationary" % sc, x.air_gap_t, "tco2e")
    L("Combustion as share of scaled accounts", "%",
      "=BL_Scope1Stationary/D%d" % sc, x.combustion_share_of_air, "pct",
      note="not forced to reconcile")
    s.text_block(
        "The accounts include process emissions (e.g. ammonia, nitric acid "
        "N2O) and other gases a household-products firm would not have; not "
        "forced to reconcile; 2024 value imputed by Eurostat (flag i).")

    # 9 Scope 2
    s.section("Scope 2 (purchased electricity and heat, D-12)",
              "Location-based (LB)", "Market-based (MB)")
    fr = s.r + 1
    cells.tag("Baseline", fr, LB_COL, fr + 3, LB_COL, "LB")
    cells.tag("Baseline", fr, MB_COL, fr + 3, MB_COL, "MB")
    r = s.next("s2_factor")
    s.label(r, "Grid emission factor", "tCO2e/MWh",
            "LB: national grid; MB: residual mix")
    s.f(r, LB_COL, "=EF_GridLB", v["EF_GridLB"], "dec5", True)
    s.f(r, MB_COL, "=EF_ResidualMB", v["EF_ResidualMB"], "dec5", True)
    r = s.next("s2_elec")
    s.label(r, "Purchased electricity", "tCO2e")
    s.f(r, LB_COL, "=BL_Elec_MWh*D%d" % (r), x.s2_elec_lb_t, "tco2e")
    s.f(r, MB_COL, "=BL_Elec_MWh*E%d" % (r), x.s2_elec_mb_t, "tco2e")
    r = s.next("s2_heat")
    s.label(r, "Purchased heat", "tCO2e",
            "UK proxy, same under both bases")
    s.f(r, LB_COL, "=BL_Heat_MWh*EF_HeatProxy", x.s2_heat_t, "tco2e")
    s.f(r, MB_COL, "=BL_Heat_MWh*EF_HeatProxy", x.s2_heat_t, "tco2e")
    r = s.next("s2_tot")
    s.label(r, "Scope 2 total", "tCO2e")
    s.f(r, LB_COL, "=SUM(D%d:D%d)" % (r - 1, r), x.s2_lb_t, "tco2e", False,
        "BL_S2_LB")
    s.f(r, MB_COL, "=SUM(E%d:E%d)" % (r - 1, r), x.s2_mb_t, "tco2e", False,
        "BL_S2_MB")
    cells.tag_name("EF_GridLB", "LB")
    cells.tag_name("EF_ResidualMB", "MB")
    cells.tag_name("BL_S2_LB", "LB")
    cells.tag_name("BL_S2_MB", "MB")
    s.text_block(
        "LB and MB are alternative reporting bases: they are never added "
        "(GHG Protocol Scope 2 dual reporting). MB assumes no existing "
        "renewable contract (analyst assumption)")

    # 10 Scope 1 + 2
    s.section("Scope 1 + 2 by basis", "Location-based (LB)",
              "Market-based (MB)")
    r = s.next("s12")
    cells.tag("Baseline", r, LB_COL, r, LB_COL, "LB")
    cells.tag("Baseline", r, MB_COL, r, MB_COL, "MB")
    s.label(r, "Scope 1 + 2", "tCO2e", "one total per basis")
    s.f(r, LB_COL, "=BL_Scope1+BL_S2_LB", x.s12_lb_t, "tco2e", False,
        "BL_S12_LB")
    s.f(r, MB_COL, "=BL_Scope1+BL_S2_MB", x.s12_mb_t, "tco2e", False,
        "BL_S12_MB")
    cells.tag_name("BL_S12_LB", "LB")
    cells.tag_name("BL_S12_MB", "MB")

    # 11/12 Scope 3 and limitations
    s.section("Scope 3")
    s.text_block(SCOPE3_TEXT)
    s.section("Limitations")
    s.text_block(LIMIT_D06)
    s.text_block(LIMIT_NAPHTHA)

    # 13 Checks
    s.section("Checks")
    r1 = s.next("chk_carriers")
    s.label(r1, "Carriers sum to total and remainder not negative", "check")
    s.f(r1, LB_COL,
        '=IF(AND(D%d>=0,ABS((BL_Gas_MWh+BL_Elec_MWh+BL_Heat_MWh+BL_LPG_MWh'
        '+BL_Naphtha_MWh+BL_Other_MWh)-BL_Total_MWh)<=Const_CheckTolerance),'
        '"OK","ERROR")' % (rem + 1), x.check_carriers, "general")
    r2 = s.next("chk_ratio")
    s.label(r2, "Scaling ratio between 0 and 1", "check")
    s.f(r2, LB_COL, '=IF(AND(BL_RatioVA>0,BL_RatioVA<=1),"OK","ERROR")',
        x.check_ratio, "general")
    apply_check_format(ws, styles, r1, LB_COL, r2, LB_COL)
    return BaselineLayout(tuple(s.keys))
