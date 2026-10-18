"""Literal-free MACC helper tables for techniques A and C (D-17).

Row and column numbers are zero-based in the layout dataclasses; the formula
strings use Excel A1 notation. Cached values come from
checkmodel.macc_reference. Measures arrive as arguments (name, annual
abatement tCO2e, cost EUR per tCO2e); no test module is used here.
"""
from dataclasses import dataclass
from typing import Sequence, Tuple

from checkmodel import macc_reference as ref
from xlsxwriter.utility import xl_col_to_name

MACC_C_BINS = 200
N_SLOTS = 6

SHEET_A = "MACC_A"
SHEET_C = "MACC_C"
CARBON_PRICE_NAME = "Spike_CarbonPrice"

# MACC_A zero-based rows.
HEADER_ROW = 5
DATA_FIRST = 6
PRICE_ROW = 12
SORT_HEADER_ROW = 13
SORT_FIRST = 14
SLOT_ROW = 21
NAME_ROW = 22
HELPER_FIRST = 23
# MACC_C zero-based rows.
C_TOTAL_ROW = 4
C_SLOT_ROW = 7
C_NAME_ROW = 8
C_FIRST = 9


@dataclass(frozen=True)
class MaccALayout:
    sheet: str
    data_rows: Tuple[int, int]
    sorted_rows: Tuple[int, int]
    helper_first_row: int
    helper_last_row: int
    x_col: int
    series_cols: Tuple[int, ...]
    name_row: int
    ref_col: int


@dataclass(frozen=True)
class MaccCLayout:
    sheet: str
    first_row: int
    last_row: int
    start_col: int
    series_cols: Tuple[int, ...]
    name_row: int


def _a(col, row, abs_col=True, abs_row=True):
    return "%s%s%s%d" % ("$" if abs_col else "", xl_col_to_name(col),
                         "$" if abs_row else "", row + 1)


def write_macc_a_block(cells, styles, ws, measures, carbon_price):
    # type: (object, object, object, Sequence[tuple], float) -> MaccALayout
    n = len(measures)
    if n != N_SLOTS:
        raise ValueError("the spike MACC block is built for %d measures" % N_SLOTS)
    srt = ref.rank_measures(measures)
    ranks = ref.input_ranks(measures)
    cum = ref.cumulative(srt)
    pts = ref.macc_a_points(srt)
    vals = ref.macc_a_values(srt)
    hdr = styles.get("header")
    d0, d1 = DATA_FIRST, DATA_FIRST + n - 1          # data rows
    s0, s1 = SORT_FIRST, SORT_FIRST + n - 1          # sorted rows
    h0 = HELPER_FIRST
    h1 = HELPER_FIRST + 4 * n - 1

    # Data block.
    for c, t in enumerate(("Measure (synthetic)", "Annual abatement (tCO2e)",
                           "Cost (EUR per tCO2e)", "Rank (1 = cheapest)")):
        cells.text(ws, HEADER_ROW, 1 + c, t, hdr)
    dcost = "$D$%d:$D$%d" % (d0 + 1, d1 + 1)
    for i, (name, ab, cost) in enumerate(measures):
        r = d0 + i
        cells.text(ws, r, 1, name, styles.get("input"))
        cells.number(ws, r, 2, ab, styles.get("input", "tco2e"))
        cells.number(ws, r, 3, cost, styles.get("input", "eur2"))
        cells.formula(
            ws, r, 4,
            "=RANK(D%d,%s,1)+COUNTIF($D$%d:D%d,D%d)"
            % (r + 1, dcost, HEADER_ROW + 1, r, r + 1),
            styles.get("calc", "int"), value=ranks[i])
    cells.text(ws, PRICE_ROW, 1, "Reference carbon price (synthetic)",
               styles.get("label"))
    cells.number(ws, PRICE_ROW, 3, carbon_price, styles.get("input", "eur2"))
    cells.define_name(CARBON_PRICE_NAME, "=%s!$D$%d" % (SHEET_A, PRICE_ROW + 1))

    # Sorted block.
    for c, t in enumerate(("Slot", "Measure", "Cost (EUR per tCO2e)",
                           "Width (tCO2e)", "Start", "End")):
        cells.text(ws, SORT_HEADER_ROW, 1 + c, t, hdr)
    rank_rng = "$E$%d:$E$%d" % (d0 + 1, d1 + 1)
    for k in range(n):
        r = s0 + k
        m = "MATCH($B%d,%s,0)" % (r + 1, rank_rng)
        cells.number(ws, r, 1, k + 1, styles.get("index"))
        cells.formula(ws, r, 2, "=INDEX($B$%d:$B$%d,%s)" % (d0 + 1, d1 + 1, m),
                      styles.get("calc"), value=srt[k][0])
        cells.formula(ws, r, 3, "=INDEX(%s,%s)" % (dcost, m),
                      styles.get("calc", "eur2"), value=srt[k][2])
        cells.formula(ws, r, 4,
                      "=ROUND(INDEX($C$%d:$C$%d,%s),0)" % (d0 + 1, d1 + 1, m),
                      styles.get("calc", "tco2e"), value=cum[k][1] - cum[k][0])
        cells.formula(ws, r, 5, "=SUM($E$%d:E%d)" % (SORT_HEADER_ROW + 1, r),
                      styles.get("calc", "tco2e"), value=cum[k][0])
        cells.formula(ws, r, 6, "=F%d+E%d" % (r + 1, r + 1),
                      styles.get("calc", "tco2e"), value=cum[k][1])

    # Chart helper block.
    cells.text(ws, SLOT_ROW, 1, "Series slot number", styles.get("label"))
    for c, t in enumerate(("Slot", "Edge", "Height flag",
                           "x: cumulative abatement (tCO2e)")):
        cells.text(ws, NAME_ROW, 1 + c, t, hdr)
    series_cols = tuple(5 + k for k in range(n))
    ref_col = 5 + n
    for k, col in enumerate(series_cols):
        cells.number(ws, SLOT_ROW, col, k + 1, styles.get("index"))
        cl = xl_col_to_name(col)
        cells.formula(ws, NAME_ROW, col,
                      "=INDEX($C$%d:$C$%d,%s$%d)" % (s0 + 1, s1 + 1, cl, SLOT_ROW + 1),
                      hdr, value=srt[k][0])
    cells.text(ws, NAME_ROW, ref_col, "Reference carbon price", hdr)
    for i, (slot, edge, flag, x) in enumerate(pts):
        r = h0 + i
        cells.number(ws, r, 1, slot, styles.get("index"))
        cells.number(ws, r, 2, edge, styles.get("index"))
        cells.number(ws, r, 3, flag, styles.get("index"))
        cells.formula(
            ws, r, 4,
            "=INDEX($F$%d:$F$%d,$B%d)+$C%d*INDEX($E$%d:$E$%d,$B%d)"
            % (s0 + 1, s1 + 1, r + 1, r + 1, s0 + 1, s1 + 1, r + 1),
            styles.get("calc", "tco2e"), value=x)
        for k, col in enumerate(series_cols):
            cl = xl_col_to_name(col)
            cells.formula(
                ws, r, col,
                "=IF($B%d=%s$%d,$D%d*INDEX($D$%d:$D$%d,$B%d),0)"
                % (r + 1, cl, SLOT_ROW + 1, r + 1, s0 + 1, s1 + 1, r + 1),
                styles.get("calc", "eur2"), value=vals[i][k])
        cells.formula(ws, r, ref_col, "=" + CARBON_PRICE_NAME,
                      styles.get("calc", "eur2"), value=carbon_price)
    return MaccALayout(SHEET_A, (d0, d1), (s0, s1), h0, h1, 4, series_cols,
                       NAME_ROW, ref_col)


def write_macc_c_block(cells, styles, ws, a_layout, sorted_ref):
    # type: (object, object, object, MaccALayout, Sequence[tuple]) -> MaccCLayout
    n = len(sorted_ref)
    bins = ref.macc_c_bins(sorted_ref, MACC_C_BINS)
    vals = ref.macc_c_values(sorted_ref, MACC_C_BINS)
    cum = ref.cumulative(sorted_ref)
    total = cum[-1][1]
    a = a_layout.sheet
    s0, s1 = a_layout.sorted_rows[0] + 1, a_layout.sorted_rows[1] + 1
    first, last = C_FIRST, C_FIRST + MACC_C_BINS - 1
    hdr = styles.get("header")
    lbl = styles.get("label")

    cells.text(ws, C_TOTAL_ROW, 1, "Total annual abatement (tCO2e)", lbl)
    cells.formula(ws, C_TOTAL_ROW, 3, "=SUM(%s!$E$%d:$E$%d)" % (a, s0, s1),
                  styles.get("link", "tco2e"), value=total)
    cells.text(ws, C_TOTAL_ROW + 1, 1, "Number of bins", lbl)
    cells.formula(ws, C_TOTAL_ROW + 1, 3,
                  "=COUNT($B$%d:$B$%d)" % (first + 1, last + 1),
                  styles.get("calc", "int"), value=MACC_C_BINS)
    cells.text(ws, C_TOTAL_ROW + 2, 1, "Bin width (tCO2e)", lbl)
    cells.formula(ws, C_TOTAL_ROW + 2, 3, "=D%d/D%d" % (C_TOTAL_ROW + 1, C_TOTAL_ROW + 2),
                  styles.get("calc", "eur2"), value=total / MACC_C_BINS)

    cells.text(ws, C_SLOT_ROW, 1, "Series slot number", lbl)
    for c, t in enumerate(("Bin", "Bin start (tCO2e)", "Slot")):
        cells.text(ws, C_NAME_ROW, 1 + c, t, hdr)
    series_cols = tuple(4 + k for k in range(n))
    for k, col in enumerate(series_cols):
        cl = xl_col_to_name(col)
        cells.number(ws, C_SLOT_ROW, col, k + 1, styles.get("index"))
        cells.formula(ws, C_NAME_ROW, col,
                      "=INDEX(%s!$C$%d:$C$%d,%s$%d)" % (a, s0, s1, cl, C_SLOT_ROW + 1),
                      styles.get("link"), value=sorted_ref[k][0])
    for i, (idx, start, slot) in enumerate(bins):
        r = first + i
        cells.number(ws, r, 1, idx, styles.get("index"))
        cells.formula(ws, r, 2, "=($B%d-1)*$D$%d" % (r + 1, C_TOTAL_ROW + 3),
                      styles.get("calc", "eur2"), value=start)
        cells.formula(ws, r, 3, "=MATCH($C%d,%s!$F$%d:$F$%d,1)" % (r + 1, a, s0, s1),
                      styles.get("link", "int"), value=slot)
        for k, col in enumerate(series_cols):
            cl = xl_col_to_name(col)
            cells.formula(
                ws, r, col,
                "=IF($D%d=%s$%d,INDEX(%s!$D$%d:$D$%d,$D%d),0)"
                % (r + 1, cl, C_SLOT_ROW + 1, a, s0, s1, r + 1),
                styles.get("link", "eur2"), value=vals[i][k])
    return MaccCLayout(ws.get_name(), first, last, 2, series_cols, C_NAME_ROW)
