"""Blocking provenance validators (D-12). Collects all problems, then raises."""
import datetime
import math
import re

from config.schema import (
    ID_PATTERN, NOT_APPLICABLE, RESERVED_IDS, SECTIONS, Kind, ProvenanceError,
    Status,
)
from config.security import host_allowed

_ID_RE = re.compile(ID_PATTERN)


def _blank(s):
    return not isinstance(s, str) or not s.strip()


def _check_sources(sources, problems):
    seen = set()
    for s in sources:
        sid = s.id
        if _blank(sid) or not _ID_RE.match(sid) or sid.lower() in RESERVED_IDS:
            problems.append("%s: source id invalid" % sid)
        if sid in seen:
            problems.append("%s: duplicate source id" % sid)
        seen.add(sid)
        for field in ("publisher", "dataset", "url", "edition", "licence_note"):
            if _blank(getattr(s, field)):
                problems.append("%s: source field '%s' is empty" % (sid, field))
        if (not isinstance(s.retrieved, datetime.date)
                or isinstance(s.retrieved, datetime.datetime)):
            problems.append("%s: retrieved must be a date" % sid)
        if not _blank(s.url) and not host_allowed(s.url):
            problems.append("%s: url not https on an allowed domain" % sid)


def _check_series(r, years, problems):
    if r.published_value is not None:
        problems.append("%s: series record must not set published_value" % r.id)
    if not r.series:
        problems.append("%s: series is empty" % r.id)
        return
    ys = [y for y, _ in r.series]
    if any(b <= a for a, b in zip(ys, ys[1:])):
        problems.append("%s: series years unsorted or duplicated" % r.id)
    for y, v in r.series:
        if y not in years:
            problems.append("%s: series year %s outside timeline" % (r.id, y))
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            problems.append("%s: series value for %s not finite" % (r.id, y))


def _check_input(r, source_ids, constants, years, problems):
    rid = r.id
    if _blank(rid) or not _ID_RE.match(rid) or rid.lower() in RESERVED_IDS:
        problems.append("%s: id invalid (pattern or reserved)" % rid)
    if r.section not in SECTIONS:
        problems.append("%s: section '%s' not in SECTIONS" % (rid, r.section))
    for field in ("description", "published_unit", "model_unit"):
        if _blank(getattr(r, field)):
            problems.append("%s: %s is empty" % (rid, field))

    if r.status is Status.PLACEHOLDER:
        problems.append("%s: placeholder record blocks the build" % rid)
    elif r.status is Status.SOURCED:
        if _blank(r.source_id):
            problems.append("%s: sourced record has no source_id" % rid)
        elif r.source_id not in source_ids:
            problems.append("%s: source_id '%s' not in register"
                            % (rid, r.source_id))
    elif r.status is Status.ASSUMPTION:
        if _blank(r.rationale):
            problems.append("%s: assumption has no rationale" % rid)

    if r.section == "Constants":
        if r.conversion_ref is not None:
            problems.append("%s: Constants record must not set conversion_ref"
                            % rid)
        if r.kind is Kind.SERIES:
            problems.append("%s: Constants record must be a scalar" % rid)
    elif r.conversion_ref is None:
        problems.append("%s: conversion_ref required outside Constants" % rid)
    elif r.conversion_ref not in constants:
        problems.append("%s: conversion_ref '%s' is not a Constants record"
                        % (rid, r.conversion_ref))

    if r.price_basis is None:
        problems.append("%s: price_basis is None" % rid)
    else:
        units = "%s %s" % (r.published_unit or "", r.model_unit or "")
        if (("EUR" in units or "USD" in units)
                and r.price_basis == NOT_APPLICABLE):
            problems.append("%s: monetary unit needs a price basis" % rid)

    if r.kind is Kind.SERIES:
        _check_series(r, years, problems)
    else:
        v = r.published_value
        if v is None:
            problems.append("%s: scalar has no published_value" % rid)
        elif not isinstance(v, (int, float)) or not math.isfinite(v):
            problems.append("%s: published_value not finite" % rid)
        if r.series:
            problems.append("%s: scalar must not have a series" % rid)


def validate_provenance(sources, inputs, timeline_years):
    problems = []
    years = set(timeline_years)
    _check_sources(sources, problems)
    source_ids = set(s.id for s in sources)

    seen = set()
    # Only scalar constants can serve as a conversion factor (WR-04).
    constants = set(r.id for r in inputs
                    if r.section == "Constants" and r.kind is not Kind.SERIES)
    for r in inputs:
        if r.id in seen:
            problems.append("%s: duplicate input id" % r.id)
        seen.add(r.id)
        _check_input(r, source_ids, constants, years, problems)

    used = set(r.source_id for r in inputs if r.source_id)
    for s in sources:
        if s.id not in used:
            problems.append("%s: source not used by any input" % s.id)

    by_id = {}
    for r in inputs:
        by_id.setdefault(r.id, r)
    ident = by_id.get("Const_None")
    if ident is None or ident.published_value != 1.0:
        problems.append("Const_None: required structural record missing or not 1.0")
    first = by_id.get("Time_FirstYear")
    if (first is None or not timeline_years
            or first.published_value != float(timeline_years[0])):
        problems.append("Time_FirstYear: required record missing or not equal "
                        "to first timeline year")

    if problems:
        raise ProvenanceError(problems)
