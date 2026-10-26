# Maison Veritas model walkthrough

This note consolidates the model into one reading. It supersedes the reading order of `docs/walkthroughs/02-real-data-baseline.md`, `03-measures-macc.md` and `04-carbon-exposure-sensitivity.md`. Those three stay unchanged as phase records. Read this one first.

It assumes you know nothing about Excel or carbon finance. Plain words come first, then the formula, then the cell or name to click. Every number quoted below is read from the workbook in its default state (Market-based, Central, direct ETS Off) and is listed in the "Figures quoted" table at the end. A test rebuilds the workbook and fails if any quoted number drifts or if an unlisted number appears. Money is in real 2025 euros.

## Words used

- **Input**: a number typed once on the Inputs sheet, with a source or an "analyst assumption" label.
- **Defined name**: a label for a cell, such as `Rate_DiscountReal`. Type it in the Name Box (top left) to jump there.
- **NPV (net present value)**: all future money in and out, shrunk to today's value and added up. Positive means the measure earns more than the cost of money.
- **IRR (internal rate of return)**: the discount rate at which the NPV is exactly zero.
- **Payback**: years until the money put in has come back.
- **tCO2e**: tonnes of carbon dioxide equivalent.
- **Abatement cost**: net cost of avoiding one tonne. Negative means the measure saves money and carbon.
- **MACC**: marginal abatement cost curve. Measures sorted from cheapest to dearest per tonne; width is tonnes avoided, height is cost per tonne.
- **Scope 1 and 2**: direct emissions (fuel burnt) and purchased-electricity emissions.
- **Location-based (LB) and market-based (MB)**: two ways to count electricity emissions. LB uses the national grid average. MB uses the supplier or residual mix.
- **ETS1 and ETS2**: the EU carbon market for large installations, and a newer one charged on fuel suppliers.
- **Pass-through**: carbon cost paid upstream that shows up in the price you pay, here the power price.
- **ICP**: internal carbon price, a price a company sets itself to judge decisions. It is a lens, not a bill.
- **Real and nominal**: real money is in the purchasing power of one fixed year (2025). Nominal includes inflation.

## 1. The 2-minute pitch

Maison Veritas is a representative mid-sized Belgian chemicals manufacturer, built from official Eurostat sector statistics. It is a placeholder name; the data is real and cited, and every assumption is labelled.

The workbook answers two questions. First, which of six decarbonisation measures are worth doing, and in what order? Second, what will the company pay for carbon over the next ten years if it does nothing, and what if it acts?

The six measures are LED lighting, variable-speed drives, rooftop solar, a renewable electricity contract, a high-temperature heat pump and fleet electrification. Each gets an NPV, IRR, payback and a levelised abatement cost, and they are ranked on a MACC.

The headline results, in the default state:
- The six measures abate `Dash_AbatedSel` = 3,219 tCO2e a year on average, which is `Dash_Share` = 39.2% of Scope 1 and 2 emissions (`BL_S12_MB` = 8,204 tCO2e).
- On cash alone the portfolio NPV is `Dash_NPVFin` = -EUR 72,399, slightly negative. Adding the value of the avoided carbon cost lifts it to `Dash_NPVIncl` = EUR 2,519,250.
- Doing nothing costs `Dash_CostNotActingDisc` = EUR 10,076,534 in discounted carbon cost over the window, against `Expo_DiscWith_Sel` = EUR 9,019,888 after acting. The saving is `Expo_DiscAvoided_Sel` = EUR 1,056,646.
- The answer depends far more on which carbon price path comes true than on any technical input.

Anyone can click a cell, follow it back to a cited source or an analyst assumption, and change an input to see every result update. There are no macros and no Data Tables, so it works in Excel for the web.

## 2. Sheet-by-sheet tour

The tabs run in this order.

- **Cover**: title, version and the master check flag (`Chk_Master`, reads OK). Contents are hyperlinked.
- **ReadMe**: the model map and how to use the selectors, with links to trace a number.
- **Dashboard**: the one-page answer. Tiles for the headline figures (`Dash_NPVFin`, `Dash_NPVIncl`, `Dash_AbatedSel`, `Dash_CostNotActing`), the MACC, a bridge chart and a scenario chart. Click a tile to see its formula; it links to a named result elsewhere.
- **Inputs**: the only place with typed numbers. Each row has value, unit, price year, source id and status. The three yellow dropdowns are `Sel_Scenario`, `Sel_Basis` and `Sel_DirectETS`.
- **Sources**: the register of every source: dataset, URL, edition, retrieval date, licence note.
- **Baseline**: builds the firm. Firm value added (`BL_FirmVA`) over sector value added (`BL_SectorVA`) gives the scaling ratio `BL_RatioVA`, which shrinks sector energy use to one firm. Then it prices the energy and computes Scope 1 (`BL_Scope1` = 5,800 tCO2e) and Scope 2 on both bases (`BL_S2_LB` = 2,200 tCO2e, `BL_S2_MB` = 2,404 tCO2e).
- **Rates**: restates money into real 2025 euros using euro-area HICP, and derives the real discount rate `Rate_DiscountReal` = 5.7%.
- **Carbon**: Low, Central and High price paths to 2055, plus the market anchor and ETS2 parameters.
- **Measures**: the engine. One block per measure with cash-flow rows, discount factors, NPV, IRR, payback, abated tonnes and levelised cost.
- **MACC**: the sorted curve, tiers and the levelised reference line.
- **Exposure**: carbon cost by channel with and without acting, the bridge, and the ICP lens.
- **Sensitivity**: the price grid, rate strip, tornado, rank stability under higher hurdle rates.
- **Disclosure**: maps model outputs to IFRS S2 and revised ESRS E1 requirements. It states strength of support and never claims compliance.
- **Checks**: every reconciliation check, rolled up into `Chk_FailCount` and `Chk_Master`.
- **Notes**: scope, method choices, limitations, corrections, version log, Excel verification record.
- **Lists**: dropdown lists.

## 3. Key formulas

### NPV

What: all cash flows of a measure shrunk to today and added. The formula in words: each year's net financial cash flow times its discount factor, summed from year 0 (2026) to 2055. The factor for year n is 1 divided by (1 plus the rate) to the power n, and year 0 is not discounted. Click `M_LED_NPV` (= EUR 95,185) and trace its row on Measures. Why: it is the primary decision measure because it values size and timing together. Rate: `Rate_DiscountReal` = 5.7%.

### IRR

What: the rate that makes NPV zero. In words: the root of the NPV function, found by Excel's IRR. Click `M_LED_IRR` (= 10.0%) and `M_HP_IRR` (= -12.5%). Why it is secondary: cash flows that change sign more than once (replacement outlays) may have several roots, so the sheet prints a warning next to LED, VSD and Fleet (`M_LED_IRRFlag`). The contract has no upfront outlay, so IRR shows "n/a".

### Payback

Simple payback is the year the running total of undiscounted flows turns positive. Discounted payback does the same after discounting. The heat pump shows "Not within 2055" because it never pays back inside the horizon.

### Levelised abatement cost

In words: minus the NPV divided by the present value of the abated tonnes, using the same discount factors. Click `M_LED_LevCost` (= -EUR 220 per tCO2e) and `M_HP_LevCost` (= EUR 106 per tCO2e). Why levelised: measures with different lives and profiles land on one comparable number.

### Break-even carbon price

It is the same figure. It is the carbon price at which the measure's NPV including carbon value is exactly zero. It is closed form, so no Goal Seek is needed and it updates live. Check: the heat pump pays once carbon exceeds about EUR 106 per tonne.

### MACC widths and heights

Width is abated tonnes a year on the selected basis; height is levelised cost. Measures are sorted by cost with a RANK-based helper block. The chart is a native Excel area chart on a date-style axis, so the blocks have vertical edges. Click `MACC_TotalAbatement` (= 3,220 tCO2e); a check (`Chk_TileVsMACC`) compares like with like: the MACC width total against the measures shown on the MACC (`MACC_Data_Eligible` = 1), and the Dashboard tile against the net sum of all six. The tile is that net sum, so a measure with negative abatement (for example a fleet with a very high EV consumption) lowers the tile but is left off the MACC, and the master check stays OK.

### Scope 2: LB versus MB selection

One selector, `Sel_Basis`, feeds a CHOOSE/IF that picks the grid factor. The two bases are calculated from the same activity data and are never added. Under LB the renewable contract abates nothing.

### Carbon price path anchoring

The cash carbon price starts at the observed 2025 allowance average (`Carbon_EUA_Avg2025` = EUR 73) and slides linearly to the NGFS path by the convergence year (`Carbon_ETS1_ConvYear`, 2030). The weights on NGFS rise in equal steps. NGFS prices are in 2010 US dollars; they are converted with the 2010 exchange rate and euro-area HICP (`Carb_USDtoEUR2025`).

### Pass-through netting

Electricity cost from carbon = purchased MWh times the marginal emission factor times the pass-through rate times (ETS1 price minus the embedded 2025 allowance price). Only the change versus what the 2025 power price already holds is new. Under Low it can be negative.

### Cumulative and discounted exposure

Cumulative adds the nominal yearly bills (`Dash_CostNotActing` = EUR 13,870,507, undiscounted). Discounted applies the factors first (`Expo_DiscBAU_Sel`, same value as `Dash_CostNotActingDisc`). Use discounted to compare with NPVs. The Dashboard headline tile is the undiscounted cumulative sum and is labelled that way.

### The bridge

It starts at the discounted do-nothing bill and steps down by each measure's discounted avoided cost, ending at "After acting". The heat pump is the biggest step (`Expo_DiscAvoided_HP` = EUR 666,422). A check (`Expo_Check_BridgeSums`) confirms the steps add up.

### The closed-form sensitivity grid and the tornado

NPV is a straight line in each price. Each grid cell is the centre NPV plus (energy multiplier minus 1) times the present value of energy volume plus (carbon multiplier minus 1) times the present value of gross carbon. The centre cell equals `Sens_PortfolioNPV`; `Sens_Check_GridCentre` confirms it. The rate strip recomputes NPV directly at each rate (`Sens_RateNPV_1` = EUR 3,731,880 at `Sens_Rate_1` = 3.7%). The tornado moves each driver alone and sorts by swing.

### The ICP lens

Scope 1 and 2 tonnes on the selected basis times the internal price (`Carbon_ICP_Level` = EUR 100). Discounted: do nothing `Expo_ICP_DiscBAU` = EUR 6,475,078, after acting `Expo_ICP_DiscWith` = EUR 4,256,199, avoided `Expo_ICP_DiscAvoided` = EUR 2,218,879. It is never added to cash totals and is not in the NPV.

### Chk_Master

It reads OK only if every group of checks passes. `Chk_FailCount` counts failures (0 now). Click `Chk_Master` on Cover or Checks.

## 4. Method choices and rejected alternatives

- **Representative firm, not a real company.** A real firm's report would be a one-off, and gaps in its disclosure would force guesses. A scaled sector firm lets every number be traced to Eurostat; real data can replace the Base inputs without changing a formula. Rejected: Corbion and Belgian listed firms, which are larger or partly outside the EU ETS scope or unread.
- **Levelised cost, not an annuity.** The annuity form is kept as an internal check only. Levelised cost handles replacements and residual values cleanly.
- **Closed form, not Data Tables.** Data Tables cannot be created in Excel for the web and cannot be authored by the library. Rejected: Goal Seek and Solver for the same reason.
- **Anchored carbon prices, not raw NGFS.** NGFS values are model shadow prices far from the traded price today. Rejected: using NGFS from year 0, or using the market price flat for ever.
- **Discounted headline for comparisons, undiscounted for the Dashboard tile.** The tile follows the common reading of "what we pay"; the discounted figure is shown beside it and used wherever NPV is compared.
- **Incremental capex for heat pump and fleet.** The firm needs a boiler and vans anyway. The full-capex NPV is a memo (`M_HP_NPVFullCapex`).
- **Real discount rate.** Cash flows are in constant 2025 euros, so the rate is real, derived with the Fisher formula from a nominal cost of capital (`Fin_CoC_ChemSpecialty` = 7.8%) and long-run inflation (`Fin_InflationLongRun` = 2.0%).
- **Avoiding new Excel functions.** No XLOOKUP, LET, LAMBDA or dynamic arrays, so older Excel and the web version behave the same.

## 5. Limitations

These mirror the Notes sheet.
- The firm is representative. Real site data would change every number.
- Many technology inputs are analyst assumptions, labelled as such on Inputs.
- The MACC is a screening, not an optimiser. Kesicki and Ekins (2012) argue that MACCs hide barriers, split incentives and interactions, and that negative-cost measures are often not done in practice. The stack applies measures in a fixed order, so the split of electricity tonnes between measures depends on that order.
- NGFS prices are scenario values, not forecasts. The USD to EUR conversion assumes the dollar kept its 2010 real value; a US-CPI route would give higher prices.
- The EUA 2025 average is an analyst assumption because the underlying rows were not kept.
- ETS2 timing is politically uncertain. The model uses the delayed start (`Carbon_ETS2_StartYear` = 2028).
- Two sensitivities on Notes are computed in Python at build time and are not live cells.
- The Disclosure sheet maps outputs to requirements; it is not a compliance statement.
- Excel for the web: not verified. The final Excel review (GATE-B) passed in Excel desktop on 2026-10-26.

## 6. Interview questions

### Q1. Why is year 0 not discounted?
Year 0 is 2026, when the money is spent; a cash flow today is worth its face value. Operating flows start at the end of year 1 and are discounted from there. See the discount-factor row on Measures.

### Q2. Why can a negative-cost measure be undone?
The cost is net of savings but hides barriers: attention, disruption, split incentives (Kesicki and Ekins). VSD (`M_VSD_LevCost` = -EUR 722) and solar (`M_PV_LevCost` = -EUR 591) rest on analyst assumptions. Negative means "worth testing first", not "free".

### Q3. Why does the green contract save no cash?
The marginal power plant sets the price whatever certificates the firm holds. The contract changes reported MB emissions, not the bill. `Expo_DiscAvoided_RC` is zero and `Expo_Check_ContractZero` enforces it. Its NPV is `M_RC_NPV` = -EUR 368,799 because it costs money for a reporting benefit.

### Q4. Why is the ICP not in the NPV?
It is a decision lens, not an invoice. Putting it into NPV would count carbon twice, once as cash exposure and once as a shadow price. It is shown separately (`Expo_ICP_DiscAvoided` = EUR 2,218,879).

### Q5. Why levelised rather than annuity?
Levelised divides the present value of net cost by the present value of tonnes, so replacements, residual values and different lives are handled in one step. The annuity form is a cross-check of the same figure.

### Q6. What would change with real company data?
Replace the Base inputs (value added, energy use, fleet). Nothing else changes: every formula flows from them. Measure sizing, the stack and exposure all re-run.

### Q7. Why is the NPV excluding carbon negative while the NPV with carbon is positive?
Cash only: `Dash_NPVFin` = -EUR 72,399. The heat pump alone is `M_HP_NPV` = -EUR 1,177,292 and outweighs the winners. Adding the discounted avoided carbon cost (`Sens_PVCarbon` = EUR 2,591,649) gives `Dash_NPVIncl` = EUR 2,519,250. The case rests on the carbon price.

### Q8. Why is the heat pump IRR negative?
Electricity is dear relative to gas for this firm, so the pump has a negative operating cash flow and a high incremental capex. `M_HP_IRR` = -12.5%. It pays only above a carbon price of about `M_HP_LevCost` = EUR 106 per tonne.

### Q9. Why can the Low scenario cost of not acting be negative?
In Low the 2030 allowance price is below the embedded 2025 level, so the pass-through credit on electricity outweighs the fuel cost. See `Expo_DiscBAU_CP` = -EUR 203,756. Read Low as "carbon is nearly free".

### Q10. Why are LB and MB never added?
They count the same megawatt-hours in two ways. Adding double counts. The GHG Protocol asks for both side by side. Compare `BL_S2_LB` = 2,200 tCO2e with `BL_S2_MB` = 2,404 tCO2e.

### Q11. What does the Disclosure sheet deliberately not claim?
Compliance. It gives analyst classifications (Direct, Supports, Not covered) of how an output supports a requirement, with a verification status per reference. Unverified references are flagged as such.

### Q12. How does the 12-state test work?
Two bases times three scenarios times direct ETS Off or On gives 12 states. The workbook is built in each, and every formula is re-evaluated by an independent evaluator and compared with the reference model. All checks must be TRUE.

### Q13. Why does the Dashboard show undiscounted cumulative cost?
It is the plain "what we pay" total (`Dash_CostNotActing` = EUR 13,870,507). The discounted equivalent (`Dash_CostNotActingDisc` = EUR 10,076,534) sits beside it and is the one to compare with NPVs. The label states which is which.

### Q14. Why is the discount rate real?
Cash flows are in constant 2025 euros. A nominal rate would be inconsistent and penalise long-lived projects. `Rate_DiscountReal` = 5.7%.

### Q15. Why use the ECB target rather than current inflation?
Recent inflation is an energy-driven spike. A long-run model needs a long-run rate (`Fin_InflationLongRun` = 2.0%). The spike is a sensitivity.

### Q16. Why are NGFS prices anchored to the market?
NGFS values are shadow prices. The path starts at `Carbon_EUA_Avg2025` = EUR 73 and converges to NGFS by 2030, so early years match what allowances trade at.

### Q17. ETS1 or ETS2?
Never both (`Expo_Check_ETSExclusive`). A normal manufacturer pays through its fuel supplier under ETS2. Direct ETS1 applies to large installations above a thermal threshold of `Carbon_ETS1_ThermalThresholdMW` = 20 MW. Fleet diesel is always ETS2.

### Q18. How do you do sensitivities without Data Tables?
NPV is linear in prices, so each cell is the centre plus a multiplier times a present value, in plain formulas. The centre cell equals `Sens_PortfolioNPV`.

### Q19. What is the biggest uncertainty?
The carbon price path. Compare `Expo_DiscBAU_CP` = -EUR 203,756 with `Expo_DiscBAU_NZ50` = EUR 17,105,634 for do-nothing cost across the Low and High paths.

### Q20. What is wrong with the IRR for LED, VSD and Fleet?
Several sign changes mean the IRR may not be unique; the sheet flags it. For Fleet it is only `M_Fleet_IRR` = 0.7%. NPV is the decision measure.

### Q21. Is the MACC an optimiser?
No. It ranks by cost per tonne. It ignores budget limits, barriers and interactions beyond the stack. Ranking held at higher hurdle rates in the Sensitivity sheet (`Sens_RankStab_AnyChanged` is 0).

### Q22. How do you know the workbook is correct?
See section 7: an independent Python re-implementation, a formula-string evaluator, lint and scan tests, 12 states, and a scripted recalculation in Excel for Mac.

## 7. How the model was verified

- **Independent reference model.** A pure-Python re-implementation computes every result. The cached value in each formula cell comes from it, not from the workbook.
- **compare_cached.** A small evaluator re-computes every workbook formula from its literal inputs and compares with the cached value. It refuses, rather than guesses, where Excel and Python differ (text in arithmetic, ranges as scalars, chained comparisons).
- **Lint and scan.** Tests check write discipline (no typed numbers outside Inputs), unit vocabulary, internal links and a security scan.
- **12 states.** The same comparison in all selector combinations, with every check TRUE.
- **Excel desktop scripted check.** Recorded in `docs/EXCEL_CHECKS.md` and on Notes: Phase 3 default and six states, Phase 4 twelve states, no mismatches and no error values.
- **GATE-B.** On 2026-10-26, 12 states were recalculated in Excel desktop with no mismatches and the master flag OK, and the user approved the visual review in Excel desktop. Excel for the web: not verified.
- **This document.** A test rebuilds the workbook and checks every number below against it.

## Figures quoted

Rule: eur0 = thousands separators, no decimals, prefixed "EUR " (minus sign first when negative); t0 = thousands separators, no decimals, suffixed " tCO2e"; pct1 = one decimal, percent; int = plain integer.

| Name | Value as written | Rule |
|---|---|---|
| `Dash_NPVFin` | -EUR 72,399 | eur0 |
| `Dash_NPVIncl` | EUR 2,519,250 | eur0 |
| `Sens_PVCarbon` | EUR 2,591,649 | eur0 |
| `Dash_CostNotActing` | EUR 13,870,507 | eur0 |
| `Dash_CostNotActingDisc` | EUR 10,076,534 | eur0 |
| `Expo_DiscWith_Sel` | EUR 9,019,888 | eur0 |
| `Expo_DiscAvoided_Sel` | EUR 1,056,646 | eur0 |
| `Dash_CostAvoided` | EUR 1,473,267 | eur0 |
| `Dash_Share` | 39.2% | pct1 |
| `Dash_AbatedSel` | 3,219 tCO2e | t0 |
| `MACC_TotalAbatement` | 3,220 tCO2e | t0 |
| `BL_S12_MB` | 8,204 tCO2e | t0 |
| `BL_S12_LB` | 8,000 tCO2e | t0 |
| `BL_Scope1` | 5,800 tCO2e | t0 |
| `BL_S2_MB` | 2,404 tCO2e | t0 |
| `BL_S2_LB` | 2,200 tCO2e | t0 |
| `M_LED_NPV` | EUR 95,185 | eur0 |
| `M_VSD_NPV` | EUR 156,074 | eur0 |
| `M_PV_NPV` | EUR 1,296,040 | eur0 |
| `M_RC_NPV` | -EUR 368,799 | eur0 |
| `M_HP_NPV` | -EUR 1,177,292 | eur0 |
| `M_Fleet_NPV` | -EUR 73,606 | eur0 |
| `M_LED_IRR` | 10.0% | pct1 |
| `M_VSD_IRR` | 42.8% | pct1 |
| `M_PV_IRR` | 18.8% | pct1 |
| `M_HP_IRR` | -12.5% | pct1 |
| `M_Fleet_IRR` | 0.7% | pct1 |
| `M_LED_LevCost` | -EUR 220 | eur0 |
| `M_VSD_LevCost` | -EUR 722 | eur0 |
| `M_PV_LevCost` | -EUR 591 | eur0 |
| `M_RC_LevCost` | EUR 12 | eur0 |
| `M_HP_LevCost` | EUR 106 | eur0 |
| `M_Fleet_LevCost` | EUR 148 | eur0 |
| `Rate_DiscountReal` | 5.7% | pct1 |
| `Fin_CoC_ChemSpecialty` | 7.8% | pct1 |
| `Fin_InflationLongRun` | 2.0% | pct1 |
| `Carbon_EUA_Avg2025` | EUR 73 | eur0 |
| `Carbon_ICP_Level` | EUR 100 | eur0 |
| `Carbon_ETS2_StabPrice` | EUR 45 | eur0 |
| `Expo_ICP_DiscBAU` | EUR 6,475,078 | eur0 |
| `Expo_ICP_DiscWith` | EUR 4,256,199 | eur0 |
| `Expo_ICP_DiscAvoided` | EUR 2,218,879 | eur0 |
| `Expo_DiscBAU_CP` | -EUR 203,756 | eur0 |
| `Expo_DiscBAU_NZ50` | EUR 17,105,634 | eur0 |
| `Expo_DiscAvoided_HP` | EUR 666,422 | eur0 |
| `Sens_RateNPV_1` | EUR 3,731,880 | eur0 |
| `Sens_Rate_1` | 3.7% | pct1 |
| `Carbon_ETS1_ThermalThresholdMW` | 20 | int |

