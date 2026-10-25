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
                   layouts)
    return ExposureLayout(tuple(rows), cur[0], HDR_ROW)


def _results_layer(w, ws, cells, styles, ref, dataset, rows, cur, nxt, a, h,
                   layouts):
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

    icp_series("Expo_ICP_tBAU", "BAU Scope 1 + Scope 2 on the selected basis",
               "tCO2e", lambda k, c: "=BL_Scope1+CHOOSE(M_BasisIdx,BL_S2_LB,"
               "BL_S2_MB)", ref.icp_t_bau, "tco2e")
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
