"""Rates sheet: HICP ratios and EUR 2025 restatements (plan 02-10, D-01).

Every formula is live on named Inputs; cached values come from
checkmodel.rates_reference.
"""
from dataclasses import dataclass
from typing import Tuple

from checkmodel.baseline_reference import model_values
from checkmodel.rates_reference import (
    eur2025_conversions, hicp_ratio, restate_eur2025)
from xl.layout import LABEL_COL, UNIT_COL, setup_sheet
from xl.sheets.common import num_role_for_unit, write_title_band
from xl.styles import SheetKind

LAST_COL = 8
ORIG_COL, YEAR_COL, RATIO_COL, VAL_COL = 3, 4, 5, 6


@dataclass(frozen=True)
class RatesLayout:
    rows: Tuple[Tuple[str, int], ...]  # (name, zero-based row)


def build_rates(wb, styles, cells, dataset, cfg):
    v = model_values(dataset.inputs)
    by_id = {r.id: r for r in dataset.inputs}
    conv = eur2025_conversions(dataset.inputs)
    years = sorted(set(y for _, y in conv))
    ws = wb.add_worksheet("Rates")
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=4)
    write_title_band(
        cells, styles, ws, "Rates",
        "Price-index restatements to EUR 2025 (and, from plan 02-13, the "
        "discount-rate derivation)",
        "Euro-area HICP (prc_hicp_aind, 2015=100). EUR 2025 = value x HICP "
        "2025 / HICP price year (D-01)", LAST_COL)
    hdr = styles.get("header")
    for c, t in ((LABEL_COL, "Item"), (UNIT_COL, "Unit"),
                 (ORIG_COL, "Original"), (YEAR_COL, "Price basis"),
                 (RATIO_COL, "HICP ratio"), (VAL_COL, "EUR 2025")):
        cells.text(ws, 4, c, t, hdr)
    sec = styles.get("section")
    rows = []
    r = 5
    cells.text(ws, r, LABEL_COL, "Euro-area HICP ratios", sec)
    for c in range(LABEL_COL + 1, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    ratio_row = {}
    for y in years:
        r += 1
        name = "Rate_HICP_2025_%d" % y
        cells.text(ws, r, LABEL_COL, "HICP 2025 / HICP %d" % y,
                   styles.get("label"))
        cells.text(ws, r, UNIT_COL, "factor", styles.get("unit"))
        cells.formula(ws, r, ORIG_COL,
                      "=Fin_HICP_EA_2025/Fin_HICP_EA_%d" % y,
                      styles.get("calc", "dec5"), value=hicp_ratio(v, y))
        cells.define_name(name, "=Rates!$D$%d" % (r + 1))
        ratio_row[y] = r
        rows.append((name, r))
    r += 2
    cells.text(ws, r, LABEL_COL, "Inputs restated to EUR 2025", sec)
    for c in range(LABEL_COL + 1, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    for iid, y in conv:
        r += 1
        rec = by_id[iid]
        role = num_role_for_unit(rec.model_unit)
        cells.text(ws, r, LABEL_COL, rec.description, styles.get("label"))
        cells.text(ws, r, UNIT_COL, rec.model_unit, styles.get("unit"))
        cells.formula(ws, r, ORIG_COL, "=" + iid, styles.get("link", role),
                      value=v[iid])
        cells.text(ws, r, YEAR_COL, rec.price_basis.label,
                   styles.get("label"))
        cells.formula(ws, r, RATIO_COL, "=Rate_HICP_2025_%d" % y,
                      styles.get("calc", "dec5"), value=hicp_ratio(v, y))
        cells.formula(ws, r, VAL_COL, "=%s*Rate_HICP_2025_%d" % (iid, y),
                      styles.get("calc", role),
                      value=restate_eur2025(v, iid, y))
        cells.define_name(iid + "_EUR2025", "=Rates!$G$%d" % (r + 1))
        rows.append((iid + "_EUR2025", r))
    r += 2
    cells.text(ws, r, LABEL_COL,
               "Exempt from restatement: Eurostat SBS values (used only in "
               "ratios, price year cancels), 2026-S1 context prices, and "
               "exchange rates (not euro amounts).", styles.get("note"))
    return RatesLayout(tuple(rows))
