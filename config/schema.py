"""Provenance contracts: frozen records for sources and inputs (D-10, D-11, D-12)."""
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

SECTIONS = ("Baseline", "Energy prices", "Emission factors", "Carbon prices",
            "Finance", "Measures", "Constants",
            "Carbon exposure (Phase 4)", "Sensitivity (Phase 4)")

# Underscore required so ids are valid Excel defined names and never look like
# cell references such as ETS2 or LB1.
ID_PATTERN = r"^[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]+$"
# Tokenizer float() quirk: these parse as numbers, so they are not usable ids.
RESERVED_IDS = frozenset(["inf", "nan", "infinity", "true", "false"])


class Status(Enum):
    SOURCED = "sourced"
    ASSUMPTION = "assumption"
    PLACEHOLDER = "placeholder"

    @property
    def label(self):
        return {"sourced": "Sourced", "assumption": "Analyst assumption",
                "placeholder": "Placeholder"}[self.value]


class Kind(Enum):
    SCALAR = "scalar"
    SERIES = "series"


@dataclass(frozen=True)
class PriceBasis:
    currency: str
    year: Optional[int]
    real_nominal: str

    @property
    def label(self):
        if self.currency == "n/a":
            return "n/a (non-monetary)"
        return "%s %s %s" % (self.currency, self.year, self.real_nominal)


NOT_APPLICABLE = PriceBasis("n/a", None, "n/a")


@dataclass(frozen=True)
class Source:
    id: str
    publisher: str
    dataset: str
    url: str
    edition: str
    retrieved: datetime.date
    licence_note: str


@dataclass(frozen=True)
class InputRecord:
    id: str
    section: str
    description: str
    published_value: Optional[float]
    published_unit: str
    conversion_ref: Optional[str]
    model_unit: str
    price_basis: PriceBasis
    source_id: Optional[str]
    status: Status
    rationale: str
    note: str = ""
    kind: Kind = Kind.SCALAR
    series: Tuple[Tuple[int, float], ...] = ()


class ProvenanceError(ValueError):
    def __init__(self, problems):
        self.problems = tuple(problems)
        ValueError.__init__(self, "\n".join(self.problems))

    def __str__(self):
        return "\n".join(self.problems)
