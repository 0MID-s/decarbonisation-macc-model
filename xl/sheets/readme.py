"""ReadMe / model map sheet (plan 05-05, D-12, OQ-2).

Sheet-flow table, selector steps, worked trace paths and conventions in brief.
Prose refers to input ids and defined names, never to input values. Every link
is an internal link written through CellWriter.internal_link (T-05-12).
"""
from xl.layout import LABEL_COL, setup_sheet
from xl.sheets.common import SHEET_INFO, get_or_add, write_title_band
from xl.sheets.notes import CONVENTIONS, WRAP
from xl.styles import SheetKind

SHEET = "ReadMe"
LAST_COL = 4

PURPOSE = "Read-me and model map"
NOTE = ("Start here: how the workbook flows, how to use the selectors and a "
        "few worked paths from a headline number back to its source.")

# Sheets in the D-12 flow order; only those present in the build are listed.
FLOW_ORDER = ("Inputs", "Sources", "Rates", "Carbon", "Baseline", "Measures",
              "MACC", "Exposure", "Sensitivity", "Dashboard", "Disclosure",
              "Checks", "Notes", "Lists")
KEY_OUTPUTS = {
    "Inputs": "Every input by id, plus Sel_Scenario, Sel_Basis, Sel_DirectETS",
    "Sources": "Source register (Src_ ids) behind every sourced input",
    "Rates": "Restated prices and the real discount rate",
    "Carbon": "Carbon price paths by scenario (Carb_ names)",
    "Baseline": "BL_S12_LB, BL_S12_MB, BL_S2_LB, BL_S2_MB",
    "Measures": "M_Portfolio_NPV and M_<measure>_NPV per measure",
    "MACC": "MACC_Rank_Cost, MACC_Rank_Width, MACC_Rank_Measure",
    "Exposure": "Expo_CumBAU_Sel, Expo_CumAvoided_Sel",
    "Sensitivity": "Sens_PortfolioNPV and the grids",
    "Dashboard": "Dash_ tiles (links only)",
    "Disclosure": "IFRS S2 and ESRS E1 rows with the cells that support them",
    "Checks": "Chk_Master and Chk_FailCount",
    "Notes": "Method, limitations, version log",
    "Lists": "List_ names used by the dropdowns",
}
FLOW_ARROWS = ("Inputs -> Rates / Carbon / Baseline -> Measures -> MACC -> "
               "Exposure -> Sensitivity -> Dashboard / Disclosure")

# (step text, defined name of the selector cell)
SELECTORS = (
    ("Step 1. Sel_Scenario (Low / Central / High carbon price path). "
     "Changes the Carbon paths used in Exposure, the MACC reference price, "
     "the bridge and Sensitivity.", "Sel_Scenario"),
    ("Step 2. Sel_Basis (Location-based / Market-based Scope 2). Changes the "
     "abatement tonnes, the MACC widths and the share of Scope 1 and Scope 2.",
     "Sel_Basis"),
    ("Step 3. Sel_DirectETS (Off / On). Switches whether Scope 1 stationary "
     "combustion sits inside EU ETS1; changes the direct ETS channel in "
     "Exposure.", "Sel_DirectETS"),
)
NEVER_CHANGES = (
    "The internal carbon price is a management lens and never a cash flow.",
    "The renewable electricity contract saves no cash under pass-through.",
    "Location-based and market-based Scope 2 are never added together.",
)
NPV_INVARIANT = ("The financial NPV (Dash_NPVFin, from M_Portfolio_NPV) "
                 "excludes carbon cash savings and is identical in every "
                 "selector state.")

# (link text, defined name, path description)
TRACES = (
    ("Financial NPV", "Dash_NPVFin",
     "Dashboard tile -> M_Portfolio_NPV -> a measure cash-flow row on "
     "Measures -> capex input on Inputs -> Sources"),
    ("Abatement cost of the first ranked measure", "MACC_Rank_Cost",
     "MACC ranked cost -> levelised cost (M_<K>_LevCost) of whichever "
     "measure ranks first on Measures (variable-speed drives in every "
     "selector state with the shipped inputs) -> that measure's capex and "
     "energy input rows on Inputs"),
    ("Cost of not acting", "Dash_CostNotActing",
     "Dashboard tile -> Expo_CumBAU_Sel -> ETS2 row on Exposure -> carbon "
     "path on Carbon -> NGFS input on Inputs"),
    ("Share of Scope 1 and Scope 2", "Dash_Share",
     "Dashboard tile -> BL_S12_LB / BL_S12_MB -> energy on Baseline -> "
     "Eurostat inputs"),
    ("Scope 2, location-based vs market-based", "BL_S2_LB",
     "Baseline Scope 2 -> grid and residual-mix factor inputs (EEA, AIB)"),
    ("NPV including carbon", "Dash_NPVIncl",
     "Dashboard tile -> Sens_PortfolioNPV -> avoided carbon cost on "
     "Exposure"),
    ("Master check", "Chk_Master",
     "Checks master flag -> group row on Checks -> owning check on its "
     "sheet"),
)


def _wrap(text):
    cur, lines = "", []
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > WRAP:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return lines


def build_readme(wb, styles, cells, dataset, cfg):
    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.COVER, freeze_row=3, freeze_col=0)
    write_title_band(cells, styles, ws, "Read-me and model map", PURPOSE,
                     NOTE, LAST_COL)
    ws.set_column(0, 0, 2.0)
    ws.set_column(1, 1, 40)
    ws.set_column(2, 2, 12)
    ws.set_column(3, 3, 52)
    ws.set_column(4, 4, 62)
    label = styles.get("label")
    sec = styles.get("section")
    hdr = styles.get("header")
    nav = styles.get("nav_link")
    present = set(_present_sheets(wb))
    r = [3]

    def section(title):
        r[0] += 2
        cells.text(ws, r[0], LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            cells.blank(ws, r[0], c, sec)

    def para(text):
        for ln in _wrap(text):
            r[0] += 1
            cells.text(ws, r[0], LABEL_COL, ln, label)

    # (1) flow
    section("How the model flows")
    r[0] += 1
    for c, h in enumerate(("Sheet", "Type", "Purpose", "Key outputs")):
        cells.text(ws, r[0], LABEL_COL + c, h, hdr)
    for name in FLOW_ORDER:
        if name not in present:
            continue
        r[0] += 1
        kind, purpose = SHEET_INFO[name]
        cells.internal_link(ws, r[0], 1, name, "A1", name, nav,
                            "Go to " + name)
        cells.text(ws, r[0], 2, kind, label)
        cells.text(ws, r[0], 3, purpose, label)
        cells.text(ws, r[0], 4, KEY_OUTPUTS[name], label)
    r[0] += 1
    cells.text(ws, r[0], LABEL_COL, FLOW_ARROWS, label)

    # (2) selectors
    section("How to use the selectors")
    for text, name in SELECTORS:
        r[0] += 1
        cells.text(ws, r[0], LABEL_COL, text, label)
        sheet, cell = cells.target_of(name)
        r[0] += 1
        cells.internal_link(ws, r[0], 1, sheet, cell, "Go to " + name, nav,
                            "Open the selector cell")
    r[0] += 1
    cells.text(ws, r[0], LABEL_COL, "What never changes", sec)
    for t in NEVER_CHANGES:
        para(t)
    para(NPV_INVARIANT)

    # (3) traces
    section("Trace this")
    para("Each link opens the start cell; follow the arrows to the source.")
    for text, name, path in TRACES:
        r[0] += 1
        sheet, cell = cells.target_of(name)
        cells.internal_link(ws, r[0], 1, sheet, cell, text, nav,
                            "Open " + name)
        cells.text(ws, r[0], 2, path, label)

    # (4) conventions
    section("Conventions in brief")
    for t in CONVENTIONS:
        para(t)
    para("Year zero is the first model year; the sign convention and units "
         "are stated on the Notes sheet.")


def _present_sheets(wb):
    return [w.get_name() for w in wb.worksheets()]
