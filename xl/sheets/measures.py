"""Measures sheet, engine half (plan 03-07): timeline band, electricity stack
with cap checks and six identically structured measure blocks up to the eight
D-03 cash-flow rows.

Every cell is a live formula on named Inputs or Baseline/Carbon cells. Cached
values come from checkmodel.measures_reference (D-27); this module never
computes a result itself. Results rows (NPV, IRR, payback, abatement cost) are
added in plan 03-08 on top of the rows allocated here.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

from xl.selector import selector_state
from checkmodel import appraisal as ap
from checkmodel.baseline_reference import model_values
from checkmodel.measures_reference import (
    DEFAULT_STATE, SCENARIOS_UI, compute_measures)
from config.measures_catalog import COUNTERFACTUAL_NOTE, MEASURES
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter,
    setup_sheet)
from xl.sheets.common import get_or_add, write_title_band
from xl.styles import SheetKind, apply_bool_check_format

SHEET = "Measures"
LAST_COL = TIMELINE_LAST_COL
HDR_ROW = 4  # zero-based; Excel row 5
SCALAR_COL = 3  # column D
NOTE_COL = 4  # column E
SUMMARY_HEIGHT = 14  # title, header, six measures, blank, 3 portfolio rows,
# market-based note, M_Check_All
NYEARS = TIMELINE_LAST_COL - TIMELINE_FIRST_COL + 1

TITLE_NOTE = (
    "Pre-tax, ex-VAT, real EUR 2025 (D-04). + = benefit to the firm. Heat "
    "pump and fleet use incremental capex over the boiler / diesel van the "
    "firm would buy anyway; LED, VSD and PV are full-cost retrofits; the "
    "contract has no capex (D-05)")
SIGN_NOTE = (
    "Year 0 (the first model year) carries the investment, undiscounted; "
    "operating flows start in year 1. Physical rows: + = more purchased "
    "energy than the baseline, - = less. Location-based and market-based "
    "tonnes are both shown and are never added together (D-14)")

SIZING = {
    "LED": ("kwh", "units"),
    "VSD": ("kwh", "units"),
    "HP": ("lowshare", "heat", "kw", "indirect"),
    "Fleet": ("vehicles",),
    "PV": ("size", "roof", "peak"),
    "RC": ("rcnote",),
}  # type: Dict[str, Tuple[str, ...]]
SCALAR_KEYS = ("capex", "fullcapex", "life", "sub", "resfrac", "om")
FLAG_KEYS = ("init", "repl")
PHYS_KEYS = ("dE", "dG", "dD", "cov", "tLB", "tMB", "tSel")
MONEY_KEYS = ("m_capex", "m_sub", "m_res", "m_om", "m_eE", "m_eG", "m_eD",
              "m_cf", "m_carbon", "m_cfi")
STACK_KEYS = ("s0", "s1", "s2", "s3", "s4", "s5", "red", "gas0", "gasA",
              "dsl0", "dslA", "hr_red", "hr_pv", "hr_cov",
              "chk_nonneg", "chk_red", "chk_pv", "chk_cov", "chk_gas",
              "chk_dsl")
RESULT_KEYS = (
    "r_band", "dcf", "cum", "cumd", "reach", "reachd", "sign", "chg",
    "npv", "npvmemo", "pvsub", "npvpre", "npvcarb", "capfac", "npvfull",
    "guess", "irr", "nchg", "irrflag", "first_s", "pay_s", "first_d", "pay_d",
    "pvlb", "pvmb", "pvsel", "avglb", "avgmb", "avgsel", "elig", "lev", "be",
    "chk_memo", "chk_be",
    "i_band", "levpre", "crf", "eqcap", "avgben", "eqt", "ann", "chk_ann",
    "chk_zero",
    "chk_irr")
TIMELINE_KEYS = ("tl_band", "idx", "op", "lastidx", "df", "pidx", "basisidx",
                 "scenidx", "cprice", "ef_lb", "ef_mb", "ef_sel")


@dataclass(frozen=True)
class MeasuresLayout:
    rows: Dict[str, int]  # timeline, derived and stack rows (zero-based)
    blocks: Dict[str, Dict[str, int]]  # per measure key: row map (zero-based)
    summary_first: int
    summary_height: int
    check_names: Tuple[str, ...]
    summary: Dict[str, int]


def allocate_rows():
    # type: () -> Tuple[Dict[str, int], Dict[str, Dict[str, int]], int]
    """Pure row allocation (zero-based) so forward references are known.

    Returns (shared rows, per-block row maps, first row after the last block).
    """
    rows = {"note1": HDR_ROW + 1, "note2": HDR_ROW + 2}
    r = HDR_ROW + 4
    rows["sum_band"] = r
    r += SUMMARY_HEIGHT + 1
    for k in TIMELINE_KEYS:
        rows[k] = r
        r += 1
    r += 1
    rows["der_band"] = r
    rows["dieselex"] = r + 1
    r += 3
    rows["stack_band"] = r
    r += 1
    for k in STACK_KEYS:
        rows[k] = r
        r += 1
    r += 1
    blocks = {}  # type: Dict[str, Dict[str, int]]
    for ms in MEASURES:
        m = {"band": r}
        r += 1
        for k in SIZING[ms.key] + SCALAR_KEYS + FLAG_KEYS + PHYS_KEYS \
                + MONEY_KEYS + RESULT_KEYS:
            m[k] = r
            r += 1
        blocks[ms.key] = m
        r += 1  # blank row between blocks
    return rows, blocks, r


class _Writer(object):
    def __init__(self, ws, cells, styles):
        self.ws, self.cells, self.styles = ws, cells, styles

    def band(self, r, title):
        sec = self.styles.get("section")
        self.cells.text(self.ws, r, LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            self.cells.blank(self.ws, r, c, sec)

    def line(self, r, text, unit=""):
        self.cells.text(self.ws, r, LABEL_COL, text, self.styles.get("label"))
        if unit:
            self.cells.text(self.ws, r, UNIT_COL, unit,
                            self.styles.get("unit"))

    def note(self, r, text, col=NOTE_COL):
        self.cells.text(self.ws, r, col, text, self.styles.get("note"))

    def scalar(self, r, f, value, num, link=False, name=None):
        role = "link" if link else "calc"
        self.cells.formula(self.ws, r, SCALAR_COL, f,
                           self.styles.get(role, num), value=value)
        if name:
            cells = self.cells
            cells.define_name(name, "=%s!$D$%d" % (SHEET, r + 1))

    def series(self, r, fn, values, num, link=False, name=None, tag=None):
        role = "link" if link else "calc"
        fmt = self.styles.get(role, num)
        for k in range(NYEARS):
            cl = col_letter(TIMELINE_FIRST_COL + k)
            self.cells.formula(self.ws, r, TIMELINE_FIRST_COL + k,
                               fn(k, cl), fmt, value=values[k])
        if name:
            cells = self.cells
            cells.define_name(name, "=%s!$%s$%d:$%s$%d" % (
                SHEET, col_letter(TIMELINE_FIRST_COL), r + 1,
                col_letter(TIMELINE_LAST_COL), r + 1))
            if tag:
                cells.tag_name(name, tag)


def _a(cl, row):
    return "%s$%d" % (cl, row + 1)


def _d(row):
    return "$D$%d" % (row + 1)


def _rng(row_a, row_b=None):
    row_b = row_a if row_b is None else row_b
    return "$%s$%d:$%s$%d" % (col_letter(TIMELINE_FIRST_COL), row_a + 1,
                              col_letter(TIMELINE_LAST_COL), row_b + 1)


def _ints(xs):
    return [int(x) for x in xs]


def build_measures(wb, styles, cells, dataset, cfg, layouts):
    ref = compute_measures(dataset.inputs, *selector_state(dataset))
    state = selector_state(dataset)
    mvals = dict(model_values(dataset.inputs))
    rows, blocks, _end = allocate_rows()
    carbon_rows = dict(layouts["carbon"].rows)
    ny = len(ref.years)
    if ny != NYEARS:
        raise ValueError("timeline length mismatch")

    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=HDR_ROW)
    write_title_band(
        cells, styles, ws, "Measures",
        "Six decarbonisation measures appraised on one 2026-2055 timeline",
        TITLE_NOTE, LAST_COL)
    w = _Writer(ws, cells, styles)
    hdr = styles.get("header")
    cells.text(ws, HDR_ROW, LABEL_COL, "Item", hdr)
    cells.text(ws, HDR_ROW, UNIT_COL, "Unit", hdr)
    yr = styles.get("header_year", "year")
    c0 = TIMELINE_FIRST_COL
    cells.formula(ws, HDR_ROW, c0, "=Time_FirstYear", yr, value=ref.years[0])
    for k in range(1, ny):
        cells.formula(ws, HDR_ROW, c0 + k,
                      "=%s%d+1" % (col_letter(c0 + k - 1), HDR_ROW + 1),
                      yr, value=ref.years[k])
    hdr_ref = HDR_ROW + 1
    w.note(rows["note1"], COUNTERFACTUAL_NOTE, LABEL_COL)
    w.note(rows["note2"], SIGN_NOTE, LABEL_COL)

    # Register LB/MB tags before any formula that reads those rows (lint).
    for k, tag in (("ef_lb", "LB"), ("ef_mb", "MB")):
        cells.tag(SHEET, rows[k], TIMELINE_FIRST_COL, rows[k],
                  TIMELINE_LAST_COL, tag)
    for key, m in blocks.items():
        for k, tag in (("tLB", "LB"), ("tMB", "MB")):
            cells.tag(SHEET, m[k], TIMELINE_FIRST_COL, m[k],
                      TIMELINE_LAST_COL, tag)

    # --- timeline band (D-01, D-14, D-16)
    R = rows
    w.band(R["tl_band"], "Shared timeline, discounting, prices and emission "
           "factors")
    w.line(R["idx"], "Year index n", "index")
    w.series(R["idx"], lambda k, c: "=%s$%d-Time_FirstYear" % (c, hdr_ref),
             list(range(ny)), "int", name="M_Idx")
    w.line(R["op"], "Operating flag (1 from year 1)", "flag (1/0)")
    w.series(R["op"], lambda k, c: "=IF(%s>=1,1,0)" % _a(c, R["idx"]),
             _ints(ref.op), "int", name="M_Op")
    w.line(R["lastidx"], "Last year index", "index")
    w.scalar(R["lastidx"], "=MAX(%s)" % _rng(R["idx"]), ny - 1, "int",
             name="M_LastIdx")
    w.line(R["df"], "Discount factor 1/(1+r)^n (real rate)", "factor")
    w.series(R["df"], lambda k, c: "=1/(1+Rate_DiscountReal)^%s"
             % _a(c, R["idx"]), ref.df, "dec5", name="M_DF")
    w.line(R["pidx"], "Real energy price index (1+escalation)^n", "index")
    w.series(R["pidx"], lambda k, c: "=(1+Price_RealEscalation)^%s"
             % _a(c, R["idx"]), ref.price_idx, "factor", name="M_PriceIdx")
    w.line(R["basisidx"], "Basis index (1 = location-based, 2 = "
           "market-based)", "index")
    basis_i = 2 if state[0] == "Market-based" else 1
    w.scalar(R["basisidx"], "=MATCH(Sel_Basis,List_Basis,0)", basis_i, "int",
             link=True, name="M_BasisIdx")
    w.line(R["scenidx"], "Scenario index (1 Low, 2 Central, 3 High)", "index")
    scen_i = SCENARIOS_UI.index(state[1]) + 1
    w.scalar(R["scenidx"], "=MATCH(Sel_Scenario,List_Scenario,0)", scen_i,
             "int", link=True, name="M_ScenIdx")
    w.line(R["cprice"], "Selected carbon price (shadow price lens)",
           "EUR/tCO2e")
    cp, ndc, nz = (carbon_rows["Path_Carbon_CP"] + 1,
                   carbon_rows["Path_Carbon_NDC"] + 1,
                   carbon_rows["Path_Carbon_NZ50"] + 1)
    w.series(R["cprice"], lambda k, c: "=CHOOSE(M_ScenIdx,Carbon!%s$%d,"
             "Carbon!%s$%d,Carbon!%s$%d)" % (c, cp, c, ndc, c, nz),
             ref.carbon, "eur2", link=True, name="M_CarbonPrice")
    w.line(R["ef_lb"], "Grid factor, location-based", "tCO2e/MWh")
    w.series(R["ef_lb"], lambda k, c: "=EF_GridLB*(1+EF_GridLB_Change)^%s"
             % _a(c, R["idx"]), ref.f_lb, "dec5", link=True, name="M_EF_LB",
             tag="LB")
    w.line(R["ef_mb"], "Residual mix factor, market-based (CO2 only)",
           "tCO2/MWh")
    w.series(R["ef_mb"], lambda k, c: "=EF_ResidualMB*(1+EF_ResidualMB_Change)"
             "^%s" % _a(c, R["idx"]), ref.f_mb, "dec5", link=True,
             name="M_EF_MB", tag="MB")
    w.line(R["ef_sel"], "Electricity factor, selected basis (display only)",
           "tCO2e/MWh (LB); tCO2/MWh (MB)")
    w.series(R["ef_sel"], lambda k, c: "=CHOOSE(M_BasisIdx,%s,%s)"
             % (_a(c, R["ef_lb"]), _a(c, R["ef_mb"])), ref.f_sel, "dec5",
             name="M_EF_Sel")
    w.note(R["ef_sel"], "display row: shows the factor in use; the tonnes "
           "rows compute LB and MB separately and select with CHOOSE",
           SCALAR_COL)

    # --- shared derived input
    w.band(R["der_band"], "Shared derived inputs")
    w.line(R["dieselex"], "Diesel price ex-VAT incl. excise", "EUR/l")
    w.scalar(R["dieselex"], "=Price_DieselBE_WithTax/(1+Price_DieselBE_VAT)",
             ref.diesel_exvat, "price4", link=True, name="M_DieselExVAT")
    w.note(R["dieselex"], "VAT recoverable, excise is a cost (D-11)")

    # --- electricity stack (D-13)
    ms_by = dict((m.key, m) for m in ref.measures)
    st = ref.stack
    B = blocks
    w.band(R["stack_band"], "Electricity stack (applied in this order: "
           "efficiency, electrification, solar, contract)")

    def stack_row(key, text, unit, fn, vals, name=None):
        w.line(R[key], text, unit)
        w.series(R[key], fn, vals, "mwh", name=name)

    stack_row("s0", "Purchased electricity, baseline", "MWh",
              lambda k, c: "=BL_Elec_MWh", st.s0, "M_Stack_S0")
    prev = "s0"
    for key, text, src, vals in (
            ("s1", "after LED", "LED", st.s1),
            ("s2", "after VSD", "VSD", st.s2),
            ("s3", "after heat pump load", "HP", st.s3),
            ("s4", "after fleet load", "Fleet", st.s4),
            ("s5", "after solar PV = residual purchased", "PV", st.s5)):
        stack_row(key, "Purchased electricity " + text, "MWh",
                  (lambda p, s: lambda k, c: "=%s+%s" % (
                      _a(c, R[p]), _a(c, B[s]["dE"])))(prev, src), vals,
                  "M_Stack_" + key.upper())
        prev = key
    red = [-(ms_by["LED"].d_elec[n] + ms_by["VSD"].d_elec[n]
             + ms_by["PV"].d_elec[n]) for n in range(ny)]
    stack_row("red", "Electricity reductions (LED + VSD + PV)", "MWh",
              lambda k, c: "=-(%s+%s+%s)" % (
                  _a(c, B["LED"]["dE"]), _a(c, B["VSD"]["dE"]),
                  _a(c, B["PV"]["dE"])), red, "M_Stack_Reductions")
    stack_row("gas0", "Gas, baseline", "MWh NCV", lambda k, c: "=BL_Gas_MWh",
              [ref.stack.gas_after[0] - ms_by["HP"].d_gas[0]] * ny)
    stack_row("gasA", "Gas after heat pump", "MWh NCV",
              lambda k, c: "=%s+%s" % (_a(c, R["gas0"]), _a(c, B["HP"]["dG"])),
              st.gas_after, "M_Stack_GasAfter")
    stack_row("dsl0", "Diesel, baseline", "litres",
              lambda k, c: "=BL_Fleet_Litres",
              [st.diesel_after[0] - ms_by["Fleet"].d_diesel[0]] * ny)
    stack_row("dslA", "Diesel after fleet", "litres",
              lambda k, c: "=%s+%s" % (_a(c, R["dsl0"]),
                                       _a(c, B["Fleet"]["dD"])),
              st.diesel_after, "M_Stack_DieselAfter")
    hr_red = [st.s0[n] - red[n] for n in range(ny)]
    stack_row("hr_red", "Headroom: baseline minus reductions", "MWh",
              lambda k, c: "=%s-%s" % (_a(c, R["s0"]), _a(c, R["red"])),
              hr_red)
    hr_pv = [st.s4[n] + ms_by["PV"].d_elec[n] for n in range(ny)]
    stack_row("hr_pv", "Headroom: purchased after electrification minus PV "
              "output", "MWh",
              lambda k, c: "=%s+%s" % (_a(c, R["s4"]), _a(c, B["PV"]["dE"])),
              hr_pv)
    hr_cov = [st.s5[n] - st.covered[n] for n in range(ny)]
    stack_row("hr_cov", "Headroom: residual purchased minus contract-covered",
              "MWh",
              lambda k, c: "=%s-%s" % (_a(c, R["s5"]), _a(c, B["RC"]["cov"])),
              hr_cov)

    check_names = []
    for key, name, text, f, val in (
            ("chk_nonneg", "M_Check_StackNonNeg",
             "Check: no stack step goes below zero",
             "=MIN(%s)>=0" % _rng(R["s1"], R["s5"]),
             min(list(st.s1) + list(st.s2) + list(st.s3) + list(st.s4)
                 + list(st.s5)) >= 0),
            ("chk_red", "M_Check_ElecReductionsCap",
             "Check: LED + VSD + PV never exceed baseline electricity",
             "=MIN(%s)>=0" % _rng(R["hr_red"]), min(hr_red) >= 0),
            ("chk_pv", "M_Check_PVSelfConsumed",
             "Check: PV output never exceeds electricity left to purchase",
             "=MIN(%s)>=0" % _rng(R["hr_pv"]), min(hr_pv) >= 0),
            ("chk_cov", "M_Check_ContractCap",
             "Check: contract never covers more than residual purchases",
             "=MIN(%s)>=0" % _rng(R["hr_cov"]), min(hr_cov) >= 0),
            ("chk_gas", "M_Check_GasCap",
             "Check: gas after heat pump is not negative",
             "=MIN(%s)>=0" % _rng(R["gasA"]), min(st.gas_after) >= 0),
            ("chk_dsl", "M_Check_DieselCap",
             "Check: diesel after fleet is not negative",
             "=MIN(%s)>=0" % _rng(R["dslA"]), min(st.diesel_after) >= 0)):
        w.line(R[key], text, "TRUE/FALSE")
        w.scalar(R[key], f, bool(val), "general", name=name)
        apply_bool_check_format(ws, styles, R[key], SCALAR_COL, R[key],
                                SCALAR_COL)
        check_names.append(name)

    # --- six measure blocks
    for ms in MEASURES:
        _write_block(w, ms, ms_by[ms.key], B[ms.key], R, B, ref, hdr_ref,
                     check_names, mvals)
    summary = _write_summary(w, ref, R, B, check_names)
    return MeasuresLayout(R, B, R["sum_band"], SUMMARY_HEIGHT,
                          tuple(check_names), summary)


def _write_block(w, ms, m, b, R, B, ref, hdr_ref, check_names, mv):
    key = ms.key
    ny = len(ref.years)
    zero = [0.0] * ny
    nm = lambda s: "M_%s_%s" % (key, s)  # noqa: E731
    D = _d
    w.band(b["band"], ms.name)

    # (b) measure-specific sizing rows (scalars in D)
    sz = m.sizing
    if key in ("LED", "VSD"):
        share, cov_, rate_, per_unit = (
            ("Meas_LED_LightingShare", "Meas_LED_Coverage",
             "Meas_LED_SavingRate", "Meas_LED_ZMSaving") if key == "LED" else
            ("Meas_VSD_MotorShare", "Meas_VSD_Coverage",
             "Meas_VSD_SavingRate", "Meas_VSD_Saving"))
        w.line(b["kwh"], "Electricity saved per year", "kWh/yr")
        w.scalar(b["kwh"], "=BL_Elec_MWh*Const_kWh_per_MWh*%s*%s*%s"
                 % (share, cov_, rate_), sz["kwh_saved"], "eur", link=True,
                 name=nm("kWhSaved"))
        w.line(b["units"], "Units installed", "units")
        w.scalar(b["units"], "=%s/%s" % (D(b["kwh"]), per_unit), sz["units"],
                 "eur", link=True, name=nm("Units"))
    elif key == "HP":
        w.line(b["lowshare"], "Low-temperature share of process heat",
               "fraction")
        w.scalar(b["lowshare"], "=Meas_HP_HeatLowPJ/(Meas_HP_HeatHighPJ+"
                 "Meas_HP_HeatMedPJ+Meas_HP_HeatLowPJ)", sz["low_share"],
                 "pct", link=True, name=nm("LowShare"))
        w.line(b["heat"], "Heat replaced per year", "MWh")
        w.scalar(b["heat"], "=BL_Gas_MWh*Meas_Boiler_Eff*%s" % D(b["lowshare"]),
                 sz["heat_mwh"], "mwh", link=True, name=nm("HeatMWh"))
        w.line(b["kw"], "Heat pump capacity", "kW")
        w.scalar(b["kw"], "=%s/Meas_HP_FullLoadHours*Const_kW_per_MW"
                 % D(b["heat"]), sz["kw"], "eur", link=True, name=nm("kW"))
        w.line(b["indirect"], "Indirect investment difference HP minus "
               "boiler (excluded from capex, D-06)", "EUR")
        w.scalar(b["indirect"], "=%s*(Meas_HP_IndirectCapex_HT-"
                 "Meas_Boiler_IndirectCapex)" % D(b["kw"]), m.indirect_diff,
                 "eur", link=True, name=nm("IndirectDiff"))
    elif key == "Fleet":
        w.line(b["vehicles"], "Vehicles replaced", "vehicles")
        w.scalar(b["vehicles"], "=Base_Fleet_Vehicles", sz["vehicles"],
                 "count", link=True, name=nm("Vehicles"))
    elif key == "PV":
        w.line(b["size"], "PV system size", "kWp")
        w.scalar(b["size"], "=Meas_PV_Size", sz["size_kwp"], "count",
                 link=True, name=nm("SizeKWp"))
        w.line(b["roof"], "Implied roof area (memo)", "m2")
        w.scalar(b["roof"], "=Meas_PV_Size*Meas_PV_RoofArea",
                 sz["roof_area_m2"], "count", link=True, name=nm("RoofM2"))
        w.line(b["peak"], "Check: PV peak output (MW) is below average "
               "electricity load (MW)", "TRUE/FALSE")
        w.scalar(b["peak"], "=Meas_PV_Size/Const_kW_per_MW<=BL_Elec_MWh/"
                 "Const_HoursPerYear", bool(sz["peak_ok"]), "general",
                 link=True, name="M_Check_PVPeakBelowLoad")
        apply_bool_check_format(w.ws, w.styles, b["peak"], SCALAR_COL,
                                b["peak"], SCALAR_COL)
        check_names.append("M_Check_PVPeakBelowLoad")
    else:  # RC
        w.line(b["rcnote"], "Covers residual purchased electricity after "
               "the stack (D-12)", "")

    # (c) identical scalar rows
    cap_f = {
        "LED": "=%s*Meas_LED_ZMCapex_EUR2025" % D(b.get("units", 0)),
        "VSD": "=%s*Meas_VSD_ZMCapex_EUR2025" % D(b.get("units", 0)),
        "HP": "=%s*(Meas_HP_Capex_HT-Meas_Boiler_Capex)" % D(b.get("kw", 0)),
        "Fleet": "=Base_Fleet_Vehicles*(Meas_Fleet_EVPremium+"
                 "Meas_Fleet_ChargerCapex)",
        "PV": "=Meas_PV_Size*Meas_PV_CapexDEA_EUR2025",
        "RC": "=0",
    }[key]
    w.line(b["capex"], "Capex, initial (incremental where a counterfactual "
           "exists)", "EUR")
    w.scalar(b["capex"], cap_f, m.capex, "eur", link=True, name=nm("Capex"))
    if key == "RC":
        w.note(b["capex"], "no capex (D-12)")
    w.line(b["fullcapex"], "Full capex (memo, D-05)", "EUR")
    if key == "HP":
        w.scalar(b["fullcapex"], "=%s*Meas_HP_Capex_HT" % D(b["kw"]),
                 m.full_capex, "eur", link=True, name=nm("FullCapex"))
    elif key == "Fleet":
        w.scalar(b["fullcapex"], "=Base_Fleet_Vehicles*(Meas_Fleet_"
                 "DieselVanPrice+Meas_Fleet_EVPremium+Meas_Fleet_ChargerCapex)",
                 m.full_capex, "eur", link=True, name=nm("FullCapex"))
    else:
        w.cells.text(w.ws, b["fullcapex"], SCALAR_COL,
                     "n/a (no counterfactual purchase)",
                     w.styles.get("note"))
    life_name = {"LED": "Meas_LED_Life", "VSD": "Meas_VSD_Life",
                 "HP": "Meas_HP_Life_HT", "Fleet": "Meas_Fleet_Life",
                 "PV": "Meas_PV_Life", "RC": "Meas_RC_Term"}[key]
    w.line(b["life"], "Lifetime", "years")
    w.scalar(b["life"], "=" + life_name, m.life, "count", link=True,
             name=nm("Life"))
    w.line(b["sub"], "Subsidy, share of initial capex", "fraction")
    w.scalar(b["sub"], "=Meas_%s_Subsidy" % key, m.subsidy_frac, "pct",
             link=True, name=nm("SubsidyFrac"))
    life = D(b["life"])
    w.line(b["resfrac"], "Residual value fraction at end of horizon",
           "fraction")
    w.scalar(b["resfrac"], "=IF(MOD(M_LastIdx,{l})=0,0,({l}-MOD(M_LastIdx,"
             "{l}))/{l})".format(l=life), m.res_frac, "pct",
             name=nm("ResFrac"))
    om_f = {
        "LED": "=0", "VSD": "=0",
        "HP": "=-(%s*(Meas_HP_FixOM_HT-Meas_Boiler_FixOM)+%s*(Meas_HP_VarOM_HT"
              "-Meas_Boiler_VarOM))" % (D(b.get("kw", 0)), D(b.get("heat", 0))),
        "Fleet": "=BL_Fleet_km*Meas_Fleet_MaintSaving",
        "PV": "=-Meas_PV_Size*Meas_PV_FixOMDEA_EUR2025",
        "RC": "=0",
    }[key]
    w.line(b["om"], "Annual O&M benefit", "EUR/yr")
    w.scalar(b["om"], om_f, m.om_benefit, "eur", link=True, name=nm("OMBenefit"))
    if key in ("LED", "VSD"):
        w.note(b["om"], "RVO EML gives investment only; no O&M change "
               "assumed")

    # (d) flag rows
    idx_r = R["idx"]
    w.line(b["init"], "Initial investment flag", "flag (1/0)")
    w.series(b["init"], lambda k, c: "=IF(%s=0,1,0)" % _a(c, idx_r),
             [1 if n == 0 else 0 for n in range(ny)], "int")
    repl = [1 if n in range(1, ny - 1) and n % m.life == 0 else 0
            for n in range(ny)]
    w.line(b["repl"], "Replacement flag", "flag (1/0)")
    w.series(b["repl"], lambda k, c: "=IF(AND(%s>=1,%s<M_LastIdx,MOD(%s,%s)=0)"
             ",1,0)" % (_a(c, idx_r), _a(c, idx_r), _a(c, idx_r), life), repl,
             "int")

    # (e) physical rows
    op = lambda c: _a(c, R["op"])  # noqa: E731
    zf = lambda k, c: "=0*%s" % op(c)  # noqa: E731
    if key in ("LED", "VSD"):
        f_de = lambda k, c: "=-%s/Const_kWh_per_MWh*%s" % (  # noqa: E731
            D(b["kwh"]), op(c))
    elif key == "HP":
        f_de = lambda k, c: "=%s/Meas_HP_COP_HT*%s" % (  # noqa: E731
            D(b["heat"]), op(c))
    elif key == "Fleet":
        f_de = lambda k, c: ("=BL_Fleet_km*Meas_Fleet_EVkWhPerKm/"  # noqa: E731
                             "Const_kWh_per_MWh*%s" % op(c))
    elif key == "PV":
        f_de = lambda k, c: (  # noqa: E731
            "=-Meas_PV_Size*Meas_PV_YieldTilt10/Const_kWh_per_MWh*"
            "(1-Meas_PV_Degradation)^(%s-1)*%s" % (_a(c, idx_r), op(c)))
    else:
        f_de = zf
    w.line(b["dE"], "Change in purchased electricity", "MWh")
    w.series(b["dE"], f_de, m.d_elec, "mwh", link=True, name=nm("dElec"))
    w.line(b["dG"], "Change in gas", "MWh NCV")
    if key == "HP":
        f_dg = lambda k, c: "=-%s/Meas_Boiler_Eff*%s" % (  # noqa: E731
            D(b["heat"]), op(c))
    else:
        f_dg = zf
    w.series(b["dG"], f_dg, m.d_gas, "mwh", link=True, name=nm("dGas"))
    w.line(b["dD"], "Change in diesel", "litres")
    if key == "Fleet":
        f_dd = lambda k, c: "=-BL_Fleet_Litres*%s" % op(c)  # noqa: E731
    else:
        f_dd = zf
    w.series(b["dD"], f_dd, m.d_diesel, "mwh", link=True, name=nm("dDiesel"))
    w.line(b["cov"], "Contract-covered electricity", "MWh")
    if key == "RC":
        f_cov = lambda k, c: "=%s*%s" % (_a(c, R["s5"]), op(c))  # noqa: E731
    else:
        f_cov = zf
    w.series(b["cov"], f_cov, m.covered, "mwh", name=nm("Covered"))

    def tonnes(ef_row, with_cov):
        def fn(k, c):
            core = "%s*%s+%s*EF_Gas_NCV+%s*EF_Diesel_l/Const_kg_per_t" % (
                _a(c, b["dE"]), _a(c, ef_row), _a(c, b["dG"]),
                _a(c, b["dD"]))
            if with_cov:
                return "=-(%s)+%s*%s" % (core, _a(c, b["cov"]),
                                         _a(c, ef_row))
            return "=-(%s)" % core
        return fn
    w.line(b["tLB"], "Abated tCO2e, location-based", "tCO2e")
    w.series(b["tLB"], tonnes(R["ef_lb"], False), m.t_lb, "tco2e", link=True,
             name=nm("tLB"), tag="LB")
    w.line(b["tMB"], "Abated tCO2e, market-based", "tCO2e")
    w.series(b["tMB"], tonnes(R["ef_mb"], True), m.t_mb, "tco2e", link=True,
             name=nm("tMB"), tag="MB")
    w.line(b["tSel"], "Abated tCO2e, selected basis", "tCO2e")
    w.series(b["tSel"], lambda k, c: "=CHOOSE(M_BasisIdx,%s,%s)" % (
        _a(c, b["tLB"]), _a(c, b["tMB"])), m.t_sel, "tco2e",
        name=nm("tSel"))

    # (f) the eight D-03 money rows
    pidx = lambda c: _a(c, R["pidx"])  # noqa: E731
    w.line(b["m_capex"], "Capex (initial and replacements)", "EUR")
    w.series(b["m_capex"], lambda k, c: "=-%s*(%s+%s)" % (
        D(b["capex"]), _a(c, b["init"]), _a(c, b["repl"])), m.capex_row,
        "eur")
    w.line(b["m_sub"], "Subsidy (initial capex only)", "EUR")
    w.series(b["m_sub"], lambda k, c: "=%s*%s*%s" % (
        D(b["sub"]), D(b["capex"]), _a(c, b["init"])), m.subsidy_row, "eur")
    w.line(b["m_res"], "Residual value", "EUR")
    w.series(b["m_res"], lambda k, c: "=IF(%s=M_LastIdx,%s*%s,0)" % (
        _a(c, idx_r), D(b["capex"]), D(b["resfrac"])), m.residual_row, "eur")
    w.line(b["m_om"], "Change in O&M", "EUR")
    w.series(b["m_om"], lambda k, c: "=%s*%s" % (D(b["om"]), op(c)),
             m.om_row, "eur")
    w.line(b["m_eE"], "Energy saving, electricity (incl. contract premium)",
           "EUR")
    w.series(b["m_eE"], lambda k, c: "=-(%s*BL_ElecPrice+%s*Meas_RC_GOPrice)"
             "*%s" % (_a(c, b["dE"]), _a(c, b["cov"]), pidx(c)), m.e_elec,
             "eur", link=True)
    w.line(b["m_eG"], "Energy saving, gas", "EUR")
    w.series(b["m_eG"], lambda k, c: "=-%s*BL_GasPriceNCV*%s" % (
        _a(c, b["dG"]), pidx(c)), m.e_gas, "eur", link=True)
    w.line(b["m_eD"], "Energy saving, diesel", "EUR")
    w.series(b["m_eD"], lambda k, c: "=-%s*M_DieselExVAT*%s" % (
        _a(c, b["dD"]), pidx(c)), m.e_diesel, "eur")
    w.line(b["m_cf"], "Net financial cash flow", "EUR")
    w.series(b["m_cf"], lambda k, c: "=SUM(%s:%s)" % (
        _a(c, b["m_capex"]), _a(c, b["m_eD"])), m.cf_fin, "eur",
        name=nm("CF"))
    w.line(b["m_carbon"], "Carbon value at selected scenario (shadow-price "
           "lens, not cash)", "EUR")
    w.series(b["m_carbon"], lambda k, c: "=%s*%s" % (
        _a(c, b["tSel"]), _a(c, R["cprice"])), m.carbon_value, "eur")
    w.line(b["m_cfi"], "Cash flow incl. carbon value", "EUR")
    w.series(b["m_cfi"], lambda k, c: "=%s+%s" % (
        _a(c, b["m_cf"]), _a(c, b["m_carbon"])), m.cf_incl, "eur",
        name=nm("CFCarbon"))


    _write_results(w, m, b, R, ref, check_names, mv, nm)


def _accum(xs):
    out, tot = [], 0.0
    for x in xs:
        tot += x
        out.append(tot)
    return out


def _first_reach(cum):
    for n, v in enumerate(cum):
        if v >= 0:
            return n
    return None


def _write_results(w, m, b, R, ref, check_names, mv, nm):
    """Decision metrics, internal checks (plan 03-08) for one block."""
    key = m.key
    ny = len(ref.years)
    D = _d
    cf = list(m.cf_fin)
    dfs = list(ref.df)
    dcf = [c * d for c, d in zip(cf, dfs)]
    cum, cumd = _accum(cf), _accum(dcf)
    reach = [1 if v >= 0 else 0 for v in cum]
    reachd = [1 if v >= 0 else 0 for v in cumd]
    sign, last = [], 0
    for c in cf:
        last = 1 if c > 0 else (-1 if c < 0 else last)
        sign.append(last)
    chg = [0] + [1 if sign[n - 1] != 0 and sign[n] != sign[n - 1] else 0
                 for n in range(1, ny)]
    cfr, dcfr = _rng(b["m_cf"]), _rng(b["dcf"])
    # year 0 cell and the year 1..n range of the net cash flow row, derived
    # from the timeline layout (WR-05), never hard-coded letters
    cf0 = "$%s$%d" % (col_letter(TIMELINE_FIRST_COL), b["m_cf"] + 1)
    cf_rest = "$%s$%d:$%s$%d" % (col_letter(TIMELINE_FIRST_COL + 1),
                                 b["m_cf"] + 1, col_letter(TIMELINE_LAST_COL),
                                 b["m_cf"] + 1)
    pc = lambda k: col_letter(TIMELINE_FIRST_COL + k - 1)  # noqa: E731

    w.band(b["r_band"], "Results: " + m.name)
    w.line(b["dcf"], "Discounted net cash flow", "EUR")
    w.series(b["dcf"], lambda k, c: "=%s*%s" % (_a(c, b["m_cf"]),
                                                _a(c, R["df"])), dcf, "eur")
    w.line(b["cum"], "Cumulative net cash flow", "EUR")
    w.series(b["cum"], lambda k, c: ("=%s" % _a(c, b["m_cf"]) if k == 0 else
                                     "=%s+%s" % (_a(pc(k), b["cum"]),
                                                 _a(c, b["m_cf"]))),
             cum, "eur")
    w.line(b["cumd"], "Cumulative discounted cash flow", "EUR")
    w.series(b["cumd"], lambda k, c: ("=%s" % _a(c, b["dcf"]) if k == 0 else
                                      "=%s+%s" % (_a(pc(k), b["cumd"]),
                                                  _a(c, b["dcf"]))),
             cumd, "eur")
    w.line(b["reach"], "Cumulative >= 0 (simple)", "flag (1/0)")
    w.series(b["reach"], lambda k, c: "=IF(%s>=0,1,0)" % _a(c, b["cum"]),
             reach, "int")
    w.line(b["reachd"], "Cumulative >= 0 (discounted)", "flag (1/0)")
    w.series(b["reachd"], lambda k, c: "=IF(%s>=0,1,0)" % _a(c, b["cumd"]),
             reachd, "int")
    w.line(b["sign"], "Sign of latest non-zero flow", "sign")
    w.series(b["sign"], lambda k, c: (
        "=IF(%s>0,1,IF(%s<0,-1,0))" % (_a(c, b["m_cf"]), _a(c, b["m_cf"]))
        if k == 0 else "=IF(%s>0,1,IF(%s<0,-1,%s))" % (
            _a(c, b["m_cf"]), _a(c, b["m_cf"]), _a(pc(k), b["sign"]))),
        sign, "int")
    w.line(b["chg"], "Sign change", "flag (1/0)")
    w.series(b["chg"], lambda k, c: ("=0" if k == 0 else
                                     "=IF(AND(%s<>0,%s<>%s),1,0)" % (
                                         _a(pc(k), b["sign"]),
                                         _a(c, b["sign"]),
                                         _a(pc(k), b["sign"]))),
             chg, "int")

    # ---- NPV family
    w.line(b["npv"], "Financial NPV, after subsidy (excl. carbon value; "
           "drives IRR, payback, abatement cost)", "EUR")
    w.scalar(b["npv"], "=SUMPRODUCT(%s,M_DF)" % cfr, m.npv, "eur",
             name=nm("NPV"))
    w.line(b["npvmemo"], "Memo: CF0 + NPV(rate, CF1..CFn)", "EUR")
    w.scalar(b["npvmemo"], "=%s+NPV(Rate_DiscountReal,%s)" % (cf0, cf_rest),
             m.npv_memo, "eur", name=nm("NPVMemo"))
    w.note(b["npvmemo"], "Excel NPV() discounts its first value one period, "
           "so year 0 stays outside it")
    w.line(b["pvsub"], "PV of subsidy", "EUR")
    w.scalar(b["pvsub"], "=SUMPRODUCT(%s,M_DF)" % _rng(b["m_sub"]),
             m.pv_subsidy, "eur", name=nm("PVSubsidy"))
    w.line(b["npvpre"], "NPV before subsidy", "EUR")
    w.scalar(b["npvpre"], "=%s-%s" % (D(b["npv"]), D(b["pvsub"])),
             m.npv_pre_sub, "eur", name=nm("NPVPreSub"))
    w.line(b["npvcarb"], "NPV incl. carbon value at the selected scenario "
           "(shadow-price lens, not cash)", "EUR")
    w.scalar(b["npvcarb"], "=SUMPRODUCT(%s,M_DF)" % _rng(b["m_cfi"]),
             m.npv_incl_carbon, "eur", name=nm("NPVCarbon"))
    capfac = (sum(dfs[n] for n in range(ny)
                  if n == 0 or ref_is_repl(m, ref, n))
              - m.res_frac * dfs[-1] - m.subsidy_frac)
    w.line(b["capfac"], "Capex PV factor (memo)", "factor")
    w.scalar(b["capfac"], "=SUMPRODUCT(%s,M_DF)+SUMPRODUCT(%s,M_DF)-%s*"
             "INDEX(M_DF,M_LastIdx+1)-%s" % (
                 _rng(b["init"]), _rng(b["repl"]), D(b["resfrac"]),
                 D(b["sub"])), capfac, "factor", name=nm("CapexPVFactor"))
    w.line(b["npvfull"], "Full-capex NPV (memo, D-05)", "EUR")
    if m.npv_full_capex is None:
        w.cells.text(w.ws, b["npvfull"], SCALAR_COL,
                     "n/a (no counterfactual purchase)", w.styles.get("note"))
        cells = w.cells
        cells.define_name(nm("NPVFullCapex"),
                            "=%s!$D$%d" % (SHEET, b["npvfull"] + 1))
    else:
        w.scalar(b["npvfull"], "=%s-(%s-%s)*%s" % (
            D(b["npv"]), D(b["fullcapex"]), D(b["capex"]), D(b["capfac"])),
            m.npv_full_capex, "eur", name=nm("NPVFullCapex"))

    # ---- IRR
    guess = -mv["Const_IRR_Guess"] if sum(cf) < 0 else mv["Const_IRR_Guess"]
    w.line(b["guess"], "IRR guess", "fraction")
    w.scalar(b["guess"], "=IF(SUM(%s)<0,-Const_IRR_Guess,Const_IRR_Guess)"
             % cfr, guess, "pct")
    # numeric view of a cell that may hold an n/a text, so a guarded branch
    # never does arithmetic on text
    nz = lambda row: "IF(ISNUMBER(%s),%s,0)" % (D(row), D(row))  # noqa: E731
    w.line(b["irr"], "IRR (on financial cash flows)", "%")
    w.scalar(b["irr"], '=IF(%s>=0,"%s",IF(MAX(%s)<=0,"%s",IFERROR(IRR(%s,%s),'
             '"%s")))' % (cf0, ap.NA_NO_OUTLAY, cfr, ap.NA_NEVER_PAYS, cfr,
                          D(b["guess"]), ap.NA_NO_SOLUTION), m.irr, "pct",
             name=nm("IRR"))
    w.line(b["nchg"], "Sign changes in cash flow", "count")
    w.scalar(b["nchg"], "=SUM(%s)" % _rng(b["chg"]), m.sign_changes, "int")
    w.line(b["irrflag"], "IRR uniqueness flag", "")
    w.scalar(b["irrflag"], '=IF(%s>1,"%s","")' % (D(b["nchg"]), ap.MULTI_SIGN),
             m.multi_flag, "general", name=nm("IRRFlag"))

    # ---- payback
    def payback(first_k, pay_k, reach_k, cum_k, flow_k, cum_list, text, name,
                value):
        fv = _first_reach(cum_list)
        w.line(b[first_k], "First year index with cumulative >= 0 (%s; -1 = "
               "never within the horizon)" % text, "index")
        w.scalar(b[first_k], "=IF(MAX(%s)=0,-1,MATCH(1,%s,0)-1)" % (
            _rng(b[reach_k]), _rng(b[reach_k])), -1 if fv is None else fv,
            "int")
        f = D(b[first_k])
        w.line(b[pay_k], "%s payback (years after %d)" % (
            text.capitalize(), ref.years[0]), "years")
        w.scalar(b[pay_k], '=IF(%s<0,"%s",IF(%s=0,"%s",(%s-1)+(-INDEX(%s,'
                 '%s))/INDEX(%s,%s+1)))' % (
                     f, ap.NOT_WITHIN, f, ap.NA_NO_OUTLAY, f,
                     _rng(b[cum_k]), f, _rng(b[flow_k]), f), value, "dec1",
                 name=name)
    payback("first_s", "pay_s", "reach", "cum", "m_cf", cum, "simple",
            nm("PaySimple"), m.pay_simple)
    payback("first_d", "pay_d", "reachd", "cumd", "dcf", cumd, "discounted",
            nm("PayDisc"), m.pay_disc)

    # ---- tonnes
    for k, row, lst, tag, label in (
            ("pvlb", "tLB", m.t_lb, "LB", "location-based"),
            ("pvmb", "tMB", m.t_mb, "MB", "market-based"),
            ("pvsel", "tSel", m.t_sel, None, "selected basis")):
        val = m.pv_t_lb if k == "pvlb" else (m.pv_t_mb if k == "pvmb"
                                             else m.pv_t_sel)
        w.line(b[k], "PV of abated tCO2e, %s" % label, "tCO2e")
        w.scalar(b[k], "=SUMPRODUCT(%s,M_DF)" % _rng(b[row]), val, "tco2e",
                 name=nm("PVt" + row[1:]))
        if tag:
            w.cells.tag(SHEET, b[k], SCALAR_COL, b[k], SCALAR_COL, tag)
    for k, row, val, tag, label in (
            ("avglb", "tLB", m.avg_t_lb, "LB", "location-based"),
            ("avgmb", "tMB", m.avg_t_mb, "MB", "market-based"),
            ("avgsel", "tSel", m.avg_t_sel, None, "selected basis")):
        w.line(b[k], "Average annual abated tCO2e, %s" % label, "tCO2e/yr")
        w.scalar(b[k], "=SUM(%s)/SUM(M_Op)" % _rng(b[row]), val, "tco2e",
                 name=nm("Avgt" + row[1:]))
        if tag:
            w.cells.tag(SHEET, b[k], SCALAR_COL, b[k], SCALAR_COL, tag)
    elig = D(b["elig"])
    w.line(b["elig"], "Abatement on selected basis (1 = yes: PV of tonnes "
           "and average annual tonnes both > 0)", "flag (1/0)")
    w.scalar(b["elig"], "=IF(AND(%s>0,%s>0),1,0)" % (D(b["pvsel"]),
                                                     D(b["avgsel"])),
             1 if m.eligible else 0, "int", name=nm("Eligible"))
    w.line(b["lev"], "Levelised abatement cost (EUR/tCO2e, excl. carbon "
           "value; negative = saves money)", "EUR/tCO2e")
    w.scalar(b["lev"], '=IF(%s=0,"%s",-%s/%s)' % (
        elig, ap.NA_NO_ABATEMENT, D(b["npv"]), D(b["pvsel"])), m.lev,
        "eur_per_t", name=nm("LevCost"))
    w.line(b["be"], "Break-even carbon price (constant real price at which "
           "NPV incl. carbon = 0)", "EUR/tCO2e")
    w.scalar(b["be"], '=IF(%s=0,"%s",-%s/%s)' % (
        elig, ap.NA_NO_ABATEMENT, D(b["npv"]), D(b["pvsel"])), m.break_even,
        "eur_per_t", name=nm("BreakEven"))

    def check(row, name, text, f, val, note=None):
        w.line(row, text, "TRUE/FALSE")
        w.scalar(row, f, bool(val), "general", name=name)
        apply_bool_check_format(w.ws, w.styles, row, SCALAR_COL, row,
                                SCALAR_COL)
        if note:
            w.note(row, note)
        check_names.append(name)
    tol_m = mv["Const_CheckTolMoney"]
    check(b["chk_memo"], "M_Check_%s_NPVMemo" % key,
          "Check: SUMPRODUCT NPV equals CF0 + NPV() memo",
          "=ABS(%s-%s)<=Const_CheckTolMoney" % (D(b["npv"]), D(b["npvmemo"])),
          abs(m.npv - m.npv_memo) <= tol_m)
    # WR-08: a real test of the definition, recomputed from the yearly
    # cash-flow and tonnes rows (not from the NPV / PV(tonnes) cells the
    # break-even formula reads): NPV incl. carbon value at a constant carbon
    # price equal to the break-even price must be zero.
    be_num = isinstance(m.break_even, float)
    check(b["chk_be"], "M_Check_%s_BreakEven" % key,
          "Check: NPV incl. carbon value at the break-even price is zero "
          "(recomputed from the yearly rows)",
          "=IF(ISNUMBER(%s),ABS(SUMPRODUCT(%s,M_DF)+%s*SUMPRODUCT(%s,M_DF))"
          "<=Const_CheckTolMoney,TRUE)" % (
              D(b["be"]), cfr, nz(b["be"]), _rng(b["tSel"])),
          (abs(ap.npv0(ref.rate, cf) + m.break_even
               * ap.npv0(ref.rate, list(m.t_sel))) <= tol_m)
          if be_num else True)

    # ---- internal reconciliation
    w.band(b["i_band"], "Internal reconciliation (not a client output)")
    w.line(b["levpre"], "Levelised cost before subsidy", "EUR/tCO2e")
    w.scalar(b["levpre"], '=IF(%s=0,"%s",-%s/%s)' % (
        elig, ap.NA_NO_ABATEMENT, D(b["npvpre"]), D(b["pvsel"])),
        m.lev_pre_sub, "eur_per_t")
    # WR-10: the annuity form annualises every term with one capital
    # recovery factor over the levelised-cost horizon (the operating years,
    # SUM(M_Op)), so it equals the levelised cost before subsidy for any
    # tonne or benefit profile. It is built from separate sums (capex x the
    # initial / replacement / residual flags, the O&M and energy rows, the LB
    # or MB tonne row), not from the NPV, PV(tonnes) or net cash flow cells
    # the levelised cost reads, so a broken row or formula still fails it.
    w.line(b["crf"], "Capital recovery factor over the levelised-cost "
           "horizon (operating years, SUM(M_Op))", "factor")
    # WR-13: at a real rate of exactly 0 (nominal rate = inflation) the
    # closed form is 0/0; the limit is 1/n, as in checkmodel.appraisal.crf.
    w.scalar(b["crf"], "=IF(Rate_DiscountReal=0,1/SUM(M_Op),"
             "Rate_DiscountReal/(1-1/(1+Rate_DiscountReal)^SUM(M_Op)))",
             m.ann_crf, "factor")
    crf_c = D(b["crf"])
    w.line(b["eqcap"], "Equivalent annual capital cost before subsidy (CRF "
           "x PV of initial capex and replacements less residual value)",
           "EUR/yr")
    w.scalar(b["eqcap"], "=%s*%s*(SUMPRODUCT(%s,M_DF)+SUMPRODUCT(%s,M_DF)-"
             "%s*INDEX(M_DF,M_LastIdx+1))" % (
                 crf_c, D(b["capex"]), _rng(b["init"]), _rng(b["repl"]),
                 D(b["resfrac"])), m.ann_capital, "eur")
    w.line(b["avgben"], "Equivalent annual operating benefit (CRF x PV of "
           "the O&M and energy rows)", "EUR/yr")
    w.scalar(b["avgben"], "=%s*(SUMPRODUCT(%s,M_DF)+SUMPRODUCT(%s,M_DF)+"
             "SUMPRODUCT(%s,M_DF)+SUMPRODUCT(%s,M_DF))" % (
                 crf_c, _rng(b["m_om"]), _rng(b["m_eE"]), _rng(b["m_eG"]),
                 _rng(b["m_eD"])), m.ann_benefit, "eur")
    w.line(b["eqt"], "Equivalent annual abated tCO2e, selected basis (CRF x "
           "PV of the location- or market-based tonne row)", "tCO2e/yr")
    w.scalar(b["eqt"], "=%s*IF(M_BasisIdx=1,SUMPRODUCT(%s,M_DF),"
             "SUMPRODUCT(%s,M_DF))" % (crf_c, _rng(b["tLB"]), _rng(b["tMB"])),
             m.ann_tonnes, "tco2e")
    ann_v = m.annuity if m.eligible else ap.NA_NO_ABATEMENT
    w.line(b["ann"], "Annuity-method cost (equivalent annual cost / "
           "equivalent annual tonnes)", "EUR/tCO2e")
    w.scalar(b["ann"], '=IF(%s=0,"%s",(%s-%s)/%s)' % (
        elig, ap.NA_NO_ABATEMENT, D(b["eqcap"]), D(b["avgben"]),
        D(b["eqt"])), ann_v, "eur_per_t")
    ann_ok = m.annuity_ok if m.eligible else True
    check(b["chk_ann"], "M_Check_%s_Annuity" % key,
          "Check: annuity cost agrees with levelised cost before subsidy",
          "=IF(%s=0,TRUE,ABS(%s-%s)<=Const_AnnuityTolAbs+Const_AnnuityTolRel*"
          "ABS(%s))" % (elig, nz(b["ann"]), nz(b["levpre"]), nz(b["levpre"])),
          ann_ok, "one CRF over the levelised-cost horizon annualises cost and "
          "tonnes, so the forms agree for any profile; recomputed from the "
          "yearly rows (tolerance Const_AnnuityTolAbs / Const_AnnuityTolRel)")
    check(b["chk_zero"], "M_Check_%s_NPVatZero" % key,
          "Check: NPV at r = 0 equals the plain sum",
          "=ABS((%s+NPV(0,%s))-SUM(%s))<=Const_CheckTolMoney" % (
              cf0, cf_rest, cfr),
          abs(cf[0] + sum(cf[1:]) - sum(cf)) <= tol_m)
    irr_num = isinstance(m.irr, float)
    check(b["chk_irr"], "M_Check_%s_NPVatIRR" % key,
          "Check: NPV at the IRR is about zero",
          "=IF(ISNUMBER(%s),ABS(%s+NPV(%s,%s))<="
          "Const_IRRCheckTolMoney,TRUE)" % (
              D(b["irr"]), cf0, nz(b["irr"]), cf_rest),
          (abs(ap.npv0(m.irr, cf)) <= mv["Const_IRRCheckTolMoney"])
          if irr_num else True)


def ref_is_repl(m, ref, n):
    return ref.years[n] in m.replacement_years


def _write_summary(w, ref, R, B, check_names):
    r0 = R["sum_band"]
    cells = w.cells
    w.band(r0, "Results summary (selected basis and scenario; details in each "
           "block below)")
    hdr = w.styles.get("header")
    heads = ("Measure", "Annual tCO2e (selected)",
             "Annual tCO2e, location-based", "Annual tCO2e, market-based",
             "Abatement cost EUR/tCO2e", "Financial NPV (after subsidy)",
             "NPV before subsidy", "NPV incl. carbon value (lens)", "IRR",
             "Simple payback (years)", "Discounted payback (years)")
    for i, t in enumerate(heads):
        w.cells.text(w.ws, r0 + 1, LABEL_COL + i, t, hdr)
    first = r0 + 2
    last = first + len(ref.measures) - 1
    cols = (("AvgtSel", "tco2e", lambda x: x.avg_t_sel),
            ("AvgtLB", "tco2e", lambda x: x.avg_t_lb),
            ("AvgtMB", "tco2e", lambda x: x.avg_t_mb),
            ("LevCost", "eur_per_t", lambda x: x.lev),
            ("NPV", "eur", lambda x: x.npv),
            ("NPVPreSub", "eur", lambda x: x.npv_pre_sub),
            ("NPVCarbon", "eur", lambda x: x.npv_incl_carbon),
            ("IRR", "pct", lambda x: x.irr),
            ("PaySimple", "dec1", lambda x: x.pay_simple),
            ("PayDisc", "dec1", lambda x: x.pay_disc))
    # summary column index and letter from the position in cols (WR-05)
    ci = dict((suffix, LABEL_COL + 1 + j)
              for j, (suffix, _n, _a) in enumerate(cols))
    sc = dict((k, col_letter(c)) for k, c in ci.items())
    # tags first, so the LB / MB lint sees them before any reader formula
    w.cells.tag(SHEET, first, ci["AvgtLB"], last, ci["AvgtLB"], "LB")
    w.cells.tag(SHEET, first, ci["AvgtMB"], last, ci["AvgtMB"], "MB")
    for i, mr in enumerate(ref.measures):
        r = first + i
        w.cells.text(w.ws, r, LABEL_COL, mr.name, w.styles.get("label"))
        for j, (suffix, num, attr) in enumerate(cols):
            w.cells.formula(w.ws, r, LABEL_COL + 1 + j,
                            "=M_%s_%s" % (mr.key, suffix),
                            w.styles.get("link", num), value=attr(mr))
    pr = last + 2

    # portfolio rows keep values in column D under their own labels
    ms = ref.measures
    w.cells.text(w.ws, pr, LABEL_COL, "Portfolio financial NPV (sum of "
                 "measures, stack order applied)", w.styles.get("label"))
    w.cells.formula(w.ws, pr, 3, "=SUM(%s%d:%s%d)" % (
                        sc["NPV"], first + 1, sc["NPV"], last + 1),
                    w.styles.get("calc", "eur"),
                    value=sum(x.npv for x in ms))
    cells.define_name("M_Portfolio_NPV", "=%s!$D$%d" % (SHEET, pr + 1))
    w.cells.text(w.ws, pr + 1, LABEL_COL, "Total annual tCO2e, "
                 "location-based", w.styles.get("label"))
    w.cells.formula(w.ws, pr + 1, 3, "=SUM(%s%d:%s%d)" % (
                        sc["AvgtLB"], first + 1, sc["AvgtLB"], last + 1),
                    w.styles.get("calc", "tco2e"),
                    value=sum(x.avg_t_lb for x in ms))
    cells.define_name("M_Total_tLB", "=%s!$D$%d" % (SHEET, pr + 2))
    w.cells.text(w.ws, pr + 2, LABEL_COL, "Total annual tCO2e, "
                 "market-based", w.styles.get("label"))
    w.cells.formula(w.ws, pr + 2, 3, "=SUM(%s%d:%s%d)" % (
                        sc["AvgtMB"], first + 1, sc["AvgtMB"], last + 1),
                    w.styles.get("calc", "tco2e"),
                    value=sum(x.avg_t_mb for x in ms))
    cells.define_name("M_Total_tMB", "=%s!$D$%d" % (SHEET, pr + 3))
    w.cells.tag(SHEET, pr + 1, 3, pr + 1, 3, "LB")
    w.cells.tag(SHEET, pr + 2, 3, pr + 2, 3, "MB")
    w.note(pr + 3, "The electricity part of the six measures' market-based "
           "tonnes sums exactly to the baseline market-based electricity "
           "emissions; the split between measures depends on the stack order "
           "(see Notes)", LABEL_COL)
    w.cells.text(w.ws, pr + 4, LABEL_COL, "All Measures checks (TRUE = "
                 "every check passes)", w.styles.get("label"))
    names = [n for n in check_names]
    w.cells.formula(w.ws, pr + 4, 3, "=AND(%s)" % ",".join(names),
                    w.styles.get("calc", "general"), value=True)
    cells.define_name("M_Check_All", "=%s!$D$%d" % (SHEET, pr + 5))
    apply_bool_check_format(w.ws, w.styles, pr + 4, 3, pr + 4, 3)
    return {"first": first, "last": last, "portfolio": pr,
            "check_all": pr + 4}
