"""Notes shell: scope, conventions, limitations, exclusions (plan 02-10).

Prose carries no figures that are also input values; it refers to input ids.
Lists are generated from the dataset (transcribed inputs, ETS2 projection).
"""
import re
from typing import Dict, List

from config.build_config import EXCEL_RECORD, VERSION_LOG
from config.disclosure import CORRECTIONS
from config.schema import Status
from xl.layout import LABEL_COL, setup_sheet
from xl.sheets.carbon import (
    EUA_NOTE, NGFS_ATTRIBUTION, NGFS_LICENCE, NGFS_MODIFIED,
    ngfs_model_text)
from xl.sheets.common import get_or_add, disclaimer_text, write_title_band
from xl.styles import SheetKind

LAST_COL = 8
WRAP = 130
PROJ_PREFIX = "Carbon_ETS2_Proj_"
NO_PROJECTION = (
    "ETS2 price projection: Not captured: no official projection located on "
    "allowlisted sources (see RESEARCH 3.11). Carbon prices are applied to "
    "each exposure channel on the Exposure sheet (D-30).")

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
    "addressable by the six decarbonisation measures (D-06).",
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
    "The DEA indirect-investment difference (heat pump minus boiler) is "
    "excluded from capex and shown as a memo line on the Measures sheet "
    "(D-06).",
    "No size or illiquidity premium is added to the discount rate; the "
    "MACC rank-stability block on the Sensitivity sheet re-ranks the "
    "measures at several real hurdle rates instead (D-20).",
    "Discount-rate basis: the Euros column of Damodaran's waccEurope.xls "
    "(January 2026 update, read from the official file with a read-only "
    "parser after a macro check, D-42). That column embeds 1.5% expected euro "
    "inflation while the model deflates with the ECB target held in "
    "Fin_InflationLongRun, an inflation mismatch that makes the real rate "
    "slightly lower.",
    "The NGFS region OECD & EU (R5) is used as the EU proxy (D-27).",
    "Alternative conversion route (D-41): a US-CPI route would give a factor "
    "(input Carbon_NGFS_AltRouteFactor) instead of the Eurostat route factor, so carbon prices "
    "about a quarter higher (an indicative analyst estimate, not a sourced "
    "input; see docs/DATA_LOG.md); tested as the NGFS currency conversion "
    "route driver of the tornado on the Sensitivity sheet.",
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
    "Electricity valuation (an analyst assumption): every electricity change "
    "is valued at the full Eurostat X_VAT band price (BL_ElecPrice), which "
    "includes network charges and levies. PV output is treated as fully "
    "self-consumed (a check keeps it below the remaining load) with no "
    "export value, so the PV saving is an upper bound: self-consumed solar "
    "avoids the energy part of the bill but only part of the network "
    "charges and levies. The fleet's charging electricity is costed at the "
    "same full price, so its saving is fuel avoided less charging at that "
    "price.",
    "Gas basis of the electricity factors: the market-based residual mix "
    "(EF_ResidualMB, AIB) is CO2 only, while the location-based grid factor "
    "(EF_GridLB, EEA) and the fuel factors are CO2e. Market-based "
    "electricity tonnes therefore exclude non-CO2 gases, so the two bases "
    "and the MACC rankings under them are not on an identical gas basis; "
    "the gap is not quantified in the model.",
    "Carbon value at the selected NGFS scenario is a shadow-price lens, not "
    "cash. Cash carbon costs by channel are on the Exposure sheet (D-16).",
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
    "Chart technique: the MACC is an area chart on a date axis whose "
    "positions are cumulative tCO2e, so bar widths equal annual abatement. "
    "The axis is set to Date axis (time scale) in the file; a build step "
    "does this because the charting library always writes automatic.",
    "MACC eligibility (one rule for the flag and the bar width): a measure "
    "is shown on the MACC only if both its present value of abated tonnes "
    "(the cost denominator) and its average annual abated tonnes (the bar "
    "width) on the selected basis are above zero (M_*_Eligible). Otherwise "
    "it stays in the ranked table as n/a, ranks last and has zero width, so "
    "no bar can have a negative width whatever the inputs.",
    "Key analyst assumptions behind the measure results: "
    "Meas_LED_LightingShare, "
    "Meas_LED_Coverage, Meas_LED_SavingRate, Meas_VSD_MotorShare, "
    "Meas_VSD_Coverage, Meas_VSD_SavingRate, Meas_PV_Size, "
    "Meas_Fleet_ChargerCapex, Meas_Fleet_MaintSaving, Meas_RC_GOPrice "
    "(producer-side value), Meas_HP_FullLoadHours (PBL subsidy reference "
    "case) and the JRC 2009 heat split.",
    "The annuity-method reconciliation is an internal check, not a client "
    "output: equivalent annual cost divided by equivalent annual tonnes, "
    "both annualised with one capital recovery factor over the operating "
    "years, recomputed from the yearly rows. It equals the levelised cost "
    "before subsidy for any profile, within Const_AnnuityTolAbs and "
    "Const_AnnuityTolRel.",
)

EXPOSURE_TITLE = "Carbon exposure and sensitivity method (Phase 4)"
EXPOSURE_METHOD = (
    "Cash carbon price paths are market-anchored: the observed 2025 EUA "
    "average (Carbon_EUA_Avg2025) is the starting point, converges linearly "
    "to the selected NGFS scenario path by the convergence years "
    "(Carbon_ETS1_ConvYear, Carbon_ETS2_ConvYear), and follows NGFS "
    "afterwards.",
    "ETS2 cost = ETS2-scope tonnes x ETS2 price. It is zero before "
    "Carbon_ETS2_StartYear. Fuel suppliers are the regulated parties and "
    "are assumed to pass 100% of the cost on to the firm (an analyst "
    "assumption).",
    "Electricity pass-through = purchased MWh x MEF x PTR x (ETS1 price - "
    "embedded 2025 EUA). Subtracting the EUA already embedded in the 2025 "
    "power price makes it a change versus what the baseline already paid, "
    "so it can be negative under the Low scenario.",
    "The renewable electricity contract does not reduce cash carbon cost: "
    "the power price is set by the marginal plant whichever certificates "
    "the firm buys. It affects only the market-based emissions inventory "
    "and the internal carbon price lens.",
    "The direct ETS1 toggle (Sel_DirectETS) moves stationary fuel from "
    "ETS2 to ETS1; the two are mutually exclusive by construction (both price rows "
    "come from one On/Off switch) and a bookkeeping check confirms the price "
    "rows never overlap. Automated tests, not the in-sheet check, exercise "
    "the Off and On branches.",
    "The internal carbon price is a non-cash decision lens on Scope 1 + 2 "
    "of the selected basis. It is never added to a cash total.",
    "Discounting uses 2026 as year 0 over the exposure window "
    "(Expo_LastYear), the same discount factors as the Measures sheet.",
    "The sensitivity metric is the carbon-inclusive portfolio NPV: "
    "financial NPV plus the discounted avoided cash carbon cost.",
    "Sensitivity grids are closed-form formulas built from gross carbon "
    "present values, so there are no Data Tables and they work in Excel "
    "for the web.",
    "The tornado ranks one-at-a-time swings of the main drivers; rank "
    "stability re-ranks the measures at several hurdle rates.",
)
EXPOSURE_LIMITATIONS = (
    "PTR 1.0 is the upper end of the literature (Fabra and Reguant; Sijm "
    "et al.); the range 0.6 to 1.0 is tested.",
    "Industrial retail tariffs are assumed to pass the wholesale carbon "
    "change through one-for-one on top of a flat real tariff, a "
    "simplification.",
    "ETS2 prices CO2 while the DESNZ factors are CO2e, and the diesel "
    "factor includes an average biofuel blend; the effect is under 1%.",
    "The DEA efficiency figures are assumed to be on a lower heating value "
    "(LHV) basis.",
    "The Annex III exclusivity of ETS1 and ETS2 was read from Commission "
    "material, not from the primary legal text.",
    "Central reaches the NGFS price by 2030, a steep 2028-2030 rise above "
    "market forecasts; change the convergence years to test.",
    "No ETS2 price floor is modelled.",
    "Free-allocation benchmarks are not modelled (a share input, default "
    "0).",
    "The CBAM screen is as of 2026-10-25.",
)


METHOD_CHOICES = (
    "Representative firm: the baseline is built from official Eurostat "
    "sector statistics for Belgian NACE C20 and scaled to one mid-sized "
    "firm using the Base_* inputs. It is not a real company, so company-"
    "specific data can replace the Base_* inputs without changing any "
    "formula.",
    "NGFS anchoring: the cash carbon price starts at the observed EUA "
    "average (Carbon_EUA_Avg2025) and converges linearly to the NGFS path "
    "by the convergence-year inputs (Carbon_ETS1_ConvYear, "
    "Carbon_ETS2_ConvYear). Low, Central and High map to Current Policies, "
    "NDCs and Net Zero 2050. Anchoring keeps the early years consistent "
    "with the market while the scenarios still differ in the long run.",
    "Levelised abatement cost: the cost of a measure is the present value "
    "of its net cost divided by the present value of its abated tonnes, so "
    "measures with different lives and cash profiles are comparable on one "
    "number. The annuity form (equivalent annual cost / equivalent annual "
    "tonnes, Const_AnnuityTolRel) is an internal check of the same figure, "
    "recomputed from the yearly rows.",
    "Pass-through netting: the electricity carbon cost reaches the firm "
    "through the power price at the pass-through rate Pass_PTR and is "
    "netted against the embedded EUA already in the baseline price. The "
    "renewable electricity contract therefore changes the emissions "
    "inventory but saves no cash carbon cost.",
    "Closed-form sensitivities: net present value is linear in the price "
    "deltas, so each grid cell is a plain formula on gross carbon present "
    "values. No Data Tables are used, the grid centre equals the base "
    "case, and the grids work in Excel for the web.",
    "Location-based and market-based treatment: both bases are calculated "
    "from the same activity data and a selector picks one. The two are "
    "never added. Under the location-based basis the renewable contract "
    "abates nothing, because the grid factor does not change when "
    "certificates are bought.",
)
LIMITATIONS_P5 = (
    "Marginal abatement cost curves are criticised in Kesicki, F. and "
    "Ekins, P. (2012), Climate Policy 12(2), 219-236, "
    "doi:10.1080/14693062.2011.582347. The critiques that apply here are: "
    "the curve has no interactions between measures beyond the stack "
    "order; it is static, with no intertemporal dynamics; it ignores "
    "non-financial barriers and ancillary benefits; and uncertainty is not "
    "shown in the bar widths, while the assumptions behind a bar can be "
    "opaque.",
    "Scope: all cash flows are pre-tax and ex-VAT. Corporate tax, "
    "depreciation allowances and subsidies other than the Meas_*_Subsidy "
    "inputs are not modelled.",
    "Independence: apart from the electricity stack order, measures are "
    "treated as independent of each other. Real projects interact "
    "through shared loads, shared roofs and shared budgets, which this "
    "model does not capture.",
    "The firm is a representative firm built from sector statistics, not a "
    "real company, so results show the method and the order of magnitude, "
    "not a prediction for any single site.",
    "NGFS carbon prices are model shadow prices, not market forecasts. "
    "They show what a scenario needs to reach its emissions path, not what "
    "the EU ETS will clear at.",
    "Some sensitivities are not tested in the sheet: the lifetime and "
    "heat-share cases are note-only values calculated in Python at build "
    "and are not live cells.",
)
CORRECTIONS_TITLE = "Disclosure and Dashboard corrections"
DASHBOARD_CORRECTION = (
    "Dashboard wording: the cost-of-not-acting tile and the exposure-by-"
    "scenario chart use Expo_CumBAU_Sel and the Expo_Cum* series, which are "
    "cumulative and undiscounted; the discounted figure (Expo_DiscBAU_Sel) "
    "is shown as a sub-line. Context decisions D-07 and D-08 called this "
    "series discounted; the labels follow the workbook.")


def _eur(x):
    return "%s EUR %s" % ("minus" if x < 0 else "plus",
                          format(abs(round(x)), ","))


def python_verified_note(inputs):
    """One paragraph of note-only sensitivities, computed in Python at
    build time (text, not formulas)."""
    from checkmodel.baseline_reference import model_values
    from checkmodel.sensitivity_reference import untested_note_values
    o = untested_note_values(inputs)
    v = model_values(inputs)
    lp, hs = v["Sens_Note_LifePct"] * 100, v["Sens_Note_HPShareDelta"] * 100
    return (
        "Python-verified at build for the default inputs, not a live cell "
        "and not updated when inputs change: portfolio NPV incl. carbon "
        "changes by %s / %s when LED lifetime moves by minus %g%% / plus %g%%, by "
        "%s / %s when VSD lifetime moves by minus %g%% / plus %g%%, and by %s / %s "
        "when the low-temperature heat share moves by minus %g / plus %g percentage "
        "points." % (
            _eur(o["led_life_low"]), _eur(o["led_life_high"]), lp, lp,
            _eur(o["vsd_life_low"]), _eur(o["vsd_life_high"]), lp, lp,
            _eur(o["hp_share_low"]), _eur(o["hp_share_high"]), hs, hs))


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
    return ("Official ETS2 price projection captured as data: "
            + ", ".join(ids) + " (" + ds + "); it is not used in the model "
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
        "value against the euro; a US-CPI route would give the factor in input Carbon_NGFS_AltRouteFactor, so "
        "prices about 25% higher (an indicative analyst estimate, not a sourced "
        "input; see docs/DATA_LOG.md), tested as the NGFS currency "
        "conversion route driver of the tornado on the Sensitivity sheet.",
        "EUA anchor (D-29): " + EUA_NOTE + ".",
        NGFS_ATTRIBUTION, NGFS_MODIFIED, NGFS_LICENCE,
    )


def build_notes(wb, styles, cells, dataset, cfg):
    ws = get_or_add(wb, "Notes")
    setup_sheet(ws, SheetKind.NOTES, freeze_row=4, freeze_col=1)
    write_title_band(
        cells, styles, ws, "Notes",
        "Method choices, limitations, corrections, version log and Excel "
        "verification record", "Prose refers to input ids rather than repeating "
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
        n.section(EXPOSURE_TITLE)
        for t in EXPOSURE_METHOD:
            n.para(t)
        n.section("Limitations (Phase 4)")
        for t in EXPOSURE_LIMITATIONS:
            n.para(t)
        n.para(python_verified_note(dataset.inputs))
        n.section("Method choices")
        for t in METHOD_CHOICES:
            n.para(t)
        n.section("Limitations (Phase 5)")
        for t in LIMITATIONS_P5:
            n.para(t)
        n.section(CORRECTIONS_TITLE)
        n.r += 1
        for c, h in zip((LABEL_COL, LABEL_COL + 1, LABEL_COL + 2),
                        ("Hypothesis", "Official finding", "Action")):
            cells.text(ws, n.r, c, h, styles.get("header"))
        for row in CORRECTIONS:
            n.r += 1
            for c, t in zip((LABEL_COL, LABEL_COL + 1, LABEL_COL + 2), row):
                cells.text(ws, n.r, c, t, styles.get("label"))
        n.para(DASHBOARD_CORRECTION)
    n.section("Version log")
    n.r += 1
    for c, h in zip((LABEL_COL, LABEL_COL + 1, LABEL_COL + 2),
                    ("Version", "Date", "Change")):
        cells.text(ws, n.r, c, h, styles.get("header"))
    for v, d, ch in VERSION_LOG:
        n.r += 1
        for c, t in zip((LABEL_COL, LABEL_COL + 1, LABEL_COL + 2), (v, d, ch)):
            cells.text(ws, n.r, c, t, styles.get("label"))
    n.section("Excel verification record")
    for t in EXCEL_RECORD:
        n.para(t)
    return None
