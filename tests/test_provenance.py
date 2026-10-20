"""Tests for provenance schema and blocking validators (DATA-01..03, D-10..D-13)."""
import ast
import dataclasses
import datetime
import glob
import os
import unittest

from config.build_config import BUILD
from config.inputs import INPUTS
from config.schema import (
    NOT_APPLICABLE, InputRecord, Kind, PriceBasis, ProvenanceError, Source,
    Status,
)
from config.sources import SOURCES
from config.validate import validate_provenance
from tests.fixtures.synthetic import SYNTHETIC_INPUTS, SYNTHETIC_SOURCES

YEARS = tuple(range(2026, 2056))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _inp(rid):
    return next(r for r in SYNTHETIC_INPUTS if r.id == rid)


def _src(sid):
    return next(s for s in SYNTHETIC_SOURCES if s.id == sid)


def _swap_input(rid, **changes):
    return tuple(dataclasses.replace(r, **changes) if r.id == rid else r
                 for r in SYNTHETIC_INPUTS)


def _swap_source(sid, **changes):
    return tuple(dataclasses.replace(s, **changes) if s.id == sid else s
                 for s in SYNTHETIC_SOURCES)


class ProvenanceTests(unittest.TestCase):
    def assertFails(self, sources, inputs, mention):
        with self.assertRaises(ProvenanceError) as cm:
            validate_provenance(sources, inputs, YEARS)
        joined = "\n".join(cm.exception.problems)
        self.assertIn(mention, joined)
        return cm.exception

    def test_clean_synthetic_passes(self):
        validate_provenance(SYNTHETIC_SOURCES, SYNTHETIC_INPUTS, YEARS)

    def test_config_passes(self):
        validate_provenance(SOURCES, INPUTS, BUILD.timeline_years)
        self.assertEqual(len(BUILD.timeline_years), 30)

    def test_placeholder_blocked(self):
        ins = _swap_input("Baseline_SynthGasMWh", status=Status.PLACEHOLDER)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Baseline_SynthGasMWh")

    def test_sourced_missing_source_id(self):
        ins = _swap_input("Baseline_SynthGasMWh", source_id=None)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Baseline_SynthGasMWh")

    def test_sourced_unresolved_source_id(self):
        ins = _swap_input("Baseline_SynthGasMWh", source_id="Src_Nope")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Baseline_SynthGasMWh")

    def test_assumption_without_rationale(self):
        ins = _swap_input("Finance_SynthWacc", rationale="   ")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_source_empty_fields(self):
        for field in ("publisher", "dataset", "url", "edition", "licence_note"):
            with self.subTest(field=field):
                srcs = _swap_source("Src_SynthA", **{field: "  "})
                self.assertFails(srcs, SYNTHETIC_INPUTS, "Src_SynthA")

    def test_source_retrieved_not_date(self):
        srcs = _swap_source("Src_SynthA", retrieved="2026-10-17")
        self.assertFails(srcs, SYNTHETIC_INPUTS, "Src_SynthA")

    def test_source_url_off_allowlist(self):
        for url in ("http://ec.europa.eu/", "https://eurostat.evil.com/",
                    "https://ec.europa.eu@evil.example/"):
            with self.subTest(url=url):
                srcs = _swap_source("Src_SynthA", url=url)
                self.assertFails(srcs, SYNTHETIC_INPUTS, "Src_SynthA")

    def test_duplicate_source_ids(self):
        srcs = SYNTHETIC_SOURCES + (_src("Src_SynthA"),)
        self.assertFails(srcs, SYNTHETIC_INPUTS, "Src_SynthA")

    def test_duplicate_input_ids(self):
        ins = SYNTHETIC_INPUTS + (_inp("Finance_SynthWacc"),)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_unused_source(self):
        extra = dataclasses.replace(_src("Src_SynthA"), id="Src_SynthUnused")
        self.assertFails(SYNTHETIC_SOURCES + (extra,), SYNTHETIC_INPUTS,
                         "Src_SynthUnused")

    def test_bad_id_pattern(self):
        for bad in ("ETS2", "lower_case", "NoUnderscore"):
            with self.subTest(bad=bad):
                ins = _swap_input("Finance_SynthWacc", id=bad)
                self.assertFails(SYNTHETIC_SOURCES, ins, bad)

    def test_reserved_ids(self):
        for bad in ("Inf", "NaN", "TRUE"):
            with self.subTest(bad=bad):
                ins = _swap_input("Finance_SynthWacc", id=bad)
                self.assertFails(SYNTHETIC_SOURCES, ins, bad)

    def test_unknown_section(self):
        ins = _swap_input("Finance_SynthWacc", section="Misc")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_conversion_ref_missing_outside_constants(self):
        ins = _swap_input("Finance_SynthWacc", conversion_ref=None)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_conversion_ref_set_inside_constants(self):
        ins = _swap_input("Const_SynthKWhPerMWh", conversion_ref="Const_None")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Const_SynthKWhPerMWh")

    def test_conversion_ref_not_constants(self):
        ins = _swap_input("Finance_SynthWacc",
                          conversion_ref="Energy_SynthElecPrice")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")
        ins = _swap_input("Finance_SynthWacc", conversion_ref="Const_Nope")
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_constants_must_be_scalar(self):
        # WR-04: a Constants series broke Inputs at build time (TypeError).
        sid = "Const_SynthKWhPerMWh"
        ins = _swap_input(sid, kind=Kind.SERIES, published_value=None,
                          series=((2026, 1000.0),))
        e = self.assertFails(SYNTHETIC_SOURCES, ins, sid)
        joined = "\n".join(e.problems)
        self.assertIn("Constants record must be a scalar", joined)
        self.assertIn("Baseline_SynthGasMWh: conversion_ref", joined)

    def test_price_basis_none(self):
        ins = _swap_input("Finance_SynthWacc", price_basis=None)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_monetary_unit_needs_price_basis(self):
        ins = _swap_input("Energy_SynthElecPrice", price_basis=NOT_APPLICABLE)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Energy_SynthElecPrice")

    def test_monetary_basis_complete(self):
        # WR-05: a monetary basis needs a base year and real/nominal.
        for basis in (PriceBasis("EUR", None, "nominal"),
                      PriceBasis("EUR", "2025", "real"),
                      PriceBasis("EUR", True, "real"),
                      PriceBasis("EUR", 2025, "n/a"),
                      PriceBasis("EUR", 2025, "Real"),
                      PriceBasis("", 2025, "real")):
            with self.subTest(basis=basis):
                ins = _swap_input("Energy_SynthElecPrice", price_basis=basis)
                self.assertFails(SYNTHETIC_SOURCES, ins, "Energy_SynthElecPrice")

    def test_monetary_unit_variants_detected(self):
        for unit in ("€/kWh", "US$2010/tCO2", "GBP/t", "USD/t"):
            with self.subTest(unit=unit):
                ins = _swap_input("EF_SynthGas", published_unit=unit)
                self.assertFails(SYNTHETIC_SOURCES, ins, "monetary unit")

    def test_scalar_rules(self):
        for changes in ({"published_value": None},
                        {"published_value": float("nan")},
                        {"published_value": float("inf")},
                        {"series": ((2026, 1.0),)}):
            with self.subTest(changes=changes):
                ins = _swap_input("Finance_SynthWacc", **changes)
                self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_series_rules(self):
        sid = "CarbonPrice_SynthCentral"
        for changes in ({"published_value": 1.0},
                        {"series": ()},
                        {"series": ((2027, 1.0), (2026, 2.0))},
                        {"series": ((2026, 1.0), (2026, 2.0))},
                        {"series": ((2026, 1.0), (2099, 2.0))}):
            with self.subTest(changes=changes):
                ins = _swap_input(sid, **changes)
                self.assertFails(SYNTHETIC_SOURCES, ins, sid)

    def test_empty_unit_and_description(self):
        for field in ("published_unit", "model_unit", "description"):
            with self.subTest(field=field):
                ins = _swap_input("Finance_SynthWacc", **{field: ""})
                self.assertFails(SYNTHETIC_SOURCES, ins, "Finance_SynthWacc")

    def test_required_structural_records(self):
        ins = tuple(r for r in SYNTHETIC_INPUTS if r.id != "Const_None")
        ins = tuple(dataclasses.replace(r, conversion_ref="Const_SynthKWhPerMWh")
                    if r.conversion_ref == "Const_None" else r for r in ins)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Const_None")
        ins = _swap_input("Time_FirstYear", published_value=2030.0)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Time_FirstYear")
        ins = _swap_input("Const_None", published_value=2.0)
        self.assertFails(SYNTHETIC_SOURCES, ins, "Const_None")

    def test_multi_error_reports_all(self):
        ins = _swap_input("Baseline_SynthGasMWh", status=Status.PLACEHOLDER)
        ins = tuple(dataclasses.replace(r, rationale="")
                    if r.id == "Finance_SynthWacc" else r for r in ins)
        srcs = _swap_source("Src_SynthB", url="http://evil.example/")
        err = self.assertFails(srcs, ins, "Baseline_SynthGasMWh")
        self.assertGreaterEqual(len(err.problems), 3)
        self.assertEqual(str(err), "\n".join(err.problems))

    def test_enum_labels(self):
        self.assertEqual(Status.SOURCED.label, "Sourced")
        self.assertEqual(Status.ASSUMPTION.label, "Analyst assumption")
        self.assertEqual(Status.PLACEHOLDER.label, "Placeholder")
        self.assertEqual(PriceBasis("EUR", 2025, "nominal").label,
                         "EUR 2025 nominal")
        self.assertEqual(NOT_APPLICABLE.label, "n/a (non-monetary)")

    def test_records_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            _inp("Const_None").id = "X_y"

    def test_config_has_no_fixtures(self):
        for path in sorted(glob.glob(os.path.join(ROOT, "config", "*.py"))):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotIn("SYNTHETIC", text, path)
            tree = ast.parse(text)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for n in names:
                    self.assertFalse(n == "tests" or n.startswith("tests."),
                                     "%s imports %s" % (path, n))

    def test_build_config_fixed(self):
        self.assertEqual(BUILD.created, datetime.datetime(2026, 10, 17, 0, 0, 0))
        self.assertEqual(BUILD.timeline_years[0], 2026)
        self.assertEqual(BUILD.timeline_years[-1], 2055)


class NgfsY0Guard(unittest.TestCase):
    def test_y0_must_precede_timeline(self):
        ins = tuple(dataclasses.replace(r, published_value=2026.0)
                    if r.id == "Carbon_NGFS_Y0Year" else r for r in INPUTS)
        with self.assertRaises(ProvenanceError) as cm:
            validate_provenance(SOURCES, ins, YEARS)
        self.assertIn("Carbon_NGFS_Y0Year", "\n".join(cm.exception.problems))

    def test_real_config_and_absent_record_pass(self):
        validate_provenance(SOURCES, INPUTS, YEARS)
        validate_provenance(SYNTHETIC_SOURCES, SYNTHETIC_INPUTS, YEARS)


if __name__ == "__main__":
    unittest.main()
