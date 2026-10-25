"""Phase 4 inputs (04-01): carbon exposure and sensitivity constants.

Lint allows only the literals 0 and 1 in formulas, so every year, step, range
and rate used on the Exposure and Sensitivity sheets is a named row here.
Literature (Fabra and Reguant 2014, Sijm et al. 2006, High-Level Commission on
Carbon Prices 2017, CDP 2021) is cited as text inside assumption rationales;
no allowlist change (04-01 decision).
"""
import datetime
from typing import Tuple

from config._helpers import EUR2025_REAL, NA, Status, scalar
from config.schema import Source

_SEC_EXPO = "Carbon exposure (Phase 4)"
_SEC_SENS = "Sensitivity (Phase 4)"
_A = Status.ASSUMPTION
_S = Status.SOURCED

SOURCES = (
    Source("Src_CBAM", "European Commission, DG Taxation and Customs Union",
           "Carbon Border Adjustment Mechanism: Regulation (EU) 2023/956, "
           "Annex I goods and current scope",
           "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en",
           "page as of 2026-10-25 (definitive regime from 2026-01-01; "
           "Regulation (EU) 2025/2083 simplification)",
           datetime.date(2026, 10, 25),
           "Commission website reuse policy (Decision 2011/833/EU); text "
           "facts only"),
)  # type: Tuple[Source, ...]


def _a(id_, sec, desc, val, unit, rationale, basis=NA, note=""):
    return scalar(id_, sec, desc, val, unit, "Const_None", unit, basis, None,
                  _A, rationale, note)


def _sens(id_, desc, val, unit, rationale, note=""):
    return _a(id_, _SEC_SENS, desc, val, unit, rationale, NA, note)


_HURDLE = ("Real hurdle-rate stress test; corporate hurdle rates of 8-10% are "
           "typical and above the 5.70% WACC (D-22, band D-21)")

INPUTS = (
    scalar("Pass_CCGT_Eff", _SEC_EXPO,
           "Gas CCGT electrical efficiency, net annual average, 2020 "
           "(price-setting plant)", 0.56, "fraction", "Const_None",
           "fraction", NA, "Src_DEAElectricity", _S, "",
           "DEA Technology Data for Generation of Electricity and District "
           "Heating, version 0019, sheet '05 Gas turb. CC, steam extract.', "
           "row 'Electrical efficiency (net, annual average)', 2020 column "
           "(alldata_long row 1203); range 0.52-0.58 (D-09). Basis assumed LHV"),
    _a("Pass_PTR", _SEC_EXPO, "Carbon cost pass-through rate to electricity "
       "price", 1.0, "fraction",
       "Upper-bound pass-through of the marginal plant's carbon cost in a "
       "competitive wholesale market (Fabra and Reguant, AER 2014: above 80%, "
       "about 100% at peak; Sijm, Neuhoff and Chen, Climate Policy 2006: "
       "60-100%). Tested 0.6 to 1.0 in the tornado (D-10)"),
    _a("Carbon_EUA_AnchorYear", _SEC_EXPO, "ETS1 anchor year of the observed "
       "EUA average", 2025, "year",
       "Year of the observed EUA average used as the ETS1 anchor (D-02)"),
    _a("Carbon_ETS1_ConvYear", _SEC_EXPO, "Year by which the ETS1 market "
       "path converges to the scenario", 2030, "year",
       "First NGFS five-year point after the anchor; market-anchored path "
       "converges to the scenario by this year (D-01, D-02); change it to "
       "test a slower convergence"),
    _a("Carbon_ETS2_ConvYear", _SEC_EXPO, "Year by which the ETS2 path "
       "converges to the scenario", 2030, "year",
       "First NGFS five-year point after the ETS2 start; same convergence "
       "logic as ETS1 because no official Commission ETS2 price projection "
       "was found (D-03); change it to test a slower convergence"),
    _a("Carbon_ICP_Level", _SEC_EXPO, "Internal carbon price (decision lens)",
       100, "EUR/tCO2e",
       "Management policy assumption at the upper end of benchmarks: "
       "High-Level Commission on Carbon Prices (2017) USD 50-100 by 2030; "
       "CDP 2021 median about USD 25. A non-cash decision lens, never added "
       "to cash costs (D-12, D-13)", EUR2025_REAL),
    _a("Carbon_DirectETS_FreeAlloc", _SEC_EXPO, "Free allocation share if "
       "the firm were inside ETS1", 0, "fraction",
       "Conservative: no free allocation if the firm were inside ETS1; only "
       "used when Sel_DirectETS = On (D-14)"),
    scalar("Carbon_CBAM_InScope", _SEC_EXPO,
           "Maison Veritas products in CBAM Annex I scope (1) or not (0)", 0,
           "flag (1/0)", "Const_None", "flag (1/0)", NA, "Src_CBAM", _S, "",
           "C20 household and chemical products are not Annex I goods; "
           "indirect exposure via imported hydrogen/fertiliser inputs only "
           "(D-15)"),
    _a("Expo_LastYear", _SEC_EXPO, "Last year of the exposure tables", 2035,
       "year", "Requirement window for exposure tables (EXPO-01, D-04); NPV "
       "outputs still run to 2055"),
    _sens("Sens_GridStep", "Sensitivity grid step", 0.2, "fraction",
          "Step of the price-change axis in the two-way grids (D-21)"),
    _sens("Sens_RateStep", "Discount-rate grid step", 0.01, "fraction",
          "Step of the discount-rate axis in the sensitivity grids (D-21)"),
    _sens("Sens_Hurdle_1", "Hurdle rate stress test 1", 0.06, "fraction",
          _HURDLE),
    _sens("Sens_Hurdle_2", "Hurdle rate stress test 2", 0.08, "fraction",
          _HURDLE),
    _sens("Sens_Hurdle_3", "Hurdle rate stress test 3", 0.10, "fraction",
          _HURDLE),
    _sens("Sens_Torn_RateDelta", "Tornado: discount rate change (+/-)", 0.02,
          "fraction", "Tornado range, band D-21: plus or minus 2 percentage "
          "points around the real discount rate"),
    _sens("Sens_Torn_ElecPct", "Tornado: electricity price change (+/-)",
          0.2, "fraction", "Tornado range, band D-21: plus or minus 20%"),
    _sens("Sens_Torn_GasPct", "Tornado: gas price change (+/-)", 0.2,
          "fraction", "Tornado range, band D-21: plus or minus 20%"),
    _sens("Sens_Torn_CapexPct", "Tornado: capex change (+/-)", 0.2,
          "fraction", "Tornado range, band D-21: plus or minus 20%"),
    _sens("Sens_Torn_GOPct", "Tornado: guarantee-of-origin price change "
          "(+/-)", 0.5, "fraction",
          "Tornado range, band D-21: plus or minus 50%; the GO price is a "
          "thin, volatile market value"),
    _sens("Sens_Torn_EVPct", "Tornado: EV premium change (+/-)", 0.3,
          "fraction", "Tornado range, band D-21: plus or minus 30%; the EV "
          "premium is itself an analyst assumption"),
    _sens("Sens_Torn_PTRLow", "Tornado: low pass-through rate", 0.6,
          "fraction", "Lower end of the pass-through literature range "
          "(Sijm, Neuhoff and Chen 2006: 60-100%); upper end is Pass_PTR"),
    _sens("Sens_Torn_MEFPct", "Tornado: marginal emission factor change "
          "(+/-)", 0.15, "fraction", "Tornado range, band D-21: plus or "
          "minus 15%, covers the GCV-versus-LHV basis gap (MEF 0.326 vs "
          "0.361)"),
    _sens("Sens_ETS2_StartDelay", "Further ETS2 delay tested", 1, "years",
          "One further year of ETS2 delay (open political risk, EPRS)"),
    _sens("Carbon_NGFS_AltRouteFactor", "Alternative NGFS conversion route "
          "factor", 1.31, "factor",
          "Indicative analyst estimate of the US-CPI conversion route "
          "(Phase 2 D-41 flag), not a sourced input; tested against the "
          "Eurostat route"),
    _sens("Sens_Note_LifePct", "Note-only sensitivity: lifetime change",
          0.2, "fraction", "Used only for the Python-verified note on Notes "
          "(not live, D-21)"),
    _sens("Sens_Note_HPShareDelta", "Note-only sensitivity: heat-pump share "
          "change", 0.1, "fraction", "Used only for the Python-verified "
          "note on Notes (not live, D-21)"),
)  # type: Tuple[object, ...]
