# Phase 4 walkthrough: carbon cost exposure, scenarios and sensitivity

This note explains what Phase 4 built, in plain words, assuming you know nothing about carbon markets or Excel. Every number below comes from the reference models (`checkmodel/exposure_reference.py` and `checkmodel/sensitivity_reference.py`) in the default state (Market-based, Central scenario, direct ETS1 Off) and equals what the workbook (`dist/maison_veritas.xlsx`) shows in that state. Money is real EUR 2025. Named cells are given so you can click one and check. The exposure window is 2026 to 2035 (`Expo_LastYear`), with 2026 as year 0.

The big question Phase 4 answers: **what will the company pay for carbon over the next ten years if it does nothing, what if it carries out the six measures, and how sure are we?**

## 0. Words used

- **Carbon price**: what one tonne of CO2 costs, in EUR per tonne.
- **ETS1**: the EU Emissions Trading System for big installations (power plants, large factories). Each tonne emitted needs an allowance (an EUA) that is bought on a market.
- **ETS2**: a second, newer system. It charges the suppliers of fuels (gas, diesel, heating oil) for the CO2 their fuel will release, from 2028 in this model. Suppliers pass the cost to customers.
- **Pass-through**: when a cost upstream shows up in the price you pay. Power producers pay for carbon, so electricity gets dearer. A share of that rise reaches the firm.
- **MEF (marginal emission factor)**: how many tonnes of CO2 the power plant that sets the electricity price emits per MWh. Here 0.3607 tCO2/MWh (a gas power plant).
- **PTR (pass-through rate)**: the share of the plant's carbon cost that reaches the power price. Default 1.0 (all of it), the top of the range found in the literature. The tornado tests 0.6.
- **Internal carbon price**: a price a company sets itself (here EUR 100 per tonne, `Carbon_ICP_Level`) to judge decisions. It is not a bill.
- **Discounting**: money far in the future counts for less. Each year's amount is multiplied by a factor below 1 (2030 is 0.8012). Adding the results gives a "present value".
- **Multiplier**: a number like 1.2 that means "20% higher than the base".
- **Tornado**: a bar chart of how much one result moves when each input is pushed up and down, longest bar on top.
- **Hurdle rate**: the minimum yearly return a company demands before it will invest. Here 6%, 8% and 10% are tried.

## 1. The new dropdown: Sel_DirectETS

On the Inputs sheet, next to the scenario and basis dropdowns, sits **Sel_DirectETS** (Off or On). Default Off.
- **Off**: the firm burns gas and fuel and pays through its fuel supplier, so ETS2 applies.
- **On**: the firm is treated as a large installation (the rule uses a thermal threshold of 20 MW, `Carbon_ETS1_ThermalThresholdMW`) that buys its own allowances under ETS1. It then pays ETS1 instead of ETS2 on stationary fuel.
- It is **never both**. A check (`Expo_Check_All` includes it) multiplies the two price rows together and requires the total to be zero.
- Fleet diesel always pays ETS2, because vans are not an installation.

## 2. Market-anchored prices: why NGFS is not used raw

NGFS (the central banks' climate scenarios) gives price paths that are model "shadow prices", not market prices. In 2026 they are far from what allowances actually trade at. So the model starts at what we observed, the 2025 EUA average of EUR 73.43 (`Carbon_EUA_Avg2025`), and slides linearly to the NGFS path by 2030 (`Carbon_ETS1_ConvYear`, `Carbon_ETS2_ConvYear`).

Worked example, Central, ETS1:
- Weights on NGFS: 2026 = 0.2, 2027 = 0.4, 2028 = 0.6, 2029 = 0.8, 2030 and later = 1.0.
- 2029 NGFS Central is about EUR 206.3. Price = 0.2 x 73.43 + 0.8 x 206.3 = **EUR 179.72**.
- 2030: price = 1.0 x NGFS = **EUR 226.18**.

ETS2 starts in 2028 (`Carbon_ETS2_StartYear`, delayed from the enacted 2027): zero before, EUR 55.15 in 2028 (the EUR 45 stability price in 2020 money, restated to 2025), EUR 130.72 in 2029 (half stability price, half NGFS), EUR 226.18 in 2030. The Low path is 63.6 in 2026 falling to 24.3 in 2030; the High path rises to 294.3 in 2030.

## 3. ETS2 on fuels: tonnes x price

Cost = tonnes of CO2 burnt x ETS2 price. Example 2030 (do-nothing case):
- Stationary fuels (gas and similar): 5,754.2 tonnes x EUR 226.18 = EUR 1,301,460.
- Van diesel: 46.2 tonnes x EUR 226.18 = EUR 10,455.
- Total ETS2 bill that year: **EUR 1,311,915** (`Expo_BAU_ETS2` row, 2030).

Assumption to defend: the fuel supplier passes 100% of the cost on. That is an analyst assumption.

## 4. Pass-through on electricity, with the embedded allowance netted

Electricity prices already contain some carbon cost: the 2025 power price you pay already includes the allowances (about EUR 73.43 per tonne) that the gas plant bought. Only the **change** versus that is new. So:

pass-through = purchased MWh x MEF x PTR x (ETS1 price - **embedded** 2025 EUA)

2030 worked example: 12,016 MWh x 0.3607 x 1.0 x (226.18 - 73.43) = 4,334 tonnes-equivalent x 152.75 = **EUR 662,025**.

Why it can be negative under Low: in 2030 the Low ETS1 price is EUR 24.27, below the embedded 73.43. 4,334 x (24.27 - 73.43) = **EUR -213,060**. Meaning: power prices would fall below the level the 2025 bill already holds. Over the window the Low pass-through totals EUR -1.28 million (discounted).

Why the green contract saves no cash: the power price is set by the marginal plant, whatever certificates the firm holds. The renewable contract (Guarantees of Origin) lowers reported market-based emissions, not the cash bill. In the model its avoided cash carbon cost is exactly zero (a check, `Expo_Avoided_RC`, requires it).

## 5. The 20 MW rule and the CBAM verdict

Direct ETS1 (Sel_DirectETS On) only makes sense if the installation passes the 20 MW rule. This firm's sector (a mid-sized manufacturer) normally does not, which is why Off is the default. With On, Central discounted do-nothing cost is EUR 11.87 million instead of EUR 10.08 million, because the ETS1 price applies to the stationary fuel in every year from 2026, while ETS2 only starts in 2028.

CBAM (the EU border carbon charge) is shown as a screen on the Exposure sheet, as of 2026-10-25. It concerns imported goods in covered sectors, so it is a note on the company's inputs, not a cost line.

## 6. The internal carbon price: a lens, not a cost

Take Scope 1 + 2 tonnes on the selected basis and multiply by EUR 100. In 2026 that is 8,204 tonnes x 100 = EUR 820,432. It shows what the firm "should" care about when deciding, and it is **never added to the cash totals**.

Market-based discounted values (Central): do nothing EUR 6.48 million, after acting EUR 4.26 million, avoided EUR 2.22 million. Switch the basis to Location-based and the avoided figure falls to EUR 0.72 million: the difference, about EUR 1.5 million, is the renewable contract, which only counts on the market-based basis. That is the "MB contract effect".

## 7. Cost of not acting vs acting

Two ways to total the years:
- **Cumulative**: add the undiscounted yearly bills (real 2025 euros, no inflation).
- **Discounted** (`Expo_DiscBAU_Sel`, `Expo_DiscWith_Sel`, `Expo_DiscAvoided_Sel`): add after applying discount factors. Use this to compare with NPVs.

Headline, direct ETS Off, in EUR million (discounted; cumulative in brackets):

| Scenario | Do nothing | After acting | Avoided (`Expo_DiscAvoided_Sel`) |
|---|---|---|---|
| Low | -0.20 (-0.31) | -0.50 (-0.70) | 0.30 (0.39) |
| Central | 10.08 (13.87) | 9.02 (12.40) | 1.06 (1.47) |
| High | 17.11 (24.09) | 15.48 (21.78) | 1.62 (2.31) |

A negative Low total is not a typo: the electricity credit from section 4 outweighs the fuel cost. A reader should treat Low as "carbon is nearly free".

## 8. The bridge chart, bar by bar

The stacked-column bridge on the Exposure sheet starts at the discounted do-nothing bill (EUR 10.08 million, Central) and steps down one measure at a time, ending at "After acting" (EUR 9.02 million). The step per measure (discounted avoided cost): LED 0.05, VSD 0.03, heat pump 0.67, fleet 0.03, PV 0.28, contract 0.00 (million EUR).

Why a bar can go up: a measure that shifts fuel use to electricity (the heat pump, an electric van) adds electricity purchases, and under positive pass-through that adds cost. The heat pump here still comes out ahead (2030: electricity bought rises from 12,016 to 12,800 MWh, but gas ETS2 falls by much more). The opposite happens under Low: LED, VSD and PV cut electricity, and with negative pass-through that cuts a credit, so their bars rise (LED -0.02, VSD -0.01, PV -0.10 million). Do not read this as the measures being bad: they are judged on financial NPV, with carbon as a lens.

## 9. Carbon-inclusive NPV vs financial NPV

- **Financial NPV** (`Sens_PortfolioNPV_Fin`): the six measures' cash flows only. Portfolio total: EUR -72,399.
- **Carbon-inclusive NPV** (`Sens_PortfolioNPV`): financial NPV plus the discounted avoided cash carbon cost. Total: EUR 2,519,250 (carbon adds EUR 2.59 million).

So at a Central carbon path the portfolio turns from slightly negative to clearly positive. This is the number every sensitivity moves.

## 10. The closed-form grid trick

The sensitivity grid (energy price multiplier down the side, carbon price multiplier across the top, both from 0.6 to 1.4 in steps of 0.2) is plain arithmetic. NPV is a straight line in a price: a price 20% higher changes NPV by 0.2 times the present value of the volume affected. So each cell is:

centre NPV + (energy multiplier - 1) x PV of energy saved + (carbon multiplier - 1) x PV of gross carbon

Example: centre EUR 2,519,250; carbon x1.2 and energy x1.0 gives 2,977,824 (+458,574, which is 0.2 x gross carbon PV). The centre cell must equal `Sens_PortfolioNPV`, and a check confirms it.

Why not Excel's Data Table? Data Tables cannot be created in Excel for the web, and the reviewer may use it. "Gross" carbon means each carbon PV before netting, so lines stay straight.

## 11. The rate strip

Same idea along the discount rate: 3.70%, 4.70%, 5.70% (the model's rate), 6.70%, 7.70%. Carbon-inclusive NPV: EUR 3.73 million, 3.07, 2.52, 2.06, 1.67. Higher rate, lower NPV, because savings arrive late. The 5.70% cell must equal `Sens_PortfolioNPV`.

## 12. The tornado

Each driver moves alone (plus/minus 20% for energy prices and capex, 50% for guarantee-of-origin price, 30% for EV premium, 15% for MEF, PTR 0.6 to 1.0, ETS2 start one year later, discount rate plus/minus 2 points). Swing in portfolio NPV, largest first:
1. **Carbon price scenario (Low to High)**: EUR 5.76 million (NPV 0.53 to 6.30 million). The assumption that matters most.
2. **Discount rate**: EUR 2.07 million (3.73 down to 1.67 million).
3. **Gas price**: EUR 1.70 million. Dearer gas makes switching away from gas worth more.
Smallest: ETS2 delay (0.13 million), MEF (0.17), EV premium (0.20).

Takeaway: the case depends on which carbon path comes true, not on small technical inputs. Another bar tests the alternative NGFS currency conversion (NPV +0.57 million).

## 13. Rank stability and hurdle rate vs WACC

The MACC ranks measures by abatement cost. Does that order change if the company demands a higher return? The Sensitivity sheet recomputes each measure's cost per tonne at hurdle rates of 6%, 8% and 10% (`Sens_Hurdle_1` to `_3`) against the base rate of 5.70%.

Result: the order is the same at every hurdle: variable-speed drives, solar PV, LED, renewable contract, heat pump, fleet. Costs per tonne rise (LED -220 at base to -2 at 10%; heat pump 106 to 136), but no measure changes rank.

Hurdle rate vs WACC: WACC (weighted average cost of capital) is what the capital costs the firm; a hurdle rate is what managers demand on top, often because projects are risky or capital is rationed. Using hurdles above WACC tests whether the plan survives a stricter investor.

## 14. Interview questions and short answers

1. **Why is the scenario price market-anchored?** NGFS values are shadow prices far from the traded price today, so the path starts at the observed EUR 73.43 and converges to NGFS by 2030.
2. **What does netting the embedded allowance do?** It counts only the change versus the carbon already in the 2025 power price; otherwise the model would double count.
3. **Why can pass-through be negative under Low?** Low prices in 2030 (EUR 24) are below the embedded EUR 73, so electricity would be cheaper than the 2025 baseline.
4. **Why does a green contract save no carbon cash?** The marginal plant sets the price; certificates change the reporting, not the bill.
5. **ETS1 or ETS2?** Never both. Fuel suppliers pay ETS2 for a normal manufacturer; only large installations (20 MW) pay ETS1 directly.
6. **Why is the internal carbon price not a cost?** It is a decision lens; no one invoices it, so it stays out of cash totals.
7. **Why can heat pumps and EVs raise pass-through cost?** They add electricity purchases; under high pass-through that adds a cost, but fuel savings usually outweigh it.
8. **How do you do sensitivities without Data Tables?** NPV is linear in prices, so each cell is the centre plus a multiplier times a present value, in plain formulas that work in Excel for the web.
9. **Hurdle rate versus WACC?** WACC is the cost of capital; a hurdle is the stricter return management demands. The ranking held at 6, 8 and 10%.
10. **What is the biggest uncertainty?** The carbon path: Low to High swings portfolio NPV by EUR 5.8 million, more than any technical input.
11. **What is not live?** The LED/VSD lifetime and heat-pump-share sensitivities on the Notes sheet are computed in Python at build time and labelled "not a live cell".
