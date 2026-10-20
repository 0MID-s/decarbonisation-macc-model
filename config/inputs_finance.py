"""Finance section inputs (02-07): HICP, 2010 USD per EUR rate, inflation target.

Damodaran cost of capital was added in 02-12. Values are transcribed from
docs/DATA_LOG.md (Eurostat files) and 02-RESEARCH 3.9 (ECB, Eurostat flash).
"""
import datetime
from typing import Tuple

from config._helpers import NA, EUR2025_NOM, Status, scalar  # noqa: F401
from config.schema import PriceBasis, Source

_D = datetime.date(2026, 10, 19)
_SEC = "Finance"
_S = Status.SOURCED
_EUROSTAT_LIC = ("Eurostat reuse policy (free reuse with source "
                 "acknowledged; exact wording not verified)")

SOURCES = (
    Source("Src_EurostatHICP", "Eurostat",
           "HICP annual data, average index (prc_hicp_aind), CP00 all-items, "
           "euro area, 2015=100",
           "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_aind/default/table",
           "annual averages 2010-2025, fetched 2026-10-19 "
           "(sha256 in docs/DATA_LOG.md)", _D, _EUROSTAT_LIC),
    Source("Src_ECBTarget", "European Central Bank",
           "Monetary policy strategy: price stability, 2% inflation over the "
           "medium term",
           "https://www.ecb.europa.eu/mopo/strategy/pricestab/html/index.en.html",
           "strategy review concluded July 2021", _D,
           "ECB website; reuse with source acknowledged (wording not "
           "verified)"),
    Source("Src_EurostatFlash", "Eurostat",
           "Euro indicators release: euro area annual inflation, "
           "September 2026",
           "https://ec.europa.eu/eurostat/web/products-euro-indicators/w/2-16102026-ap",
           "euro indicator release 2-16102026-AP (September 2026)", _D,
           _EUROSTAT_LIC),
    Source("Src_EurostatFX", "Eurostat",
           "Euro/ECU exchange rates, annual data (ert_bil_eur_a), US dollar "
           "per euro, annual average",
           "https://ec.europa.eu/eurostat/databrowser/view/ert_bil_eur_a/default/table",
           "annual averages, fetched 2026-10-19 (sha256 in "
           "docs/DATA_LOG.md)", _D, _EUROSTAT_LIC),
    Source("Src_Damodaran",
           "Aswath Damodaran, NYU Stern School of Business (Damodaran "
           "Online)",
           "Cost of Capital by Industry Sector, Europe (waccEurope.xls), "
           "sheet Industry Averages, column Cost of Capital (Euros)",
           "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccEurope.xls",
           "January 2026 update; date updated 2026-01-05; file saved "
           "2026-01-09; sha256 05caa571...cf5e", _D,
           "Damodaran Online data, free to use with attribution (usage-terms "
           "wording not verified); only three industry rows are cited"),
)  # type: Tuple[Source, ...]


def _hicp(year, val, rationale=""):
    return scalar("Fin_HICP_EA_%d" % year, _SEC,
                  "Euro-area HICP all-items, annual average index, %d "
                  "(2015=100)" % year,
                  val, "index", "Const_None", "index", NA,
                  "Src_EurostatHICP", _S, rationale,
                  "Transcribed from docs/DATA_LOG.md (Src_EurostatHICP, "
                  "address A|INX_A_AVG|CP00|EA|%d, flag none)" % year)


_R2025 = ("D-01: the model runs in real EUR 2025 prices; euro inputs priced "
          "in another year are restated with the ratio HICP 2025 / HICP "
          "year on the Rates sheet. Euro-area (not Belgian) HICP is used "
          "because DEA, RVO and EU legal amounts are euro-area or EU "
          "figures")

INPUTS = (
    _hicp(2010, 93.14, "D-41: base year of the NGFS US$2010 conversion; EUR "
          "2010 values are restated to EUR 2025 by HICP 2025 / HICP 2010"),
    _hicp(2019, 104.80), _hicp(2020, 105.06), _hicp(2021, 107.78),
    _hicp(2022, 116.82), _hicp(2023, 123.15), _hicp(2024, 126.07),
    _hicp(2025, 128.75, _R2025),
    scalar("Fin_InflationLongRun", _SEC,
           "Long-run inflation for the Fisher conversion (ECB medium-term "
           "target)",
           2.0, "per cent", "Const_PctToFrac", "%", NA, "Src_ECBTarget",
           _S,
           "D-19: long-run inflation for the Fisher conversion of the "
           "nominal cost of capital = ECB medium-term target; re-read "
           "2026-10-20 (see docs/DATA_LOG.md)",
           "Transcribed: ECB page, \"price stability is best maintained by "
           "aiming for 2% inflation over the medium term\" (strategy review "
           "concluded July 2021). Sentence first read in 02-RESEARCH 3.9; "
           "re-read 2026-10-20, VERIFIED (DATA_LOG, Context figures and "
           "dates)"),
    scalar("Fin_HICP_EA_Sep2026", _SEC,
           "Euro-area annual HICP inflation, September 2026 (context)",
           3.8, "per cent", "Const_PctToFrac", "%", NA, "Src_EurostatFlash",
           _S,
           "Re-read 2026-10-20 (see docs/DATA_LOG.md). Context only (D-19): "
           "the 2026 energy-driven spike; flagged for the Phase 4 inflation "
           "sensitivity; not used in the base case",
           "Transcribed: Eurostat euro indicator release 2-16102026-AP "
           "(16 October 2026), euro area 3.8% in September 2026 (Belgium "
           "4.5%). First read in 02-RESEARCH 3.9; re-read 2026-10-20, "
           "VERIFIED (DATA_LOG, Context figures and dates)"),
    scalar("Fin_FX_USDperEUR_2010", _SEC,
           "US dollar per euro, 2010 annual average (NGFS conversion)",
           1.3257, "USD per EUR", "Const_None", "USD per EUR",
           PriceBasis("EUR", 2010, "nominal"), "Src_EurostatFX", _S,
           "D-41 (supersedes D-28): NGFS US$2010 prices are divided by this "
           "2010 average rate to give EUR 2010, then restated to EUR 2025 "
           "with euro-area HICP (combined factor about 1.0427 EUR 2025 per "
           "US$2010). Limitation: the route assumes the dollar kept its "
           "2010 real value against the euro; the US-CPI route would give a "
           "factor of about 1.31, i.e. prices about 25% higher (an "
           "indicative analyst estimate, not a sourced input; see "
           "docs/DATA_LOG.md; candidate Phase 4 sensitivity)",
           "Transcribed from docs/DATA_LOG.md (Src_EurostatFX, address "
           "A|AVG|NAC|USD|2010, flag none)"),
)

_NOTE = ("Transcribed (D-14 route 3): read from the official waccEurope.xls "
         "(sheet Industry Averages, date updated 2026-01-05, sha256 "
         "05caa571...) with a read-only stdlib parser after a check found no "
         "VBA or macro streams; file deleted afterwards (D-42). US$ column: ")

INPUTS = INPUTS + (
    scalar("Fin_CoC_ChemSpecialty", _SEC,
           "Cost of capital, Chemical (Specialty), Europe, Euros column (base)",
           7.811, "per cent", "Const_PctToFrac", "%", NA, "Src_Damodaran", _S,
           "D-18: a mid-sized C20 household-products firm is closer to specialty "
           "chemicals than to basic petrochemicals. Nominal cost of capital in "
           "euros (Damodaran's Euros column, 92 firms), converted to real on the "
           "Rates sheet by the Fisher formula with the ECB 2% target: "
           "1.07811/1.02 - 1 = 5.70% (D-19, D-42). Basic 5.144% (58 firms) and "
           "Diversified 7.608% (7 firms) are memo rows; Total market (without "
           "financials) 6.594% for context. No size or illiquidity premium "
           "(D-20). Mismatch: Damodaran's Euros column embeds 1.5% expected "
           "euro inflation, while the Fisher step uses the ECB 2.0% target, so "
           "the real rate is about 0.5 points lower than with Damodaran's own "
           "assumption",
           _NOTE + "8.873%"),
    scalar("Fin_CoC_ChemBasic", _SEC,
           "Cost of capital, Chemical (Basic), Europe, Euros column (memo)",
           5.144, "per cent", "Const_PctToFrac", "%", NA, "Src_Damodaran", _S,
           "D-42 memo row (not used in the base case): Chemical (Basic), Damodaran Euros column; the 1.5% euro inflation embedded in it differs from the 2.0% Fisher assumption",
           _NOTE + "6.180%"),
    scalar("Fin_CoC_ChemDiversified", _SEC,
           "Cost of capital, Chemical (Diversified), Europe, Euros column (memo)",
           7.608, "per cent", "Const_PctToFrac", "%", NA, "Src_Damodaran", _S,
           "D-42 memo row (not used in the base case): Chemical (Diversified), Damodaran Euros column; the 1.5% euro inflation embedded in it differs from the 2.0% Fisher assumption",
           _NOTE + "8.668%"),
)
