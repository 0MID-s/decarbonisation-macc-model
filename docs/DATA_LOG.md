# DATA_LOG: fetched files, hashes and parsed values (Phase 2)

`data_raw/` is gitignored (only its README is tracked), so this file is the committed provenance trail for every machine-readable Phase 2 source. The build stays offline: values are copied into `config/inputs_*.py` by hand from this reviewed log (plans 02-05 to 02-07).

- All files were fetched on 2026-10-19 through `python3 -I tools/fetch_all.py` (allowlisted hosts, sha256 manifest in `data_raw/<Src_ID>/MANIFEST.jsonl`).
- Downloaded files are untrusted data. They were only read by the read-only parsers under `python -I`, with the data path passed as an argument and never from inside `data_raw/`. Nothing was opened in Excel or any other application.
- "Status" compares the live value with the 02-RESEARCH.md value: `match` = identical; `revised` = live value differs and wins; `new` = not in research, logged now.
- Parser commands (from the repo root): `PE` = `.venv/bin/python -W ignore -I tools/parse_eurostat.py`, `PX` = `.venv/bin/python -W ignore -I tools/parse_xlsx.py`, `PM` = `.venv/bin/python -W ignore -I tools/parse_misc.py`.
- Eurostat addresses use the printed key `freq|indicator-or-nrg_bal|NACE-or-siec|size-or-unit|geo|time`. Eurostat flag `-` means no status flag on the cell; `i` means imputed.
- Summary: no research value was revised by the live data. New values: C20 and C21 net turnover, the full Eurostat price-band lists, DESNZ row IDs, RVO and PBL cell addresses, the LED/VSD lifetime search result.

## Src_EurostatSBS

- File: `sbs_sc_ovw_BE_C20_C21.json`
- sha256: `e8f38afb04113a358437f3efbf7bebe64611489d163a41698fee4bdc0467cd0a`
- retrieved_utc: 2026-10-19T19:52:04Z (26,628 bytes)
- Command: `PE data_raw/Src_EurostatSBS/sbs_sc_ovw_BE_C20_C21.json`
- All cells below carry no status flag.

| Item | Live value | Research value | Status | Address |
|---|---|---|---|---|
| C20 50-249 enterprises, 2024 | 110 | 110 | match | A\|ENT_NR\|C20\|50-249\|BE\|2024 |
| C20 50-249 persons employed, 2024 | 13,960 | 13,960 | match | A\|EMP_NR\|C20\|50-249\|BE\|2024 |
| C20 50-249 value added AV_MEUR, 2024 | 2,536.48 | 2,536.48 | match | A\|AV_MEUR\|C20\|50-249\|BE\|2024 |
| C20 50-249 net turnover NETTUR_MEUR, 2024 | 12,396.76 | 12,396.76 | match | A\|NETTUR_MEUR\|C20\|50-249\|BE\|2024 |
| C20 TOTAL AV_MEUR, 2024 | 8,911.42 | 8,911.42 | match | A\|AV_MEUR\|C20\|TOTAL\|BE\|2024 |
| C20 TOTAL NETTUR_MEUR, 2024 (D-03 sector turnover) | **42,576.38** | not in research | new | A\|NETTUR_MEUR\|C20\|TOTAL\|BE\|2024 |
| C21 TOTAL AV_MEUR, 2024 | 16,919.86 | 16,919.86 | match | A\|AV_MEUR\|C21\|TOTAL\|BE\|2024 |
| C21 TOTAL NETTUR_MEUR, 2024 (D-03 sector turnover) | **48,554.13** | not in research | new | A\|NETTUR_MEUR\|C21\|TOTAL\|BE\|2024 |
| C20 50-249 AV_MEUR 2021 / 2022 / 2023 | 2,063.44 / 2,388.30 / 2,397.82 | same | match | A\|AV_MEUR\|C20\|50-249\|BE\|2021..2023 |
| C20 50-249 ENT_NR 2021 / 2022 / 2023 | 98 / 105 / 112 | same | match | A\|ENT_NR\|C20\|50-249\|BE\|2021..2023 |
| C20 50-249 NETTUR_MEUR 2021 / 2022 / 2023 | 8,874.36 / 13,107.24 / 10,769.24 | same | match | A\|NETTUR_MEUR\|C20\|50-249\|BE\|2021..2023 |
| Value added per enterprise EUR m, 2021 / 2022 / 2023 / 2024 (stability note) | 21.06 / 22.75 / 21.41 / 23.06 | 21.1 / 22.7 / 21.4 / 23.1 | match | computed AV_MEUR / ENT_NR |
| Turnover per enterprise EUR m, C20 50-249, 2024 | 112.70 (12,396.76 / 110) | 112.7 | match | computed |

Notes for the D-03 cross-check: C20 TOTAL 634 enterprises (A\|ENT_NR\|C20\|TOTAL\|BE\|2024), C21 TOTAL 165 enterprises (same key with C21). The "NETTUR_MEUR" sector values above are Belgium totals, not per firm.

## Src_EurostatEnergyBalance

- File: `nrg_bal_c_BE_FC_IND_CPC_E_TJ.json`
- sha256: `fc77c63d6ea455a5633c53f1262f40f6bd1fd9fa1f2effe046e8e3a860730fc4`
- retrieved_utc: 2026-10-19T19:52:05Z (40,183 bytes)
- Command: `PE data_raw/Src_EurostatEnergyBalance/nrg_bal_c_BE_FC_IND_CPC_E_TJ.json`
- Unit printed: TJ (net calorific value basis per research 3.2). All cells flag `-`.

| Item (BE, 2024, TJ) | Live value | Research value | Status | Address |
|---|---|---|---|---|
| TOTAL | 162,119.849 | 162,119.849 | match | A\|FC_IND_CPC_E\|TOTAL\|TJ\|BE\|2024 |
| G3000 natural gas | 62,515.885 | 62,515.885 | match | A\|FC_IND_CPC_E\|G3000\|TJ\|BE\|2024 |
| E7000 electricity | 48,458.52 | 48,458.52 | match | A\|FC_IND_CPC_E\|E7000\|TJ\|BE\|2024 |
| H8000 derived heat | 8,030.8 | 8,030.8 | match | A\|FC_IND_CPC_E\|H8000\|TJ\|BE\|2024 |
| O4630 LPG | 11,356.73 | 11,356.73 | match | A\|FC_IND_CPC_E\|O4630\|TJ\|BE\|2024 |
| O4640 naphtha | 29,361.1 | 29,361.1 | match | A\|FC_IND_CPC_E\|O4640\|TJ\|BE\|2024 |
| O4671XR5220B gas oil / diesel | 1,143.8 | 1,143.8 | match | A\|FC_IND_CPC_E\|O4671XR5220B\|TJ\|BE\|2024 |
| Sum of the five main carriers (G3000+E7000+H8000+O4630+O4640) | 160,866.835 | 160,866.835 | match | computed |
| Remainder = TOTAL minus the five carriers | 2,396.814 (1.48% of total) | 2,396.8 | match | computed; equals 1,143.8 + 513.08 + 379.834 + 260.1 + 100 per research |

Sum check: five carriers + remainder = 162,119.849 exactly (remainder derived as the difference; the research itemised remainder (gas oil 1,143.8 + fuel oil 513.08 + coke 379.834 + renewables 260.1 + waste 100) adds to the same 2,396.814).

## Src_EurostatAirAccounts

- File: `env_ac_ainah_r2_BE_C20_C21_GHG.json`
- sha256: `cafccb7208ce9fc3f3c54b11731ae2de0c499116bb91a55104a65a5c3575e3ef`
- retrieved_utc: 2026-10-19T19:52:06Z (6,720 bytes)
- Command: `PE data_raw/Src_EurostatAirAccounts/env_ac_ainah_r2_BE_C20_C21_GHG.json`
- Unit code printed: `T` (tonne). The dataset also exposes G_HAB, KG_HAB, THS_T and I15; use `T`.

| Item (BE, 2024) | Live value | Research value | Status | Address |
|---|---|---|---|---|
| C20 GHG tonnes | 9,173,823.08, flag `i` (imputed) | 9,173,823.08, flag i | match | A\|GHG\|C20\|T\|BE\|2024 |
| C21 GHG tonnes | 238,898.76, flag `i` (imputed) | 238,898.76, flag i | match | A\|GHG\|C21\|T\|BE\|2024 |

## Src_EurostatElecPrice

- File: `nrg_pc_205_BE_X_VAT.json`
- sha256: `319b25f3d84cdc740b13c647913a7dce2e50053d21601a6e2e075a33c966a8f2`
- retrieved_utc: 2026-10-19T19:52:07Z (15,758 bytes); dataset `updated` field 2026-10-19
- Command: `PE data_raw/Src_EurostatElecPrice/nrg_pc_205_BE_X_VAT.json`
- Unit KWH, tax X_VAT, currency EUR, product E7000, geo BE. All cells flag `-`. Address key: `S|E7000|<band code>|KWH|X_VAT|EUR|BE|<semester>`.
- Band codes and labels (annual consumption; lower bound in MWh): IA `MWH_LT20` (<20, lower bound 0); IB `MWH20-499` (20); IC `MWH500-1999` (500); ID `MWH2000-19999` (2,000); IE `MWH20000-69999` (20,000); IF `MWH70000-149999` (70,000); IG `MWH_GE150000` (150,000).

| Band (EUR/kWh) | 2025-S1 live | 2025-S2 live | 2026-S1 live | Research (S1 / S2 / 2026-S1) | Status |
|---|---|---|---|---|---|
| IA MWH_LT20 | 0.3138 | 0.2808 | 0.3172 | 0.3138 / 0.2808 / 0.3172 | match |
| IB MWH20-499 | 0.2314 | 0.2158 | 0.2318 | same | match |
| IC MWH500-1999 | 0.1940 | 0.1866 | 0.1902 | same | match |
| ID MWH2000-19999 | 0.1659 | 0.1571 | 0.1600 | same | match |
| IE MWH20000-69999 | 0.1348 | 0.1311 | 0.1332 | same | match |
| IF MWH70000-149999 | 0.1155 | 0.1141 | 0.1148 | same | match |
| IG MWH_GE150000 | 0.0982 | 0.0920 | 0.1014 | same | match |
| TOT_KWH (all bands) | 0.1666 | 0.1587 | 0.1678 | same | match |

D-21 check: mean of ID 2025-S1 and 2025-S2 = (0.1659 + 0.1571) / 2 = 0.1615 EUR/kWh, as in research.

## Src_EurostatGasPrice

- File: `nrg_pc_203_BE_X_VAT.json`
- sha256: `9aea07af850898fe6aca6581828ed0728cdf522577c238b9f0c0264d95774c36`
- retrieved_utc: 2026-10-19T19:52:08Z (16,372 bytes); dataset `updated` 2026-10-19
- Command: `PE data_raw/Src_EurostatGasPrice/nrg_pc_203_BE_X_VAT.json`
- Product G3000, tax X_VAT, currency EUR, geo BE. Both unit codes are present: `KWH` (kilowatt-hour; used here) and `GJ_GCV` (gigajoule, gross calorific value). Eurostat prices per kWh are therefore on a GCV basis (research 3.6). All cells flag `-`. Address key: `S|G3000|<band>|KWH|X_VAT|EUR|BE|<semester>`.
- Band codes (annual consumption in GJ GCV; lower bound in GJ): I1 `GJ_LT1000` (<1,000; 0); I2 `GJ1000-9999` (1,000); I3 `GJ10000-99999` (10,000); I4 `GJ100000-999999` (100,000); I5 `GJ1000000-3999999` (1,000,000); I6 `GJ_GE4000000` (4,000,000).

| Band (EUR/kWh GCV) | 2025-S1 live | 2025-S2 live | 2026-S1 live | Research | Status |
|---|---|---|---|---|---|
| I1 | 0.0749 | 0.0700 | 0.0677 | 0.0749 / 0.0700 / 0.0677 | match |
| I2 | 0.0689 | 0.0603 | 0.0548 | same | match |
| I3 | 0.0505 | 0.0481 | 0.0439 | same | match |
| I4 | 0.0428 | 0.0399 | 0.0389 | same | match |
| I5 | 0.0415 | 0.0376 | 0.0389 | same | match |
| I6 | 0.0424 | 0.0345 | 0.0392 | same | match |

D-21 check: mean of I3 2025-S1 and 2025-S2 = (0.0505 + 0.0481) / 2 = 0.0493 EUR/kWh GCV, as in research.

## Src_EurostatHICP

- File: `prc_hicp_aind_EA_CP00.json`
- sha256: `080757eb93d26b42c2d713f3fe8117cc5d88a89426fb6e879dfd687ae251b1ec`
- retrieved_utc: 2026-10-19T19:52:08Z (4,287 bytes)
- Command: `PE data_raw/Src_EurostatHICP/prc_hicp_aind_EA_CP00.json`
- Euro-area HICP annual average index (2015=100), coicop CP00, unit INX_A_AVG. Flags `-`. Address key: `A|INX_A_AVG|CP00|EA|<year>`.

| Year | Live value | Research value | Status |
|---|---|---|---|
| 2010 (D-41 NGFS conversion base) | 93.14 | 93.14 | match |
| 2019 | 104.8 | 104.80 | match |
| 2020 | 105.06 | 105.06 | match |
| 2021 | 107.78 | 107.78 | match |
| 2022 | 116.82 | 116.82 | match |
| 2023 | 123.15 | 123.15 | match |
| 2024 | 126.07 | 126.07 | match |
| 2025 | 128.75 | 128.75 | match |

Derived (not stored): 2025/2020 = 128.75 / 105.06 = 1.2255 (as in research); 2025/2010 = 128.75 / 93.14 = 1.3823.

## Src_EurostatFX

- File: `ert_bil_eur_a_USD_AVG.json`
- sha256: `3c96ca57c15266d07e1976d90ba806a5bb90ab46a503b6311df3aaa9f5ba66c7`
- retrieved_utc: 2026-10-19T19:52:08Z (4,488 bytes)
- Command: `PE data_raw/Src_EurostatFX/ert_bil_eur_a_USD_AVG.json`
- Annual average USD per EUR (ert_bil_eur_a, statinfo AVG, currency USD). Address key: `A|AVG|NAC|USD|<year>`. The D-41 route (NGFS US$2010 to EUR via Eurostat 2010 FX and euro HICP) uses only Eurostat series; no other exchange-rate or price-index host is fetched or logged.

| Year | Live value (USD per EUR) | Research value | Status | Flag |
|---|---|---|---|---|
| 2010 (D-41) | 1.3257 | 1.3257 | match | none (`-`) |
| 2024 | 1.0824 | 1.0824 | match | none |
| 2025 | 1.13 | 1.1300 | match | none |

The live 2010 value has no more decimals than the research value (1.3257).

## Src_EEAGridIntensity

- File: `eea_co2_emission_intensity_15.csv`
- sha256: `530d94a536bea86696048cb639d663f5b26bc0d2ca42212e979eed08600f9e85`
- retrieved_utc: 2026-10-19T19:52:08Z (18,552 bytes)
- Command: `PM eea data_raw/Src_EEAGridIntensity/eea_co2_emission_intensity_15.csv --country Belgium`
- Unit gCO2e/kWh of gross electricity generation; Belgium block is rows 334-366 of the CSV (years 1990-2022). The older map edition ends in 2022; 2023 and 2024 are not in this file.

| Belgium | Live value | Research value | Status | Address |
|---|---|---|---|---|
| 2015 | 219 | 219 | match | CSV row 359 |
| 2016 | 161 | 161 | match | CSV row 360 |
| 2017 | 169 | 169 | match | CSV row 361 |
| 2018 | 197 | 197 | match | CSV row 362 |
| 2019 | 170 | 170 | match | CSV row 363 |
| 2020 | 166 | 166 | match | CSV row 364 |
| 2021 | 138 | 138 | match | CSV row 365 |
| 2022 (latest in file) | 154 | 154 | match | CSV row 366 |

## Src_AIBResidualMix

- File: `aib_residual_mix_2025.xlsx`
- sha256: `0933ebb4c348442a238ef7174fcb968516bf1ce7f4e94b0b8548149528fe20f2` (equals the hash computed in research)
- retrieved_utc: 2026-10-19T19:52:08Z (79,337 bytes)
- Commands: `PX data_raw/Src_AIBResidualMix/aib_residual_mix_2025.xlsx --list-sheets`; `PX ... --sheet CO2 --match BE`
- Sheet `CO2`, row 4 (header: country code, production mix, residual mix, supplier mix), unit gCO2/kWh.

| Item (BE) | Live value | Research value | Status | Address |
|---|---|---|---|---|
| Residual mix | 171.01 | 171.01 | match | CO2!A4 (column C) |
| Production mix | 121.86 | 121.86 | match | CO2!A4 (column B) |
| Supplier mix | 114.13 | 114.13 | match | CO2!A4 (column D) |

Licence: the AIB site states no reuse terms (research); cite one figure with source and edition.

## Src_DESNZ2026

- File: `ghg-conversion-factors-2026-flat-format-revised.xlsx`
- sha256: `a9a455ab396dae226d510c7be6233748416d490c41a5d20f3dc7a0c45feecd5e`
- retrieved_utc: 2026-10-19T19:52:09Z (515,426 bytes)
- Command: `PX data_raw/Src_DESNZ2026/ghg-conversion-factors-2026-flat-format-revised.xlsx --sheet "Factors by Category" --match <row ID>`
- Front page: Version 1.2, Year 2026, status Final, updated 2026-07-10, next publication 2027-06-01. Open Government Licence v3.0 per the publication page (research). Unit kg CO2e per stated unit. Value is in the last column (`GHG Conversion Factor 2026`); the address below is the sheet row.

| Item | Row ID | Live value | Research value | Status | Address |
|---|---|---|---|---|---|
| Natural gas, kWh (Net CV) | 1_100_1004_7_1 | 0.20199 | 0.20199 | match | Factors by Category!A79 |
| Natural gas, kWh (Gross CV) | 1_100_1004_6_1 | 0.18231 | 0.18231 | match | Factors by Category!A83 |
| LPG, kWh (Net CV) | 1_100_1003_7_1 | 0.23032 | 0.23032 | match | Factors by Category!A63 |
| Naphtha, kWh (Net CV) | 1_101_1016_7_1 | 0.24891 | 0.24891 | match | Factors by Category!A271 |
| Gas oil, kWh (Net CV) | 1_101_1014_7_1 | 0.27288 | 0.27288 | match | Factors by Category!A239 |
| Diesel (average biofuel blend), per litre | 1_101_1011_8_1 | 2.58354 | 2.58354 | match | Factors by Category!A187 |
| Diesel (average biofuel blend), kWh (Net CV) | 1_101_1011_7_1 | 0.26071 | 0.26071 | match | Factors by Category!A191 |
| District heat and steam, kWh (Scope 2, UK average) | 10_401_4003_5_1 | 0.17529 | 0.17529 | match | Factors by Category!A3454 |

Derived: GCV/NCV for natural gas = 0.18231 / 0.20199 = 0.90257; NCV/GCV = 1.10795 (research 1.1079). Not re-parsed here (not needed by this plan's list): fuel oil, coal, petrol; research values stand unchecked for those.

## Src_DEAProcessHeat

- File: `technology_data_for_industrial_process_heat.xlsx`
- sha256: `8b2fd0ec97b985eb22dbae291aa550c93d67bc17057645b633ee326a938baad7`
- retrieved_utc: 2026-10-19T19:52:09Z (206,481 bytes)
- Commands: `PX <file> --list-sheets`; `PX <file> --sheet "<sheet>"` for the four sheets below, and `--sheet Index`.
- Index sheet: "All cost data is in 2025€" (Index!C2); change log entry dated 2026-01-05, sheet "All": "Update and simplification of datasheets on heat pumps ... Adjusted all prices to be 2025 Euro, instead of 2019" (Index!A8).
- Licence: the Index, Notes and Ref sheets contain no licence line (0 hits for licen/attribution/creative). Licence of this file stays **UNVERIFIED** (same publisher as the electricity file, which states CC BY 4.0). Do not claim a licence in the Source register for this file beyond "published by the Danish Energy Agency".
- Values are the 2025 `ctrl` (central) column (column C); lower/upper range 2025 in columns H, I. Note: sheet `1.2 heat_cool hp 80 C 75 K ` has a trailing space in its name.

| Sheet / parameter | Live value (2025 ctrl) | Research value | Status | Address |
|---|---|---|---|---|
| 1.1: annual average COP ("Total efficiency, net [%], annual average", values are COP) | 5.28 (range 5.28 to 5.5465) | 5.28 | match | 1.1 Traditional heat pump!C8 |
| 1.1: nominal investment M EUR/MW | 0.95 (range 0.91-0.95) | 0.95 | match | !C19 |
| 1.1: fixed O&M EUR/MW/yr | 2,127 | 2,127 | match | !C22 |
| 1.1: variable O&M EUR/MWh | 3.07 | 3.07 | match | !C23 |
| 1.1: technical lifetime, years | 25 (range 15-40) | 25 | match | !C12 |
| 1.1: indirect investment cost M EUR/MW (memo) | 0.19 | 0.19 | match | !C25 |
| 1.1: unit size MW | 3 (0.5-5) | 3 | match | !C6 |
| 1.2: annual average COP | 3.30 (3.3000000000000003 stored; range 3.28-3.47) | 3.30 | match | 1.2 heat_cool hp 80 C 75 K !C8 |
| 1.2: nominal investment M EUR/MW | 0.95 | 0.95 | match | !C19 |
| 1.2: fixed O&M / variable O&M / lifetime | 2,127 / 3.07 / 25 | same as 1.1 | match | !C22, !C23, !C12 |
| 2.a: annual average COP | 2.70 (range 2.2-3.95) | 2.70 | match | 2.a High temp. hp Up to 125C!C8 |
| 2.a: nominal investment (*total) M EUR/MW | 1.2 (range 0.9-1.5) | 1.20 | match | !C22 |
| 2.a: fixed O&M EUR/MW/yr | 2,494 | 2,494 | match | !C25 |
| 2.a: variable O&M EUR/MWh | 3.6 | 3.60 | match | !C26 |
| 2.a: technical lifetime, years | 20 (range 15-30) | 20 | match | !C12 |
| 2.a: indirect investment cost M EUR/MW (memo) | 0.23 | 0.23 | match | !C29 |
| 6.1 boiler: annual efficiency | 0.939 (nominal load 0.94) | 0.939 | match | 6.1 Boiler, gas and oil!C8 (C7) |
| 6.1 boiler: nominal investment M EUR/MW | 0.09 | 0.09 | match | !C22 |
| 6.1 boiler: fixed O&M EUR/MW/yr | 2,000 | 2,000 | match | !C25 |
| 6.1 boiler: variable O&M EUR/MWh | 1.23 | 1.23 | match | !C26 |
| 6.1 boiler: technical lifetime, years | 25 | 25 | match | !C12 |
| 6.1 boiler: indirect investment cost M EUR/MW (memo) | 0.23 | 0.23 | match | !C28 |

Open point carried from research: whether "Nominal investment" already includes the "indirect investment cost" memo line is not stated in the sheets; treat the headline as total and keep the memo as a flagged item.

## Src_DEAElectricity

- File: `technology_data_for_el_and_dh_alldatalong.xlsx`
- sha256: `edfdb4c773f779c8b9d4e47b42004f09f0dd13e23fa3ef3de9f61fb24fdeb992`
- retrieved_utc: 2026-10-19T19:52:10Z (1,846,974 bytes)
- Commands: `PX <file> --sheet "22 Rooftop PV comm.&industrial"`, `PX <file> --sheet alldata_long --match "22 Rooftop PV comm"`, `PX <file> --sheet Intro`.
- Intro sheet: Version 0019 (Intro!A3); "License: This work is licensed under Attribution 4.0 International" (Intro!A15-A16).
- Price year of the per-DC investment and fixed O&M rows: 2020 (column `priceyear` on alldata_long rows A10993 and A11092). Values below are the 2025 column (column C).

| Item | Live value | Research value | Status | Address |
|---|---|---|---|---|
| Nominal investment (*total, per DC) M EUR/MWp | 0.6365236818588025 | 0.6365 | match | 22 Rooftop PV comm.&industrial!C18; alldata_long!A10993 |
| Fixed O&M (*total, per DC) EUR/MWp/yr | 2,190 | 2,190 | match | !C38; alldata_long!A11092 |
| Technical lifetime, years | 40 (range 34-50) | 40 | match | !C10 |
| Inverter lifetime, years | 15 | 15 | match | !C47 |
| Average annual degradation of full-load hours | 0.003 (0.3 %/yr) | 0.3 %/yr | match | !C41 |
| Price year (`priceyear`) | 2020 | 2020 | match | alldata_long!A10993 |
| Unit size (DC) MWp | 0.11 | 110 kWp | match | !C29 |
| Full-load context: GHI kWh/m2/y; transposition factor; performance ratio | 1,068; 1.1; 0.9 | GHI 1,068 | match | !C42, !C43, !C45 |
| 2030 nominal investment (per DC) M EUR/MWp | 0.5885 | 0.5885 | match | !D18 |

Note P (!A77): O&M includes regular inverter replacement, annualised over the 15-year lifetime and included in fixed O&M. HICP uplift 2020 to 2025 (x1.2255) is applied in config, not here: 0.6365 x 1.2255 = 0.780 M EUR/MWp = EUR 780/kWp.

## Src_PVGIS

- Files: `pvgis_antwerp_tilt10.json` (sha256 `f6ee7ca85a9c68d7601d8b2aebf730a8fc5a9b60c3ec7ea09b9d33ec06c44c8d`, 5,193 bytes, retrieved_utc 2026-10-19T19:52:11Z) and `pvgis_antwerp_tilt35.json` (sha256 `da95e543ab54980f4b69a594f98210033b53348fe84244d1c8d8b1c8ca3f355d`, 5,199 bytes, retrieved_utc 2026-10-19T19:52:11Z).
- Commands: `PM pvgis data_raw/Src_PVGIS/pvgis_antwerp_tilt10.json` and `... tilt35.json`.
- Query: lat 51.2, lon 4.4, 1 kWp, crystalline Si, losses 14 %, azimuth 0 (south), PVGIS-SARAH3, 2005-2023. No HTTP 529 occurred; both fetches succeeded first time.

| Item | Live value | Research value | Status | Address |
|---|---|---|---|---|
| Tilt 10, E_y kWh/kWp/yr | 942.09 | 942.09 | match | outputs.totals.fixed.E_y |
| Tilt 10, H(i)_y kWh/m2; SD_y | 1,188.05; 42.57 | 1,188.05; 42.57 | match | outputs.totals.fixed.H(i)_y, SD_y |
| Tilt 35, E_y kWh/kWp/yr | 1,038.15 | 1,038.15 | match | outputs.totals.fixed.E_y |
| Tilt 35, H(i)_y kWh/m2; SD_y | 1,295.35; 49.78 | 1,295.35; 49.78 | match | outputs.totals.fixed.H(i)_y, SD_y |

Terms of use not read (UNVERIFIED); cite as European Commission, Joint Research Centre, PVGIS 5.3.

## Src_RVOEML

- Workbook: `rvo_eml_2023_berekeningen_v1-4.xlsx`
- sha256: `bc94c284bf1927fbcf97a0a87950a84b7a9f80db46cfcbbf6d6b5fda34e1bfb0`
- retrieved_utc: 2026-10-19T19:52:12Z (153,510 bytes)
- Also fetched as text (HTML saved with a `.txt` name through `tools/fetch_raw.py`, host rvo.nl allowlisted, treated as data only): `rvo_eml_informatiebank_index.txt` (sha256 `2564e83e15c79060cb6c910edbbae75d35b93399429e902aede80198b390a79d`, 176,856 bytes, retrieved_utc 2026-10-19T19:54:14Z) and `rvo_eml_page.txt` (sha256 `73480e7ab4d532104bef35111588944a1303cb115e4fd624a47a08945fc5bad8`, 251,518 bytes, retrieved_utc 2026-10-19T19:54:26Z).
- Commands: `PX <workbook> --list-sheets` (sheets: Maatregelenlijst, Zonnepanelen orientatie O-W, Samengevoegde maatregelen); `PX <workbook> --sheet "Samengevoegde maatregelen"`.
- Sheet `Samengevoegde maatregelen` columns: A measure number, B name, C calculation unit, D moment (NM natural moment / ZM independent moment), E labour EUR, F material EUR, G equipment EUR, H net benefits EUR, I gas saving m3/yr, J electricity saving kWh/yr, K total investment EUR, L financing cost EUR, M total saving EUR/yr. Each measure has an NM row and a ZM row (ZM directly below, name cell blank). The price year is not stated in the sheet (record "not stated; assumed 2023 list year" as an assumption). RVO licence/terms not read (UNVERIFIED).

| Measure (NM row) | Unit | Labour / material / equipment EUR | Net benefits EUR | kWh/yr saved | Total investment EUR | Total saving EUR/yr | Research | Status | Address |
|---|---|---|---|---|---|---|---|---|---|
| Vervang halogeenlampen door ledlampen | per lamp (53 W) | 0 / 5.856 / 0 | 2.351 | 118.625 | 6.79296 | 27.26225 | material 5.86, 118.62 kWh, saving 27.26 | match | rows 10 (NM) and 11 (ZM); cells E10:M10 |
| Vervang lichtlijnen met dubbele TL-buizen door led-armaturen | per fixture | 0 / 0.001 / 0 | 1.033 | 215.75 | 0.00116 | 46.3405 | 215.75 kWh | match | row 14 (NM), 15 (ZM); the near-zero material cost and total investment (EUR 0.00116) are as published; treat this row as unreliable for CAPEX and prefer the halogen-to-LED row |
| Frequentieregelaar op de compressoren van de koelinstallatie | per piece (40 kW) | 560 / 3,000 / 200 | 0 | 15,360 | 4,361.60 | 3,225.60 | labour 560, material 3,000, equipment 200, 15,360 kWh | match | row 2 (NM), 3 (ZM, material 4,000, total 5,521.60) |
| Frequentieregelaar op centrifugaalpomp | per pump (3 kW) | 1,040 / 1,765 / 0 | 0 | 7,740 | 3,253.80 | 1,625.40 | not in research | new | row 28 (NM) |
| Frequentieregelaar kneed-/mengmachine | per motor (5.3 kW) | 325 / 1,300 / 0 | 0 | 2,049.6 | 1,885.00 | 430.42 | not in research | new | row 20 (NM) |
| Frequentieregelaar elektromotor | per motor (4 kW) | 280 / 1,100 / 0 | -70 | 5,400 | 1,600.80 | 1,064.00 | not in research | new | row 26 (NM) |

Other frequency-controller rows exist on rows 4, 6, 18, 22, 24, 32, 34 and 36. Compressed air ("perslucht"): on `Samengevoegde maatregelen` rows 42 and 44 (air duct so the compressor draws cold outside air; 60 kW: labour 3,330 / material 3,770 / equipment 394, 7,679.181 kWh saved; 30 kW: 560 / 700 / 0, 2,532.87 kWh saved). On `Maatregelenlijst` there are 16 rows with Activiteit "Perslucht" (rows 2-17, measures FA1 onward, for example FA1 "Vergroot de persluchtbuffer", FA2 shut-off valve with timer, FA3 flow pressure regulator); these are qualitative conditions with no cost columns.

### Lifetime search for LED and frequency controller (DATA-08, for plan 02-06: Meas_LED_Life and Meas_VSD_Life)

- LED lifetime (Meas_LED_Life): **Lifetime not found.** Searched: workbook sheets `Maatregelenlijst`, `Zonnepanelen orientatie O-W` and `Samengevoegde maatregelen` with the keywords levensduur, afschrijving, technische, gebruiksduur and jaar. Zero hits for levensduur, afschrijving, technische and gebruiksduur in all three sheets. "jaar" hits are unrelated (kWh/jaar, "once per 5 years" heat measurement, "roof need not be renovated within 10 years", and a solar-panel yield sheet with a 0.5 %/yr degradation note). Also searched the static text of the RVO pages https://www.rvo.nl/onderwerpen/energiebesparingsplicht/eml/informatiebank and https://www.rvo.nl/onderwerpen/energiebesparingsplicht/eml: the informatiebank is client-side rendered (the HTML contains `BAILOUT_TO_CLIENT_SIDE_RENDERING`) and has no measure text in the static page; the EML page states only the 5-year payback rule and no lifetimes. The WebFetch page-read route in the plan was not available in this run, so the static fetch through `tools/fetch_raw.py` was used instead; two page reads were made. Plan 02-06 applies its labelled analyst-assumption fallback.
- Frequency controller lifetime (Meas_VSD_Life): **Lifetime not found.** Same places searched, same result. Plan 02-06 applies its labelled analyst-assumption fallback.

## Src_PBLSDE2026

- File: `pbl_ot_model_eindadvies_sde_2026.xlsx`
- sha256: `02da21c35827714bf27e769b87fbc59d80cd52633ca42c08fb571db3f375636a`
- retrieved_utc: 2026-10-19T19:52:14Z (5,844,422 bytes)
- Commands: `PX <file> --list-sheets` (180 sheets: Colofon, Overzicht, Correcties, Wordtabellen, 1-175, Rangschikking); `PX <file> --sheet Overzicht`; `PX <file> --sheet 16`; `PX <file> --sheet 98`; `PX <file> --sheet Colofon`.
- Colofon: "SDE++ 2026", date 2026-06-29, version "Eindadvies SDE++ 2026 - 1" (Colofon!A13-A16). Values are in column C of each category sheet.
- Price-level year: **not found in OT-model** (keywords prijspeil, prijsniveau, prijsjaar, constante, reeel, prijzen searched in Colofon, Overzicht, sheet 16 and Wordtabellen; no hit). Record "price level not stated in the workbook" and do not infer a year.

| Item | Live value | Research value | Status | Address |
|---|---|---|---|---|
| Category 16 "Zon-pv >=15 kWp en <1 MWp, gebouwgebonden": investment cost (input based) | 531 EUR/kW (power unit kW as labelled in the sheet) | not read in research | new | 16!C39 |
| Category 16: total investment, EUR million (reference project) | 0.133612875 | n/a | new | 16!C41 |
| Category 16: fixed operating cost | 15.2 EUR/kW/yr | n/a | new | 16!C42 |
| Category 16: full-load hours | 840 | n/a | new | 16!C30 |
| Category 16: economic lifetime | 20 years | n/a | new | 16!C73 |
| Category 16: base amount (basisbedrag) | 0.0945 EUR/kWh | n/a | new | 16!C5 (Overzicht!A25) |
| Category 98 "Industriele warmtepomp, gesloten systeem (8.000 uur)": investment cost (output based) | 1,476 EUR/kW | n/a | new | 98!C40 |
| Category 98: total investment, EUR million (reference project) | 2.0808648 | n/a | new | 98!C41 |
| Category 98: fixed operating cost (output based) | 89.9 EUR/kW/yr | n/a | new | 98!C43 |
| Category 98: full-load hours / electricity use / economic lifetime | 8,000 h / 3,200 MWh/yr / 12 years | n/a | new | 98!C29, !C56, !C73 |
| WACC used by PBL for category 16 (nominal / real) | 5.2 % / 3.1 % | n/a | new | 16!A154 (text "5,2% / 3,1%") |

Cross-check observations (D-31, informational; the live DEA values remain the config source): PBL rooftop PV investment 531 EUR/kW is well below the DEA 2025 figure of about EUR 780/kWp (after HICP uplift), a gap of about 32 %, plausibly because of different unit scope, size class and price level; PBL industrial heat pump 1,476 EUR/kW (output) is above DEA 1.1 at 950 EUR/kW plus 190 indirect (1,140), a gap of about 29 %. Sub-par agreement is a limitation to mention, not a reason to change the DEA-based inputs.

## Not fetched here (by design)

- NGFS Phase V carbon prices: user-supplied (`data_raw/Src_NGFSPhaseV/`, D-43), handled in plan 02-11 and the NGFS parser.
- Damodaran waccEurope: user-supplied (D-42); EUR-Lex legal texts: see the section "Legal texts (WR-02 re-read, plan 02-15)" below (7 VERIFIED by user paste (plan 02-16), 9 NOT READ); EEX auction data: hand entry (D-14 route 3), plan 02-07.

## User-supplied data (filled in plan 02-11)

### NGFS Phase V (D-40, D-43; user paste of the IIASA explorer table, route 3)

- File: `data_raw/Src_NGFSPhaseV/ngfs_price_carbon_user_paste.tsv` (gitignored), 2,228 bytes, .tsv suffix, sha256 `42bd29b4b90294beeb9548235dbedf75954186caf5a7b4855ad860e3f6396281`.
- Method: sha256 computed with a stdlib script under `python3 -I` (path as argument); parsed read-only with `.venv/bin/python -W ignore -I tools/parse_ngfs.py` using `--model "REMIND-MAgPIE 3.3-4.8" --region "OECD & EU (R5)"`. Exactly three rows returned; all values compared one by one with the RESEARCH addendum (all equal).
- Model: REMIND-MAgPIE 3.3-4.8. Region: OECD & EU (R5) (note: R5 aggregate used as the EU proxy; limitation). Variable: `Price|Carbon`. Unit: US$2010/t CO2.
- Footer in the export: "© NGFS Phase 5 Scenario Explorer https://data.ene.iiasa.ac.at/ngfs".

| Scenario | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 | 2055 |
|---|---|---|---|---|---|---|---|
| Current Policies | 23.28186044073566 | 23.27705035642764 | 23.31220235560375 | 23.39144477859998 | 23.52964512661944 | 23.71263250865933 | 23.94119902155565 |
| Nationally Determined Contributions (NDCs) | 121.5670480013598 | 216.911391375443 | 215.9468030914937 | 214.9804569215596 | 213.8716366193923 | 211.1302917041736 | 206.8712342559588 |
| Net Zero 2050 | 152.3844736690992 | 282.2098852376754 | 452.7636315503082 | 623.9807303273395 | 795.3846925061491 | 870.0502582689974 | 898.2429363719594 |

Excluded rows and why:
- GCAM 6.0 NGFS (3 rows): Current Policies is identically 0.
- MESSAGEix-GLOBIOM 2.0-M-R12-NGFS (2 rows): no Net Zero 2050 row.
- REMIND-MAgPIE 3.3-4.8 IntegratedPhysicalDamages (median) (2 rows): damage variants, not the baseline scenarios.

The explorer snapshot ngfs_snapshot_1792416458.csv (sha256 15d8e1eaf46989f6cab3f19243fd66e375781e1d2221011cf09e747ea175639f) and its .zip (sha256 7d62bf5b45d5c4f2ab11fb014aa2b72fae83d0e4ed2582e42fe243939144983b) matched this paste and were deleted at the user's request on 2026-10-19 (D-43); the .zip was never extracted by code.

Licence: adapted CC BY 4.0 (NGFS Phase 5 Scenario Explorer licence). Transcribed from https://data.ene.iiasa.ac.at/ngfs/#/license by the user on 2026-10-19 (D-44; key clauses in `data_raw/Src_NGFSPhaseV/license_summary_user_paste.txt`). "This Public License is adapted from the Creative Commons Attribution 4.0 International Public License with the aim of keeping the Licensed Material always up-to-date and avoiding the circulation of obsolescent data constituting substantial portions of the Licensed Material." Section 2(a)(1): may "reproduce and Share parts of the Licensed Material, as long as this does not constitute a reproduction of a substantial portion of the Licensed Material" and produce, reproduce and share Adapted Material (figures, tables, derived analysis). Section 3(a)(1): attribution required (creator, copyright notice, licence and warranty-disclaimer notice, URI), "indicate if You modified the Licensed Material", and include the licence text or URI. Section 2(a)(5)(C): no implication of endorsement. Our use (3 scenarios x 7 years of one variable, model and region, converted to EUR 2025 and interpolated) is parts plus adapted material. Citation wording: "NGFS Phase 5 Scenario Explorer, hosted by IIASA", https://data.ene.iiasa.ac.at/ngfs, with the line "© NGFS Phase 5 Scenario Explorer" and a statement that values were modified.

### Damodaran Europe (D-42; D-14 route 3, read from the official file)

- Source URL: https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccEurope.xls
- sha256: `05caa5715824c0855d42f6726e8b7f52f77b220cd5d2893af9cbbc71c4abcf5e`; sheet "Industry Averages"; date updated 2026-01-05 (serial 46027); file saved 2026-01-09.
- Method: OLE streams checked first: only Workbook and summary information, no VBA or macro storage; read through a read-only stdlib parser; file deleted at the user's request. Claude's fetcher was not used and no .xls exception was added (D-16).

| Industry | Firms | Cost of capital (US$) | Cost of capital (Euros) |
|---|---|---|---|
| Chemical (Specialty) (base) | 92 | 8.873% | 7.811% |
| Chemical (Basic) | 58 | 6.180% | 5.144% |
| Chemical (Diversified) | 7 | 8.668% | 7.608% |
| Total market (without financials), context | 5,757 | 7.644% | 6.594% |

Sheet inputs (context): long-term treasury 3.95%, equity risk premium 5.27%, global default spread 0.68%, expected euro inflation 1.5% (used by Damodaran's Euros column).

Fisher (D-19, D-42): 1.07811 / 1.02 - 1 = 5.70% real. Mismatch to state in the rationale: Damodaran's Euros column embeds 1.5% expected euro inflation; the model's Fisher step uses the ECB 2.0% target.

## EEX 2025 auctions (WR-01, plan 02-16)

Parameter: Carbon_EUA_Avg2025 = 73.43 EUR/tCO2 (2025 volume-weighted mean auction clearing price, EU ETS1 primary market, EEX).

Route-3 history: the figure (and the simple mean 73.45, 213 successful auctions, last auction 15 Dec 2025 at 84.60) was computed during research on 2026-10-18 from the EEX auction history file. The inputs were not retained and the code never opens the EEX .zip (D-37), so the arithmetic cannot be reproduced from this repository. The user chose not to supply the 2025 auction rows on 2026-10-20 (option A2). Outcome: status downgraded to Analyst assumption, rationale begins "Unverified transcription:", value unchanged at 73.43. No sha256, sums or row-level data are logged because no file was supplied.

## Legal texts (WR-02 re-read, plan 02-15)

Read date: 2026-10-20. Method: HTTP GET of the HTML page only, nothing saved to disk. The WebFetch tool was not available in the executor session, so a plain GET was used. Outcome words: VERIFIED (sentence read and equal to config), NOT READ (page empty, blocked or without the sentence), MISMATCH (sentence read and different).

EUR-Lex answered every request with HTTP 202 and an empty body (AWS WAF challenge page), as 02-RESEARCH 3.11 predicted. The Eurostat nrg_bal metadata page was read (HTTP 200) but only says that classification follows NACE Rev. 2; it does not state that the chemical and petrochemical sector covers Divisions 20 and 21, so it does not corroborate the flag.

| Parameter id | URL tried | Article | Outcome | Quote or failure |
|---|---|---|---|---|
| Carbon_ETS2_StartYear | https://eur-lex.europa.eu/eli/reg/2026/667/oj/eng | Art. 2 | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_StartYearEnacted | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30d(1) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_StabPrice | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30h(2) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_StabMonths | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30h(2) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_StabRelease | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30h(2) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_TripleTrigger | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30h(3) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_TripleRelease | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Art. 30h(3) | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_Gas | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_LPG | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_Naphtha | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_OtherFuels | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_FleetDiesel | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_Elec | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS2_Scope_Heat | https://eur-lex.europa.eu/eli/dir/2023/959/oj/eng | Annex III and Art. 30a | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Carbon_ETS1_ThermalThresholdMW | https://eur-lex.europa.eu/eli/dir/2003/87/oj/eng | Annex I, combustion of fuels, 20 MW | NOT READ | EUR-Lex returned HTTP 202 with an empty body (WAF challenge) |
| Base_NRG_IncludesC21 | https://eur-lex.europa.eu/eli/reg/2008/1099/oj/eng (Annex A item 2.6.1.6); also https://ec.europa.eu/eurostat/cache/metadata/en/nrg_bal_esms.htm | Annex A 2.6.1.6, NACE 20 and 21 | NOT READ | EUR-Lex: HTTP 202, empty body (WAF challenge). Eurostat metadata: page read, no statement on NACE 20 and 21 |

VERIFIED rows: 0. NOT READ rows: 16. MISMATCH rows: 0. Plan 02-16 asks the user to paste the article text for each NOT READ row.

### Final outcomes after user paste (plan 02-16, Part B1, partial)

Read date: 2026-10-20. File: data_raw/Src_ETSDirective/legal_text_user_paste.txt (plain text, user paste from EUR-Lex in a browser, read as untrusted data only), 4134 bytes, sha256 6530b21dadb8d601890c6299be6cc546cca4ea7ff860bee96d6a5f748dd531b8 (updated after the user pasted the full Article 30h on 2026-10-20; earlier version was 3134 bytes, sha256 180236187b0b2475791ebb4b8731e39653458ff7d34f911c04c48361b1a53fb0). The file is kept in data_raw (untracked).

| Parameter id | Outcome | Quote from the paste |
|---|---|---|
| Carbon_ETS2_StartYear | VERIFIED (user paste) | Reg. (EU) 2026/667, postponement provision (article number not shown in the paste; copied by the user from https://eur-lex.europa.eu/eli/reg/2026/667/oj/eng): "The operation of emissions trading for buildings, road transport and additional sectors set out in Chapter IVa of Directive 2003/87/EC shall be postponed until 2028." |
| Carbon_ETS2_StabPrice | VERIFIED (user paste) | Text read: Dir. (EU) 2023/959 as enacted; later amendments (2026) not checked. Dir. 2003/87/EC Art. 30h(2) as inserted by Dir. (EU) 2023/959: "Where the average price of allowances referred to in paragraph 1 of this Article exceeds a price of EUR 45 for a period of two consecutive months, 20 million allowances ... Indexation based on the European index of consumer prices for 2020 shall apply. ... up to 31 December 2029." (EUR 45 in 2020 prices) |
| Carbon_ETS2_StabMonths | VERIFIED (user paste) | Text read: Dir. (EU) 2023/959 as enacted; later amendments (2026) not checked. Same Art. 30h(2) sentence: "for a period of two consecutive months" |
| Carbon_ETS2_StabRelease | VERIFIED (user paste) | Text read: Dir. (EU) 2023/959 as enacted; later amendments (2026) not checked. Same Art. 30h(2) sentence: "20 million allowances covered by this Chapter shall be released". Release possible up to 31 Dec 2029. The consolidated text after the 2026 amendments was not read. |
| Carbon_ETS1_ThermalThresholdMW | VERIFIED (user paste, original 2003 wording only) | Text read: original 2003 Annex I wording; consolidated text not read. Dir. 2003/87/EC Annex I: "Combustion installations with a rated thermal input exceeding 20 MW (except hazardous or municipal waste installations)", gas column "Carbon dioxide". This is the original 2003 wording; the consolidated text was not read (an analyst note in the paste says the threshold is unchanged, which is not itself verified). |
| Carbon_ETS2_StartYearEnacted | NOT READ (stays Analyst assumption) | Art. 30d(1) not supplied |
| Carbon_ETS2_TripleTrigger | VERIFIED (user paste) | Text read: Dir. (EU) 2023/959 as enacted; later amendments (2026) not checked. Art. 30h(3) as inserted by Dir. (EU) 2023/959: "3. Where the average price of allowances referred to in paragraph 1 of this Article is more than three times the average price of allowances during the six preceding consecutive months, 150 million allowances covered by this Chapter shall be released from the market stability reserve in accordance with Article 1a(7) of Decision (EU) 2015/1814." Multiple = 3. |
| Carbon_ETS2_TripleRelease | VERIFIED (user paste) | Text read: Dir. (EU) 2023/959 as enacted; later amendments (2026) not checked. Same Art. 30h(3) sentence: "150 million allowances covered by this Chapter shall be released". |
| Carbon_ETS2_Scope_Gas, _LPG, _Naphtha, _OtherFuels, _FleetDiesel, _Elec, _Heat | NOT READ (stay Analyst assumption) | Annex III and Art. 30a not supplied |
| Base_NRG_IncludesC21 | NOT READ (stays Analyst assumption) | Reg. 1099/2008 Annex A not supplied |

Art. 30h(1) review note resolved: Art. 30h(1) (price more than twice, or 1.5 times for 2027 and 2028, the six-month average for more than three consecutive months; 50 million allowances) and Art. 30h(3) (more than three times; 150 million allowances) are separate mechanisms. The model uses 30h(2) and 30h(3); 30h(1) is context only and no model id refers to it. Paragraph 4 (when the 30h(2) condition is met on the same day as the 30h(1) or (3) condition, additional allowances are released only under paragraph 1 or 3) and paragraph 6 (no further release under this Article earlier than 12 months after a release) were read and are context only.

Counts after this plan (updated for Art. 30h(3)): VERIFIED 7 (user paste), NOT READ 9 ids (StartYearEnacted, 7 scope flags, Base_NRG_IncludesC21), MISMATCH 0 (no value was contradicted by a supplied text).

## Context figures and dates (WR-01, plan 02-18)

Executor session 2026-10-20. No web reader (WebFetch) was available in this session, so web figures could not be re-read today; they are downgraded to Analyst assumption ("Unverified transcription") and listed for user follow-up. Dataset dates were read from local files with a stdlib script (python3 -I, path as argument, prints only the top-level `updated` field).

| Item | URL | Read date | Outcome | Value |
|---|---|---|---|---|
| Src_EurostatSBS dataset date | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sbs_sc_ovw?geo=BE&nace_r2=C20&nace_r2=C21&format=JSON&lang=EN | 2026-10-20 (file fetched 2026-10-19) | VERIFIED | sbs_sc_ovw_BE_C20_C21.json, sha256 e8f38afb04113a358437f3efbf7bebe64611489d163a41698fee4bdc0467cd0a, `updated` = 2026-09-30T11:00:00+0200 |
| Src_EurostatElecPrice dataset date | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_205?geo=BE&tax=X_VAT&currency=EUR&format=JSON&lang=EN | 2026-10-20 (file fetched 2026-10-19) | VERIFIED | nrg_pc_205_BE_X_VAT.json, sha256 319b25f3d84cdc740b13c647913a7dce2e50053d21601a6e2e075a33c966a8f2, `updated` = 2026-10-19T11:00:00+0200. The earlier edition text "2026-10-16" was wrong and is corrected to 2026-10-19. |
| Base_Fleet_gCO2PerKm 184.9 gCO2/km (2024; 2025 provisional 172.1) | https://www.eea.europa.eu/en/newsroom/news/average-co2-emissions-from-new-cars-and-vans-significantly-decreased-in-2025 (published 25 June 2026) | 2026-10-20 | VERIFIED | Orchestrator web fetch of the official HTML page (text extracted by the fetch tool; nothing saved to disk). Quote: "Average CO2 emissions: 172.1 g CO2/km (184.9 g CO2/km in 2024)" and "The average emissions were 172.1 grams CO2/km, down by 12.8 g CO2/km compared to 2024." Status Sourced. |
| Fin_HICP_EA_Sep2026 3.8% (Belgium 4.5%) | https://ec.europa.eu/eurostat/web/products-euro-indicators/w/2-16102026-ap | 2026-10-20 | VERIFIED | Orchestrator web fetch of the official HTML page (text extracted by the fetch tool; nothing saved to disk). Release "Annual inflation up to 3.8% in the euro area", 16 October 2026. Quote: "The euro area annual inflation rate was 3.8% in September 2026, up from 3.2% in August." Belgium September 2026: 4.5% (table). Status Sourced. Context only, not used in the base case. |
| Fin_InflationLongRun 2.0% | https://www.ecb.europa.eu/mopo/strategy/pricestab/html/index.en.html | 2026-10-20 | VERIFIED | Orchestrator web fetch of the official HTML page (text extracted by the fetch tool; nothing saved to disk). Quote: "price stability is best maintained by aiming for 2% inflation over the medium term" (Governing Council, after the July 2021 strategy review). Status Sourced. |

These three rows were NOT READ in the 02-18 executor session (WebFetch unavailable) and were temporarily downgraded to Analyst assumption; the orchestrator re-read them on 2026-10-20 and each matched, so they are promoted back to Sourced. No numeric value was changed.

### US-CPI comparison factor (indicative, D-41)

The workbook says a US-CPI route "would give about 1.31, so prices about 25% higher". This is an indicative analyst estimate, not a sourced input.

- Research record: 02-RESEARCH 3.9, read 2026-10-18, from the US statistics agency API (api.bls.gov, text only). US CPI-U series CUUR0000SA0, annual average: 2010 = 218.056, 2025 = 321.943.
- Ratio 321.943 / 218.056 = 1.47638.
- Divided by the 2025 average USD per EUR: research used 1.12998, giving 1.47638 / 1.12998 = 1.3066; with the Eurostat 2025 average of 1.13 in this log, 1.47638 / 1.13 = 1.3065. Rounded: about 1.31.
- That host is not allowlisted (D-41) and the values were not re-fetched, which is why the figure is labelled indicative. There is no US CPI input and no source row for it in the workbook.
