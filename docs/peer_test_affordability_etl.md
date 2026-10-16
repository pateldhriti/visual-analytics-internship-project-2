# Peer Test: Affordability ETL (Dhritiben's shelter-cost pipeline)

**Scope:** `etl/extract_windsor_shelter_cost.py`, `etl/load_windsor_shelter_cost_to_postgres.py`, `etl/reshape_shelter_cost_long.py`, `etl/load_windsor_shelter_cost_long_to_postgres.py` -- the Story 1 affordability pipeline (StatCan table 98-10-0252-01, shelter-cost-to-income ratio by tenure), author-verified via `git log` as entirely authored by `pateldhriti`.

**Method:** genuinely clean test, not a re-run of existing output. Dropped both tables this pipeline owns (`public.windsor_shelter_cost`, `public.windsor_shelter_cost_long`) and deleted both intermediate staging CSVs before running, forcing every step to regenerate from the raw source file (`data/raw/shelter_cost/98100252.csv`) with nothing left over from a prior run. Ran all 4 scripts in dependency order, then ran the whole thing a second time to check idempotency.

## Result: the pipeline works

- All 4 scripts ran successfully from a clean database, in order, with no errors.
- Row counts match expectations at every stage: 5,019,840 source rows -> 30,240 Windsor rows (extract) -> 30,240 rows loaded (wide table) -> 90,720 rows (reshape to long, with the reshape script's own built-in preservation checks all passing: cell count, non-null value count, symbol count all preserved, 0 round-trip mismatches on a 20-row spot check) -> 90,720 rows loaded (long table).
- Re-ran the full pipeline a second time: identical row counts both times, no duplication, no errors -- genuinely safe to re-run, not just in the docstring.
- Spot-checked a known value (Owner households spending 30%+ on shelter costs = 13,005) directly against the freshly reloaded table -- correct, matches every prior independent calculation of this number across this project.

**Total runtime:** about 32 seconds end-to-end on this machine (15.9s extract, 4.5s wide load, 3.2s reshape, 8.4s long load) -- not a concern.

## Problems found

### 1. The wide table's value columns are stored as TEXT, not numeric

`windsor_shelter_cost`'s `tenure_total`, `tenure_owner`, and `tenure_renter` columns -- the actual household-count values -- are stored as Postgres `text`, confirmed via `information_schema.columns`. Any SQL query that sums, averages, or numerically compares these columns needs an explicit `CAST(... AS NUMERIC)` first; without it, Postgres will either error (comparing text to a number) or silently do string comparison instead of numeric comparison, depending on the query.

This is inconsistent with the sibling long-format loader: `load_windsor_shelter_cost_long_to_postgres.py` explicitly converts its equivalent `value` column with `pd.to_numeric(...)` before loading (confirmed: that column is `double precision` in Postgres), but `load_windsor_shelter_cost_to_postgres.py` has no equivalent conversion for its 3 value columns.

**Suggested fix:** add the same `pd.to_numeric(..., errors="coerce")` conversion for `tenure_total`, `tenure_owner`, `tenure_renter` before the `to_sql` call in `load_windsor_shelter_cost_to_postgres.py`, matching what the long-table loader already does.

### 2. `windsor_shelter_cost_long`'s column names require double-quoting in SQL

The long table keeps StatCan's original column names un-renamed for 4 columns: `REF_DATE`, `GEO`, `DGUID`, `Coordinate` (mixed case, as published). Postgres treats any identifier with uppercase letters as case-sensitive once it's quoted at creation time (which `pandas.to_sql` does automatically), so these columns can only be queried as `"REF_DATE"`, `"GEO"`, `"DGUID"`, `"Coordinate"` -- not the unquoted lowercase form (`ref_date`) that matches this project's naming convention everywhere else (the wide table's own renamed columns, the warehouse schema, every SQL view in `sql/`).

**Verified, not assumed:** `SELECT "REF_DATE" FROM public.windsor_shelter_cost_long` works; `SELECT ref_date FROM public.windsor_shelter_cost_long` fails with `column "ref_date" does not exist`. This is a real trap for anyone writing a quick query by habit, matching the convention used everywhere else in this project -- they'll hit a confusing error on a seemingly-correct query.

**Suggested fix:** `reshape_shelter_cost_long.py` already renames 6 of its 10 non-value columns to clean snake_case (`income_group`, `household_type`, `housing_suitability`, etc.) -- extend that same rename to the remaining 4 (`REF_DATE` -> `ref_date`, `GEO` -> `geo`, `DGUID` -> `dguid`, `Coordinate` -> `coordinate`), matching `load_windsor_shelter_cost_to_postgres.py`'s `COLUMN_RENAME` map, which already handles this correctly for the wide table.

## What's NOT a problem (checked and ruled out)

- Encoding: the extract script reads the 1.3GB raw CSV with `utf-8-sig`; both load scripts read the staging CSVs (written by the extract/reshape scripts as plain `utf-8`) with `utf-8`. Consistent, no mismatch.
- Missing-source handling: `extract_windsor_shelter_cost.py` and `load_windsor_shelter_cost_long_to_postgres.py` both raise a clear `FileNotFoundError` naming the exact missing file if run out of order, rather than failing with a cryptic error.
- Data correctness: the actual numbers are right (spot-checked independently above), and the reshape step's own built-in verification (cell count, non-null count, symbol count, round-trip spot check) all pass.
