"""Cover shell: title, legend, contents, version (D-02)."""
from xl.layout import setup_sheet
from xl.sheets.common import (
    SHEET_INFO, get_or_add,
    FICTITIOUS_NOTE, disclaimer_text, write_synthetic_banner, write_title_band)
from xl.selector import direct_ets_state, selector_state
from xl.styles import SheetKind, apply_check_format

__all__ = ["FICTITIOUS_NOTE", "LEGEND_MEANINGS", "build_cover"]
LEGEND_MEANINGS = (
    ("legend_input", "Input: change these"),
    ("legend_calc", "Formula on this sheet"),
    ("legend_link", "Link from another sheet"),
    ("legend_selector", "Selector / switch (dropdown)"),
    ("legend_assumption", "Analyst assumption (status column)"),
    ("legend_ok", "Check passes"),
    ("legend_err", "Check fails"),
)
LAST_COL = 8


def build_cover(wb, styles, cells, dataset, cfg, sheet_names):
    ws = get_or_add(wb, "Cover")
    setup_sheet(ws, SheetKind.COVER, freeze_row=3, freeze_col=1)
    write_title_band(cells, styles, ws, cfg.company, cfg.title, cfg.subject,
                     LAST_COL)
    if dataset.synthetic:
        write_synthetic_banner(cells, styles, ws, 3, LAST_COL)
    cells.text(ws, 4, 1, disclaimer_text(dataset.sources), styles.get("label"))
    for i, (role, meaning) in enumerate(LEGEND_MEANINGS):
        cells.text(ws, 6 + i, 1, "Sample", styles.get(role))
        cells.text(ws, 6 + i, 2, meaning, styles.get("label"))
    cells.text(ws, 15, 1, "Contents", styles.get("section"))
    row = 16
    for name in sheet_names:
        cells.internal_link(ws, row, 1, name, "A1", name,
                            styles.get("nav_link"), "Go to " + name)
        cells.text(ws, row, 2, SHEET_INFO.get(name, ("", ""))[1],
                   styles.get("label"))
        row += 1
    if "Chk_Master" in cells.names:
        _master_flag(ws, styles, cells, dataset)
    row += 1
    cells.text(ws, row, 1, "Version", styles.get("label"))
    cells.text(ws, row, 2, cfg.version, styles.get("label"))
    cells.text(ws, row + 1, 1, "Build date", styles.get("label"))
    cells.date(ws, row + 1, 2, cfg.created.date(), styles.get("label", "date"))


def _master_flag(ws, styles, cells, dataset):
    """Master check flag right of the legend (D-11, D-17)."""
    from checkmodel.outputs_reference import compute_outputs
    basis, scenario = selector_state(dataset)
    ref = compute_outputs(dataset.inputs, basis, scenario,
                          direct_ets_state(dataset))
    cells.text(ws, 6, 4, "Model checks", styles.get("label"))
    cells.formula(ws, 6, 5, "=Chk_Master", styles.get("flag"),
                  value=ref.chk_master)
    apply_check_format(ws, styles, 6, 5, 6, 5)
    cells.text(ws, 7, 4, "Green OK means every check on the Checks sheet "
               "passes", styles.get("note"))
    sheet, cell = cells.target_of("Chk_Master")
    cells.internal_link(ws, 8, 4, sheet, cell, "Go to Checks",
                        styles.get("nav_link"), "Open the master check")
