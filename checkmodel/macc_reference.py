"""Pure-Python reference for the live-sorted MACC helper tables (D-17).

Measures are tuples (name, annual_abatement_t, cost_eur_per_t). Everything
here mirrors the spreadsheet formulas in xl/macc.py step for step.
"""
import math
from typing import List, Sequence, Tuple

Measure = Tuple[str, int, float]

N_BINS = 200


def _excel_round0(x):
    # type: (float) -> int
    """Excel ROUND(x, 0): half away from zero (differs from Python round)."""
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def input_ranks(measures):
    # type: (Sequence[Measure]) -> List[int]
    """RANK(cost, costs, 1) + COUNTIF(earlier costs, cost), in input order."""
    costs = [m[2] for m in measures]
    return [1 + sum(1 for x in costs if x < c)
            + sum(1 for x in costs[:i] if x == c)
            for i, c in enumerate(costs)]


def rank_measures(measures):
    # type: (Sequence[Measure]) -> List[Measure]
    """Cheapest first; ties keep input order."""
    ranks = input_ranks(measures)
    out = [None] * len(measures)
    for m, r in zip(measures, ranks):
        out[r - 1] = (m[0], m[1], m[2])
    return out


def cumulative(sorted_measures):
    # type: (Sequence[Measure]) -> List[Tuple[int, int]]
    out = []
    start = 0
    for m in sorted_measures:
        width = _excel_round0(m[1])
        out.append((start, start + width))
        start += width
    return out


def macc_a_points(sorted_measures):
    # type: (Sequence[Measure]) -> List[Tuple[int, int, int, int]]
    """(slot, edge, height_flag, x): four points per slot, slot-major."""
    cum = cumulative(sorted_measures)
    out = []
    for k, (start, end) in enumerate(cum):
        width = end - start
        for edge, flag in ((0, 0), (0, 1), (1, 1), (1, 0)):
            out.append((k + 1, edge, flag, start + edge * width))
    return out


def macc_a_values(sorted_measures):
    # type: (Sequence[Measure]) -> List[List[float]]
    n = len(sorted_measures)
    rows = []
    for slot, _edge, flag, _x in macc_a_points(sorted_measures):
        rows.append([flag * sorted_measures[s][2] if slot == s + 1 else 0
                     for s in range(n)])
    return rows


def macc_c_bins(sorted_measures, n_bins=N_BINS):
    # type: (Sequence[Measure], int) -> List[Tuple[int, float, int]]
    """(bin index, bin start, slot) with slot = MATCH(start, starts, 1)."""
    cum = cumulative(sorted_measures)
    total = sum(e - s for s, e in cum)
    width = total / n_bins
    out = []
    for i in range(1, n_bins + 1):
        start = (i - 1) * width
        slot = 1
        for k, (s, _e) in enumerate(cum):
            if s <= start:
                slot = k + 1
        out.append((i, start, slot))
    return out


def macc_c_values(sorted_measures, n_bins=N_BINS):
    # type: (Sequence[Measure], int) -> List[List[float]]
    n = len(sorted_measures)
    return [[sorted_measures[s][2] if slot == s + 1 else 0 for s in range(n)]
            for (_i, _start, slot) in macc_c_bins(sorted_measures, n_bins)]


EligibleMeasure = Tuple[str, int, object, bool]


def input_ranks_eligible(measures):
    # type: (Sequence[EligibleMeasure]) -> List[int]
    """Eligible measures rank by cost (ties in input order); ineligible ones
    follow in input order (workbook rule: COUNT(costs) + COUNTIF(flags))."""
    elig_costs = [m[2] for m in measures if m[3]]
    n_elig = len(elig_costs)
    out = []
    seen_costs = []
    n_inelig = 0
    for m in measures:
        if m[3]:
            c = m[2]
            out.append(1 + sum(1 for x in elig_costs if x < c)
                       + sum(1 for x in seen_costs if x == c))
            seen_costs.append(c)
        else:
            n_inelig += 1
            out.append(n_elig + n_inelig)
    return out


def rank_measures_eligible(measures):
    # type: (Sequence[EligibleMeasure]) -> List[Measure]
    """Sorted list; ineligible measures carry width 0 and cost 0."""
    ranks = input_ranks_eligible(measures)
    out = [None] * len(measures)
    for m, r in zip(measures, ranks):
        out[r - 1] = (m[0], m[1], m[2]) if m[3] else (m[0], 0, 0)
    return out
