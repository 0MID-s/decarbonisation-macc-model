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
class MaccGeometry:
    """Zero-based row positions of the helper tables on one sheet."""
    sheet: str
    header_row: int
    data_first: int
    sort_header_row: int
    sort_first: int
    slot_row: int
    name_row: int
    helper_first: int
    c_total_row: int
    c_slot_row: int
    c_name_row: int
    c_first: int


SPIKE_GEOMETRY = MaccGeometry(
    SHEET_A, HEADER_ROW, DATA_FIRST, SORT_HEADER_ROW, SORT_FIRST, SLOT_ROW,
    NAME_ROW, HELPER_FIRST, C_TOTAL_ROW, C_SLOT_ROW, C_NAME_ROW, C_FIRST)


@dataclass(frozen=True)
class LinkedRow:
    """One measure of the linked data block (formulas plus cached values)."""
    name: str
    width_f: str
    width_v: float
    cost_f: str
    cost_v: object          # float, or the n/a text
    elig_f: str
    elig_v: int
    extras: Tuple[tuple, ...]   # (formula, cached value, number role) x4
    note: str               # barrier note text (analyst commentary)


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
    feed_col: object = None   # date-formatted copy of x (chart A categories)


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


def write_macc_c_block(cells, styles, ws, a_layout, sorted_ref,
                       geometry=SPIKE_GEOMETRY):
    # type: (object, object, object, MaccALayout, Sequence[tuple], MaccGeometry) -> MaccCLayout
    n = len(sorted_ref)
    bins = ref.macc_c_bins(sorted_ref, MACC_C_BINS)
    vals = ref.macc_c_values(sorted_ref, MACC_C_BINS)
    cum = ref.cumulative(sorted_ref)
    total = cum[-1][1]
    a = a_layout.sheet
    s0, s1 = a_layout.sorted_rows[0] + 1, a_layout.sorted_rows[1] + 1
    first, last = geometry.c_first, geometry.c_first + MACC_C_BINS - 1
    hdr = styles.get("header")
    lbl = styles.get("label")

    cells.text(ws, geometry.c_total_row, 1, "Total annual abatement (tCO2e)", lbl)
    cells.formula(ws, geometry.c_total_row, 3, "=SUM(%s!$E$%d:$E$%d)" % (a, s0, s1),
                  styles.get("link", "tco2e"), value=total)
    cells.text(ws, geometry.c_total_row + 1, 1, "Number of bins", lbl)
    cells.formula(ws, geometry.c_total_row + 1, 3,
                  "=COUNT($B$%d:$B$%d)" % (first + 1, last + 1),
                  styles.get("calc", "int"), value=MACC_C_BINS)
    cells.text(ws, geometry.c_total_row + 2, 1, "Bin width (tCO2e)", lbl)
    cells.formula(ws, geometry.c_total_row + 2, 3, "=D%d/D%d" % (geometry.c_total_row + 1, geometry.c_total_row + 2),
                  styles.get("calc", "eur2"), value=total / MACC_C_BINS)

    cells.text(ws, geometry.c_slot_row, 1, "Series slot number", lbl)
    for c, t in enumerate(("Bin", "Bin start (tCO2e)", "Slot")):
        cells.text(ws, geometry.c_name_row, 1 + c, t, hdr)
    series_cols = tuple(4 + k for k in range(n))
    for k, col in enumerate(series_cols):
        cl = xl_col_to_name(col)
        cells.number(ws, geometry.c_slot_row, col, k + 1, styles.get("index"))
        cells.formula(ws, geometry.c_name_row, col,
                      "=INDEX(%s!$C$%d:$C$%d,%s$%d)" % (a, s0, s1, cl, geometry.c_slot_row + 1),
                      styles.get("link"), value=sorted_ref[k][0])
    for i, (idx, start, slot) in enumerate(bins):
        r = first + i
        cells.number(ws, r, 1, idx, styles.get("index"))
        cells.formula(ws, r, 2, "=($B%d-1)*$D$%d" % (r + 1, geometry.c_total_row + 3),
                      styles.get("calc", "eur2"), value=start)
        cells.formula(ws, r, 3, "=MATCH($C%d,%s!$F$%d:$F$%d,1)" % (r + 1, a, s0, s1),
                      styles.get("link", "int"), value=slot)
        for k, col in enumerate(series_cols):
            cl = xl_col_to_name(col)
            cells.formula(
                ws, r, col,
                "=IF($D%d=%s$%d,INDEX(%s!$D$%d:$D$%d,$D%d),0)"
                % (r + 1, cl, geometry.c_slot_row + 1, a, s0, s1, r + 1),
                styles.get("link", "eur2"), value=vals[i][k])
    return MaccCLayout(ws.get_name(), first, last, 2, series_cols, geometry.c_name_row)


def write_macc_linked_block(cells, styles, ws, geometry, rows, ref_price_name,
                            ref_price):
    # type: (object, object, object, MaccGeometry, Sequence[LinkedRow], str, float) -> MaccALayout
    """Data, sorted and helper tables for the real MACC (links, not numbers).

    Columns: data B name, C width, D cost (EUR/t or n/a text), E rank,
    F eligible flag, G-J extra table values, K barrier note. The sorted block
    reads chart width/height (0 for a measure with no abatement), never the
    raw cost, so text in a cost cell cannot break the arithmetic.
    """
    n = len(rows)
    meas = [(r.name, r.width_v, r.cost_v if r.elig_v else 0, bool(r.elig_v))
            for r in rows]
    ranks = ref.input_ranks_eligible(meas)
    srt = ref.rank_measures_eligible(meas)
    sorted_elig = [0] * n
    for r, rk in zip(rows, ranks):
        sorted_elig[rk - 1] = 1 if r.elig_v else 0
    cum = ref.cumulative(srt)
    pts = ref.macc_a_points(srt)
    vals = ref.macc_a_values(srt)
    hdr = styles.get("header")
    g = geometry
    hdr_row = g.header_row
    d0, d1 = g.data_first, g.data_first + n - 1
    s0, s1 = g.sort_first, g.sort_first + n - 1
    h0 = g.helper_first
    h1 = h0 + 4 * n - 1

    for c, t in enumerate(("Measure", "Annual abatement (tCO2e, selected "
                           "basis)", "Cost (EUR per tCO2e)",
                           "Rank (1 = cheapest)", "Abatement on basis (1/0)",
                           "Financial NPV (after subsidy)", "NPV before subsidy",
                           "IRR", "Discounted payback (years)",
                           "Barrier note (analyst commentary)")):
        cells.text(ws, hdr_row, 1 + c, t, hdr)
    dcost = "$D$%d:$D$%d" % (d0 + 1, d1 + 1)
    delig = "$F$%d:$F$%d" % (d0 + 1, d1 + 1)
    for i, row in enumerate(rows):
        r = d0 + i
        cells.text(ws, r, 1, row.name, styles.get("label"))
        cells.formula(ws, r, 2, row.width_f, styles.get("link", "tco2e"),
                      value=row.width_v)
        cells.formula(ws, r, 3, row.cost_f, styles.get("link", "eur_per_t"),
                      value=row.cost_v)
        cells.formula(
            ws, r, 4,
            "=IF(F%d=1,RANK(D%d,%s,1)+COUNTIF($D$%d:D%d,D%d),"
            "COUNT(%s)+COUNTIF($F$%d:F%d,0))"
            % (r + 1, r + 1, dcost, hdr_row + 1, r, r + 1, dcost, d0 + 1, r + 1),
            styles.get("calc", "int"), value=ranks[i])
        cells.formula(ws, r, 5, row.elig_f, styles.get("link", "int"),
                      value=row.elig_v)
        for j, (f, v, num) in enumerate(row.extras):
            cells.formula(ws, r, 6 + j, f, styles.get("link", num), value=v)
        cells.text(ws, r, 10, row.note, styles.get("text"))

    # Sorted block.
    for c, t in enumerate(("Slot", "Measure", "Chart height (EUR per tCO2e)",
                           "Chart width (tCO2e)", "Start", "End",
                           "Chart label", "Abatement on basis (1/0)")):
        cells.text(ws, g.sort_header_row, 1 + c, t, hdr)
    rank_rng = "$E$%d:$E$%d" % (d0 + 1, d1 + 1)
    names = "$B$%d:$B$%d" % (d0 + 1, d1 + 1)
    width = "$C$%d:$C$%d" % (d0 + 1, d1 + 1)
    for k in range(n):
        r = s0 + k
        m = "MATCH($B%d,%s,0)" % (r + 1, rank_rng)
        elig = "INDEX(%s,%s)=1" % (delig, m)
        cells.number(ws, r, 1, k + 1, styles.get("index"))
        cells.formula(ws, r, 2, "=INDEX(%s,%s)" % (names, m),
                      styles.get("calc"), value=srt[k][0])
        cells.formula(ws, r, 3, "=IF(%s,INDEX(%s,%s),0)" % (elig, dcost, m),
                      styles.get("calc", "eur2"), value=srt[k][2])
        cells.formula(ws, r, 4, "=IF(%s,ROUND(INDEX(%s,%s),0),0)"
                      % (elig, width, m),
                      styles.get("calc", "tco2e"), value=cum[k][1] - cum[k][0])
        cells.formula(ws, r, 5,
                      "=SUM($E$%d:E%d)" % (g.sort_header_row + 1, r),
                      styles.get("calc", "tco2e"), value=cum[k][0])
        cells.formula(ws, r, 6, "=F%d+E%d" % (r + 1, r + 1),
                      styles.get("calc", "tco2e"), value=cum[k][1])
        cells.formula(ws, r, 7, '=IF(%s,INDEX(%s,%s),"")' % (elig, names, m),
                      styles.get("calc"),
                      value=srt[k][0] if sorted_elig[k] else "")
        cells.formula(ws, r, 8, "=INDEX(%s,%s)" % (delig, m),
                      styles.get("calc", "int"), value=sorted_elig[k])

    # Chart helper block.
    cells.text(ws, g.slot_row, 1, "Series slot number", styles.get("label"))
    for c, t in enumerate(("Slot", "Edge", "Height flag",
                           "x: cumulative abatement (tCO2e)")):
        cells.text(ws, g.name_row, 1 + c, t, hdr)
    series_cols = tuple(5 + k for k in range(n))
    ref_col = 5 + n
    for k, col in enumerate(series_cols):
        cells.number(ws, g.slot_row, col, k + 1, styles.get("index"))
        cl = xl_col_to_name(col)
        cells.formula(ws, g.name_row, col,
                      "=INDEX($C$%d:$C$%d,%s$%d)" % (s0 + 1, s1 + 1, cl, g.slot_row + 1),
                      hdr, value=srt[k][0])
    cells.text(ws, g.name_row, ref_col, "Reference carbon price", hdr)
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
                % (r + 1, cl, g.slot_row + 1, r + 1, s0 + 1, s1 + 1, r + 1),
                styles.get("calc", "eur2"), value=vals[i][k])
        cells.formula(ws, r, ref_col, "=" + ref_price_name,
                      styles.get("calc", "eur2"), value=ref_price)
    # Chart axis feed: a date-formatted copy of x. XlsxWriter always writes
    # c:auto=1 on a date axis, so Excel only uses a true number-scale axis when
    # the category cells carry a date number format. The visible tonnes column
    # stays a plain number format.
    feed_col = ref_col + 1
    cells.text(ws, g.slot_row, feed_col,
               "Chart axis feed: same tonnes as column E, date-formatted only "
               "so Excel spaces the bars by tCO2e (read as tonnes, not dates)",
               styles.get("note"))
    cells.text(ws, g.name_row, feed_col, "Chart axis feed (tCO2e)", hdr)
    for i, (slot, edge, flag, x) in enumerate(pts):
        r = h0 + i
        cells.formula(ws, r, feed_col, "=E%d" % (r + 1),
                      styles.get("calc", "date_feed"), value=x)
    layout = MaccALayout(g.sheet, (d0, d1), (s0, s1), h0, h1, 4, series_cols,
                         g.name_row, ref_col, feed_col)
    return layout, tuple(srt)
