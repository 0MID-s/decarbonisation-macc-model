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
    version="0.2.0-phase2",
    created=datetime.datetime(2026, 10, 17, 0, 0, 0),
    timeline_start=2026,
    timeline_end=2055,
    macc_technique="A",
    dropdown_source="name",
)

# Version log source for the ReadMe (D-13): (version, ISO date, change).
VERSION_LOG = (
    ("0.1.0-phase1", "2026-10-18",
     "Phase 1: foundation, security controls and rendering spikes"),
    ("0.2.0-phase2", "2026-10-20",
     "Phase 2: real data, company baseline, rates and carbon price paths"),
    ("0.3.0-phase3", "2026-10-25",
     "Phase 3: measures engine, basis selector and MACC"),
    ("0.4.0-phase4", "2026-10-25",
     "Phase 4: carbon cost exposure, scenarios and sensitivity"),
)
