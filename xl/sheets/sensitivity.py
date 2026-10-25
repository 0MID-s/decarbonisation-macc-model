"""Sensitivity sheet, part 1 (plan 04-08): carbon-inclusive portfolio NPV,
gross helper PVs, 5x5 energy x carbon grid and discount-rate strip.

Everything is a plain formula (no Data Tables). Cached values come from
checkmodel.sensitivity_reference. The tornado and rank stability follow in
plan 04-09; they append below SensitivityLayout.end_row and add checks to
CHECK_NAMES before Sens_Check_All is written (see _finish_checks).
"""
from dataclasses import dataclass
from typing import Tuple

from checkmodel.measures_reference import DEFAULT_DIRECT_ETS  # noqa: F401
from checkmodel.sensitivity_reference import compute_sensitivity
from config.measures_catalog import MEASURES
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter,
    setup_sheet)
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import write_title_band
from xl.sheets.rowwriter import RowWriter
from xl.styles import SheetKind, apply_bool_check_format

SHEET = "Sensitivity"
LAST_COL = TIMELINE_LAST_COL
HDR_ROW = 4  # zero-based; Excel row 5
SCALAR_COL = 3  # column D
NOTE_COL = 4  # column E
CHECK_NAMES = []  # type: list  # module-level so plan 04-09 can add checks
MEASURE_KEYS = ("LED", "VSD", "HP", "Fleet", "PV", "RC")
SHORT = {m.key: m.short for m in MEASURES}

TITLE_NOTE = (
    "Real EUR 2025, 2026-2055, selected scenario. NPV including carbon is the "
    "financial NPV plus the cash carbon cost each measure avoids; the "
    "shadow-price lens on Measures is separate")
PURPOSE = (
    "How robust is the business case? Portfolio NPV including carbon cash "
    "savings, under changes to energy price, carbon price and discount rate "
    "(formula grids, no Data Tables)")
NOTE_NPV = (
    "The financial NPV (Measures) leaves carbon out on purpose; adding the "
    "cash carbon cost each measure avoids (ETS2 and pass-through, selected "
    "scenario, 2027-2055) gives the real business case. The shadow-price "
    "'NPV incl. carbon value' on Measures is a different lens.")
NOTE_GROSS = (
    "Only the gross carbon PVs scale with the carbon price; the embedded-EUA "
    "part is a fixed offset (the carbon already in today's tariff) and must "
    "not be scaled.")


@dataclass(frozen=True)
class SensitivityLayout:
    rows: Tuple[Tuple[str, int], ...]
    end_row: int  # first free zero-based row below part 1
    hdr_row: int


def build_sensitivity(wb, styles, cells, dataset, cfg, layouts):
    state = selector_state(dataset)
    ref = compute_sensitivity(dataset.inputs, state[0], state[1],
                              direct_ets_state(dataset))
    ny = len(ref.elec_saved)
    ms_rows = layouts["measures"].rows
    blocks = layouts["measures"].blocks
    idx_r = ms_rows["idx"] + 1

    ws = wb.add_worksheet(SHEET)
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=HDR_ROW)
    write_title_band(cells, styles, ws, "Sensitivity", PURPOSE, TITLE_NOTE,
                     LAST_COL)
    hdr = styles.get("header")
    cells.text(ws, HDR_ROW, LABEL_COL, "Item", hdr)
    cells.text(ws, HDR_ROW, UNIT_COL, "Unit", hdr)
    yr = styles.get("header_year", "year")
    c0 = TIMELINE_FIRST_COL
    years = [cfg.timeline_start + k for k in range(ny)]
    cells.formula(ws, HDR_ROW, c0, "=Time_FirstYear", yr, value=years[0])
    for k in range(1, ny):
        cells.formula(ws, HDR_ROW, c0 + k,
                      "=%s%d+1" % (col_letter(c0 + k - 1), HDR_ROW + 1),
                      yr, value=years[k])

    w = RowWriter(ws, cells, styles, SHEET, LAST_COL, SCALAR_COL, NOTE_COL, ny)
    rows = []  # type: list
    cur = [HDR_ROW + 2]
    CHECK_NAMES[:] = []

    def nxt():
        r = cur[0]
        cur[0] += 1
        return r

    def reg(name, r):
        rows.append((name, r))

    def series(name, text, unit, fn, vals, num, note=None):
        r = nxt()
        w.line(r, text, unit)
        w.series(r, fn, vals, num, name=name)
        if note:
            w.note(r, note)
        reg(name, r)
        return r

    def scalar(name, text, unit, f, val, num, note=None):
        r = nxt()
        w.line(r, text, unit)
        w.scalar(r, f, val, num, name=name)
        if note:
            w.note(r, note)
        reg(name, r)
        return r

    def check(name, text, f, val):
        r = nxt()
        w.line(r, text, "TRUE/FALSE")
        w.scalar(r, f, bool(val), "general", name=name)
        apply_bool_check_format(ws, styles, r, 3, r, 3)
        CHECK_NAMES.append(name)
        reg(name, r)

    def a(c, name):
        return "%s$%d" % (c, dict(rows)[name] + 1)

    calc_eur = styles.get("calc", "eur")
    tol = "Const_CheckTolMoney"

    # ---- (A) portfolio NPV incl. carbon --------------------------------
    w.band(nxt(), "Portfolio NPV incl. carbon cash savings (D-19)")
    r = nxt()
    w.line(r, "Measure")
    for col, txt in ((3, "Financial NPV"), (4, "PV carbon cash saving"),
                     (5, "NPV incl. carbon")):
        cells.text(ws, r, col, txt, hdr)
    first = cur[0]
    for key in MEASURE_KEYS:
        r = nxt()
        w.line(r, SHORT[key], "EUR")
        R = r + 1
        cells.formula(ws, r, 3, "=M_%s_NPV" % key, styles.get("link", "eur"),
                      value=ref.npv_fin_by_measure[key])
        cells.formula(ws, r, 4, "=SUMPRODUCT(Expo_Avoided_%s,M_DF,M_Op)" % key,
                      calc_eur, value=ref.pv_carbon_by_measure[key])
        cells.formula(ws, r, 5, "=D%d+E%d" % (R, R), calc_eur,
                      value=ref.npv_incl_by_measure[key])
    last = cur[0] - 1
    r = nxt()
    w.line(r, "Portfolio total", "EUR")
    for col, nm, val in ((3, "Sens_PortfolioNPV_Fin", ref.npv_fin),
                         (4, "Sens_PVCarbon", ref.pv_carbon),
                         (5, "Sens_PortfolioNPV", ref.npv_incl)):
        L = col_letter(col)
        cells.formula(ws, r, col, "=SUM(%s%d:%s%d)" % (L, first + 1, L,
                                                         last + 1),
                      calc_eur, value=val)
        cells.define_name(nm, "=%s!$%s$%d" % (SHEET, L, r + 1))
    reg("Sens_PortfolioNPV", r)
    w.note(nxt(), NOTE_NPV, LABEL_COL)
    check("Sens_Check_Reconcile", "Check: portfolio NPV equals Measures "
          "portfolio NPV plus discounted avoided carbon cost",
          "=ABS(Sens_PortfolioNPV-(M_Portfolio_NPV+SUMPRODUCT("
          "Expo_Avoided_Sel,M_DF,M_Op)))<=%s" % tol, True)
    nxt()

    # ---- (B) helper rows -----------------------------------------------
    w.band(nxt(), "Helper rows: portfolio quantities saved (per year)")

    def msum(field, sign=""):
        def fn(k, c):
            return "=%s(%s)" % (sign, "+".join(
                "Measures!%s$%d" % (c, blocks[m][field] + 1)
                for m in MEASURE_KEYS))
        return fn

    series("Sens_ElecSaved", "Purchased electricity saved", "MWh",
           msum("dE", "-"), ref.elec_saved, "mwh")
    series("Sens_GasSaved", "Gas saved", "MWh", msum("dG", "-"),
           ref.gas_saved, "mwh")
    series("Sens_DieselSaved", "Diesel saved", "litres", msum("dD", "-"),
           ref.diesel_saved, "mwh")
    series("Sens_Covered", "Contract-covered electricity", "MWh",
           msum("cov"), ref.covered_sum, "mwh")
    series("Sens_tStatSaved", "Stationary-fuel tCO2 saved in ETS2 scope",
           "tCO2", lambda k, c: "=%s*EF_Gas_NCV*Carbon_ETS2_Scope_Gas"
           % a(c, "Sens_GasSaved"), ref.t_stat_saved, "tco2e")
    series("Sens_tFleetSaved", "Fleet-diesel tCO2 saved in ETS2 scope",
           "tCO2", lambda k, c: (
               "=%s*EF_Diesel_l/Const_kg_per_t*Carbon_ETS2_Scope_FleetDiesel"
               % a(c, "Sens_DieselSaved")), ref.t_fleet_saved, "tco2e")
    nxt()

    # ---- (C) helper PVs ------------------------------------------------
    w.band(nxt(), "Helper PVs at the base case (gross, so the grid stays "
           "exact)")
    scalar("Sens_PV_Elec", "PV of electricity cost saved", "EUR",
           "=BL_ElecPrice*SUMPRODUCT(Sens_ElecSaved,M_PriceIdx,M_DF)",
           ref.pv_elec, "eur")
    scalar("Sens_PV_Gas", "PV of gas cost saved", "EUR",
           "=BL_GasPriceNCV*SUMPRODUCT(Sens_GasSaved,M_PriceIdx,M_DF)",
           ref.pv_gas, "eur")
    scalar("Sens_PV_Diesel", "PV of diesel cost saved", "EUR",
           "=M_DieselExVAT*SUMPRODUCT(Sens_DieselSaved,M_PriceIdx,M_DF)",
           ref.pv_diesel, "eur")
    scalar("Sens_PV_Energy", "PV of energy cost saved (electricity, gas, "
           "diesel)", "EUR",
           "=Sens_PV_Elec+Sens_PV_Gas+Sens_PV_Diesel", ref.pv_energy, "eur")
    scalar("Sens_PV_GO", "PV of guarantee-of-origin cost (kept out of the "
           "energy multiplier)", "EUR",
           "=Meas_RC_GOPrice/Const_MWh_per_GO*SUMPRODUCT(Sens_Covered,"
           "M_PriceIdx,M_DF)", ref.pv_go, "eur")
    scalar("Sens_PV_ETS2Gross", "PV of ETS2 cost avoided (gross)", "EUR",
           "=SUMPRODUCT(Sens_tStatSaved,Expo_PStat2_Sel,M_DF)"
           "+SUMPRODUCT(Sens_tStatSaved,Expo_PStat1_Sel,M_DF)"
           "+SUMPRODUCT(Sens_tFleetSaved,Expo_PETS2_Sel,M_DF)",
           ref.pv_ets2_gross, "eur")
    scalar("Sens_PV_PTGross", "PV of pass-through avoided (gross)", "EUR",
           "=Expo_MEF*Pass_PTR*SUMPRODUCT(Sens_ElecSaved,Expo_PETS1_Sel,M_DF)",
           ref.pv_pt_gross, "eur")
    scalar("Sens_PV_PTEmbedded", "PV of pass-through already in the tariff "
           "(embedded EUA)", "EUR",
           "=Expo_MEF*Pass_PTR*Expo_EmbeddedEUA*SUMPRODUCT(Sens_ElecSaved,"
           "M_DF)", ref.pv_pt_embedded, "eur")
    scalar("Sens_PV_PTNet", "PV of pass-through avoided (net)", "EUR",
           "=Sens_PV_PTGross-Sens_PV_PTEmbedded", ref.pv_pt_net, "eur")
    w.note(nxt(), NOTE_GROSS, LABEL_COL)
    check("Sens_Check_CarbonPV", "Check: gross carbon PVs less the embedded "
          "part equal the PV of avoided carbon cost",
          "=ABS(Sens_PVCarbon-(Sens_PV_ETS2Gross+Sens_PV_PTGross"
          "-Sens_PV_PTEmbedded))<=%s" % tol, True)
    nxt()

    # ---- (D) grid --------------------------------------------------------
    w.band(nxt(), "Grid: portfolio NPV incl. carbon (EUR) by energy price "
           "(rows) and carbon price (columns) multipliers")
    w.note(nxt(), "Columns: Carbon price multiplier (whole ETS1 and ETS2 "
           "cash paths). Rows: Energy price multiplier (electricity, gas and "
           "diesel together)", LABEL_COL)
    hr = nxt()
    w.line(hr, "Carbon price multiplier (whole ETS1 and ETS2 cash paths)")
    mult = styles.get("calc", "factor")
    axis = ref.grid_axis
    ccol = 5  # centre column F
    for j in range(5):
        col = 3 + j
        L = col_letter(col)
        if j == 2:
            f = "=1"
        elif j < 2:
            f = "=%s%d-Sens_GridStep" % (col_letter(col + 1), hr + 1)
        else:
            f = "=%s%d+Sens_GridStep" % (col_letter(col - 1), hr + 1)
        cells.formula(ws, hr, col, f, mult, value=axis[j])
    gr = []
    for i in range(5):
        r = nxt()
        gr.append(r)
        if i == 0:
            w.line(r, "Energy price multiplier (electricity, gas and diesel "
                   "together)")
    # row axis in column C (unit column); built after rows allocated
    for i, r in enumerate(gr):
        if i == 2:
            f = "=1"
        elif i < 2:
            f = "=C%d-Sens_GridStep" % (gr[i + 1] + 1)
        else:
            f = "=C%d+Sens_GridStep" % (gr[i - 1] + 1)
        cells.formula(ws, r, UNIT_COL, f, mult, value=axis[i])
        for j in range(5):
            col = 3 + j
            L = col_letter(col)
            f = ("=Sens_PortfolioNPV+($C%d-1)*Sens_PV_Energy+(%s$%d-1)*"
                 "(Sens_PV_ETS2Gross+Sens_PV_PTGross)" % (r + 1, L, hr + 1))
            cells.formula(ws, r, col, f, calc_eur, value=ref.grid[i][j])
    cells.define_name("Sens_Grid", "=%s!$D$%d:$H$%d" % (SHEET, gr[0] + 1,
                                                       gr[-1] + 1))
    cells.define_name("Sens_GridCentre", "=%s!$%s$%d" % (
        SHEET, col_letter(ccol), gr[2] + 1))
    reg("Sens_Grid", gr[0])
    check("Sens_Check_GridCentre", "Check: grid centre equals the base "
          "portfolio NPV",
          "=ABS(Sens_GridCentre-Sens_PortfolioNPV)<=%s" % tol, True)
    nxt()

    # ---- (E) discount-rate strip ---------------------------------------
    w.band(nxt(), "Discount-rate strip (real)")
    rr = nxt()
    w.line(rr, "Real discount rate", "fraction")
    pct = "pct"
    for j in range(5):
        col = 3 + j
        if j == 2:
            f = "=Rate_DiscountReal"
        elif j < 2:
            f = "=%s%d-Sens_RateStep" % (col_letter(col + 1), rr + 1)
        else:
            f = "=%s%d+Sens_RateStep" % (col_letter(col - 1), rr + 1)
        cells.formula(ws, rr, col, f, styles.get("calc", pct),
                      value=ref.rate_axis[j])
        cells.define_name("Sens_Rate_%d" % (j + 1), "=%s!$%s$%d" % (
            SHEET, col_letter(col), rr + 1))
    reg("Sens_Rate_1", rr)
    ex_row = dict(layouts["exposure"].rows)["Expo_Avoided_Sel"] + 1
    series("Sens_PortfolioCF", "Portfolio cash flow incl. avoided carbon "
           "cost", "EUR",
           lambda k, c: "=%s+Exposure!%s$%d" % ("+".join(
               "Measures!%s$%d" % (c, blocks[m]["m_cf"] + 1)
               for m in MEASURE_KEYS), c, ex_row),
           ref.portfolio_cf, "eur")
    idx_vals = list(range(ny))
    for j in range(5):
        rate_cell = "$%s$%d" % (col_letter(3 + j), rr + 1)
        series("Sens_DF_R%d" % (j + 1), "Discount factor at strip rate %d"
               % (j + 1), "factor",
               (lambda rc: lambda k, c: "=1/(1+%s)^Measures!%s$%d" % (
                   rc, c, idx_r))(rate_cell),
               [1.0 / (1.0 + ref.rate_axis[j]) ** n for n in idx_vals],
               "dec5")
    nr = nxt()
    w.line(nr, "Portfolio NPV incl. carbon at the strip rate", "EUR")
    for j in range(5):
        cells.formula(ws, nr, 3 + j, "=SUMPRODUCT(Sens_PortfolioCF,"
                      "Sens_DF_R%d)" % (j + 1), calc_eur,
                      value=ref.rate_npvs[j])
        cells.define_name("Sens_RateNPV_%d" % (j + 1), "=%s!$%s$%d" % (
            SHEET, col_letter(3 + j), nr + 1))
    reg("Sens_RateNPV_1", nr)
    w.note(nxt(), "Recomputed directly with its own discount-factor rows: "
           "the rate changes the discount factors themselves, so it is not a "
           "straight-line shift like a price.", LABEL_COL)
    check("Sens_Check_RateCentre", "Check: rate-strip centre equals the base "
          "portfolio NPV (independent discount-factor path)",
          "=ABS(Sens_RateNPV_3-Sens_PortfolioNPV)<=%s" % tol, True)
    nxt()

    r = nxt()
    w.line(r, "All Sensitivity checks (TRUE = every check passes)",
           "TRUE/FALSE")
    w.scalar(r, "=AND(%s)" % ",".join(CHECK_NAMES), True, "general",
             name="Sens_Check_All")
    apply_bool_check_format(ws, styles, r, 3, r, 3)
    reg("Sens_Check_All", r)
    return SensitivityLayout(tuple(rows), cur[0], HDR_ROW)
