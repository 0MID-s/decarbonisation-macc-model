"""Cover shell: title, legend, contents, version (D-02)."""
from xl.layout import setup_sheet
from xl.sheets.common import write_synthetic_banner, write_title_band
from xl.styles import SheetKind

FICTITIOUS_NOTE = ("Maison Veritas is a fictitious company. All figures are "
                   "built from cited public data or labelled analyst "
                   "assumptions.")
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
    ws = wb.add_worksheet("Cover")
    setup_sheet(ws, SheetKind.COVER, freeze_row=3, freeze_col=1)
    write_title_band(cells, styles, ws, cfg.company, cfg.title, cfg.subject,
                     LAST_COL)
    if dataset.synthetic:
        write_synthetic_banner(cells, styles, ws, 3, LAST_COL)
    cells.text(ws, 4, 1, FICTITIOUS_NOTE, styles.get("label"))
    for i, (role, meaning) in enumerate(LEGEND_MEANINGS):
        cells.text(ws, 6 + i, 1, "Sample", styles.get(role))
        cells.text(ws, 6 + i, 2, meaning, styles.get("label"))
    cells.text(ws, 15, 1, "Contents", styles.get("section"))
    row = 16
    for name in sheet_names:
        cells.text(ws, row, 1, name, styles.get("label"))
        row += 1
    row += 1
    cells.text(ws, row, 1, "Version", styles.get("label"))
    cells.text(ws, row, 2, cfg.version, styles.get("label"))
    cells.text(ws, row + 1, 1, "Build date", styles.get("label"))
    cells.date(ws, row + 1, 2, cfg.created.date(), styles.get("label", "date"))
