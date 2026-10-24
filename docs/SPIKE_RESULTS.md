# MACC and dropdown spike: results

## Purpose

Throwaway workbook that de-risks the Phase 3 marginal abatement cost curve and
the cross-sheet dropdowns before any real model is built. All data is labelled
synthetic. The file is not a deliverable and is not tracked (`dist/` is
gitignored).

## Build

```
.venv/bin/python build.py --target spike --dataset fixtures
```

Output `dist/spike_macc.xlsx`, sha256
`bb4c7a87cec8bc7e68f552c12b963f04740d24de403c6ac9097177876d45621e`
(22 parts; same hash on every PYTHONHASHSEED). The spike refuses the real
`config` dataset (exit code 2).

## Automated evidence

| Test | What it proves |
|---|---|
| tests.test_macc_reference | Reference ranking, cumulative widths, technique A points, technique C bins; every helper formula has the documented pattern and its cached value equals the reference |
| tests.test_charts | Exactly 2 chart parts; area chart is non-stacked with `c:dateAx`, 6 area series plus 1 reference line series; column chart has gap 0, overlap 100 and 6 series; chart x cache equals the reference x values |
| tests.test_spike | Dropdown sheet has validation sources `Lists!$B$6:$B$8`, `List_Scenario`, `List_Basis`; all formula cells have cached values equal to the reference; scan clean; spike refuses `config`; Instructions is the first sheet with 12 checks |
| tests.test_determinism | The spike is byte-identical across 4 hash seeds (12 subprocess builds across 3 target/dataset pairs) |
| tests.test_offline | `checkmodel/` is audited; no production module except `build.py` imports tests |
| Build pipeline | Lint (only 0 and 1 as numeric literals), default-deny scan, openpyxl read-back run on the spike like the main build |

Full suite: 174 tests pass.

## Quick Look observation

`qlmanage -t -s 1200` rendered
`/private/tmp/claude-501/-Users-o-Desktop-Claude-Projects-maison-veritas-decarb-macc/6df99bd5-15c4-484a-86a1-a444d58b03a8/scratchpad/ql3/spike_macc.xlsx.png`
and it was inspected. It shows only the first sheet: the "GATE-A: Excel check
for the MACC spike" title, the synthetic banner, the Check 1 to Check 12 table
and the reply-format line. No chart is visible in the thumbnail (expected: Quick
Look renders the first sheet only). Chart presence is proven by the XML tests,
not by the thumbnail.

## Known unverified items (need Excel)

- A6: date-axis area chart rendering (duplicate x values as vertical edges) in
  Excel for the web.
- Axis minimum 0 and `#,##0` label format on the date axis.
- Custom data labels on area series (placement is left to Excel).
- A7: direct cross-sheet range as a dropdown source (the defined-name form is
  the default).

## GATE-A status

Correction (2026-10-21): the conclusion below that technique A "works" for
variable widths was probably wrong. The spike chart used the same XML as the
Phase 3 chart: a date axis with `c:auto=1` fed by plain-number category cells,
which Excel renders as a text axis (equal spacing). The "crowded labels" were
likely the 24 category labels. Equal spacing was not detected at the time.
Root cause now confirmed in Excel (2026-10-21): XlsxWriter hard-codes
`c:auto=1`; Excel then picks a text axis. A date-formatted category column did
NOT fix it. Setting the axis to Date axis (`c:auto=0`) did, and the build now
applies that via `xl/postprocess.py` to both the main and the spike workbooks.
Re-check of the rebuilt files is part of Phase 3 plan 03-11.

GATE-A: Passed (Excel desktop) on 2026-10-18, with notes. Excel for the web not yet checked.

Environment: Microsoft Excel for Mac 16.114, spike sha256
bb4c7a87cec8bc7e68f552c12b963f04740d24de403c6ac9097177876d45621e (fresh rebuild,
identical to the 01-07 build).

### Scripted checks in Excel desktop (AppleScript, Claude)

| Check | Result |
|---|---|
| Recalculation vs cached values | All 1,848 formulas on MACC_A, MACC_C and Dropdown recalculated by Excel match the Python reference cached values (relative tolerance 1e-7; Mac locale uses decimal comma) |
| 8 (data side) | MACC_A D9 set to -100: M3 moved to slot 1 of the sorted table and MACC_C bins followed; restoring 112.5 restored the order |
| 11 | C6 = High, C7 = Low: echo cells showed High / Low and MATCH 3 / 1; restored to Central |
| 12 (error values) | No error values on any sheet after recalculation |

### Visual checks (user)

The user reviewed checks 1 to 12 in Excel desktop and reported "looks good ...
I think everything works", with one note:

- Check 3: on MACC_A the x-axis numbers are crowded ("a bit squished").
  Labels are numbers, not dates, so the technique works; Phase 3 must set the
  date-axis major unit (or label interval) and/or chart width so labels do not
  crowd.

The user did not report each check separately; no problems were reported for
checks 1, 2, 4 to 10 or 12.

### Decisions (config/build_config.py)

- `BUILD.macc_technique = "A"` (checks 1, 2, 3, 8 OK on desktop). Technique C
  stays available as the fallback.
- `BUILD.dropdown_source = "name"` (check 10 OK).

### Still open

- Excel for the web rendering of technique A and the dropdowns (checks 1 to 3,
  9, 10) has not been checked. Must be closed by GATE-B (Phase 5) at the latest;
  switch to technique C if the web rendering fails.
