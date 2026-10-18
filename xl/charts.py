"""MACC chart factories (D-04, D-17): technique A (area) and C (columns).

Charts reference the helper tables written by xl/macc.py. Arial fonts, the
Okabe-Ito palette in slot order, no 3D, gradients or shadows.
"""
from xl.macc import MaccALayout, MaccCLayout
from xl.styles import OKABE_ITO

FONT = {"name": "Arial", "size": 9}
X_TITLE = "Cumulative annual abatement (tCO2e)"
Y_TITLE = "Abatement cost (EUR per tCO2e)"


def _q(sheet):
    return "'%s'" % sheet if " " in sheet else sheet


def _axes(chart):
    chart.set_x_axis({
        "date_axis": True, "num_format": "#,##0", "min": 0,
        "label_position": "low", "num_font": FONT,
        "name": X_TITLE, "name_font": dict(FONT, bold=False),
    })
    chart.set_y_axis({
        "num_format": "#,##0", "name": Y_TITLE,
        "name_font": dict(FONT, bold=False), "num_font": FONT,
        "major_gridlines": {"visible": True, "line": {"color": "#D9D9D9"}},
    })
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": 900, "height": 420})


def macc_area_chart(wb, a_layout, with_reference_line=True):
    # type: (object, MaccALayout, bool) -> object
    chart = wb.add_chart({"type": "area"})
    sh = a_layout.sheet
    h0, h1 = a_layout.helper_first_row, a_layout.helper_last_row
    s0 = a_layout.sorted_rows[0]
    cats = [sh, h0, a_layout.x_col, h1, a_layout.x_col]
    n_points = h1 - h0 + 1
    for k, col in enumerate(a_layout.series_cols):
        labels = [{"delete": True}] * n_points
        labels[4 * k + 1] = {"value": "=%s!$C$%d" % (_q(sh), s0 + k + 1)}
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
    chart.set_title({"name": "Technique A: variable-width MACC (synthetic data)",
                     "name_font": {"name": "Arial", "size": 11}})
    _axes(chart)
    return chart


def macc_column_chart(wb, c_layout):
    # type: (object, MaccCLayout) -> object
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
    chart.set_title({"name": "Technique C: 200-bin MACC fallback (synthetic data)",
                     "name_font": {"name": "Arial", "size": 11}})
    chart.set_x_axis({"num_format": "#,##0", "name": X_TITLE,
                      "name_font": dict(FONT, bold=False), "num_font": FONT,
                      "interval_unit": 20, "label_position": "low"})
    chart.set_y_axis({"num_format": "#,##0", "name": Y_TITLE,
                      "name_font": dict(FONT, bold=False), "num_font": FONT,
                      "major_gridlines": {"visible": True,
                                          "line": {"color": "#D9D9D9"}}})
    chart.set_legend({"position": "bottom", "font": FONT})
    chart.set_size({"width": 900, "height": 420})
    return chart
