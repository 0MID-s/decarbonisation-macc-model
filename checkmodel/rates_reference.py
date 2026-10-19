"""Price-index restatement reference (plan 02-10, D-01).

Stdlib + config only. EUR 2025 value = value x HICP 2025 / HICP price year.
"""
from typing import Dict, List, Sequence, Tuple

from config.schema import Kind

# Exempt from restatement, with the reason:
#  Base_SBS_*      Eurostat SBS values are used only inside ratios (firm /
#                  sector), so the price year cancels.
#  Price_Elec26S1_ / Price_Gas26S1_  2026-S1 prices are context rows shown
#                  beside the 2025 averages; they are not model inputs.
#  Fin_FX_*        exchange rates are not euro amounts; the 2010 USD per EUR
#                  rate is used only inside the NGFS conversion (D-41), which
#                  applies HICP 2025 / HICP 2010 itself.
EXEMPT_PREFIXES = ("Base_SBS_", "Price_Elec26S1_", "Price_Gas26S1_",
                   "Fin_FX_")
#  Price year after 2025 (PBL SDE++ advice, EUR 2026): no annual 2026 HICP
#  exists yet (the year is incomplete), so these values are used as stated and
#  flagged on the Notes sheet; the price year is a label, not verified.
EXEMPT_AFTER_BASE = True
TARGET_YEAR = 2025


def eur2025_conversions(inputs):
    # type: (Sequence) -> List[Tuple[str, int]]
    out = []
    for r in inputs:
        pb = r.price_basis
        if r.kind != Kind.SCALAR or r.section == "Constants":
            continue
        if pb.currency != "EUR" or pb.year == TARGET_YEAR:
            continue
        if r.id.startswith(EXEMPT_PREFIXES):
            continue
        if pb.year > TARGET_YEAR:
            continue  # see EXEMPT_AFTER_BASE
        out.append((r.id, pb.year))
    return out


def hicp_ratio(v, year):
    # type: (Dict[str, float], int) -> float
    key = "Fin_HICP_EA_%d" % year
    if key not in v:
        raise ValueError("missing HICP input %s" % key)
    return v["Fin_HICP_EA_%d" % TARGET_YEAR] / v[key]


def restate_eur2025(v, input_id, year):
    # type: (Dict[str, float], str, int) -> float
    return v[input_id] * hicp_ratio(v, year)


def fisher_real(nominal, inflation):
    # type: (float, float) -> float
    """Fisher: (1 + nominal) / (1 + inflation) - 1 (D-19, D-42)."""
    return (1.0 + nominal) / (1.0 + inflation) - 1.0


def discount_rate_real(v):
    # type: (Dict[str, float]) -> float
    """Real discount rate from the Damodaran Euros column (no currency
    adjustment, D-42) and the ECB 2% target."""
    return fisher_real(v["Fin_CoC_ChemSpecialty"], v["Fin_InflationLongRun"])
