"""Carbon prices section inputs (02-07): EUA 2025 average, ETS2 and ETS1 legal
parameters. NGFS paths were added in 02-12.

Legal values were transcribed in 02-RESEARCH 3.11 from the ELI pages on
EUR-Lex (enacted Directive (EU) 2023/959, Regulation (EU) 2026/667). Plan
02-07 ran without a web reader, so nothing was re-read and the consolidated
Directive 2003/87/EC was not available.
"""
import datetime
from typing import Tuple

from config._helpers import NA, Status, scalar, series
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
    Source("Src_NGFSPhaseV",
           "Network for Greening the Financial System (NGFS); data hosted by "
           "IIASA",
           "NGFS long-term climate scenarios Phase V (v5.0), variable "
           "Price|Carbon, model REMIND-MAgPIE 3.3-4.8, region OECD & EU (R5)",
           "https://data.ene.iiasa.ac.at/ngfs/",
           "Phase V, November 2024; explorer table pasted by the user on "
           "2026-10-19 (TSV sha256 42bd29b4b902... in DATA_LOG); the explorer "
           "CSV snapshot matched and was deleted at the user's request "
           "(sha256 15d8e1ea...639f, D-43)", _D,
           "Adapted CC BY 4.0 (NGFS Phase 5 Scenario Explorer licence, "
           "transcribed by the user, D-44): parts and adapted material may "
           "be shared with attribution (\"NGFS Phase 5 Scenario Explorer, "
           "hosted by IIASA\", (c) NGFS Phase 5 Scenario Explorer), a "
           "statement that values were modified, and no implied endorsement"),
)  # type: Tuple[Source, ...]

_ENACTED = "(per 02-RESEARCH 3.11: Directive (EU) 2023/959 as enacted, OJ L 130, 16.5.2023)"


_UNV = ("Unverified transcription: transcribed from 02-RESEARCH 3.11 "
        "(secondary reading of the EUR-Lex page); to be verified against "
        "the legal text. ")
_USER = ("Text supplied by the user from EUR-Lex on 2026-10-20 (sha256 in "
         "docs/DATA_LOG.md): ")
_LOG = ("see docs/DATA_LOG.md, Legal texts (WR-02 re-read)")
# WR-03: which wording was actually read, shown first in the Inputs notes so
# "Sourced" is not read as "checked against current consolidated law"
READ_ETS2_ENACTED = ("Dir. (EU) 2023/959 as enacted; later amendments (2026) "
                     "not checked")
READ_ANNEX_I_2003 = ("original 2003 Annex I wording; consolidated text not "
                     "read")


def _legal(id_, desc, val, unit, art, rationale, src="Src_ETSDirective",
           basis=NA, text=_ENACTED, extra="", status=Status.ASSUMPTION,
           read=None):
    """Legal parameter. Sourced only when status=SOURCED is passed after a
    VERIFIED row in docs/DATA_LOG.md; the default is an analyst assumption.
    ``read`` names the exact text that was read (shown first)."""
    if status is Status.SOURCED:
        rationale = (("Text read: %s. " % read) if read else "") + _USER + rationale
        # IN-04: the text was read in the user's paste, not via 02-RESEARCH
        text = text.replace("per 02-RESEARCH 3.11: ", "")
        note = ("Transcribed: %s %s; text supplied by the user from EUR-Lex "
                "on 2026-10-20, quote and sha256 in docs/DATA_LOG.md "
                "(Legal texts, plan 02-16)%s" % (art, text, extra))
    else:
        rationale = _UNV + rationale
        note = ("Transcribed: %s %s; EUR-Lex re-read 2026-10-20 returned no "
                "text (NOT READ), %s%s" % (art, text, _LOG, extra))
    return scalar(id_, _SEC, desc, val, unit, "Const_None", unit, basis,
                  src, status, rationale, note)


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
           PriceBasis("EUR", 2025, "nominal"), "Src_EEXAuctions",
           Status.ASSUMPTION,
           "Unverified transcription: not reproducible from the repository "
           "(WR-01); the user chose on 2026-10-20 not to supply the EEX rows, "
           "see docs/DATA_LOG.md, EEX 2025 auctions (plan 02-16). "
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
           "Regulation (EU) 2026/667, postponement provision (as pasted from "
           "the ELI page; article number not shown in the paste)",
           "Default 2028 (input; a further delay of Sens_ETS2_StartDelay "
           "years is a tornado driver on the Sensitivity sheet)",
           src="Src_Reg2026_667", status=Status.SOURCED,
           text="(per 02-RESEARCH 3.11: Regulation (EU) 2026/667, OJ L 2026/667, "
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
           basis=PriceBasis("EUR", 2020, "real"), status=Status.SOURCED,
           read=READ_ETS2_ENACTED),
    _legal("Carbon_ETS2_StabMonths",
           "Consecutive months above threshold that trigger release", 2,
           "months", "Art. 30h(2)",
           "Trigger condition for the stability release (D-30)",
           status=Status.SOURCED, read=READ_ETS2_ENACTED),
    _legal("Carbon_ETS2_StabRelease",
           "Allowances released when the stability threshold is exceeded",
           20, "allowances (million)", "Art. 30h(2)",
           "Release volume in the enacted text; EPRS reports the 2026 "
           "amendments added more (secondary), so the consolidated value "
           "may differ (D-30)", status=Status.SOURCED,
           read=READ_ETS2_ENACTED),
    _legal("Carbon_ETS2_TripleTrigger",
           "Price multiple of the preceding six-month average that triggers "
           "the larger release", 3, "multiple", "Art. 30h(3)",
           "Trigger for the larger release (D-30)",
           status=Status.SOURCED, read=READ_ETS2_ENACTED),
    _legal("Carbon_ETS2_TripleRelease",
           "Allowances released at the price-multiple trigger", 150,
           "allowances (million)", "Art. 30h(3)",
           "Release volume in the enacted text (D-30)",
           status=Status.SOURCED, read=READ_ETS2_ENACTED),
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
           "20 MW per Annex I, original 2003 wording (consolidated text not "
           "read; the threshold is unchanged per an analyst note). Used by the "
           "Baseline D-07 sanity row (average fuel load is a "
           "lower bound on rated thermal input, not proof of being below "
           "the threshold)",
           status=Status.SOURCED, read=READ_ANNEX_I_2003,
           extra="; verified against the original 2003 Annex I wording only, "
                 "the consolidated text was not read"),
)


_NGFS_BASIS = PriceBasis("USD", 2010, "real")
_NGFS_NOTE = ("Transcribed (D-14 route 3): NGFS Phase V explorer table pasted "
              "by the user, model REMIND-MAgPIE 3.3-4.8, region OECD & EU "
              "(R5), variable Price|Carbon, unit US$2010/t CO2; see "
              "docs/DATA_LOG.md \"NGFS Phase V (D-40, D-43\"")
_NGFS_RAT = ("%s scenario = NGFS %s (D-26); one IAM for all three scenarios, "
             "EU region (D-27). NGFS carbon prices are model shadow prices "
             "(marginal abatement costs), not market prices. Converted to EUR "
             "2025 on the Carbon sheet by the 2010 average USD per EUR rate, "
             "then euro-area HICP 2025/2010 (D-41), and interpolated to "
             "annual values to 2055. The OECD & EU (R5) region is used as the "
             "EU proxy (limitation)")
_NGFS_UNIT = "US$2010/tCO2"


def _ngfs(key, label, tier, y0, pts):
    rat = _NGFS_RAT % (tier, label)
    return (
        scalar("Carbon_NGFS_%s_Y0" % key, _SEC,
               "NGFS Price|Carbon, %s, 2025 (pre-timeline anchor)" % label,
               y0, _NGFS_UNIT, "Const_None", _NGFS_UNIT, _NGFS_BASIS,
               "Src_NGFSPhaseV", _S, rat, _NGFS_NOTE),
        series("Carbon_NGFS_%s" % key, _SEC,
               "NGFS Price|Carbon, %s, 2030-2055 points" % label, pts,
               _NGFS_UNIT, "Const_None", _NGFS_UNIT, _NGFS_BASIS,
               "Src_NGFSPhaseV", _S, rat, _NGFS_NOTE),
    )

_CP = _ngfs('CP', 'Current Policies', 'Low', 23.28186044073566,
      ((2030, 23.27705035642764), (2035, 23.31220235560375), (2040, 23.39144477859998), (2045, 23.52964512661944), (2050, 23.71263250865933), (2055, 23.94119902155565)))
_NDC = _ngfs('NDC', 'Nationally Determined Contributions (NDCs)', 'Central', 121.5670480013598,
      ((2030, 216.911391375443), (2035, 215.9468030914937), (2040, 214.9804569215596), (2045, 213.8716366193923), (2050, 211.1302917041736), (2055, 206.8712342559588)))
_NZ50 = _ngfs('NZ50', 'Net Zero 2050', 'High', 152.3844736690992,
      ((2030, 282.2098852376754), (2035, 452.7636315503082), (2040, 623.9807303273395), (2045, 795.3846925061491), (2050, 870.0502582689974), (2055, 898.2429363719594)))

INPUTS = INPUTS + (
    scalar("Carbon_NGFS_Y0Year", _SEC,
           "NGFS anchor year before the 2026 timeline start", 2025, "year",
           "Const_None", "year", NA, "Src_NGFSPhaseV", _S,
           "First NGFS point before the 2026 timeline start; anchors the "
           "2026-2029 interpolation", _NGFS_NOTE),
    _CP[0], _NDC[0], _NZ50[0], _CP[1], _NDC[1], _NZ50[1],
)
