"""Baseline section inputs (02-05): Eurostat BE NACE C20 statistics and fleet."""
import datetime
from typing import Tuple

from config._helpers import NA, PriceBasis, Status, scalar
from config.schema import InputRecord, Source

_D = datetime.date(2026, 10, 19)
_LIC = ("Eurostat: free re-use for commercial and non-commercial purposes, "
        "source acknowledged")
_NOM24 = PriceBasis("EUR", 2024, "nominal")
_S = Status.SOURCED
_SEC = "Baseline"
_VA_RAT = ("Used only inside ratios (firm / sector), so the price year "
           "cancels and no deflation is needed (D-01 note)")

SOURCES = (
    Source("Src_EurostatSBS", "Eurostat",
           "Structural business statistics by size class of employment "
           "(sbs_sc_ovw)",
           "https://ec.europa.eu/eurostat/databrowser/view/sbs_sc_ovw/default/table",
           "data updated 2026-09-30 (per DATA_LOG); reference year 2024",
           _D, _LIC),
    Source("Src_EurostatEnergyBalance", "Eurostat",
           "Complete energy balances (nrg_bal_c), final consumption "
           "industry chemical and petrochemical, energy use (FC_IND_CPC_E)",
           "https://ec.europa.eu/eurostat/databrowser/view/nrg_bal_c/default/table",
           "reference year 2024; fetched 2026-10-19 (see DATA_LOG)",
           _D, _LIC),
    Source("Src_EurostatAirAccounts", "Eurostat",
           "Air emissions accounts by NACE Rev. 2 activity (env_ac_ainah_r2)",
           "https://ec.europa.eu/eurostat/databrowser/view/env_ac_ainah_r2/default/table",
           "reference year 2024; fetched 2026-10-19 (see DATA_LOG)",
           _D, _LIC),
    Source("Src_Reg1099", "European Parliament and Council (EUR-Lex)",
           "Regulation (EC) No 1099/2008 on energy statistics, Annex A item "
           "2.6.1.6 (chemical and petrochemical = NACE Rev. 2 Divisions 20 "
           "and 21)",
           "https://eur-lex.europa.eu/eli/reg/2008/1099/oj/eng",
           "as amended (incl. Regulation (EU) 2019/2146)",
           _D, "EU legal text; reuse permitted with source acknowledged"),
    Source("Src_EEAVans", "European Environment Agency",
           "News: average CO2 emissions from new cars and vans significantly "
           "decreased in 2025 (provisional data)",
           "https://www.eea.europa.eu/en/newsroom/news/average-co2-emissions-from-new-cars-and-vans-significantly-decreased-in-2025",
           "published 25 June 2026, provisional", _D,
           "CC BY 4.0, EEA acknowledged"),
)  # type: Tuple[Source, ...]


def _nrg(id_, desc, val, siec, rationale=""):
    return scalar(id_, _SEC, desc, val, "TJ", "Const_TJ_to_MWh", "MWh", NA,
                  "Src_EurostatEnergyBalance", _S, rationale,
                  "nrg_bal_c FC_IND_CPC_E, BE, 2024, siec %s, unit TJ "
                  "(net calorific value)" % siec)


def _air(id_, desc, val, nace):
    return scalar(id_, _SEC, desc, val, "tCO2e", "Const_None", "tCO2e", NA,
                  "Src_EurostatAirAccounts", _S, "",
                  "env_ac_ainah_r2 airpol GHG, NACE %s, BE, 2024, unit "
                  "tonnes CO2e; 2024 value flagged i (imputed by Eurostat); "
                  "2023 is the latest non-imputed year" % nace)


INPUTS = (
    scalar("Base_RefYear", _SEC, "Common reference year for the three Eurostat datasets",
           2024, "year", "Const_None", "year", NA, "Src_EurostatSBS", _S, "",
           "Common reference year for sbs_sc_ovw, nrg_bal_c and "
           "env_ac_ainah_r2 (D-04): 2024 is the latest year all three "
           "publish for BE"),
    scalar("Base_SBS_C20M_Ent", _SEC, "BE NACE C20, size class 50-249: enterprises",
           110, "enterprises", "Const_None", "enterprises", NA,
           "Src_EurostatSBS", _S, "",
           "sbs_sc_ovw ENT_NR, NACE C20, size 50-249, BE, 2024"),
    scalar("Base_SBS_C20M_Persons", _SEC, "BE NACE C20, size class 50-249: persons employed",
           13960, "persons", "Const_None", "persons", NA, "Src_EurostatSBS",
           _S, "", "sbs_sc_ovw EMP_NR, NACE C20, size 50-249, BE, 2024"),
    scalar("Base_SBS_C20M_VA", _SEC, "BE NACE C20, size class 50-249: value added",
           2536.48, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, _VA_RAT,
           "sbs_sc_ovw AV_MEUR, NACE C20, size 50-249, BE, 2024. Value added "
           "per enterprise (EUR m) 2021/2022/2023/2024: 21.06 / 22.75 / "
           "21.41 / 23.06, stable"),
    scalar("Base_SBS_C20M_Turnover", _SEC, "BE NACE C20, size class 50-249: net turnover",
           12396.76, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, "",
           "sbs_sc_ovw NETTUR_MEUR, NACE C20, size 50-249, BE, 2024"),
    scalar("Base_SBS_C20_VA", _SEC, "BE NACE C20, all sizes: value added",
           8911.42, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, _VA_RAT,
           "sbs_sc_ovw AV_MEUR, NACE C20, TOTAL, BE, 2024"),
    scalar("Base_SBS_C21_VA", _SEC, "BE NACE C21, all sizes: value added",
           16919.86, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, _VA_RAT,
           "sbs_sc_ovw AV_MEUR, NACE C21, TOTAL, BE, 2024"),
    scalar("Base_SBS_C20_Turnover", _SEC, "BE NACE C20, all sizes: net turnover",
           42576.38, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, "",
           "sbs_sc_ovw NETTUR_MEUR, NACE C20, TOTAL, BE, 2024"),
    scalar("Base_SBS_C21_Turnover", _SEC, "BE NACE C21, all sizes: net turnover",
           48554.13, "EUR m", "Const_None", "EUR m", _NOM24,
           "Src_EurostatSBS", _S, "",
           "sbs_sc_ovw NETTUR_MEUR, NACE C21, TOTAL, BE, 2024"),
    scalar("Base_NRG_IncludesC21", _SEC,
           "Energy balance sector includes NACE C21 (1 = yes)",
           1, "flag (1/0)", "Const_None", "flag (1/0)", NA, "Src_Reg1099",
           Status.ASSUMPTION,
           "Unverified transcription: transcribed from 02-RESEARCH (read via "
           "legislation.gov.uk); to be verified against the legal text. "
           "The energy balance sector chemical and petrochemical covers NACE "
           "20 and 21, so value added and air emissions for the scaling "
           "denominator must include C21 (D-05, D-39). Set to 0 only to see "
           "the C20-only memo; that overstates firm energy about 2.9 times.",
           "Regulation (EC) 1099/2008 Annex A item 2.6.1.6: chemical and "
           "petrochemical = NACE Rev. 2 Divisions 20 and 21. Transcribed "
           "from the 02-RESEARCH record (read there via legislation.gov.uk); "
           "EUR-Lex re-read 2026-10-20 returned no text (NOT READ) and the "
           "Eurostat nrg_bal metadata does not state the NACE coverage; see "
           "docs/DATA_LOG.md, Legal texts (WR-02 re-read)"),
    _nrg("Base_NRG_Total", "BE chemical and petrochemical final energy use, total",
         162119.849, "TOTAL",
         "Final energy consumption, energy use only (FC_IND_CPC_E); "
         "non-energy (feedstock) use is excluded because it is not combusted "
         "(D-05). Eurostat balances are on a net calorific value basis for "
         "all carriers (D-08). Materiality cut-off (D-09, Claude's "
         "discretion): carriers above 1% of sector final energy are separate "
         "lines (gas, electricity, naphtha, LPG, derived heat); the rest is "
         "one remainder line computed on Baseline as total minus those five"),
    _nrg("Base_NRG_Gas", "BE chemical and petrochemical: natural gas",
         62515.885, "G3000"),
    _nrg("Base_NRG_Elec", "BE chemical and petrochemical: electricity",
         48458.52, "E7000"),
    _nrg("Base_NRG_Heat", "BE chemical and petrochemical: derived heat",
         8030.8, "H8000"),
    _nrg("Base_NRG_LPG", "BE chemical and petrochemical: LPG", 11356.73,
         "O4630"),
    _nrg("Base_NRG_Naphtha", "BE chemical and petrochemical: naphtha",
         29361.1, "O4640",
         "Sector-specific petrochemical fuel kept as a separate flagged "
         "line; no unsourced size adjustment (D-06, Claude's discretion)"),
    _nrg("Base_NRG_GasOil", "BE chemical and petrochemical: gas oil / diesel (memo)",
         1143.8, "O4671XR5220B",
         "Memo: dominant fuel of the remainder (gas oil, fuel oil, coke, "
         "renewables, non-renewable waste), so the remainder uses the DESNZ "
         "gas oil factor (D-09)"),
    _air("Base_Air_C20_GHG", "BE NACE C20 greenhouse gas emissions",
         9173823.08, "C20"),
    _air("Base_Air_C21_GHG", "BE NACE C21 greenhouse gas emissions",
         238898.76, "C21"),
    scalar("Base_Fleet_Vehicles", _SEC, "Company light commercial vehicles",
           10, "vehicles", "Const_None", "vehicles", NA, None,
           Status.ASSUMPTION,
           "Analyst assumption (D-10): illustrative light commercial fleet "
           "for a medium manufacturer; fleet fuel is booked under transport "
           "in the energy balance, so it is not in the Eurostat lines"),
    scalar("Base_Fleet_KmPerVehicle", _SEC, "Annual distance per vehicle",
           25000, "km/yr", "Const_None", "km/yr", NA, None,
           Status.ASSUMPTION,
           "Analyst assumption (D-10): typical annual distance for a "
           "delivery van; fleet is kept apart from the Eurostat lines"),
    scalar("Base_Fleet_gCO2PerKm", _SEC, "Tailpipe emissions of a new van (diesel-heavy anchor)",
           184.9, "gCO2/km", "Const_None", "gCO2/km", NA, "Src_EEAVans", _S,
           "",
           "Transcribed: EEA 2024 new-van average (WLTP); 2025 provisional "
           "172.1 includes about 10% battery-electric vans, so 2024 is the "
           "diesel-heavy anchor; WLTP understates real-world use"),
)  # type: Tuple[InputRecord, ...]
