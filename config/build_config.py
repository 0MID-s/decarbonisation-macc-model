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
    author="0MID-s",
    company="Maison Veritas (fictitious)",
    version="1.0.0",
    created=datetime.datetime(2026, 10, 25, 0, 0, 0),
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
    ("1.0.0", "2026-10-25",
     "Outputs, hardening and interview pack: Dashboard, Disclosure, Checks, "
     "ReadMe, finished Cover and Notes"),
)

# Excel verification record shown on Notes. Only what has happened so far
# (docs/EXCEL_CHECKS.md, docs/SPIKE_RESULTS.md). Plan 05-10 replaces these
# lines after GATE-B.
EXCEL_RECORD = (
    "GATE-A passed on Excel for Mac desktop on 2026-10-18 (MACC technique A "
    "chosen).",
    "Phase 3 scripted recalculation in Excel for Mac 16.114 on 2026-10-21: "
    "every formula cell compared with the cached reference values, no "
    "mismatches and no error values.",
    "Phase 4 scripted recalculation in Excel for Mac 16.114.1 on 2026-10-25: "
    "12 selector states, no mismatches and no error values (re-run after the "
    "code-review fixes, same result).",
    "Phase 5 GATE-B: pending.",
    "Excel for the web: not verified.",
)
