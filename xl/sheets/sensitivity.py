"""Sensitivity sheet, part 1 (plan 04-08): carbon-inclusive portfolio NPV,
gross helper PVs, 5x5 energy x carbon grid and discount-rate strip.

Everything is a plain formula (no Data Tables). Cached values come from
checkmodel.sensitivity_reference. The tornado and rank stability follow in
plan 04-09; they append below SensitivityLayout.end_row and add checks to
CHECK_NAMES before Sens_Check_All is written (see _finish_checks).
"""
from dataclasses import dataclass
from typing import Tuple

from checkmodel.appraisal import NA_NO_ABATEMENT
from checkmodel.baseline_reference import model_values
from checkmodel.measures_reference import DEFAULT_DIRECT_ETS  # noqa: F401
from checkmodel.sensitivity_reference import compute_sensitivity
from config.measures_catalog import MEASURES
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter,
    setup_sheet)
from xl.selector import direct_ets_state, selector_state
from xl.charts import TornadoLayout, tornado_chart
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
    scalar("Sens_PV_PTNetPerUnit", "PV of pass-through avoided (net), per "
           "unit of pass-through rate", "EUR",
           "=Expo_MEF*(SUMPRODUCT(Sens_ElecSaved,Expo_PETS1_Sel,M_DF)"
           "-Expo_EmbeddedEUA*SUMPRODUCT(Sens_ElecSaved,M_DF))",
           ref.pv_pt_net_unit, "eur")
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

    _tornado(ws, wb, cells, styles, w, ref, nxt, reg, check, rows, ny, idx_r,
             tol, model_values(dataset.inputs))
    _rank_stability(ws, cells, styles, w, ref, nxt, reg, check, ny, idx_r)

    r = nxt()
    w.line(r, "All Sensitivity checks (TRUE = every check passes)",
           "TRUE/FALSE")
    w.scalar(r, "=AND(%s)" % ",".join(CHECK_NAMES), True, "general",
             name="Sens_Check_All")
    apply_bool_check_format(ws, styles, r, 3, r, 3)
    reg("Sens_Check_All", r)
    return SensitivityLayout(tuple(rows), cur[0], HDR_ROW)


NOTE_UNTESTED = (
    "Not tested in-sheet (they change replacement timing or sizing, which "
    "needs Data Tables): LED and VSD lifetime, heat pump temperature share. "
    "Their effect is Python-verified and stated on the Notes sheet.")
NOTE_RANK = (
    "A company often demands more than its cost of capital "
    "before approving a project. If the order of measures does not change at "
    "8-10%, the 'do first' advice is robust.")

RATIONALE = {
    "rate": "Symmetric change around the real discount rate (analyst range, see the Low and High inputs)",
    "elec": "Symmetric percentage band for energy price uncertainty (analyst range, see the Low and High inputs)",
    "gas": "Symmetric percentage band for energy price uncertainty (analyst range, see the Low and High inputs)",
    "carbon_level": "Low path (Current Policies) vs High path (Net Zero "
                    "2050), NGFS scenarios, cash carbon only",
    "capex": "Symmetric percentage band for early-stage cost estimates (analyst range, see the Low and High inputs)",
    "go": "Symmetric percentage band: the guarantee-of-origin market is thin and "
          "volatile (analyst range, see the Low and High inputs)",
    "ev": "Symmetric percentage band: the EV premium is an uncertain cost line "
          "(analyst range, see the Low and High inputs)",
    "ptr": "Low input taken from the Sijm et al. 60-100% pass-through literature "
           "range; one-sided: 1.0 is the top of that range",
    "mef": "Symmetric percentage band intended to cover the GCV-versus-LHV basis "
           "gap in the marginal emission factor (see the Low and High inputs)",
    "ets2_delay": "One further year of ETS2 delay (open political risk, "
                  "EPRS); one-sided",
    "ngfs_route": "Eurostat conversion route vs the alternative US-CPI route factor "
                  "(Carbon_NGFS_AltRouteFactor, indicative analyst estimate); "
                  "one-sided",
}


def _tornado(ws, wb, cells, styles, w, ref, nxt, reg, check, rows, ny, idx_r,
             tol, vals):
    yr_row = HDR_ROW + 1
    T = {t.driver_id: t for t in ref.tornado}
    calc_eur = styles.get("calc", "eur")
    sx = lambda c: "Measures!%s$%d+1" % (c, idx_r)  # noqa: E731

    w.band(nxt(), "Tornado: what moves the portfolio NPV incl. carbon most? "
           "(D-21)")
    w.note(nxt(), "Each input is moved to a low and a high case, one at a "
           "time; the NPV is recomputed by a closed-form or direct formula "
           "(no Data Tables). Swing = high NPV less low NPV, in absolute "
           "terms.", LABEL_COL)

    def scalar(name, text, unit, f, val, num):
        r = nxt()
        w.line(r, text, unit)
        w.scalar(r, f, val, num, name=name)
        reg(name, r)

    def series(name, text, unit, fn, vals, num):
        r = nxt()
        w.line(r, text, unit)
        w.series(r, fn, vals, num, name=name)
        reg(name, r)
        return r

    scalar("Sens_PV_Capex", "PV of capex (net of subsidy and residual) for "
           "all measures", "EUR",
           "=" + "+".join("M_%s_Capex*M_%s_CapexPVFactor" % (k, k)
                          for k in MEASURE_KEYS), ref.pv_capex, "eur")
    scalar("Sens_PV_EV", "PV of the EV price premium", "EUR",
           "=Base_Fleet_Vehicles*Meas_Fleet_EVPremium*M_Fleet_CapexPVFactor",
           ref.pv_ev, "eur")
    scalar("Sens_RouteRatio", "NGFS alternative route factor relative to the "
           "Eurostat route", "factor",
           "=Carbon_NGFS_AltRouteFactor/Carb_USDtoEUR2025",
           ref.route_ratio, "factor")

    d = vals["Sens_Torn_RateDelta"]
    series("Sens_DF_TornLo", "Discount factor, rate less the tornado delta",
           "factor", lambda k, c: "=1/(1+(Rate_DiscountReal-Sens_Torn_"
           "RateDelta))^Measures!%s$%d" % (c, idx_r),
           [1.0 / (1.0 + ref.rate - d) ** n for n in range(ny)], "dec5")
    series("Sens_DF_TornHi", "Discount factor, rate plus the tornado delta",
           "factor", lambda k, c: "=1/(1+(Rate_DiscountReal+Sens_Torn_"
           "RateDelta))^Measures!%s$%d" % (c, idx_r),
           [1.0 / (1.0 + ref.rate + d) ** n for n in range(ny)], "dec5")

    st = "(Carbon_ETS2_StartYear+Sens_ETS2_StartDelay)"
    rw = series("Sens_Delay_W", "ETS2 blend weight with the delayed start",
                "fraction", lambda k, c: (
                    "=MIN(1,MAX(0,(%s$%d-%s)/MAX(Carbon_ETS2_ConvYear-%s,1)))"
                    % (c, yr_row, st, st)), ref.delay_w, "dec5")
    series("Sens_Delay_P", "ETS2 price path with the delayed start",
           "EUR/tCO2e", lambda k, c: (
               "=IF(%s$%d<%s,0,(1-%s%d)*Carbon_ETS2_StabPrice_EUR2025+"
               "%s%d*INDEX(M_CarbonPrice,%s))" % (c, yr_row, st, c, rw + 1,
                                                  c, rw + 1, sx(c))),
           ref.delay_p, "eur2")
    rp = dict(rows)["Sens_Delay_P"] + 1
    series("Sens_Delay_dStat", "Change in the price paid by stationary "
           "fuels", "EUR/tCO2e", lambda k, c: (
               '=IF(Sel_DirectETS="On",0,%s%d)-INDEX(Expo_PStat2_Sel,%s)'
               % (c, rp, sx(c))), ref.delay_dstat, "eur2")
    series("Sens_Delay_dFleet", "Change in the ETS2 price paid by fleet "
           "diesel", "EUR/tCO2e", lambda k, c: (
               "=%s%d-INDEX(Expo_PETS2_Sel,%s)" % (c, rp, sx(c))),
           ref.delay_dfleet, "eur2")
    series("Sens_Route_dETS1", "ETS1 price change on the alternative NGFS "
           "conversion route", "EUR/tCO2e", lambda k, c: (
               "=INDEX(Carb_Blend_W_ETS1,%s)*INDEX(M_CarbonPrice,%s)"
               "*(Sens_RouteRatio-1)" % (sx(c), sx(c))), ref.route_d1,
           "eur2")
    series("Sens_Route_dETS2", "ETS2 price change on the alternative NGFS "
           "conversion route", "EUR/tCO2e", lambda k, c: (
               "=IF(%s$%d<Carbon_ETS2_StartYear,0,INDEX(Carb_Blend_W_ETS2,%s)"
               "*INDEX(M_CarbonPrice,%s)*(Sens_RouteRatio-1))"
               % (c, yr_row, sx(c), sx(c))), ref.route_d2, "eur2")
    r1 = dict(rows)["Sens_Route_dETS1"] + 1
    r2 = dict(rows)["Sens_Route_dETS2"] + 1
    series("Sens_Route_dStat", "Price change paid by stationary fuels",
           "EUR/tCO2e", lambda k, c: (
               '=IF(Sel_DirectETS="On",%s%d*(1-Carbon_DirectETS_FreeAlloc),'
               '%s%d)' % (c, r1, c, r2)), ref.route_dstat, "eur2")
    nxt()

    # ---- input table ---------------------------------------------------
    hdr = styles.get("header")
    hr = nxt()
    for col, t in ((LABEL_COL, "Driver"), (UNIT_COL, "Unit"),
                   (3, "Low input"), (4, "Base input"), (5, "High input"),
                   (6, "NPV at low"), (7, "NPV at high"), (8, "Swing"),
                   (9, "Rank"), (10, "Rationale")):
        cells.text(ws, hr, col, t, hdr)
    ids = [t.driver_id for t in ref.tornado]
    first = hr + 1
    last = first + len(ids) - 1
    for _ in ids:
        nxt()
    swings = "$I$%d:$I$%d" % (first + 1, last + 1)
    pct, fac = "pct", "factor"
    P = "Sens_PortfolioNPV"
    spec = {
        "rate": ("fraction", "=Rate_DiscountReal-Sens_Torn_RateDelta",
                 "=Rate_DiscountReal", "=Rate_DiscountReal+Sens_Torn_"
                 "RateDelta", "=SUMPRODUCT(Sens_PortfolioCF,Sens_DF_TornLo)",
                 "=SUMPRODUCT(Sens_PortfolioCF,Sens_DF_TornHi)", pct),
        "elec": ("price change", "=-Sens_Torn_ElecPct", 0.0,
                 "=Sens_Torn_ElecPct",
                 "=%s-Sens_Torn_ElecPct*Sens_PV_Elec" % P,
                 "=%s+Sens_Torn_ElecPct*Sens_PV_Elec" % P, pct),
        "gas": ("price change", "=-Sens_Torn_GasPct", 0.0,
                "=Sens_Torn_GasPct",
                "=%s-Sens_Torn_GasPct*Sens_PV_Gas" % P,
                "=%s+Sens_Torn_GasPct*Sens_PV_Gas" % P, pct),
        "carbon_level": ("scenario path", "Low path", "Selected path",
                         "High path",
                         "=Sens_PortfolioNPV_Fin+SUMPRODUCT(Expo_Avoided_CP,"
                         "M_DF,M_Op)",
                         "=Sens_PortfolioNPV_Fin+SUMPRODUCT(Expo_Avoided_"
                         "NZ50,M_DF,M_Op)", None),
        "capex": ("cost change", "=-Sens_Torn_CapexPct", 0.0,
                  "=Sens_Torn_CapexPct",
                  "=%s+Sens_Torn_CapexPct*Sens_PV_Capex" % P,
                  "=%s-Sens_Torn_CapexPct*Sens_PV_Capex" % P, pct),
        "go": ("price change", "=-Sens_Torn_GOPct", 0.0, "=Sens_Torn_GOPct",
               "=%s+Sens_Torn_GOPct*Sens_PV_GO" % P,
               "=%s-Sens_Torn_GOPct*Sens_PV_GO" % P, pct),
        "ev": ("cost change", "=-Sens_Torn_EVPct", 0.0, "=Sens_Torn_EVPct",
               "=%s+Sens_Torn_EVPct*Sens_PV_EV" % P,
               "=%s-Sens_Torn_EVPct*Sens_PV_EV" % P, pct),
        "ptr": ("pass-through rate", "=Sens_Torn_PTRLow", "=Pass_PTR",
                "=Pass_PTR",
                "=%s+(Sens_Torn_PTRLow-Pass_PTR)*Sens_PV_PTNetPerUnit" % P,
                "=%s" % P, pct),
        "mef": ("factor change", "=-Sens_Torn_MEFPct", 0.0,
                "=Sens_Torn_MEFPct",
                "=%s-Sens_Torn_MEFPct*Sens_PV_PTNet" % P,
                "=%s+Sens_Torn_MEFPct*Sens_PV_PTNet" % P, pct),
        "ets2_delay": ("ETS2 start year", "=Carbon_ETS2_StartYear",
                       "=Carbon_ETS2_StartYear",
                       "=Carbon_ETS2_StartYear+Sens_ETS2_StartDelay",
                       "=%s" % P,
                       "=%s+SUMPRODUCT(Sens_tStatSaved,Sens_Delay_dStat,"
                       "M_DF)+SUMPRODUCT(Sens_tFleetSaved,Sens_Delay_dFleet,"
                       "M_DF)" % P, "year"),
        "ngfs_route": ("route factor vs Eurostat", 1.0, 1.0,
                       "=Sens_RouteRatio", "=%s" % P,
                       "=%s+SUMPRODUCT(Sens_tStatSaved,Sens_Route_dStat,"
                       "M_DF)+SUMPRODUCT(Sens_tFleetSaved,Sens_Route_dETS2,"
                       "M_DF)+Expo_MEF*Pass_PTR*SUMPRODUCT(Sens_ElecSaved,"
                       "Sens_Route_dETS1,M_DF)" % P, fac),
    }
    for i, did in enumerate(ids):
        r = first + i
        t = T[did]
        unit, lo, ba, hi, nl, nh, num = spec[did]
        cells.text(ws, r, LABEL_COL, t.label, styles.get("label"))
        cells.text(ws, r, UNIT_COL, unit, styles.get("unit"))
        base_val = {"rate": ref.rate, "ptr": vals["Pass_PTR"],
                    "ets2_delay": t.low_input}.get(did, 0.0)
        if did == "ngfs_route":
            base_val = 1.0
        for col, item, val in ((3, lo, t.low_input), (4, ba, base_val),
                               (5, hi, t.high_input)):
            if isinstance(item, str) and item.startswith("="):
                cells.formula(ws, r, col, item, styles.get("calc", num),
                              value=float(val))
            elif isinstance(item, str):
                cells.text(ws, r, col, item, styles.get("label"))
            else:
                cells.number(ws, r, col, item, styles.get("calc", num))
        cells.formula(ws, r, 6, nl, calc_eur, value=t.npv_low)
        cells.formula(ws, r, 7, nh, calc_eur, value=t.npv_high)
        cells.formula(ws, r, 8, "=ABS(H%d-G%d)" % (r + 1, r + 1), calc_eur,
                      value=t.swing)
        cells.formula(
            ws, r, 9, "=RANK(I%d,%s,0)+COUNTIF($I$%d:I%d,I%d)" % (
                r + 1, swings, first, r, r + 1) if i else
            "=RANK(I%d,%s,0)" % (r + 1, swings),
            styles.get("calc", "int"), value=t.rank)
        cells.text(ws, r, 10, RATIONALE[did], styles.get("note"))
    reg("Sens_Torn_First", first)
    ranks = "$J$%d:$J$%d" % (first + 1, last + 1)
    cells.define_name("Sens_Torn_Ranks", "=%s!%s" % (SHEET, ranks))
    nxt()

    # ---- sorted table ----------------------------------------------------
    w.band(nxt(), "Tornado, sorted by swing (largest first)")
    sh = nxt()
    for col, t_ in ((LABEL_COL, "Driver"), (UNIT_COL, "Position"),
                    (3, "Downside"), (4, "Upside")):
        cells.text(ws, sh, col, t_, hdr)
    sfirst = sh + 1
    order = sorted(ref.tornado, key=lambda x: x.rank)
    for i, t in enumerate(order):
        r = nxt()
        R = r + 1
        pos = "$C%d" % R
        cells.formula(ws, r, UNIT_COL, ("=C%d+1" % (R - 1)) if i else "=1",
                      styles.get("calc", "int"), value=i + 1)
        cells.formula(ws, r, LABEL_COL, "=INDEX($B$%d:$B$%d,MATCH(%s,%s,0))"
                      % (first + 1, last + 1, pos, ranks),
                      styles.get("calc"), value=t.label)
        lo = "INDEX($G$%d:$G$%d,MATCH(%s,%s,0))" % (first + 1, last + 1,
                                                     pos, ranks)
        hi = lo.replace("$G$", "$H$")
        base = ref.npv_incl
        dn = min(t.npv_low, t.npv_high) - base
        up = max(t.npv_low, t.npv_high) - base
        for col, fn, val in ((3, "MIN", dn), (4, "MAX", up)):
            x = "%s(%s,%s)-Sens_PortfolioNPV" % (fn, lo, hi)
            cells.formula(ws, r, col, "=IF(ABS(%s)<=%s,0,%s)" % (x, tol, x),
                          calc_eur, value=0.0 if abs(val) <= 1.0 else val)
    slast = sfirst + len(order) - 1
    reg("Sens_TornSorted_First", sfirst)
    cells.define_name("Sens_TornPos", "=%s!$C$%d:$C$%d" % (
        SHEET, sfirst + 1, slast + 1))
    cells.define_name("Sens_TornDown", "=%s!$D$%d:$D$%d" % (
        SHEET, sfirst + 1, slast + 1))
    cells.define_name("Sens_TornUp", "=%s!$E$%d:$E$%d" % (
        SHEET, sfirst + 1, slast + 1))
    tr = nxt()
    w.line(tr, "Chart title", "text")
    title = "Tornado: change in portfolio NPV incl. carbon vs base (EUR): "
    cells.formula(ws, tr, 3, '="%s"&Sel_Scenario&" scenario, "&Sel_Basis&'
                  '" basis"' % title, styles.get("calc"),
                  value="%s%s scenario, %s basis" % (title, ref.scenario,
                                                     ref.basis))
    cells.define_name("Sens_TornadoTitle", "=%s!$D$%d" % (SHEET, tr + 1))
    reg("Sens_TornadoTitle", tr)
    w.note(nxt(), NOTE_UNTESTED, LABEL_COL)
    layout = TornadoLayout(SHEET, sfirst, slast, LABEL_COL, 3, 4)
    chart = tornado_chart(wb, layout, "=%s!$D$%d" % (SHEET, tr + 1))
    cells.insert_chart(ws, "G%d" % (sh + 1), chart)
    for _ in range(12):
        nxt()
    check("Sens_Check_Torn", "Check: tornado ranks form a complete 1..n "
          "ordering and the bars bracket the base",
          "=AND(MAX(Sens_Torn_Ranks)=COUNT(Sens_Torn_Ranks),"
          "SUM(Sens_Torn_Ranks)=SUM(Sens_TornPos),MAX(Sens_TornDown)<=0,MIN(Sens_TornUp)>=0)", True)
    nxt()




def _rank_stability(ws, cells, styles, w, ref, nxt, reg, check, ny, idx_r):
    tol = "Const_CheckTolMoney"
    hdr = styles.get("header")
    calc = lambda n: styles.get("calc", n)  # noqa: E731
    link = lambda n: styles.get("link", n)  # noqa: E731
    w.band(nxt(), "MACC rank stability at real hurdle rates (D-22; follows "
           "Sel_Basis)")
    rs = ref.rank_stab
    # DF rows for the three hurdles
    for i, h in enumerate(ref.hurdles):
        r = nxt()
        w.line(r, "Discount factor at real hurdle rate %d" % (i + 1),
               "factor")
        w.series(r, (lambda j: lambda k, c: "=1/(1+Sens_Hurdle_%d)^Measures!"
                     "%s$%d" % (j, c, idx_r))(i + 1),
                 [1.0 / (1.0 + h) ** n for n in range(ny)], "dec5",
                 name="Sens_DF_H%d" % (i + 1))
        reg("Sens_DF_H%d" % (i + 1), r)
    g = nxt()
    for col, t in ((5, "Levelised cost (EUR/tCO2e) at real hurdle rate"),
                   (9, "Rank at real hurdle rate"),
                   (12, "Same / Changed vs base rank")):
        cells.text(ws, g, col, t, styles.get("note"))
    rr = nxt()
    w.line(rr, "real hurdle rate", "fraction")
    cells.formula(ws, rr, 4, "=Rate_DiscountReal", link("pct"),
                  value=ref.rate)
    cells.formula(ws, rr, 8, "=Rate_DiscountReal", link("pct"),
                  value=ref.rate)
    for i, h in enumerate(ref.hurdles):
        for col in (5 + i, 9 + i, 12 + i):
            cells.formula(ws, rr, col + (0 if col != 9 + i else 0),
                          "=Sens_Hurdle_%d" % (i + 1), link("pct"), value=h)
    # column map: D elig, E lev base, F-H lev hurdle, I rank base,
    # J-L rank hurdle, M-O flags
    th = nxt()
    for col, t in ((LABEL_COL, "Measure"), (3, "Eligible"),
                   (4, "Base rate"), (5, "Hurdle 1"), (6, "Hurdle 2"),
                   (7, "Hurdle 3"), (8, "Base rank"), (9, "Hurdle 1"),
                   (10, "Hurdle 2"), (11, "Hurdle 3"), (12, "Hurdle 1"),
                   (13, "Hurdle 2"), (14, "Hurdle 3")):
        cells.text(ws, th, col, t, hdr)
    first = nxt()
    rows_ = [first] + [nxt() for _ in MEASURE_KEYS[1:]]
    last = rows_[-1]
    elig = "$D$%d:$D$%d" % (first + 1, last + 1)
    dfs = ["M_DF", "Sens_DF_H1", "Sens_DF_H2", "Sens_DF_H3"]
    levcols = ["E", "F", "G", "H"]
    rkcols = ["I", "J", "K", "L"]
    for i, key in enumerate(MEASURE_KEYS):
        r = rows_[i]
        R = r + 1
        row = rs[i]
        cells.text(ws, r, LABEL_COL, SHORT[key], styles.get("label"))
        cells.formula(ws, r, 3, "=M_%s_Eligible" % key, link("int"),
                      value=1 if row.lev_base != "n/a" else 0)
        levs = (row.lev_base, row.lev_r1, row.lev_r2, row.lev_r3)
        for j in range(4):
            f = ('=IF($D%d=1,-SUMPRODUCT(M_%s_CF,%s)/SUMPRODUCT(M_%s_tSel,%s)'
                 ',"%s")' % (R, key, dfs[j], key, dfs[j], NA_NO_ABATEMENT))
            cells.formula(ws, r, 4 + j, f, calc("eur_per_t"),
                          value=levs[j] if levs[j] != "n/a"
                          else NA_NO_ABATEMENT)
        rks = (row.rank_base, row.rank_r1, row.rank_r2, row.rank_r3)
        for j in range(4):
            lc = levcols[j]
            costs = "%s$%d:%s$%d" % (lc, first + 1, lc, last + 1)
            earlier = ("COUNTIF(%s$%d:%s%d,%s%d)" % (lc, first + 1, lc, R - 1,
                                                    lc, R)
                       if i else "0")
            f = ("=IF($D%d=1,RANK(%s%d,%s,1)+%s,COUNT(%s)+COUNTIF($D$%d:$D%d,"
                 "0))" % (R, lc, R, costs, earlier, costs, first + 1, R))
            cells.formula(ws, r, 8 + j, f, calc("int"), value=rks[j])
        for j in range(3):
            cells.formula(ws, r, 12 + j, '=IF(%s%d=$I%d,"Same","Changed")'
                          % (rkcols[j + 1], R, R), calc("general"),
                          value="Same" if rks[j + 1] == rks[0] else "Changed")
    flags = "$M$%d:$O$%d" % (first + 1, last + 1)
    cells.define_name("Sens_RankStab_Flags", "=%s!%s" % (SHEET, flags))
    reg("Sens_RankStab_Flags", first)
    nchanged = sum(1 for i in range(len(rs)) for j in range(3)
                   if (rs[i].rank_r1, rs[i].rank_r2, rs[i].rank_r3)[j]
                   != rs[i].rank_base)
    r = nxt()
    w.line(r, "Number of changed ranks across the three hurdle rates",
           "count")
    w.scalar(r, '=COUNTIF(Sens_RankStab_Flags,"Changed")', nchanged, "int",
             name="Sens_RankStab_AnyChanged")
    reg("Sens_RankStab_AnyChanged", r)
    w.note(nxt(), NOTE_RANK, LABEL_COL)
    terms = ",".join("ABS(IF($D$%d=1,$E$%d,0)-IF($D$%d=1,M_%s_LevCost,0))<=%s"
                     % (rows_[i] + 1, rows_[i] + 1, rows_[i] + 1, k, tol)
                     for i, k in enumerate(MEASURE_KEYS))
    check("Sens_Check_LevBase", "Check: base-rate levelised cost equals the "
          "Measures levelised cost for every eligible measure",
          "=AND(%s)" % terms, True)
    nxt()
