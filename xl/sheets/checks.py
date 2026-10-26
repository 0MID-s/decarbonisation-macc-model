"""Checks sheet (plan 05-03, QA-03, D-14 to D-18).

Every existing owner check is linked exactly once, wrapped in IFERROR so that a
broken input shows FALSE (and the master "ERROR"), never an error value. No
check is recomputed here. Group flags and counts feed Chk_Master and
Chk_FailCount. Plan 05-04 adds the Dashboard-dependent checks to groups 5 and 6 (CUSTOM).

Cached values (WR-01): every status cell caches the reference value from
checkmodel.outputs_reference.check_inventory; group flags, counts, the master
and the fail count are derived from those, never written as literals.
"""
from checkmodel.outputs_reference import compute_outputs
from xl.layout import col_letter, setup_sheet
from xl.selector import direct_ets_state, selector_state
from xl.sheets.common import get_or_add, write_title_band
from xl.sheets.exposure import CHECK_NAMES as EXPO_CHECKS
from xl.sheets.sensitivity import CHECK_NAMES as SENS_CHECKS
from xl.styles import SheetKind, apply_bool_check_format, apply_check_format

SHEET = "Checks"
LAST_COL = 7
PURPOSE = ("Every model check in one place. Each status is a link to the "
           "check on its owner sheet; nothing is recalculated here.")
NOTE = ("TRUE = the check passes. The master flag is OK only when every group "
        "flag is TRUE. Click Go to to see the check where it is calculated.")
MEASURE_KEYS = ("LED", "VSD", "HP", "PV", "Fleet", "RC")
LB_MB_TEXT = (
    "LB and MB are never added together. This is a build-time guarantee: "
    "qa/lint.py rejects any formula that combines LB- and MB-tagged ranges, "
    "so the build fails otherwise. It cannot be tested by a live formula.")
TEXT_CHECKS = ("Carb_Check_Anchors_CP", "Carb_Check_Anchors_NDC",
               "Carb_Check_Anchors_NZ50", "BL_Check_Carriers",
               "BL_Check_Ratio")

DESC = {
    "M_Check_StackNonNeg": "Check: no stack step goes below zero",
    "M_Check_ElecReductionsCap":
        "Check: LED + VSD + PV never exceed baseline electricity",
    "M_Check_PVSelfConsumed":
        "Check: PV output never exceeds electricity left to purchase",
    "M_Check_ContractCap":
        "Check: contract never covers more than residual purchases",
    "M_Check_GasCap": "Check: gas after heat pump is not negative",
    "M_Check_DieselCap": "Check: diesel after fleet is not negative",
    "M_Check_PVPeakBelowLoad":
        "Check: PV peak output (MW) is below the average electrical load",
    "BL_Check_Carriers": "Check: baseline fuel carriers add up to the total",
    "BL_Check_Ratio": "Check: baseline Scope 2 ratio is consistent",
    "Carb_Check_Anchors_CP":
        "Check: Current Policies carbon path hits its anchor values",
    "Carb_Check_Anchors_NDC":
        "Check: NDC carbon path hits its anchor values",
    "Carb_Check_Anchors_NZ50":
        "Check: Net Zero 2050 carbon path hits its anchor values",
    "Carb_Check_ConvYears": "Check: convergence years are not before the "
                            "anchor / start year",
    "Expo_Check_ETS2ZeroBeforeStart":
        "Check: ETS2 cost is zero before the ETS2 start year",
    "Expo_Check_ETSExclusive": "Bookkeeping check (true by construction): "
                               "stationary fuel price rows never overlap",
    "Expo_Check_CashIsChannels": "Bookkeeping check: each cash total equals "
                                 "its ETS2, direct ETS1 and pass-through rows",
    "Expo_Check_ConvYears": "Check: convergence years are valid",
    "Expo_Check_MeasuresReconcile":
        "Check: the six per-measure rows sum to the selected-scenario "
        "avoided cost",
    "Expo_Check_ContractZero":
        "Check: the renewable contract saves no cash carbon cost",
    "Expo_Check_BridgeSums":
        "Check: BAU minus the six measure bars equals the cost after acting",
    "Sens_Check_Reconcile":
        "Check: portfolio NPV equals Measures portfolio NPV plus discounted "
        "avoided carbon cost",
    "Sens_Check_CarbonPV":
        "Check: gross carbon PVs less the embedded part equal the PV of "
        "avoided carbon cost",
    "Sens_Check_GridCentre":
        "Check: grid centre equals the base portfolio NPV",
    "Sens_Check_RateCentre":
        "Check: rate-strip centre equals the base portfolio NPV "
        "(independent discount-factor path)",
    "Sens_Check_Torn":
        "Check: tornado ranks form a complete 1..n ordering and the bars "
        "bracket the base",
    "Sens_Check_LevBase":
        "Check: base-rate levelised cost equals the Measures levelised cost "
        "for every eligible measure",
}
SUFFIX_DESC = {
    "NPVMemo": "Check: SUMPRODUCT NPV equals CF0 + NPV() memo",
    "BreakEven": "Check: break-even price equals levelised cost",
    "Annuity": "Check: annuity cost agrees with levelised cost before subsidy",
    "NPVatZero": "Check: NPV at r = 0 equals the plain sum",
    "NPVatIRR": "Check: NPV at the IRR is about zero",
}
MEASURE_NAMES = {"LED": "LED lighting", "VSD": "Variable-speed drives",
                 "HP": "Heat pump", "PV": "Rooftop PV",
                 "Fleet": "Electric fleet", "RC": "Renewable contract"}
SELECTORS = (
    ("Chk_Sel_Scenario", "Sel_Scenario", "List_Scenario",
     "Check: the carbon price scenario selector holds a valid choice"),
    ("Chk_Sel_Basis", "Sel_Basis", "List_Basis",
     "Check: the emissions basis selector holds a valid choice"),
    ("Chk_Sel_DirectETS", "Sel_DirectETS", "List_OnOff",
     "Check: the direct ETS1 switch holds a valid choice"),
)


# Dashboard-dependent checks (plan 05-04): name -> (formula, description,
# name of the Dashboard cell the row links to). They are calculated here.
CUSTOM = {
    # Like for like (CR-01): the MACC leaves out a measure with no abatement
    # (M_<K>_Eligible = 0), so the MACC width total is reconciled with the
    # eligible measures only, and the tile with the net sum of all six.
    "Chk_TileVsMACC": (
        "=IFERROR(AND(ABS(SUMPRODUCT(MACC_Data_Abatement,MACC_Data_Eligible)"
        "-MACC_TotalAbatement)<=COUNT(MACC_Chart_Width)*Const_MACCRoundTol,"
        "ABS(SUM(MACC_Data_Abatement)-Dash_AbatedSel)<=Const_CheckTolerance),"
        "FALSE)",
        "Abatement of the measures on the MACC equals the MACC width total "
        "(widths rounded to whole tonnes; tolerance Const_MACCRoundTol per "
        "measure), and the Dashboard tile equals the net sum of all six "
        "measures, including any with negative abatement that the MACC "
        "leaves out", "Dash_AbatedSel"),
    "Chk_ShareInRange": (
        "=IFERROR(AND(Dash_Share>=0,Dash_Share<=1),FALSE)",
        "Share of Scope 1+2 abated is between 0 and 1", "Dash_Share"),
    "Chk_BasisExact": (
        "=IFERROR(OR(Dash_AbatedSel=M_Total_tLB,Dash_AbatedSel=M_Total_tMB),"
        "FALSE)",
        "Bookkeeping check: the selected-basis abatement equals exactly the "
        "LB total or the MB total, never their sum (companion to the "
        "build-time lint guarantee)", "Dash_AbatedSel"),
}


def _describe(name):
    if name in CUSTOM:
        return CUSTOM[name][1]
    if name in DESC:
        return DESC[name]
    parts = name.split("_")  # M_Check_<K>_<suffix>
    if len(parts) == 4 and parts[0] == "M" and parts[3] in SUFFIX_DESC:
        return "%s (%s)" % (SUFFIX_DESC[parts[3]],
                            MEASURE_NAMES.get(parts[2], parts[2]))
    raise KeyError("no description for check %s" % name)


def _groups(measure_checks):
    mk = set(measure_checks)
    by_suffix = {}
    caps = []
    for n in measure_checks:
        p = n.split("_")
        if len(p) == 4 and p[2] in MEASURE_KEYS:
            by_suffix.setdefault(p[3], []).append(n)
        else:
            caps.append(n)

    def per_measure(suffix):
        names = ["M_Check_%s_%s" % (k, suffix) for k in MEASURE_KEYS]
        missing = [n for n in names if n not in mk]
        if missing:
            raise ValueError("Measures checks missing: %s" % missing)
        return names

    return [
        ("1. Balance and caps",
         caps + ["BL_Check_Carriers", "BL_Check_Ratio",
                 "Carb_Check_Anchors_CP", "Carb_Check_Anchors_NDC",
                 "Carb_Check_Anchors_NZ50", "Carb_Check_ConvYears"]),
        ("2. NPV at r = 0",
         per_measure("NPVatZero") + per_measure("NPVMemo")),
        ("3. NPV at IRR = 0", per_measure("NPVatIRR")),
        ("4. Sensitivity centre = base",
         ["Sens_Check_GridCentre", "Sens_Check_RateCentre",
          "Sens_Check_LevBase", "Sens_Check_Reconcile",
          "Sens_Check_CarbonPV", "Sens_Check_Torn"]),
        ("5. Abatement-method reconciliation",
         per_measure("Annuity") + per_measure("BreakEven")
         + ["Chk_TileVsMACC", "Chk_ShareInRange"]),
        ("6. LB/MB never summed", ["Chk_BasisExact"]),
        ("7. Exposure integrity", list(EXPO_CHECKS)),
        ("8. Selector validity", [s[0] for s in SELECTORS]),
    ]


def build_checks(wb, styles, cells, dataset, cfg, out):
    measure_checks = list(out["measures"].check_names)
    groups = _groups(measure_checks)
    listed = [n for _, ns in groups if ns for n in ns
              if not n.startswith("Chk_")]
    for n in listed:
        if n not in cells.names:
            raise ValueError("Checks: owner check %s is not a defined name" % n)
    if sorted(listed) != sorted(set(listed)):
        raise ValueError("Checks: a check is linked more than once")
    if set(SENS_CHECKS) != set(n for n in listed if n.startswith("Sens_")):
        raise ValueError("Checks: sensitivity inventory mismatch")
    for n in measure_checks:
        if n not in listed:
            raise ValueError("Checks: measure check %s not grouped" % n)
    basis, scenario = selector_state(dataset)
    ref = compute_outputs(dataset.inputs, basis, scenario,
                          direct_ets_state(dataset))
    rows_all = [n for _, ns in groups for n in ns]
    if sorted(rows_all) != sorted(ref.checks):
        raise ValueError("Checks: reference inventory mismatch: %s" % sorted(
            set(rows_all) ^ set(ref.checks)))
    vals = ref.checks

    ws = get_or_add(wb, SHEET)
    setup_sheet(ws, SheetKind.CHECKS, freeze_row=8, freeze_col=0)
    write_title_band(cells, styles, ws, "Checks", PURPOSE, NOTE, LAST_COL)
    for c, w in ((0, 2.0), (1, 34.0), (2, 78.0), (3, 14.0), (4, 24.0),
                 (5, 16.0), (6, 12.0), (7, 14.0)):
        ws.set_column(c, c, w)
    hdr = styles.get("header")
    sec = styles.get("section")
    lbl = styles.get("label")
    text = styles.get("text")
    flag = styles.get("flag")
    link = styles.get("link", "general")
    calc = styles.get("calc", "general")
    nav = styles.get("nav_link")

    # row plan (0-based): master rows 4 and 5, header row 7, groups from 8
    r_master, r_fail, r_hdr = 4, 5, 7
    r = r_hdr + 1
    plan = []
    for title, names in groups:
        head = r
        r += 1
        rows = []
        for n in names:
            rows.append((n, r))
            r += 1
        if title.startswith("6."):
            rows.append((None, r))  # text row, after the Boolean rows
            r += 1
        plan.append((title, head, rows))

    for c, t in enumerate(("Group", "Check", "Status", "Source", "Owner sheet",
                           "Group OK", "Failing")):
        cells.text(ws, r_hdr, 1 + c, t, hdr)

    flag_cells, count_cells = [], []
    for (title, head, rows), (_, names) in zip(plan, groups):
        cells.text(ws, head, 1, title, sec)
        for c in range(2, 6):
            cells.blank(ws, head, c, sec)
        if names:
            bool_rows = [row for n, row in rows if n]
            first, last = bool_rows[0] + 1, bool_rows[-1] + 1
            rng = "$D$%d:$D$%d" % (first, last)
            g_ok = all(vals[n] for n in names)
            g_fail = sum(1 for n in names if not vals[n])
            cells.formula(ws, head, 6, "=AND(%s)" % rng, flag, value=g_ok)
            cells.formula(ws, head, 7, "=COUNTIF(%s,FALSE)" % rng, flag,
                          value=g_fail)
            apply_bool_check_format(ws, styles, head, 6, head, 6)
            flag_cells.append("G%d" % (head + 1))
            count_cells.append("H%d" % (head + 1))
        else:
            cells.blank(ws, head, 6, sec)
            cells.blank(ws, head, 7, sec)
        for name, row in rows:
            if name is None:
                cells.text(ws, row, 2, LB_MB_TEXT, text)
                cells.text(ws, row, 3, "Enforced at build", lbl)
                cells.text(ws, row, 5, "Build (qa/lint.py)", lbl)
                ws.set_row(row, 38)
                continue
            cells.text(ws, row, 2, _describe(name) if not name.startswith(
                "Chk_Sel_") else dict((s[0], s[3]) for s in SELECTORS)[name],
                       text)
            if name in CUSTOM:
                f, _desc, src = CUSTOM[name]
                sheet, cell = cells.target_of(src)
                cells.formula(ws, row, 3, f, calc, value=vals[name])
                cells.define_name(name, "=%s!$D$%d" % (SHEET, row + 1))
            elif name.startswith("Chk_Sel_"):
                sel, lst = next((s[1], s[2]) for s in SELECTORS
                                if s[0] == name)
                f = "=IFERROR(ISNUMBER(MATCH(%s,%s,0)),FALSE)" % (sel, lst)
                sheet, cell = cells.target_of(sel)
                cells.formula(ws, row, 3, f, calc, value=vals[name])
                cells.define_name(name, "=%s!$D$%d" % (SHEET, row + 1))
            else:
                f = ('=IFERROR(%s="OK",FALSE)' if name in TEXT_CHECKS
                     else "=IFERROR(%s,FALSE)") % name
                sheet, cell = cells.target_of(name)
                cells.formula(ws, row, 3, f, link, value=vals[name])
            apply_bool_check_format(ws, styles, row, 3, row, 3)
            cells.internal_link(ws, row, 4, sheet, cell,
                                "Go to %s!%s" % (sheet, cell), nav,
                                "Open the check on its owner sheet")
            cells.text(ws, row, 5, sheet, lbl)

    cells.text(ws, r_master, 1, "Master check", lbl)
    cells.formula(ws, r_master, 3,
                  '=IF(AND(%s),"OK","ERROR")' % ",".join(flag_cells), flag,
                  value=ref.chk_master)
    cells.define_name("Chk_Master", "=%s!$D$%d" % (SHEET, r_master + 1))
    apply_check_format(ws, styles, r_master, 3, r_master, 3)
    cells.text(ws, r_fail, 1, "Failing checks", lbl)
    cells.formula(ws, r_fail, 3, "=SUM(%s)" % ",".join(count_cells), flag,
                  value=ref.chk_fail_count)
    cells.define_name("Chk_FailCount", "=%s!$D$%d" % (SHEET, r_fail + 1))
    return {"master_cell": "D%d" % (r_master + 1),
            "fail_cell": "D%d" % (r_fail + 1),
            "groups": [(t, h, [n for n, _ in rows if n])
                       for t, h, rows in plan],
            "group_flags": flag_cells, "group_counts": count_cells,
            "last_row": r}
