"""Emission factors section inputs (02-06): EEA grid, AIB residual mix, DESNZ fuels."""
import datetime
from typing import Tuple

from config._helpers import NA, Status, scalar
from config.schema import Source

_D = datetime.date(2026, 10, 19)
_SEC = "Emission factors"
_S = Status.SOURCED
_A = Status.ASSUMPTION

SOURCES = (
    Source("Src_EEAGridIntensity", "European Environment Agency",
           "Greenhouse gas emission intensity of electricity generation, "
           "country data (map/chart co2-emission-intensity-15, CSV download)",
           "https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1",
           "CSV edition with data to 2022; current indicator covers "
           "1990-2024 but country values for 2023-2024 are chart-only",
           _D, "CC BY 4.0, EEA acknowledged in every copy"),
    Source("Src_AIBResidualMix", "Association of Issuing Bodies (AIB)",
           "European Residual Mixes 2025, calculation results workbook, "
           "sheet CO2",
           "https://www.aib-net.org/facts/european-residual-mix/2025",
           "Version 1.0, calculation dated 2026-05-26", _D,
           "AIB material copyrighted, all rights reserved, no reuse terms "
           "stated; a single figure is cited with source, the dataset is "
           "not republished"),
    Source("Src_DESNZ2026",
           "UK Department for Energy Security and Net Zero (DESNZ) / DEFRA",
           "Greenhouse gas reporting: conversion factors 2026, flat file, "
           "sheet Factors by Category, column GHG Conversion Factor 2026",
           "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026",
           "published 11 Jun 2026, flat file v1.2 republished July 2026",
           _D, "Open Government Licence v3.0"),
)  # type: Tuple[Source, ...]

_KWH_ID = ("kgCO2e per kWh equals tCO2e per MWh numerically, so no "
           "conversion is applied")


def _desnz(id_, desc, val, row_id, addr, rationale):
    return scalar(id_, _SEC, desc, val, "kgCO2e/kWh", "Const_None",
                  "tCO2e/MWh", NA, "Src_DESNZ2026", _S, rationale,
                  "DESNZ 2026 flat file, Factors by Category, row ID %s, "
                  "cell %s; %s" % (row_id, addr, _KWH_ID))


INPUTS = (
    scalar("EF_GridLB", _SEC,
           "Belgium grid emission intensity, location-based (EEA, 2022)",
           154, "gCO2e/kWh", "Const_g_per_kWh_to_t_per_MWh", "tCO2e/MWh", NA,
           "Src_EEAGridIntensity", _S, "",
           "Belgium 2022, gCO2e per kWh of gross electricity generation "
           "(public electricity and heat apportioned); the latest "
           "machine-readable year (D-38). Belgian series is volatile: 2015 "
           "219, 2016 161, 2017 169, 2018 197, 2019 170, 2020 166, 2021 "
           "138, 2022 154 (DATA_LOG, CSV row 366)"),
    scalar("EF_GridLB_Change", _SEC,
           "Annual change in location-based grid intensity",
           0.0, "per cent", "Const_PctToFrac", "%", NA, None, _A,
           "Analyst assumption (D-23 fallback, D-38): no sourced Belgian "
           "projection of grid intensity on an allowlisted host; held flat. "
           "A declining path matters because of the Belgian nuclear "
           "extension; option to source the Federal Planning Bureau path is "
           "recorded in Notes",
           "Accepted deviation from DATA-05 (declining LB path), user-locked "
           "in D-38"),
    scalar("EF_ResidualMB", _SEC,
           "Belgium residual mix, market-based (AIB 2025)",
           171.01, "gCO2/kWh", "Const_g_per_kWh_to_t_per_MWh", "tCO2/MWh", NA,
           "Src_AIBResidualMix", _S, "",
           "Belgium, sheet CO2, residual mix column, cell CO2!A4 (column C); "
           "unit is gCO2 (CO2 only), unlike the EEA CO2e factor (Pitfall 5)"),
    scalar("EF_ResidualMB_Change", _SEC,
           "Annual change in market-based residual mix",
           0.0, "per cent", "Const_PctToFrac", "%", NA, None, _A,
           "Analyst assumption (D-24): AIB publishes no projection; held "
           "flat"),
    _desnz("EF_Gas_NCV", "Natural gas combustion factor, net calorific value",
           0.20199, "1_100_1004_7_1", "A79",
           "DESNZ net CV factor; the model energy unit is MWh NCV to match "
           "Eurostat balances (D-08). All fuel factors are constant over "
           "time (D-25)"),
    _desnz("EF_Gas_GCV", "Natural gas combustion factor, gross calorific value",
           0.18231, "1_100_1004_6_1", "A83",
           "Stored so Baseline computes the GCV/NCV ratio (EF_Gas_NCV / "
           "EF_Gas_GCV) as a visible formula to convert the Eurostat gas "
           "price from per kWh GCV to per kWh NCV and the consumption to GJ "
           "GCV for the band (D-08)"),
    _desnz("EF_LPG_NCV", "LPG combustion factor, net calorific value",
           0.23032, "1_100_1003_7_1", "A63", "DESNZ net CV factor (D-08)"),
    _desnz("EF_Naphtha_NCV", "Naphtha combustion factor, net calorific value",
           0.24891, "1_101_1016_7_1", "A271", "DESNZ net CV factor (D-08)"),
    _desnz("EF_GasOil_NCV", "Gas oil combustion factor, net calorific value",
           0.27288, "1_101_1014_7_1", "A239",
           "Also used for the remainder carrier, whose dominant fuel is gas "
           "oil (D-09)"),
    _desnz("EF_Diesel_NCV",
           "Diesel (average biofuel blend) factor, net calorific value",
           0.26071, "1_101_1011_7_1", "A191",
           "Average biofuel blend; used for the fleet block (energy MWh = "
           "litres x kgCO2e/l / kgCO2e/kWh)"),
    scalar("EF_Diesel_l", _SEC, "Diesel (average biofuel blend) factor per litre",
           2.58354, "kgCO2e/l", "Const_None", "kgCO2e/l", NA,
           "Src_DESNZ2026", _S,
           "Average biofuel blend; used for the fleet block (litres, energy "
           "MWh = litres x kgCO2e/l / kgCO2e/kWh)",
           "DESNZ 2026 flat file, Factors by Category, row ID "
           "1_101_1011_8_1, cell A187"),
    scalar("EF_HeatProxy", _SEC,
           "Purchased heat and steam factor (UK proxy for Belgium)",
           0.17529, "kgCO2e/kWh", "Const_None", "tCO2e/MWh", NA,
           "Src_DESNZ2026", _A,
           "Analyst assumption (research A4): no Belgian derived-heat "
           "factor found on an allowlisted host; UK DESNZ heat and steam "
           "factor used as a proxy; same factor under both LB and MB",
           "DESNZ 2026 flat file, row ID 10_401_4003_5_1, cell A3454 (UK "
           "average, Scope 2); " + _KWH_ID),
)
