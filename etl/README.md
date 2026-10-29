# ETL

How to run the pipeline end to end, how to add a new dataset, and how to
read the load-audit table. For what the resulting schemas look like and
how they relate, see [docs/conceptual_er_model.md](../docs/conceptual_er_model.md)
and [docs/data_architecture.md](../docs/data_architecture.md).

All commands below run from the project root with the virtual environment
active (`.venv\Scripts\python.exe ...` on Windows, `.venv/bin/python ...`
on macOS/Linux), and assume `.env` is filled in per `.env.example` and the
Postgres container is up (see the top-level [README.md](../README.md)).

## How to run

The pipeline has three stages: extract raw sources into staging CSVs, load
those into Postgres, then build the SQL views on top. Each stage is
idempotent (safe to re-run) and most scripts print what they did.

**One-command refresh for stages 2-3** (load + views + Superset datasets,
from already-extracted staging CSVs): `etl/refresh_all.py` runs
`create_warehouse_schema.py`, `load_warehouse_facts.py`,
`run_framework_loads.py`, `apply_sql_views.py`, and
`register_superset_datasets.py` in order, stopping at the first failing
step. Superset registration is skipped automatically if Superset isn't
reachable (or always, with `--skip-superset`) -- Postgres-only refreshes
are a legitimate use case. Verified safe to run twice in a row: identical
row counts both times, no errors, no duplication.
```
.venv\Scripts\python.exe etl\refresh_all.py
```
Deliberately doesn't include the extract stage below -- those scripts hit
real external sources (StatCan, CMHC) over the network, so re-running them
on every refresh would be slow and adds unnecessary repeat load on those
services for data that doesn't change between runs. Run the extract
scripts first if the staging CSVs don't exist yet.

### 1. Extract (raw file -> staging CSV)

Each source has its own extract script, writing to `data/staging/`:

| Script | Produces |
|---|---|
| `extract_windsor_shelter_cost.py` + `reshape_shelter_cost_long.py` | `windsor_shelter_cost(_long).csv` |
| `extract_windsor_census_profile.py` + `reshape_census_profile_long.py` | `windsor_census_profile_long.csv` |
| `extract_windsor_rms.py` | `windsor_rental_market.csv` (Windsor, Oct-24/Oct-25) |
| `extract_windsor_rms_historical.py` | `windsor_rental_market_historical.csv` (Windsor, Oct-20 to Oct-23 -- see its own docstring on why this isn't "10 years") |
| `extract_rms_canada_comparison.py` | `rms_canada_comparison.csv` (comparator CMAs -- see [docs/comparator_cmas_justification.md](../docs/comparator_cmas_justification.md)) |
| `extract_cmhc_starts_completions.py` | `ontario_canada_starts_completions.csv` |

Optionally, `load_raw_files_to_postgres.py` loads every file under
`data/raw/` as-is into Postgres's `raw` schema first, for reference --
this is separate from, and not required by, the staging/warehouse path
below.

### 2. Load (staging CSV -> Postgres)

Two different loaders, for two different kinds of destination:

- **`create_warehouse_schema.py`** -- creates and seeds `sql/warehouse_schema.sql`'s
  dimensional model (run once, or after a schema change).
- **`load_warehouse_facts.py`** -- bulk-loads all 4 fact tables
  (`fact_shelter_cost`, `fact_census_profile`, `fact_rental_market`,
  `fact_starts_completions`) from the staging CSVs above, resolving every
  dimension foreign key by joining on real values (geography DGUID,
  period label, zone label, etc.), not assumed or guessed. Safe to
  re-run: each fact table is truncated first. It also re-runs
  `validate_rental_market_data.py` at the end and writes its section of
  `docs/data_quality_report.md` -- see "Read the load-audit table" below
  for how this differs from `raw.load_audit`.
- **`run_framework_loads.py`** -- loads every dataset configured under
  `etl/configs/*.yaml` through the shared schema-validated loader
  (`etl_framework.py`), and is what actually writes to `raw.load_audit`.
  See "Add a dataset" below for when to use this path instead of (or
  alongside) `load_warehouse_facts.py`.

Run order from a clean database:
```
.venv\Scripts\python.exe etl\create_warehouse_schema.py
.venv\Scripts\python.exe etl\load_warehouse_facts.py
.venv\Scripts\python.exe etl\run_framework_loads.py
```
(`etl\refresh_all.py` runs these 3 plus the views/Superset steps below in
one command -- see "How to run" above.)

`validate_supply_data.py` is a separate, manual data-quality check (not
wired into either loader above) -- run it directly after a supply-data
reload:
```
.venv\Scripts\python.exe etl\validate_supply_data.py
```

### 3. Views and Superset

Apply the SQL view files (`sql/story1_views.sql`, `story2_views.sql`,
`story3_views.sql`, `story4_views.sql`, `dashboard1_views.sql`) against the
warehouse schema:
```
.venv\Scripts\python.exe etl\apply_sql_views.py
```
Then, to register the views as Superset datasets:
```
.venv\Scripts\python.exe etl\register_superset_datasets.py
```

`dashboard1_views.sql` backs "01 - Windsor Housing Executive Overview", a
combined dashboard across Stories 1-4 (not a story of its own). Build it
with:
```
.venv\Scripts\python.exe etl\build_dashboard1_overview.py
```

To standardize percentage formatting on the handful of charts with no
idempotent builder script of their own (Renter/Owner Burden Rate, Burden
Rate by Income Band/Household Type -- shared by Dashboards 1 and 2):
```
.venv\Scripts\python.exe etl\polish_percentage_kpi_formatting.py
```

Build Story 4's dashboard ("How does Windsor compare to similar
markets?" -- Windsor vs. the 4 real comparator CMAs on vacancy, rent,
and the real rent-growth side of the affordability-gap index):
```
.venv\Scripts\python.exe etl\build_story4_dashboard.py
```

Apply `docs/filter_standards.md`'s naming rule to Story 1's dashboard
(renames its "Household type" native filter to "Household Type"):
```
.venv\Scripts\python.exe etl\apply_filter_standards_story1.py
```

## Add a dataset

There are two real paths in this project, depending on what the new data
needs to do:

**A -- Join into the star schema** (the new data needs to combine with
existing dimensions, e.g. another Census or CMHC table keyed by
geography/period/zone): write an `extract_*.py` script producing a
long-format staging CSV, then add a `load_*_facts()` function to
`load_warehouse_facts.py` that resolves each dimension key the same way
the existing loaders do (join on the dimension's real label/code, don't
assume row order) and appends to the right fact table. This is the path
`fact_rental_market`'s three sources (Windsor, historical, comparator
CMAs) all use.

**B -- Flat, already-clean, schema-validated load** (the new data doesn't
need to join into the star schema, just needs a reliable, audited load of
a CSV with a known column set): write an `extract_*.py`/`reshape_*.py`
script producing a flat staging CSV, then add a config file under
`etl/configs/`:
```yaml
name: my_new_dataset             # used as raw.load_audit.dataset_name
csv_path: data/staging/my_new_dataset.csv
schema: public
table: my_new_dataset
expected_columns: [col_a, col_b, col_c]
column_rename: {}                # optional, applied before validation
numeric_columns: [col_c]         # optional, coerced via pd.to_numeric
```
`etl_framework.py`'s `load_dataset()` then validates the CSV's columns
exactly match `expected_columns` (extra or missing columns both stop the
load) before loading, and records the attempt in `raw.load_audit` either
way. Run it standalone, or let `run_framework_loads.py` pick it up
automatically along with every other `etl/configs/*.yaml` file.

This project's real configs (`etl/configs/*.yaml`) are themselves the
clearest worked examples -- read one alongside `etl_framework.py`'s own
module docstring before writing a new one.

## Read the load-audit table

`raw.load_audit` (defined in `sql/load_audit_schema.sql`) has one row per
load *attempt* -- success or failed -- for every dataset loaded through
`etl_framework.py` (path B above). It does **not** cover
`load_warehouse_facts.py`'s fact-table loads (path A) or
`load_raw_files_to_postgres.py`'s raw landing -- those aren't
config-driven, so there's nothing to audit in the same structured way.

Columns: `audit_id`, `dataset_name`, `file_name`, `target_table`,
`rows_loaded` (NULL if the load failed before counting rows),
`started_at`, `finished_at`, `status` (`'success'` | `'failed'`),
`error_message` (NULL on success).

Real example, queried from the live table:
```sql
SELECT dataset_name, target_table, rows_loaded, status, finished_at
FROM raw.load_audit
ORDER BY audit_id DESC
LIMIT 5;
```
```
 windsor_shelter_cost_long        | public.windsor_shelter_cost_long        | 90720 | success | 2026-10-22 16:33:29
 windsor_shelter_cost              | public.windsor_shelter_cost              | 30240 | success | 2026-10-22 16:33:11
 windsor_census_profile_long       | public.windsor_census_profile_long       |   360 | success | 2026-10-22 16:33:04
 ontario_canada_starts_completions | public.ontario_canada_starts_completions |    50 | success | 2026-10-22 16:33:03
 windsor_shelter_cost_long        | public.windsor_shelter_cost_long        | 90720 | success | 2026-10-21 14:49:24
```

To check whether the most recent attempt at a specific dataset succeeded:
```sql
SELECT status, error_message, finished_at
FROM raw.load_audit
WHERE dataset_name = 'windsor_census_profile_long'
ORDER BY audit_id DESC
LIMIT 1;
```

A `'failed'` row always has a non-NULL `error_message` (schema drift, a
missing CSV, or whatever exception the database raised) -- every failure
path in `etl_framework.py`'s `load_dataset()` writes the audit row before
re-raising, so a failed load is never silent.
