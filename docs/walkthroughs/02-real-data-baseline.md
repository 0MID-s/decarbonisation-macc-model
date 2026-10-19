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

**Carbon.** Three carbon price paths to 2055 (Low, Central, High), each converted into EUR 2025, plus the observed 2025 EU allowance price and the ETS2 parameters (start year 2028, which fuels are covered).

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

### 3. Central carbon price in 2030 (Carbon R32 = EUR 226.18 per tCO2)
1. Carbon R32 is the interpolation formula. Look up two rows: R30 (the year, 2030) and R31 (which NGFS point to use).
2. The EUR 2025 anchors sit in row 29 (D29 to J29). E29 = 226.18 is the 2030 point.
3. E29 comes from E28 times the HICP ratio (D13, 1.3823). E28 comes from E27 times D12 (1 divided by 1.3257 US dollars per euro, 0.7543).
4. E27 = US$216.91 per tonne (2010 dollars) links to the Inputs series `Carbon_NGFS_NDC`, source `Src_NGFSPhaseV` (NGFS Phase V, model REMIND-MAgPIE 3.3-4.8, region OECD & EU).
5. Combined conversion factor: D14 = 1.0427.

## Why these choices

**Value added as the yardstick.** The sector data covers a whole country. To shrink it to one firm, I need a size measure that fits money-making activity. Value added (revenue minus bought-in goods) tracks how much a firm does, better than headcount. The energy balance covers both chemicals (C20) and pharmaceuticals (C21), so the sector value added is the sum of both (D15). The C20-only ratio (D17, 0.002588) and a turnover-based ratio (D19, 0.001237) are shown as memos.

**MWh on a net calorific value (NCV) basis.** Gas can be measured with or without the energy in the water vapour of the flue gas. Gross (GCV) includes it, net (NCV) does not. Eurostat energy balances use NCV. Gas prices are quoted on GCV. The model converts using the ratio of 1.108 (D43). Mixing the two would overstate gas use by about 11%.

**Why the air-accounts cross-check does not match exactly.** Eurostat's air emissions accounts for the sector, scaled to one firm, give 8,402 tCO2e (D74). My bottom-up combustion figure is 5,754 tCO2e (D68), 68% of that (D76). The accounts include process emissions (for example ammonia and nitric acid plants) and other gases that a household-products firm would not have. So the gap is expected, and the model does not force a match.

**Why location-based and market-based Scope 2 are never added.** They are two ways of reporting the same electricity. Location-based uses the national grid average (`EF_GridLB`, 0.154 tCO2e/MWh). Market-based uses the supplier or residual mix (`EF_ResidualMB`, 0.17101). Adding them would count the same megawatt-hours twice. The GHG Protocol asks for both to be reported side by side. Baseline row 87 gives one total per basis.

**Real versus nominal money, EUR 2025 and the Fisher formula.** Nominal money includes inflation. Real money is measured in the purchasing power of one fixed year (here 2025). The model works in real EUR 2025, so the discount rate must be real too. Damodaran's cost of capital is nominal. The Fisher formula converts: real = (1 + nominal) / (1 + inflation) - 1. With nominal 7.811% and inflation at the ECB 2.0% target (`Fin_InflationLongRun`), real = 5.70% (Rates D23). The Damodaran Euros column assumes 1.5% inflation, so using 2.0% gives a slightly lower real rate. This is stated on Rates and in Notes. Memo rows show the Basic (3.08%, D24) and Diversified (5.50%, D25) chemical groups.

**Why NGFS prices are converted with the 2010 exchange rate and then euro-area inflation.** The NGFS price is in 2010 US dollars. Step one: divide by 1.3257 US dollars per euro, the 2010 average (Eurostat), to get 2010 euros. Step two: multiply by euro-area HICP 2025 over 2010 (D13, 1.3823) to get 2025 euros. Combined factor 1.0427 (D14). The limitation: this assumes the dollar kept its 2010 real value against the euro. A US-CPI route would give a factor of about 1.31, so prices about 25% higher. That is a candidate sensitivity in Phase 4. NGFS prices are also model shadow prices (the carbon price needed for the model to hit its target), not market prices.

**The EUA anchor.** The 2025 average of EU allowance auction prices (`Carbon_EUA_Avg2025`, EUR 73.43) sits beside the scenarios on the Carbon sheet. Gaps to the 2025 NGFS value: Low +49.15, Central -53.33, High -85.46 (D45 to D47). The scenarios are not adjusted to the market price. How to blend the short run is a Phase 4 decision.

## What is an assumption, not data

- **The fleet block** (Baseline rows 55 to 57): 10 vehicles, 25,000 km a year, 184.9 g CO2 per km. Eurostat has no fleet data for a firm this size. These are labelled analyst assumptions.
- **The flat grid factor and flat residual mix paths.** No sourced Belgian projection was found on an approved source, so both are held at the latest values (an accepted deviation, in Notes).
- **The UK heat factor** used as a Belgian proxy for purchased heat (DESNZ).
- **ICCT-anchored electric vehicle values**, where the fleet measure uses the study's trucks and delivery vans as a stand-in.
- **The RVO price year**, assumed to be the list year.
- **No size or illiquidity premium** on the discount rate.

## Likely interview questions

1. **Why value added, not turnover, to scale the sector?** Value added measures real activity and is less distorted by pass-through of raw material costs. Turnover is shown as a memo (D19) and gives a ratio about 39% higher; both are visible.
2. **What is NCV versus GCV, and why does it matter?** GCV counts the heat from condensing flue-gas water vapour, NCV does not. Eurostat uses NCV, gas prices use GCV. I convert with a ratio of 1.108 from DESNZ factors so energy and price are consistent.
3. **Your bottom-up emissions are lower than the Eurostat accounts. Why?** The accounts include process emissions and other gases from large chemical plants. Combustion is 68% of the scaled figure, and I do not force a reconciliation.
4. **Why are location-based and market-based Scope 2 never added?** They describe the same electricity with different factors. Adding them double counts. The GHG Protocol requires dual reporting, not summing.
5. **Why is the discount rate real?** The cash flows are in constant 2025 euros, so discounting at a nominal rate would be inconsistent and would penalise long-lived projects. Fisher converts the nominal 7.811% to 5.70% at 2.0% inflation.
6. **Why use the ECB 2% target rather than recent inflation?** Euro-area inflation was 3.8% in September 2026 (Rates D26), an energy-driven spike. A long-run model needs a long-run rate. The spike is a Phase 4 sensitivity.
7. **What are the NGFS carbon prices, and can you rely on them?** They are model shadow prices, the cost of the last tonne abated in the model, from NGFS Phase V (REMIND-MAgPIE, OECD & EU region). They are scenario inputs, not forecasts. I show Low, Central and High and do not blend them with the market price.
8. **How did you convert US dollars from 2010 into euros from 2025?** Divide by the 2010 average exchange rate of 1.3257 US dollars per euro, then multiply by euro-area HICP 2025 over 2010. The factor is 1.0427. The weak point is the assumption that the dollar held its 2010 real value; a US-CPI route would give about 1.31.
9. **Why does the Central scenario sit below the market price now?** Compare the EUA 2025 average of EUR 73.43 with the Central 2025 NGFS value of EUR 126.76. The Central path is a policy-ambition path, so it is higher than today's market; the model keeps both visible rather than hiding the gap.
10. **How do you know the formulas are right?** An independent Python reference model recomputes every figure, and the cached values in the workbook are compared to it. Formulas use only plain functions (INDEX, MATCH, MIN, MAX, SUM), so the workbook opens in Excel desktop and Excel for the web.
11. **What is ETS2, and when does it start?** A second EU carbon market for fuels used in buildings and road transport, covering fuel suppliers. The start was postponed to 2028 (Carbon D51). Natural gas, LPG and road diesel are in scope; electricity and heat are not.

## What comes next in Phase 3

Phase 3 builds the decarbonisation measures themselves (heat pumps, rooftop PV, LED lighting, motor drives, fleet electrification and so on). Each measure gets cash flows, NPV, IRR, payback and abatement cost, discounted at `Rate_DiscountReal` and priced from the Baseline figures. Phase 3 also checks the workbook's formulas against the reference model, and prepares the marginal abatement cost curve. Phase 4 then applies the three carbon price paths to the exposure, with and without acting, and runs the sensitivities flagged above.
