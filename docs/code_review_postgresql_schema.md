# Code Review: PostgreSQL Schema (`sql/warehouse_schema.sql`)

**Scope:** the 8 dimension tables + 4 fact tables in `warehouse` -- keys, data types, naming, and a
real set of test inserts (valid and invalid) run against the live database, not just read from the
DDL.

## Result: solid. Every constraint actually works, confirmed by testing it, not just reading it

Pulled every column's real data type and nullability from `information_schema.columns` (not just
the DDL file) and ran 5 test inserts designed to fail in 5 different ways, plus 2 designed to
succeed. All 7 behaved exactly as the schema claims:

| Test | Expected | Result |
|---|---|---|
| Valid insert into `dim_tenure` / `dim_zone` | succeeds | **Succeeded**, rolled back by hand afterward |
| `fact_shelter_cost` with a `geography_key` that doesn't exist | FK rejection | **Rejected**: `violates foreign key constraint "fact_shelter_cost_geography_key_fkey"` |
| `dim_zone` with `zone_level = 'not_a_real_level'` | CHECK rejection | **Rejected**: `violates check constraint "dim_zone_zone_level_check"` |
| `fact_starts_completions` with `activity = 'NotARealActivity'` | CHECK rejection | **Rejected**: `violates check constraint "fact_starts_completions_activity_check"` |
| `fact_census_profile` missing `geography_key` | NOT NULL rejection | **Rejected**: `null value in column "geography_key" violates not-null constraint` |
| Duplicate `dim_period.period_label = '2021'` | UNIQUE rejection | **Rejected**: `duplicate key value violates unique constraint "dim_period_period_label_key"` |

Confirmed afterward that none of the failed inserts left a stray row behind (`dim_tenure` still 3
rows, `dim_zone` still 13, `fact_starts_completions` still 50) -- the rejections rolled back cleanly,
not just raised an error while partially writing.

## Keys

- Every dimension has a real primary key; `fact_shelter_cost`, `fact_rental_market`, and
  `fact_census_profile` each have a `UNIQUE` constraint on their documented grain (verified
  separately, with 0 violations against the real loaded data, when those constraints were added).
- One deliberate, correct design choice worth calling out rather than flagging as a gap:
  `dim_household_type.household_type_key` is `INT PRIMARY KEY`, not `SERIAL` -- it's StatCan's own
  member ID (1-16), used as a real natural key rather than inventing a surrogate on top of an
  already-stable source ID. Right call, not an oversight.

## Data types

- `geography_key` is `TEXT` (a StatCan DGUID string, e.g. `2021S0503559`), correctly not forced into
  an integer.
- Every `symbol`/`data_quality_flag`/`reliability_letter`/`yoy_trend`/label column is `TEXT`, not
  `VARCHAR(n)` -- idiomatic Postgres (no performance difference, no need to guess a max length).
- **One thing worth knowing, not fixing:** every fact table's `value`/`units` column is
  unconstrained `NUMERIC` (no precision/scale). That's the right call given how mixed the real data
  is -- the same column name holds percentages (`3.6`), dollars (`1,451`), and unit counts
  (`162,138`) depending on `metric_type` -- but it does mean Postgres won't catch an obviously
  out-of-range value (e.g. a `vacancy_rate` of `36000`) at insert time. Not urgent given the ETL
  scripts' own verification steps already catch this class of error upstream, but worth knowing if
  a future loader skips those checks.

## Naming

Checked every column name across all 12 tables via `information_schema.columns` rather than
eyeballing the DDL. Consistent snake_case throughout, consistent `dim_`/`fact_` table prefixes,
consistent `_key` suffix for every key column. Two small inconsistencies found, both informational:

1. **`_label` vs `_name`:** 5 of 7 dimension display-name columns use `_label`
   (`bedroom_type_label`, `dwelling_type_label`, `household_type_label`, `band_label`, `zone_label`),
   but `dim_geography.geography_name` and `dim_tenure.tenure_name` use `_name` instead. Not a bug --
   nothing breaks -- but worth standardizing on one suffix if either table's column is ever
   renamed, rather than adding a third variant.
2. **`value` vs `units`:** `fact_starts_completions.units` is the one fact table that doesn't use
   the generic `value` column name the other three share. Checked this is deliberate, not an
   inconsistency to "fix": `units` genuinely always means a dwelling-unit count in that table, while
   the other three tables' `value` column holds different measures depending on `metric_type`
   (dollars, percentages, counts) -- a more specific name there would be misleading.

## What's solid

- Every FK, CHECK, NOT NULL, and UNIQUE constraint in the schema was exercised with a real failing
  insert during this review, not just read off the DDL -- all 5 behaved correctly.
- Column types match what they hold -- no integer-coded text, no oversized `VARCHAR`, no silent
  truncation risk.
- Naming is consistent enough that a new contributor can predict a column name correctly without
  checking the DDL first, the two `_label`/`_name` exceptions aside.
