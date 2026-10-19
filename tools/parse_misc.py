"""PVGIS and EEA parsers.

run as .venv/bin/python -W ignore -I tools/parse_misc.py pvgis PATH
or     .venv/bin/python -W ignore -I tools/parse_misc.py eea PATH [--country Belgium];
read-only; prints values for human review; never writes.
"""
import argparse
import csv
import json
import sys


def _find(obj, key, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + "." + k if path else k
            if k == key:
                yield p, v
            for hit in _find(v, key, p):
                yield hit


def pvgis(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    fixed = d["outputs"]["totals"]["fixed"]
    for k in ("E_y", "H(i)_y", "SD_y"):
        print("outputs.totals.fixed.%s = %s" % (k, fixed.get(k)))
    ms = d.get("inputs", {}).get("mounting_system", {})
    for p, v in _find(ms, "angle"):
        print("inputs.mounting_system.%s = %s" % (p, v))
    for p, v in _find(ms, "value"):
        print("inputs.mounting_system.%s = %s" % (p, v))


def eea(path, country=None):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        keep = [c for c in cols if any(t in c.lower() for t in ("year", "intens", "co2", "country", "ghg"))] or cols
        for i, row in enumerate(rd, start=2):
            if country and country.lower() not in [str(v).strip().lower() for v in row.values()]:
                continue
            print("row %d: %s" % (i, " | ".join("%s=%s" % (c, row.get(c)) for c in keep)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print PVGIS / EEA values (read-only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pvgis").add_argument("path")
    e = sub.add_parser("eea")
    e.add_argument("path")
    e.add_argument("--country")
    a = ap.parse_args(argv)
    if a.cmd == "pvgis":
        pvgis(a.path)
    else:
        eea(a.path, a.country)
    return 0


if __name__ == "__main__":
    sys.exit(main())
