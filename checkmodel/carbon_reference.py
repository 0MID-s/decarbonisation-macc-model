"""NGFS carbon price conversion and annual interpolation (plan 02-12).

Stdlib + config + checkmodel only. All figures are read from config.

Route (D-41): EUR 2025 = US$2010 / FX_2010 (USD per EUR) x HICP_2025 / HICP_2010.
The same factor applies to every NGFS point.

Excel formulas the Carbon sheet (02-13) writes, per scenario and year:
  effective year  =MIN(year, MAX(anchor_years))
  index k         =MATCH(effective, anchor_years_but_last, 1)
  value           =INDEX(v,k)+(INDEX(v,k+1)-INDEX(v,k))*(eff-INDEX(y,k))
                       /(INDEX(y,k+1)-INDEX(y,k))
"""
from typing import Dict, List, Sequence, Tuple

from checkmodel.baseline_reference import excel_match_approx, model_values
from config.build_config import BUILD

SCENARIOS = (("CP", "Low", "Current Policies"),
             ("NDC", "Central", "Nationally Determined Contributions (NDCs)"),
             ("NZ50", "High", "Net Zero 2050"))


def eur_route_factor(v, unit_year):
    # type: (Dict[str, float], int) -> float
    keys = ("Fin_HICP_EA_2025", "Fin_HICP_EA_%d" % unit_year,
            "Fin_FX_USDperEUR_%d" % unit_year)
    for k in keys:
        if k not in v:
            raise ValueError("missing input %s" % k)
    return (v[keys[0]] / v[keys[1]]) / v[keys[2]]


def usd_to_eur2025(x, factor):
    # type: (float, float) -> float
    return x * factor


def interp_annual(anchor_years, anchor_values, years):
    # type: (Sequence[int], Sequence[float], Sequence[int]) -> List[float]
    ay = list(anchor_years)
    av = list(anchor_values)
    years = list(years)
    if len(ay) < 2 or len(ay) != len(av):
        raise ValueError("need at least 2 anchors with matching values")
    if any(b <= a for a, b in zip(ay, ay[1:])):
        raise ValueError("anchor years must be strictly ascending")
    if ay[0] >= years[0]:
        raise ValueError("first anchor must be before the first timeline year")
    out = []
    for y in years:
        ye = min(y, ay[-1])
        k = excel_match_approx(ye, ay[:-1])
        y0, y1 = ay[k - 1], ay[k]
        v0, v1 = av[k - 1], av[k]
        out.append(v0 + (v1 - v0) * (ye - y0) / (y1 - y0))
    return out


def carbon_paths(inputs):
    # type: (Sequence) -> Dict[str, Tuple[Tuple[int, ...], Tuple[float, ...], Tuple[float, ...]]]
    by_id = {r.id: r for r in inputs}
    v = model_values(inputs)
    y0 = int(v["Carbon_NGFS_Y0Year"])
    unit_year = by_id["Carbon_NGFS_CP"].price_basis.year
    f = eur_route_factor(v, unit_year)
    out = {}
    for key, _tier, _label in SCENARIOS:
        pts = by_id["Carbon_NGFS_" + key].series
        ays = (y0,) + tuple(y for y, _ in pts)
        avs = ((v["Carbon_NGFS_%s_Y0" % key],) + tuple(x for _, x in pts))
        avs = tuple(usd_to_eur2025(x, f) for x in avs)
        annual = tuple(interp_annual(ays, avs, BUILD.timeline_years))
        out[key] = (ays, avs, annual)
    return out


def eua_gaps(inputs):
    # type: (Sequence) -> Dict[str, float]
    v = model_values(inputs)
    return {k: v["Carbon_EUA_Avg2025"] - p[1][0]
            for k, p in carbon_paths(inputs).items()}
