# Data Dictionary

The single index for every table and view in the project database. Tables already described column by column in a source-specific dictionary link to it; everything else is described here.

Row counts are from the local warehouse, checked again on 13 November 2026 after `etl/refresh_all.py`.

**Two copies.** The local database `housing_windsor` holds every schema below. The university's database (`whva` on psql.cs.uwindsor.ca, which apss reads) holds only the `warehouse` schema, loaded from `etl/export_for_shared_db.py`; there, `windsor_shelter_cost_long` is in `warehouse` instead of `public` (`docs/deploy_university.md`).

## Index

| Table / view | Schema | Rows | Documented in |
|---|---|---|---|
| `dim_geography` | warehouse | 1 | [Dimensions](#1-dimensions) |
| `dim_period` | warehouse | 7 | [Dimensions](#1-dimensions) |
| `dim_tenure` | warehouse | 3 | [Dimensions](#1-dimensions) |
| `dim_income_band` | warehouse | 21 | [Dimensions](#1-dimensions) |
| `dim_household_type` | warehouse | 16 | [Dimensions](#1-dimensions) |
| `dim_bedroom_type` | warehouse | 5 | [Dimensions](#1-dimensions) |
| `dim_zone` | warehouse | 13 | [Dimensions](#1-dimensions) |
| `dim_dwelling_type` | warehouse | 3 | [Dimensions](#1-dimensions) |
| `fact_shelter_cost` | warehouse | 90,720 | [Section 2.1](#21-fact_shelter_cost) |
| `fact_rental_market` | warehouse | 2,385 | [Section 2.2](#22-fact_rental_market) |
| `fact_windsor_starts_completions` | warehouse | 1,935 | [Section 2.3](#23-fact_windsor_starts_completions) |
| `fact_starts_completions` | warehouse | 50 | `docs/data_dictionary_supply.md` |
| `fact_census_profile` | warehouse | 360 | `docs/data_dictionary_census_comparison.md`, section 1 |
| `fact_rental_market_comparison` | warehouse | 36 | `docs/data_dictionary_census_comparison.md`, section 2 |
| `fact_peer_cma_context` | warehouse | 1,054 | [Section 2.4](#24-fact_peer_cma_context) |
| `load_audit` | raw | one row per load | [Section 3](#3-rawload_audit) |
| `v_*` views (37) | warehouse | — | [Section 4](#4-views) |
| `windsor_shelter_cost_long` | public (warehouse on `whva`) | 90,720 | [Section 5](#5-story-1-source-tables) |
| `windsor_shelter_cost` | public | 30,240 | [Section 5](#5-story-1-source-tables) |
| `raw.*` source tables | raw | ~5 million | Exact copies of `data/raw` files; columns are the source's own (`docs/data_architecture.md`) |
| `staging.*` tables | staging | — | Cleaned copies of the `raw.*` tables with the same names, input to the warehouse loads; rebuilt by `etl/refresh_all.py`, not backed up (`docs/data_architecture.md`) |

## How the tables connect

The fact tables share dimensions, which is what lets two stories be combined in one query:

| Shared key | Links |
|---|---|
| `tenure_key` | `fact_shelter_cost` (Story 1) ↔ `fact_rental_market` (Story 2) |
| `income_band_key` | `fact_shelter_cost` (StatCan income brackets) ↔ `fact_rental_market` (CMHC renter income quintiles, Table 3.1.8) |
| `period_key` | Census year 2021 and CMHC survey months Oct-20 to Oct-25 across all three CMHC/StatCan facts |
| `zone_key` | `fact_rental_market` (Windsor zones) ↔ `fact_rental_market_comparison` (comparison CMAs) |
| City (CMA) | `fact_peer_cma_context.cma_name` (Windsor and the 4 comparison CMAs) ↔ `fact_rental_market_comparison` / `v_story4_rent_comparison` market names (Story 5) |
| Year | `fact_windsor_starts_completions.period_year` ↔ the October survey year in `fact_rental_market` (Story 5) |
| Windsor CMA | `geography_key` 2021S0503559 (StatCan), `dim_zone` "Windsor CMA" (CMHC), `dguid` 2011S0503559 in `fact_windsor_starts_completions` (older vintage of the same area) |

---

## 1. Dimensions

**`dim_geography`** — StatCan geographies.

| Column | Meaning |
|---|---|
| `geography_key` | StatCan DGUID, e.g. `2021S0503559` = Windsor CMA (primary key) |
| `geography_name` | StatCan's name, e.g. "Windsor (CMA), Ont." |
| `geography_level` | `CMA` |

**`dim_period`** — Reference periods.

| Column | Meaning |
|---|---|
| `period_key` | Surrogate key |
| `period_label` | `2021` (Census) or `Oct-20` … `Oct-25` (CMHC survey) |
| `period_type` | `census_year` or `survey_month` |
| `period_year`, `period_month` | Calendar year; month (10) for survey rows, NULL for the Census |

**`dim_tenure`** — `Total`, `Owner`, `Renter`.

**`dim_income_band`** — Income groupings from two different schemes, kept apart by `scheme`.

| Column | Meaning |
|---|---|
| `income_band_key` | Surrogate key |
| `scheme` | `statcan_bracket` (household income in $10,000 brackets, plus totals, median and average) or `cmhc_quintile` (renter income quintiles Q1–Q5, CMHC Table 3.1.8) |
| `member_id` | The source's own ordering (1–14 for StatCan, 0–6 for CMHC) |
| `band_label` | e.g. "Under $10,000", "$100,000 and over", "Q1" |

**`dim_household_type`** — StatCan's 16 household types as a hierarchy.

| Column | Meaning |
|---|---|
| `household_type_key` | StatCan's member ID, 1–16 (1 = all households) |
| `household_type_label` | StatCan's label; two labels repeat ("With children", "Without children") and are told apart by parent |
| `parent_member_id` | Parent in the hierarchy (NULL for the total) |

**`dim_bedroom_type`** — `Studio` (CMHC "Bachelor"), `1 Bedroom`, `2 Bedroom`, `3 Bedroom +`, `Total`.

**`dim_zone`** — CMHC geographies.

| Column | Meaning |
|---|---|
| `zone_key`, `zone_label` | e.g. "Zone 1 - Centre", "Windsor CMA", "London CMA" |
| `zone_level` | `zone` (7 Windsor zones), `city_subtotal` (Windsor City, zones 1–4), `cma_total` (Windsor CMA), `comparator_cma` (London, Kitchener-Cambridge-Waterloo, Hamilton, St. Catharines-Niagara) |

**`dim_dwelling_type`** — CMHC rental structure type: `Apartment`, `Row (Townhouse)`, `Combined`.

---

## 2. Fact tables not covered elsewhere

### 2.1 `fact_shelter_cost`

**Source:** StatCan Table 98-10-0252-01, Shelter-cost-to-income ratio by tenure, 2021 Census (2020 incomes), Windsor CMA. **Grain:** one row per geography × period × income band × household type × tenure × housing suitability × dwelling condition × statistic × shelter-cost ratio. **Used by:** Story 1, Dashboard 1, Story 5.

| Column | Meaning | Values / unit |
|---|---|---|
| `geography_key`, `period_key`, `income_band_key`, `household_type_key`, `tenure_key` | Links to the dimensions | — |
| `housing_suitability` | Whether the dwelling has enough bedrooms (National Occupancy Standard) | `Total - Housing suitability`, `Suitable`, `Not suitable` |
| `dwelling_condition` | Whether the dwelling needs major repairs | `Total - Dwelling condition`, `Only regular maintenance  and minor repairs needed` (StatCan's label has a double space), `Major repairs needed` |
| `statistic` | What `value` is | `Number of private households` (the count used everywhere), and its 95% confidence interval lower / upper bounds |
| `shelter_cost_ratio` | Share of income spent on shelter | `Total`, `Spending less than 30%…`, `Spending 30% or more…`, `30% to less than 100%` (part of 30%+), `Not applicable` (zero/negative income or farm) |
| `value` | The number | households (StatCan rounds counts to multiples of 5) |
| `symbol` | StatCan's symbol, unchanged | e.g. `x`, `...` |
| `data_quality_flag` | `symbol` translated | `suppressed` (x), `not_applicable` (...), `not_available`, `use_with_caution`, `too_unreliable`, `revised`, or NULL |
| `source_coordinate` | StatCan's coordinate for the cell, for tracing back | text |

Notes: In Story 1's scope, the only suppressed cells (40) are the median/average income of "Not applicable" households; no household count is suppressed. "100% or more" is not a row: it is `Spending 30% or more` minus `30% to less than 100%` (see `sql/story1_views.sql`).

### 2.2 `fact_rental_market`

**Source:** CMHC Rental Market Survey data tables, Windsor CMA, October 2020–2025 (`etl/extract_windsor_rms.py`, `etl/extract_windsor_rms_historical.py`). **Grain:** one row per zone × period × bedroom type × dwelling type × tenure × income quintile × metric. **Used by:** Story 2, Dashboard 1, Story 5.

| Column | Meaning | Values / unit |
|---|---|---|
| `zone_key`, `period_key`, `bedroom_type_key`, `dwelling_type_key`, `tenure_key` | Links to the dimensions | — |
| `income_band_key` | CMHC renter income quintile; only set for Table 3.1.8 metrics, otherwise NULL | Q1–Q5, Total |
| `metric_type` | What `value` measures | see below |
| `value` | The number; NULL where CMHC suppressed it (`**`) | see unit below |
| `reliability_letter` | CMHC's reliability grade | `a` excellent, `b` very good, `c` good, `d` use with caution; NULL where not graded |
| `yoy_trend` | CMHC's year-over-year change indicator | `↑` / `↓` significant change, `-` no significant change, `Y` / `N` significant or not (tables that report it that way), `**` suppressed, NULL where the table has none |

| `metric_type` | Unit | Meaning |
|---|---|---|
| `average_rent` | $ per month | Average rent of all surveyed units |
| `vacancy_rate` | % | Share of units vacant and available |
| `universe` | units | Number of purpose-built rental units |
| `turnover_rate` | % | Share of units with a new tenant during the year |
| `rent_vacant_units`, `rent_occupied_units` | $ per month | Average rent of vacant vs occupied units |
| `new_stock_average_rent`, `new_stock_universe`, `new_stock_vacancy_rate` | $ / units / % | The same measures for recently built structures |
| `quintile_universe` | units | Units whose rent is affordable (30% of income) to each renter income quintile (Table 3.1.8) |
| `quintile_vacancy_rate` | % | Vacancy among those units |

### 2.3 `fact_windsor_starts_completions`

**Source:** StatCan Table 34-10-0154-01, CMHC housing starts, under construction and completions, selected CMAs, monthly (`etl/extract_windsor_starts_completions.py`). **Grain:** one row per month × activity × dwelling type, Windsor CMA, January 2016 to September 2026. **Used by:** Story 3, Story 5.

| Column | Meaning | Values / unit |
|---|---|---|
| `dguid` | StatCan's ID for Windsor CMA in this table | `2011S0503559` (2011 boundaries) |
| `ref_month` | Reference month | `YYYY-MM` |
| `period_year`, `period_month` | Year and month split out for grouping | integers |
| `activity` | Construction stage | `Starts`, `Completions`, `Under Construction` |
| `dwelling_type` | Structure type (same labels as `fact_starts_completions`) | `Singles`, `Semis`, `Row`, `Apartment and Other`, `Total` |
| `units` | Number of dwelling units | units |

### 2.4 `fact_peer_cma_context`

**Source:** Windsor's and the four comparison CMAs' rows (London, Hamilton, St. Catharines-Niagara, Kitchener-Cambridge-Waterloo) from six StatCan files (98-10-0252-01, Census Profile 98-401-X2021002, 34-10-0154-01, 98-10-0241-01, and CMHC's October rents and vacancy rates as republished in 34-10-0133-01 and 34-10-0130-01) and CMHC's five city Rental Market Survey workbooks (`etl/extract_peer_cma_context.py`). **Grain:** one row per city × source × indicator × tenure × category × year, long format. **Used by:** Story 4 (ten-year trend) and Story 5.

| Column | Meaning | Values / unit |
|---|---|---|
| `cma_code` | Last 3 digits of the CMA's DGUID, used to match cities across files | `559` Windsor, `555` London, `537` Hamilton, `539` St. Catharines-Niagara, `541` Kitchener-Cambridge-Waterloo |
| `cma_name` | City, spelled as in Story 4 | e.g. `Windsor CMA` |
| `source_table` | StatCan table the row came from | `98-10-0252-01`, `98-401-X2021002`, `34-10-0154-01`, `98-10-0241-01`, `CMHC RMS 3.1.3`, `34-10-0133-01`, `34-10-0130-01` |
| `indicator` | What is counted | 98-10-0252-01: `households`, `households_30pct_plus`, `median_household_income`, `average_household_income`. 98-401-X2021002: `population_2016`, `population_2021`, `private_households`, `persons_in_private_households`, `renter_households`, `median_household_income`, `pct_spending_30pct_plus`, `median_monthly_shelter_cost`. 34-10-0154-01: `starts`, `completions`. 98-10-0241-01: `households`, `households_30pct_plus`, `households_core_need`. CMHC RMS 3.1.3: `rental_universe`. 34-10-0133-01: `average_rent` (dollars a month). 34-10-0130-01: `vacancy_rate` (%) |
| `tenure` | Whose figure | `Total`, `Renter`, or empty |
| `category` | Breakdown | income band label (98-10-0252-01), `Total` or `Apartment and Other` (34-10-0154-01), age of primary household maintainer (98-10-0241-01), unit size `Studio`, `1 Bedroom`, `2 Bedroom`, `3 Bedroom +` (34-10-0133-01), else empty |
| `period_year` | Year | 2021 for Census rows (incomes are for 2020); 2016 to the last full calendar year for construction; 2024 and 2025 (October) for rental units; 2015 to the latest October survey for rents and vacancy |
| `value` | The figure | households, people, dollars, % or units, by indicator |

---

## 3. `raw.load_audit`

One row per file load by the ETL framework (`etl/etl_framework.py`), for checking what was loaded and when.

| Column | Meaning |
|---|---|
| `audit_id` | Surrogate key |
| `dataset_name` | Name of the dataset configuration |
| `file_name` | Source file, relative to the project root |
| `target_table` | `<schema>.<table>` loaded into |
| `rows_loaded` | Rows written; NULL if the load failed first |
| `started_at`, `finished_at` | Timestamps |
| `status` | `success` or `failed` |
| `error_message` | Error text when `status = failed` |

---

## 4. Views

Each story's measures are defined once as a view (`sql/*.sql`, applied by `etl/apply_sql_views.py`) and registered as a Superset dataset.

| View | One row per | Used by |
|---|---|---|
| `v_story1_burden_by_tenure` | tenure: burdened households, total, burden rate % | Story 1, Dashboard 1 |
| `v_story1_burden_by_income_band` | income bracket: burden rate % | Story 1 |
| `v_story1_burden_by_household_type` | household type: burden rate % | Story 1 |
| `v_story1_burden_severity` | tenure: burdened split into 30%–<100% and 100%+ | Story 1 |
| `v_story1_burden_severity_breakdown` | tenure × band (long form of the above) | Story 1 |
| `v_story2_rent_yoy_change` | bedroom type × survey year: average rent and change from the year before ($, %), `period_date` (1 October, for trendline tiles) | Story 2 |
| `v_story2_rent_growth` | bedroom type: rent in the first vs last survey year, growth ($, %) | Story 2 |
| `v_story2_vacancy_trend` | dwelling type × bedroom type × survey year: vacancy rate, `period_date` (1 October) | Story 2 |
| `v_story2_turnover_by_bedroom` | dwelling type × bedroom type × survey year: turnover rate | Story 2 |
| `v_story2_rent_by_zone_bedroom` | zone × bedroom type × survey year: average rent | Story 2 |
| `v_story2_zone_snapshot` | zone: Oct-25 rent, vacancy, units, turnover, share of stock | Story 2 |
| `v_story2_vacancy_by_zone_trend` | zone × period: vacancy rate | Story 2 |
| `v_story2_zone_explanation` | zone: Oct-25 figures, Windsor CMA figures, rank, and plain-language comparison sentences computed from them | Story 2 explanation panel |
| `v_story2_zone_bedroom_explanation` | zone × unit size (Studio, 1, 2, 3+ bedroom, Total): the same panel figures and sentences, compared with Windsor's figure for the same unit size; suppressed cells say "not published" | Story 2 panel, through the virtual dataset `story2_panel_by_unit_size` (keeps the Bedroom Type filter's unit size, else Total) |
| `v_story3_starts_completions_by_dwelling_type` | province × period × activity × dwelling type (CMHC quarterly) | Dashboard 1 |
| `v_story3_supply_per_1000_households` | province × period: starts total; the per-1,000 rate is deliberately NULL because the source has no Windsor figure | Story 3 (earlier version) |
| `v_story3_windsor_supply_annual` | year × activity × dwelling type: Windsor units (flags partial years) | Story 3 |
| `v_story3_period_comparison` | period (2016-2020, 2021-2025) x activity (starts, completions) x dwelling type: average units a year, total units, share of the period's total; only complete five-year periods | Story 3 "Before vs From 2020" tab; home/story-page charts |
| `v_story3_windsor_supply_per_1000_households` | year: Windsor starts and completions per 1,000 households (2021 household count) | Story 3 |
| `v_story4_vacancy_comparison` | market × period: vacancy rate | Story 4 |
| `v_story4_rent_comparison` | market × period: average 2-bedroom rent | Story 4; Story 5 through `v_story5_peer_affordability` |
| `v_story4_rent_history` | city × year (2015 onward): October 2-bedroom rent and vacancy rate (apartments and row houses), yearly rent change, rent as % of 2015, `period_date` (1 October of the year, for trendline tiles) | Story 4 ten-year section |
| `v_story4_period_comparison` | city: rent in 2015, 2020, 2025; average yearly rent rise 2015-2020 and 2020-2025; average vacancy per period; Windsor's rent as % of the other four cities' average | Story 4 ten-year section |
| `v_story4_affordability_gap` | market: rent growth %; renter income growth and the gap index stay NULL until an income-growth source exists (`docs/affordability_gap_index.md`) | Story 4 |
| `v_dashboard1_rental_yoy` | metric × dwelling type: Windsor previous vs latest survey and the change | Dashboard 1 |
| `v_dashboard1_rental_trend` | metric (average_rent, vacancy_rate, universe, turnover_rate) × October: Windsor CMA, apartments and row houses, all unit sizes, with `period_date` | Overview trendline tiles |
| `v_dashboard1_cma_benchmark` | metric: Windsor vs median of the 5 CMAs, with rank | Dashboard 1 |
| `v_story5_income_bands` | income band: lower and upper bound, for counting households below an income | Story 5 views |
| `v_story5_rent_affordability` | unit size: Windsor Oct-25 rent, income needed, median renter income, renters who cannot afford it | Story 5 (Story 1 + 2) |
| `v_story5_windsor_vs_peers` | two rows (Windsor; average of the 4 comparison cities): eight measures from `v_story5_city_profile`, each as Windsor's % of the four cities' average (the average row is 100) | Story 5 overview radar |
| `v_story5_peer_affordability` | city: 2-bedroom rent, median renter income, rent as % of income, % who cannot afford, % spending 30%+, short city name (`city_short`) | Story 5 (Story 1 + 4) |
| `v_story5_supply_vs_rental_market` | year 2020–2025: Windsor starts and completions, October vacancy, rent and rent change | Story 5 (Story 3 + 2) |
| `v_story5_peer_construction` | city × year: starts, completions, starts per 1,000 households, apartment share | Story 5 (Story 3 + 4) |
| `v_story5_supply_vs_demand` | city: 2016–2021 population growth, homes needed, homes completed 2016–2020, built per home needed | Story 5 (Story 3 + Census population) |
| `v_story5_renter_burden_by_age` | city × age group: renter households, share spending 30%+ on shelter, the all-renter share and the gap | Story 5 (Census renters by age + Story 1 + Story 4) |
| `v_story5_rental_stock` | city: purpose-built rental units (Oct-24, Oct-25), renter households, units per 100 renters | Story 5 (CMHC rental units + Census renters) |
| `v_story5_city_profile` | city: rent, vacancy, units per 100 renters, renter income, rent share, burden (all and 15–24), starts per 1,000, share of needed homes built | Story 5 (all stories) |

## 5. Story 1 source tables

StatCan Table 98-10-0252-01 (shelter-cost-to-income ratio by tenure, Windsor CMA, 2021 Census), extracted by `etl/extract_windsor_shelter_cost.py` (wide) and reshaped by `etl/reshape_shelter_cost_long.py` (long). `fact_shelter_cost` is built from the same file; these two keep the source's own labels and are what Story 1's tenure chart (`setup_superset_dashboard.py`) reads.

**`windsor_shelter_cost`** (wide, 30,240 rows): one row per income group × household type × housing suitability × dwelling condition × statistic × shelter-cost ratio.

| Column | Type | Meaning |
|---|---|---|
| `ref_date` | text | Census year (2021) |
| `geo`, `dguid` | text | Windsor CMA and its StatCan geography id |
| `income_group`, `household_type`, `housing_suitability`, `dwelling_condition` | text | StatCan dimension labels as published |
| `statistic` | text | Number of private households, or the lower / upper bound of its confidence interval |
| `shelter_cost_ratio` | text | Total, less than 30%, 30% or more, 30% to less than 100%, or Not applicable |
| `coordinate` | text | StatCan's cell coordinate |
| `tenure_total`, `tenure_owner`, `tenure_renter` | double | Value for all, owner and renter households; NULL where suppressed |
| `tenure_*_symbol` | text | StatCan symbol for the value ("x" = suppressed) |

**`windsor_shelter_cost_long`** (long, 90,720 rows): the same data with one row per tenure. Same columns as above, except that `tenure` (Total, Owner, Renter) and `value` / `symbol` replace the three tenure column pairs, `source_coordinate` replaces `coordinate`, and it adds `household_type_member_id` (StatCan member id) and `data_quality_flag`: `suppressed` (symbol "x", value NULL; 906 rows), `not_applicable` (symbol "..."; 2,940 rows), otherwise empty.
