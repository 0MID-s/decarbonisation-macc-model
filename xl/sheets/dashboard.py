"""Dashboard (plan 05-04, OUT-03, D-07 to D-10): headline tiles, selector
display, three charts, navigation and one-page print.

Links only. The formulas on this sheet are =Name links, one CHOOSE per helper
cell for the selected basis, one ratio of two untagged helper cells and text
labels. Nothing is calculated here; the owner sheets do the work.
"""
from checkmodel.outputs_reference import compute_outputs
from xl.charts import bridge_chart, exposure_scenario_chart, macc_area_chart
from xl.layout import dashboard_print, setup_sheet
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import get_or_add, write_title_band
from xl.styles import SheetKind, apply_check_format

SHEET = "Dashboard"
FIRST_COL = 1
N_COLS = 5
LAST_COL = FIRST_COL + N_COLS - 1
COL_WIDTH = 37.5

PURPOSE = "Headline results of the decarbonisation business case"
NOTE = ("How to read this: every number here is a link to the sheet that "
        "calculates it. Change the scenario, basis or Direct-ETS toggle on "
        "Inputs and all tiles and charts update. Maison Veritas is a "
        "representative firm built from Belgian sector averages (Eurostat), "
        "not a real company.")

R_SEL = 4
R_TILE = 8          # tile label row; value/sub rows follow
R_CHART1 = 17
R_CHART2 = 38
R_DATA = 58

TIER_KEYS = (("Low", "CP"), ("Central", "NDC"), ("High", "NZ50"))


def build_dashboard(wb, styles, cells, dataset, cfg, out):
    basis, scenario = selector_state(dataset)
    ets = direct_ets_state(dataset)
    ref = compute_outputs(dataset.inputs, basis, scenario, ets)
    lab = ref.labels
    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.DASHBOARD, freeze_row=3, freeze_col=0)
    write_title_band(cells, styles, ws, "Dashboard", PURPOSE, NOTE, LAST_COL)
    ws.set_column(0, 0, 2.0)
    ws.set_column(FIRST_COL, LAST_COL, COL_WIDTH)
    ws.set_column(LAST_COL + 1, LAST_COL + 1, 2.0)
    lbl = styles.get("label")
    tl = styles.get("tile_label")
    nav = styles.get("nav_link")
    sec = styles.get("section")
    link = styles.get("link")
    note = styles.get("note")

    # --- selector strip (D-09): display only, change on Inputs
    sel = lab["selectors"]
    cells.text(ws, R_SEL, 1, "Active selection", sec)
    for c in range(2, LAST_COL + 1):
        cells.blank(ws, R_SEL, c, sec)
    r = R_SEL + 1
    for c, (title, name) in enumerate((("Scenario", "Sel_Scenario"),
                                       ("Basis", "Sel_Basis"),
                                       ("Direct EU ETS", "Sel_DirectETS"))):
        cells.text(ws, r, 1 + c, title, lbl)
        cells.formula(ws, r + 1, 1 + c, "=" + name, link, value=sel[name])
    sheet, cell = cells.target_of("Sel_Scenario")
    cells.internal_link(ws, r + 1, 4, sheet, cell, "Change on Inputs", nav,
                        "Open the selectors on the Inputs sheet")

    def tile_cell(row, col, name, f, value, num):
        cells.formula(ws, row, col, f, styles.get("tile", num), value=value)
        cells.define_name(name, "=%s!$%s$%d" % (
            SHEET, "ABCDEFGH"[col], row + 1))

    def label(row, col, f, value):
        if f is None:
            cells.text(ws, row, col, value, tl)
        else:
            cells.formula(ws, row, col, f, tl, value=value)

    t = R_TILE
    for rr, h in ((t, 30), (t + 1, 26), (t + 2, 30), (t + 3, 26),
                  (t + 4, 30), (t + 5, 26), (t + 6, 30), (t + 7, 30)):
        ws.set_row(rr, h)
    # (1) portfolio NPV
    c = 1
    label(t, c, None, "Portfolio NPV, real EUR 2025")
    tile_cell(t + 1, c, "Dash_NPVFin", "=M_Portfolio_NPV", ref.npv_fin, "eur")
    label(t + 2, c, None, "Financial NPV, excluding carbon")
    tile_cell(t + 3, c, "Dash_NPVIncl", "=Sens_PortfolioNPV", ref.npv_incl,
              "eur")
    label(t + 4, c,
          '="Including carbon cash savings, "&Sel_Scenario&" scenario, "'
          '&Sel_Basis&" basis"', lab["npv_incl"])
    # (2) abatement
    c = 2
    label(t, c, '="Abated per year, "&Sel_Basis&" basis"', lab["abated"])
    tile_cell(t + 1, c, "Dash_AbatedSel",
              "=CHOOSE(M_BasisIdx,M_Total_tLB,M_Total_tMB)", ref.abated_sel,
              "tco2e")
    # CR-01: the tile is the net sum; the MACC omits non-abating measures
    label(t + 2, c, None,
          "tCO2e per year, net of all six measures; the MACC omits any "
          "negative one")
    # (3) share of Scope 1+2
    c = 3
    label(t, c, '="Share of Scope 1+2 abated, "&Sel_Basis&" basis"',
          lab["share"])
    tile_cell(t + 1, c, "Dash_Share", "=Dash_AbatedSel/Dash_S12Sel", ref.share,
              "pct")
    label(t + 2, c, None, "Scope 1+2 on the same basis, tCO2e")
    tile_cell(t + 3, c, "Dash_S12Sel",
              "=CHOOSE(M_BasisIdx,BL_S12_LB,BL_S12_MB)", ref.s12_sel, "tco2e")
    # (4) cost of not acting
    c = 4
    label(t, c, '="Cost of not acting, "&Sel_Scenario&" scenario"',
          lab["cost"])
    tile_cell(t + 1, c, "Dash_CostNotActing", "=Expo_CumBAU_Sel",
              ref.cum_bau_sel, "eur")
    # CR-02: the cumulative sums only the exposure window, which ends at
    # Expo_LastYear (NPVs still run to the last model year); say so live.
    label(t + 2, c, '="Cash carbon cost "&Time_FirstYear&" to "&Expo_LastYear'
          '&" (exposure window), undiscounted, real EUR 2025"',
          lab["cost_window"])
    tile_cell(t + 3, c, "Dash_CostAvoided", "=Expo_CumAvoided_Sel",
              ref.cum_avoided_sel, "eur")
    label(t + 4, c, None, "Carbon cost avoided by the measures (undiscounted)")
    tile_cell(t + 5, c, "Dash_CostNotActingDisc", "=Expo_DiscBAU_Sel",
              ref.disc_bau_sel, "eur")
    label(t + 6, c, None, "Same window, discounted at the real rate")
    label(t + 7, c, None, "Under the Low scenario this can be negative: the "
          "electricity bill falls when carbon prices fall (pass-through).")
    # (5) model checks
    c = 5
    label(t, c, None, "Model checks")
    cells.formula(ws, t + 1, c, "=Chk_Master", styles.get("flag"),
                  value=ref.chk_master)
    cells.define_name("Dash_Flag", "=%s!$F$%d" % (SHEET, t + 2))
    apply_check_format(ws, styles, t + 1, c, t + 1, c)
    tile_cell(t + 3, c, "Dash_FailCount", "=Chk_FailCount",
              ref.chk_fail_count, "count")
    label(t + 4, c, None, "failing checks")
    sheet, cell = "Checks", "A1"
    cells.internal_link(ws, t + 5, c, sheet, cell, "Go to Checks", nav,
                        "Open the Checks sheet")

    # --- chart data block (links only)
    d = R_DATA
    cells.text(ws, d, 1, "Chart data (links to the Exposure results)", sec)
    for cc in range(2, LAST_COL + 1):
        cells.blank(ws, d, cc, sec)
    cells.formula(ws, d + 1, 1,
                  '="Cost of not acting by scenario: BAU vs with measures ("'
                  '&Sel_Basis&" basis, Direct ETS "&Sel_DirectETS&")"',
                  styles.get("calc"), value=lab["scen_chart"])
    cells.define_name("Dash_ScenChartTitle",
                      "=%s!$B$%d" % (SHEET, d + 2))
    hdr = styles.get("header")
    hr = d + 2
    for cc, h in enumerate(("Scenario", "BAU", "With measures", "Avoided")):
        cells.text(ws, hr, 1 + cc, h, hdr)
    for k, (tier, key) in enumerate(TIER_KEYS):
        row = hr + 1 + k
        blk = ref.chart_block[tier]
        cells.text(ws, row, 1, tier, lbl)
        for cc, (nm, v) in enumerate((("Expo_CumBAU_", blk["cum_bau"]),
                                      ("Expo_CumWith_", blk["cum_with"]),
                                      ("Expo_CumAvoided_",
                                       blk["cum_avoided"]))):
            cells.formula(ws, row, 2 + cc, "=" + nm + key,
                          styles.get("link", "eur"), value=v)
    first, last = hr + 1, hr + len(TIER_KEYS)

    # --- charts (D-08): three new objects, formula-linked titles
    m = out["macc"]
    msheet, mcell = cells.target_of("MACC_Title")
    macc_title = "=%s!$%s$%s" % (msheet, mcell[0], mcell[1:])
    cells.insert_chart(ws, "B%d" % (R_CHART1 + 1), macc_area_chart(
        wb, m.a_layout, title=macc_title, major_unit=m.chart_step,
        label_col=7, size=(700, 330), axis_max=None))
    bsheet, bcell = cells.target_of("Expo_BridgeTitle")
    bridge_title = "=%s!$%s$%s" % (bsheet, bcell[0], bcell[1:])
    cells.insert_chart(ws, "D%d" % (R_CHART1 + 1),
                       bridge_chart(wb, out["bridge"], bridge_title,
                                    (620, 330)), {"x_offset": 170})
    cells.insert_chart(ws, "B%d" % (R_CHART2 + 1), exposure_scenario_chart(
        wb, SHEET, hr, first, last, 1, 2, 3, "=%s!$B$%d" % (SHEET, d + 2),
        (520, 300)))

    # --- navigation strip beside the scenario chart
    n = R_CHART2
    cells.text(ws, n, 3, "Go to", sec)
    cells.blank(ws, n, 4, sec)
    cells.blank(ws, n, 5, sec)
    tsheet, tcell = cells.target_of("Sens_TornadoTitle")
    for k, (txt, sh, ce, tip) in enumerate((
            ("MACC (ranked measures)", "MACC", "A1", "Open the MACC sheet"),
            ("Bridge: BAU to after acting", bsheet, bcell,
             "Open the bridge on the Exposure sheet"),
            ("Sensitivity tornado", tsheet, tcell,
             "Open the tornado on the Sensitivity sheet"),
            ("Checks", "Checks", "A1", "Open the Checks sheet"),
            ("Disclosure map", "Disclosure", "A1",
             "Open the IFRS S2 and ESRS E1 mapping"))):
        cells.internal_link(ws, n + 1 + k, 3, sh, ce, txt, nav, tip)
    cells.text(ws, n + 6, 3, "Source of every figure: the sheet named in each "
               "link; inputs and sources are on Inputs and Sources.", note)

    last_row = last + 1
    dashboard_print(ws, last_row, LAST_COL + 1)
    return {"last_row": last_row, "first_col": FIRST_COL, "last_col": LAST_COL}
