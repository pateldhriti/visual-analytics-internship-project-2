# Story 5 — Cross-Dataset CMA Audit

Audit date: 2026-11-13. Branch: `rebaseline-data-pipeline`.
Scope: **read-only audit**. No staging CSVs, PostgreSQL objects, analysis views or Superset assets were created or changed.

### Decisions recorded (project owner, 2026-11-13)

- **D1: Primary 2021 cross-dataset design = Option 1:** StatsCan Census Profile 2021 + CMHC **October 2021** (C21), 36 matched CMA-level geographies. Option 2 (CMHC 2022 revised) is **not** used as the primary design.
- **D2: Geography-basis caveats are mandatory** in every cross-dataset view and chart. Each view carries `cmhc_geography_basis = 'pre_2021_census'`, `census_geography_basis = '2021_census'` and a `geography_caveat` text column. Each chart shows the caveat in its subtitle or footnote.
- **D3: Q2 (count-based) keeps a stronger warning,** because the boundary mismatch is material for counts. Its view carries `boundary_mismatch_severity = 'material'` and a dedicated `count_ratio_warning` column. The chart shows the warning prominently (subtitle, not only a footnote). See §7 Q2.

Sources audited (all read in place, never modified):

| # | File | SHA-256 (before = after audit) |
|---|---|---|
| S1 | `data/raw/statcan/98-401-X2021002_eng_CSV.zip` (Census Profile 2021, CMA/CA) | `fd4c3000e3598ee9227c5093be5a239785487dfcf16933d28a7d6a218ed1f68c` |
| C19 | `data/raw/cmhc/canada_history/rmr-canada-2019-en.xlsx` | `8389cae5200639cfb966ff7bbe9d65ae723e335bf1d6179abbe004e7731a6274` |
| C20 | `data/raw/cmhc/canada_history/rmr-canada-2020-en.xlsx` | `5cb1a4ab7cb6b5652531e6282ff148ea81a0010909e87354b86c7c48756b6104` |
| C21 | `data/raw/cmhc/canada_history/rmr-canada-2021-en.xlsx` | `e8a02c437480ea47ccd9ad07e9aad3c874546ed37edb059f3c3d1b0624d08f49` |
| C22 | `data/raw/cmhc/canada_history/rmr-canada-2022-en.xlsx` | `2f5a8a47c1ae07bd4c58b396eb57777408156db0c7e8e6c9adcef311d9356a08` |
| C23 | `data/raw/cmhc/canada_history/rmr-canada-2023-en.xlsx` | `c8bc5f6c1e43ab8d2bcb227c94336f7bc8e6b9fd35e40c089d30cc2cf14f2b68` |
| C24 | `data/raw/cmhc/canada_history/rmr-canada-2024-en.xlsx` | `9585b923ece39c0847a8fd1de4a57579c099b08ef2a836c8e811ff808efb0a1f` |
| C25 | `data/raw/cmhc/rmr-canada-2025-en.xlsx` | `ac2f4157917a6efed405f6da67751ef3c32d378f27fdff602f99a12d84d813ea` |

Full hashes were recorded before the audit and re-verified after it with `sha256sum -c` (all 8 OK). `data/raw/` is git-ignored (`.gitignore:228`), so the new `canada_history/` workbooks are not tracked by git; a checksum manifest for them should be added when production ETL is built (see §9).

---

## 1. StatsCan fields discovered (Census Profile 2021, 98-401-X2021002)

### 1.1 File structure

- ZIP entries: `98-401-X2021002_English_CSV_data.csv` (66.3 MB, cp1252), `98-401-X2021002_English_meta.txt`, `98-401-X2021002_Geo_starting_row.CSV`, `README_meta.txt`.
- 420,960 rows = **160 geographies × 2,631 characteristics**. Every geography has all 2,631 characteristics, and `CHARACTERISTIC_ID → CHARACTERISTIC_NAME` is identical for all 43 CMA-level geographies (verified).
- Columns: `CENSUS_YEAR, DGUID, ALT_GEO_CODE, GEO_LEVEL, GEO_NAME, TNR_SF, TNR_LF, DATA_QUALITY_FLAG, CHARACTERISTIC_ID, CHARACTERISTIC_NAME, CHARACTERISTIC_NOTE, C1_COUNT_TOTAL, SYMBOL, C2_COUNT_MEN+, SYMBOL, C3_COUNT_WOMEN+, SYMBOL, C10_RATE_TOTAL, SYMBOL, C11_RATE_MEN+, SYMBOL, C12_RATE_WOMEN+, SYMBOL` (the six `SYMBOL` headers repeat, so parsers must read columns by position).
- GEO_LEVEL counts: Census metropolitan area **41**, Census metropolitan area part **2** (Ottawa – Gatineau Quebec part `24505`, Ontario part `35505`), Census agglomeration 111, Census agglomeration part 6. **There is no Canada or province row.**
- Symbol legend (meta file): `..` not available for the reference period, `...` not applicable, `E` use with caution, `F` too unreliable to be published, `r` revised, `x` suppressed, `rE` revised and use with caution.
- `DATA_QUALITY_FLAG` (5 digits): `20000` (excludes one or more incompletely enumerated reserves) for **Montréal, Brantford, Calgary, Vancouver**. All other CMAs are `00000`. Long-form non-response (`TNR_LF`) ranges from 2.5% to 5.8%, and Windsor is 3.1%.

### 1.2 Requested fields: exact characteristics

Grain: one value per CMA (or CMA part) for census year 2021. Values are in `C1_COUNT_TOTAL`, and percentages are repeated in `C10_RATE_TOTAL`.

| Requested concept | Exists? | CHARACTERISTIC_ID | Exact CHARACTERISTIC_NAME | Unit | Source / ref. period | Footnote | Windsor value |
|---|---|---|---|---|---|---|---|
| Total private households (tenure base) | Yes | **1414** | `Total - Private households by tenure - 25% sample data` | households | 25% sample, May 2021 | 50 | 165,675 |
| Owner households | Yes | 1415 | `Owner` | households | 25% sample | 50 | 120,050 (72.5%) |
| **Renter households** | Yes | **1416** | `Renter` | households (C1); % of 1414 (C10) | 25% sample | 50 | 45,625 (27.5%) |
| Band housing | Yes | 1417 | `Dwelling provided by the local government, First Nation or Indian band` | households | 25% sample | 50 | 0 |
| **Renter share / tenure** | Yes (published) | 1416 `C10_RATE_TOTAL` | (rate column of `Renter`) | % | 25% sample | 50 | 27.5 |
| Total private households (100% data) | Yes | 50 | `Total - Private households by household size - 100% data` | households | 100% data | — | 165,665 |
| Tenant households base for shelter indicators | Yes | **1490** | `Total - Tenant households in non-farm, non-reserve private dwellings - 25% sample data` | households | 25% sample | — | 45,605 (C10 = `...`) |
| **Renter households spending 30%+ on shelter** | **Rate only** | **1492** | `% of tenant households spending 30% or more of its income on shelter costs` | % | shelter cost 2021, income 2020 | 61 | 34.8 |
| Renter 30%+ **count** | **Not published per tenure in S1** | — | Only the all-tenure count exists (1467 `Spending 30% or more of income on shelter costs`, under 1465 owner+tenant base) | — | — | 61 | (all tenures 28,745) |
| Tenant core housing need | Yes | 1493 | `% in core housing need` (child of 1490) | % | 25% sample | 63 | 20.3 |
| Tenant subsidized housing | Yes | 1491 | `% of tenant households in subsidized housing` | % | 25% sample | 67 | 16.4 |
| Renter shelter cost (median) | Yes | **1494** | `Median monthly shelter costs for rented dwellings ($)` | $ / month | 2021 | 65 | 980 |
| Renter shelter cost (average) | Yes | 1495 | `Average monthly shelter costs for rented dwellings ($)` | $ / month | 2021 | 65 | 1,069 |
| Owner 30%+ (for contrast) | Yes | 1484 | `% of owner households spending 30% or more of its income on shelter costs` | % | | 61 | 10.9 |
| **Median renter household income** | **NO** | — | **No tenure-specific income characteristic exists in S1** (searched all 2,631 names for tenant/renter/rent/shelter) | — | — | — | — |
| Median household income (all tenures) | Yes | 243 | `Median total income of household in 2020 ($)` | $ / year | 100% data, income year 2020 | 26 | 82,000 |
| Median after-tax household income (all tenures) | Yes | 244 | `Median after-tax income of household in 2020 ($)` | $ / year | 100% data | 26 | 73,000 |
| Average household income (all tenures) | Yes | 252 | `Average total income of household in 2020 ($)` | $ / year | 25% sample | 27 | 102,300 |
| Other renter-specific income measures | **NO** | — | None in S1 | — | — | — | — |

Supporting dwelling-stock context (100% data, all tenures): 41 `Total - Occupied private dwellings by structural type of dwelling`, 46 `Apartment in a building that has fewer than five storeys`, 47 `Apartment in a building that has five or more storeys`.

### 1.3 Definitions that constrain interpretation (meta file footnotes)

- **Footnote 50 (Tenure):** a household rents if no member owns the dwelling. This includes dwellings provided **without cash rent or at reduced rent, and co-operatives**. Census "renter households" therefore include subsidized, co-op, condo-rented and house-rented households, not only purpose-built rental apartments.
- **Footnote 61 (Shelter-cost-to-income ratio):** covers households with total income above 0 that are not on a farm or a reserve. **Shelter cost refers to 2021 and income to 2020.** The 2020 income includes COVID-19 benefits (characteristic 124 shows 29.9% of Windsor's 15+ population received them).
- **Footnote 65 (Shelter cost, renters):** rent plus electricity, heat, water and municipal services where these apply. This differs from CMHC's rent concept (see §5).
- **Footnote 67 (Subsidized):** RGI, social, public, non-profit, rent supplements and housing allowances.

### 1.4 Coverage of key fields across the 43 CMA-level geographies

All 43 have published values for 1414, 1416, 1490, 1491, 1492, 1493, 1494, 1495 and 243. The only symbols on these IDs are `...` in the rate column of base/total rows (1, 242, 251, 1490), which is expected. **No `x`, `F` or `E` appears on any key field.**

### 1.5 What S1 cannot provide

- Median or average **renter** household income, or any rent-to-renter-income ratio.
- The count of renter households spending 30%+ (only the percentage is published). A count could only be derived as `1492 × 1490 / 100`. That is a derived estimate subject to rounding, so it should not be stored as if published.
- Renter shelter-cost-to-income distribution beyond the 30% threshold.
- Note: the project's Windsor-only table 98-10-0252 (`data/raw/statcan/9810025201_databaseLoadingData (1).csv`) does give tenure × 30%+ counts, but **for Windsor only**. It cannot support cross-CMA comparison and is out of scope here.

---

## 2. CMHC historical metrics discovered (Canada RMR 2019–2025)

### 2.1 Sheets per workbook

| Workbook | Sheets |
|---|---|
| 2019 | Table 1.0, 4.1, 4.2 (no index, no legend text) |
| 2020 | Index, 1.0, 4.1, 4.2, **5.0** |
| 2021 | Index, 1.0, 4.1, 4.2, 5.0 |
| 2022 | Index, 1.0, 4.1, 4.2, 5.0, **6.0, 6.1** |
| 2023 | Table of Contents, 1.0, 4.1, 4.2, 5.0, 6.0, 6.1 |
| 2024 | Table of Contents, 1.0, 4.1, 4.2, 5.0, 6.0, **6.1 (new: contribution of turnover units), 6.2** |
| 2025 | Table of Contents, 1.0, 4.1, 4.2, 5.0, **6.0 (restructured: all bedroom types, 44 cols)**, 6.1, 6.2 |

### 2.2 Table 1.0: the only table present in all seven years

Title (every year): *"1.0 Rental Market Indicators – Privately Initiated Apartment Structures of Three Units and Over – Provinces and Major Centres."* The 2019 title is split across rows 1–3. From 2020 on it is in a single cell, A3.

| Item | 2019 | 2020–2025 |
|---|---|---|
| Header row (`Centre`) | row 6 | row 7 |
| First data row | 7 | 8 |
| Column layout (identical all years) | A centre · B/C prev vacancy+quality · D/E cur vacancy+quality · F trend · G/H prev turnover+q · I/J cur turnover+q · K trend · L/M prev rent+q · N/O cur rent+q · P/Q prev fixed-sample % change+q · R/S cur % change+q | same |
| Number format | numeric cells | text with thousands commas (`'1,154'`) |
| Trend glyph for "no significant change" | `−` (U+2212) | `-` (2020–2022), `-` (2023–2025). Legend uses `–` |

Metrics in Table 1.0 (all CMAs, **Privately initiated apartment structures of 3+ units**, October survey):

| Metric | Bedroom scope | Dwelling scope | Unit | Period columns | Quality letter | Trend flag |
|---|---|---|---|---|---|---|
| Vacancy rate | **Total (all bedroom types)** | apartment, 3+ units | % | Oct prev, Oct current | yes | yes |
| Turnover rate | Total | apartment | % | Oct prev, Oct current | yes | yes |
| Average rent | **2 bedroom**, "New and Existing Structures" | apartment | $ / month | Oct prev, Oct current | yes | no |
| % change of average rent from fixed sample | **2 bedroom**, "Existing Structures Only" | apartment | % | Oct(Y-2)→Oct(Y-1), Oct(Y-1)→Oct(Y) | yes | no (uses `++`) |
| **Rental universe** | — | — | — | **NOT IN TABLE 1.0 IN ANY YEAR** | — | — |

### 2.3 Where a rental universe does exist

| Table | Years | Universe definition | CMAs | Windsor? | Verdict |
|---|---|---|---|---|---|
| 4.1 "Apts in the RMS" | 2019–2025 | private apartments in the RMS | **17 fixed condo-market CMAs** | **No** (Windsor never listed) | Rejected for Story 5 |
| 5.0 "Universe" (rental arrears table) | **2020–2025 only** | 2020 title: *"Privately Initiated **Apartment** Structures of Three Units and Over"*. 2021–2025 title: *"Privately Initiated **Row (Townhouse) and Apartment** Structures of Three Units and Over"* | 2020–2022: 36 CMA rows. 2023–2025: 42 | Yes | **Usable for 2021 only, as row + apartment** (see below) |

Verification of Table 5.0 "Universe":
- Windsor 2024 = **19,292** and 2025 = **19,883**. These equal the Windsor RMR Table 3.1.3 *row and apartment* universe already in `data/staging/windsor_rental_market.csv` (Oct-24 19,292; Oct-25 19,883). So the column is the CMHC row+apartment universe.
- Windsor 2021 = 16,314, versus the apartment-only universe of 15,657 (Windsor RMR Table 1.1.3 history). This is consistent with row+apartment.
- **2020 inconsistency:** the title says *apartment*, but Windsor 2020 = 16,067, while the apartment-only universe is 15,412. The value looks like row+apartment. The scope for 2020 cannot be confirmed from the file, so 2020 must not be combined with 2021+.
- 2019: Table 5.0 does not exist.
- Universe cells carry no quality letter (it is a census of structures, not a sample estimate).
- Table 5.0 has a single period per workbook (no prior-year column), so **there is no 2022 value revised to the 2021 census geography**. 2022 exists only on the pre-2021 boundary (in C22), and 2023 onward only on the 2021 boundary.

### 2.4 Other tables (not consistently available 2019–2025)

- 4.2 (rental condominium apartments): 17 CMAs, no Windsor. Rejected.
- 5.0 arrears rates: mostly `**` for Windsor. Rejected.
- 6.0 / 6.1 / 6.2 turnover vs non-turnover rent: from 2022 only, and the layout changes in 2024 and 2025. Rejected for a 2019–2025 series.

### 2.5 Suppression / reliability handling (Table 1.0)

Legend text (C20–C25; C19 has none): `a` Excellent, `b` Very good, `c` Good, `d` Poor (use with caution); `**` data suppressed; `++` change in rent not statistically significant; `↑`/`↓` statistically significant increase or decrease; `-`/`–` effective sample does not allow a significance call. C20 adds `- – No units exist in the universe for this category` and an `N/A – Data not available` legend line (which sits in column A, so parsers must not read it as a centre).

Marker counts in the **current-year** column, CMA rows only:

| Year | Vacancy | Avg 2BR rent | Turnover | Fixed-sample % change |
|---|---|---|---|---|
| 2019 | 0 suppressed | 0 | 1 `**` (Barrie), 6 `d` | 1 `d` |
| 2020 | 0 | 0 | 3 `d` | 1 `**`, 2 `++`, 1 `d` |
| 2021 | 0 | 0 | 4 `d` | 2 `**`, 3 `++`, 1 `d` |
| 2022 | 0 | 0 | 1 `d` | 2 `**`, 2 `d` |
| 2023 | 0 | 0 | 1 `**` | 3 `**`, 4 `d` |
| 2024 | 0 | 0 | 1 `**`, 4 `d` | 4 `**`, 2 `++`, 8 `d` |
| 2025 | 1 `d` | 0 | 3 `d` | 8 `**`, 1 `++`, 3 `d` |

Rules for later ETL (consistent with existing project rules): `**` → value NULL with status `suppressed`; `++` → value NULL with status `change_not_significant` (never 0); `d` kept as `reliability_code = 'd'` with the value retained.

### 2.6 Census-geography boundary change

- C23 footnote §: *"2023 and 2022 data are based on the 2021 census geographic definitions; 2022 data have been revised to reflect these definitions."* C24 and C25 say the same for their own two years.
- C19–C22 have no geography footnote, so their values are on the **pre-2021 (2016) census** definitions.
- **The CMHC 2021 data (C21) are therefore on 2016-census CMA boundaries, while the StatsCan 2021 Census Profile is on 2021-census boundaries.** This is the most important constraint for the "same-year 2021" design (see §5).
- New CMAs appear from C23 onward (2021 census CMAs): **Fredericton, Drummondville, Red Deer, Kamloops, Chilliwack, Nanaimo**. *Belleville CMA* (C19–C22) becomes *Belleville - Quinte West CMA* (C23–C25), a name **and** definition change.

---

## 3. Year-to-year CMHC comparability

### 3.1 Cross-workbook consistency test

Each workbook repeats the previous October in its "prev" columns. I compared every CMA × metric "prev" value in workbook Y with the "current" value in workbook Y-1: **901 matched exactly and 11 differed**.

| Workbook | Differences (published in Y-1 → restated in Y) | Cause |
|---|---|---|
| 2021 | Saint John fixed-sample 3.3→3.4; Saguenay fixed-sample 1.9→2.0; Sudbury rent 1133→1134; Lethbridge rent 1051→1050 | minor CMHC revisions |
| 2022 | Winnipeg vacancy 5.0→5.1 | minor revision |
| 2023 | Halifax rent 1449→1445, fixed-sample 9.3→9.2; Ottawa-Gatineau (Ont.) turnover 16.8→16.7, rent 1625→1615; **Windsor turnover 12.7→12.0, rent 1197→1174** | **2021-census geography revision of 2022** |

Windsor's 2022 values match the project's existing verified history (`clean.rental_market_windsor_history`: pre-2021 rent 1197 / turnover 12.7; 2021-census rent 1174 / turnover 12.0). This cross-confirms the two sources.

### 3.2 Metric-by-metric verdict (2019–2025)

| Metric | Table | Present all 7 years | Definition stable | Verdict |
|---|---|---|---|---|
| Vacancy rate, apartments, total bedrooms | 1.0 | Yes | Yes | **Consistent** (break at 2022 geography) |
| Average rent, 2-bedroom apartments | 1.0 | Yes | Yes | **Consistent** (break at 2022) |
| Turnover rate, apartments, total | 1.0 | Yes | Yes | **Consistent** (break at 2022, rare `**`) |
| Fixed-sample % change in 2BR rent | 1.0 | Yes | Yes | **Consistent but often suppressed or `++`** (up to 9 of 42 CMAs in 2025) |
| Rental universe | 5.0 / 4.1 | **No** (5.0 2020–2025; 2020 scope ambiguous; 4.1 has no Windsor) | No | **Not consistent 2019–2025** |

Recommended yearly selection rule, mirroring the accepted Windsor history design:
- Year Y comes from workbook Y's current-year column (`geography_basis = pre_2021_census` for 2019–2021, `2021_census` for 2023–2025).
- 2022 gets **two rows**: C22 current column (`pre_2021_census`) and C23 previous column (`2021_census`, `is_primary_series = true`).
- The minor revisions in the "prev" columns are documented but not substituted.

---

## 4. CMA overlap and mapping

### 4.1 Counts

| Item | Count |
|---|---|
| StatsCan CMAs (GEO_LEVEL = CMA) | **41** (+ 2 Ottawa – Gatineau parts = 43 CMA-level geographies) |
| CMHC CMA rows, 2019 / 2020 / 2021 / 2022 | 36 / 36 / 36 / 36 (34 whole CMAs + 2 Ottawa – Gatineau parts) |
| CMHC CMA rows, 2023 / 2024 / 2025 | 42 / 42 / 42 (40 whole CMAs + 2 parts) |
| CMHC CMA rows present in **every** year 2019–2025 by exact name | **35** (33 whole CMAs + 2 Ottawa – Gatineau parts) |
| …plus Belleville via the explicit rename | 36 geographies (Belleville flagged as a definition change) |
| CMHC rows **not** mapped | `Canada CMAs` (national aggregate). Province "10,000+", `Canada 10,000+` and `Charlottetown CA` are excluded by design |
| StatsCan geography with no CMHC row | `Ottawa - Gatineau` (whole CMA). CMHC publishes only the two parts |
| **Safely matched for 2021 cross-dataset analysis** | **36** (C21 rows ↔ S1 DGUIDs, 1:1, no duplicates) |
| **Safely matched for 2023–2025** | **42** |

CMHC does not publish a whole Ottawa – Gatineau row. The two parts match the two StatsCan CMA-part rows exactly, so the parts are the unit of comparison. **Do not sum the parts to make a whole CMA** (rates and averages cannot be summed).

### 4.2 Deterministic mapping strategy (no fuzzy matching)

1. **Rule A (exact after suffix):** strip the trailing literal `" CMA"` from the CMHC centre name and require an **exact, case-sensitive, accent-sensitive** match to S1 `GEO_NAME` where `GEO_LEVEL = 'Census metropolitan area'`. This matches 35 CMHC names.
2. **Rule B (explicit lookup table):** a checked-in table, keyed by the exact CMHC string, with the target **DGUID**:

| CMHC centre (exact) | StatsCan GEO_NAME | DGUID | Reason |
|---|---|---|---|
| `Kitchener-Cambridge-Waterloo CMA` | `Kitchener - Cambridge - Waterloo` | 2021S0503541 | hyphen spacing |
| `St. Catharines-Niagara CMA` | `St. Catharines - Niagara` | 2021S0503539 | hyphen spacing |
| `Abbotsford-Mission CMA` | `Abbotsford - Mission` | 2021S0503932 | hyphen spacing |
| `Greater Sudbury/Grand Sudbury CMA` | `Greater Sudbury / Grand Sudbury` | 2021S0503580 | slash spacing |
| `Ottawa-Gatineau CMA (Ont. part)` | `Ottawa - Gatineau (Ontario part)` | 2021S050535505 | CMA part, abbreviation |
| `Ottawa-Gatineau CMA (Qué. part)` | `Ottawa - Gatineau (Quebec part)` | 2021S050524505 | CMA part, abbreviation |
| `Belleville - Quinte West CMA` | `Belleville - Quinte West` | 2021S0503522 | exact (2023+) |
| `Belleville CMA` (2019–2022) | `Belleville - Quinte West` | 2021S0503522 | **renamed and redefined**. Flag `boundary_changed = true` |

3. **Validation gates for later ETL:** every CMHC CMA row maps to exactly one DGUID, no DGUID receives two rows in the same year/basis, any unmapped name stops the run, and a mapping is never inferred.
4. Store the stable key as the **StatsCan DGUID** (`cma_dguid`), with both original names kept for lineage.

The full 43-row mapping output was produced during the audit. All 36 (2019–2022) and 42 (2023–2025) CMHC CMA rows mapped, with 0 duplicates.

### 4.3 Focus CMAs

| CMA | S1 DGUID | In C19–C25 every year | Name rule |
|---|---|---|---|
| Windsor | 2021S0503559 | Yes | A |
| London | 2021S0503555 | Yes | A |
| Hamilton | 2021S0503537 | Yes | A |
| Kitchener-Cambridge-Waterloo | 2021S0503541 | Yes | B |
| Toronto | 2021S0503535 | Yes | A |

All five are consistently available in all seven CMHC years and in S1. In the 2022 geography revision, Windsor is the only one of the five whose values changed (rent −23, turnover −0.7). London, Hamilton, Kitchener-Cambridge-Waterloo and Toronto have identical 2022 values on both bases for vacancy, turnover and rent.

---

## 5. 2021 same-year integration feasibility

**Feasible, with three explicit caveats.** The data needed exists for 36 matched geographies with no suppression on the key fields (vacancy, rent, universe; tenant 30%+ and renter count).

| Caveat | Detail | Evidence |
|---|---|---|
| **G1: Geography basis mismatch** | CMHC Oct-2021 uses **2016-census** CMA boundaries. Census 2021 uses **2021** boundaries. For rates and averages the effect is small for most CMAs. For **counts** (universe) it can be material | Windsor apartment universe in 2022: 15,629 (old) vs 17,196 (new), **+10.0%**. Windsor rent 1197 vs 1174 (−1.9%). Only 3 CMA rows changed rate/rent values on revision (Halifax, Ottawa-Gatineau Ont. part, Windsor) |
| **G2: Reference-period mismatch** | Census shelter cost = 2021 and income = 2020 (COVID-affected). CMHC = October 2021 | S1 footnote 61 |
| **G3: Population mismatch** | CMHC = purpose-built apartments (3+ units) for rent and vacancy, row+apartment for universe. Census renters = **all** renter households (incl. condos, houses, secondary suites, subsidized and co-op). CMHC rent = contract rent. Census shelter cost = rent + utilities | S1 fn 50, 65; Table 1.0 / 5.0 titles |

**Decision D1 (project owner, 2026-11-13): Option 1 is the primary design.** The options considered were:
- **Option 1 (CHOSEN):** CMHC Oct-2021 (C21). Same year, but pre-2021 boundaries, and 36 CMAs.
- **Option 2 (not chosen):** CMHC Oct-2022 revised (C23 previous column). Same boundaries as the Census, one year later, and 42 CMAs for rent/vacancy/turnover. The universe is not available for 2022 on the 2021 boundary, so Q2 would still need C21 (2016 boundaries) or C23 (Oct-2023).

**Option 1 is the primary design** (it matches the professor's "same-year" framing). Per D2, every 2021 cross-dataset view carries `cmhc_geography_basis = 'pre_2021_census'`, `census_geography_basis = '2021_census'` and `geography_caveat`. Standard caveat text for rate and average views (Q1, Q3, Q5): *"CMHC October 2021 values use 2016-census CMA boundaries; Census 2021 values use 2021-census CMA boundaries. The effect on rents and rates is small for most CMAs."*

---

## 6. 2019–2025 historical comparison feasibility

**Feasible** for vacancy, 2-bedroom rent and turnover. Fixed-sample rent change is also feasible with suppression gaps.
- Source: Table 1.0 in all seven workbooks. 35 CMA-level geographies are present by exact name in every year (36 with Belleville flagged).
- 2019–2021 use `pre_2021_census` and 2023–2025 use `2021_census`. 2022 carries two rows (bridge year), as in the accepted Windsor history design.
- Continuous line charts must use `is_primary_series = true`. The 2021→2022 change must be flagged `comparable_with_previous_year = false` for CMAs whose 2022 values differ between bases. A uniform rule (flag it for every CMA) is simpler and safer.
- Rental universe: **not feasible for 2019–2025**. A row+apartment universe exists only for 2021–2025 (2020 scope ambiguous). It breaks between 2022 (old boundary) and 2023 (new boundary), with no bridge year.
- Six CMAs (Fredericton, Drummondville, Red Deer, Kamloops, Chilliwack, Nanaimo) have data **only from 2022 (revised) / 2023**. They must not appear in 2019–2025 change calculations.

Audit-time spot values (current-year columns, primary basis):

| CMA | 2019 rent / vac / turn | 2021 rent / vac / turn | 2025 rent / vac / turn |
|---|---|---|---|
| Windsor | 949 / 2.9 / 17.4 | 1,154 / 3.5 / 16.8 | 1,454 / 3.7 / 12.2 |
| London | 1,107 / 1.8 / 19.3 | 1,275 / 1.9 / 19.1 | 1,651 / 4.0 / 15.1 |
| Hamilton | 1,219 / 3.9 / 14.0 | 1,362 / 2.8 / 14.9 | 1,656 / 3.6 / 13.1 |
| Kitchener-Cambridge-Waterloo | 1,231 / 2.1 / 14.2 | 1,356 / 2.0 / 16.9 | 1,832 / 4.1 / 16.1 |
| Toronto | 1,562 / 1.5 / 9.5 | 1,679 / 4.6 / 14.4 | 2,046 / 3.0 / 8.7 |

The Windsor values equal the existing verified `clean.rental_market_windsor_history` primary series (949 / 1,154 / 1,454).

---

## 7. Q1–Q5 feasibility

### Q1. Is Windsor actually more affordable than other CMAs, or simply cheaper? **PARTIALLY SUPPORTED**

- **Fields:**
  - CMHC C21 Table 1.0, average 2BR rent, Oct-21
  - S1 1492 (% tenant 30%+)
  - S1 1494 (median monthly shelter cost, rented)
  - S1 1493 (% tenant core housing need)
  - optional context: S1 243 (median household income, **all tenures**)
- **Year / grain:** 2021, one row per matched CMA (36).
- **Calculation:** no new formula. Compare the rank of the CMHC rent with the rank of the Census renter burden (both published measures), and show the gap: `rent_rank − burden_rank`, or a two-axis scatter.
- **Why partial:** S1 has **no renter household income**. A defensible "rent ÷ renter income" ratio cannot be computed, and dividing rent by all-household median income mixes owner incomes into the denominator. **That ratio is rejected** (§8). The question can be answered only through the official Census burden measure, not through a constructed rent-to-income ratio.
- **Limitations:** G1–G3. The CMHC rent covers purpose-built 2BR apartments, while the burden covers all renter households.
- **Interpretation restrictions:** "lower rent with similar burden" may be said; "Windsor renters are X% better off" may not. Do not rank CMAs on a composite.
- **Visualization:** scatter (x = CMHC 2BR rent, y = % tenant 30%+), Windsor and the four peers highlighted, other CMAs grey. Companion: a small-multiples bar chart of rent rank vs burden rank for the 5 focus CMAs.

### Q2. How large is Windsor's purpose-built rental market relative to its renter population? **PARTIALLY SUPPORTED**

- **Fields:**
  - CMHC C21 **Table 5.0 "Universe"** (row + apartment, privately initiated, 3+ units), Oct-21
  - S1 1416 `Renter` (households)
- **Year / grain:** 2021, one row per matched CMA (36). No universe is suppressed.
- **Formula:** `purpose_built_units_per_1000_renter_households = T5.0_universe / S1_1416 × 1000`, computed in a view with `NULLIF`.
- **Audit-time illustration:** Windsor 16,314 / 45,625 → **357.6**; London 618.4; Hamilton 493.4; Kitchener-Cambridge-Waterloo 510.4; Toronto 415.4.
- **Why partial:**
  1. The universe comes from the **arrears supplementary table**, not Table 1.0. It is row + apartment, not the apartment-only universe used in Story 2.
  2. **The geography mismatch (G1) is material for a count ratio.** Windsor's universe was ~10% larger on the 2021 boundary. Windsor's ratio is therefore biased **downward** against the 2021-boundary renter count.
  3. Units (including vacant ones) are divided by occupied renter households, so this is a ratio, not a share.
- **Interpretation restrictions:** label it "purpose-built rental units per 1,000 renter households (CMHC Oct-2021 universe on 2016-census CMA boundaries ÷ Census 2021 renter households)". Never call it "% of renters in purpose-built housing".
- **Stronger warning (decision D3).** This applies to Q2 only, because counts are sensitive to boundaries:
  - The view carries `boundary_mismatch_severity = 'material'`.
  - It also carries a `count_ratio_warning` column with this text: *"WARNING: numerator (CMHC Oct-2021 rental universe) uses 2016-census CMA boundaries; denominator (Census 2021 renter households) uses 2021-census boundaries. For CMAs whose boundaries grew, the ratio is understated. Windsor's apartment universe was about 10% larger on the 2021 boundary (15,629 vs 17,196 in Oct-2022). Compare CMAs with caution."*
  - The chart shows the warning in its **subtitle** (not only a footnote).
  - Windsor's bar is annotated "likely understated (boundary change)".
  - No ranking statements are made, such as "Windsor has the smallest purpose-built market".
- **Visualization:** sorted horizontal bar chart (36 CMAs, focus CMAs highlighted), plus a basis/caveat annotation.

### Q3. Do tighter rental markets coincide with greater renter affordability pressure? **SUPPORTED** (descriptive association only)

- **Fields:** CMHC C21 Table 1.0 vacancy (total, apartments) Oct-21 + reliability code; S1 1492; optionally S1 1493.
- **Year / grain:** 2021, 36 CMAs. Vacancy is never suppressed in 2021.
- **Calculation:** none required. An optional descriptive Pearson/Spearman correlation could be computed in a view and shown as text only.
- **Limitations:** G1–G3, n = 36. Vacancy measures purpose-built apartments only. 2021 vacancy was pandemic-affected (e.g. Toronto 4.6%).
- **Interpretation restrictions:** association, not causation. No regression line presented as a model.
- **Visualization:** scatter (x = vacancy %, y = % tenant 30%+), with points coloured by reliability letter or province and focus CMAs labelled.

### Q4. How has Windsor's rental market changed 2019–2025 compared with selected Ontario CMAs? **SUPPORTED**

- **Fields:** CMHC Table 1.0, C19–C25: vacancy, 2BR rent, turnover, and fixed-sample 2BR % change, plus reliability and trend flags.
- **Grain:** year × CMA × metric × geography_basis. 2022 has two rows.
- **Calculations:**
  - Within-basis year-over-year change.
  - Rent index to the 2019 base (`rent_Y / rent_2019 × 100`), primary series only. It must **break or annotate at 2022**.
  - The published fixed-sample % change is the statistically preferred rent-growth measure and is shown as published (NULL where `**` or `++`).
- **Limitations:**
  - geography break in 2022
  - fixed-sample change gaps
  - turnover `d` reliability in some years
  - Ontario peers outside the 5 focus CMAs are available, but six newer CMAs start only in 2022/2023
- **Visualization:**
  - multi-line chart of rent and vacancy by year for the 5 CMAs, with a vertical marker at 2022 ("CMA boundaries revised")
  - indexed rent line (2019 = 100)
  - a table of the published fixed-sample % change with suppression shown as "suppressed" or "n.s."

### Q5. Do lower-rent CMAs necessarily show lower renter affordability pressure? **SUPPORTED** (descriptive)

- **Fields:** CMHC C21 Table 1.0 2BR rent; S1 1492. Optional: S1 1494, 1493.
- **Year / grain:** 2021, 36 CMAs.
- **Calculation:** rank comparison, or quadrant assignment against the median of the 36 matched CMAs (low/high rent × low/high burden). The medians are computed in the view from the published values.
- **Audit-time illustration (2021):** Windsor 1,154 / 34.8%; London 1,275 / 38.4%; Hamilton 1,362 / 39.0%; Kitchener-Cambridge-Waterloo 1,356 / 36.9%; Toronto 1,679 / 40.5%.
- **Limitations / restrictions:** same as Q1. The burden reflects incomes (2020) as well as rents, so a low rent with a high burden can reflect low renter incomes, which this dataset cannot isolate.
- **Visualization:** quadrant scatter (median lines), Windsor annotated.

Q1 and Q5 share a dataset. In Superset they can be one scatter with two framings.

---

## 8. Rejected metrics / questions and reasons

| Rejected item | Reason |
|---|---|
| Median renter household income | Not in S1 (no tenure-specific income characteristic) |
| Rent ÷ all-household median income as an "affordability ratio" | The denominator includes owners (median income 82,000 in Windsor vs a renter income that cannot be observed). Mixes populations and income years. Not an official measure |
| Synthetic / composite affordability index | No defensible weighting from official measures. Would hide G1–G3. The official measure (S1 1492, plus 1493 core need) already exists |
| Renter 30%+ **count** across CMAs as published data | Only the % is published in S1. A derived count (1492 × 1490 / 100) would be an estimate with rounding error |
| Rental universe 2019–2025 trend | Absent from Table 1.0. Table 5.0 is missing in 2019 and has an ambiguous scope in 2020. Table 4.1 lacks Windsor. Boundary break with no 2022 bridge |
| Table 4.1 / 4.2 (condo market) | 17 CMAs only, Windsor not included |
| Table 5.0 arrears rates | Windsor values `**` in most years |
| Tables 6.0–6.2 (turnover vs non-turnover rent) | Only from 2022, layout changes in 2024/2025 |
| Whole Ottawa – Gatineau CMA | CMHC publishes parts only, and rates cannot be summed. Use the parts |
| Province "10,000+" and `Canada 10,000+` rows as CMA comparators | Not CMAs. Could be used as an optional labelled national benchmark (`Canada CMAs`) only |
| Census agglomerations (e.g. Charlottetown CA) | Outside the CMA grain |

---

## 9. Recommended staging design (not created)

### 9.1 `data/staging/canada_cma_rental_history.csv`

Source: Table 1.0, C19–C25. Grain: **(cma_dguid, year, metric, geography_basis)**.

| Column | Notes |
|---|---|
| `year` | October survey year |
| `cma_dguid`, `statcan_geo_name`, `cmhc_centre_name` | DGUID from the explicit mapping table; both names kept for lineage |
| `metric` | `vacancy_rate`, `average_rent_2br`, `turnover_rate`, `fixed_sample_rent_change_2br` |
| `bedroom_scope`, `dwelling_scope`, `unit` | `total` / `2_bedroom`; `apartment_3plus_private`; `percent` / `dollars_monthly` |
| `value`, `raw_value`, `value_status` | `published` / `suppressed` (`**`) / `change_not_significant` (`++`). NULL ⇔ not published |
| `reliability_code`, `yoy_trend` | as published |
| `geography_basis` | `pre_2021_census` (2019–2021 and 2022-old) / `2021_census` (2022-revised, 2023–2025) |
| `is_primary_series` | one primary row per (cma, year, metric) |
| `boundary_changed_flag` | true for Belleville (rename and definition change) |
| `source_workbook`, `source_table`, `source_cell`, `source_edition_year` | lineage |

Expected size: (36 × 4 metrics × 2019–2021) + (36 × 4 × 2022 old) + (42 × 4 × 2022 revised and 2023–2025). That is about 432 + 144 + 672 = **~1,248 rows**.

### 9.2 `data/staging/canada_cma_housing_profile.csv`

Source: S1, 43 CMA-level geographies (41 CMAs + 2 Ottawa – Gatineau parts). Grain: **(cma_dguid, characteristic_id)** in long form.
- Columns: `census_year, cma_dguid, alt_geo_code, geo_level, geo_name, tnr_sf, tnr_lf, data_quality_flag, characteristic_id, characteristic_name, characteristic_note, count_total, count_status, rate_total, rate_status, unit`.
- Allowlist of characteristic IDs (exactly): 1, 41, 46, 47, 50, 243, 244, 252, 1414, 1415, 1416, 1417, 1484, 1490, 1491, 1492, 1493, 1494, 1495.
- About 43 × 19 = **817 rows**.

### 9.3 `data/staging/canada_cma_rental_universe.csv` (optional, for Q2)

- Source: Table 5.0, **C21 only** for the 2021 integration. C23–C25 may be added for an annotated 2023–2025 trend on the 2021 boundary.
- Columns: `year, cma_dguid, cmhc_centre_name, universe_units, dwelling_scope='row_and_apartment_3plus_private', geography_basis, source_workbook, source_cell`.
- 2020 should be excluded (scope ambiguity) and 2022 should be excluded (no bridge).

### 9.4 Supporting artefacts

- `etl/cma_geography_map.csv`: the explicit mapping table (§4.2), keyed by the exact CMHC string → DGUID, with a `match_rule` column.
- `etl/raw_canada_history_manifest.json`: SHA-256 baseline for C19–C24. C25 and S1 are already covered by `etl/raw_manifest.json`.
- Header/layout assertions per workbook year: header row 6 (2019) vs 7 (2020+), numeric vs comma-text values, and the glyph variants.

---

## 10. Recommended PostgreSQL design (not created)

Additive only. Existing `clean.*` tables, the 37 `analysis.*` views and `clean.rental_market_canada` are untouched.

### 10.1 Tables

- **`clean.cma_geography`**:
  - Columns: `cma_dguid` PK, `geo_name`, `geo_level`, `alt_geo_code`, `province`, `is_cma_part`, `focus_peer` boolean (Windsor, London, Hamilton, Kitchener-Cambridge-Waterloo, Toronto).
  - It records every CMHC name mapped to the geography.
- **`clean.cma_rental_history`**:
  - Primary key (`cma_dguid`, `year`, `metric`, `geography_basis`).
  - A partial unique index on (`cma_dguid`, `year`, `metric`) WHERE `is_primary_series`.
  - CHECK constraints: NULL ⇔ non-published, rates 0–100, rent > 0, and basis-by-year.
  - Foreign key to `clean.cma_geography`.
- **`clean.cma_housing_profile`**:
  - Primary key (`cma_dguid`, `characteristic_id`).
  - CHECK that `characteristic_id` is in the allowlist.
  - Foreign key to `clean.cma_geography`.
- **`clean.cma_rental_universe`** (optional, Q2): primary key (`cma_dguid`, `year`, `geography_basis`).

### 10.2 Integrated Story 5 views (`sql/analysis/06_story5_cma_comparison.sql`, CREATE OR REPLACE)

| View | Content |
|---|---|
| `story5_cma_profile_2021` | one row per CMA: renter households (1416), renter share (1416 rate), tenant 30%+ (1492), core need (1493), median rented shelter cost (1494), subsidized share (1491) |
| `story5_cma_rent_vs_burden_2021` (Q1, Q5) | CMHC 2021 2BR rent + reliability + S1 1492/1494/1493; ranks; quadrant vs the 36-CMA median; `cmhc_geography_basis`, `census_geography_basis`, `geography_caveat` |
| `story5_cma_vacancy_vs_burden_2021` (Q3) | CMHC 2021 vacancy + reliability + S1 1492; `cmhc_geography_basis`, `census_geography_basis`, `geography_caveat` |
| `story5_cma_rental_supply_ratio_2021` (Q2) | T5.0 universe ÷ S1 1416 × 1000 (`NULLIF`); `cmhc_geography_basis`, `census_geography_basis`, `geography_caveat`, **`boundary_mismatch_severity = 'material'`, `count_ratio_warning`** (D3) |
| `story5_cma_rental_trends` (Q4) | primary series 2019–2025 for all CMAs; within-basis year-over-year change; `comparable_with_previous_year`; `is_focus_peer` |
| `story5_cma_rent_index` (Q4) | 2BR rent indexed to 2019 = 100, primary series, with a break flag at 2022 |
| `story5_cma_period_summary` (Q4) | metric × CMA × era (2019–2021 vs 2022–2025) |

---

## 11. Recommended Dashboard 5 visuals

1. **"Cheaper ≠ more affordable"** (Q1/Q5): scatter of CMHC 2021 2BR rent vs Census 2021 % tenant 30%+, with median quadrant lines and the 5 focus CMAs labelled.
2. **Rental-market tightness vs pressure** (Q3): scatter of 2021 vacancy vs % tenant 30%+.
3. **Purpose-built supply per 1,000 renter households** (Q2): sorted bar, with the boundary caveat in the subtitle.
4. **Windsor vs Ontario peers 2019–2025** (Q4): rent and vacancy line charts (primary series), with a vertical "2022 CMA boundary revision" annotation.
5. **Rent index 2019 = 100** (Q4): line chart of the 5 CMAs.
6. **Fixed-sample rent growth table** (Q4): published values, with "suppressed" and "not significant" shown explicitly (never 0).
7. **CMA profile table:** renter share, burden, core need, median shelter cost and subsidized share for the 5 focus CMAs and the Canada-CMA context.

Per D2, every cross-dataset chart (visuals 1–3 and 7) must name both sources, years and geography bases. Visual 3 (Q2) must show the stronger D3 count warning in its subtitle.

---

## 12. Major limitations

1. **Geography basis:** CMHC 2019–2021 use 2016-census CMAs and the Census uses 2021 CMAs. This is material for counts (Windsor universe ~+10% on the new boundary) and small for rates and rents.
2. **No renter income** in the CMA Census Profile, so no rent-to-renter-income measure.
3. **Population scope differs:** CMHC covers the purpose-built rental market (3+ units). The Census covers all renter households, including condo, house and subsidized renters.
4. **Reference periods differ:** Census income 2020 (COVID benefits), Census shelter cost 2021, CMHC October 2021.
5. **Rental universe** is not available as a consistent 2019–2025 CMA series. For 2021 it is row+apartment from a supplementary table.
6. **Fixed-sample rent change** is often suppressed or not significant.
7. **New CMAs** (6) exist only from 2022-revised/2023. Belleville is renamed and redefined.
8. **Ottawa – Gatineau** is comparable only as two parts.
9. **n = 36** for 2021 cross-dataset analysis: descriptive association only, no causal inference.
10. **CMHC minor revisions** (5 non-geographic cells, restated in the 2021 and 2022 editions) are documented. The value published in each year's own edition is used.

---

## Audit summary

| Item | Result |
|---|---|
| StatsCan CMA count | **41 CMAs** (+2 Ottawa – Gatineau parts = 43 CMA-level geographies) |
| CMHC CMA rows by year | 2019–2022: **36** each; 2023–2025: **42** each |
| CMHC CMA rows common to all 7 years | **35** by exact name (36 with the explicit Belleville rename, flagged) |
| Safely matched CMAs (CMHC ↔ StatsCan) | **36** for 2021 · **42** for 2023–2025 · 0 unmatched, 0 duplicates |
| Consistent CMHC metrics 2019–2025 | vacancy rate (total, apartments) · average 2BR rent · turnover rate · fixed-sample 2BR rent change (with suppression). Rental universe **not** consistent |
| Q1 | PARTIALLY SUPPORTED (no renter income in S1) |
| Q2 | PARTIALLY SUPPORTED (universe from Table 5.0, row+apartment, 2016-boundary numerator) |
| Q3 | SUPPORTED (descriptive) |
| Q4 | SUPPORTED (2022 break flagged) |
| Q5 | SUPPORTED (descriptive) |
| Same-year 2021 cross-dataset analysis | **Feasible**, with geography-basis, reference-period and population caveats. **Chosen as the primary design (D1: Census 2021 + CMHC Oct-2021)** |
| Multi-year CMA comparison 2019–2025 | **Feasible** for 35–36 CMAs (vacancy, rent, turnover, fixed-sample change), with the 2022 bridge year |
