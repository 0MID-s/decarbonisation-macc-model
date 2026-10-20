"""Carbon sheet: NGFS paths converted to EUR 2025, EUA anchor, ETS2 (plan 02-13).

Every cell is a live formula on named Inputs; cached values come from
checkmodel.carbon_reference and checkmodel.rates_reference (D-26, D-27, D-29,
D-30, D-41, D-44).
"""
from dataclasses import dataclass
from typing import Dict, Tuple

from checkmodel.baseline_reference import excel_match_approx, model_values
from checkmodel.carbon_reference import (
    SCENARIOS, carbon_paths, eua_gaps, eur_route_factor)
from checkmodel.rates_reference import restate_eur2025
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_for_year,
    col_letter, setup_sheet)
from xl.sheets.common import num_role_for_unit, write_title_band
from xl.styles import SheetKind, apply_check_format

LAST_COL = TIMELINE_LAST_COL
HDR_ROW = 4  # zero-based; Excel row 5
GRID_FIRST = 3  # column D
GRID_MAX = 9  # D..L
UNIT_BASE_YEAR = 2010

NGFS_ATTRIBUTION = (
    "Source: NGFS Phase 5 Scenario Explorer, hosted by IIASA "
    "(https://data.ene.iiasa.ac.at/ngfs/). (c) NGFS Phase 5 Scenario Explorer.")
NGFS_MODIFIED = (
    "Values modified: converted from US$2010 to EUR 2025 (2010 average "
    "exchange rate, then euro-area HICP) and interpolated linearly to annual "
    "values. No endorsement by NGFS or IIASA is implied.")
NGFS_LICENCE = (
    "Licence: adapted CC BY 4.0, https://data.ene.iiasa.ac.at/ngfs/#/license")
LIMIT_NOTE = (
    "Assumes the US dollar kept its 2010 real value against the euro. A "
    "US-CPI route would give about 1.31, so prices about 25% higher; "
    "candidate Phase 4 sensitivity (D-41)")
ANCHOR_NOTE = (
    "NGFS point years are fixed cells on Inputs; changing First model year "
    "shifts the timeline and the paths re-interpolate to the new years")
EUA_NOTE = (
    "EUA 2025 average in nominal 2025 euros = EUR 2025 prices; scenarios are "
    "not floored or blended to it (D-29); any short-run blending is a "
    "Phase 4 decision")
SCOPE_IDS = ("Carbon_ETS2_Scope_Gas", "Carbon_ETS2_Scope_LPG",
             "Carbon_ETS2_Scope_Naphtha", "Carbon_ETS2_Scope_OtherFuels",
             "Carbon_ETS2_Scope_FleetDiesel", "Carbon_ETS2_Scope_Elec",
             "Carbon_ETS2_Scope_Heat")


@dataclass(frozen=True)
class CarbonLayout:
    rows: Tuple[Tuple[str, int], ...]
    path_names: Tuple[str, ...]


def ngfs_model_text(sources):
    for s in sources:
        if s.id == "Src_NGFSPhaseV":
            d = s.dataset
            return d.split("Price|Carbon, ", 1)[1] if "Price|Carbon, " in d else d
    raise ValueError("Src_NGFSPhaseV missing")


def build_carbon(wb, styles, cells, dataset, cfg, inputs_layout):
    by_id = {r.id: r for r in dataset.inputs}
    v = model_values(dataset.inputs)
    paths = carbon_paths(dataset.inputs)
    gaps = eua_gaps(dataset.inputs)
    srows = dict(inputs_layout.series_model_rows)
    yrows = dict(inputs_layout.series_year_rows)
    unit_year = by_id["Carbon_NGFS_CP"].price_basis.year
    if unit_year != UNIT_BASE_YEAR:
        raise ValueError("NGFS unit base year must be %d, got %r"
                         % (UNIT_BASE_YEAR, unit_year))
    factor = eur_route_factor(v, unit_year)
    model_text = ngfs_model_text(dataset.sources)

    ws = wb.add_worksheet("Carbon")
    setup_sheet(ws, SheetKind.CALC, freeze_row=5, freeze_col=3,
                header_last_row=HDR_ROW)
    write_title_band(
        cells, styles, ws, "Carbon",
        "NGFS Phase V carbon price paths converted to EUR 2025, the observed "
        "EUA anchor and ETS2 parameters",
        "Low = Current Policies, Central = NDCs, High = Net Zero 2050 (D-26). "
        "Conversion (Eurostat route, D-41): US$2010 / USD-per-EUR 2010 x HICP "
        "2025 / HICP 2010. Linear interpolation between NGFS points; flat "
        "after the last point", LAST_COL)
    hdr = styles.get("header")
    cells.text(ws, HDR_ROW, LABEL_COL, "Item", hdr)
    cells.text(ws, HDR_ROW, UNIT_COL, "Unit", hdr)
    yr = styles.get("header_year", "year")
    c0 = TIMELINE_FIRST_COL
    cells.formula(ws, HDR_ROW, c0, "=Time_FirstYear", yr,
                  value=cfg.timeline_start)
    for k in range(1, len(cfg.timeline_years)):
        cells.formula(ws, HDR_ROW, c0 + k,
                      "=%s%d+1" % (col_letter(c0 + k - 1), HDR_ROW + 1),
                      yr, value=cfg.timeline_start + k)

    sec = styles.get("section")
    label, unit_s, note = (styles.get("label"), styles.get("unit"),
                           styles.get("note"))
    rows = []

    def band(r, title):
        cells.text(ws, r, LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, LAST_COL + 1):
            cells.blank(ws, r, c, sec)

    def line(r, text, unit):
        cells.text(ws, r, LABEL_COL, text, label)
        cells.text(ws, r, UNIT_COL, unit, unit_s)

    # --- attribution (D-44)
    r = 5
    for t in (NGFS_ATTRIBUTION, NGFS_MODIFIED, NGFS_LICENCE):
        cells.text(ws, r, LABEL_COL, t, note)
        r += 1
    r += 1
    # --- conversion block (D-41)
    band(r, "Conversion from US$2010 to EUR 2025 (Eurostat route, D-41)")
    r += 1
    line(r, "US dollars per euro, 2010 average", "USD per EUR")
    cells.formula(ws, r, GRID_FIRST, "=Fin_FX_USDperEUR_2010",
                  styles.get("link", "dec5"), value=v["Fin_FX_USDperEUR_2010"])
    r += 1
    line(r, "EUR 2010 per US$2010", "factor")
    cells.formula(ws, r, GRID_FIRST, "=1/Fin_FX_USDperEUR_2010",
                  styles.get("calc", "dec5"),
                  value=1.0 / v["Fin_FX_USDperEUR_2010"])
    cells.define_name("Carb_EUR2010perUSD", "=Carbon!$D$%d" % (r + 1))
    rows.append(("Carb_EUR2010perUSD", r))
    r += 1
    line(r, "Euro-area HICP 2025 / HICP 2010", "factor")
    cells.formula(ws, r, GRID_FIRST, "=Fin_HICP_EA_2025/Fin_HICP_EA_2010",
                  styles.get("calc", "dec5"),
                  value=v["Fin_HICP_EA_2025"] / v["Fin_HICP_EA_2010"])
    cells.define_name("Carb_HICPRatio2010", "=Carbon!$D$%d" % (r + 1))
    rows.append(("Carb_HICPRatio2010", r))
    r += 1
    line(r, "Combined factor: EUR 2025 per US$2010", "factor")
    cells.formula(ws, r, GRID_FIRST,
                  "=Carb_EUR2010perUSD*Carb_HICPRatio2010",
                  styles.get("calc", "dec5"), value=factor)
    cells.define_name("Carb_USDtoEUR2025", "=Carbon!$D$%d" % (r + 1))
    rows.append(("Carb_USDtoEUR2025", r))
    cells.text(ws, r, GRID_FIRST + 1, LIMIT_NOTE, note)
    r += 1
    cells.text(ws, r, LABEL_COL, ANCHOR_NOTE, note)
    r += 2

    # --- scenarios
    hdr_ref = HDR_ROW + 1
    path_names = []
    for key, tier, name in SCENARIOS:
        ays, avs, annual = paths[key]
        n = len(ays)
        if n > GRID_MAX:
            raise ValueError("more than %d anchors for %s" % (GRID_MAX, key))
        last = GRID_FIRST + n - 1
        band(r, "%s: %s, %s" % (tier, name, model_text))
        r += 1
        r_yr, r_us, r_e10, r_e25 = r, r + 1, r + 2, r + 3
        r_eff, r_idx, r_val = r + 4, r + 5, r + 6

        def rng(row, a=GRID_FIRST, b=last):
            return "$%s$%d:$%s$%d" % (col_letter(a), row + 1,
                                      col_letter(b), row + 1)

        line(r_yr, "NGFS anchor years", "year")
        line(r_us, "NGFS published (US$2010)", "US$2010/tCO2")
        line(r_e10, "/ FX 2010 = EUR 2010", "EUR/tCO2")
        line(r_e25, "x HICP ratio = EUR 2025 anchors", "EUR/tCO2")
        line(r_eff, "Effective year (capped at last anchor)", "year")
        line(r_idx, "Anchor index (last anchor <= effective year)", "index")
        line(r_val, "%s price, EUR 2025 (interpolated)" % tier, "EUR/tCO2")
        for i in range(n):
            col = GRID_FIRST + i
            cl = col_letter(col)
            if i == 0:
                cells.formula(ws, r_yr, col, "=Carbon_NGFS_Y0Year",
                              styles.get("link", "year"), value=ays[0])
                cells.formula(ws, r_us, col, "=Carbon_NGFS_%s_Y0" % key,
                              styles.get("link", "dec2"),
                              value=v["Carbon_NGFS_%s_Y0" % key])
            else:
                y = ays[i]
                ycol = col_letter(col_for_year(y))
                cells.formula(
                    ws, r_yr, col,
                    "=Inputs!$%s$%d" % (ycol, yrows["Carbon_NGFS_" + key] + 1),
                    styles.get("link", "year"), value=y)
                ser = dict(by_id["Carbon_NGFS_" + key].series)
                cells.formula(
                    ws, r_us, col,
                    "=Inputs!$%s$%d" % (ycol, srows["Carbon_NGFS_" + key] + 1),
                    styles.get("link", "dec2"), value=ser[y] * 1.0)
            us_val = (v["Carbon_NGFS_%s_Y0" % key] if i == 0 else
                      dict(by_id["Carbon_NGFS_" + key].series)[ays[i]])
            cells.formula(ws, r_e10, col, "=%s%d*Carb_EUR2010perUSD"
                          % (cl, r_us + 1), styles.get("calc", "eur2"),
                          value=us_val * (1.0 / v["Fin_FX_USDperEUR_2010"]))
            cells.formula(ws, r_e25, col, "=%s%d*Carb_HICPRatio2010"
                          % (cl, r_e10 + 1), styles.get("calc", "eur2"),
                          value=avs[i])
        y_all, y_but_last = rng(r_yr), rng(r_yr, GRID_FIRST, last - 1)
        e_all = rng(r_e25)
        for k, y in enumerate(cfg.timeline_years):
            col = col_for_year(y)
            cl = col_letter(col)
            eff = min(y, ays[-1])
            kk = excel_match_approx(eff, ays[:-1])
            cells.formula(ws, r_eff, col, "=MIN(%s$%d,MAX(%s))"
                          % (cl, hdr_ref, y_all),
                          styles.get("calc", "year"), value=eff)
            cells.formula(ws, r_idx, col, "=MATCH(%s%d,%s,1)"
                          % (cl, r_eff + 1, y_but_last),
                          styles.get("index"), value=kk)
            ix = "%s%d" % (cl, r_idx + 1)
            ef = "%s%d" % (cl, r_eff + 1)
            f = ("=INDEX({e},{k})+(INDEX({e},{k}+1)-INDEX({e},{k}))"
                 "*({ef}-INDEX({y},{k}))/(INDEX({y},{k}+1)-INDEX({y},{k}))"
                 .format(e=e_all, y=y_all, k=ix, ef=ef))
            cells.formula(ws, r_val, col, f, styles.get("calc", "eur2"),
                          value=annual[k])
        pname = "Path_Carbon_%s" % key
        cells.define_name(pname, "=Carbon!$%s$%d:$%s$%d" % (
            col_letter(TIMELINE_FIRST_COL), r_val + 1,
            col_letter(TIMELINE_LAST_COL), r_val + 1))
        path_names.append(pname)
        rows.append((pname, r_val))
        rows.append(("anchor_eur2025_" + key, r_e25))
        r_chk = r_val + 1
        line(r_chk, "Anchor-year check (ascending; first anchor before "
             "first model year)", "check")
        conds = ["%s%d<%s%d" % (col_letter(GRID_FIRST + i), r_yr + 1,
                                col_letter(GRID_FIRST + i + 1), r_yr + 1)
                 for i in range(n - 1)]
        conds.append("%s%d<$%s$%d" % (col_letter(GRID_FIRST), r_yr + 1,
                                      col_letter(TIMELINE_FIRST_COL), hdr_ref))
        cells.formula(ws, r_chk, GRID_FIRST,
                      '=IF(AND(%s),"OK","ERROR")' % ",".join(conds),
                      styles.get("calc", "general"), value="OK")
        apply_check_format(ws, styles, r_chk, GRID_FIRST, r_chk, GRID_FIRST)
        cname = "Carb_Check_Anchors_" + key
        cells.define_name(cname, "=Carbon!$%s$%d" % (col_letter(GRID_FIRST),
                                                     r_chk + 1))
        rows.append((cname, r_chk))
        r = r_chk + 2

    # --- EUA anchor (D-29)
    band(r, "Observed EUA anchor (D-29)")
    r += 1
    line(r, "EUA auction average 2025", "EUR/tCO2")
    cells.formula(ws, r, GRID_FIRST, "=Carbon_EUA_Avg2025",
                  styles.get("link", "eur2"), value=v["Carbon_EUA_Avg2025"])
    r_eua = r
    r += 1
    for key, tier, name in SCENARIOS:
        r_anchor = dict(rows)["anchor_eur2025_" + key]
        line(r, "Gap: EUA 2025 minus %s NGFS 2025 (EUR 2025)" % tier,
             "EUR/tCO2")
        cells.formula(ws, r, GRID_FIRST, "=Carbon_EUA_Avg2025-$D$%d"
                      % (r_anchor + 1), styles.get("calc", "eur2"),
                      value=gaps[key])
        rows.append(("eua_gap_" + key, r))
        r += 1
    cells.text(ws, r, LABEL_COL, EUA_NOTE, note)
    r += 2

    # --- ETS2 block (D-30)
    band(r, "ETS2 parameters (D-30)")
    r += 1
    items = [("Carbon_ETS2_StartYear", None),
             ("Carbon_ETS2_StabPrice", None),
             ("Carbon_ETS2_StabPrice_EUR2025", 2020),
             ("Carbon_ETS2_StabMonths", None),
             ("Carbon_ETS2_StabRelease", None)]
    items += [(i, None) for i in SCOPE_IDS]
    for iid, yr_ in items:
        base = iid.replace("_EUR2025", "")
        rec = by_id[base]
        text = rec.description
        if yr_:
            text = "ETS2 stability threshold restated to EUR 2025 (Rates sheet)"
            val = restate_eur2025(v, base, yr_)
            role = "eur2"
            unit = "EUR/tCO2"
        else:
            val = v[base]
            role = num_role_for_unit(rec.model_unit)
            unit = rec.model_unit
        line(r, text, unit)
        cells.formula(ws, r, GRID_FIRST, "=" + iid,
                      styles.get("link", role), value=val)
        rows.append((iid, r))
        r += 1
    return CarbonLayout(tuple(rows), tuple(path_names))
