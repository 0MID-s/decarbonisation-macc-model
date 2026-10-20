"""Notes shell: scope, conventions, limitations, exclusions (plan 02-10).

Prose carries no figures that are also input values; it refers to input ids.
Lists are generated from the dataset (transcribed inputs, ETS2 projection).
"""
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
ETS2_UNVERIFIED = (
    "Legal parameters whose text the user supplied from EUR-Lex on "
    "2026-10-20 are shown as Sourced (ETS2 start year 2028, price-stability "
    "threshold, months and release volume, the price-multiple trigger "
    "and release, read in Dir. (EU) 2023/959 as enacted, later amendments "
    "(2026) not checked; and the EU ETS1 thermal threshold, read in the "
    "original 2003 Annex I wording, consolidated text not read). "
    "The enacted ETS2 start year, "
    "the fuel scope flags, and the chemical-sector NACE coverage of the "
    "energy balance sector remain analyst assumptions pending verification: "
    "no legal text was supplied for them. The log is in docs/DATA_LOG.md, "
    "Legal texts (WR-02 re-read and plan 02-16).")
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
    n.para(ETS2_UNVERIFIED)
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
    n.section("Version log")
    n.para("Phase 2: real cited data, Baseline, Rates, Carbon and Notes")
    return None
