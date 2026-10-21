"""Independent finance layer for QA-02 (plan 03-05).

Stdlib only, written from textbook definitions rather than from sheet
formulas. Conventions:
- NPV with year 0 (2026) undiscounted: NPV = sum cf[n] / (1+r)^n.
- Excel's NPV() discounts its first value by one period (Microsoft NPV
  docs), so cf[0] + excel_npv(r, cf[1:]) equals npv0(r, cf).
- IRR is the unique root of NPV(r) on [-0.99, 10]; otherwise it is reported
  as not available.
"""
import math
from typing import List, Optional, Sequence, Union

from config.build_config import BUILD

NA_NO_OUTLAY = "n/a (no upfront outlay)"
NA_NEVER_PAYS = "n/a (never pays back)"
NA_NO_SOLUTION = "n/a (no solution found)"
NA_NO_ABATEMENT = "n/a (no abatement on this basis)"
NOT_WITHIN = "Not within %d" % BUILD.timeline_end
MULTI_SIGN = "multiple sign changes: IRR may not be unique"

IRR_LO = -0.99
IRR_HI = 10.0

Number = Union[int, float]


def discount_factors(rate, n_years):
    # type: (float, int) -> List[float]
    return [1.0 / (1.0 + rate) ** n for n in range(n_years)]


def npv0(rate, cf):
    # type: (float, Sequence[Number]) -> float
    return sum(c / (1.0 + rate) ** n for n, c in enumerate(cf))


def excel_npv(rate, values):
    # type: (float, Sequence[Number]) -> float
    """Excel NPV(): the first value is discounted one full period."""
    return sum(v / (1.0 + rate) ** (i + 1) for i, v in enumerate(values))


def sign_changes(cf):
    # type: (Sequence[Number]) -> int
    signs = [1 if c > 0 else -1 for c in cf if c != 0]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


def _grid():
    # type: () -> List[float]
    pts = set()
    for i in range(2001):
        pts.add(IRR_LO + (IRR_HI - IRR_LO) * i / 2000.0)
    for i in range(2001):
        pts.add(-0.2 + 1.2 * i / 2000.0)
    return sorted(pts)


_GRID = _grid()


def irr(cf):
    # type: (Sequence[Number]) -> Optional[float]
    """Unique root of npv0 on [-0.99, 10] by bisection, else None."""
    vals = [npv0(r, cf) for r in _GRID]
    roots = []
    for i in range(len(_GRID)):
        if vals[i] == 0.0:
            roots.append((_GRID[i], _GRID[i]))
        elif i + 1 < len(_GRID) and vals[i] * vals[i + 1] < 0:
            roots.append((_GRID[i], _GRID[i + 1]))
    if len(roots) != 1:
        return None
    lo, hi = roots[0]
    if lo == hi:
        return lo
    flo = npv0(lo, cf)
    for _ in range(200):
        mid = (lo + hi) / 2.0
        fmid = npv0(mid, cf)
        if fmid == 0.0:
            return mid
        if (fmid < 0) == (flo < 0):
            lo, flo = mid, fmid
        else:
            hi = mid
        if hi - lo < 1e-13:
            break
    return (lo + hi) / 2.0


def irr_text(cf):
    # type: (Sequence[Number]) -> Union[float, str]
    if cf[0] >= 0:
        return NA_NO_OUTLAY
    if not any(c > 0 for c in cf):
        return NA_NEVER_PAYS
    r = irr(cf)
    return NA_NO_SOLUTION if r is None else r


def multiple_sign_flag(cf):
    # type: (Sequence[Number]) -> str
    return MULTI_SIGN if sign_changes(cf) > 1 else ""


def payback(cf):
    # type: (Sequence[Number]) -> Union[float, str]
    """Years to first non-negative cumulative, interpolated within the year."""
    if cf[0] >= 0:
        return NA_NO_OUTLAY
    cum = []
    total = 0.0
    for c in cf:
        total += c
        cum.append(total)
    for k, v in enumerate(cum):
        if v >= 0:
            return (k - 1) + (-cum[k - 1]) / cf[k]
    return NOT_WITHIN


def discounted_payback(cf, rate):
    # type: (Sequence[Number], float) -> Union[float, str]
    df = discount_factors(rate, len(cf))
    return payback([c * d for c, d in zip(cf, df)])


def levelised(npv_fin, pv_tonnes):
    # type: (float, float) -> Union[float, str]
    """Levelised abatement cost = -NPV / PV(tonnes)."""
    if pv_tonnes <= 0:
        return NA_NO_ABATEMENT
    return -npv_fin / pv_tonnes


def break_even(npv_fin, pv_tonnes):
    # type: (float, float) -> Union[float, str]
    """Carbon price at which NPV = 0: same closed form as levelised()."""
    return levelised(npv_fin, pv_tonnes)


def crf(rate, life):
    # type: (float, int) -> float
    if rate == 0:
        return 1.0 / life
    return rate / (1.0 - 1.0 / (1.0 + rate) ** life)


def annuity_cost(capex, rate, life, avg_net_operating_benefit, avg_tonnes):
    # type: (float, float, int, float, float) -> float
    """Annuity-form abatement cost, used only for the reconciliation."""
    return (capex * crf(rate, life) - avg_net_operating_benefit) / avg_tonnes


def levelised_price(price_row, df, op):
    # type: (Sequence[float], Sequence[float], Sequence[float]) -> float
    num = sum(p * d * o for p, d, o in zip(price_row, df, op))
    den = sum(d * o for d, o in zip(df, op))
    return num / den


def residual_fraction(last_n, life):
    # type: (int, int) -> float
    """Unexpired fraction of the last asset at the end of the horizon."""
    rem = last_n % life
    return 0.0 if rem == 0 else (life - rem) / float(life)


def replacement_flags(n_years, life):
    # type: (int, int) -> List[int]
    last = n_years - 1
    return [1 if 1 <= n < last and n % life == 0 else 0
            for n in range(n_years)]
