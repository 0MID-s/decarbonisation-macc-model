"""SYNTHETIC FIXTURE DATA - not real, for pipeline tests only (D-12).

Nothing in this module is a real figure or a real source. It must never be
imported by config/ or presented in a deliverable workbook.
"""
import datetime

from config.schema import (
    InputRecord, Kind, NOT_APPLICABLE, PriceBasis, Source, Status,
)

_D = datetime.date(2026, 10, 17)

SYNTHETIC_SOURCES = (
    Source(
        id="Src_SynthA",
        publisher="SYNTHETIC FIXTURE (not a real source)",
        dataset="Synthetic dataset A",
        url="https://ec.europa.eu/eurostat/",
        edition="synthetic",
        retrieved=_D,
        licence_note="Synthetic test data, no licence",
    ),
    Source(
        id="Src_SynthB",
        publisher="SYNTHETIC FIXTURE (not a real source)",
        dataset="Synthetic dataset B",
        url="https://www.gov.uk/",
        edition="synthetic",
        retrieved=_D,
        licence_note="Synthetic test data, no licence",
    ),
)

_EUR_NOM = PriceBasis("EUR", 2025, "nominal")
_EUR_REAL = PriceBasis("EUR", 2025, "real")


def _scalar(id_, section, desc, value, unit, conv, model_unit, basis, src,
            status, rationale=""):
    return InputRecord(
        id=id_, section=section, description=desc, published_value=value,
        published_unit=unit, conversion_ref=conv, model_unit=model_unit,
        price_basis=basis, source_id=src, status=status, rationale=rationale,
    )


SYNTHETIC_INPUTS = (
    _scalar("Const_None", "Constants",
            "SYNTHETIC identity conversion factor", 1.0, "factor", None,
            "factor", NOT_APPLICABLE, None, Status.ASSUMPTION,
            "Identity factor, one formula pattern (D-11)."),
    _scalar("Time_FirstYear", "Constants",
            "SYNTHETIC first model year", 2026.0, "year", None, "year",
            NOT_APPLICABLE, None, Status.ASSUMPTION,
            "Synthetic timeline start."),
    _scalar("Const_SynthKWhPerMWh", "Constants",
            "SYNTHETIC kWh per MWh", 1000.0, "factor", None, "factor",
            NOT_APPLICABLE, None, Status.ASSUMPTION,
            "Synthetic unit conversion constant."),
    _scalar("Baseline_SynthGasMWh", "Baseline",
            "SYNTHETIC gas use", 12.5, "MWh", "Const_SynthKWhPerMWh", "kWh",
            NOT_APPLICABLE, "Src_SynthA", Status.SOURCED),
    _scalar("Energy_SynthElecPrice", "Energy prices",
            "SYNTHETIC electricity price", 0.16, "EUR/kWh", "Const_None",
            "EUR/kWh", _EUR_NOM, "Src_SynthA", Status.SOURCED),
    _scalar("EF_SynthGas", "Emission factors",
            "SYNTHETIC gas emission factor", 0.18, "kg CO2e/kWh",
            "Const_None", "kg CO2e/kWh", NOT_APPLICABLE, "Src_SynthB",
            Status.SOURCED),
    InputRecord(
        id="CarbonPrice_SynthCentral", section="Carbon prices",
        description="SYNTHETIC central carbon price path",
        published_value=None, published_unit="EUR/tCO2e",
        conversion_ref="Const_None", model_unit="EUR/tCO2e",
        price_basis=_EUR_REAL, source_id="Src_SynthB", status=Status.SOURCED,
        rationale="", kind=Kind.SERIES,
        series=tuple((2026 + i, 60.0 + 5.0 * i) for i in range(10)),
    ),
    _scalar("Finance_SynthWacc", "Finance",
            "SYNTHETIC discount rate", 0.08, "fraction", "Const_None",
            "fraction", NOT_APPLICABLE, None, Status.ASSUMPTION,
            "Synthetic analyst assumption with a stated rationale."),
    _scalar("Measure_SynthCapex", "Measures",
            "SYNTHETIC measure capex", 250000.0, "EUR", "Const_None", "EUR",
            _EUR_NOM, None, Status.ASSUMPTION,
            "Synthetic analyst assumption with a stated rationale."),
)

# (name, annual_abatement_t, cost_eur_per_t); deliberately not sorted by cost.
SYNTHETIC_MEASURES = (
    ("Synthetic M1", 2400, 35.0),
    ("Synthetic M2", 5200, -48.0),
    ("Synthetic M3", 900, 112.5),
    ("Synthetic M4", 3700, -6.0),
    ("Synthetic M5", 1600, 0.4),
    ("Synthetic M6", 5900, 71.0),
)

# SYNTHETIC reference carbon price (EUR/tCO2e) for the spike line; not a real price.
SYNTHETIC_REFERENCE_PRICE = 80.0
