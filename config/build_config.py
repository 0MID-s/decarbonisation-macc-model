"""Fixed build settings (D-16: fixed created timestamp for reproducible output)."""
import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildConfig:
    title: str
    subject: str
    author: str
    company: str
    version: str
    created: datetime.datetime
    timeline_start: int
    timeline_end: int
    macc_technique: str
    dropdown_source: str

    @property
    def timeline_years(self):
        return tuple(range(self.timeline_start, self.timeline_end + 1))


BUILD = BuildConfig(
    title="Maison Veritas - Decarbonisation Business Case and Carbon Cost Exposure Model",
    subject="Illustrative model, fictitious company, real public data",
    author="Model generator",
    company="Maison Veritas (fictitious)",
    version="0.1.0-phase1",
    created=datetime.datetime(2026, 10, 17, 0, 0, 0),
    timeline_start=2026,
    timeline_end=2055,
    macc_technique="A",
    dropdown_source="name",
)
