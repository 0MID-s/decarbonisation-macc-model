"""Record helpers shared by the config section modules (stdlib + schema only)."""
from config.schema import (
    InputRecord, Kind, NOT_APPLICABLE, PriceBasis, Status,  # noqa: F401
)

EUR2025_NOM = PriceBasis("EUR", 2025, "nominal")
EUR2025_REAL = PriceBasis("EUR", 2025, "real")
NA = NOT_APPLICABLE


def scalar(id_, section, description, value, unit, conv, model_unit, basis,
           source_id, status, rationale="", note=""):
    # type: (...) -> InputRecord
    return InputRecord(
        id=id_, section=section, description=description,
        published_value=value, published_unit=unit, conversion_ref=conv,
        model_unit=model_unit, price_basis=basis, source_id=source_id,
        status=status, rationale=rationale, note=note, kind=Kind.SCALAR,
    )


def series(id_, section, description, points, unit, conv, model_unit, basis,
           source_id, status, rationale="", note=""):
    # type: (...) -> InputRecord
    return InputRecord(
        id=id_, section=section, description=description,
        published_value=None, published_unit=unit, conversion_ref=conv,
        model_unit=model_unit, price_basis=basis, source_id=source_id,
        status=status, rationale=rationale, note=note, kind=Kind.SERIES,
        series=tuple(points),
    )
