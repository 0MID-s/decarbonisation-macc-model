# Phase 3 walkthrough: the measures engine and the MACC

This note explains what Phase 3 built, in plain words. Every number below comes from the reference model (`checkmodel/measures_reference.py`) in the default state (market-based, Central scenario), and equals what the workbook (`dist/maison_veritas.xlsx`) shows in that state. Euro amounts are real EUR 2025. Named cells are given so you can click and check.

Words used throughout:
- **Measure**: one decarbonisation action (for example replacing lights with LEDs).
- **NPV (net present value)**: all future money in and out, shrunk to today's value, then added up. Positive means the measure earns more than the cost of money.
- **Discount rate**: the yearly "shrink" rate. Here it is the real rate `Rate_DiscountReal`, 5.697%.
- **tCO2e**: tonnes of carbon dioxide equivalent.
- **Abatement cost**: the net cost, in EUR, of avoiding one tonne. Negative means the measure saves money while it cuts emissions.

## 1. The two dropdowns

On the Inputs sheet, two yellow cells sit at the top:
- **Sel_Scenario** (Inputs G8): Low, Central or High carbon price path (NGFS Current Policies, NDCs, Net Zero 2050). Default Central.
- **Sel_Basis** (Inputs G9): Location-based or Market-based electricity emissions. Default Market-based.

Click the cell, click the small arrow, pick a value. Every result on Measures and MACC follows.

What each one changes:
- The **scenario** changes only the carbon price. That moves the carbon value of each measure, the levelised reference line on the MACC (Low 24.4, Central 216.4, High 536.0 EUR/tCO2e) and the tiers. It does not change any cash flow, NPV, IRR or payback.
- The **basis** changes how electricity tonnes are counted. Location-based uses the national grid average (0.154 tCO2e/MWh). Market-based uses the residual mix (0.17101 tCO2e/MWh), which is what a supplier contract can change. The basis moves tonnes, so it moves abatement cost and the ranking, but not the cash NPV.

## 2. One measure from start to finish: LED lighting

**Sizing.** How much electricity does LED save? Three analyst assumptions multiply the firm's electricity use:
- electricity use 12,016 MWh a year (from the Baseline sheet),
- times the lighting share of electricity, `Meas_LED_LightingShare` = 6%,
- times the share of lighting converted, `Meas_LED_Coverage` = 50%,
- times the saving rate of converted lights, `Meas_LED_SavingRate` = 50%.

12,016 x 0.06 x 0.5 x 0.5 = 180.24 MWh a year saved (`kwh_saved` 180,240 kWh).

**Value of the saving.** The firm's electricity price is EUR 161.5 per MWh (Eurostat, band ID, 2025 average, excluding VAT). 180.24 x 161.5 = EUR 29,109 a year.

**Cost.** Capex is EUR 220,293, paid in year 0 (2026). It is a full cost, because the firm gets nothing it would have bought anyway.

**Life.** LED lasts 15 years (`Meas_LED_Life`). So the lights are replaced in 2041 at the same real cost (no learning-curve decline assumed). In 2055, the last year of the model, 14 of the second set's 15 years are used, so one fifteenth of its value is left. That is credited as a residual value: 220,293 / 15 = EUR 14,686.

**The cash-flow rows on the Measures sheet.** For each measure the sheet has these money rows, year by year (labels as on the sheet):
1. Capex (initial and replacements): negative in 2026 and 2041,
2. Subsidy (initial capex only): zero by default,
3. Residual value: positive in 2055,
4. Change in O&M: zero for LED,
5. Energy saving, electricity (also gas and diesel rows, zero for LED): EUR 29,109 a year,
6. Net financial cash flow: rows 1 to 5 added,
7. Carbon value at the selected scenario (shadow-price lens, not cash),
8. Cash flow including carbon value.
Below them come the discounted and cumulative rows that feed NPV and payback.

**Discount factor.** The factor for year n is 1 / (1 + 0.05697)^n. Year 0 (2026) is 1.0000, year 1 (2027) is 0.9461, year 15 (2041) is 0.4356, year 29 (2055) is 0.2005. Money far away counts for less.

## 3. Rebuild the LED NPV by hand

Open a blank sheet or take paper and a calculator. The answer should land on the model's `M_LED_NPV`, EUR 95,185.

Step 1. Start with year 0 (2026): capex = -220,293.

Step 2. Savings. EUR 29,109 arrives at the end of each year from 2027 to 2055, which is 29 years. The factors for those 29 years add up to 14.0331. So the present value is 29,109 x 14.0331 = EUR 408,485.

(To do it the long way, in a spreadsheet: type 29,109 in 29 rows, give each the factor 1/1.05697^n for n = 1 to 29, add them. You get the same number.)

Step 3. Replacement in 2041 (n = 15): -220,293 x 0.4356 = -EUR 95,953.

Step 4. Residual in 2055 (n = 29): +14,686 x 0.2005 = +EUR 2,945.

Step 5. Add up: -220,293 + 408,485 - 95,953 + 2,945 = **EUR 95,185** (give or take a euro of rounding).

Compare with the model:
- `M_LED_NPV` = 95,185.
- Positive NPV: LED earns more than the 5.697% cost of money. It beats doing nothing.

Extra: try the same with the discount rate at 0%. You just add the cash flows: -220,293 + 29 x 29,109 - 220,293 + 14,686 = 418,000 or so. The higher the rate, the more the far-away savings shrink.

## 4. IRR, payback and why the IRR carries a warning

**IRR (internal rate of return).** The discount rate at which the NPV becomes exactly zero. For LED it is 10.04% (`M_LED_IRR`). Above the 5.697% hurdle, so consistent with a positive NPV.

**Multiple sign changes.** Read the net cash flow of LED: negative in 2026, positive for 14 years, negative in 2041 (the replacement outweighs that year's saving), positive again, with a small residual at the end. The sign flips three times. A series like that can have more than one rate that gives NPV = 0, so the IRR may not be unique. The workbook flags this in words next to the IRR for LED (3 changes), VSD (3 changes) and Fleet (7 changes). Heat pump (1) and PV (1) are clean. The renewable electricity contract has no upfront outlay, so IRR and payback show "n/a (no upfront outlay)".

Rule of thumb for the interview: NPV is the decision measure. IRR is a supporting measure and not reliable when the sign flips more than once.

**Payback.** Years until the money put in has come back.
- Simple payback (no discounting): LED 7.6 years.
- Discounted payback (each year's flow shrunk first): LED 10.2 years.
The heat pump shows "Not within 2055": it never pays back inside the model horizon.

## 5. Abatement cost and the break-even carbon price: the same number

Each measure avoids tonnes of CO2e every year. Discount those tonnes with the same discount factors (the "present value of tonnes", LED 432.5 tonnes) and divide the negative NPV by it.

LED: -95,185 / 432.5 = **-220.06 EUR/tCO2e** (`M_LED_LevCost`).

Reading it:
- A negative abatement cost means the measure saves money and cuts carbon.
- The same figure is the **break-even carbon price**: the carbon price at which the measure's NPV (cash plus the value of the avoided carbon) is exactly zero. For LED that is -220, because LED has a positive NPV even if carbon were free. Carbon would have to cost -220 EUR per tonne to wipe out the gain. For a measure with a positive figure, the break-even is the price carbon must reach to make the measure pay.
- The workbook computes it in closed form (no Goal Seek), so it updates live and works in Excel for the web. A check (`M_Check_<measure>_BreakEven`) then recomputes the NPV including carbon value at that constant price straight from the yearly rows and confirms it is zero.

Carbon value is a **shadow-price lens**: tonnes times the selected scenario price, shown as "NPV including carbon value" (LED EUR 188,793). It is not cash. What the firm actually pays for carbon, channel by channel, is Phase 4.

## 6. The stack and why the contract is zero under location-based

Several measures act on the same 12,016 MWh of electricity, so they cannot all take the same MWh. The Measures sheet applies them in one fixed order, a "stack":
1. Efficiency (LED, then VSD) cuts electricity use.
2. Electrification: the heat pump adds electricity use (it replaces gas heat with electric heat) and the electric fleet adds some.
3. Rooftop PV supplies part of what is left, so it is limited to what remains after the first steps.
4. The renewable electricity contract (Guarantees of Origin) covers the residual.

Each step works on what the step before left behind. That is why results are not fully independent: swap the order and the split between measures changes (the total tonnes do not).

**Why the contract is zero under location-based.** A guarantee of origin does not change what the national grid emits. Location-based reporting uses the grid average, so buying certificates changes nothing. Under market-based reporting the contract makes the electricity count as renewable, so it abates 2,194 tCO2e a year on average. With the location-based switch on, the contract's tonnes row is zero (`M_RC_tLB` is all zeros) and its abatement cost shows "n/a (no abatement on this basis)". The two bases are never added together, because they describe the same MWh in two ways.

## 7. The heat pump and the electricity-to-gas price ratio

The heat pump replaces gas heat up to 125 C. In Belgium for this firm, electricity costs EUR 161.5 per MWh and gas (net calorific basis) EUR 54.6 per MWh, a ratio of 2.96. A high-temperature heat pump gives roughly 2.7 units of heat per unit of electricity (`Meas_HP_COP_HT`). So each MWh of heat costs more with electricity than with gas: 161.5 / 2.7 = EUR 59.8, against 54.6 for gas, before boiler losses and O&M.

The result:
- Net operating cash flow is negative, about -EUR 21,191 a year.
- Capex is incremental: EUR 721,309 above the gas boiler the firm would buy anyway (a full-capex memo is EUR 779,793).
- NPV is -EUR 1,177,292 and the IRR is -12.5%.
- Abatement cost is +106 EUR/tCO2e (789 tCO2e a year avoided, market-based).

So the heat pump is **not** a negative-cost measure. It only pays off once carbon is priced above about 106 EUR/tCO2e. At the Central reference price of 216.4 it is worth doing; at Low (24.4) it is not. If electricity became cheaper relative to gas, the number would fall quickly. This is the single most price-sensitive result in the model.

## 8. Reading the MACC chart and the tiers

The MACC (marginal abatement cost curve) sorts measures from cheapest to dearest per tonne. Each measure is a block: **width** is the tonnes it avoids per year, **height** is its abatement cost. Negative blocks sit below the zero line.

**Which measures get a block.** A measure is drawn only if it abates on the selected basis, and the workbook tests that with one rule: both the present value of its abated tonnes (the denominator of the abatement cost) and its average annual abated tonnes (the block width) must be above zero (`M_<measure>_Eligible` = 1). If either is zero or negative, the measure stays in the ranked table as "n/a", ranks last and gets zero width. Using one rule for the flag and the width means no block can ever have a negative width, even after an extreme input edit such as a fast-rising grid factor.

Default order (market-based, Central), in EUR per tCO2e:
1. VSD (variable-speed drives): -722
2. PV (rooftop solar): -591
3. LED: -220
4. Renewable electricity contract: +12
5. Heat pump: +106
6. Fleet electrification: +148

The horizontal reference line is a **levelised carbon price**: the single constant price that has the same present value as the whole Central price path over the model years. It is 216.4 EUR/tCO2e (Low 24.4, High 536.0). A measure below the line costs less per tonne than carbon is expected to be worth.

Tiers, from the workbook:
- **Do first**: abatement cost below zero (VSD, PV, LED).
- **Next**: positive, but at or below the reference line (contract, heat pump, fleet).
- **Later**: above the line, or no abatement on this basis (the contract under location-based).

The MACC is a **screening, not an optimiser**. It ranks by cost per tonne. It does not pick the best budget-constrained portfolio, it does not model interactions beyond the stack, and it leaves out barriers and hidden costs. Kesicki and Ekins (2012) make this point: negative-cost measures often are not done in practice because of attention, disruption and information costs not in the numbers.

## 9. Ten likely interview questions

**1. Why is year 0 not discounted?** Year 0 is 2026, when the money is spent. A cash flow today is worth its face value, so its discount factor is 1. Operating flows start at the end of year 1 (2027) and are discounted from there.

**2. Why incremental capex for the heat pump and fleet but full capex for LED?** The firm needs a boiler and vans anyway, so the real decision is the extra cost over what it would otherwise buy (the usual MACC convention). LED, VSD and PV replace nothing the firm must buy. The full-capex NPV is shown as a memo for transparency.

**3. Location-based or market-based, and which is the headline?** Location-based uses the grid average, market-based reflects the supplier or contract. CSRD/ESRS and the GHG Protocol ask for both. The workbook defaults to market-based as the headline and lets you flip to location-based. They are never added together.

**4. Are negative-cost measures really free money?** Not necessarily. Kesicki and Ekins (2012) argue that negative costs often hide barriers: hidden costs, split incentives, limited attention. Here VSD (-722), PV (-591) and LED (-220) are negative, but each rests on analyst assumptions that Phase 4 will stress.

**5. What is wrong with the IRR for LED, VSD and Fleet?** Their cash flows change sign more than once (replacement outlays in the middle), so the IRR may not be unique. The workbook flags it. NPV is the primary decision measure.

**6. Is the MACC an optimiser?** No. It is a cost-ranked screening. It ignores budget limits, interactions beyond the fixed stack and barriers. It tells you what is cheap per tonne, not the best portfolio.

**7. Why is the reference line a levelised price?** A carbon price path changes by year, but a measure's abatement cost is one number. The levelised price gives the one constant price with the same discounted value as the path, so the two are comparable on one chart.

**8. What changes with the scenario and what changes with the basis?** The scenario changes only the carbon price: the reference line, the carbon value and the tiers. The basis changes the tonnes counted, so it changes the abatement costs and the ranking (the contract drops out under location-based). Neither changes the cash NPV.

**9. What are the limits of the stack?** It fixes one order (efficiency, electrification, PV, contract), so the split of electricity tonnes between measures depends on that order and the measures are not fully independent. The totals do not depend on the order.

**10. How do you know the workbook is correct?** An independent Python re-implementation of the whole model computes every result. For each of the six selector states (two bases times three scenarios) the workbook is built, and every formula cell on every sheet is re-evaluated by an independent evaluator and compared with the reference value (QA-02). A mismatch fails the test. Because Excel recalculates on opening, the reviewer sees the same numbers.

## What to do next

Rebuild the LED NPV by hand (section 3). If your answer is within a few euros of 95,185 you understand the core mechanic behind every other measure: the same money rows, the same discount factors, different cash flows.
