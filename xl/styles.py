"""Semantic style factory (D-01..D-07). The only module that calls add_format.

Cell roles map to one style each. Callers ask ``Styles.get(role, num)`` and
never build formats themselves (write discipline, threat T-01-22).
"""
from enum import Enum
from typing import Dict, Optional, Tuple

PALETTE = {
    "input_font": "#0000FF",
    "input_fill": "#FFF2CC",
    "formula_font": "#000000",
    "link_font": "#008000",
    "ok_fill": "#C6EFCE",
    "ok_font": "#006100",
    "err_fill": "#FFC7CE",
    "err_font": "#9C0006",
    "assumption_fill": "#FCE4D6",
    "title_fill": "#1F3864",
    "title_font": "#FFFFFF",
    "section_fill": "#D9D9D9",
    "accent": "#2E75B6",
    "synthetic_fill": "#F2F2F2",
    "index_font": "#7F7F7F",
}  # type: Dict[str, str]

# Okabe-Ito colour-blind-safe palette; yellow moved late (research A9).
OKABE_ITO = (
    "#E69F00", "#56B4E9", "#009E73", "#0072B2",
    "#D55E00", "#CC79A7", "#F0E442", "#000000",
)

NUM_FORMATS = {
    "eur": '#,##0;(#,##0);"–"',
    "eur2": '#,##0.00;(#,##0.00);"–"',
    "tco2e": '#,##0;(#,##0);"–"',
    "pct": "0.0%",
    "eur_per_t": '#,##0;(#,##0);"–"',
    "price4": "0.0000",
    "year": "0",
    "factor": "0.0000",
    "int": "0",
    "general": "General",
    "mwh": '#,##0;(#,##0);"–"',
    "count": "#,##0",
    "dec1": "#,##0.0",
    "dec2": "#,##0.00",
    "dec3": "#,##0.000",
    "dec5": "0.00000",
    "eur_m": "#,##0.00",
    "date": "yyyy-mm-dd",
}  # type: Dict[str, str]


class SheetKind(Enum):
    COVER = "cover"
    DASHBOARD = "dashboard"
    INPUTS = "inputs"
    SOURCES = "sources"
    LISTS = "lists"
    CALC = "calc"
    CHECKS = "checks"
    NOTES = "notes"
    DISCLOSURE = "disclosure"
    SPIKE_NOTES = "spike_notes"


TAB_COLOURS = {
    SheetKind.COVER: "#1F3864",
    SheetKind.DASHBOARD: "#1F3864",
    SheetKind.INPUTS: "#FFC000",
    SheetKind.SOURCES: "#FFC000",
    SheetKind.LISTS: "#FFC000",
    SheetKind.CALC: None,
    SheetKind.CHECKS: "#00B050",
    SheetKind.NOTES: "#7030A0",
    SheetKind.DISCLOSURE: "#7030A0",
    SheetKind.SPIKE_NOTES: "#7030A0",
}  # type: Dict[SheetKind, Optional[str]]

ROLES = (
    "title", "purpose", "note", "section", "header", "header_year", "label",
    "unit", "text", "input", "selector", "calc", "link", "index",
    "status_sourced", "status_assumption", "synthetic_banner",
    "legend_input", "legend_calc", "legend_link", "legend_selector",
    "legend_assumption", "legend_ok", "legend_err", "check_ok", "check_err",
    "nav_link", "tile_label", "tile", "flag",
)

_BASE = {"font_name": "Arial", "font_size": 10, "valign": "vcenter"}


def _role_props(role):
    # type: (str) -> Dict[str, object]
    P = PALETTE
    inp = {"font_color": P["input_font"], "bg_color": P["input_fill"],
           "pattern": 1, "locked": False, "border": 1, "border_color": "#BFBFBF"}
    box = {"border": 1, "border_color": "#BFBFBF"}
    table = {
        "title": {"font_size": 14, "bold": True, "font_color": P["title_font"],
                  "bg_color": P["title_fill"], "pattern": 1},
        "purpose": {"italic": True},
        "note": {"font_color": P["index_font"], "italic": True},
        "section": {"bold": True, "bg_color": P["section_fill"], "pattern": 1},
        "header": {"bold": True, "font_color": P["title_font"],
                   "bg_color": P["title_fill"], "pattern": 1, "bottom": 1,
                   "text_wrap": True, "align": "center"},
        "header_year": {"bold": True, "font_color": P["title_font"],
                        "bg_color": P["title_fill"], "pattern": 1, "bottom": 1,
                        "align": "center", "num_format": NUM_FORMATS["year"]},
        "label": {},
        "unit": {"font_color": P["index_font"]},
        "text": {"text_wrap": True, "valign": "top"},
        "input": inp,
        "selector": dict(inp, border=2, border_color="#000000"),
        "calc": {"font_color": P["formula_font"]},
        "link": {"font_color": P["link_font"]},
        "index": {"font_color": P["index_font"], "num_format": NUM_FORMATS["int"]},
        "status_sourced": {"font_color": P["formula_font"]},
        "status_assumption": {"bg_color": P["assumption_fill"], "pattern": 1},
        "synthetic_banner": {"bold": True, "bg_color": P["synthetic_fill"],
                             "pattern": 1, "text_wrap": True},
        "legend_input": dict(inp),
        "legend_calc": dict(box, font_color=P["formula_font"]),
        "legend_link": dict(box, font_color=P["link_font"]),
        "legend_selector": dict(inp, border=2, border_color="#000000"),
        "legend_assumption": dict(box, bg_color=P["assumption_fill"], pattern=1),
        "legend_ok": dict(box, font_color=P["ok_font"], bg_color=P["ok_fill"], pattern=1),
        "legend_err": dict(box, font_color=P["err_font"], bg_color=P["err_fill"], pattern=1),
        "check_ok": {"font_color": P["ok_font"], "bg_color": P["ok_fill"]},
        "check_err": {"font_color": P["err_font"], "bg_color": P["err_fill"]},
        "nav_link": {"font_color": P["accent"], "underline": 1},
        "tile_label": {"font_color": P["index_font"], "italic": True,
                       "text_wrap": True, "align": "center"},
        "tile": {"bold": True, "font_size": 16, "center_across": True,
                 "valign": "vcenter"},
        "flag": {"bold": True, "align": "center", "border": 1,
                 "border_color": "#BFBFBF"},
    }
    return table[role]


class Styles(object):
    """Cached Format factory bound to one workbook."""

    def __init__(self, workbook):
        self._wb = workbook
        self._cache = {}  # type: Dict[Tuple[str, Optional[str]], object]

    def get(self, role, num=None):
        key = (role, num)
        if key in self._cache:
            return self._cache[key]
        if role not in ROLES:
            raise KeyError("unknown style role: %r" % (role,))
        if num is not None and num not in NUM_FORMATS:
            raise KeyError("unknown number format: %r" % (num,))
        props = dict(_BASE)
        props.update(_role_props(role))
        if num is not None:
            props["num_format"] = NUM_FORMATS[num]
        fmt = self._wb.add_format(props)
        self._cache[key] = fmt
        return fmt


def apply_check_format(ws, styles, first_row, first_col, last_row, last_col):
    """Green for "OK", red for "ERROR" via conditional formatting (D-01)."""
    for value, role in (('"OK"', "check_ok"), ('"ERROR"', "check_err")):
        ws.conditional_format(first_row, first_col, last_row, last_col, {
            "type": "cell", "criteria": "==", "value": value,
            "format": styles.get(role),
        })


def apply_bool_check_format(ws, styles, first_row, first_col, last_row,
                            last_col):
    """Green for TRUE, red for FALSE via conditional formatting."""
    for value, role in (("TRUE", "check_ok"), ("FALSE", "check_err")):
        ws.conditional_format(first_row, first_col, last_row, last_col, {
            "type": "cell", "criteria": "==", "value": value,
            "format": styles.get(role),
        })
