"""Disclosure sheet (plan 05-06, DISC-01..03, D-01 to D-06).

Maps model outputs to IFRS S2 and revised ESRS E1. No calculations: only static
text, =Name links to existing outputs and internal links. Requirements are
paraphrased (D-04); every row carries a strength and a verification status.
"""
from checkmodel.outputs_reference import linked_value
from config.disclosure import (CORRECTIONS, DISCLOSURE_ROWS, NONE, FLAG_1563,
                               OUTPUT_UNITS, STD_REFS, STRENGTHS, value_name)
from config.security import host_allowed
from xl.layout import setup_sheet
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import get_or_add, write_title_band
from xl.styles import SheetKind

SHEET = "Disclosure"
LAST_COL = 10
HEADERS = ("Standard", "Reference", "Set 1 equivalent",
           "Requirement (our words)", "Model output", "Value", "Strength",
           "Gap / comment", "Verification status", "Source ID")
WIDTHS = (14, 17, 17, 46, 30, 15, 12, 44, 34, 24)

PURPOSE = "How the model's outputs map to IFRS S2 and the revised ESRS E1"
NOTE = ("Requirements are paraphrased; see the standards register at the "
        "bottom for the official texts. Strengths are analyst "
        "classifications, not claims of compliance.")

KEY_LINES = (
    "Direct: the model produces the same kind of figure the paragraph asks "
    "for, at the scope of this representative firm.",
    "Supports: the model gives inputs or partial evidence that a reporter "
    "would build on, but not the disclosure itself.",
    "Not covered: the model deliberately does not address this requirement.",
    "Maison Veritas is a representative firm built from sector averages, so "
    "most company-specific disclosures can only be Supported.",
    "The Value column shows the first single-cell output named; ranges are "
    "reached through the link.",
)
CORRECTIONS_HEAD = ("Hypothesis", "Official finding", "Action")
LINE_H = 12.75
CORR_COLS = (4, 8, 9)


def _height(pairs):
    """Row height for wrapped text: pairs of (text, column index)."""
    lines = 1
    for text, col in pairs:
        per_line = max(1, int(WIDTHS[col - 1] * 1.05))
        n = 0
        for para in text.split("\n"):
            n += max(1, -(-len(para) // per_line))
        lines = max(lines, n)
    return LINE_H * lines


def build_disclosure(wb, styles, cells, dataset, cfg):
    basis, scenario = selector_state(dataset)
    state = (basis, scenario, direct_ets_state(dataset))
    missing = [(r.reference, n) for r in DISCLOSURE_ROWS
               for n in r.output_names if n not in cells.names]
    if missing:
        raise ValueError("Disclosure row output name not defined: %r"
                         % (missing[0],))
    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.DISCLOSURE, freeze_row=3, freeze_col=0)
    write_title_band(cells, styles, ws, "Disclosure map", PURPOSE, NOTE,
                     LAST_COL)
    ws.set_column(0, 0, 2.0)
    for i, w in enumerate(WIDTHS):
        ws.set_column(1 + i, 1 + i, w)
    lbl = styles.get("label")
    txt = styles.get("text")
    sec = styles.get("section")
    hdr = styles.get("header")
    nav = styles.get("nav_link")
    link = styles.get("link")

    # --- key (D-05)
    r = 4
    cells.text(ws, r, 1, "How to read the strength column", sec)
    for c in range(2, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    for line in KEY_LINES:
        r += 1
        cells.text(ws, r, 1, line, lbl)

    # --- mapping table
    r += 2
    hdr_row = r
    for c, h in enumerate(HEADERS):
        cells.text(ws, r, 1 + c, h, hdr)
    first = r + 1
    for row in DISCLOSURE_ROWS:
        r += 1
        cells.text(ws, r, 1, row.standard, txt)
        cells.text(ws, r, 2, row.reference, txt)
        cells.text(ws, r, 3, row.set1_equivalent, txt)
        cells.text(ws, r, 4, row.requirement, txt)
        if row.output_names:
            sheet, cell = cells.target_of(row.output_names[0])
            cells.internal_link(ws, r, 5, sheet, cell,
                                ", ".join(row.output_names), nav,
                                "Open " + row.output_names[0])
        else:
            cells.text(ws, r, 5, NONE, txt)
        vn = value_name(row)
        if vn:
            val = linked_value(vn, state, dataset.inputs)
            role = OUTPUT_UNITS[vn]
            fmt = styles.get("link", None if role == "general" else role)
            cells.formula(ws, r, 6, "=" + vn, fmt, value=val)
        else:
            cells.blank(ws, r, 6, link)
        cells.text(ws, r, 7, row.strength, txt)
        cells.text(ws, r, 8, row.gap, txt)
        status = row.status
        if row.status_note:
            status += ": " + row.status_note
        cells.text(ws, r, 9, status, txt)
        cells.text(ws, r, 10, row.ref_id or NONE, txt)
        ws.set_row(r, _height([(row.reference, 2), (row.set1_equivalent, 3),
                               (row.requirement, 4),
                               (", ".join(row.output_names) or "-", 5),
                               (row.gap, 8), (status, 9), (row.ref_id, 10)]))
    last = r
    cells.validation(ws, first, 7, last, 7, {
        "validate": "list", "source": list(STRENGTHS),
        "input_title": "Strength",
        "input_message": "Direct, Supports or Not covered (see the key)",
        "error_title": "Not a valid strength",
        "error_message": "Choose Direct, Supports or Not covered"})

    # --- standards register
    r += 2
    cells.text(ws, r, 1, "Standards register", sec)
    for c in range(2, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    r += 1
    reg_cols = (("ID", 1), ("Publisher", 2), ("Retrieved", 3), ("Title", 4),
                ("Edition", 5), ("Link", 6), ("Status note", 8),
                ("Licence note", 9))
    for h, c in reg_cols:
        cells.text(ws, r, c, h, hdr)
    for ref in STD_REFS.values():
        r += 1
        vals = (ref.ref_id, ref.publisher, ref.retrieved, ref.title,
                ref.edition, None, ref.status_note, ref.licence_note)
        for (h, c), v in zip(reg_cols, vals):
            if v is not None:
                cells.text(ws, r, c, v, txt)
        if host_allowed(ref.url):
            cells.link(ws, r, 6, ref.url, nav, "Open source")
        else:
            cells.text(ws, r, 6, ref.url, txt)
        ws.set_row(r, _height([(ref.ref_id, 1), (ref.publisher, 2),
                               (ref.title, 4), (ref.edition, 5),
                               (ref.status_note, 8), (ref.licence_note, 9)]))
    r += 1
    cells.text(ws, r, 1, "Flag on the revised ESRS legal basis: " + FLAG_1563
               + ". Cited as Commission Delegated Regulation (EU) 2026/1563.",
               lbl)

    # --- corrections to the working hypotheses
    r += 2
    cells.text(ws, r, 1, "Corrections to working hypotheses", sec)
    for c in range(2, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    r += 1
    for h, c in zip(CORRECTIONS_HEAD, CORR_COLS):
        cells.text(ws, r, c, h, hdr)
    for vals in CORRECTIONS:
        r += 1
        for v, c in zip(vals, CORR_COLS):
            cells.text(ws, r, c, v, txt)
        ws.set_row(r, _height(list(zip(vals, CORR_COLS))))
    return {"header_row": hdr_row, "first_row": first, "last_row": last}
