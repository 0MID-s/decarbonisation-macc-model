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
    _c("Const_PerThousand", "Per thousand", 0.001, "per thousand",
       "Definitional: a price per 1000 litres divided by 1000 is a price "
       "per litre"),
    _c("Const_kW_per_MW", "Kilowatts per megawatt", 1000.0, "kW/MW",
       "Definitional: 1 MW = 1000 kW"),
    _c("Const_MWh_per_GO", "Megawatt-hours per Guarantee of Origin", 1.0,
       "MWh/GO", "One Guarantee of Origin covers 1 MWh (Directive (EU) "
       "2018/2001 art. 19(2), flagged as not re-read this phase)"),
    _c("Const_IRR_Guess", "IRR starting guess", 0.1, "fraction",
       "Starting value for Excel IRR (Excel default 10%); the Measures "
       "sheet flips its sign when the undiscounted sum of flows is "
       "negative so Excel searches near a negative root"),
    _c("Const_CheckTolMoney", "Check tolerance, money", 1.0,
       "abs tolerance (currency units)",
       "Absolute tolerance for euro reconciliation checks (SUMPRODUCT NPV "
       "vs CF0+NPV memo); Const_CheckTolerance (1e-6) is too tight for "
       "euro sums"),
    _c("Const_IRRCheckTolMoney", "Check tolerance, NPV at IRR", 10.0,
       "abs tolerance (currency units)",
       "Tolerance for NPV at the IRR = 0: Excel IRR is accurate to about "
       "1e-7 in the rate, which moves NPV by up to a few euros on these "
       "capex sizes (research Pitfall 4)"),
    _c("Const_AnnuityTolRel", "Annuity reconciliation tolerance, relative",
       0.05, "fraction",
       "Relative tolerance of the internal annuity vs levelised "
       "reconciliation. The annuity form annualises cost and tonnes with "
       "one capital recovery factor over the levelised-cost horizon, so the "
       "two forms agree for any profile; a gap beyond the tolerance means a "
       "broken row or formula (WR-10)"),
    _c("Const_AnnuityTolAbs", "Annuity reconciliation tolerance, absolute",
       1.0, "abs tolerance (currency units per tonne)",
       "Absolute floor for the annuity reconciliation for costs near zero"),
    _c("Const_MACCRoundTol", "MACC rounding tolerance per measure", 0.5,
       "tCO2e per measure",
       "Analyst assumption: MACC chart widths are rounded to whole tonnes "
       "(ROUND to 0 decimals in xl/macc.py), so the chart total can differ "
       "from the unrounded Measures total by up to half a tonne per "
       "measure; used only by the Dashboard tile vs MACC total check"),
)  # type: Tuple[InputRecord, ...]

SOURCES = ()
