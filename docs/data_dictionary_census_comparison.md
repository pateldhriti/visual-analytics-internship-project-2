# Data Dictionary — Census Profile & RMS Canada Comparison

Every column kept through to the warehouse for two sources: `warehouse.fact_census_profile`
(Windsor's 2021 Census characteristics) and `warehouse.fact_rental_market_comparison`
(Windsor + 4 comparator CMAs' rent/vacancy indicators). `fact_id`
surrogate keys are omitted from both tables below — every other column is covered.

## 1. Census Profile — `warehouse.fact_census_profile`

**Source:** Statistics Canada table **98-401-X2021002**, "Census Profile, 2021 — Census
Metropolitan Areas and Census Agglomerations" (`data/raw/statcan/98-401-X2021002_English_CSV_data.csv`).
**Reference year: 2021** (2021 Census; table released 2022-12-15) for every row — this source has
only one period.

**Pipeline stage:** raw CSV → `etl/extract_windsor_census_profile.py` (filters to Windsor CMA, 60
curated characteristics of 2,631 published) → `data/staging/windsor_census_profile.csv` (wide: one
row per characteristic, 6 value/symbol column pairs) → `etl/reshape_census_profile_long.py`
(melts to long: one row per characteristic × measure_type × sex) →
`data/staging/windsor_census_profile_long.csv` → `etl/load_warehouse_facts.py` →
`warehouse.fact_census_profile`.

| Column | Meaning | Unit | Source table / column |
|---|---|---|---|
| `geography_key` | Which geography this row describes. Resolved from `DGUID` — always `2021S0503559` (Windsor CMA's standard 2021 Census geographic identifier) in this table, since the extraction filters to Windsor only. | code (DGUID string) | 98-401-X2021002, `DGUID` column. |
| `period_key` | Which census cycle this row is from. Resolved from `CENSUS_YEAR`, joined to `dim_period`'s `period_label = '2021'` row (`period_type = 'census_year'`). | categorical (year label) | 98-401-X2021002, `CENSUS_YEAR` column. |
| `characteristic_id` | StatCan's own numeric ID for the census characteristic this row measures (e.g. `1` = "Population, 2021"), one of the 60 curated in `etl/extract_windsor_census_profile.py`'s `CHARACTERISTIC_IDS` out of 2,631 published. | integer code (StatCan's own numbering; not sequential or meaningful on its own) | 98-401-X2021002, `CHARACTERISTIC_ID` column. |
| `characteristic_name` | Human-readable label for the characteristic, StatCan's own wording (e.g. `"Average household size"`, `"Median total income of household in 2020 ($)"`). | text | 98-401-X2021002, `CHARACTERISTIC_NAME` column. |
| `measure_type` | Which of the two published value families this row reports: `count` (a raw tally) or `rate` (StatCan's own derived percentage/ratio for that characteristic). | categorical: `count` \| `rate` | Derived by `etl/reshape_census_profile_long.py` from which melted column pair this row came from (`C1_COUNT_TOTAL`/`C2_COUNT_MEN+`/`C3_COUNT_WOMEN+` → `count`; `C10_RATE_TOTAL`/`C11_RATE_MEN+`/`C12_RATE_WOMEN+` → `rate`) — not itself a raw column. |
| `sex` | Which sex breakdown this row reports. `men`/`women` is StatCan's own "Men+"/"Women+" column naming (totals include diverse-gender respondents counted under the corresponding sex-at-birth category, per StatCan's 2021 methodology). | categorical: `total` \| `men` \| `women` | Derived from which wide column pair was melted (`C1`/`C10` → `total`, `C2`/`C11` → `men`, `C3`/`C12` → `women`). |
| `value` | The published number for this (characteristic × measure_type × sex) combination. | varies by characteristic — dollars, years, persons, km², percent, ratio, etc.; see `characteristic_name`. `count` rows are whole numbers (or StatCan's randomly-rounded approximation); `rate` rows are percentages/ratios. `NULL` with `symbol = '...'` means *not applicable* for that breakdown (e.g. most household-level characteristics have no sex breakdown), never zero. | 98-401-X2021002, whichever of `C1_COUNT_TOTAL` / `C2_COUNT_MEN+` / `C3_COUNT_WOMEN+` / `C10_RATE_TOTAL` / `C11_RATE_MEN+` / `C12_RATE_WOMEN+` matches this row's `measure_type`/`sex`. |
| `symbol` | StatCan's data-quality/availability symbol for this specific value, if any (e.g. `...` = not applicable, `x` = suppressed for confidentiality, `F` = too unreliable to publish, `E` = use with caution). | categorical code — full legend in `98-401-X2021002_English_meta.txt`'s Symbol section | 98-401-X2021002, whichever of `SYMBOL` / `SYMBOL.1` / `SYMBOL.2` / `SYMBOL.3` / `SYMBOL.4` / `SYMBOL.5` matches. |

### What's deliberately not kept

Present in the staging CSVs but not carried into `fact_census_profile`:

- **`ALT_GEO_CODE`, `GEO_LEVEL`, `GEO_NAME`** — redundant with `DGUID`/`geography_key` once every
  row is confirmed Windsor CMA; nothing they add isn't already on `dim_geography`.
- **`TNR_SF`, `TNR_LF`** — StatCan's short-form/long-form total non-response rate for Windsor as a
  whole (constant across all 60 characteristics: `2.4`, `3.1`). A geography-level survey-quality
  metric, not a per-characteristic one — doesn't belong on a fact row grained at
  (characteristic × measure_type × sex).
- **`DATA_QUALITY_FLAG`** — the 5-digit flag StatCan derives from `TNR_SF`/`TNR_LF` (constant
  `00000` for Windsor, i.e. every digit at its cleanest default). Same reasoning as above.
- **`CHARACTERISTIC_NOTE`** — empty for every one of the 60 curated characteristics in this
  extraction; nothing to keep.

## 2. RMS Canada Comparison — `warehouse.fact_rental_market_comparison`

**Source:** CMHC's national Rental Market Survey workbook, **Table 1.0** — "Rental Market
Indicators - Privately Initiated Apartment Structures of Three Units and Over - Provinces and
Major Centres" (`data/raw/cmhc/rmr-canada-2025-en.xlsx`, the 2025 edition). **Reference years:
2024 and 2025** — every row is tagged `Oct-24` or `Oct-25` (the survey's two most recent October
collection rounds); there is no other period in this table.

**Pipeline stage:** raw workbook → `etl/extract_rms_canada_comparison.py` (Windsor + 4 comparator
CMAs — see `docs/comparator_cmas_justification.md`) → `data/staging/rms_canada_comparison.csv` →
`etl/load_warehouse_facts.py`'s `load_rms_canada_comparison_facts()` → `warehouse.fact_rental_market_comparison`,
a **separate table** from the one the Windsor-specific RMS extraction
(`etl/extract_windsor_rms.py`) loads into (`fact_rental_market`) — this source is a different
workbook (CMHC Canada RMS 2025 vs. CMHC Windsor RMS 2025), so it gets its own fact table per this
schema's one-table-per-source rule; see `sql/warehouse_schema.sql`'s comment on
`fact_rental_market_comparison`.

| Column | Meaning | Unit | Source table / column |
|---|---|---|---|
| `zone_key` | Which CMA this row's metric is for. Resolved from the staging `centre` column (`"Windsor CMA"`, `"London CMA"`, `"Kitchener-Cambridge-Waterloo CMA"`, `"Hamilton CMA"`, `"St. Catharines-Niagara CMA"`) against `dim_zone` — Windsor resolves to the existing `zone_level = 'cma_total'` row, the 4 others to new `zone_level = 'comparator_cma'` rows. | categorical | Table 1.0, column A ("Centre"). |
| `period_key` | Which survey round this row covers. Resolved from staging `period_label` (`Oct-24` / `Oct-25`) against `dim_period` (`period_type = 'survey_month'`). | categorical (survey month label) | Table 1.0's "October 2024" / "October 2025" column groups. |
| `bedroom_type_key` | Which bedroom-size breakdown this metric is reported at. Table 1.0 reports vacancy and turnover as one overall rate (no bedroom breakdown) and average rent / its % change for 2-bedroom units only — a narrower bedroom scope than the Windsor-specific 3.1.x tables. | categorical: `Total` (vacancy_rate, turnover_rate) \| `2 Bedroom` (average_rent, pct_change_rent) | Table 1.0's column grouping (no explicit "bedroom type" column in this table — scope is implicit per metric). |
| `dwelling_type_key` | Structural type of rental units covered. Constant `Apartment` for every row from this source — Table 1.0 covers privately initiated apartment structures of 3+ units only, not the Row+Apartment Combined scope the Windsor-specific 3.1.x tables use (so Windsor's own vacancy rate here legitimately differs from the Windsor workbook's Combined figure — a scope difference, not a contradiction). | categorical, constant `Apartment` for this source | Table 1.0's title/scope, "Privately Initiated Apartment Structures of Three Units and Over". |
| `tenure_key` | Confirms this row describes rental-tenure stock. Hardcoded to `Renter` for every row — CMHC's Rental Market Survey is rental-market by definition, nothing in Table 1.0 itself encodes tenure. | categorical, constant `Renter` | Not a raw column — assigned by `load_rms_canada_comparison_facts()`. |
| `metric_type` | Which rental-market indicator this row measures. | categorical: `vacancy_rate` \| `turnover_rate` \| `average_rent` \| `pct_change_rent` | Table 1.0's 4 metric column-groups (columns 2, 7, 12, 16 respectively). |
| `value` | The published number for this (zone × period × metric) combination. | `percent` for `vacancy_rate` / `turnover_rate` / `pct_change_rent`; `CAD per month` for `average_rent` | Table 1.0's numeric cell under each metric's column group; `**` (suppressed) read as `NULL`. |
| `reliability_letter` | CMHC's own data-quality letter for this specific cell. | categorical letter code (CMHC RMS reliability rating) | Table 1.0, the column immediately right of each value column. |
| `yoy_trend` | CMHC's own year-over-year trend indicator for the latest period. Populated only for `vacancy_rate` and `turnover_rate` rows where `period_label = 'Oct-25'` — Table 1.0 only publishes a trend column for the latest period on those two metrics (always `NULL` for `average_rent`, `pct_change_rent`, and every `Oct-24` row). | text/symbol as published | Table 1.0, column 6 (vacancy) / column 11 (turnover). |

### Windsor rows: partial de-duplication against the Windsor-specific extraction

Loaded Windsor rows from this source are **not** the full 8 Windsor rows the extraction produces:

- **Excluded** — `vacancy_rate` and `average_rent` for Windsor: genuine duplicates of
  `etl/extract_windsor_rms.py`'s Table 1.1.1/1.1.2 at the same Apartment scope. Kept once (from the
  Windsor-specific extraction, already documented separately), to avoid double-counting the same
  real metric.
- **Kept** — `turnover_rate` and `pct_change_rent` for Windsor: genuinely unique to this source.
  The Windsor-specific extraction never pulled an apartment-only turnover table (no Table 1.1.6 in
  its scope) or any rent-percentage-change table at all (1.1.5/2.1.5/3.1.5 were explicitly out of
  scope — see `docs/cmhc_rms_sheet_catalogue.md`). An earlier version of the loader excluded *all*
  Windsor rows from this source and silently dropped these two real metrics — caught because
  `warehouse.v_story4_affordability_gap` (`sql/story4_views.sql`) came back with no Windsor row at
  all.

The 4 comparator CMAs' rows are loaded in full (all 4 metrics × both periods, no de-duplication
needed — they have no other source in this warehouse).
