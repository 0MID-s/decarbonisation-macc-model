"""Sources sheet: one row per source ID, URLs as plain text (DATA-02, D-13)."""
from xl.layout import setup_sheet
from xl.sheets.common import write_synthetic_banner, write_title_band
from xl.styles import SheetKind

SOURCE_COLUMNS = ("Source ID", "Publisher", "Document or dataset", "URL",
                  "Edition", "Retrieved", "Licence note")
HEADER_ROW = 4
LAST_COL = 7


def build_sources(wb, styles, cells, dataset, cfg):
    ws = wb.add_worksheet("Sources")
    setup_sheet(ws, SheetKind.SOURCES, freeze_row=5, freeze_col=2,
                header_last_row=HEADER_ROW)
    write_title_band(
        cells, styles, ws, "Sources register",
        "Every source ID used on Inputs, with publisher, dataset, URL, "
        "edition, retrieval date and licence",
        "URLs are plain text by design (no workbook links); copy into a "
        "browser.", LAST_COL)
    if dataset.synthetic:
        write_synthetic_banner(cells, styles, ws, 3, LAST_COL)
    for i, name in enumerate(SOURCE_COLUMNS):
        cells.text(ws, HEADER_ROW, 1 + i, name, styles.get("header"))
    row = HEADER_ROW + 1
    if not dataset.sources:
        cells.text(ws, row, 1, "No sources registered yet; real sources are "
                   "added with the Phase 2 data.", styles.get("text"))
        return None
    for s in dataset.sources:
        cells.text(ws, row, 1, s.id, styles.get("label"))
        cells.text(ws, row, 2, s.publisher, styles.get("text"))
        cells.text(ws, row, 3, s.dataset, styles.get("text"))
        cells.text(ws, row, 4, s.url, styles.get("text"))
        cells.text(ws, row, 5, s.edition, styles.get("text"))
        cells.date(ws, row, 6, s.retrieved, styles.get("label", "date"))
        cells.text(ws, row, 7, s.licence_note, styles.get("text"))
        row += 1
    return None
