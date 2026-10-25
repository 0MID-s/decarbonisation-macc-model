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

from checkmodel.exposure_reference import compute_exposure
from checkmodel.carbon_reference import SCENARIOS
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter,
    setup_sheet)
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import write_title_band
from xl.sheets.rowwriter import RowWriter
from xl.styles import SheetKind

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

    return ExposureLayout(tuple(rows), cur[0], HDR_ROW)
