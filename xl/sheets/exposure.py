"""Exposure sheet, part 1 (plan 04-05): per-year cash carbon cost channels.

For each of Low / Central / High side by side, BAU and with the six measures:
ETS2 fuel cost, direct EU ETS1 cost (zero unless Sel_DirectETS = On) and the
electricity pass-through. Every cost row is built from visible tonnes, MWh
and price rows. Cached values come from checkmodel.exposure_reference.
Totals, ICP, CBAM and checks follow in plan 04-06, the bridge in 04-07; they
append below ExposureLayout.end_row.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

from checkmodel.baseline_reference import compute_baseline, model_values
from checkmodel.exposure_reference import compute_exposure
from checkmodel.carbon_reference import SCENARIOS
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter,
    setup_sheet)
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import write_title_band
from xl.sheets.rowwriter import RowWriter
from config.measures_catalog import MEASURES
from xl.charts import BridgeLayout, bridge_chart
from xl.styles import SheetKind, apply_bool_check_format

SHEET = "Exposure"
LAST_COL = TIMELINE_LAST_COL
HDR_ROW = 4  # zero-based; Excel row 5
SCALAR_COL = 3  # column D
NOTE_COL = 4  # column E

TITLE_NOTE = (
    "Cash cost of carbon in real EUR 2025; positive = the firm pays. Three "
    "channels only: ETS2 on fuels, direct EU ETS1 (a switch, off by default) "
    "and the electricity pass-through. The internal carbon price lens is "
    "separate and is never added to these")
TBL_NOTE_COL = 8  # column I, right of the four table columns D to G
CHECK_NAMES = []  # type: list  # module-level so plan 04-07 can add checks
MEASURE_KEYS = ("LED", "VSD", "HP", "Fleet", "PV", "RC")
NOTE_NOT_ADDED = ("Never added to the internal carbon price below; cash "
                  "channels only")
NOTE_LOW = (
    "Under Low the ETS1 price falls below the 2025 level already in the "
    "tariff, so the pass-through term is negative (the bill falls). Saving "
    "electricity then removes part of that gain, which is why some measures "
    "show a negative carbon saving under Low.")


@dataclass(frozen=True)
class ExposureLayout:
    rows: Tuple[Tuple[str, int], ...]
    end_row: int  # first free zero-based row below part 1
    hdr_row: int


def build_exposure(wb, styles, cells, dataset, cfg, layouts):
    state = selector_state(dataset)
    ref = compute_exposure(dataset.inputs, state[0], state[1],
                           direct_ets_state(dataset))
    ny = len(ref.years)
    ms_rows = layouts["measures"].rows
    gas_r, dsl_r, s5_r = (ms_rows["gasA"] + 1, ms_rows["dslA"] + 1,
                          ms_rows["s5"] + 1)

    ws = wb.add_worksheet(SHEET)
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=HDR_ROW)
    write_title_band(
        cells, styles, ws, "Exposure",
        "Carbon cost exposure 2026-2035: what Maison Veritas would pay for "
        "carbon, by scenario and channel, with and without the six measures",
        TITLE_NOTE, LAST_COL)
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
    h = HDR_ROW + 1

    w = RowWriter(ws, cells, styles, SHEET, LAST_COL, SCALAR_COL, NOTE_COL, ny)
    rows = []  # type: list
    carbon_rows = dict(layouts["carbon"].rows)
    cur = [HDR_ROW + 2]

    def nxt(skip=0):
        r = cur[0]
        cur[0] += 1 + skip
        return r

    def series(name, text, unit, fn, vals, num, link=False, note=None):
        r = nxt()
        w.line(r, text, unit)
        w.series(r, fn, vals, num, link=link, name=name)
        if note:
            w.note(r, note)
        rows.append((name, r))
        return r

    def scalar(name, text, unit, f, val, num, note=None):
        r = nxt()
        w.line(r, text, unit)
        w.scalar(r, f, val, num, name=name)
        if note:
            w.note(r, note)
        rows.append((name, r))
        return r

    def a(c, name):
        return "%s$%d" % (c, dict(rows)[name] + 1)

    # ---- timing -------------------------------------------------------
    w.band(nxt(), "Timing")
    series("Expo_Window", "In exposure window (1 = summed in the tables)",
           "flag (1/0)",
           lambda k, c: "=IF(%s$%d<=Expo_LastYear,1,0)" % (c, h),
           [int(x) for x in ref.window], "int",
           note="Exposure tables sum 2026 to Expo_LastYear; later years feed "
                "only the Sensitivity NPV (to 2055)")
    nxt()

    # ---- physical quantities -----------------------------------------
    w.band(nxt(), "Physical quantities (tonnes and MWh)")
    scalar("Expo_MEF", "Marginal emission factor of the price-setting gas "
           "plant", "tCO2/MWh", "=EF_Gas_NCV/Pass_CCGT_Eff", ref.mef, "dec5",
           note="marginal emission factor of the price-setting gas plant, "
                "tCO2 per MWh of electricity")
    scalar("Expo_EmbeddedEUA", "EUA price already inside today's electricity "
           "tariff", "EUR/tCO2", "=Carbon_EUA_Avg2025", ref.embedded_eua,
           "eur2",
           note="carbon cost already inside today's electricity tariff (2025 "
                "EUA); only the change from this level is new cost")
    stat_bau = ("=BL_Gas_MWh*EF_Gas_NCV*Carbon_ETS2_Scope_Gas"
                "+BL_LPG_MWh*EF_LPG_NCV*Carbon_ETS2_Scope_LPG"
                "+BL_Naphtha_MWh*EF_Naphtha_NCV*Carbon_ETS2_Scope_Naphtha"
                "+BL_Other_MWh*EF_GasOil_NCV*Carbon_ETS2_Scope_OtherFuels")
    series("Expo_BAU_tStat", "BAU stationary-fuel tCO2 in ETS2 scope",
           "tCO2", lambda k, c: stat_bau, ref.t_stat_bau, "tco2e")
    fleet_f = ("=BL_Fleet_Litres*EF_Diesel_l/Const_kg_per_t"
               "*Carbon_ETS2_Scope_FleetDiesel")
    series("Expo_BAU_tFleet", "BAU fleet-diesel tCO2 in ETS2 scope", "tCO2",
           lambda k, c: fleet_f, ref.t_fleet_bau, "tco2e")
    series("Expo_BAU_ElecMWh", "BAU purchased electricity", "MWh",
           lambda k, c: "=BL_Elec_MWh", ref.elec_bau, "mwh")
    stat_with = ("=Measures!%%s$%d*EF_Gas_NCV*Carbon_ETS2_Scope_Gas"
                 "+BL_LPG_MWh*EF_LPG_NCV*Carbon_ETS2_Scope_LPG"
                 "+BL_Naphtha_MWh*EF_Naphtha_NCV*Carbon_ETS2_Scope_Naphtha"
                 "+BL_Other_MWh*EF_GasOil_NCV*Carbon_ETS2_Scope_OtherFuels"
                 % gas_r)
    series("Expo_With_tStat", "With measures: stationary-fuel tCO2 in ETS2 "
           "scope (gas after heat pump, M_Stack_GasAfter)", "tCO2",
           lambda k, c: stat_with % c, ref.t_stat_with, "tco2e")
    series("Expo_With_tFleet", "With measures: fleet-diesel tCO2 in ETS2 "
           "scope (M_Stack_DieselAfter)", "tCO2",
           lambda k, c: ("=Measures!%s$%d*EF_Diesel_l/Const_kg_per_t"
                         "*Carbon_ETS2_Scope_FleetDiesel" % (c, dsl_r)),
           ref.t_fleet_with, "tco2e")
    series("Expo_With_ElecMWh", "With measures: purchased electricity "
           "(M_Stack_S5)", "MWh",
           lambda k, c: "=Measures!%s$%d" % (c, s5_r), ref.elec_with, "mwh",
           note="The renewable contract does not reduce purchased MWh: the "
                "firm still buys grid power at a carbon-inclusive price; a "
                "GO certificate changes reported emissions, not the power "
                "price (D-11)")
    nxt()

    # ---- prices -------------------------------------------------------
    w.band(nxt(), "Prices by scenario (from Carbon)")
    for key, tier, _name in SCENARIOS:
        sc = ref.scen[key]
        e1 = carbon_rows["Path_ETS1_%s" % key] + 1
        e2 = carbon_rows["Path_ETS2_%s" % key] + 1
        series("Expo_PETS1_%s" % key, "%s ETS1 cash price" % tier,
               "EUR/tCO2", (lambda r: lambda k, c: "=Carbon!%s$%d" % (c, r))(e1),
               sc.ets1, "eur2", link=True)
        series("Expo_PETS2_%s" % key, "%s ETS2 cash price" % tier,
               "EUR/tCO2", (lambda r: lambda k, c: "=Carbon!%s$%d" % (c, r))(e2),
               sc.ets2, "eur2", link=True)
        series("Expo_PStat1_%s" % key, "%s price paid by stationary fuels, "
               "direct ETS1 (net of free allocation)" % tier, "EUR/tCO2",
               (lambda kk: lambda k, c: (
                   '=IF(Sel_DirectETS="On",%s*(1-Carbon_DirectETS_FreeAlloc),0)'
                   % a(c, "Expo_PETS1_%s" % kk)))(key),
               sc.p_stat1, "eur2")
        series("Expo_PStat2_%s" % key, "%s price paid by stationary fuels, "
               "ETS2" % tier, "EUR/tCO2",
               (lambda kk: lambda k, c: (
                   '=IF(Sel_DirectETS="On",0,%s)'
                   % a(c, "Expo_PETS2_%s" % kk)))(key),
               sc.p_stat2, "eur2",
               note="stationary fuels carry either an ETS1 or an ETS2 price, "
                    "never both (one switch drives both rows)")
    sel = ref.scen[ref.sel_key]
    for nm, lab, vals in (("PETS1", "ETS1 cash price", sel.ets1),
                          ("PETS2", "ETS2 cash price", sel.ets2),
                          ("PStat1", "stationary direct-ETS1 price",
                           sel.p_stat1),
                          ("PStat2", "stationary ETS2 price", sel.p_stat2)):
        series("Expo_%s_Sel" % nm, "Selected scenario: %s" % lab, "EUR/tCO2",
               (lambda n_: lambda k, c: (
                   "=CHOOSE(M_ScenIdx,%s,%s,%s)" % tuple(
                       a(c, "Expo_%s_%s" % (n_, kk))
                       for kk, _t, _n in SCENARIOS)))(nm),
               vals, "eur2")
    nxt()

    # ---- cash cost per scenario ---------------------------------------
    for key, tier, name in SCENARIOS:
        sc = ref.scen[key]
        w.band(nxt(), "%s scenario (%s): cash carbon cost, EUR 2025"
               % (tier, name))
        for case, lab, ts, tf, em, v2, vd, vp, vt in (
                ("BAU", "BAU", "Expo_BAU_tStat", "Expo_BAU_tFleet",
                 "Expo_BAU_ElecMWh", sc.bau_ets2, sc.bau_dir, sc.bau_pt,
                 sc.bau_total),
                ("With", "With measures", "Expo_With_tStat",
                 "Expo_With_tFleet", "Expo_With_ElecMWh", sc.with_ets2,
                 sc.with_dir, sc.with_pt, sc.with_total)):
            series("Expo_%s_ETS2_%s" % (case, key),
                   "%s: ETS2 fuel cost" % lab, "EUR",
                   (lambda ts, tf, kk: lambda k, c: "=%s*%s+%s*%s" % (
                       a(c, ts), a(c, "Expo_PStat2_%s" % kk), a(c, tf),
                       a(c, "Expo_PETS2_%s" % kk)))(ts, tf, key),
                   v2, "eur")
            series("Expo_%s_DirETS_%s" % (case, key),
                   "%s: direct EU ETS1 cost (zero unless switched on)" % lab,
                   "EUR",
                   (lambda ts, kk: lambda k, c: "=%s*%s" % (
                       a(c, ts), a(c, "Expo_PStat1_%s" % kk)))(ts, key),
                   vd, "eur")
            series("Expo_%s_PT_%s" % (case, key),
                   "%s: electricity pass-through" % lab, "EUR",
                   (lambda em, kk: lambda k, c: (
                       "=%s*Expo_MEF*Pass_PTR*(%s-Expo_EmbeddedEUA)" % (
                           a(c, em), a(c, "Expo_PETS1_%s" % kk))))(em, key),
                   vp, "eur")
            series("Expo_%s_Total_%s" % (case, key),
                   "%s: total cash carbon cost" % lab, "EUR",
                   (lambda cs, kk: lambda k, c: "=%s+%s+%s" % (
                       a(c, "Expo_%s_ETS2_%s" % (cs, kk)),
                       a(c, "Expo_%s_DirETS_%s" % (cs, kk)),
                       a(c, "Expo_%s_PT_%s" % (cs, kk))))(case, key),
                   vt, "eur")
        series("Expo_Avoided_%s" % key, "Avoided cash carbon cost "
               "(BAU minus with measures)", "EUR",
               (lambda kk: lambda k, c: "=%s-%s" % (
                   a(c, "Expo_BAU_Total_%s" % kk),
                   a(c, "Expo_With_Total_%s" % kk)))(key),
               sc.avoided, "eur", note=NOTE_NOT_ADDED)
        if tier == "Low":
            w.note(nxt(), NOTE_LOW, LABEL_COL)
        nxt()

    _results_layer(w, ws, cells, styles, ref, dataset, rows, cur, nxt, a, h,
                   layouts, wb)
    return ExposureLayout(tuple(rows), cur[0], HDR_ROW)


def _results_layer(w, ws, cells, styles, ref, dataset, rows, cur, nxt, a, h,
                   layouts, wb):
    """Plan 04-06: totals, toggle rationale, CBAM, ICP lens, checks."""
    ny = len(ref.years)
    c0 = TIMELINE_FIRST_COL
    hdr = styles.get("header")
    CHECK_NAMES[:] = []

    def reg(name, r):
        rows.append((name, r))

    # ---- (A) cost of not acting vs acting ------------------------------
    w.band(nxt(), "Cost of not acting vs acting, 2026 to Expo_LastYear "
           "(EUR 2025)")
    r = nxt()
    w.line(r, "Scenario")
    for col, txt in ((3, "Low"), (4, "Central"), (5, "High"),
                     (6, "Selected (Sel_Scenario)")):
        cells.text(ws, r, col, txt, hdr)
    keys = [k for k, _t, _n in SCENARIOS]
    chan = (("ets2", "ETS2", "ETS2"), ("dir", "DirETS", "direct EU ETS1"),
            ("pt", "PT", "electricity pass-through"), ("total", "Total",
                                                         "total"))

    def _sel_cell(r, name, val):
        cells.formula(ws, r, 6, "=CHOOSE(M_ScenIdx,D%d,E%d,F%d)"
                      % (r + 1, r + 1, r + 1), styles.get("calc", "eur"),
                      value=val)
        if name:
            cells.define_name(name, "=%s!$G$%d" % (SHEET, r + 1))

    for tag, label, kind, win_df in (
            ("Cum", "Cumulative, undiscounted", "cum", ""),
            ("Disc", "Discounted to 2026 (real rate, 2026 = year 0)", "disc",
             "M_DF,")):
        w.note(nxt(), label, LABEL_COL)
        tot_r = {}
        for case, cl in (("bau", "BAU"), ("with", "With")):
            for ck, cn, ct in chan:
                r = nxt()
                w.line(r, "%s: %s" % ("BAU" if case == "bau" else
                                      "With measures", ct), "EUR")
                for i, key in enumerate(keys):
                    f = "=SUMPRODUCT(Expo_%s_%s_%s,%sExpo_Window)" % (
                        cl, cn, key, win_df)
                    cells.formula(ws, r, 3 + i, f, styles.get("calc", "eur"),
                                  value=_agg(ref.scen[key], kind)[
                                      "%s_%s" % (ck, case)])
                    if ck == "total":
                        cells.define_name("Expo_%s%s_%s" % (tag, cl, key),
                                          "=%s!$%s$%d" % (
                                              SHEET, col_letter(3 + i), r + 1))
                if ck == "total":
                    tot_r[case] = r
                _sel_cell(r, "Expo_%s%s_Sel" % (tag, cl) if ck == "total"
                          else None, _agg(ref.scen[ref.sel_key], kind)[
                              "%s_%s" % (ck, case)])
        r = nxt()
        w.line(r, "Carbon cost avoided (BAU minus with measures)", "EUR")
        for i, key in enumerate(keys):
            col = col_letter(3 + i)
            cells.formula(ws, r, 3 + i, "=%s%d-%s%d" % (
                col, tot_r["bau"] + 1, col, tot_r["with"] + 1),
                styles.get("calc", "eur"),
                value=_agg(ref.scen[key], kind)["avoided"])
            cells.define_name("Expo_%sAvoided_%s" % (tag, key),
                              "=%s!$%s$%d" % (SHEET, col_letter(3 + i), r + 1))
        _sel_cell(r, "Expo_%sAvoided_Sel" % tag,
                  _agg(ref.scen[ref.sel_key], kind)["avoided"])
        w.note(r, "Positive = cash carbon cost saved by acting", TBL_NOTE_COL)
        nxt()
    w.note(nxt(), "Discounted at the real rate with 2026 = year 0, as in the "
           "Measures sheet", LABEL_COL)
    nxt()

    # ---- (B) direct ETS1 toggle ---------------------------------------
    w.band(nxt(), "Direct EU ETS1 toggle (D-14)")
    r = nxt()
    w.line(r, "Sel_DirectETS (selector on Inputs)", "On/Off")
    cells.formula(ws, r, 3, "=Sel_DirectETS", styles.get("link", "general"),
                  value=ref.direct_ets)
    bl = compute_baseline(dict(model_values(dataset.inputs)))
    v = model_values(dataset.inputs)
    r = nxt()
    w.line(r, "Average fuel load of the firm", "MW")
    cells.formula(ws, r, 3, "=BL_FuelLoadMW", styles.get("link", "dec2"),
                  value=bl.fuel_load_mw)
    r = nxt()
    w.line(r, "EU ETS1 combustion threshold (rated thermal input)", "MW")
    cells.formula(ws, r, 3, "=Carbon_ETS1_ThermalThresholdMW",
                  styles.get("link", "dec2"),
                  value=v["Carbon_ETS1_ThermalThresholdMW"])
    w.note(nxt(), "Off by default: the average fuel load is far below the "
           "20 MW rated thermal input threshold (Directive 2003/87/EC Annex "
           "I). On: stationary fuels pay the ETS1 path x (1 - free "
           "allocation) and ETS2 on them switches off (Annex III excludes "
           "fuels used in ETS1 activities; read from Commission material). "
           "Fleet diesel stays in ETS2.", LABEL_COL)
    r = nxt()
    w.line(r, "Toggle effect: selected-scenario discounted BAU direct ETS1 "
           "cost", "EUR")
    cells.formula(ws, r, 3, "=CHOOSE(M_ScenIdx,%s)" % ",".join(
        "SUMPRODUCT(Expo_BAU_DirETS_%s,M_DF,Expo_Window)" % k for k in keys),
        styles.get("calc", "eur"),
        value=ref.scen[ref.sel_key].disc["dir_bau"])
    cells.define_name("Expo_DirETS_DiscSel", "=%s!$D$%d" % (SHEET, r + 1))
    nxt()

    # ---- (C) CBAM screen ----------------------------------------------
    w.band(nxt(), "CBAM relevance screen (D-15)")
    for lab, txt in (
            ("Covered goods", "Annex I of Regulation (EU) 2023/956: cement, "
             "iron and steel, aluminium, fertilisers, hydrogen, electricity"),
            ("Relevance", "Belgian NACE C20 household and chemical products "
             "maker: products are not Annex I goods"),
            ("Verdict", "Not directly in scope; indirect exposure via "
             "imported hydrogen/fertiliser inputs only; monitor scope review "
             "(as of 2026-10-25)")):
        r = nxt()
        w.line(r, lab)
        cells.text(ws, r, 3, txt, styles.get("note"))
    r = nxt()
    w.line(r, "In CBAM scope? (Inputs flag, 1 = yes)", "flag (1/0)")
    cells.formula(ws, r, 3, "=Carbon_CBAM_InScope", styles.get("link", "int"),
                  value=int(v["Carbon_CBAM_InScope"]))
    r = nxt()
    w.line(r, "Source")
    cells.text(ws, r, 3, "Src_CBAM", styles.get("note"))
    w.note(r, "A text screen, not a cost channel", 4)
    nxt()

    # ---- (D) ICP lens -------------------------------------------------
    nxt()
    icp_first = nxt()
    w.band(icp_first, "Management lens: not a cash cost (internal carbon "
           "price, D-12, D-13)")
    r = nxt()
    w.line(r, "Internal carbon price", "EUR/tCO2e")
    cells.formula(ws, r, 3, "=Carbon_ICP_Level", styles.get("link", "eur2"),
                  value=v["Carbon_ICP_Level"])
    cells.define_name("Expo_ICP_Level", "=%s!$D$%d" % (SHEET, r + 1))
    tr = {}

    def icp_series(name, text, unit, fn, vals, num):
        r = nxt()
        w.line(r, text, unit)
        w.series(r, fn, vals, num, name=name)
        reg(name, r)
        tr[name] = r
        return r

    efsel_r = layouts["measures"].rows["ef_sel"] + 1
    icp_series("Expo_ICP_tBAU", "BAU Scope 1 + Scope 2 on the selected basis",
               "tCO2e", lambda k, c: "=BL_Scope1+BL_Heat_MWh*EF_HeatProxy"
               "+BL_Elec_MWh*Measures!%s$%d" % (c, efsel_r),
               ref.icp_t_bau, "tco2e")
    mrows = layouts["measures"].blocks
    cprice_r = layouts["measures"].rows["cprice"] + 1
    icp_series("Expo_ICP_tWith", "With measures: Scope 1 + Scope 2 after the "
               "six measures", "tCO2e",
               lambda k, c: "=%s-%s" % (a(c, "Expo_ICP_tBAU"), "-".join(
                   "Measures!%s$%d" % (c, mrows[m]["tSel"] + 1)
                   for m in MEASURE_KEYS)),
               ref.icp_t_with, "tco2e")
    icp_series("Expo_ICP_BAU", "BAU internal carbon cost (lens)", "EUR",
               lambda k, c: "=%s*Expo_ICP_Level" % a(c, "Expo_ICP_tBAU"),
               ref.icp_bau, "eur")
    icp_series("Expo_ICP_With", "With measures internal carbon cost (lens)",
               "EUR", lambda k, c: "=%s*Expo_ICP_Level"
               % a(c, "Expo_ICP_tWith"), ref.icp_with, "eur")
    icp_series("Expo_ICP_Avoided", "Internal carbon cost avoided (lens)",
               "EUR", lambda k, c: "=%s-%s" % (a(c, "Expo_ICP_BAU"),
                                               a(c, "Expo_ICP_With")),
               ref.icp_avoided, "eur")
    r = icp_series("Expo_ICP_MemoNGFS", "Memo: selected NGFS scenario price, "
                   "for comparison only", "EUR/tCO2",
                   lambda k, c: "=Measures!%s$%d" % (c, cprice_r), ref.icp_memo_ngfs,
                   "eur2")
    for nm, lab, val in (("Expo_ICP_DiscBAU", "BAU", ref.icp_disc_bau),
                         ("Expo_ICP_DiscWith", "With measures",
                          ref.icp_disc_with),
                         ("Expo_ICP_DiscAvoided", "Avoided",
                          ref.icp_disc_avoided)):
        src = {"Expo_ICP_DiscBAU": "Expo_ICP_BAU",
               "Expo_ICP_DiscWith": "Expo_ICP_With",
               "Expo_ICP_DiscAvoided": "Expo_ICP_Avoided"}[nm]
        r = nxt()
        w.line(r, "Discounted to 2026, %s (lens)" % lab, "EUR")
        w.scalar(r, "=SUMPRODUCT(%s,M_DF,Expo_Window)" % src, val, "eur",
                 name=nm)
        reg(nm, r)
    w.note(nxt(), "Policy number for decisions, not a payment: never added "
           "to any cash total, bridge or NPV. Under market-based reporting "
           "the renewable contract lowers this figure with no cash effect.",
           LABEL_COL)
    icp_last = cur[0] - 1
    cells.define_name("Expo_ICP_Band", "=%s!$%s$%d:$%s$%d" % (
        SHEET, col_letter(LABEL_COL), icp_first + 1, col_letter(LAST_COL),
        icp_last + 1))
    nxt()

    # ---- (F) per-measure attribution and bridge (plan 04-07) -----------
    extra_checks = _bridge_layer(w, ws, wb, cells, styles, ref, dataset, rows,
                                 cur, nxt, a, h, layouts)

    # ---- (E) checks ---------------------------------------------------
    w.band(nxt(), "Checks")
    series_pre = nxt()
    w.line(series_pre, "Helper: year before the ETS2 start (1 = yes)",
           "flag (1/0)")
    pre_vals = [1 if y < dataset_value(dataset, "Carbon_ETS2_StartYear")
                else 0 for y in ref.years]
    w.series(series_pre, lambda k, c: "=IF(%s$%d<Carbon_ETS2_StartYear,1,0)"
             % (c, h), pre_vals, "int", name="Expo_PreStart")
    reg("Expo_PreStart", series_pre)

    def check(name, text, f, val):
        r = nxt()
        w.line(r, text, "TRUE/FALSE")
        w.scalar(r, f, bool(val), "general", name=name)
        apply_bool_check_format(ws, styles, r, 3, r, 3)
        CHECK_NAMES.append(name)
        reg(name, r)

    check("Expo_Check_ETS2ZeroBeforeStart", "Check: ETS2 cost is zero before "
          "the ETS2 start year",
          "=AND(%s)" % ",".join("SUMPRODUCT(Expo_PETS2_%s,Expo_PreStart)=0"
                                % k for k in keys),
          all(sum(x * p for x, p in zip(ref.scen[k].ets2, pre_vals)) == 0
              for k in keys))
    check("Expo_Check_ETSExclusive", "Check: a fuel never carries both an "
          "ETS1 and an ETS2 price",
          "=AND(%s)" % ",".join("SUMPRODUCT(Expo_PStat1_%s,Expo_PStat2_%s)=0"
                                % (k, k) for k in keys),
          all(sum(x * y for x, y in zip(ref.scen[k].p_stat1,
                                        ref.scen[k].p_stat2)) == 0
              for k in keys))
    parts = []
    for k in keys:
        for cl in ("BAU", "With"):
            parts.append(
                "ABS(SUM(Expo_%s_Total_%s)-SUM(Expo_%s_ETS2_%s)"
                "-SUM(Expo_%s_DirETS_%s)-SUM(Expo_%s_PT_%s))"
                "<=Const_CheckTolMoney" % ((cl, k) * 4))
    check("Expo_Check_CashIsChannels", "Cash totals contain only ETS2, "
          "direct ETS1 and pass-through (no internal carbon price)",
          "=AND(%s)" % ",".join(parts), True)
    check("Expo_Check_ConvYears", "Check: convergence years are valid",
          "=Carb_Check_ConvYears", True)
    for nm_, text_, f_, val_ in extra_checks:
        check(nm_, text_, f_, val_)
    r = nxt()
    w.line(r, "All Exposure checks (TRUE = every check passes)", "TRUE/FALSE")
    w.scalar(r, "=AND(%s)" % ",".join(CHECK_NAMES), True, "general",
             name="Expo_Check_All")
    apply_bool_check_format(ws, styles, r, 3, r, 3)
    reg("Expo_Check_All", r)


def _agg(scen, kind):
    return scen.cum if kind == "cum" else scen.disc


def dataset_value(dataset, name):
    return model_values(dataset.inputs)[name]


SHORT = {m.key: m.short for m in MEASURES}
NOTE_CONTRACT = ("Contract: zero cash saving. It changes reported "
                 "(market-based) emissions, not the power price or purchased "
                 "MWh (D-11).")
NOTE_NET = ("Heat pump and fleet: ETS2 on gas or diesel falls, but extra "
            "electricity raises the pass-through term; the bar is the net.")
# bridge helper table columns (zero-based)
B_A, B_B, B_BPOS, B_BNEG = 3, 4, 5, 6
B_TPOS, B_TNEG, B_SPOS, B_SNEG, B_IPOS = 7, 8, 9, 10, 11
B_INEG, B_VAL = 13, 14  # column M (12) is the narrow timeline spacer
B_LBL0 = 15  # six label columns P..U: Total pos/neg, Saving pos/neg, Incr...
B_COLOURS = ("#595959", "#009E73", "#D55E00")
BRIDGE_HDRS = (
    (B_A, "Start"), (B_B, "End"), (B_BPOS, "Base above zero"),
    (B_BNEG, "Base below zero"), (B_TPOS, "Total"),
    (B_TNEG, "Total (below zero)"), (B_SPOS, "Cost saving"),
    (B_SNEG, "Cost saving (below zero)"), (B_IPOS, "Cost increase"),
    (B_INEG, "Cost increase (below zero)"), (B_VAL, "Bar value"),
    (B_LBL0, "Label total (+)"), (B_LBL0 + 1, "Label total (-)"),
    (B_LBL0 + 2, "Label saving (+)"), (B_LBL0 + 3, "Label saving (-)"),
    (B_LBL0 + 4, "Label increase (+)"), (B_LBL0 + 5, "Label increase (-)"))


def _split(a_, b_):
    """Python mirror of the helper formulas: (basepos, baseneg, barpos,
    barneg)."""
    bpos = max(0.0, min(a_, b_))
    bneg = min(0.0, max(a_, b_))
    return (bpos, bneg, max(0.0, max(a_, b_)) - bpos,
            min(0.0, min(a_, b_)) - bneg)


def _bridge_layer(w, ws, wb, cells, styles, ref, dataset, rows, cur, nxt, a,
                  h, layouts):
    """Plan 04-07: avoided cash carbon cost per measure and the bridge."""
    ny = len(ref.years)
    ms_blocks = layouts["measures"].blocks
    v = model_values(dataset.inputs)
    scale = v["Const_PerThousand"]
    sel = ref.scen[ref.sel_key]
    keys = MEASURE_KEYS

    def reg(name, r):
        rows.append((name, r))

    # ---- per-measure avoided rows -------------------------------------
    w.band(nxt(), "Carbon cost avoided per measure, selected scenario "
           "(stack order: LED, VSD, heat pump, fleet, solar PV, contract; "
           "D-17)")
    r = nxt()
    w.line(r, "Avoided cash carbon cost, selected scenario (total)", "EUR")
    w.series(r, lambda k, c: "=CHOOSE(M_ScenIdx,%s,%s,%s)" % tuple(
        a(c, "Expo_Avoided_%s" % kk) for kk in ("CP", "NDC", "NZ50")),
        sel.avoided, "eur", name="Expo_Avoided_Sel")
    reg("Expo_Avoided_Sel", r)
    for key in keys:
        b = ms_blocks[key]
        dg, dd, de = b["dG"] + 1, b["dD"] + 1, b["dE"] + 1

        def f(k, c, dg=dg, dd=dd, de=de):
            return (
                "=-(Measures!%s$%d*EF_Gas_NCV*Carbon_ETS2_Scope_Gas*(%s+%s)"
                "+Measures!%s$%d*EF_Diesel_l/Const_kg_per_t"
                "*Carbon_ETS2_Scope_FleetDiesel*%s"
                "+Measures!%s$%d*Expo_MEF*Pass_PTR*(%s-Expo_EmbeddedEUA))" % (
                    c, dg, a(c, "Expo_PStat1_Sel"), a(c, "Expo_PStat2_Sel"),
                    c, dd, a(c, "Expo_PETS2_Sel"),
                    c, de, a(c, "Expo_PETS1_Sel")))
        r = nxt()
        w.line(r, "Avoided: %s" % SHORT[key], "EUR")
        w.series(r, f, ref.measure_avoided[key], "eur",
                 name="Expo_Avoided_%s" % key)
        if key == "RC":
            w.note(r, NOTE_CONTRACT)
        elif key in ("HP", "Fleet"):
            w.note(r, NOTE_NET)
        reg("Expo_Avoided_%s" % key, r)
    tol = v["Const_CheckTolMoney"]
    diff = [d_ if abs(d_) > tol else 0.0 for d_ in (
        sum(ref.measure_avoided[k][n] for k in keys) - sel.avoided[n]
        for n in range(ny))]
    r = nxt()
    w.line(r, "Helper: sum of the six measures minus the selected-scenario "
           "total, floating-point noise below the check tolerance set to 0 (should be zero)", "EUR")
    def _diff_f(k, c):
        x = "(%s-%s)" % ("+".join(a(c, "Expo_Avoided_%s" % kk)
                                  for kk in keys), a(c, "Expo_Avoided_Sel"))
        return "=IF(ABS(%s)<=Const_CheckTolMoney,0,%s)" % (x, x)
    w.series(r, _diff_f, diff, "eur", name="Expo_Avoided_Diff")
    reg("Expo_Avoided_Diff", r)
    for key in keys:
        r = nxt()
        w.line(r, "Discounted avoided: %s" % SHORT[key], "EUR")
        w.scalar(r, "=SUMPRODUCT(Expo_Avoided_%s,M_DF,Expo_Window)" % key,
                 ref.measure_disc_avoided[key], "eur",
                 name="Expo_DiscAvoided_%s" % key)
        reg("Expo_DiscAvoided_%s" % key, r)
    nxt()

    # ---- bridge helper table ------------------------------------------
    w.band(nxt(), "Bridge: BAU to after acting, discounted, selected "
           "scenario (EUR thousand)")
    r = nxt()
    w.line(r, "Chart title (text)")
    title = ("Discounted cash carbon cost over the exposure window, BAU to "
             "after acting: %s scenario, %s basis, direct ETS1 %s" % (
                 ref.scenario, ref.basis, ref.direct_ets))
    cells.formula(
        ws, r, 3,
        '="Discounted cash carbon cost over the exposure window, BAU to '
        'after acting: "&Sel_Scenario&" scenario, "&Sel_Basis&" basis, '
        'direct ETS1 "&Sel_DirectETS', styles.get("calc"), value=title)
    cells.define_name("Expo_BridgeTitle", "=%s!$D$%d" % (SHEET, r + 1))
    reg("Expo_BridgeTitle", r)
    hr = nxt()
    hdr = styles.get("header")
    cells.text(ws, hr, LABEL_COL, "Step", hdr)
    cells.text(ws, hr, UNIT_COL, "Unit", hdr)
    for col, txt in BRIDGE_HDRS:
        cells.text(ws, hr, col, txt, hdr)
    calc = styles.get("calc", "eur")
    first = cur[0]
    steps = [("BAU", "total")] + [(SHORT[k], k) for k in keys] + [
        ("After acting", "total")]
    br = ref.bridge
    cols = {n: [] for n in range(3, B_LBL0 + 6)}

    def L(c):
        return col_letter(c)

    for i, (lab, kind) in enumerate(steps):
        rr = nxt()
        R = rr + 1
        total = kind == "total"
        w.line(rr, lab, "EUR thousand")
        # numeric values (EUR thousand)
        if i == 0:
            av, bv = 0.0, br[0][2] * scale
        elif i == len(steps) - 1:
            av, bv = 0.0, br[-1][2] * scale
        else:
            av = cols[B_B][-1]
            bv = av - ref.measure_disc_avoided[kind] * scale
        bp, bn, brp, brn = _split(av, bv)
        A, B_ = "%s%d" % (L(B_A), R), "%s%d" % (L(B_B), R)
        BP, BN = "%s%d" % (L(B_BPOS), R), "%s%d" % (L(B_BNEG), R)
        barpos = "(MAX(0,MAX(%s,%s))-%s)" % (A, B_, BP)
        barneg = "(MIN(0,MIN(%s,%s))-%s)" % (A, B_, BN)
        if i == 0:
            fa, fb = "=0", "=Expo_DiscBAU_Sel*Const_PerThousand"
        elif i == len(steps) - 1:
            fa, fb = "=0", "=Expo_DiscWith_Sel*Const_PerThousand"
        else:
            fa = "=%s%d" % (L(B_B), R - 1)
            fb = "=%s-Expo_DiscAvoided_%s*Const_PerThousand" % (A, kind)
        val = bv if total else bv - av
        sv = {k_: 0.0 for k_ in range(3, B_LBL0 + 6)}
        sv[B_A], sv[B_B], sv[B_BPOS], sv[B_BNEG] = av, bv, bp, bn
        fm = {B_A: fa, B_B: fb, B_BPOS: "=MAX(0,MIN(%s,%s))" % (A, B_),
              B_BNEG: "=MIN(0,MAX(%s,%s))" % (A, B_),
              B_VAL: ("=%s" % B_) if total else "=%s-%s" % (B_, A)}
        sv[B_VAL] = val
        zero = "=0"
        for c_ in (B_TPOS, B_TNEG, B_SPOS, B_SNEG, B_IPOS, B_INEG):
            fm[c_] = zero
        save = av >= bv
        if total:
            fm[B_TPOS], fm[B_TNEG] = "=" + barpos, "=" + barneg
            sv[B_TPOS], sv[B_TNEG] = brp, brn
        else:
            fm[B_SPOS] = "=IF(%s>=%s,%s,0)" % (A, B_, barpos)
            fm[B_SNEG] = "=IF(%s>=%s,%s,0)" % (A, B_, barneg)
            fm[B_IPOS] = "=IF(%s>%s,%s,0)" % (B_, A, barpos)
            fm[B_INEG] = "=IF(%s>%s,%s,0)" % (B_, A, barneg)
            if save:
                sv[B_SPOS], sv[B_SNEG] = brp, brn
            else:
                sv[B_IPOS], sv[B_INEG] = brp, brn
        negonly = "AND(%s=0,%s<0)" % (barpos, barneg)
        is_negonly = brp == 0 and brn < 0
        val_cell = "%s%d" % (L(B_VAL), R)
        for j in range(6):
            c_ = B_LBL0 + j
            grp, pos = j // 2, j % 2 == 0
            app = (total and grp == 0) or (not total and grp == 1 and save
                                           ) or (not total and grp == 2
                                                 and not save)
            if not ((total and grp == 0) or (not total and grp > 0)):
                fm[c_], sv[c_] = '=""', ""
                continue
            cond = {0: "", 1: "%s>=%s," % (A, B_), 2: "%s>%s," % (B_, A)}[grp]
            core = negonly if not pos else "NOT(%s)" % negonly
            fm[c_] = '=IF(AND(%s%s),%s,"")' % (cond, core, val_cell)
            sv[c_] = val if (app and (is_negonly != pos)) else ""
        for c_ in range(3, B_LBL0 + 6):
            if c_ in (12,):
                continue
            cells.formula(ws, rr, c_, fm[c_], calc, value=sv[c_])
            cols[c_].append(sv[c_])
    last = cur[0] - 1
    for nm, c_ in (("Expo_Br_Start", B_A), ("Expo_Br_End", B_B),
                   ("Expo_Br_BasePos", B_BPOS), ("Expo_Br_BaseNeg", B_BNEG),
                   ("Expo_Br_TotalPos", B_TPOS), ("Expo_Br_TotalNeg", B_TNEG),
                   ("Expo_Br_SavePos", B_SPOS), ("Expo_Br_SaveNeg", B_SNEG),
                   ("Expo_Br_IncPos", B_IPOS), ("Expo_Br_IncNeg", B_INEG),
                   ("Expo_Br_Value", B_VAL)):
        cells.define_name(nm, "=%s!$%s$%d:$%s$%d" % (
            SHEET, L(c_), first + 1, L(c_), last + 1))
    w.note(nxt(), "Read the chart left to right: BAU bill, then one bar per "
           "measure (green falls, orange rises), then the bill after acting. "
           "The invisible base columns only position the bars, so they also "
           "work when the bill is negative.", LABEL_COL)
    chart_row = nxt()
    layout = BridgeLayout(
        SHEET, first, last, LABEL_COL, B_BPOS, B_BNEG,
        ((("Total"), B_TPOS, B_TNEG, B_COLOURS[0], B_LBL0, B_LBL0 + 1),
         (("Cost saving"), B_SPOS, B_SNEG, B_COLOURS[1], B_LBL0 + 2,
          B_LBL0 + 3),
         (("Cost increase"), B_IPOS, B_INEG, B_COLOURS[2], B_LBL0 + 4,
          B_LBL0 + 5)), B_VAL, hr)
    chart = bridge_chart(
        wb, layout, "=%s!$D$%d" % (SHEET, [rr for n, rr in rows
                                           if n == "Expo_BridgeTitle"][0] + 1),
        (980, 460))
    cells.insert_chart(ws, "B%d" % (chart_row + 1), chart)
    for _ in range(24):
        nxt()

    ctol = "Const_CheckTolMoney"
    disc_sum = "+".join("Expo_DiscAvoided_%s" % k for k in keys)
    contract_sq = sum(x * x for x in ref.measure_avoided["RC"])
    return [
        ("Expo_Check_MeasuresReconcile", "Check: the six per-measure rows "
         "sum to the selected-scenario avoided cost",
         "=SUMPRODUCT(Expo_Avoided_Diff,Expo_Avoided_Diff)<=%s" % ctol,
         sum(x * x for x in diff) <= v["Const_CheckTolMoney"]),
        ("Expo_Check_ContractZero", "Check: the renewable contract saves no "
         "cash carbon cost",
         "=SUMPRODUCT(Expo_Avoided_RC,Expo_Avoided_RC)<=%s" % ctol,
         contract_sq <= v["Const_CheckTolMoney"]),
        ("Expo_Check_BridgeSums", "Check: BAU minus the six measure bars "
         "equals the cost after acting",
         "=ABS(Expo_DiscBAU_Sel-(%s)-Expo_DiscWith_Sel)<=%s" % (disc_sum,
                                                                  ctol),
         abs(sel.disc["total_bau"] - sum(
             ref.measure_disc_avoided[k] for k in keys)
             - sel.disc["total_with"]) <= v["Const_CheckTolMoney"]),
    ]
