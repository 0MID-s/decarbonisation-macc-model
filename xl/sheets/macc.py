"""MACC sheet (plan 03-09): live-sorted ranked table, tiers, reference carbon
price and the two MACC charts (technique A primary, technique C fallback).

Everything is driven by the Measures result names and the two selectors
(Sel_Basis, Sel_Scenario). Barrier notes are analyst commentary (D-24).
"""
from dataclasses import dataclass
from typing import Tuple

from xl.selector import selector_state
from checkmodel.measures_reference import (
    DEFAULT_STATE, all_states, compute_measures)
from config.measures_catalog import MEASURES
from xl.charts import macc_area_chart, macc_column_chart, nice_step
from xl.layout import setup_sheet
from xl.macc import (
    LinkedRow, MaccGeometry, write_macc_c_block, write_macc_linked_block)
from xl.sheets.common import get_or_add, write_title_band
from xl.styles import SheetKind

SHEET = "MACC"
LAST_COL = 10

TITLE_ROW = 4
REF_ROW = 5
TBL_HDR = 7
TBL_FIRST = 8
CHART_A_CELL = "B17"
DATA_BAND = 47
GEOMETRY = MaccGeometry(
    sheet=SHEET, header_row=48, data_first=49, sort_header_row=57,
    sort_first=58, slot_row=65, name_row=66, helper_first=67,
    c_total_row=124, c_slot_row=127, c_name_row=128, c_first=129)
SORT_BAND = 56
HELPER_BAND = 64
C_BAND = 92
CHART_C_CELL = "B94"
ZOOM_NOTE_CELL = "K17"
ZOOM_CELL = "K18"

PURPOSE = ("Measures ranked cheapest first; bar width = annual tCO2e on the "
           "selected basis, height = EUR per tCO2e")
NOTE = ("A cost-ranked screening, not an optimiser: measures interact through "
        "the stack (see Notes); negative cost = saves money without any "
        "carbon price")
TIER_NOTE = ("Tier rule: Do first if cost < 0; Next if cost is between 0 and "
             "the reference carbon price; Later if above it, or if the "
             "measure has no abatement on the selected basis.")
BARRIER_NOTE = ("Barrier notes are analyst commentary, not sourced data. "
                "A measure with no abatement on the selected basis (the "
                "renewable contract under location-based) stays in the table "
                "as n/a, ranks last and has zero chart width.")
HEADS = ("Rank", "Measure", "Annual tCO2e (selected basis)",
         "Abatement cost (EUR/tCO2e)", "Financial NPV (after subsidy)",
         "NPV before subsidy", "IRR", "Discounted payback (years)", "Tier",
         "Barrier note (analyst commentary)")
REF_LABEL = ("Reference carbon price: levelised price of the selected "
             "scenario 2027-2055 (EUR/tCO2e)")


@dataclass(frozen=True)
class MaccSheetLayout:
    table_rows: Tuple[int, int]
    data_rows: Tuple[int, int]
    sorted_rows: Tuple[int, int]
    helper_rows: Tuple[int, int]
    ref_price_cell: str
    title_cell: str
    a_layout: object
    c_layout: object
    chart_step: int = 0
    chart_axis_max: int = 0


def _rows(ref):
    out = []
    for spec in MEASURES:
        mr = ref.by_key(spec.key)
        k = spec.key
        out.append(LinkedRow(
            name=mr.name,
            width_f="=M_%s_AvgtSel" % k, width_v=mr.avg_t_sel,
            cost_f="=M_%s_LevCost" % k, cost_v=mr.lev,
            elig_f="=M_%s_Eligible" % k, elig_v=1 if mr.eligible else 0,
            extras=(("=M_%s_NPV" % k, mr.npv, "eur"),
                    ("=M_%s_NPVPreSub" % k, mr.npv_pre_sub, "eur"),
                    ("=M_%s_IRR" % k, mr.irr, "pct"),
                    ("=M_%s_PayDisc" % k, mr.pay_disc, "dec1")),
            note=spec.barrier_note, short=spec.short))
    return out


def build_macc(wb, styles, cells, dataset, cfg, layouts):
    ref = compute_measures(dataset.inputs, *selector_state(dataset))
    n = len(ref.measures)
    g = GEOMETRY
    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=2,
                header_last_row=2)
    write_title_band(cells, styles, ws, "MACC", PURPOSE, NOTE, LAST_COL)
    ws.set_column(1, 1, 8.0)
    ws.set_column(2, 2, 46.0)
    ws.set_column(3, 9, 16.0)
    ws.set_column(10, 10, 72.0)
    ws.set_column(11, 11, 14.0)
    hdr = styles.get("header")
    sec = styles.get("section")
    lbl = styles.get("label")

    # --- title cell and reference price
    title_val = "MACC: %s basis, %s carbon price scenario" % (
        ref.basis, ref.scenario)
    cells.formula(ws, TITLE_ROW, 1,
                  '="MACC: "&Sel_Basis&" basis, "&Sel_Scenario&'
                  '" carbon price scenario"',
                  styles.get("calc"), value=title_val)
    cells.define_name("MACC_Title", "=%s!$B$%d" % (SHEET, TITLE_ROW + 1))
    cells.text(ws, REF_ROW, 1, REF_LABEL, lbl)
    cells.formula(ws, REF_ROW, 6,
                  "=SUMPRODUCT(M_CarbonPrice,M_DF,M_Op)/SUMPRODUCT(M_DF,M_Op)",
                  styles.get("calc", "eur_per_t"), value=ref.ref_price)
    cells.define_name("MACC_RefPrice", "=%s!$G$%d" % (SHEET, REF_ROW + 1))

    # --- lower blocks first (the ranked table reads them)
    for r, t in ((DATA_BAND, "Data block (links to the Measures results, "
                  "stack order)"),
                 (SORT_BAND, "Sorted block (cheapest first; zero width and "
                  "height for a measure with no abatement)"),
                 (HELPER_BAND, "Chart helper rows (technique A: four points "
                  "per measure)"),
                 (C_BAND, "Fallback view (technique C: 200 bins, same "
                  "ranking)")):
        cells.text(ws, r, 1, t, sec)
        for c in range(2, LAST_COL + 1):
            cells.blank(ws, r, c, sec)
    a_layout, srt = write_macc_linked_block(
        cells, styles, ws, g, _rows(ref), "MACC_RefPrice", ref.ref_price)
    d0, d1 = a_layout.data_rows
    s0, s1 = a_layout.sorted_rows

    # --- ranked table (live sort: INDEX/MATCH on the rank column)
    for c, t in enumerate(HEADS):
        cells.text(ws, TBL_HDR, 1 + c, t, hdr)
    ws.set_row(TBL_HDR, 38)
    ranks = "$E$%d:$E$%d" % (d0 + 1, d1 + 1)

    def col(letter):
        return "$%s$%d:$%s$%d" % (letter, d0 + 1, letter, d1 + 1)

    spec = (("B", 2, None, lambda m: m.name),
            ("C", 3, "tco2e", lambda m: m.avg_t_sel),
            ("D", 4, "eur_per_t", lambda m: m.lev),
            ("G", 5, "eur", lambda m: m.npv),
            ("H", 6, "eur", lambda m: m.npv_pre_sub),
            ("I", 7, "pct", lambda m: m.irr),
            ("J", 8, "dec1", lambda m: m.pay_disc))
    notes = {s.key: s.barrier_note for s in MEASURES}
    for k in range(n):
        r = TBL_FIRST + k
        key = ref.sorted_keys[k]
        mr = ref.by_key(key)
        idx = [m.key for m in ref.measures].index(key)
        ws.set_row(r, 40)
        cells.number(ws, r, 1, k + 1, styles.get("index"))
        for src, c, num, get in spec:
            cells.formula(
                ws, r, c, "=INDEX(%s,MATCH($B%d,%s,0))" % (col(src), r + 1, ranks),
                styles.get("calc", num) if num else styles.get("calc"),
                value=get(mr))
        sr = s0 + k + 1
        cells.formula(
            ws, r, 9,
            "=IF($I%d=0,Tier_Later,IF($D%d<0,Tier_First,"
            "IF($D%d<=MACC_RefPrice,Tier_Next,Tier_Later)))" % (sr, sr, sr),
            styles.get("calc"), value=ref.tiers[idx])
        cells.formula(
            ws, r, 10, "=INDEX(%s,MATCH($B%d,%s,0))" % (col("K"), r + 1, ranks),
            styles.get("text"), value=notes[key])
    t1 = TBL_FIRST + n - 1
    cells.text(ws, t1 + 1, 1, TIER_NOTE, styles.get("note"))
    cells.text(ws, t1 + 2, 1, BARRIER_NOTE, styles.get("note"))
    for name, c in (("MACC_Rank_Measure", "C"), ("MACC_Rank_Width", "D"),
                    ("MACC_Rank_Cost", "E"), ("MACC_Rank_Tier", "J")):
        cells.define_name(name, "=%s!$%s$%d:$%s$%d" % (
            SHEET, c, TBL_FIRST + 1, c, t1 + 1))
    for name, c in (("MACC_Chart_Width", "E"), ("MACC_Chart_Height", "D")):
        cells.define_name(name, "=%s!$%s$%d:$%s$%d" % (
            SHEET, c, s0 + 1, c, s1 + 1))
    for r in range(d0, d1 + 1):
        ws.set_row(r, 40)
    ws.set_row(g.header_row, 38)
    ws.set_row(g.sort_header_row, 26)

    # --- charts
    total = max(sum(res.chart_widths) for res in all_states(dataset.inputs).values())
    title_ref = "=%s!$B$%d" % (SHEET, TITLE_ROW + 1)
    step = nice_step(total)
    axis_max = int(-(-total // step) * step)
    chart_a = macc_area_chart(wb, a_layout, title=title_ref,
                              major_unit=step, label_col=7,
                              size=(980, 460), axis_max=axis_max)
    cells.insert_chart(ws, CHART_A_CELL, chart_a)
    # Zoom chart: same series as chart A, x-axis cut just above the largest
    # cumulative abatement of the "Do first" (negative-cost) measures over all
    # six selector states. Computed, not hard-coded.
    first_tot = 0
    for res in all_states(dataset.inputs).values():
        first_tot = max(first_tot, sum(
            w for w, t in zip(res.chart_widths, res.tiers) if t == "Do first"))
    zstep = nice_step(first_tot, max_intervals=5)
    zoom_max = int(-(-first_tot // zstep) * zstep)
    cells.text(ws, 16, 10,
               "Zoom view: the same data as the full chart, with the x-axis "
               "cut at %d tCO2e, so it never shows the full curve." % zoom_max,
               styles.get("note"))
    chart_z = macc_area_chart(
        wb, a_layout, title="Zoom: money-saving measures (first %d tCO2e)"
        % zoom_max, major_unit=zstep, label_col=7, size=(700, 460),
        axis_max=zoom_max)
    cells.insert_chart(ws, ZOOM_CELL, chart_z)
    c_layout = write_macc_c_block(cells, styles, ws, a_layout, srt, g)
    chart_c = macc_column_chart(
        wb, c_layout, title="Fallback view (200-bin column chart): same ranking",
        size=(980, 460))
    cells.insert_chart(ws, CHART_C_CELL, chart_c)
    return MaccSheetLayout(
        (TBL_FIRST, t1), (d0, d1), (s0, s1),
        (a_layout.helper_first_row, a_layout.helper_last_row),
        "G%d" % (REF_ROW + 1), "B%d" % (TITLE_ROW + 1), a_layout, c_layout,
        step, axis_max)
