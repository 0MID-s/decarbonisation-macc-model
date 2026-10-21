"""Single entry point: validates, builds, lints, scans and reads back the workbook.

Usage: .venv/bin/python build.py [--target main] [--dataset config|fixtures] [--out PATH]

Do NOT run this with ``python -I``: isolated mode drops the script directory
from sys.path and the project packages (config, xl, qa) cannot be imported.

Exit codes: 0 ok, 2 provenance, 3 lint or unsafe cell, 4 security scan,
5 read-back. On any failure nothing is written to the output path.
This module is the composition root: it is the only production module that
imports tests (lazily, for the synthetic fixtures dataset).
"""
import argparse
import hashlib
import io
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple

import xlsxwriter

from config.build_config import BUILD
from config.schema import InputRecord, ProvenanceError, Source
from config.validate import validate_provenance
from qa.lint import LintError, lint_or_raise
from qa.readback import ReadbackError, verify_workbook
from qa.scan import ScanError, part_names, scan_or_raise
from xl.selector import selector_state  # noqa: F401 (re-export)
from xl.cells import CellWriter, FormulaRecord, UnsafeCellError
from xl.sheets.baseline import build_baseline
from xl.sheets.carbon import build_carbon
from xl.sheets.cover import build_cover
from xl.sheets.inputs import build_inputs
from xl.sheets.lists import build_lists
from xl.sheets.macc import build_macc
from xl.sheets.measures import build_measures
from xl.sheets.notes import build_notes
from xl.sheets.rates import build_rates
from xl.sheets.sources import build_sources
from xl.sheets.spike import build_spike
from xl.postprocess import patch_date_axis
from xl.styles import Styles

OPTIONS = {
    "in_memory": True,
    "strings_to_formulas": False,
    "strings_to_urls": False,
    "strings_to_numbers": False,
    "default_format_properties": {"font_name": "Arial", "font_size": 10},
}


@dataclass(frozen=True)
class Dataset:
    name: str
    sources: Tuple[Source, ...]
    inputs: Tuple[InputRecord, ...]
    measures: Tuple[Tuple[str, int, float], ...]
    synthetic: bool
    reference_price: Optional[float] = None
    # Test-only (basis, scenario); None = deliverable default (T-03-24).
    selector_state: Optional[Tuple[str, str]] = None


def load_dataset(name):
    # type: (str) -> Dataset
    if name == "config":
        from config.inputs import INPUTS
        from config.sources import SOURCES
        return Dataset("config", tuple(SOURCES), tuple(INPUTS), (), False)
    if name == "fixtures":
        from tests.fixtures import synthetic  # lazy: fixtures only
        return Dataset("fixtures", tuple(synthetic.SYNTHETIC_SOURCES),
                       tuple(synthetic.SYNTHETIC_INPUTS),
                       tuple(synthetic.SYNTHETIC_MEASURES), True,
                       synthetic.SYNTHETIC_REFERENCE_PRICE)
    raise ValueError("unknown dataset: %r" % (name,))


MAIN_SHEETS_BASE = ("Cover", "Inputs", "Sources", "Lists")
REAL_DATA_SHEETS = ("Baseline", "Rates", "Carbon", "Measures", "MACC")
NOTES_SHEETS = ("Notes",)


def main_sheets(dataset):
    return (MAIN_SHEETS_BASE + (() if dataset.synthetic else REAL_DATA_SHEETS)
            + NOTES_SHEETS)


def _build_main(wb, styles, cells, dataset, cfg):
    build_cover(wb, styles, cells, dataset, cfg, list(main_sheets(dataset)))
    inputs = build_inputs(wb, styles, cells, dataset, cfg)
    build_sources(wb, styles, cells, dataset, cfg)
    lists = build_lists(wb, styles, cells, dataset, cfg)
    out = {"inputs": inputs, "lists": lists}
    if not dataset.synthetic:
        out["baseline"] = build_baseline(wb, styles, cells, dataset, cfg,
                                         inputs)
        out["rates"] = build_rates(wb, styles, cells, dataset, cfg)
        out["carbon"] = build_carbon(wb, styles, cells, dataset, cfg, inputs)
        out["measures"] = build_measures(wb, styles, cells, dataset, cfg, out)
        out["macc"] = build_macc(wb, styles, cells, dataset, cfg, out)
    out["notes"] = build_notes(wb, styles, cells, dataset, cfg)
    return out


TARGETS = {}  # type: Dict[str, Tuple[str, Callable]]


def register_target(name, default_out, builder):
    TARGETS[name] = (default_out, builder)


DELIVERABLE = os.path.join("dist", "maison_veritas.xlsx")
SYNTHETIC_MAIN_OUT = os.path.join("dist", "maison_veritas_SYNTHETIC.xlsx")
register_target("main", DELIVERABLE, _build_main)
register_target("spike", os.path.join("dist", "spike_macc.xlsx"), build_spike)


def build_bytes(target, dataset, extra_builders=()):
    # type: (str, Dataset, Sequence[Callable]) -> Tuple[bytes, Tuple[FormulaRecord, ...]]
    # The layout grid (xl/layout.py) is fixed to BUILD at import time, so the
    # build config is not a parameter: another timeline would disagree with
    # col_for_year (WR-09).
    cfg = BUILD
    validate_provenance(dataset.sources, dataset.inputs, cfg.timeline_years)
    builder = TARGETS[target][1]
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, OPTIONS)
    wb.set_properties({
        "title": cfg.title,
        "subject": cfg.subject,
        "author": cfg.author,
        "company": cfg.company,
        "comments": "Version " + cfg.version,
        "created": cfg.created,
    })
    styles = Styles(wb)
    cells = CellWriter(wb)
    layouts = dict(builder(wb, styles, cells, dataset, cfg))
    for extra in extra_builders:
        extra(wb, styles, cells)
    wb.close()
    # XlsxWriter hard-codes c:auto=1 on date axes; force a true date axis on
    # the one technique A MACC chart (see xl/postprocess.py).
    data = patch_date_axis(buf.getvalue(), expected_charts=1)
    registry = cells.registry
    for rec in registry:
        lint_or_raise(rec.text, rec.sheet, cells.tags)
    scan_or_raise(data)
    layouts["names"] = dict(cells.names)
    problems = verify_workbook(data, registry, layouts)
    if problems:
        raise ReadbackError(problems)
    return data, registry


def _write_atomic(out, data):
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the workbook offline.")
    ap.add_argument("--target", choices=sorted(TARGETS), default="main")
    ap.add_argument("--dataset", choices=("config", "fixtures"), default="config")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = args.out or TARGETS[args.target][0]
    if args.dataset == "fixtures":
        # Synthetic data must never land on the client deliverable path (WR-08).
        if args.out is None and out == DELIVERABLE:
            out = SYNTHETIC_MAIN_OUT
        if os.path.abspath(out) == os.path.abspath(DELIVERABLE):
            ap.error("refusing to write synthetic fixtures data to the client "
                     "deliverable %s; pass another --out" % DELIVERABLE)
    try:
        data, _ = build_bytes(args.target, load_dataset(args.dataset))
    except ProvenanceError as exc:
        sys.stderr.write("PROVENANCE ERROR\n%s\n\n" % exc)
        return 2
    except (LintError, UnsafeCellError) as exc:
        sys.stderr.write("LINT ERROR\n%s\n\n" % exc)
        return 3
    except ScanError as exc:
        sys.stderr.write("SCAN ERROR\n%s\n\n" % "\n".join(exc.findings))
        return 4
    except ReadbackError as exc:
        sys.stderr.write("READBACK ERROR\n%s\n\n" % "\n".join(exc.problems))
        return 5
    _write_atomic(out, data)
    print("sha256 %s  %s" % (hashlib.sha256(data).hexdigest(), out))
    print("parts %d" % len(part_names(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
