"""IAMC-format reader for the user-supplied NGFS file.

run as .venv/bin/python -W ignore -I tools/parse_ngfs.py PATH [--model TEXT]
[--region TEXT]; read-only; prints values for human review; never writes.
Reads .csv (comma) or .tsv (tab); only Variable == "Price|Carbon" rows.
"""
import argparse
import csv
import os
import sys

MAX_BYTES = 50 * 1024 * 1024
YEARS = [str(y) for y in range(2020, 2061)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print NGFS Price|Carbon rows (read-only).")
    ap.add_argument("path")
    ap.add_argument("--model")
    ap.add_argument("--region")
    a = ap.parse_args(argv)
    suffix = os.path.splitext(a.path)[1].lower()
    if suffix not in (".csv", ".tsv"):
        print("refused: suffix must be .csv or .tsv", file=sys.stderr)
        return 1
    if os.path.getsize(a.path) > MAX_BYTES:
        print("refused: file larger than 50 MB", file=sys.stderr)
        return 1
    delim = "\t" if suffix == ".tsv" else ","
    with open(a.path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh, delimiter=delim)
        header = next(rd, None)
        if not header or "Model" not in header or "Scenario" not in header:
            print("refused: first line lacks Model and Scenario", file=sys.stderr)
            return 1
        ix = {h.strip(): i for i, h in enumerate(header)}
        for row in rd:
            if not row:
                continue
            if len(row) < len(header):
                print("footer: %s" % " ".join(row))
                continue
            if row[ix["Variable"]] != "Price|Carbon":
                continue
            if a.model is not None and row[ix["Model"]] != a.model:
                continue
            if a.region is not None and row[ix["Region"]] != a.region:
                continue
            head = [row[ix[k]] for k in ("Model", "Scenario", "Region", "Variable", "Unit")]
            yrs = ["%s=%s" % (y, row[ix[y]]) for y in YEARS if y in ix and row[ix[y]] != ""]
            print(" | ".join(head) + " | " + " ".join(yrs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
