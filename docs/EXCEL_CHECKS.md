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

Cause: XlsxWriter 3.2.9 always writes `<c:auto val="1"/>` inside `<c:dateAx>`, so
Excel chooses the axis type from the number format of the category cells. The x
helper cells (MACC E68:E91) were plain numbers, so Excel fell back to a text
axis: 24 equally spaced categories, and the major unit of 500 was read as a
label interval (only "0" shown).

Fix (commit "date-formatted axis feed"): a dedicated chart-feed column
(MACC M68:M91, header "Chart axis feed (tCO2e)", note in M65) holds `=E68` ...
`=E91` with the number format `d/m/yyyy`. Chart A categories (bars and the
reference line) point at that column. The visible tonnes column E keeps its
plain format; the chart axis labels use `#,##0` (not source-linked), so they
read as tonnes. The axis now has min 0, major unit = nice step of the largest
total across the six states, and a max rounded up to a multiple of that step.
The QA comparer converts openpyxl date-decoded cached values back to serials.
The Phase 1 spike builder is untouched (its layout has no feed column).

Re-verification of variable widths and axis labels in Excel: pending, user.

### User visual verdict

Pending (Task 2); the user re-checks after the fix above.
