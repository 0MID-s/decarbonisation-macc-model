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

Pending: waiting for the human Excel check (plan 01-08). Non-blocking for
Phases 2 to 4: default technique A with C ready; dropdown default = defined
name per config BUILD.dropdown_source. The checklist is the Instructions sheet
of `dist/spike_macc.xlsx`; reply in one message in the format shown there.
