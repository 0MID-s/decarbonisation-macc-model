"""MACC chart factories (D-04, D-17): technique A (area) and C (columns).

Charts reference the helper tables written by xl/macc.py. Arial fonts, the
Okabe-Ito palette in slot order, no 3D, gradients or shadows.
"""
from dataclasses import dataclass
from typing import Tuple

from xl.macc import MaccALayout, MaccCLayout
from xl.styles import OKABE_ITO
from xlsxwriter.utility import xl_col_to_name

FONT = {"name": "Arial", "size": 9}
X_TITLE = "Cumulative annual abatement (tCO2e)"
Y_TITLE = "Abatement cost (EUR per tCO2e)"


def _q(sheet):
    return "'%s'" % sheet if " " in sheet else sheet


def nice_step(total, max_intervals=8):
    # type: (float, int) -> int
    """Smallest of 1, 2, 5 x 10^k giving at most max_intervals major steps."""
    total = max(float(total), 1.0)
    k = 0
    while True:
        for m in (1, 2, 5):
            step = m * 10 ** k
            if total / step <= max_intervals:
                return step
        k += 1


def _axes(chart, major_unit=None, size=(900, 420), axis_max=None):
    x_axis = {
        "date_axis": True, "num_format": "#,##0", "min": 0,
        "label_position": "low", "num_font": FONT,
        "name": X_TITLE, "name_font": dict(FONT, bold=False),
    }
    if major_unit is not None:
        x_axis["major_unit"] = major_unit
        x_axis["major_unit_type"] = "days"
    if axis_max is not None:
        x_axis["max"] = axis_max
    chart.set_x_axis(x_axis)
    chart.set_y_axis({
        "num_format": "#,##0", "name": Y_TITLE,
        "name_font": dict(FONT, bold=False), "num_font": FONT,
        "major_gridlines": {"visible": True, "line": {"color": "#D9D9D9"}},
    })
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": size[0], "height": size[1]})


def macc_area_chart(wb, a_layout, with_reference_line=True, title=None,
                    major_unit=None, label_col=None, size=(900, 420),
                    axis_max=None):
    # type: (object, MaccALayout, bool, object, object, object, tuple, object) -> object
    chart = wb.add_chart({"type": "area"})
    sh = a_layout.sheet
    h0, h1 = a_layout.helper_first_row, a_layout.helper_last_row
    s0 = a_layout.sorted_rows[0]
    cats = [sh, h0, a_layout.x_col, h1, a_layout.x_col]
    n_points = h1 - h0 + 1
    for k, col in enumerate(a_layout.series_cols):
        labels = [{"delete": True}] * n_points
        lc = "C" if label_col is None else xl_col_to_name(label_col)
        labels[4 * k + 1] = {"value": "=%s!$%s$%d" % (_q(sh), lc, s0 + k + 1)}
        chart.add_series({
            "name": [sh, a_layout.name_row, col],
            "categories": cats,
            "values": [sh, h0, col, h1, col],
            "fill": {"color": OKABE_ITO[k]},
            "border": {"none": True},
            "data_labels": {"value": True, "custom": labels,
                            "font": {"name": "Arial", "size": 8}},
        })
    if with_reference_line:
        line = wb.add_chart({"type": "line"})
        line.add_series({
            "name": [sh, a_layout.name_row, a_layout.ref_col],
            "categories": cats,
            "values": [sh, h0, a_layout.ref_col, h1, a_layout.ref_col],
            "line": {"color": "#000000", "width": 1.5, "dash_type": "dash"},
            "marker": {"type": "none"},
        })
        chart.combine(line)
    chart.set_title({
        "name": ("Technique A: variable-width MACC (synthetic data)"
                 if title is None else title),
        "name_font": {"name": "Arial", "size": 11}})
    _axes(chart, major_unit, size, axis_max)
    return chart


def macc_column_chart(wb, c_layout, title=None, size=(900, 420)):
    # type: (object, MaccCLayout, object, tuple) -> object
    chart = wb.add_chart({"type": "column"})
    sh = c_layout.sheet
    cats = [sh, c_layout.first_row, c_layout.start_col,
            c_layout.last_row, c_layout.start_col]
    for k, col in enumerate(c_layout.series_cols):
        chart.add_series({
            "name": [sh, c_layout.name_row, col],
            "categories": cats,
            "values": [sh, c_layout.first_row, col, c_layout.last_row, col],
            "fill": {"color": OKABE_ITO[k]},
            "border": {"none": True},
            "gap": 0, "overlap": 100,
        })
    chart.set_title({
        "name": ("Technique C: 200-bin MACC fallback (synthetic data)"
                 if title is None else title),
        "name_font": {"name": "Arial", "size": 11}})
    chart.set_x_axis({"num_format": "#,##0", "name": X_TITLE,
                      "name_font": dict(FONT, bold=False), "num_font": FONT,
                      "interval_unit": 20, "label_position": "low"})
    chart.set_y_axis({"num_format": "#,##0", "name": Y_TITLE,
                      "name_font": dict(FONT, bold=False), "num_font": FONT,
                      "major_gridlines": {"visible": True,
                                          "line": {"color": "#D9D9D9"}}})
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": size[0], "height": size[1]})
    return chart


@dataclass(frozen=True)
class BridgeLayout:
    """Where the bridge helper table sits (zero-based rows and columns).

    series_cols entries: (name, pos_col, neg_col, colour, label_pos_col,
    label_neg_col). The header row holds the series names.
    """
    sheet: str
    first_row: int
    last_row: int
    label_col: int
    base_pos_col: int
    base_neg_col: int
    series_cols: Tuple[Tuple[str, int, int, str, int, int], ...]
    value_col: int
    header_row: int


def bridge_chart(wb, layout, title, size=(900, 420)):
    # type: (object, BridgeLayout, str, tuple) -> object
    """Waterfall as a stacked column: invisible positive and negative bases
    place each bar, so the chart survives bars that cross or sit below zero.
    No axis bounds are written (they would clip when inputs change) and no
    date axis is used."""
    chart = wb.add_chart({"type": "column", "subtype": "stacked"})
    sh = layout.sheet
    r0, r1 = layout.first_row, layout.last_row
    cats = [sh, r0, layout.label_col, r1, layout.label_col]
    n = r1 - r0 + 1
    for col in (layout.base_pos_col, layout.base_neg_col):
        chart.add_series({
            "name": [sh, layout.header_row, col], "categories": cats,
            "values": [sh, r0, col, r1, col],
            "fill": {"none": True}, "border": {"none": True},
            "gap": 50, "overlap": 100,
        })
    for _name, pos, neg, colour, lpos, lneg in layout.series_cols:
        for col, lcol in ((pos, lpos), (neg, lneg)):
            labels = [{"value": "=%s!$%s$%d" % (
                _q(sh), xl_col_to_name(lcol), r0 + i + 1)} for i in range(n)]
            chart.add_series({
                "name": [sh, layout.header_row, col], "categories": cats,
                "values": [sh, r0, col, r1, col],
                "fill": {"color": colour}, "border": {"none": True},
                "data_labels": {"value": True, "custom": labels,
                                "font": {"name": "Arial", "size": 8}},
                "gap": 50, "overlap": 100,
            })
    chart.set_title({"name": title,
                     "name_font": {"name": "Arial", "size": 11}})
    chart.set_x_axis({"num_font": FONT, "label_position": "low"})
    chart.set_y_axis({
        "num_format": "#,##0", "name": "EUR thousand, discounted, real 2025",
        "name_font": dict(FONT, bold=False), "num_font": FONT,
        "major_gridlines": {"visible": True, "line": {"color": "#D9D9D9"}},
    })
    # one legend entry per colour: delete the bases and the below-zero twins
    chart.set_legend({"position": "bottom", "font": FONT,
                      "delete_series": [0, 1, 3, 5, 7]})
    chart.set_size({"width": size[0], "height": size[1]})
    return chart


@dataclass(frozen=True)
class TornadoLayout:
    """Sorted tornado table: label, downside and upside columns (zero-based)."""
    sheet: str
    first_row: int
    last_row: int
    label_col: int
    down_col: int
    up_col: int


def tornado_chart(wb, layout, title, size=(800, 420)):
    # type: (object, TornadoLayout, str, tuple) -> object
    """Horizontal bars around the base: downside (left) and upside (right),
    largest swing on top (category axis reversed). No axis bounds, no date
    axis."""
    chart = wb.add_chart({"type": "bar"})
    sh = layout.sheet
    r0, r1 = layout.first_row, layout.last_row
    cats = [sh, r0, layout.label_col, r1, layout.label_col]
    for k, (col, name) in enumerate(((layout.down_col, "Downside"),
                                     (layout.up_col, "Upside"))):
        chart.add_series({
            "name": name, "categories": cats,
            "values": [sh, r0, col, r1, col],
            "fill": {"color": OKABE_ITO[k + 1]}, "border": {"none": True},
            "gap": 40, "overlap": 100,
        })
    chart.set_title({"name": title,
                     "name_font": {"name": "Arial", "size": 11}})
    chart.set_y_axis({"reverse": True, "label_position": "low",
                      "num_font": FONT})
    chart.set_x_axis({"num_format": "#,##0", "num_font": FONT,
                      "name": "Change in portfolio NPV (EUR, real 2025)",
                      "name_font": dict(FONT, bold=False),
                      "major_gridlines": {"visible": True,
                                          "line": {"color": "#D9D9D9"}}})
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": size[0], "height": size[1]})
    return chart


def exposure_scenario_chart(wb, sheet, hdr_row, first_row, last_row, cat_col,
                            bau_col, with_col, title, size=(520, 300)):
    # type: (object, str, int, int, int, int, int, int, str, tuple) -> object
    """Clustered columns: cumulative undiscounted carbon cost without (BAU) and
    with the measures, one cluster per carbon price scenario. Rows and columns
    are zero-based. No axis bounds (the Low case can be negative), no date
    axis."""
    chart = wb.add_chart({"type": "column"})
    cats = [sheet, first_row, cat_col, last_row, cat_col]
    for k, col in enumerate((bau_col, with_col)):
        chart.add_series({
            "name": [sheet, hdr_row, col], "categories": cats,
            "values": [sheet, first_row, col, last_row, col],
            "fill": {"color": OKABE_ITO[k + 1]}, "border": {"none": True},
            "gap": 80,
        })
    chart.set_title({"name": title,
                     "name_font": {"name": "Arial", "size": 11}})
    chart.set_x_axis({"num_font": FONT, "label_position": "low"})
    chart.set_y_axis({
        "num_format": "#,##0", "name": "EUR, real 2025, undiscounted",
        "name_font": dict(FONT, bold=False), "num_font": FONT,
        "major_gridlines": {"visible": True, "line": {"color": "#D9D9D9"}},
    })
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": size[0], "height": size[1]})
    return chart
