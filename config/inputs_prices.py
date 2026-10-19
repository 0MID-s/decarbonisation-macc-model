"""Energy prices section inputs (02-05): BE non-household bands, X_VAT."""
import datetime
from typing import Tuple

from config._helpers import NA, PriceBasis, Status, scalar
from config.schema import InputRecord, Source

_D = datetime.date(2026, 10, 19)
_LIC = ("Eurostat: free re-use for commercial and non-commercial purposes, "
        "source acknowledged")
_SEC = "Energy prices"
_S = Status.SOURCED

SOURCES = (
    Source("Src_EurostatElecPrice", "Eurostat",
           "Electricity prices for non-household consumers, bi-annual data "
           "(nrg_pc_205), tax = X_VAT (excluding VAT and other recoverable "
           "taxes and levies), currency EUR",
           "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205/default/table",
           "updated 2026-10-16 (per DATA_LOG); semesters 2025-S1, 2025-S2, "
           "2026-S1", _D, _LIC),
    Source("Src_EurostatGasPrice", "Eurostat",
           "Gas prices for non-household consumers, bi-annual data "
           "(nrg_pc_203), tax = X_VAT (excluding VAT and other recoverable "
           "taxes and levies), currency EUR; prices per kWh on a gross "
           "calorific value (GCV) basis; bands defined in GJ GCV",
           "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_203/default/table",
           "semesters 2025-S1, 2025-S2, 2026-S1; fetched 2026-10-19 "
           "(see DATA_LOG)", _D, _LIC),
)  # type: Tuple[Source, ...]

ELEC_BANDS = ("IA", "IB", "IC", "ID", "IE", "IF", "IG")
ELEC_LOWER = (0, 20, 500, 2000, 20000, 70000, 150000)
ELEC_LABEL = ("< 20 MWh", "20 MWh to < 500 MWh", "500 MWh to < 2 000 MWh",
              "2 000 MWh to < 20 000 MWh", "20 000 MWh to < 70 000 MWh",
              "70 000 MWh to < 150 000 MWh", ">= 150 000 MWh")
ELEC = {
    "S1": (0.3138, 0.2314, 0.1940, 0.1659, 0.1348, 0.1155, 0.0982),
    "S2": (0.2808, 0.2158, 0.1866, 0.1571, 0.1311, 0.1141, 0.0920),
    "26S1": (0.3172, 0.2318, 0.1902, 0.1600, 0.1332, 0.1148, 0.1014),
}
GAS_BANDS = ("I1", "I2", "I3", "I4", "I5", "I6")
GAS_LOWER = (0, 1000, 10000, 100000, 1000000, 4000000)
GAS_LABEL = ("< 1 000 GJ", "1 000 GJ to < 10 000 GJ",
             "10 000 GJ to < 100 000 GJ", "100 000 GJ to < 1 000 000 GJ",
             "1 000 000 GJ to < 4 000 000 GJ", ">= 4 000 000 GJ")
GAS = {
    "S1": (0.0749, 0.0689, 0.0505, 0.0428, 0.0415, 0.0424),
    "S2": (0.0700, 0.0603, 0.0481, 0.0399, 0.0376, 0.0345),
    "26S1": (0.0677, 0.0548, 0.0439, 0.0389, 0.0389, 0.0392),
}
_SEM = {"S1": ("2025-S1", 2025), "S2": ("2025-S2", 2025),
        "26S1": ("2026-S1", 2026)}


def _lower(prefix, fuel, bands, lowers, labels, unit, src, code, rationale):
    out = []
    for i, (b, lo, lab) in enumerate(zip(bands, lowers, labels)):
        out.append(scalar(
            "Price_%sLower_%s" % (prefix, b), _SEC,
            "%s band %s lower bound" % (fuel, b), lo, unit, "Const_None",
            unit, NA, src, _S, rationale if i == 0 else "",
            "%s band %s: %s (%s annual consumption)" % (code, b, lab, unit)))
    return out


def _prices(prefix, fuel, bands, table, src, first_rat, extra_note):
    out = []
    for key in ("S1", "S2", "26S1"):
        sem, yr = _SEM[key]
        for i, (b, v) in enumerate(zip(bands, table[key])):
            rat = first_rat if (key == "S1" and i == 0) else ""
            note = "X_VAT, EUR/kWh, BE, %s%s" % (sem, extra_note)
            if key == "26S1":
                note += "; 2026-S1 is context only, not used in the base case"
            out.append(scalar(
                "Price_%s%s_%s" % (prefix, key, b), _SEC,
                "%s price band %s, %s" % (fuel, b, sem), v, "EUR/kWh",
                "Const_kWh_per_MWh", "EUR/MWh",
                PriceBasis("EUR", yr, "nominal"), src, _S, rat, note))
    return out


_ELEC_RAT = ("X_VAT is the right tax level for a VAT-registered firm; the "
             "base case uses the 2025 annual average = mean of 2025-S1 and "
             "2025-S2 (D-21), computed by a visible AVERAGE on Baseline")
_GAS_RAT = _ELEC_RAT + ("; per kWh GCV; Baseline converts to NCV with the "
                        "DESNZ GCV/NCV factor pair (D-08)")

INPUTS = tuple(
    _lower("Elec", "Electricity", ELEC_BANDS, ELEC_LOWER, ELEC_LABEL, "MWh",
           "Src_EurostatElecPrice", "nrg_pc_205",
           "Band lower bounds in ascending order feed MATCH(consumption, "
           "bounds, 1) on Baseline so the firm's band follows its derived "
           "consumption (D-21)")
    + _prices("Elec", "Electricity", ELEC_BANDS, ELEC,
              "Src_EurostatElecPrice", _ELEC_RAT, "")
    # block order required: Lower, S1, S2, 26S1 per fuel
    + _lower("Gas", "Gas", GAS_BANDS, GAS_LOWER, GAS_LABEL, "GJ",
             "Src_EurostatGasPrice", "nrg_pc_203",
             "Band lower bounds in ascending order feed MATCH on Baseline "
             "(D-21); bands are in GJ gross calorific value")
    + _prices("Gas", "Gas", GAS_BANDS, GAS, "Src_EurostatGasPrice",
              _GAS_RAT, " (per kWh GCV)")
    + [scalar("Price_RealEscalation", _SEC,
              "Real energy-price escalation per year", 0.0, "per cent",
              "Const_PctToFrac", "%", NA, None, Status.ASSUMPTION,
              "Forward energy prices held flat in real terms (D-22); "
              "energy-price sensitivity is Phase 4")]
)  # type: Tuple[InputRecord, ...]
