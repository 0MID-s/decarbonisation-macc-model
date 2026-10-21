"""Lists sheet: structural dropdown sources, exposed as defined names (D-01)."""
from dataclasses import dataclass

from xl.layout import setup_sheet
from xl.sheets.common import write_synthetic_banner, write_title_band
from xl.styles import SheetKind

SCENARIOS = ("Low", "Central", "High")
BASES = ("Location-based", "Market-based")
SCENARIO_REF = "Lists!$B$6:$B$8"
BASIS_REF = "Lists!$D$6:$D$7"
TIERS = ("Do first", "Next", "Later")


@dataclass(frozen=True)
class ListsLayout:
    scenario_ref: str
    basis_ref: str


def build_lists(wb, styles, cells, dataset, cfg):
    ws = wb.add_worksheet("Lists")
    setup_sheet(ws, SheetKind.LISTS, freeze_row=5, freeze_col=2,
                header_last_row=4)
    write_title_band(
        cells, styles, ws, "Lists",
        "Structural lists that feed dropdown selectors (labels, not data)",
        "", 5)
    if dataset.synthetic:
        write_synthetic_banner(cells, styles, ws, 3, 5)
    cells.text(ws, 4, 1, "Scenario", styles.get("header"))
    cells.text(ws, 4, 3, "Emissions basis", styles.get("header"))
    for i, v in enumerate(SCENARIOS):
        cells.text(ws, 5 + i, 1, v, styles.get("label"))
    for i, v in enumerate(BASES):
        cells.text(ws, 5 + i, 3, v, styles.get("label"))
    cells.text(ws, 4, 5, "MACC tier", styles.get("header"))
    for i, v in enumerate(TIERS):
        cells.text(ws, 5 + i, 5, v, styles.get("label"))
    for n, ref in (("Tier_First", "$F$6"), ("Tier_Next", "$F$7"),
                   ("Tier_Later", "$F$8"), ("List_Tier", "$F$6:$F$8")):
        cells.define_name(n, "=Lists!" + ref)
    cells.define_name("List_Scenario", "=" + SCENARIO_REF)
    cells.define_name("List_Basis", "=" + BASIS_REF)
    return ListsLayout(SCENARIO_REF, BASIS_REF)
