"""Inputs sheet: every input with its full provenance (DATA-01, D-06, D-10, D-11)."""
from dataclasses import dataclass
from typing import Tuple

from config.schema import SECTIONS, Kind, Status
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, col_for_year, col_letter,
    setup_sheet,
)
from xl.sheets.common import (
    num_role_for_unit, write_legend_row, write_synthetic_banner,
    write_title_band,
)
from xl.styles import SheetKind

INPUT_COLUMNS = ("ID", "Description", "Value as published", "Published unit",
                 "Conversion factor", "Model value", "Model unit",
                 "Price basis", "Source ID", "Status", "Rationale / notes")
HEADER_ROW = 6
FIRST_RECORD_ROW = 7
LAST_COL = TIMELINE_LAST_COL  # AQ for 2026-2055


@dataclass(frozen=True)
class InputsLayout:
    header_row: int
    record_rows: Tuple[Tuple[str, int], ...]
    series_model_rows: Tuple[Tuple[str, int], ...]
    series_year_rows: Tuple[Tuple[str, int], ...] = ()


def _assign_rows(dataset):
    """First pass: section band rows and record rows (zero-based)."""
    bands = []
    rows = {}
    row = FIRST_RECORD_ROW
    for section in SECTIONS:
        recs = [r for r in dataset.inputs if r.section == section]
        if not recs:
            continue
        bands.append((section, row))
        row += 1
        for r in recs:
            rows[r.id] = row
            row += 3 if r.kind is Kind.SERIES else 1
    return bands, rows


def _notes(r):
    text = r.rationale + (" | Ref: " + r.note if r.note else "")
    return text if text.strip() else "–"


def build_inputs(wb, styles, cells, dataset, cfg):
    ws = wb.add_worksheet("Inputs")
    setup_sheet(ws, SheetKind.INPUTS, freeze_row=7, freeze_col=3,
                header_last_row=HEADER_ROW)
    write_title_band(
        cells, styles, ws, "Inputs",
        "Every model input with its published value, unit, conversion, "
        "price basis, source and status",
        "Model value = Value as published x Conversion factor. Units on "
        "every row. Sign convention: outflows negative, abatement positive.",
        LAST_COL)
    if dataset.synthetic:
        write_synthetic_banner(cells, styles, ws, 3, LAST_COL)
    write_legend_row(cells, styles, ws, 4)

    hdr = styles.get("header")
    for i, name in enumerate(INPUT_COLUMNS):
        cells.text(ws, HEADER_ROW, LABEL_COL + i, name, hdr)
    yr = styles.get("header_year", "year")
    c0 = TIMELINE_FIRST_COL
    cells.formula(ws, HEADER_ROW, c0, "=Time_FirstYear", yr,
                  value=cfg.timeline_start)
    for k in range(1, len(cfg.timeline_years)):
        prev = col_letter(c0 + k - 1)
        cells.formula(ws, HEADER_ROW, c0 + k,
                      "=%s%d+1" % (prev, HEADER_ROW + 1), yr,
                      value=cfg.timeline_start + k)

    bands, rows = _assign_rows(dataset)
    const_values = dict((r.id, r.published_value) for r in dataset.inputs
                        if r.section == "Constants" and r.kind is Kind.SCALAR)
    sec = styles.get("section")
    for name, row in bands:
        cells.text(ws, row, LABEL_COL, name, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            cells.blank(ws, row, c, sec)

    record_rows = []
    series_rows = []
    year_rows = []
    for r in dataset.inputs:
        row = rows[r.id]
        R = row + 1
        record_rows.append((r.id, row))
        series = r.kind is Kind.SERIES
        cells.text(ws, row, 1, r.id, styles.get("label"))
        cells.text(ws, row, 2, r.description, styles.get("text"))
        cells.text(ws, row, 4, r.published_unit, styles.get("unit"))
        pub_num = num_role_for_unit(r.published_unit)
        if series:
            cells.text(ws, row, 3, "Series in timeline ->", styles.get("text"))
        else:
            cells.number(ws, row, 3, r.published_value,
                         styles.get("input", pub_num))
        if r.section == "Constants":
            factor = 1.0
            cells.text(ws, row, 5, "– (base constant)", styles.get("text"))
        else:
            cr = rows[r.conversion_ref] + 1
            factor = const_values[r.conversion_ref]
            cells.formula(ws, row, 5, "=G%d" % cr,
                          styles.get("calc", "factor"), value=factor)
        model_num = num_role_for_unit(r.model_unit)
        if series:
            cells.text(ws, row, 6, "See next row", styles.get("text"))
        elif r.section == "Constants":
            cells.formula(ws, row, 6, "=D%d" % R,
                          styles.get("calc", model_num),
                          value=r.published_value)
        else:
            cells.formula(ws, row, 6, "=D%d*F%d" % (R, R),
                          styles.get("calc", model_num),
                          value=r.published_value * factor)
        cells.text(ws, row, 7, r.model_unit, styles.get("unit"))
        cells.text(ws, row, 8, r.price_basis.label, styles.get("text"))
        cells.text(ws, row, 9, r.source_id or "–", styles.get("text"))
        status_role = ("status_assumption" if r.status is Status.ASSUMPTION
                       else "status_sourced")
        cells.text(ws, row, 10, r.status.label, styles.get(status_role))
        cells.text(ws, row, 11, _notes(r), styles.get("text"))
        if not series:
            cells.define_name(r.id, "=Inputs!$G$%d" % R)
            continue
        for y, v in r.series:
            cells.number(ws, row, col_for_year(y), v,
                         styles.get("input", pub_num))
        mrow = row + 1
        series_rows.append((r.id, mrow))
        cells.text(ws, mrow, 1, "  model value", styles.get("label"))
        cells.text(ws, mrow, 2, "Model value = published x conversion factor",
                   styles.get("text"))
        cells.text(ws, mrow, 7, r.model_unit, styles.get("unit"))
        for y, v in r.series:
            col = col_for_year(y)
            cells.formula(ws, mrow, col,
                          "=%s%d*$F$%d" % (col_letter(col), R, R),
                          styles.get("calc", model_num), value=v * factor)
        yrow = row + 2
        year_rows.append((r.id, yrow))
        cells.text(ws, yrow, 1, "  point year (fixed)", styles.get("label"))
        cells.text(ws, yrow, 2, "Series point years as published (source "
                   "metadata, not an input; locked). Independent of First "
                   "model year", styles.get("text"))
        for y, v in r.series:
            # WR-02: a locked constant, not the unlocked input style; the
            # Carbon anchor check also compares it with the published year
            cells.number(ws, yrow, col_for_year(y), y,
                         styles.get("calc", "year"))
    return InputsLayout(HEADER_ROW, tuple(record_rows), tuple(series_rows),
                        tuple(year_rows))
