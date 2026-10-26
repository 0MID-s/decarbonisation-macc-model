# Excel checks

Scripted and visual checks of the workbook in Excel desktop. Phase 1 results are
in docs/SPIKE_RESULTS.md.

## Phase 3 (Measures and MACC), Excel desktop

- Date: 2026-10-21
- Excel: Excel for Mac 16.114, driven by osascript (JXA) addressed to Microsoft Excel only
- File checked: a throwaway copy of dist/maison_veritas.xlsx, sha256
  `1c44c8b6d614b4bc208ab1b27571bdc19952e87be81ca79ffab7f944d2d63b32`
  (identical to the deliverable; the copy was never saved by Excel, still
  identical when closed)
- Method: full recalculation (calculateFull), read numeric values (the Mac
  locale uses a decimal comma, so never displayed text) of every formula cell on
  every sheet, compare with the cached values of a build of the same selector
  state (cached values come from checkmodel.measures_reference). Relative
  tolerance 1e-7, absolute 1e-9 near zero. Error values counted separately.
- Default state (Market-based, Central): 8,607 formula cells compared, 0
  mismatches, 0 error values.

### Six selector states

Selectors set by script on Inputs!G8 (scenario) and Inputs!G9 (basis), then a
full recalculation.

| Basis | Scenario | Formula cells compared | Mismatches | Error values | Heat pump IRR in Excel |
|---|---|---|---|---|---|
| Location-based | Low | 8,607 | 0 | 0 | -12.529499% |
| Location-based | Central | 8,607 | 0 | 0 | -12.529499% |
| Location-based | High | 8,607 | 0 | 0 | -12.529499% |
| Market-based | Low | 8,607 | 0 | 0 | -12.529499% |
| Market-based | Central | 8,607 | 0 | 0 | -12.529499% |
| Market-based | High | 8,607 | 0 | 0 | -12.529499% |

(The heat pump IRR does not depend on basis or scenario in these states; Excel
equals the reference to more than 8 decimals.)

### IRR convergence per measure

| Measure | Excel IRR | Matched reference on first run | Guess fallback used |
|---|---|---|---|
| LED | 10.041098% | yes | none |
| VSD | 42.765733% | yes | none |
| Heat pump (HP) | -12.529499% | yes | none |
| Rooftop PV | 18.771516% | yes | none |
| Fleet | 0.672449% | yes | none |
| Renewable contract (RC) | text "n/a (no upfront outlay)" | yes (same text as reference) | none (no cash outlay, so no IRR by design) |

The existing guess cell `=IF(SUM(cf)<0,-Const_IRR_Guess,Const_IRR_Guess)` was
sufficient. No second guess formula was needed. No Excel IRR limitation was
found. No fix to the workbook was applied.

Excel for the web: still open, GATE-B (Phase 5).

### Deviation: location of the throwaway copy

The plan said to copy into a `mktemp -d` folder. Excel for Mac (sandboxed)
silently refused to open a file there (0 workbooks). By the user's decision
(2026-10-21) the copy was placed in a fresh subfolder of the git-ignored dist/
folder (`dist/excel-check-<timestamp>/check.xlsx`), as in Phase 1, for this run
only. The copy was closed without saving and the copy and its subfolder were
deleted. dist/maison_veritas.xlsx was only ever read. No data_raw file was
opened in Excel.

### User finding 1 (2026-10-21): MACC technique A drew equal-width bars

The user opened dist/maison_veritas.xlsx in Excel for Mac 16.114 (Market-based,
Central). All six measures were drawn as equal-width, evenly spaced trapezoids
and the x-axis showed only a "0" label. Widths should follow tCO2e per year
(VSD 15, PV 155, LED 31, renewable contract 2,194, heat pump 789, fleet 36).
Labels, the dashed reference line, title and legend rendered correctly.

Root cause (confirmed in Excel): XlsxWriter 3.2.9 hard-codes `<c:auto val="1"/>`
inside `<c:dateAx>`. With auto on, Excel picks the axis type itself and, for this
area chart, chose a TEXT axis (24 equal slots, trapezoids, a single "0" label).

Attempt 1 (commit 94f194b, a date-formatted copy of the x column as categories)
was ineffective: Excel saw the cells as dates, yet the category type stayed
"automatic" and the axis was still text. That feed column was removed again.

Confirmed fix: setting the category axis type to "Date axis" (`<c:auto val="0"/>`)
drew variable-width rectangles at once, axis 0 to 3,500 in steps of 500
(screenshot by the user). `xl/postprocess.py` now rewrites `c:auto` 1 to 0 inside
`c:dateAx` in the built .xlsx (stdlib zipfile; other members byte-identical;
replacement count asserted; applied to the spike build too). Categories are plain
MACC column E again. The axis keeps min 0, max a multiple of the nice step,
major unit = the nice step.

Data labels now use short names (LED, VSD, Solar PV, Contract, Heat pump, Fleet)
from a "Short chart label" column (MACC column L), read through INDEX/MATCH so
they follow the live sort. The legend keeps the full names.

Re-verification of variable widths and axis labels in Excel: pending, user.

### User visual verdict

Approved, 2026-10-24, Excel for Mac 16.114, after rebuild 6b0dec23 (auto=0,
short labels). The user said the chart "seems good" and confirmed that the
dropdowns drive the model. Live values read from the open workbook with
High / Location-based: title "MACC: Location-based basis, High carbon price
scenario"; the renewable contract shows "n/a (no abatement on this basis)",
tier Later, rank 6; VSD 14 t / -801, Solar PV 139 / -656, LED 28 / -244,
Heat pump 822 / 102, Fleet 37 / 143.

The user remarked that Solar PV, VSD and LED look squished on the full MACC.
That is correct data (about 200 t of about 3,220 t), so a zoom chart was added
after the user's check (cell K18, right of chart A), using the same technique
(date axis, auto=0 post-process) and the same series, with the x-axis cut just
above the largest cumulative "Do first" abatement over all six states. Its
rendering was not part of the user's check and will be re-checked at GATE-B
(Excel for the web) and in the final review.

## Phase 4 (Exposure and Sensitivity), Excel desktop

- Date: 2026-10-25
- Excel: Excel for Mac 16.114.1, driven by osascript (JXA) addressed to Microsoft Excel only
- Deliverable: dist/maison_veritas.xlsx, sha256
  `173559767165b4c13e0b1dc642e9a42ab1ebb450aa450273e217d58ccb06182d`
  (unchanged after the run; only throwaway copies were opened)
- Method: `.venv/bin/python tools/excel_check.py` (tracked script, with
  `tools/excel_recalc.js`). For each of the 12 states
  (exposure_reference.STATES) it builds the workbook of that state, writes a
  throwaway copy to `dist/excel-check-<timestamp>/check.xlsx`, sets
  Inputs!G8 (scenario), G9 (basis) and G10 (direct ETS Off/On) in Excel, runs a
  full recalculation, reads the numeric value of every formula cell on every
  sheet (never displayed text) and compares with the cached reference values at
  relative tolerance 1e-7 (absolute 1e-9 near zero). Error values are counted
  separately. The copy is closed without saving and deleted; no data_raw file
  is opened. Unit tests for the harness need no Excel
  (`tests/test_excel_check.py`).

| Basis | Scenario | Direct ETS | Formula cells | Mismatches | Error values |
|---|---|---|---|---|---|
| Location-based | Low | Off | 12,144 | 0 | 0 |
| Location-based | Low | On | 12,144 | 0 | 0 |
| Location-based | Central | Off | 12,144 | 0 | 0 |
| Location-based | Central | On | 12,144 | 0 | 0 |
| Location-based | High | Off | 12,144 | 0 | 0 |
| Location-based | High | On | 12,144 | 0 | 0 |
| Market-based | Low | Off | 12,144 | 0 | 0 |
| Market-based | Low | On | 12,144 | 0 | 0 |
| Market-based | Central | Off | 12,144 | 0 | 0 |
| Market-based | Central | On | 12,144 | 0 | 0 |
| Market-based | High | Off | 12,144 | 0 | 0 |
| Market-based | High | On | 12,144 | 0 | 0 |

- Excel-only findings: none. No workbook fix was needed. All throwaway copies
  and check folders were deleted afterwards.
- Excel for the web: still open, GATE-B (Phase 5).

### User visual verdict (Phase 4)

- Date: 2026-10-25
- Checked by the user in Excel for Mac: the bridge chart (Exposure sheet) and the
  tornado chart (Sensitivity sheet) across Central / Market-based / Direct ETS
  Off, Low, and Direct ETS On; the sensitivity grid centre; and the
  rank-stability indicator showing "Same".
- Verdict (verbatim): "looks good"
- Findings: none.

### Re-run after code-review fixes (Phase 4)

- Date: 2026-10-25, after commits ebf677e..7d67200 (review warnings WR-01 to
  WR-08: per-year grid factor in the internal carbon price lens, per-unit
  pass-through tornado row, text fixes, hardened Excel harness with strict
  blank comparison).
- Method: `.venv/bin/python tools/excel_check.py`, Excel for Mac, all 12 states.
- Result: 12,145 formula cells per state (one new helper cell), 0 mismatches
  and 0 error values in every state. The stricter blank-versus-zero comparison
  (WR-08) exposed no hidden mismatches.
- `dist/maison_veritas.xlsx` was unchanged by the run (sha256
  `e4822ca03be4a23bca85d8c8676e26bcb3f5faf14206c3265e10e66af93d9019`), and no
  check folders were left behind.
- The user's visual verdict above was given before these fixes. The fixes do
  not touch the bridge or tornado chart definitions.

## Phase 5 / GATE-B, Excel desktop

- Date: 2026-10-26
- Excel: Excel for Mac 16.114.1, driven by osascript (JXA) addressed to Microsoft Excel only
- Deliverable: dist/maison_veritas.xlsx, sha256
  `903cb44645c1a52b81f0ee8e829e38a4cbf38e7ef57b9cd7b3a36f9a209312f1`
  (unchanged after the run; only throwaway copies were opened)
- Method: `.venv/bin/python tools/excel_check.py` (tracked script, with
  `tools/excel_recalc.js`). Same method as Phase 4: each of the 12 states is
  built, a throwaway copy is opened in Excel, the three selectors are set, a
  full recalculation runs, every formula cell is read numerically and compared
  with the cached reference values (relative 1e-7, absolute 1e-9). New in this
  run: the value Excel computes for Chk_Master (cell resolved from the defined
  name on the Checks sheet) is reported per state, and the run fails unless it
  reads "OK".

| Basis | Scenario | Direct ETS | Formula cells | Mismatches | Error values | Chk_Master in Excel |
|---|---|---|---|---|---|---|
| Location-based | Low | Off | 12,278 | 0 | 0 | OK |
| Location-based | Low | On | 12,278 | 0 | 0 | OK |
| Location-based | Central | Off | 12,278 | 0 | 0 | OK |
| Location-based | Central | On | 12,278 | 0 | 0 | OK |
| Location-based | High | Off | 12,278 | 0 | 0 | OK |
| Location-based | High | On | 12,278 | 0 | 0 | OK |
| Market-based | Low | Off | 12,278 | 0 | 0 | OK |
| Market-based | Low | On | 12,278 | 0 | 0 | OK |
| Market-based | Central | Off | 12,278 | 0 | 0 | OK |
| Market-based | Central | On | 12,278 | 0 | 0 | OK |
| Market-based | High | Off | 12,278 | 0 | 0 | OK |
| Market-based | High | On | 12,278 | 0 | 0 | OK |

- Excel-only findings: none. No workbook fix was needed. No dist/excel-check-*
  folder remains.
- Excel for the web: not verified (see the user verdict below).

### User visual verdict (Phase 5)

- Date: 2026-10-26
- Verdict: "approve desktop". The user reviewed the 8-step desktop checklist
  (Cover flag and links, ReadMe trace links, Dashboard tiles and charts,
  selector changes, MACC/bridge/tornado, Disclosure dropdown, A4 print preview)
  and approved. No issues were reported; the MACC technique stays "A".
- Excel for the web: not verified (the user did not perform the web check).

Final text-only rebuild: formula-identical, re-verified by the script in all 12
states (12,278 formula cells each, 0 mismatches, 0 error values, Chk_Master OK).
Date: 2026-10-26. Final deliverable sha256
`1668b7aeb6d8ede4462793eb6d9a01761b81c772d497389d2c2f6cce9aab0e73`
(only the Notes record text changed; unchanged by the run). Excel for the web:
not verified.

### Post-review rebuild (code review fixes CR-01..WR-04)

- Date: 2026-10-26, after the Phase 5 code review fixes (commits ea8c4f9 to
  the Notes record update): like-for-like Chk_TileVsMACC with two new MACC
  names, a live exposure-window label on the cost-of-not-acting tile, Checks
  cached values taken from the reference model, the ReadMe first-ranked trace,
  walkthrough wording and the revised ESRS row status.
- Method: `.venv/bin/python tools/excel_check.py`, Excel for Mac, all 12 states,
  same comparison as above (relative 1e-7, absolute 1e-9; Chk_Master read from
  Excel).

| Basis | Scenario | Direct ETS | Formula cells | Mismatches | Error values | Chk_Master in Excel |
|---|---|---|---|---|---|---|
| Location-based | Low | Off | 12,279 | 0 | 0 | OK |
| Location-based | Low | On | 12,279 | 0 | 0 | OK |
| Location-based | Central | Off | 12,279 | 0 | 0 | OK |
| Location-based | Central | On | 12,279 | 0 | 0 | OK |
| Location-based | High | Off | 12,279 | 0 | 0 | OK |
| Location-based | High | On | 12,279 | 0 | 0 | OK |
| Market-based | Low | Off | 12,279 | 0 | 0 | OK |
| Market-based | Low | On | 12,279 | 0 | 0 | OK |
| Market-based | Central | Off | 12,279 | 0 | 0 | OK |
| Market-based | Central | On | 12,279 | 0 | 0 | OK |
| Market-based | High | Off | 12,279 | 0 | 0 | OK |
| Market-based | High | On | 12,279 | 0 | 0 | OK |

- One more formula cell per state than GATE-B (12,279 vs 12,278): the
  exposure-window label is now a formula.
- Deliverable: dist/maison_veritas.xlsx, sha256
  `59c8ce4d10ba786dd18da56c999d756eed31d1c565840bfd630b1ae7bd1d4020`
  (unchanged by the run). No dist/excel-check-* folder remains.
- Re-verified by script only. The user's visual approval above was given for
  the pre-fix build; the fixes change visible labels (Dashboard tile
  sub-labels, scenario chart axis title, ReadMe trace text, Disclosure status
  column), which have not been reviewed visually. Excel for the web: not
  verified.

### User visual verdict (post-review build)

- Date: 2026-10-26. The user reviewed the labels changed by the code review
  fixes in Excel desktop (Dashboard tile sub-labels, scenario chart axis
  title, ReadMe trace text, Disclosure status column).
- Verdict (verbatim): "skip web, looks good overall".
- Excel for the web: not verified (the user chose to skip it).
- The flagged disclosure references ship with their visible flags.
- Final text-only rebuild after this verdict (Notes record wording only):
  re-verified by tools/excel_check.py in all 12 states, 12,279 formula cells
  each, 0 mismatches, 0 error values, Chk_Master OK. Deliverable sha256
  `61522688e388d929bf70d1819dc80b227a0ea09d3fcda9c934bcb4ad12f8e74a`.
