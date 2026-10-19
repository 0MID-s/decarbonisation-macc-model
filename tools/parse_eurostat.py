"""Flatten a Eurostat JSON-stat file for human review.

run as .venv/bin/python -W ignore -I tools/parse_eurostat.py PATH [--filter dim=code ...];
read-only; prints values for human review; never writes.
"""
import argparse
import itertools
import json
import sys


def flatten(d):
    ids, size = d["id"], d["size"]
    cats = []
    for k in ids:
        idx = d["dimension"][k]["category"]["index"]
        if isinstance(idx, dict):
            cats.append([c for c, _ in sorted(idx.items(), key=lambda kv: kv[1])])
        else:
            cats.append(list(idx))
    values = d.get("value", {})
    status = d.get("status", {})
    if isinstance(values, list):
        values = {str(i): v for i, v in enumerate(values) if v is not None}
    if isinstance(status, list):
        status = {str(i): v for i, v in enumerate(status) if v}
    for pos, combo in enumerate(itertools.product(*[range(n) for n in size])):
        v = values.get(str(pos))
        if v is None:
            continue
        codes = {ids[i]: cats[i][c] for i, c in enumerate(combo)}
        yield codes, v, status.get(str(pos))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print Eurostat JSON-stat cells (read-only).")
    ap.add_argument("path")
    ap.add_argument("--filter", action="append", default=[], metavar="dim=code")
    a = ap.parse_args(argv)
    filt = {}
    for f in a.filter:
        k, _, v = f.partition("=")
        filt.setdefault(k, set()).add(v)
    with open(a.path, encoding="utf-8") as fh:
        d = json.load(fh)
    for codes, v, flag in flatten(d):
        if any(k in codes and codes[k] not in vs for k, vs in filt.items()):
            continue
        print("%s %s %s" % ("|".join(codes[k] for k in d["id"]), v, flag or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
