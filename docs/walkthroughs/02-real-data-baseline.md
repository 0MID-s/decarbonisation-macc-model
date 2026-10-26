# Phase 2 walkthrough: the real-data baseline

This note explains what Phase 2 built, in plain words. Every number below is copied from the built workbook (`dist/maison_veritas.xlsx`) or from the input config. The cell or input id is named next to it, so you can click and check.

Two words used throughout:
- **Input**: a number typed in once on the Inputs sheet, with its source.
- **Formula**: a cell that calculates from inputs. Change an input and every formula that uses it updates.

## What this phase built

**Inputs.** The one place where every number lives. Each row has the published value, its unit, a conversion factor, the model value, the price year, the source id and a status (sourced or analyst assumption). Blue-on-yellow cells are typed inputs. Nothing else in the workbook contains a typed number.

**Sources.** The register of where the data comes from: Eurostat (company and energy statistics), the EEA and AIB (electricity emission factors), UK DESNZ (fuel emission factors), NGFS via IIASA (carbon prices), Damodaran (cost of capital) and others. Each source has a dataset name, URL, edition, retrieval date and licence note.

**Baseline.** Builds "Maison Veritas" as a representative Belgian chemicals firm (NACE C20, 50 to 249 staff). It takes the size-class value added (Baseline D9, EUR 2,536.48 m) and divides by the number of firms (D7, 110) to get one firm's value added (D11, EUR 23.06 m). It divides by the sector value added (D15, EUR 25,831.28 m) to get a scaling ratio (D16, 0.000893, named `BL_RatioVA`). That ratio shrinks the whole sector's energy use to one firm: total 40,200 MWh (E28). Then it prices the energy and computes emissions: Scope 1 of 5,800 tCO2e (D70) and Scope 2 of 2,199.5 tCO2e location-based (D83) or 2,403.9 tCO2e market-based (E83).

**Rates.** Two jobs. First, it restates money from other price years into EUR 2025 using the euro-area price index (HICP), so every euro amount is comparable. Second, it derives the discount rate (Rates D21 to D23): a nominal cost of capital of 7.811% (`Fin_CoC_ChemSpecialty`) becomes a real rate of 5.70% (`Rate_DiscountReal`).

**Carbon.** Three carbon price paths to 2055 (Low, Central, High), each converted into EUR 2025, plus the 2025 EU allowance (EUA) price used as a market reference and the ETS2 parameters (start year 2028, which fuels are covered). Each path has an "anchor-year check" row that reads OK or ERROR (explained below).

**Notes.** What the model does not do or cannot know: limitations, exclusions, the NGFS licence wording, and every input that was transcribed by hand.

## How to trace a number

### 1. Scope 2, market-based (Baseline E83 = 2,403.9 tCO2e)
1. Click Baseline E83. It is `=SUM(E81:E82)`: purchased electricity plus purchased heat.
2. E81 is `=BL_Elec_MWh*E80`: 12,016 MWh times the factor in E80.
3. E80 is `=EF_ResidualMB` = 0.17101 tCO2e/MWh. Go to the Inputs sheet, row `EF_ResidualMB`. The Source ID column says `Src_AIBResidualMix`.
4. On the Sources sheet, `Src_AIBResidualMix` names the Association of Issuing Bodies residual-mix file and its URL.

### 2. Firm gas use (Baseline E21 = 15,502 MWh)
1. E21 is `=D21*BL_RatioVA`: sector gas (D21, 17,365,524 MWh) times the scaling ratio (D16, 0.000893).
2. `BL_RatioVA` is firm value added over sector value added (D16 = `BL_FirmVA/BL_SectorVA`).
3. Both come from Eurostat inputs on the Inputs sheet (`Base_SBS_*` rows from the structural business statistics). The sector gas figure comes from the Eurostat energy balance rows (source `Src_EurostatEnergyBalance`).

### 3. Central carbon price in 2030 (Carbon R34 = EUR 226.18 per tCO2)
1. Carbon R34 (column R is the year 2030) is the interpolation formula for the Central path (named `Path_Carbon_NDC`, N34:AQ34). It reads two helper rows above it: R32 (the year to use) and R33 (which NGFS point comes just before that year).
2. The NGFS points ("anchors") for Central sit in rows 28 to 31. Row 28 holds the anchor years (D28 to J28), row 31 the prices in EUR 2025. E31 = 226.18 is the 2030 point.
3. E31 comes from E30 times the HICP ratio (D13, 1.3823). E30 comes from E29 times D12 (1 divided by 1.3257 US dollars per euro, 0.7543).
4. E29 = US$216.91 per tonne (2010 dollars) links to the Inputs series `Carbon_NGFS_NDC` (Inputs rows 122 to 124), source `Src_NGFSPhaseV` (NGFS Phase V, model REMIND-MAgPIE 3.3-4.8, region OECD & EU).
5. Combined conversion factor: D14 = 1.0427 (`Carb_USDtoEUR2025`).

## Why these choices

**Value added as the yardstick.** The sector data covers a whole country. To shrink it to one firm, I need a size measure that fits money-making activity. Value added (revenue minus bought-in goods) tracks how much a firm does, better than headcount. The energy balance covers both chemicals (C20) and pharmaceuticals (C21), so the sector value added is the sum of both (D15). The C20-only ratio (D17, 0.002588) and a turnover-based ratio (D19, 0.001237) are shown as memos.

**MWh on a net calorific value (NCV) basis.** Gas can be measured with or without the energy in the water vapour of the flue gas. Gross (GCV) includes it, net (NCV) does not. Eurostat energy balances use NCV. Gas prices are quoted on GCV. The model converts using the ratio of 1.108 (D43). Mixing the two would overstate gas use by about 11%.

**Why the air-accounts cross-check does not match exactly.** Eurostat's air emissions accounts for the sector, scaled to one firm, give 8,402 tCO2e (D74). My bottom-up combustion figure is 5,754 tCO2e (D68), 68% of that (D76). The accounts include process emissions (for example ammonia and nitric acid plants) and other gases that a household-products firm would not have. So the gap is expected, and the model does not force a match.

**Why location-based and market-based Scope 2 are never added.** They are two ways of reporting the same electricity. Location-based uses the national grid average (`EF_GridLB`, 0.154 tCO2e/MWh). Market-based uses the supplier or residual mix (`EF_ResidualMB`, 0.17101). Adding them would count the same megawatt-hours twice. The GHG Protocol asks for both to be reported side by side. Baseline row 87 gives one total per basis.

**Real versus nominal money, EUR 2025 and the Fisher formula.** Nominal money includes inflation. Real money is measured in the purchasing power of one fixed year (here 2025). The model works in real EUR 2025, so the discount rate must be real too. Damodaran's cost of capital is nominal. The Fisher formula converts: real = (1 + nominal) / (1 + inflation) - 1. With nominal 7.811% and inflation at the ECB 2.0% target (`Fin_InflationLongRun`), real = 5.70% (Rates D23). The Damodaran Euros column assumes 1.5% inflation, so using 2.0% gives a slightly lower real rate. This is stated on Rates and in Notes. Memo rows show the Basic (3.08%, D24) and Diversified (5.50%, D25) chemical groups.

**Why NGFS prices are converted with the 2010 exchange rate and then euro-area inflation.** The NGFS price is in 2010 US dollars. Step one: divide by 1.3257 US dollars per euro, the 2010 average (Eurostat), to get 2010 euros. Step two: multiply by euro-area HICP 2025 over 2010 (D13, 1.3823) to get 2025 euros. Combined factor 1.0427 (D14). The limitation: this assumes the dollar kept its 2010 real value against the euro. A US-CPI route would give a factor of about 1.31, so prices about 25% higher. That 1.31 is an indicative analyst estimate (its inputs are logged in docs/DATA_LOG.md, but it is not a sourced figure and is not used in the model). It is a candidate sensitivity in Phase 4. NGFS prices are also model shadow prices (the carbon price needed for the model to hit its target), not market prices.

**The EUA anchor.** An EUA is one EU Emissions Trading System allowance, the right to emit one tonne of CO2. The 2025 average price (`Carbon_EUA_Avg2025`, EUR 73.43, Inputs G99, shown on Carbon D48) sits beside the scenarios as a market reference. Gaps (market minus NGFS 2025 value): Low +49.15, Central -53.33, High -85.46 (Carbon D49 to D51). A positive gap means the market is above the scenario; a negative gap means the scenario is above the market. The scenarios are not adjusted to the market price. How to blend the short run is a Phase 4 decision (D-29). The 73.43 figure is an analyst assumption (see below), so treat the gaps as indicative.

**Why the NGFS point years are fixed cells, and what the anchor check does.** NGFS publishes a price only every five years (2025, 2030, 2035 and so on); the model draws straight lines between these points. Originally the point years were read from the timeline header, so changing "First model year" would have silently relabelled the 2030 price as 2031. Now each point year is a fixed, locked cell on Inputs (the "point year (fixed)" rows, for example Inputs row 124 for Central). It is styled as a constant, not as a blue-on-yellow input, because it is source metadata (the year NGFS published the price), not a lever. The Carbon sheet links to those cells. The anchor check (Carbon D25, D35, D45) reads OK only when three things hold: each anchor year equals the NGFS publication year from the config (the locked reference row just below each check, Carbon D26:J26, D36:J36 and D46:J46), the years rise in order, and the first point year is before the first model year. Otherwise it reads ERROR. So if someone types 2026 over the 2030 point year, the years still rise (2025, 2026, 2035), but the check turns red. If you change First model year to 2027 the paths re-interpolate correctly and the checks stay OK. If you set it to 2025 or earlier, the checks show ERROR, because the rule is strict: the first NGFS point (2025) must come before the first model year, not on it. At exactly 2025 the paths still calculate, since 2025 is itself an NGFS point; before 2025 they also return #N/A, because the model would need a price before the first NGFS point.

## What is an assumption, not data

- **The fleet block** (Baseline rows 55 to 57): the number of vehicles (10) and the distance (25,000 km a year) are analyst assumptions, because Eurostat has no fleet data for a firm this size. The 184.9 g CO2 per km is not an assumption: it is the EEA figure for new vans in 2024 (status Sourced, re-read on 2026-10-20).
- **The flat grid factor and flat residual mix paths.** No sourced Belgian projection was found on an approved source, so both are held at the latest values (an accepted deviation under D-23 and D-38, in Notes).
- **The EUA 2025 average (EUR 73.43).** The value was computed from EEX auction results, but the underlying rows were not kept, so it carries the status "Analyst assumption" (unverified transcription) until someone re-supplies the rows.
- **Legal parameters that were not read in the legal text.** "Sourced" now means the sentence was read in the EU legal text, but in the wording that was read, not necessarily today's consolidated law. Sourced: the ETS2 start year 2028 (Regulation 2026/667), the EUR 45 stability price, the two-month trigger and the 20 million release (Directive 2003/87/EC Art. 30h(2)), and the triple-price trigger and its release (Art. 30h(3)), all read in Dir. (EU) 2023/959 as enacted, with the later 2026 amendments not checked; and the 20 MW combustion threshold for the main EU market, read in the original 2003 Annex I wording, with the consolidated text not read. The Inputs notes for these rows start with "Text read: ..." to say exactly this. Analyst assumption: the originally enacted ETS2 start year (2027), every fuel-scope flag (gas, LPG, naphtha, other fuels, road diesel, electricity, heat), and the flag that the energy balance covers chemicals and pharmaceuticals together.
- **The UK heat factor** used as a Belgian proxy for purchased heat (DESNZ).
- **ICCT-anchored electric vehicle values**, where the fleet measure uses the study's trucks and delivery vans as a stand-in.
- **The RVO price year**, assumed to be the list year.
- **No size or illiquidity premium** on the discount rate.

## Likely reviewer questions

1. **Why value added, not turnover, to scale the sector?** Value added measures real activity and is less distorted by pass-through of raw material costs. Turnover is shown as a memo (D19) and gives a ratio about 39% higher; both are visible.
2. **What is NCV versus GCV, and why does it matter?** GCV counts the heat from condensing flue-gas water vapour, NCV does not. Eurostat uses NCV, gas prices use GCV. I convert with a ratio of 1.108 from DESNZ factors so energy and price are consistent.
3. **Your bottom-up emissions are lower than the Eurostat accounts. Why?** The accounts include process emissions and other gases from large chemical plants. Combustion is 68% of the scaled figure, and I do not force a reconciliation.
4. **Why are location-based and market-based Scope 2 never added?** They describe the same electricity with different factors. Adding them double counts. The GHG Protocol requires dual reporting, not summing.
5. **Why is the discount rate real?** The cash flows are in constant 2025 euros, so discounting at a nominal rate would be inconsistent and would penalise long-lived projects. Fisher converts the nominal 7.811% to 5.70% at 2.0% inflation.
6. **Why use the ECB 2% target rather than recent inflation?** Euro-area inflation was 3.8% in September 2026 (Rates D26), an energy-driven spike. A long-run model needs a long-run rate. The spike is shown on Rates as context only; it is not used in any calculation and is not varied on the Sensitivity sheet (the discount-rate tornado driver moves the real rate by plus or minus 2 points).
7. **What are the NGFS carbon prices, and can you rely on them?** They are model shadow prices, the cost of the last tonne abated in the model, from NGFS Phase V (REMIND-MAgPIE, OECD & EU region). They are scenario inputs, not forecasts. I show Low, Central and High and do not blend them with the market price.
8. **How did you convert US dollars from 2010 into euros from 2025?** Divide by the 2010 average exchange rate of 1.3257 US dollars per euro, then multiply by euro-area HICP 2025 over 2010. The factor is 1.0427. The weak point is the assumption that the dollar held its 2010 real value; a US-CPI route would give about 1.31.
9. **Why does the Central scenario sit above today's EUA price, and the Low scenario far below it?** The EUA 2025 average is EUR 73.43. The Central 2025 NGFS value is EUR 126.76, so Central is above the market (gap -53.33), and High (158.90) is further above (gap -85.46). Only Low (24.28) is below the market, by about 49 euros (gap +49.15), so Low is not a credible short-run price. The NGFS values are model shadow prices, not market quotes. How to bridge the short run is a Phase 4 decision (D-29); the model keeps all four numbers visible rather than hiding the gap.
10. **How do you know the formulas are right?** Two independent checks. First, the values stored in the file come from a separate Python reference model, not from the workbook formulas. Second, a test re-calculates every formula in the workbook from its inputs with a small evaluator I wrote (all 900 formulas, no mismatches) and checks it gives the same numbers, so a wrong cell reference would be caught. Where Excel and Python behave differently (text in arithmetic, a whole range used as one number, chained comparisons such as a<b<c, INDEX on a two-dimensional block), the evaluator refuses with an error instead of guessing, and it compares text without regard to case, as Excel does. Another test changes First model year and checks that the carbon paths still line up with the NGFS points, and a third types 2026 over the 2030 point year and checks that the anchor check turns to ERROR. I did not use Excel to recalculate the workbook. Formulas use only plain functions (INDEX, MATCH, MIN, MAX, SUM, IF), so the workbook opens in Excel desktop and Excel for the web.
11. **What is ETS2, and when does it start?** A second EU carbon market for fuels used in buildings and road transport, covering fuel suppliers. The start was postponed to 2028 by Regulation (EU) 2026/667 (Carbon D55). Natural gas, LPG and road diesel are in scope; electricity and heat are not.

## What comes next in Phase 3

Phase 3 builds the decarbonisation measures themselves (heat pumps, rooftop PV, LED lighting, motor drives, fleet electrification and so on). Each measure gets cash flows, NPV, IRR, payback and abatement cost, discounted at `Rate_DiscountReal` and priced from the Baseline figures. Phase 3 also checks the workbook's formulas against the reference model, and prepares the marginal abatement cost curve. Phase 4 then applies the three carbon price paths to the exposure, with and without acting, and runs the sensitivities flagged above.
