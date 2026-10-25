"""Shared layout grid and sheet-level setup (D-05, D-06, D-08).

Timeline decision (orchestrator resolution 7): Inputs needs the 11 D-10
provenance columns B..L, so the shared timeline starts at column N on EVERY
sheet. Column N (index 13) = first year (2026), column AQ (index 42) = 2055.
Column M is a narrow spacer. Calc sheets use B label, C unit, D..L for
scalars, totals and notes. Same column = same year on every sheet, and year
series rows on Inputs use the same timeline columns.

This module applies sheet-level settings only; cells are written in xl/cells.py.
"""
from typing import Dict, Tuple

from xlsxwriter.utility import xl_col_to_name

from config.build_config import BUILD
from xl.styles import TAB_COLOURS, SheetKind

SPACER_COL = 0
LABEL_COL = 1
UNIT_COL = 2
TIMELINE_SPACER_COL = 12
TIMELINE_FIRST_COL = 13
TITLE_ROWS = (0, 2)

FOOTER = "&L&A&CIllustrative model, fictitious company, real public data&RPage &P of &N"

TIMELINE_LAST_COL = TIMELINE_FIRST_COL + len(BUILD.timeline_years) - 1
_TL_LAST = TIMELINE_LAST_COL


def col_for_year(year):
    # type: (int) -> int
    if year < BUILD.timeline_start or year > BUILD.timeline_end:
        raise ValueError("year %r outside timeline %d-%d"
                         % (year, BUILD.timeline_start, BUILD.timeline_end))
    return TIMELINE_FIRST_COL + (year - BUILD.timeline_start)


def year_for_col(col):
    # type: (int) -> int
    if col < TIMELINE_FIRST_COL or col > _TL_LAST:
        raise ValueError("column %r outside timeline columns" % (col,))
    return BUILD.timeline_start + (col - TIMELINE_FIRST_COL)


def col_letter(col):
    # type: (int) -> str
    return xl_col_to_name(col)


_CALC_WIDTHS = (
    (0, 0, 2.0), (1, 1, 40.0), (2, 2, 14.0), (3, 11, 12.0),
    (TIMELINE_SPACER_COL, TIMELINE_SPACER_COL, 2.0),
    (TIMELINE_FIRST_COL, _TL_LAST, 9.0),
)
_INPUTS_WIDTHS = (
    (0, 0, 2.0), (1, 1, 22.0), (2, 2, 44.0), (3, 3, 14.0), (4, 4, 14.0),
    (5, 5, 12.0), (6, 6, 14.0), (7, 7, 14.0), (8, 8, 18.0), (9, 9, 12.0),
    (10, 10, 18.0), (11, 11, 60.0),
    (TIMELINE_SPACER_COL, TIMELINE_SPACER_COL, 2.0),
    (TIMELINE_FIRST_COL, _TL_LAST, 9.0),
)
_SOURCES_WIDTHS = (
    (0, 0, 2.0), (1, 1, 12.0), (2, 2, 30.0), (3, 3, 40.0), (4, 4, 60.0),
    (5, 5, 16.0), (6, 6, 12.0), (7, 7, 40.0),
)

COLUMN_WIDTHS = {
    SheetKind.INPUTS: _INPUTS_WIDTHS,
    SheetKind.SOURCES: _SOURCES_WIDTHS,
}  # type: Dict[SheetKind, Tuple[Tuple[int, int, float], ...]]
for _k in SheetKind:
    COLUMN_WIDTHS.setdefault(_k, _CALC_WIDTHS)


def setup_sheet(ws, kind, *, freeze_row, freeze_col, header_last_row=2):
    # type: (object, SheetKind, int, int, int) -> None
    ws.hide_gridlines(2)
    tab = TAB_COLOURS[kind]
    if tab is not None:
        ws.set_tab_color(tab)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(TITLE_ROWS[0], header_last_row)
    ws.set_footer(FOOTER)
    ws.set_margins(left=0.5, right=0.5, top=0.6, bottom=0.6)
    ws.set_default_row(12.75)
    for first, last, width in COLUMN_WIDTHS[kind]:
        ws.set_column(first, last, width)
    ws.freeze_panes(freeze_row, freeze_col)


def dashboard_print(ws, last_row, last_col):
    """One-page A4 landscape print setup for the Dashboard (D-10).
    The only place a print area is set."""
    ws.print_area(0, 0, last_row, last_col)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 1)
    ws.center_horizontally()
