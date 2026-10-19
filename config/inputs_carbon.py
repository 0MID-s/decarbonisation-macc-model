"""Carbon prices section inputs (02-07): EUA 2025 average, ETS2 and ETS1 legal
parameters. NGFS paths are added in 02-12.

Legal values were transcribed in 02-RESEARCH 3.11 from the ELI pages on
EUR-Lex (enacted Directive (EU) 2023/959, Regulation (EU) 2026/667). Plan
02-07 ran without a web reader, so nothing was re-read and the consolidated
Directive 2003/87/EC was not available.
"""
import datetime
from typing import Tuple

from config._helpers import NA, Status, scalar
from config.schema import PriceBasis, Source

_D = datetime.date(2026, 10, 19)
_SEC = "Carbon prices"
_S = Status.SOURCED

SOURCES = (
    Source("Src_EEXAuctions", "European Energy Exchange (EEX)",
           "EU ETS1 primary market auction report, 2025 auction data (sheet "
           "Primary Market Auction)",
           "https://www.eex.com/en/markets/environmentals/eu-ets1-eu-ets2-auctions/eu-ets1-auctions",
           "2025 data, 213 successful auctions, 7 Jan to 15 Dec 2025", _D,
           "EEX market data; terms of use not verified; a single derived "
           "average is cited"),
    Source("Src_ETSDirective", "European Parliament and Council (EUR-Lex)",
           "Directive 2003/87/EC (EU ETS) as amended by Directive (EU) "
           "2023/959 of 10 May 2023 (OJ L 130, 16.5.2023), Chapter IVa "
           "(ETS2) and Annex I",
           "https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng",
           "as enacted, OJ L 130, 16.5.2023; consolidated text after the "
           "2026 amendments not verified", _D,
           "EU legal text; reuse with source acknowledged"),
    Source("Src_Reg2026_667", "European Parliament and Council (EUR-Lex)",
           "Regulation (EU) 2026/667 of 11 March 2026 amending Regulation "
           "(EU) 2021/1119 (European Climate Law), Article 2: ETS2 "
           "postponed to 2028",
           "https://eur-lex.europa.eu/eli/reg/2026/667/oj/eng",
           "OJ L 2026/667, 18.3.2026", _D,
           "EU legal text; reuse with source acknowledged"),
)  # type: Tuple[Source, ...]

_ENACTED = "(text read: Directive (EU) 2023/959 as enacted, OJ L 130, 16.5.2023)"
_NOCONS = ("; read in 02-RESEARCH 3.11, not re-read in plan 02-07; "
           "consolidated Directive 2003/87/EC after the 2026 amendments "
           "not verified")


def _legal(id_, desc, val, unit, art, rationale, src="Src_ETSDirective",
           basis=NA, text=_ENACTED, extra=""):
    return scalar(id_, _SEC, desc, val, unit, "Const_None", unit, basis,
                  src, _S, rationale,
                  "Transcribed: %s %s%s%s" % (art, text, _NOCONS, extra))


_SCOPE = ("ETS2 regulates fuel suppliers for fuels released for combustion "
          "in buildings, road transport and additional sectors (Annex III); "
          "a firm outside ETS1 pays it through fuel prices. Electricity and "
          "purchased heat are not fuels under ETS2 (flag 0). Naphtha used "
          "as a fuel is flagged 1 per Annex III; non-energy use is already "
          "excluded from the baseline")


def _scope(id_, desc, flag):
    return _legal(id_, desc, flag, "flag (1/0)", "Annex III and Art. 30a",
                  _SCOPE)


INPUTS = (
    scalar("Carbon_EUA_Avg2025", _SEC,
           "Observed EU ETS1 allowance price, 2025 volume-weighted mean "
           "auction clearing price",
           73.43, "EUR/tCO2", "Const_None", "EUR/tCO2",
           PriceBasis("EUR", 2025, "nominal"), "Src_EEXAuctions", _S,
           "Transcribed (D-14 route 3): volume-weighted mean of the 2025 EU "
           "ETS1 primary auction clearing prices from the EEX auction "
           "history file, retrieved 2026-10-18; the archive is a .zip, which "
           "the fetcher refuses by design, so the figure is entered by hand. "
           "Shown beside the NGFS 2025 values with the gap (D-29); "
           "scenarios are not floored or blended to it",
           "Simple mean of the same 213 auctions: 73.45 EUR/t; last 2025 "
           "auction (15 Dec): 84.60. Computed in 02-RESEARCH 3.10 "
           "(213 auctions: 142 EU, 45 DE, 25 PL, 1 NIR)"),
    _legal("Carbon_ETS2_StartYear",
           "ETS2 start year (default, after postponement)", 2028, "year",
           "Regulation (EU) 2026/667 Art. 2 (Art. 30k(2) rules apply)",
           "Default 2028 (input; delayed-start sensitivity in Phase 4)",
           src="Src_Reg2026_667",
           text="(text read: Regulation (EU) 2026/667, OJ L 2026/667, "
                "18.3.2026)"),
    _legal("Carbon_ETS2_StartYearEnacted",
           "ETS2 start year as originally enacted (memo)", 2027, "year",
           "Directive 2003/87/EC Art. 30d(1), \"From 2027 ... auctioned\"",
           "Memo for the delayed-start sensitivity; superseded by "
           "Carbon_ETS2_StartYear"),
    _legal("Carbon_ETS2_StabPrice",
           "ETS2 price-stability threshold, EUR per allowance (2020 prices)",
           45, "EUR/tCO2e", "Art. 30h(2)",
           "EUR 45 in 2020 prices, indexed with the European consumer price "
           "index; restated to EUR 2025 on the Rates sheet (D-30)",
           basis=PriceBasis("EUR", 2020, "real")),
    _legal("Carbon_ETS2_StabMonths",
           "Consecutive months above threshold that trigger release", 2,
           "months", "Art. 30h(2)",
           "Trigger condition for the stability release (D-30)"),
    _legal("Carbon_ETS2_StabRelease",
           "Allowances released when the stability threshold is exceeded",
           20, "allowances (million)", "Art. 30h(2)",
           "Release volume in the enacted text; EPRS reports the 2026 "
           "amendments added more (secondary), so the consolidated value "
           "may differ (D-30)"),
    _legal("Carbon_ETS2_TripleTrigger",
           "Price multiple of the preceding six-month average that triggers "
           "the larger release", 3, "multiple", "Art. 30h(3)",
           "Trigger for the larger release (D-30)"),
    _legal("Carbon_ETS2_TripleRelease",
           "Allowances released at the price-multiple trigger", 150,
           "allowances (million)", "Art. 30h(3)",
           "Release volume in the enacted text (D-30)"),
    _scope("Carbon_ETS2_Scope_Gas", "Natural gas covered by ETS2 (1) or not (0)", 1),
    _scope("Carbon_ETS2_Scope_LPG", "LPG covered by ETS2 (1) or not (0)", 1),
    _scope("Carbon_ETS2_Scope_Naphtha", "Naphtha used as fuel covered by ETS2 (1) or not (0)", 1),
    _scope("Carbon_ETS2_Scope_OtherFuels", "Other combustion fuels covered by ETS2 (1) or not (0)", 1),
    _scope("Carbon_ETS2_Scope_FleetDiesel", "Road diesel (fleet) covered by ETS2 (1) or not (0)", 1),
    _scope("Carbon_ETS2_Scope_Elec", "Purchased electricity covered by ETS2 (1) or not (0)", 0),
    _scope("Carbon_ETS2_Scope_Heat", "Purchased heat covered by ETS2 (1) or not (0)", 0),
    _legal("Carbon_ETS1_ThermalThresholdMW",
           "EU ETS1 threshold: total rated thermal input of combustion "
           "installations", 20, "MW", "Annex I (combustion of fuels in "
           "installations with total rated thermal input exceeding 20 MW)",
           "Used by the Baseline D-07 sanity row (average fuel load is a "
           "lower bound on rated thermal input, not proof of being below "
           "the threshold)",
           extra="; Annex I wording was not re-read in plan 02-07 and the "
                 "20 MW figure is UNVERIFIED against the article text in "
                 "this run (it is the D-07 design value)"),
)
