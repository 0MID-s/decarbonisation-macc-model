# Maison Veritas - Decarbonisation Business Case and Carbon Cost Exposure Model

A generated Excel workbook (live formulas, native charts) that evaluates
decarbonisation measures and carbon cost exposure for a fictitious European
manufacturer, built only from cited public data or labelled analyst assumptions.

## Build

    .venv/bin/python build.py                      # main workbook, config data -> dist/maison_veritas.xlsx
    .venv/bin/python build.py --dataset fixtures   # synthetic test data (SYNTHETIC banner on every sheet)

The build is offline and deterministic (same bytes on every run). Do not run it
with `python -I`. `dist/` is gitignored and not tracked in Phase 1.

## Test

    .venv/bin/python -m unittest discover -s tests -t . -v

## Security

See `docs/SECURITY.md`. Every build validates provenance, lints every formula,
scans the final bytes against a default-deny OOXML allowlist and reads the file
back before anything is written; any failure exits non-zero and writes no file.
