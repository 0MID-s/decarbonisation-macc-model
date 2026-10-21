"""Measure catalogue (03-04): display names and barrier notes, stack order.

Stdlib + typing only; imported by checkmodel and xl, never importing them.
Names and notes are analyst commentary (D-24), not sourced data.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MeasureSpec:
    key: str
    name: str
    barrier_note: str


MEASURES = (
    MeasureSpec(
        "LED", "LED lighting retrofit",
        "Analyst commentary: negative-cost but often not done - attention "
        "cost, small budgets, split incentives and installation downtime "
        "keep cheap measures on the shelf (after Kesicki & Ekins)."),
    MeasureSpec(
        "VSD", "Variable-speed drives on compressor motors",
        "Analyst commentary: negative-cost but often not done - attention "
        "cost, small budgets, split incentives and production downtime "
        "during installation (after Kesicki & Ekins)."),
    MeasureSpec(
        "HP", "High-temperature heat pump (replaces gas heat up to 125 C)",
        "Analyst commentary: the Belgian electricity-to-gas price ratio of "
        "about 3 erodes operating savings; high-temperature process "
        "integration carries technical risk."),
    MeasureSpec(
        "Fleet", "Fleet electrification (light vans)",
        "Analyst commentary: upfront price premium, depot charging and "
        "range planning are the barriers; the result is sensitive to the "
        "diesel price."),
    MeasureSpec(
        "PV", "Rooftop solar PV (self-consumed)",
        "Analyst commentary: roof structure, grid-connection lead time and "
        "capital rationing; full self-consumption is assumed."),
    MeasureSpec(
        "RC", "Renewable electricity contract (Guarantees of Origin)",
        "Analyst commentary: changes reported market-based Scope 2, not "
        "physical emissions; additionality is questionable and the premium "
        "recurs every year."),
)  # type: Tuple[MeasureSpec, ...]

MEASURE_KEYS = tuple(m.key for m in MEASURES)  # type: Tuple[str, ...]

COUNTERFACTUAL_NOTE = (
    "Heat pump and fleet use incremental capex over the purchase the firm "
    "would make anyway (gas boiler, diesel van); LED, VSD and PV are "
    "retrofits or additions at full capex; the contract has no capex (D-05)")
