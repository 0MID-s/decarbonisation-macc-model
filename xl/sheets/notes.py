"""Notes shell: scope, conventions, limitations, exclusions (plan 02-10).

Prose carries no figures that are also input values; it refers to input ids.
Lists are generated from the dataset (transcribed inputs, ETS2 projection).
"""
import re
from typing import Dict, List

from config.schema import Status
from xl.layout import LABEL_COL, setup_sheet
from xl.sheets.carbon import (
    EUA_NOTE, NGFS_ATTRIBUTION, NGFS_LICENCE, NGFS_MODIFIED,
    ngfs_model_text)
from xl.sheets.common import disclaimer_text, write_title_band
from xl.styles import SheetKind

LAST_COL = 8
WRAP = 130
PROJ_PREFIX = "Carbon_ETS2_Proj_"
NO_PROJECTION = (
    "ETS2 price projection: Not captured: no official projection located on "
    "allowlisted sources (see RESEARCH 3.11). Phase 4 decides how carbon "
    "prices apply to each exposure channel (D-30).")

ABOUT = (
    "Every number on the Inputs sheet is either sourced to a cited real-world "
    "dataset or labelled as an analyst assumption with its rationale.",
)
CONVENTIONS = (
    "Money basis: real terms, EUR 2025 (D-01). Inputs priced in another year "
    "are restated on the Rates sheet by a visible euro-area HICP ratio; "
    "Eurostat SBS values used only in ratios, the 2026-S1 context prices and "
    "exchange rates are exempt, and the PBL values stated in EUR 2026 are used "
    "as stated because no annual 2026 HICP exists yet (price year is a label, "
    "not verified).",
    "Energy basis: MWh on a net calorific value (NCV) basis to match Eurostat "
    "balances; gas prices and DESNZ factors are converted from gross "
    "calorific value (D-08).",
    "Reference year: the common year Base_RefYear for SBS, the energy balance "
    "and air accounts (D-04).",
    "Scope of prices: energy prices exclude VAT and other recoverable taxes "
    "(Eurostat X_VAT); the model is pre-tax.",
)
LIMITATIONS = (
    "The Belgian C20 + C21 average is dominated by large petrochemical and "
    "pharmaceutical sites, so a medium household-products firm's derived "
    "energy intensity is probably overstated; no unsourced size adjustment is "
    "applied (D-06).",
    "Naphtha is kept as a flagged line: it is sector-specific and not "
    "addressable by the Phase 3 measures (D-06).",
    "The energy balance sector covers NACE divisions C20 and C21, so the value-added "
    "scaling base is C20 + C21 (D-39).",
    "The 2024 air emissions accounts are imputed by Eurostat.",
    "The UK DESNZ heat factor is used as a Belgian proxy.",
    "Accepted DATA-05 deviation (D-23 fallback, D-38): the grid factor is "
    "held flat at the latest machine-readable EEA year because no sourced "
    "Belgian projection was found on an allowlisted host; the Federal "
    "Planning Bureau (plan.be) path is an option needing an allowlist "
    "decision.",
    "The residual-mix factor is held flat (D-24).",
    "The RVO cost price year is assumed to be the list year.",
    "The DEA indirect-investment line is to be resolved in Phase 3.",
    "No size or illiquidity premium is added to the discount rate; this is "
    "covered by the Phase 4 rank-stability test (D-20).",
    "Discount-rate basis: the Euros column of Damodaran's waccEurope.xls "
    "(January 2026 update, read from the official file with a read-only "
    "parser after a macro check, D-42). That column embeds 1.5% expected euro "
    "inflation while the model deflates with the ECB target held in "
    "Fin_InflationLongRun, an inflation mismatch that makes the real rate "
    "slightly lower.",
    "The NGFS region OECD & EU (R5) is used as the EU proxy (D-27).",
    "Alternative conversion route (D-41): a US-CPI route would give a factor "
    "of about 1.31 instead of the Eurostat route factor, so carbon prices "
    "about a quarter higher (an indicative analyst estimate, not a sourced "
    "input; see docs/DATA_LOG.md); a candidate Phase 4 sensitivity.",
)
LEGAL_PREFIXES = ("Carbon_ETS2_", "Carbon_ETS1_")
LEGAL_EXTRA_IDS = ("Base_NRG_IncludesC21",)
_TEXT_READ = re.compile(r"^Text read: (.+?)\. Text supplied by the user")


def legal_status_note(inputs):
    """Notes paragraph on legal parameters, generated from the config
    statuses (IN-05) so it cannot drift from the Inputs Status column."""
    legal = [r for r in inputs
             if r.id.startswith(LEGAL_PREFIXES) or r.id in LEGAL_EXTRA_IDS]
    if not legal:
        return "No legal parameters in this dataset."
    sourced = [r for r in legal if r.status is Status.SOURCED]
    assumed = [r for r in legal if r.status is Status.ASSUMPTION]
    parts = []
    if sourced:
        parts.append("Legal parameters whose text the user supplied from "
                     "EUR-Lex on 2026-10-20 are Sourced: %s."
                     % ", ".join(r.id for r in sourced))
        by_read = {}  # type: Dict[str, List[str]]
        for r in sourced:
            m = _TEXT_READ.match(r.rationale)
            if m:
                by_read.setdefault(m.group(1), []).append(r.id)
        for q, ids in by_read.items():
            parts.append("Text read for %s: %s." % (", ".join(ids), q))
    if assumed:
        parts.append("Analyst assumptions pending verification, because no "
                     "legal text was supplied for them: %s."
                     % ", ".join(r.id for r in assumed))
    parts.append("The log is in docs/DATA_LOG.md, Legal texts (WR-02 re-read "
                 "and plan 02-16).")
    return " ".join(parts)


MEASURES_TITLE = "Measures and MACC method (Phase 3)"
MEASURES_METHOD = (
    "Cash flows are pre-tax, ex-VAT and in real EUR 2025. Year 0 is 2026 "
    "(undiscounted), operating flows run 2027-2055 and are discounted at "
    "year end (D-01, D-04).",
    "The heat pump and the fleet measure use incremental capex over the "
    "boiler or diesel van the firm would buy anyway (the McKinsey MACC "
    "convention). LED, VSD and PV use full cost. The full-capex NPV memo "
    "line is for transparency only (D-05).",
    "Assets are replaced like-for-like at the same real capex, with no "
    "learning-curve decline. Life left in 2055 is credited as a "
    "straight-line residual value (D-02).",
    "The financial NPV includes any subsidy (Meas_*_Subsidy, default 0) and "
    "drives IRR, payback and abatement cost. NPV before subsidy is shown "
    "alongside it (D-15).",
    "Carbon value at the selected NGFS scenario is a shadow-price lens, not "
    "cash. Cash carbon costs by channel belong to Phase 4 (D-16).",
    "The electricity stack applies efficiency, electrification and solar "
    "first, then the renewable contract on the residual. Measures interact "
    "and the stack fixes one order, so per-measure results are not fully "
    "independent (an independence limitation). The market-based electricity "
    "tonnes of the six measures sum exactly to the baseline market-based "
    "electricity emissions; only the split between measures depends on the "
    "stack order (D-13). Under the location-based basis the contract "
    "abates nothing.",
    "The MACC is a cost-ranked screening, not an optimiser. It ignores "
    "interactions beyond the stack, barriers and non-financial costs "
    "(Kesicki and Ekins). Negative-cost measures are often not done because "
    "of hidden and attention costs.",
    "Key analyst assumptions to test in Phase 4: Meas_LED_LightingShare, "
    "Meas_LED_Coverage, Meas_LED_SavingRate, Meas_VSD_MotorShare, "
    "Meas_VSD_Coverage, Meas_VSD_SavingRate, Meas_PV_Size, "
    "Meas_Fleet_ChargerCapex, Meas_Fleet_MaintSaving, Meas_RC_GOPrice "
    "(producer-side value), Meas_HP_FullLoadHours (PBL subsidy reference "
    "case) and the JRC 2009 heat split.",
    "The annuity-method reconciliation is an internal check with tolerance "
    "Const_AnnuityTolRel, not a client output.",
)

EXCLUSIONS = (
    "Scope 3 is excluded: no official sector-level Scope 3 intensity for "
    "Belgian chemicals was found and no synthetic figure is used (D-13).",
    "Process emissions are excluded from Scope 1 (D-11).",
    "Non-energy (feedstock) use is excluded from energy (D-05).",
)


class _N(object):
    def __init__(self, ws, cells, styles):
        self.ws, self.cells, self.styles, self.r = ws, cells, styles, 4

    def section(self, title):
        self.r += 2
        sec = self.styles.get("section")
        self.cells.text(self.ws, self.r, LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            self.cells.blank(self.ws, self.r, c, sec)

    def para(self, text):
        words, cur, lines = text.split(), "", []
        for w in words:
            if cur and len(cur) + 1 + len(w) > WRAP:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w) if cur else w
        if cur:
            lines.append(cur)
        for ln in lines:
            self.r += 1
            self.cells.text(self.ws, self.r, LABEL_COL, ln,
                            self.styles.get("label"))


def ets2_projection_line(inputs, sources):
    ids = [r.id for r in inputs if r.id.startswith(PROJ_PREFIX)]
    if not ids:
        return NO_PROJECTION
    ds = ""
    for s in sources:
        if s.id == "Src_ETS2Projection":
            ds = s.dataset
    return ("Official ETS2 price projection captured as data for Phase 4: "
            + ", ".join(ids) + " (" + ds + "); it is not used in Phase 2 "
            "calculations (D-30).")


def carbon_notes(sources):
    return (
        "NGFS carbon prices are model shadow prices (marginal abatement "
        "costs), not market prices.",
        "Scenario mapping (D-26): Low = Current Policies, Central = Nationally "
        "Determined Contributions (NDCs), High = Net Zero 2050.",
        "Pinned model and region (D-27): " + ngfs_model_text(sources) + ".",
        "Conversion route (D-41): US$2010 divided by the 2010 average US "
        "dollars per euro (Eurostat), then multiplied by euro-area HICP 2025 "
        "over 2010. Limitation: it assumes the US dollar kept its 2010 real "
        "value against the euro; a US-CPI route would give about 1.31, so "
        "prices about 25% higher (an indicative analyst estimate, not a sourced "
        "input; see docs/DATA_LOG.md), a candidate Phase 4 sensitivity.",
        "EUA anchor (D-29): " + EUA_NOTE + ".",
        NGFS_ATTRIBUTION, NGFS_MODIFIED, NGFS_LICENCE,
    )


def build_notes(wb, styles, cells, dataset, cfg):
    ws = wb.add_worksheet("Notes")
    setup_sheet(ws, SheetKind.NOTES, freeze_row=4, freeze_col=1)
    write_title_band(
        cells, styles, ws, "Notes",
        "Method notes, limitations and exclusions (full method and version "
        "log in Phase 5)", "Prose refers to input ids rather than repeating "
        "figures", LAST_COL)
    n = _N(ws, cells, styles)
    cells.text(ws, 4, LABEL_COL, disclaimer_text(dataset.sources),
               styles.get("label"))
    n.section("About this model")
    for t in ABOUT:
        n.para(t)
    n.section("Data scope and conventions")
    for t in CONVENTIONS:
        n.para(t)
    n.section("Limitations")
    for t in LIMITATIONS:
        n.para(t)
    n.para(legal_status_note(dataset.inputs))
    n.section("Exclusions")
    for t in EXCLUSIONS:
        n.para(t)
    n.section("Carbon price notes")
    n.para(ets2_projection_line(dataset.inputs, dataset.sources))
    if not dataset.synthetic:
        for t in carbon_notes(dataset.sources):
            n.para(t)
    n.section("Transcribed inputs (D-14 route 3)")
    for r in dataset.inputs:
        if (r.note.startswith("Transcribed")
                or r.rationale.startswith(("Transcribed",
                                           "Unverified transcription"))):
            n.para("%s: %s" % (r.id, r.description))
    if not dataset.synthetic:
        n.section(MEASURES_TITLE)
        for t in MEASURES_METHOD:
            n.para(t)
    n.section("Version log")
    n.para("Phase 2: real cited data, Baseline, Rates, Carbon and Notes")
    if not dataset.synthetic:
        n.para("Phase 3: Measures engine (six measures, stack, NPV/IRR/"
               "payback/abatement cost, LB/MB and scenario selectors) and "
               "MACC")
    return None
