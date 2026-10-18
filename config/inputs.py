"""Input register. Structural constants only in Phase 1; real inputs in Phase 2."""
from typing import Tuple

from config.schema import NOT_APPLICABLE, InputRecord, Status

INPUTS = (
    InputRecord(
        id="Const_None", section="Constants",
        description="Identity conversion factor (no unit change)",
        published_value=1.0, published_unit="factor", conversion_ref=None,
        model_unit="factor", price_basis=NOT_APPLICABLE, source_id=None,
        status=Status.ASSUMPTION,
        rationale=("Identity factor used where the published unit already "
                   "equals the model unit, so every Model value keeps one "
                   "formula pattern (D-11)."),
    ),
    InputRecord(
        id="Time_FirstYear", section="Constants",
        description="First model year (timeline column 1)",
        published_value=2026.0, published_unit="year", conversion_ref=None,
        model_unit="year", price_basis=NOT_APPLICABLE, source_id=None,
        status=Status.ASSUMPTION,
        rationale=("Analyst choice: appraisal timeline 2026-2055 starts in "
                   "the current year."),
    ),
)  # type: Tuple[InputRecord, ...]
