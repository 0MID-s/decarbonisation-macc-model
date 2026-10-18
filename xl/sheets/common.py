"""Shared sheet helpers: title band, legend row, synthetic banner (D-02, D-12)."""
from xl.styles import Styles

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
