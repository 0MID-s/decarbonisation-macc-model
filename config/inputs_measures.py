"""Measures section inputs (02-06): DEA, PVGIS, RVO EML, PBL cross-check, fleet."""
import datetime
from typing import Tuple

from config._helpers import EUR2025_NOM, EUR2025_REAL, NA, PriceBasis, Status, scalar
from config.schema import Source

_D = datetime.date(2026, 10, 19)
_D3 = datetime.date(2026, 10, 21)
_SEC = "Measures"
_S = Status.SOURCED
_A = Status.ASSUMPTION
_HP = "Src_DEAProcessHeat"
_EL = "Src_DEAElectricity"
_EUR2020 = PriceBasis("EUR", 2020, "real")
_EUR2023 = PriceBasis("EUR", 2023, "nominal")
_EUR2026 = PriceBasis("EUR", 2026, "nominal")
_MK = "Const_Mega_per_kilo"
_PK = "Const_PerMW_to_PerkW"

SOURCES = (
    Source(_HP, "Danish Energy Agency (Energistyrelsen)",
           "Technology Data for Industrial Process Heat, datasheet workbook",
           "https://ens.dk/en/analyses-and-statistics/technology-data-industrial-process-heat",
           "datasheet January 2026 (history entry 2026-01-05), catalogue "
           "April 2026; all cost data in 2025 EUR", _D,
           "Published by the Danish Energy Agency; licence line not found "
           "in this file (CC BY 4.0 is stated for the sister electricity "
           "file)"),
    Source(_EL, "Danish Energy Agency (Energistyrelsen)",
           "Technology Data for Generation of Electricity and District "
           "Heating, alldatalong workbook, sheet 22 Rooftop PV "
           "comm.&industrial",
           "https://ens.dk/en/analyses-and-statistics/technology-data-generation-electricity-and-district-heating",
           "version 0019, sheet 22 amended 2026-08-26; priceyear 2020", _D,
           "CC BY 4.0"),
    Source("Src_PVGIS", "European Commission, Joint Research Centre",
           "PVGIS 5.3 PVcalc, lat 51.2 lon 4.4 (Antwerp area), 1 kWp c-Si, "
           "14% loss, south, PVGIS-SARAH3 / ERA5 2005-2023",
           "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
           "PVGIS 5.3, retrieved 2026-10-19", _D,
           "JRC PVGIS; terms of use not read, cited as source"),
    Source("Src_RVOEML", "Rijksdienst voor Ondernemend Nederland (RVO)",
           "Erkende Maatregelenlijst (EML) 2023, berekeningen versie 1.4, "
           "sheet Samengevoegde maatregelen",
           "https://www.rvo.nl/onderwerpen/energiebesparingsplicht/eml",
           "v1.4 (March 2025); next EML update due December 2026", _D,
           "RVO terms not read; figures cited with source"),
    Source("Src_PBLSDE2026", "PBL Netherlands Environmental Assessment Agency",
           "OT-model Eindadvies basisbedragen SDE++ 2026",
           "https://www.pbl.nl/sde/datasets-sde-en-sce",
           "final advice 13 Feb 2026, OT-model 20 Feb 2026 (Colofon: "
           "Eindadvies SDE++ 2026 - 1)", _D,
           "PBL terms not read; figures cited with source"),
    Source("Src_JRCHeat", "European Commission, Joint Research Centre",
           "Heat and cooling demand and market perspective (EUR 25381 EN, "
           "Pardo et al. 2012), Table 3.2.a",
           "https://publications.jrc.ec.europa.eu/repository/handle/JRC70962",
           "EUR 25381 EN (2012); data year 2009", _D3,
           "Terms not stated on the page; figures cited with source"),
    Source("Src_WalloniaMarket", "Service public de Wallonie, Energie",
           "Valeurs de marche applicables en 2026 (regime CPMA)",
           "https://energie.wallonie.be/files/Soutiens%20financiers/"
           "%c3%a9lectricit%c3%a9%20verte/M%c3%a9canismes%20de%20soutiens/"
           "R%c3%a9gime%20CPMA/valeurs-de-marche-2026.pdf",
           "values applicable in 2026; GO value is the 2025 average", _D3,
           "Terms not stated on the page; figures cited with source"),
)  # type: Tuple[Source, ...]


def _hp(id_, desc, val, unit, conv, mu, basis, addr, rat="", status=_S):
    return scalar(id_, _SEC, desc, val, unit, conv, mu, basis, _HP, status,
                  rat, "DEA Industrial Process Heat, %s" % addr)


def _eur25(id_, desc, val, unit, conv, mu, addr, rat=""):
    return _hp(id_, desc, val, unit, conv, mu, EUR2025_REAL, addr, rat)


def _num(id_, desc, val, unit, mu, addr, src=_HP):
    return scalar(id_, _SEC, desc, val, unit, "Const_None", mu, NA, src, _S,
                  "", "DEA, %s" % addr)


_IND = ("Memo (research A3, D-06): the headline nominal investment is the "
        "total, so the indirect investment line is excluded from capex and "
        "shown as a memo line on the Measures sheet")
_RVO_RAT = ("RVO EML measures have payback of 5 years or less; the cost "
            "sheet does not state a price year, so 2023 (the list year) is "
            "assumed (research A2), converted on the Rates sheet")
_PV_RAT = ("PVGIS default 14% system losses already applied, so do not add "
           "a performance ratio")
_FB = "Analyst assumption (D-32 fallback): "
_FBN = ("Fallback: no numeric ICCT anchor located in the two ICCT pages "
        "named in the plan (not retrievable in this run); not sourced data")

INPUTS = (
    _num("Meas_HP_COP_Trad", "Heat pump COP, traditional (1.1)", 5.28, "COP",
         "COP", "sheet 1.1 Traditional heat pump!C8, annual average (range "
         "5.28 to 5.5465); 2025 central"),
    _num("Meas_HP_COP_80C", "Heat pump COP, 80 C / 75 K (1.2)", 3.30, "COP",
         "COP", "sheet '1.2 heat_cool hp 80 C 75 K '!C8 (3.3000000000000003 "
         "stored; range 3.28-3.47)"),
    _num("Meas_HP_COP_HT", "Heat pump COP, high temperature up to 125 C (2.a)",
         2.70, "COP", "COP", "sheet 2.a High temp. hp Up to 125C!C8 (range "
         "2.2-3.95)"),
    _eur25("Meas_HP_Capex_Trad", "Heat pump investment, traditional (1.1)",
           0.95, "M EUR/MW", _MK, "EUR/kW", "sheet 1.1!C19 (range 0.91-0.95)",
           "DEA Index!C2: all cost data in 2025 EUR"),
    _eur25("Meas_HP_Capex_80C", "Heat pump investment, 80 C / 75 K (1.2)",
           0.95, "M EUR/MW", _MK, "EUR/kW", "sheet 1.2!C19",
           "DEA Index!C2: all cost data in 2025 EUR"),
    _eur25("Meas_HP_Capex_HT", "Heat pump investment, high temperature (2.a)",
           1.20, "M EUR/MW", _MK, "EUR/kW",
           "sheet 2.a!C22 (*total; range 0.9-1.5)",
           "DEA Index!C2: all cost data in 2025 EUR"),
    _eur25("Meas_HP_IndirectCapex_Trad",
           "Heat pump indirect investment, traditional (memo)", 0.19,
           "M EUR/MW", _MK, "EUR/kW", "sheet 1.1!C25", _IND),
    _eur25("Meas_HP_IndirectCapex_HT",
           "Heat pump indirect investment, high temperature (memo)", 0.23,
           "M EUR/MW", _MK, "EUR/kW", "sheet 2.a!C29", _IND),
    _eur25("Meas_HP_FixOM_Trad", "Heat pump fixed O&M, traditional (1.1)",
           2127, "EUR/MW/yr", _PK, "EUR/kW/yr", "sheet 1.1!C22"),
    _eur25("Meas_HP_FixOM_HT", "Heat pump fixed O&M, high temperature (2.a)",
           2494, "EUR/MW/yr", _PK, "EUR/kW/yr", "sheet 2.a!C25"),
    _eur25("Meas_HP_VarOM_Trad", "Heat pump variable O&M, traditional (1.1)",
           3.07, "EUR/MWh", "Const_None", "EUR/MWh", "sheet 1.1!C23"),
    _eur25("Meas_HP_VarOM_HT", "Heat pump variable O&M, high temperature (2.a)",
           3.60, "EUR/MWh", "Const_None", "EUR/MWh", "sheet 2.a!C26"),
    _num("Meas_HP_Life_Trad", "Heat pump technical lifetime, traditional (1.1)",
         25, "years", "years", "sheet 1.1!C12 (range 15-40)"),
    _num("Meas_HP_Life_HT", "Heat pump technical lifetime, high temperature (2.a)",
         20, "years", "years", "sheet 2.a!C12 (range 15-30)"),
    _num("Meas_Boiler_Eff", "Gas boiler annual efficiency (counterfactual, 6.1)",
         0.939, "factor", "factor",
         "sheet 6.1 Boiler, gas and oil!C8 (nominal load 0.94 at C7); a "
         "ratio, not a percentage"),
    _eur25("Meas_Boiler_Capex", "Gas boiler investment (counterfactual, 6.1)",
           0.09, "M EUR/MW", _MK, "EUR/kW", "sheet 6.1!C22",
           "DEA Index!C2: all cost data in 2025 EUR"),
    _eur25("Meas_Boiler_FixOM", "Gas boiler fixed O&M (counterfactual, 6.1)",
           2000, "EUR/MW/yr", _PK, "EUR/kW/yr", "sheet 6.1!C25"),
    _eur25("Meas_Boiler_VarOM", "Gas boiler variable O&M (counterfactual, 6.1)",
           1.23, "EUR/MWh", "Const_None", "EUR/MWh", "sheet 6.1!C26"),
    _num("Meas_Boiler_Life", "Gas boiler technical lifetime (6.1)", 25,
         "years", "years", "sheet 6.1!C12"),
    scalar("Meas_PV_CapexDEA", _SEC,
           "Rooftop PV investment, commercial and industrial (DEA, per DC)",
           0.6365236818588025, "M EUR/MWp", _MK, "EUR/kWp", _EUR2020, _EL, _S,
           "EUR 2020 (DEA priceyear); converted to EUR 2025 with euro-area "
           "HICP on the Rates sheet (D-01, D-31). DEA's own Danish index "
           "would give a lower value; shown in the note for transparency "
           "only",
           "DEA el and dh alldatalong, sheet 22 Rooftop PV "
           "comm.&industrial!C18 (*total, per DC); alldata_long!A10993; "
           "priceyear 2020. Indicative HICP uplift x1.2255 gives about EUR "
           "780/kWp (DATA_LOG)"),
    scalar("Meas_PV_FixOMDEA", _SEC,
           "Rooftop PV fixed O&M (DEA, per DC)", 2190, "EUR/MWp/yr", _PK,
           "EUR/kWp/yr", _EUR2020, _EL, _S,
           "EUR 2020 (DEA priceyear); converted on the Rates sheet (D-01)",
           "DEA sheet 22!C38; alldata_long!A11092. Note P (A77): includes "
           "regular inverter replacement annualised over 15 years"),
    _num("Meas_PV_Life", "Rooftop PV technical lifetime", 40, "years", "years",
         "sheet 22!C10 (range 34-50)", _EL),
    _num("Meas_PV_InverterLife", "Rooftop PV inverter lifetime", 15, "years",
         "years", "sheet 22!C47", _EL),
    scalar("Meas_PV_Degradation", _SEC,
           "Rooftop PV average annual degradation of full-load hours", 0.3,
           "per cent", "Const_PctToFrac", "%", NA, _EL, _S, "",
           "DEA sheet 22!C41 (stored 0.003, i.e. 0.3 %/yr)"),
    scalar("Meas_PV_YieldTilt10", _SEC,
           "PV specific yield, Antwerp area, tilt 10 degrees (flat-roof-like)",
           942.09, "kWh/kWp/yr", "Const_None", "kWh/kWp/yr", NA,
           "Src_PVGIS", _S, "",
           "PVGIS 5.3 outputs.totals.fixed.E_y, lat 51.2 lon 4.4, 1 kWp "
           "c-Si, south, SARAH3 2005-2023. " + _PV_RAT),
    scalar("Meas_PV_YieldTilt35", _SEC,
           "PV specific yield, Antwerp area, tilt 35 degrees",
           1038.15, "kWh/kWp/yr", "Const_None", "kWh/kWp/yr", NA,
           "Src_PVGIS", _S, "",
           "PVGIS 5.3 outputs.totals.fixed.E_y, same query. " + _PV_RAT),
    scalar("Meas_LED_HalogenCapex", _SEC,
           "RVO EML: halogen lamp to LED lamp, total investment per lamp "
           "(53 W)", 6.79296, "EUR per unit", "Const_None", "EUR per unit",
           _EUR2023, "Src_RVOEML", _S, _RVO_RAT,
           "Samengevoegde maatregelen, NM row 10, cell K10 (labour 0, "
           "material 5.856, equipment 0, net benefits 2.351)"),
    scalar("Meas_LED_HalogenSaving", _SEC,
           "RVO EML: halogen lamp to LED lamp, electricity saving per lamp",
           118.625, "kWh/yr per unit", "Const_None", "kWh/yr per unit", NA,
           "Src_RVOEML", _S, "", "Samengevoegde maatregelen, cell J10"),
    scalar("Meas_LED_TLCapex", _SEC,
           "RVO EML: double TL light line to LED fixture, total investment "
           "per fixture", 0.00116, "EUR per unit", "Const_None",
           "EUR per unit", _EUR2023, "Src_RVOEML", _S, _RVO_RAT,
           "Samengevoegde maatregelen, NM row 14, cell K14. Flagged "
           "unreliable for CAPEX: material cost 0.001 and total investment "
           "EUR 0.00116 are as published; prefer the halogen-to-LED row"),
    scalar("Meas_LED_TLSaving", _SEC,
           "RVO EML: double TL light line to LED fixture, electricity "
           "saving per fixture", 215.75, "kWh/yr per unit", "Const_None",
           "kWh/yr per unit", NA, "Src_RVOEML", _S, "",
           "Samengevoegde maatregelen, cell J14"),
    scalar("Meas_VSD_Capex", _SEC,
           "RVO EML: frequency controller on cooling compressors, total "
           "investment per piece (40 kW)", 4361.60, "EUR per unit",
           "Const_None", "EUR per unit", _EUR2023, "Src_RVOEML", _S,
           _RVO_RAT,
           "Samengevoegde maatregelen, NM row 2, cell K2 (labour 560, "
           "material 3,000, equipment 200); ZM row 3 has material 4,000 and "
           "total 5,521.60"),
    scalar("Meas_VSD_Saving", _SEC,
           "RVO EML: frequency controller on cooling compressors, "
           "electricity saving per piece (40 kW)", 15360, "kWh/yr per unit",
           "Const_None", "kWh/yr per unit", NA, "Src_RVOEML", _S, "",
           "Samengevoegde maatregelen, cell J2"),
    scalar("Meas_LED_Life", _SEC, "LED lighting lifetime", 15, "years",
           "Const_None", "years", NA, None, _A,
           "Analyst assumption (no lifetime stated in the RVO EML workbook "
           "or Informatiebank pages searched, see DATA_LOG): LED fixtures "
           "are commonly rated for about 50,000 operating hours (a typical "
           "manufacturer rating, not a cited source); at about 3,000 to "
           "4,000 operating hours a year for a one- to two-shift plant this "
           "gives roughly 12 to 17 years; 15 adopted; a plus/minus 20% "
           "lifetime change is a Python-verified note on Notes, not a live "
           "sensitivity",
           "DATA_LOG: lifetime not found in Src_RVOEML"),
    scalar("Meas_VSD_Life", _SEC,
           "Frequency controller (VSD) on compressor lifetime", 15, "years",
           "Const_None", "years", NA, None, _A,
           "Analyst assumption (no lifetime stated in the RVO EML workbook "
           "or Informatiebank pages searched, see DATA_LOG): planning "
           "service life for a variable-speed drive on a compressor, chosen "
           "by the analyst, not taken from a source; a plus/minus 20% "
           "lifetime change is a Python-verified note on Notes, not a live "
           "sensitivity",
           "DATA_LOG: lifetime not found in Src_RVOEML"),
    scalar("Meas_PV_CapexPBL", _SEC,
           "PBL SDE++ 2026 cross-check: rooftop PV >=15 kWp <1 MWp, "
           "building-mounted, investment cost", 531, "EUR/kW", "Const_None",
           "EUR/kW", _EUR2026, "Src_PBLSDE2026", _S,
           "Cross-check only (D-31); the DEA value drives the model. The "
           "OT-model does not state a price level (searched, DATA_LOG), so "
           "the 2026 advice year is used as a label, not as a verified "
           "price year",
           "OT-model sheet 16!C39 (input based, power unit kW as labelled). "
           "Gap to DEA about 32 % below; plausibly different unit scope, "
           "size class and price level"),
    scalar("Meas_HP_CapexPBL", _SEC,
           "PBL SDE++ 2026 cross-check: industrial heat pump, closed "
           "system (8,000 h), investment cost", 1476, "EUR/kW", "Const_None",
           "EUR/kW", _EUR2026, "Src_PBLSDE2026", _S,
           "Cross-check only (D-31); output-based. Price level not stated "
           "in the OT-model (DATA_LOG); 2026 advice year used as a label",
           "OT-model sheet 98!C40. About 29 % above DEA 1.1 (950 plus 190 "
           "indirect EUR/kW)"),
    scalar("Meas_Fleet_EVPremium", _SEC,
           "Fleet: upfront price premium of a battery-electric van over "
           "diesel", 15000, "EUR per vehicle", "Const_None",
           "EUR per vehicle", EUR2025_REAL, None, _A,
           _FB + "round planning figure for the upfront price gap between a "
           "battery-electric and a diesel light van, chosen by the analyst, "
           "not taken from a source; the ICCT studies cover delivery "
           "trucks, not light vans; the EV price premium is a tornado driver "
           "on the Sensitivity sheet (plus/minus Sens_Torn_EVPct)",
           _FBN),
    scalar("Meas_Fleet_EVkWhPerKm", _SEC,
           "Fleet: electric van energy use incl. charging losses", 0.25,
           "kWh/km", "Const_None", "kWh/km", NA, None, _A,
           _FB + "round planning figure for a light electric van's energy "
           "use including charging losses, chosen by the analyst, not taken "
           "from a source", _FBN),
    scalar("Meas_Fleet_Life", _SEC, "Fleet: vehicle holding period", 8,
           "years", "Const_None", "years", NA, None, _A,
           _FB + "assumed holding period of a light commercial van, chosen "
           "by the analyst, not taken from a source", _FBN),
)

_AS = "chosen by the analyst, not taken from a source"
_SUB = ("Analyst assumption (D-15): no grant assumed by default; enter a % "
        "of the initial capex to see NPV after incentives; applies to the "
        "year-0 capex only, not to replacements (typical grant practice)")


_NOT_VARIED = "Analyst assumption; not varied on the Sensitivity sheet"


def _share(id_, desc, val, rat):
    return scalar(id_, _SEC, desc, val, "per cent", "Const_PctToFrac", "%",
                  NA, None, _A, rat, _NOT_VARIED)


def _sub(key, extra=""):
    return scalar("Meas_%s_Subsidy" % key, _SEC,
                  "Subsidy on initial capex, %s" % key, 0, "per cent",
                  "Const_PctToFrac", "%", NA, None, _A, _SUB + extra,
                  "Analyst assumption (D-15, MEAS-10)")


def _ana(id_, desc, val, unit, basis, rat, note=_NOT_VARIED):
    return scalar(id_, _SEC, desc, val, unit, "Const_None", unit, basis, None,
                  _A, rat, note)


INPUTS = INPUTS + (
    scalar("Meas_LED_ZMCapex", _SEC,
           "RVO EML: double TL light line to LED fixture, ZM (independent "
           "moment) total investment per fixture", 252.224, "EUR per unit",
           "Const_None", "EUR per unit", _EUR2023, "Src_RVOEML", _S,
           "D-05: a retrofit uses the full cost (ZM); the NM rows are "
           "incremental to a replacement that happens anyway. " + _RVO_RAT,
           "Samengevoegde maatregelen, ZM row 15, cell K15"),
    scalar("Meas_LED_ZMSaving", _SEC,
           "RVO EML: double TL light line to LED fixture, ZM electricity "
           "saving per fixture", 215.75, "kWh/yr per unit", "Const_None",
           "kWh/yr per unit", NA, "Src_RVOEML", _S, "",
           "Samengevoegde maatregelen, ZM row 15, cell J15"),
    scalar("Meas_VSD_ZMCapex", _SEC,
           "RVO EML: frequency controller on cooling compressors, ZM "
           "(independent moment) total investment per piece (40 kW)",
           5521.60, "EUR per unit", "Const_None", "EUR per unit", _EUR2023,
           "Src_RVOEML", _S,
           "D-05: full cost for a retrofit. The RVO row is a "
           "refrigeration-compressor VSD used as a cost proxy for 'VSD on "
           "compressor motors'. " + _RVO_RAT,
           "Samengevoegde maatregelen, ZM row 3, cell K3"),
    _eur25("Meas_Boiler_IndirectCapex",
           "Gas boiler indirect investment (memo)", 0.23, "M EUR/MW", _MK,
           "EUR/kW", "sheet 6.1!C28 (DATA_LOG Phase 3: rows 22-24 total, "
           "indirect at row 28)",
           "Kept out of capex (D-06, A3 resolved: the headline nominal "
           "investment is the total); identical to the heat-pump value so "
           "it cancels in the incremental capex"),
    scalar("Meas_HP_FullLoadHours", _SEC,
           "Industrial heat pump full-load hours", 8000, "h/yr",
           "Const_None", "h/yr", NA, "Src_PBLSDE2026", _S,
           "Sourced base case (orchestrator resolution 3): DEA states no "
           "hours; a subsidy reference case, not a DEA value; not varied "
           "on the Sensitivity sheet",
           "OT-model sheet 98, cell C29 (industrial heat pump, closed "
           "system, 8,000 h)"),
    scalar("Meas_HP_HeatHighPJ", _SEC,
           "JRC Belgium chemical useful heat demand, high temperature",
           25.3, "PJ", "Const_None", "PJ", NA, "Src_JRCHeat", _S, "",
           "Table 3.2.a, Belgium, chemical, useful heat demand 2009 (high)"),
    scalar("Meas_HP_HeatMedPJ", _SEC,
           "JRC Belgium chemical useful heat demand, medium temperature "
           "(100-400 C)", 12.5, "PJ", "Const_None", "PJ", NA, "Src_JRCHeat",
           _S, "", "Table 3.2.a, Belgium, chemical, useful heat demand 2009 "
           "(medium 100-400 C)"),
    scalar("Meas_HP_HeatLowPJ", _SEC,
           "JRC Belgium chemical useful heat demand, low temperature "
           "(below 100 C)", 21.0, "PJ", "Const_None", "PJ", NA,
           "Src_JRCHeat", _S,
           "The share below 100 C is computed on the Measures sheet and "
           "used as a conservative proxy for gas heat at or below 125 C "
           "(D-10; 100-125 C not separable; all fuels, 2009)",
           "Table 3.2.a, Belgium, chemical, useful heat demand 2009 (low, "
           "below 100 C)"),
    scalar("Meas_PV_RoofArea", _SEC,
           "Rooftop PV space requirement (memo for implied roof area)",
           4.479, "1000 m2/MWp", "Const_None", "m2/kWp", NA, _EL, _S,
           "Used only for the implied-roof-area memo row (D-09)",
           "sheet 22 Rooftop PV comm.&industrial!C30; note B2: 110 kWp is "
           "about 490 m2 flat"),
    scalar("Meas_RC_GOPrice", _SEC,
           "Guarantee of Origin value (Wallonia, 2025 average purchase "
           "price)", 2.05, "EUR/GO", "Const_MWh_per_GO", "EUR/MWh",
           EUR2025_NOM, "Src_WalloniaMarket", _S,
           "Producer-side regulatory reference value, likely below a retail "
           "green premium, so it flatters the contract; a tornado driver on "
           "the Sensitivity sheet (plus/minus Sens_Torn_GOPct, D-12)",
           "Page 1: \"Valeur d'une GO: 2,05 EUR/GO\" (average GO "
           "purchase price from producers, 1 Jan to 31 Dec 2025)"),
    _share("Meas_LED_LightingShare",
           "Lighting share of industrial electricity", 6,
           "Anchor: US EIA MECS 2018 (about 6% of US manufacturing "
           "electricity, eia.gov FAQ 99) as a non-EU proxy; no EU, JRC or "
           "RVO figure found (D-07); value " + _AS),
    _share("Meas_LED_Coverage",
           "Share of the lighting load still on legacy (TL/halogen) "
           "fittings", 50,
           "Avoids counting savings on fittings already LED (Pitfall 2); "
           "value " + _AS),
    _share("Meas_LED_SavingRate",
           "Electricity saving of LED vs the legacy fitting", 50,
           "Consistent in order of magnitude with the RVO TL-to-LED row; "
           "value " + _AS),
    _share("Meas_VSD_MotorShare",
           "Compressed-air share of industrial electricity", 10,
           "Analyst assumption (D-08): no official EU compressed-air share "
           "was verified. Order-of-magnitude anchor only: a Fraunhofer ISI "
           "estimate of about 10% of EU industrial electricity, read from a "
           "search summary and logged in docs/DATA_LOG.md at MEDIUM "
           "confidence, not a verified source; value " + _AS),
    _share("Meas_VSD_Coverage",
           "Share of compressed-air load suited to a VSD retrofit", 50,
           "Avoids counting savings on already-controlled compressors "
           "(Pitfall 2); value " + _AS),
    _share("Meas_VSD_SavingRate",
           "Electricity saving of a VSD on a compressor", 15,
           "Order of magnitude of the RVO row saving; value " + _AS),
    _ana("Meas_PV_Size", "Rooftop PV system size", 1000, "kWp", NA,
         "Typical flat roof of about 5,000-7,000 m2 on a medium plant; the "
         "DEA ratio (Meas_PV_RoofArea) implies about 4,480 m2 "
         "flush-mounted (D-09); " + _AS),
    _ana("Meas_Fleet_ChargerCapex", "Fleet: depot AC charger per van, "
         "installed", 2000, "EUR per vehicle", EUR2025_REAL,
         "Depot AC charger installed per van; no van TCO source found "
         "(research V9); " + _AS,
         "Analyst assumption; varied with the other capex in the Capex "
         "tornado driver on the Sensitivity sheet (plus/minus "
         "Sens_Torn_CapexPct)"),
    _ana("Meas_Fleet_MaintSaving", "Fleet: maintenance saving of an "
         "electric vs a diesel van", 0.03, "EUR/km", EUR2025_REAL,
         "Maintenance saving per km; no source found (V9); " + _AS),
    _ana("Meas_Fleet_DieselVanPrice", "Fleet: purchase price of the "
         "counterfactual new diesel light van", 35000, "EUR per vehicle",
         EUR2025_REAL,
         "Used ONLY for the D-05 full-capex memo NPV of the fleet block "
         "(the decision NPV uses the incremental premium); round planning "
         "figure " + _AS),
    _ana("Meas_RC_Term", "Renewable contract term", 10, "years", NA,
         "Contract renewed at the same real premium to 2055; disclosure "
         "only, it does not change the cash flows (D-12); " + _AS),
    _sub("LED"), _sub("VSD"), _sub("HP"), _sub("Fleet"), _sub("PV"),
    _sub("RC", "; the contract has no capex, so its subsidy has no effect"),
)
