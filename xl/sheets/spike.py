"""Throwaway MACC and dropdown spike (D-17, D-19). Synthetic data only.

Sheets: Instructions (GATE-A checklist), MACC_A (technique A), MACC_C
(technique C), Dropdown (direct range and defined-name list sources), Lists.
"""
from checkmodel import macc_reference as ref
from config.schema import ProvenanceError
from xl.charts import macc_area_chart, macc_column_chart
from xl.layout import setup_sheet
from xl.macc import write_macc_a_block, write_macc_c_block
from xl.sheets.common import write_synthetic_banner, write_title_band
from xl.sheets.lists import BASIS_REF, SCENARIO_REF, build_lists
from xl.styles import SheetKind

GATE_PURPOSE = ("Open this file in Excel for the web (upload to OneDrive) and, "
                "if available, Excel desktop. Report each check in one reply.")
CHECKS = (
    ("MACC_A: chart bar widths differ and match column E of the sorted table.",
     "Six bars of different widths; widths proportional to the Width column."),
    ("MACC_A: negative-cost bars sit below the x axis, positive above.",
     "Two measures below zero, four above."),
    ("MACC_A: x axis starts at 0 and shows numbers like 1,000, not dates.",
     "Axis labels are plain numbers, not 1900 dates."),
    ("MACC_A: legend lists the six synthetic measures cheapest first.",
     "Legend order follows the sorted table."),
    ("MACC_A: data labels show measure names on bars (optional; the legend is "
     "the fallback).", "Names visible on bars, or note that they are missing."),
    ("MACC_A: dashed horizontal reference carbon price line spans the chart.",
     "One dashed line across the full width."),
    ("MACC_C: chart shows contiguous bars without gaps.",
     "A stepped, gapless profile that matches the MACC_A shape."),
    ("Change one cost in MACC_A column D: the sorted table and both charts "
     "re-order.", "Bars move to the new cheapest-first order."),
    ("Dropdown C6 (direct range source) opens Low / Central / High.",
     "Arrow appears and the three values are listed."),
    ("Dropdown C7 (defined-name source) opens the same list.",
     "Same three values as C6."),
    ("Change C6, C7 and C8: the echo cells C10:C14 update.",
     "Echo text and match numbers follow the selection."),
    ("The file opens without a repair prompt and shows no #NAME? or #REF!.",
     "Clean open, no error values anywhere."),
)
REPLY_FORMAT = ("Reply format: GATE-A: 1 OK, 2 OK, 3 problem - <what you saw>, "
                "... (one line per check, in one message).")


def _sheet(wb, cells, styles, name, kind, dataset, title, purpose, note, last_col):
    ws = wb.add_worksheet(name)
    setup_sheet(ws, kind, freeze_row=4, freeze_col=2, header_last_row=3)
    write_title_band(cells, styles, ws, title, purpose, note, last_col)
    write_synthetic_banner(cells, styles, ws, 3, last_col)
    ws.set_row(3, 26)
    return ws


def _instructions(wb, styles, cells, dataset):
    ws = _sheet(wb, cells, styles, "Instructions", SheetKind.SPIKE_NOTES,
                dataset, "GATE-A: Excel check for the MACC spike", GATE_PURPOSE,
                "Throwaway spike; every number on these sheets is synthetic.", 4)
    ws.set_column(1, 1, 40.0)
    ws.set_column(2, 2, 70.0)
    ws.set_column(3, 3, 50.0)
    ws.set_column(4, 4, 34.0)
    hdr = styles.get("header")
    for c, t in enumerate(("Check", "What to look at", "Expected result",
                           "Your result (OK / describe problem)")):
        cells.text(ws, 5, 1 + c, t, hdr)
    for i, (look, expect) in enumerate(CHECKS):
        r = 6 + i
        ws.set_row(r, 30)
        cells.text(ws, r, 1, "Check %d" % (i + 1), styles.get("label"))
        cells.text(ws, r, 2, look, styles.get("text"))
        cells.text(ws, r, 3, expect, styles.get("text"))
        cells.blank(ws, r, 4, styles.get("input"))
    cells.text(ws, 6 + len(CHECKS) + 1, 1, REPLY_FORMAT, styles.get("label"))
    return ws


def _dropdowns(wb, styles, cells, dataset):
    ws = _sheet(wb, cells, styles, "Dropdown", SheetKind.CALC, dataset,
                "Dropdown spike",
                "Cross-sheet list sources: direct range and defined name",
                "Pick a value in each blue cell; the echo cells update.", 6)
    sel = styles.get("selector")
    rows = (
        (5, "Scenario - direct range source", "Central", "=" + SCENARIO_REF,
         "Select scenario"),
        (6, "Scenario - defined-name source", "Central", "=List_Scenario",
         "Select scenario"),
        (7, "Emissions basis - defined-name source", "Location-based",
         "=List_Basis", "Select basis"),
    )
    for r, label, value, source, title in rows:
        cells.text(ws, r, 1, label, styles.get("label"))
        cells.text(ws, r, 2, value, sel)
        cells.validation(ws, r, 2, r, 2, {
            "validate": "list", "source": source,
            "input_title": title,
            "input_message": "Choose a value from the list.",
            "error_title": "Invalid entry",
            "error_message": "Pick one of the listed values.",
            "error_type": "stop",
        })
    echo = styles.get("calc")
    link = styles.get("link", "int")
    cells.text(ws, 8, 1, "Echo (formulas)", styles.get("section"))
    cells.formula(ws, 9, 2, '="Selected (direct): "&C6', echo,
                  value="Selected (direct): Central")
    cells.formula(ws, 10, 2, '="Selected (named): "&C7', echo,
                  value="Selected (named): Central")
    cells.formula(ws, 11, 2, "=MATCH(C6,List_Scenario,0)", link, value=2)
    cells.formula(ws, 12, 2, "=MATCH(C7,List_Scenario,0)", link, value=2)
    cells.formula(ws, 13, 2, '="Basis: "&C8', echo,
                  value="Basis: Location-based")
    return ws


def build_spike(wb, styles, cells, dataset, cfg):
    if not dataset.synthetic:
        raise ProvenanceError(["spike requires the synthetic fixtures dataset"])
    if dataset.reference_price is None:
        raise ProvenanceError(["spike dataset has no synthetic reference price"])
    srt = ref.rank_measures(dataset.measures)
    _instructions(wb, styles, cells, dataset)

    wsa = _sheet(wb, cells, styles, "MACC_A", SheetKind.CALC, dataset,
                 "MACC spike: technique A (area chart on a date axis)",
                 "Variable-width marginal abatement cost curve, sorted live",
                 "Edit the blue cost or abatement cells; the sorted table and "
                 "both charts re-order.", 12)
    a_layout = write_macc_a_block(cells, styles, wsa, dataset.measures,
                                  dataset.reference_price)
    wsa.insert_chart("N6", macc_area_chart(wb, a_layout))

    wsc = _sheet(wb, cells, styles, "MACC_C", SheetKind.CALC, dataset,
                 "MACC spike: technique C (200-bin columns)",
                 "Fallback: gapless columns driven by MATCH on cumulative starts",
                 "Reads the sorted table on MACC_A.", 10)
    c_layout = write_macc_c_block(cells, styles, wsc, a_layout, srt)
    wsc.insert_chart("L6", macc_column_chart(wb, c_layout))

    _dropdowns(wb, styles, cells, dataset)
    lists = build_lists(wb, styles, cells, dataset, cfg)
    return {"lists": lists}
