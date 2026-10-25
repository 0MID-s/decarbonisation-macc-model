"""Rates sheet: HICP ratios and EUR 2025 restatements (plan 02-10, D-01).

Every formula is live on named Inputs; cached values come from
checkmodel.rates_reference.
"""
from dataclasses import dataclass
from typing import Tuple

from checkmodel.baseline_reference import model_values
from checkmodel.rates_reference import (
    discount_rate_real, eur2025_conversions, fisher_real, hicp_ratio,
    restate_eur2025)
from xl.layout import LABEL_COL, UNIT_COL, setup_sheet
from xl.sheets.common import get_or_add, num_role_for_unit, write_title_band
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
    ws = get_or_add(wb, "Rates")
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=4)
    write_title_band(
        cells, styles, ws, "Rates",
        "Price-index restatements to EUR 2025 and the discount-rate "
        "derivation (Damodaran Europe, Fisher to real)",
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
    r = _discount_block(ws, cells, styles, v, r + 2, rows)
    return RatesLayout(tuple(rows))


def _discount_block(ws, cells, styles, v, r, rows):
    sec = styles.get("section")
    note = styles.get("note")
    label, unit = styles.get("label"), styles.get("unit")
    cells.text(ws, r, LABEL_COL,
               "Discount rate (Damodaran Europe, Fisher to real, D-18/D-19)",
               sec)
    for c in range(LABEL_COL + 1, LAST_COL + 1):
        cells.blank(ws, r, c, sec)
    pct = "pct"
    r += 1
    cells.text(ws, r, LABEL_COL, "Nominal cost of capital, Chemical "
               "(Specialty), Europe (Damodaran, Euros column)", label)
    cells.text(ws, r, UNIT_COL, "%", unit)
    cells.formula(ws, r, ORIG_COL, "=Fin_CoC_ChemSpecialty",
                  styles.get("link", pct), value=v["Fin_CoC_ChemSpecialty"])
    nom = "D%d" % (r + 1)
    r += 1
    cells.text(ws, r, LABEL_COL, "Long-run euro inflation (ECB target)", label)
    cells.text(ws, r, UNIT_COL, "%", unit)
    cells.formula(ws, r, ORIG_COL, "=Fin_InflationLongRun",
                  styles.get("link", pct), value=v["Fin_InflationLongRun"])
    r += 1
    cells.text(ws, r, LABEL_COL, "Real discount rate = (1 + nominal) / "
               "(1 + inflation) - 1", label)
    cells.text(ws, r, UNIT_COL, "%", unit)
    cells.formula(ws, r, ORIG_COL,
                  "=(1+%s)/(1+Fin_InflationLongRun)-1" % nom,
                  styles.get("calc", pct), value=discount_rate_real(v))
    cells.define_name("Rate_DiscountReal", "=Rates!$D$%d" % (r + 1))
    rows.append(("Rate_DiscountReal", r))
    cells.text(ws, r, ORIG_COL + 1,
               "Damodaran's Euros column embeds 1.5% expected euro inflation; "
               "the model uses the ECB 2.0% target, so the real rate is lower "
               "than with Damodaran's own assumption (D-42)", note)
    for iid, text in (("Fin_CoC_ChemBasic", "Memo: real rate, Chemical (Basic)"),
                      ("Fin_CoC_ChemDiversified",
                       "Memo: real rate, Chemical (Diversified)")):
        r += 1
        cells.text(ws, r, LABEL_COL, text, label)
        cells.text(ws, r, UNIT_COL, "%", unit)
        cells.formula(ws, r, ORIG_COL,
                      "=(1+%s)/(1+Fin_InflationLongRun)-1" % iid,
                      styles.get("calc", pct),
                      value=fisher_real(v[iid], v["Fin_InflationLongRun"]))
    r += 1
    cells.text(ws, r, LABEL_COL, "Context: euro-area HICP inflation, "
               "September 2026", label)
    cells.text(ws, r, UNIT_COL, "%", unit)
    cells.formula(ws, r, ORIG_COL, "=Fin_HICP_EA_Sep2026",
                  styles.get("link", pct), value=v["Fin_HICP_EA_Sep2026"])
    cells.text(ws, r, ORIG_COL + 1,
               "context only, Phase 4 sensitivity (D-19)", note)
    r += 2
    cells.text(ws, r, LABEL_COL,
               "No size or illiquidity premium (D-20); 6%/8%/10% "
               "rank-stability test in Phase 4", note)
    return r
