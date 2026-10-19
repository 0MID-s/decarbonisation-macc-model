"""Constants section: structural and unit-conversion constants (02-02)."""
from typing import Tuple

from config._helpers import NA, scalar
from config.schema import InputRecord, NOT_APPLICABLE, Status


def _c(id_, desc, value, unit, rationale):
    return scalar(id_, "Constants", desc, value, unit, None, unit, NA, None,
                  Status.ASSUMPTION, rationale)


INPUTS = (
    InputRecord(
        id="Const_None", section="Constants",
        description="Identity conversion factor (no unit change)",
        published_value=1.0, published_unit="factor", conversion_ref=None,
        model_unit="factor", price_basis=NOT_APPLICABLE, source_id=None,
        status=Status.ASSUMPTION,
        rationale=("Identity factor used where the published unit already "
                   "equals the model unit, so every Model value keeps one "
                   "formula pattern (D-11)."),
    ),
    InputRecord(
        id="Time_FirstYear", section="Constants",
        description="First model year (timeline column 1)",
        published_value=2026.0, published_unit="year", conversion_ref=None,
        model_unit="year", price_basis=NOT_APPLICABLE, source_id=None,
        status=Status.ASSUMPTION,
        rationale=("Analyst choice: appraisal timeline 2026-2055 starts in "
                   "the current year."),
    ),
    _c("Const_TJ_to_MWh", "Terajoule to megawatt-hour", 1000.0 / 3.6,
       "MWh/TJ",
       "Definitional SI conversion: 1 TJ = 10^6 MJ = 1000/3.6 MWh"),
    _c("Const_GJ_per_MWh", "Gigajoules per megawatt-hour", 3.6, "GJ/MWh",
       "Definitional SI conversion: 1 MWh = 3.6 GJ"),
    _c("Const_kWh_per_MWh", "Kilowatt-hours per megawatt-hour", 1000.0,
       "kWh/MWh", "Definitional: 1 MWh = 1000 kWh"),
    _c("Const_g_per_kWh_to_t_per_MWh",
       "Grams per kWh to tonnes per MWh", 0.001, "(t/MWh)/(g/kWh)",
       "Definitional: 1 g/kWh = 1000 g/MWh = 0.001 t/MWh"),
    _c("Const_PctToFrac", "Per cent to fraction", 0.01,
       "fraction per per cent", "Definitional: 1 per cent = 0.01"),
    _c("Const_HoursPerYear", "Hours per year", 8760.0, "h/yr",
       "365-day year, used only for the D-07 average-load sanity row"),
    _c("Const_kg_per_t", "Kilograms per tonne", 1000.0, "kg/t",
       "Definitional: 1 t = 1000 kg"),
    _c("Const_g_per_kg", "Grams per kilogram", 1000.0, "g/kg",
       "Definitional: 1 kg = 1000 g"),
    _c("Const_Mega_per_kilo", "Mega per kilo factor", 1000.0,
       "factor (mega per kilo)",
       "Converts M EUR per MW to EUR per kW, 10^6/10^3"),
    _c("Const_PerMW_to_PerkW", "Cost per MW to cost per kW", 0.001, "MW/kW",
       "Converts a cost per MW to a cost per kW: 1 kW = 0.001 MW"),
    _c("Const_CheckTolerance", "Check tolerance", 1e-6, "abs tolerance",
       "Absolute tolerance for OK/ERROR reconciliation checks"),
    _c("Const_km_per_100km", "Kilometres per 100 km", 100.0,
       "km per 100 km", "Definitional: 100 km = 100 km"),
)  # type: Tuple[InputRecord, ...]

SOURCES = ()
