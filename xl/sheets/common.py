"""Shared sheet helpers: title band, legend row, synthetic banner (D-02, D-12)."""
import re

from xl.styles import Styles

def get_or_add(wb, name):
    """Return the worksheet called name, creating it if it does not exist yet.
    build.py pre-creates sheets in tab order; builders then fetch them."""
    for ws in wb.worksheets():
        if ws.get_name() == name:
            return ws
    return wb.add_worksheet(name)


FICTITIOUS_NOTE = ("Maison Veritas is a fictitious company. All figures are "
                   "built from cited public data or labelled analyst "
                   "assumptions.")
BASELINE_SOURCE_IDS = ("Src_EurostatSBS", "Src_EurostatEnergyBalance",
                       "Src_EurostatAirAccounts")
_CODE = re.compile(r"\(([a-z][a-z0-9_]*)\)")

SYNTHETIC_TEXT = ("SYNTHETIC FIXTURE DATA - not real figures, "
                  "for pipeline testing only")

LEGEND_ITEMS = (
    ("Input", "legend_input"),
    ("Formula", "legend_calc"),
    ("Link to other sheet", "legend_link"),
    ("Selector / switch", "legend_selector"),
    ("Analyst assumption", "legend_assumption"),
    ("Check OK", "legend_ok"),
    ("Check ERROR", "legend_err"),
)

_UNIT_ROLES = {
    "EUR/kWh": "price4",
    "year": "year",
    "%": "pct",
    "EUR": "eur",
    "tCO2e": "tco2e",
    "EUR/tCO2e": "eur_per_t",
    "factor": "factor",
    "TJ": "dec3",
    "MWh": "mwh",
    "GJ": "count",
    "EUR m": "eur_m",
    "enterprises": "count",
    "persons": "count",
    "vehicles": "count",
    "km/yr": "count",
    "h/yr": "count",
    "kWh/yr per unit": "dec2",
    "allowances (million)": "count",
    "months": "count",
    "gCO2e/kWh": "dec2",
    "gCO2/kWh": "dec2",
    "gCO2/km": "dec2",
    "kgCO2e/kWh": "dec5",
    "tCO2e/MWh": "dec5",
    "tCO2/MWh": "dec5",
    "kgCO2e/l": "dec5",
    "EUR/MWh": "eur2",
    "EUR/tCO2": "eur2",
    "US$2010/tCO2": "dec2",
    "index": "dec3",
    "USD per EUR": "dec5",
    "per cent": "dec2",
    "M EUR/MW": "factor",
    "M EUR/MWp": "factor",
    "EUR/kW": "eur",
    "EUR/kWp": "eur",
    "EUR/MW/yr": "eur",
    "EUR/MWp/yr": "eur",
    "EUR/kW/yr": "eur2",
    "EUR/kWp/yr": "eur2",
    "EUR per unit": "eur2",
    "EUR per vehicle": "eur",
    "kWh/kWp/yr": "dec2",
    "kWh/km": "dec3",
    "COP": "dec2",
    "years": "count",
    "MW": "dec2",
    "flag (1/0)": "count",
    "multiple": "dec2",
    "MWh/TJ": "factor",
    "GJ/MWh": "factor",
    "kWh/MWh": "count",
    "(t/MWh)/(g/kWh)": "factor",
    "fraction per per cent": "factor",
    "kg/t": "count",
    "g/kg": "count",
    "factor (mega per kilo)": "count",
    "MW/kW": "factor",
    "abs tolerance": "general",
    "km per 100 km": "count",
    "EUR/1000 l": "eur2",
    "EUR/l": "price4",
    "EUR/GO": "eur2",
    "PJ": "dec2",
    "1000 m2/MWp": "dec3",
    "m2/kWp": "dec3",
    "kWp": "count",
    "EUR/km": "price4",
    "per thousand": "factor",
    "kW/MW": "count",
    "MWh/GO": "factor",
    "fraction": "factor",
    "abs tolerance (currency units)": "general",
    "abs tolerance (currency units per tonne)": "general",
    "tCO2e per measure": "tco2e",
}


def num_role_for_unit(unit):
    # type: (str) -> str
    return _UNIT_ROLES.get(unit, "factor")


def write_title_band(cells, styles, ws, title, purpose, note, last_col):
    cells.text(ws, 0, 1, title, styles.get("title"))
    for c in range(2, last_col + 1):
        cells.blank(ws, 0, c, styles.get("title"))
    cells.text(ws, 1, 1, purpose, styles.get("purpose"))
    cells.text(ws, 2, 1, note, styles.get("note"))


def write_legend_row(cells, styles, ws, row):
    cells.text(ws, row, 1, "Colour key:", styles.get("label"))
    for i, (text, role) in enumerate(LEGEND_ITEMS):
        cells.text(ws, row, 2 + i, text, styles.get(role))


def write_synthetic_banner(cells, styles, ws, row, last_col):
    cells.text(ws, row, 1, SYNTHETIC_TEXT, styles.get("synthetic_banner"))
    for c in range(2, last_col + 1):
        cells.blank(ws, row, c, styles.get("synthetic_banner"))


def disclaimer_text(sources):
    """D-33 disclaimer assembled from the Sources register (BASE-06).

    Falls back to FICTITIOUS_NOTE when the baseline Eurostat sources are not
    all present (synthetic fixtures).
    """
    by_id = dict((s.id, s) for s in sources)
    if not all(i in by_id for i in BASELINE_SOURCE_IDS):
        return FICTITIOUS_NOTE
    codes, dates = [], []
    for i in BASELINE_SOURCE_IDS:
        m = _CODE.search(by_id[i].dataset)
        if not m:
            return FICTITIOUS_NOTE
        codes.append(m.group(1))
        dates.append(by_id[i].retrieved)
    return ("\u2018Maison Veritas\u2019 is a fictitious company. Its baseline "
            "is a representative Belgian NACE C20 mid-sized manufacturer "
            "derived from official Eurostat statistics (%s, retrieved %s). "
            "It does not represent any real company."
            % (", ".join(codes), max(dates).isoformat()))
