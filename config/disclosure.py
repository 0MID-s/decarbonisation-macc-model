"""Disclosure mapping data (plan 05-06, D-01 to D-06).

Static text only: which model outputs support which IFRS S2 paragraph or
revised ESRS E1 disclosure requirement, how strongly, and how the reference was
verified. Stdlib only; imported by xl.sheets.disclosure and the tests, never
importing them.

Requirements are paraphrases (no quotation, at most 160 characters; D-04).
Strengths are analyst classifications (RESEARCH A1), not claims of compliance.
Set 1 equivalents show the disclosure requirement and its verified paragraph
range only; sub-paragraph letters were not read and are left out.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

STRENGTHS = ("Direct", "Supports", "Not covered")
STATUSES = ("Verified", "Verified (amendment summary only)",
            "Partly verified, flagged", "Reference not verified", "n/a")

FLAG_1563 = ("OJ number checked via EUR-Lex listing and two secondary "
             "sources; EUR-Lex page not machine-readable")


@dataclass(frozen=True)
class DisclosureRow:
    standard: str
    reference: str
    set1_equivalent: str
    requirement: str
    output_names: Tuple[str, ...]
    strength: str
    gap: str
    status: str
    status_note: str
    ref_id: str


@dataclass(frozen=True)
class StdRef:
    ref_id: str
    publisher: str
    title: str
    url: str
    edition: str
    retrieved: str
    licence_note: str
    status_note: str


STD_REFS = {
    "Std_IFRS_S2": StdRef(
        "Std_IFRS_S2", "IFRS Foundation (ISSB)",
        "IFRS S2 Climate-related Disclosures (HTML text)",
        "https://www.ifrs.org/content/dam/ifrs/publications/html-standards-"
        "issb/english/2023/issued/issbs2.html",
        "June 2023 issued text", "2026-10-25",
        "IFRS Foundation copyright; requirements paraphrased",
        "Open HTML page read in full on the stated date; no login needed"),
    "Std_IFRS_S2_Amend2025": StdRef(
        "Std_IFRS_S2_Amend2025", "IFRS Foundation (ISSB)",
        "ISSB issues targeted amendments to IFRS S2 (news item)",
        "https://www.ifrs.org/news-and-events/news/2025/12/"
        "issb-issues-targeted-amendments-ifrs-s2/",
        "11 December 2025", "2026-10-25",
        "IFRS Foundation copyright; summary paraphrased",
        "Amendment text behind login, not read; summary lists four relief "
        "items, none on 29(a)(v), 29(e), 29(f)"),
    "Std_ESRS_Rev2026": StdRef(
        "Std_ESRS_Rev2026", "EFRAG",
        "Revised ESRS E1 Climate change, delegated-act view "
        "(Knowledge Hub)",
        "https://knowledgehub.efrag.org/eng/interactive/simplified-esrs/"
        "esrs-e1/delegated-act",
        "Commission Delegated Regulation (EU) 2026/1563 of 3 July 2026, "
        "OJ 21 Sep 2026", "2026-10-25",
        "EFRAG Knowledge Hub free plan; requirements paraphrased",
        FLAG_1563),
    "Std_ESRS_Set1": StdRef(
        "Std_ESRS_Set1", "EFRAG",
        "ESRS Set 1 E1 Climate change (Knowledge Hub)",
        "https://knowledgehub.efrag.org/eng/interactive/esrs-set-1/"
        "esrs-e1-climate-change/2025-11-10-quick-fix/objective",
        "Delegated Regulation (EU) 2023/2772, quick fix of 10 Nov 2025 "
        "(label in URL)", "2026-10-25",
        "EFRAG Knowledge Hub free plan; requirements paraphrased",
        "Hub rendering read; the regulation itself was not readable on "
        "EUR-Lex"),
    "Std_EC_Adoption": StdRef(
        "Std_EC_Adoption", "European Commission",
        "Commission adopts revised sustainability reporting standards",
        "https://finance.ec.europa.eu/news/commission-adopts-revised-"
        "sustainability-reporting-standards-2026-07-03_en",
        "3 July 2026", "2026-10-25",
        "European Commission reuse policy",
        "Press page read directly; confirms adoption date, not the OJ number"),
    "Std_EURLex_1563": StdRef(
        "Std_EURLex_1563", "Publications Office of the EU (EUR-Lex)",
        "Commission Delegated Regulation (EU) 2026/1563 (ELI link)",
        "https://eur-lex.europa.eu/eli/reg_del/2026/1563/oj",
        "OJ 21 Sep 2026", "2026-10-25",
        "EU legal text, reuse per Commission decision",
        FLAG_1563),
}  # type: Dict[str, StdRef]

# Single-cell defined names the Value column can show -> number-format role.
OUTPUT_UNITS = {
    "M_Portfolio_NPV": "eur", "Sens_PortfolioNPV": "eur",
    "MACC_TotalAbatement": "tco2e", "M_HP_Capex": "eur",
    "M_HP_AvgtSel": "tco2e", "Sens_RankStab_AnyChanged": "general",
    "Sel_Scenario": "general", "Sel_DirectETS": "general",
    "BL_Scope1": "tco2e", "BL_S2_LB": "tco2e", "BL_Total_MWh": "mwh",
    "Expo_CumBAU_Sel": "eur", "Expo_ICP_Level": "eur_per_t",
    "Carbon_ICP_Level": "eur_per_t",
}  # type: Dict[str, str]


def value_name(row):
    """First single-cell output name of a row, or None."""
    for n in row.output_names:
        if n in OUTPUT_UNITS:
            return n
    return None


def _s2(ref, set1, req, names, strength, gap, status="Verified",
        note="June 2023 text read on ifrs.org", ref_id="Std_IFRS_S2"):
    return DisclosureRow("IFRS S2", ref, set1, req, tuple(names), strength,
                         gap, status, note, ref_id)


def _es(ref, set1, req, names, strength, gap):
    return DisclosureRow("ESRS E1 (rev.)", ref, set1, req, tuple(names),
                         strength, gap, "Verified",
                         "EFRAG Knowledge Hub rendering of the adopted text",
                         "Std_ESRS_Rev2026")


_AMEND = ("IFRS summary only, amendment text not read; the December 2025 "
          "amendments are not stated to change this requirement")
_V = "Verified (amendment summary only)"

DISCLOSURE_ROWS = (
    # ---- IFRS S2 -------------------------------------------------------
    _s2("14(a)(ii)", "-", "Say what direct mitigation actions are taken or "
        "planned", ("MACC_Rank_Measure", "M_Portfolio_NPV"), "Supports",
        "Six candidate measures, not committed actions"),
    _s2("14(a)(iv)", "-", "Disclose any climate transition plan with its key "
        "assumptions and dependencies", ("MACC_Rank_Tier",), "Supports",
        "No board-approved plan exists for a representative firm"),
    _s2("14(a)(v)", "-", "Explain how any stated climate targets will be "
        "reached", ("MACC_TotalAbatement",), "Supports",
        "The model sets no target"),
    _s2("14(b)", "-", "Describe how these activities are or will be "
        "resourced", ("M_HP_Capex", "M_PV_Capex"), "Supports",
        "Planned appraisal capex only"),
    _s2("14(c)", "-", "Report progress against previously disclosed plans",
        (), "Not covered", "First-period model, no prior plan"),
    _s2("15(a)", "-", "Current financial effects of climate risks and "
        "opportunities on position, performance and cash flows", (),
        "Not covered", "The model is forward-looking"),
    _s2("15(b), 16(c)-(d)", "-", "Anticipated effects on position, "
        "performance and cash flows over time, including investment and "
        "funding plans",
        ("M_Portfolio_NPV", "Sens_PortfolioNPV", "Expo_CumBAU_Sel",
         "Expo_CumAvoided_Sel"), "Supports",
        "Pre-tax, ex-VAT, 10-year exposure window, no balance-sheet items"),
    _s2("16(a)-(b)", "-", "Effects in the reporting period and items at risk "
        "of material adjustment next period", (), "Not covered",
        "Needs actual accounts"),
    _s2("17-21", "-", "A single amount or a range is allowed; use supportable "
        "information; explain if quantification is omitted", ("Sens_Grid",),
        "Supports", "Model supplies ranges and sensitivities; the omission "
        "logic is a reporter judgement"),
    _s2("22(a)", "-", "Assess the resilience of strategy to climate change, "
        "the uncertainties and the capacity to adapt",
        ("Sens_RankStab_AnyChanged", "Sens_Grid"), "Supports",
        "Quantitative stress only; no strategic narrative"),
    _s2("22(b)", "-", "Describe the scenario analysis: scenarios, sources, "
        "time horizon and key assumptions", ("Sel_Scenario",), "Supports",
        "NGFS Low, Central, High map to Current Policies, NDCs and Net Zero "
        "2050; transition scenarios only, no physical"),
    _s2("29(a)(i)(1)", "E1-6 (44-55)", "Gross Scope 1 greenhouse gas "
        "emissions in tCO2e", ("BL_Scope1",), "Direct",
        "Representative sector-average firm; process emissions excluded",
        _V, _AMEND),
    _s2("29(a)(i)(2)", "E1-6 (44-55)", "Gross Scope 2 greenhouse gas "
        "emissions in tCO2e", ("BL_S2_LB", "BL_S2_MB"), "Direct",
        "Both bases shown, never summed", _V, _AMEND),
    _s2("29(a)(i)(3), 29(a)(vi)", "E1-6 (44-55)", "Scope 3 emissions and the "
        "categories included", (), "Not covered",
        "Scope 3 is excluded (see Notes and Baseline)", _V, _AMEND),
    _s2("29(a)(ii)-(iii)", "E1-6 (44-55)", "Measurement approach, inputs and "
        "assumptions under the GHG Protocol, and any changes", (), "Supports",
        "Method is described on Notes and each emission factor on Inputs; "
        "the amendments add jurisdictional relief on method", _V,
        "IFRS summary only, amendment text not read; one listed relief item "
        "concerns GHG Protocol method, so check before relying"),
    _s2("29(a)(iv)", "E1-6 (44-55)", "Split Scope 1 and 2 between the "
        "consolidated group and other investees", (), "Not covered",
        "Single-entity firm", _V, _AMEND),
    _s2("29(a)(v)", "E1-6 (44-55)", "Give location-based Scope 2 and any "
        "contractual-instrument information needed to understand it",
        ("BL_S2_LB", "BL_S2_MB", "M_RC_AvgtSel"), "Direct",
        "Strongest fit: the basis selector exists for this paragraph", _V,
        _AMEND),
    _s2("29(b)", "E1-9 (64-69)", "Amount and share of assets or activities "
        "exposed to transition risk", ("Expo_CumBAU_Sel",), "Supports",
        "Gives cost exposure, not the asset or revenue share asked for"),
    _s2("29(c)", "E1-9 (64-69)", "Amount and share of assets or activities "
        "exposed to physical risk", (), "Not covered",
        "Deliberate restraint: no physical risk analysis"),
    _s2("29(d)", "E1-9 (64-69)", "Amount and share of assets or activities "
        "aligned with climate opportunities", ("M_Portfolio_NPV",),
        "Supports", "NPV of measures, not an asset or revenue share"),
    _s2("29(e)", "E1-1 (14-17)", "Capital expenditure, financing or "
        "investment deployed toward climate risks and opportunities",
        ("M_HP_Capex", "M_PV_Capex"), "Supports",
        "Planned appraisal capex, not capital actually deployed"),
    _s2("29(f)(i)", "E1-8 (62-63)", "Explain whether and how an internal "
        "carbon price is applied in decisions",
        ("Expo_ICP_Level", "Expo_ICP_BAU"), "Direct",
        "The internal carbon price is a management lens, never cash"),
    _s2("29(f)(ii)", "E1-8 (62-63)", "State the internal carbon price per "
        "tonne of CO2e that is used", ("Carbon_ICP_Level",), "Direct",
        "Analyst assumption, see Inputs"),
    _s2("29(g)", "E1.GOV-3 (13)", "Whether executive remuneration "
        "is linked to climate-related considerations", (), "Not covered",
        "Remuneration linkage is outside the model"),
    _s2("33-36", "E1-4 (30-34)", "Climate targets: metric, scope, period and "
        "base year, including any Scope 3 targets", (), "Not covered",
        "The model sets no targets, so Scope 3 targets are also absent"),
    _s2("6 (governance)", "-", "Governance bodies "
        "overseeing climate-related risks and opportunities", (),
        "Not covered", "Governance is outside the model",
        "Reference not verified",
        "Paragraph number is an analyst recollection; it was not in the list "
        "of paragraphs read on the IFRS page, so treat as unconfirmed"),
    # ---- revised ESRS E1 -------------------------------------------------
    _es("E1-1 paras 11-13", "E1-1 (14-17)", "Transition plan: decarbonisation "
        "levers, key actions, investments and funding, assumptions",
        ("MACC_Rank_Measure", "M_Portfolio_NPV"), "Supports",
        "No plan adopted; the MACC is evidence for one"),
    _es("E1-2 paras 16-17", "E1.IRO-1 (20-21)", "Method for assessing "
        "exposure and the scenario analysis: range, scope, assumptions, "
        "period", ("Sel_Scenario",), "Supports",
        "Net Zero 2050 gives a strict-route scenario; no physical hazards"),
    _es("E1-3 paras 18-19", "E1.SBM-3 (18-19)", "Resilience of strategy and "
        "business model", ("Sens_RankStab_AnyChanged", "Sens_Grid"),
        "Supports", "Quantitative only"),
    _es("E1-5 para 22", "E1-3 (26-29)", "Key mitigation actions by "
        "decarbonisation lever, with expected GHG reduction per lever",
        ("M_HP_AvgtSel", "MACC_Rank_Width"), "Direct",
        "Expected reduction per lever is exactly the MACC bar width"),
    _es("E1-6 para 24", "E1-4 (30-34)", "GHG reduction targets: absolute, "
        "scope coverage and science-based status", (), "Not covered",
        "The model sets no targets"),
    _es("E1-7 paras 26-27", "E1-5 (35-43)", "Total energy consumption in MWh "
        "by fossil, nuclear and renewable source; fossil split by fuel",
        ("BL_Total_MWh", "BL_Gas_MWh", "BL_Elec_MWh", "BL_Heat_MWh",
         "BL_LPG_MWh"), "Supports",
        "Totals and fuels present; nuclear or renewable split of purchased "
        "electricity not modelled"),
    _es("E1-8 para 30(a)", "E1-6 (44-55)", "Gross Scope 1 and Scope 2 "
        "emissions, location-based and market-based",
        ("BL_Scope1", "BL_S2_LB", "BL_S2_MB", "BL_S12_LB", "BL_S12_MB"),
        "Direct", "Representative firm; both bases shown"),
    _es("E1-8 para 30(a)(i)", "E1-6 (44-55)", "Share of Scope 1 emissions "
        "inside the EU emissions trading system",
        ("Sel_DirectETS", "Expo_DirETS_DiscSel"), "Supports",
        "Firm is below the ETS1 threshold by default; no reported share"),
    _es("E1-8 para 30(a)(iii)", "E1-6 (44-55)", "Scope 3 emissions by "
        "significant category", (), "Not covered", "Scope 3 is excluded"),
    _es("E1-8 para 31", "E1-6 (44-55)", "Direct biogenic CO2 emissions "
        "reported separately", (), "Not covered", "Not modelled"),
    _es("E1-10 para 37(a)", "E1-8 (62-63)", "Whether and how carbon pricing "
        "is applied in decisions, and consistency with impairment prices",
        ("Expo_ICP_Level",), "Supports",
        "Consistency with impairment tests is a reporter task"),
    _es("E1-10 para 37(b)", "E1-8 (62-63)", "Average carbon price per tonne "
        "for each internal pricing scheme", ("Carbon_ICP_Level",), "Direct",
        "One scheme: a shadow price"),
    _es("E1-11 paras 39-40", "E1-9 (64-69)", "Carrying amount and share of "
        "assets and net revenue at material physical or transition risk", (),
        "Not covered", "Needs balance-sheet and revenue data a sector-average "
        "firm lacks; carbon cost is shown instead (see S2 15(b))"),
    _es("E1-11 para 41", "E1-9 (64-69)", "Methodology, scope, assumptions "
        "and limits of the financial-effects quantification",
        ("Sens_Grid",), "Supports", "Method on Notes; ranges on Sensitivity"),
    _es("E1-11 para 42", "E1-9 (64-69)", "Assets or revenue related to "
        "climate opportunities", ("M_Portfolio_NPV",), "Supports",
        "NPV, not an asset or revenue amount"),
    # ---- assurance ---------------------------------------------------------
    DisclosureRow("IFRS S2 / ESRS", "-", "-", "Assurance of the "
                  "sustainability statement is outside the disclosure "
                  "content of both standards", (), "Not covered",
                  "Outside this model", "n/a",
                  "No paragraph applies; shown for completeness", ""),
)  # type: Tuple[DisclosureRow, ...]


def value_names():
    """Distinct single-cell names the Value column links to."""
    seen = []
    for r in DISCLOSURE_ROWS:
        n = value_name(r)
        if n and n not in seen:
            seen.append(n)
    return tuple(seen)


# (hypothesis, official finding, action), recorded on Notes (D-01).
CORRECTIONS = (
    ("Revised E1-5 = energy",
     "Revised E1-7 is Energy consumption and mix (paras 25-28); revised "
     "E1-5 is Actions and resources (paras 21-22)",
     "Use E1-7 for energy"),
    ("Revised GHG row not yet numbered",
     "Revised E1-8 is Gross scope 1, 2, 3 GHG emissions (paras 29-31)",
     "Use E1-8 for GHG emissions"),
    ("E1-8 = internal carbon price and E1-9 = financial effects",
     "That is the Set 1 numbering; the revised numbering is E1-10 (carbon "
     "pricing, paras 36-37) and E1-11 (financial effects, paras 38-42)",
     "Show the revised number with the Set 1 equivalent beside it"),
    ("Revised ESRS regulation is 2026/1560 or 2026/1563",
     "2026/1563 is the revised ESRS; 2026/1560 is the voluntary standard "
     "(EUR-Lex listing, two secondary sources)",
     "Cite 2026/1563 and keep the flag: " + FLAG_1563),
    ("Disclosure source IDs come from the Sources register (D-03)",
     "Sources holds input provenance only; validate_provenance rejects a "
     "source no input uses",
     "Standards are cited in the Disclosure standards register (Std_* IDs), "
     "not config/sources.py"),
)  # type: Tuple[Tuple[str, str, str], ...]
