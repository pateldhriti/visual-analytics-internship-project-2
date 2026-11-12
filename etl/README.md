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

**On a fresh machine** (a clean clone or the university server), first put
the raw source files in `data/raw/` (not in git): every file is downloaded
from StatCan or CMHC except two that must be saved by hand (the 2021 Census
Profile comprehensive file and CMHC's quarterly starts workbook); the script
lists them with the page to get them from.
```
.venv\Scripts\python.exe etletch_raw_data.py
```
Then run the stages below. For the university's Superset, set
`SUPERSET_URL=https://apss.cs.uwindsor.ca` and `SUPERSET_TARGET=shared` in
`.env` before building the dashboards: every chart and dashboard name gets
the prefix "Windsor Housing | ", so a build can never touch another team's
work. Dashboards are addressed by slug (`windsor-overview`,
`windsor-story-1` to `windsor-story-5`), the same on every Superset; build
the website with `VITE_SUPERSET_URL` set to the Superset it embeds.

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
| `extract_windsor_starts_completions.py` | `windsor_starts_completions_monthly.csv` (Windsor CMA, monthly from Jan-2016, StatCan 34-10-0154-01 -- downloads the table zip to `data/raw/statcan/` on first run; `--refresh` re-downloads) |
| `extract_peer_cma_context.py` | `peer_cma_context.csv` (Windsor and the 4 comparison CMAs: renter incomes by band, Census population, households and tenant burden, yearly starts and completions, renter burden by age, and each city's purpose-built rental units for Story 5, and October rents and vacancy 2015 onward for Story 4's ten-year section; downloads StatCan 98-10-0241-01 to `data/raw/statcan/` and the four comparison cities' CMHC rental workbooks to `data/raw/cmhc/peer_rms_2025/` on first run, and re-downloads StatCan 34-10-0133-01 and 34-10-0130-01 on every run) |

Optionally, `load_raw_files_to_postgres.py` loads every file under
`data/raw/` as-is into Postgres's `raw` schema first, for reference --
this is separate from, and not required by, the staging/warehouse path
below.

### 2. Load (staging CSV -> Postgres)

Two different loaders, for two different kinds of destination:

- **`create_warehouse_schema.py`** -- creates and seeds `sql/warehouse_schema.sql`'s
  dimensional model (run once, or after a schema change).
- **`load_warehouse_facts.py`** -- bulk-loads all 6 fact tables
  (`fact_shelter_cost`, `fact_census_profile`, `fact_rental_market`,
  `fact_rental_market_comparison`, `fact_starts_completions`,
  `fact_windsor_starts_completions`) from the staging CSVs above, resolving every
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
`story3_views.sql`, `story4_views.sql`, `dashboard1_views.sql`,
`story5_views.sql`) against the
warehouse schema:
```
.venv\Scripts\python.exe etl\apply_sql_views.py
```
Then, to register the views as Superset datasets:
```
.venv\Scripts\python.exe etl\register_superset_datasets.py
```

**Two Superset installations.** The builders run against this project's
Superset 3.1 (default) or the university's shared Superset 6
(`apss.cs.uwindsor.ca`): set `SUPERSET_URL` and `SUPERSET_TARGET=shared` in
`.env`. `etl/superset_compat.py` handles the differences: bars are drawn with
the ECharts bar chart (the legacy `dist_bar` was removed after Superset 3),
every series gets an explicit colour (our `windsor_housing` scheme cannot be
added on a shared server), and Story 2's explanation panel becomes a plain
table (template processing and styled HTML are off there). Each builder ends
with `finish_dashboard()`, which fills in colours and cross-filter settings it
did not set itself.

Every dashboard builder below splits its dashboard into tabs that each fit
one screen: the builder lists its sections per tab in a `TABS` constant and
`dashboard_tabs.add_tabs()` arranges them (tested in `test_dashboard_tabs.py`).
To move a chart to another tab, move its row id between the lists.

Every figure quoted on the website (KPI tiles, story text, home page) comes
from `web/src/data/figures.json`, written by the same export
(`etl/site_figures.py`), so a refresh updates the numbers on the site. The
pages' wording also makes comparisons ("the most in ten years"); when a
refresh brings a newer rent survey or construction year, the export prints a
warning and `test_site_highlights.py` fails until someone re-reads the story
pages and updates `TEXT_WRITTEN_FOR` in `etl/site_figures.py`.

The home page's "story in four charts" is drawn by the website itself
(`web/src/components/StoryHighlights.jsx`) from `web/src/data/highlights.json`.
After a data refresh, re-export it from the warehouse views and rebuild the
website:
```
.venv\Scripts\python.exe etl\export_site_highlights.py
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

Build Story 3's dashboard ("Is Windsor building enough housing?" --
Windsor CMA starts vs completions by dwelling type, starts per 1,000
households and a 2016-2025 trend, with a Year filter):
```
.venv\Scripts\python.exe etl\build_story3_dashboard.py
```

Build Story 5's dashboard ("How do affordability, rental conditions, and
supply fit together?"), the combined dashboard: every chart reads a view in
`sql/story5_views.sql` that joins two stories (renter incomes x rents,
incomes x comparison cities, completions x vacancy, construction x
comparison cities, completions x population growth, renters by age, rental units x renter households, and one all-measures city table), with a Years filter. Needs `extract_peer_cma_context.py`
and the load step run first; method and findings in
[docs/story5_combined_analysis.md](../docs/story5_combined_analysis.md):
```
.venv\Scripts\python.exe etl\build_story5_dashboard.py
```

Build Story 4's dashboard ("How does Windsor compare to similar
markets?" -- Windsor vs. the 4 real comparator CMAs on vacancy, rent,
and the real rent-growth side of the affordability-gap index):
```
.venv\Scripts\python.exe etl\build_story4_dashboard.py
```

Build Story 1's dashboard (its tenure bar first, then the dashboard, its
other charts and its Tenure and Household Type filters):
```
.venv\Scripts\python.exe etl\setup_superset_dashboard.py
.venv\Scripts\python.exe etl\finalize_story1_layout.py
```

Turn on embedding for the five story dashboards (the website embeds them
by slug: `windsor-story-1` to `windsor-story-5`; the overview is
`windsor-overview`):
```
.venv\Scripts\python.exe etl\enable_dashboard_embedding.py
```

Apply (or remove) the dashboard theme on all 6 dashboards -- custom
CSS only, see the script's docstring; dashboard rebuilds keep it:
```
.venv\Scripts\python.exe etl\apply_dashboard_theme.py
.venv\Scripts\python.exe etl\apply_dashboard_theme.py --remove
```

## Weekly scheduled refresh and schema guard

`etl/scheduled_refresh.py` is the job to schedule. Each run:

1. downloads the latest StatCan 34-10-0154-01 zip (Windsor housing starts, updated monthly; the CMHC and Census files are annual and are placed in `data/raw` by hand);
2. runs the **schema guard** (`etl/schema_guard.py`), which compares every source file's columns, sheets and header rows with the saved snapshot in `etl/configs/source_schemas.json`;
3. only if the guard passes, runs every extract/reshape script and then `refresh_all.py`.

If the download, the guard or any step fails, the run stops (the database keeps the last good data), appends the reason to `logs/refresh_alerts.log`, and posts it to `ALERT_WEBHOOK_URL` (a Microsoft Teams or Slack incoming webhook) if that is set in `.env`. Every run's full output is in `logs/scheduled_refresh_<time>.log`. Exit codes: 0 success, 1 download failed, 2 schema guard failed, 3 a step failed.

```
.venv\Scripts\python.exe etl\scheduled_refresh.py                 # full run
.venv\Scripts\python.exe etl\scheduled_refresh.py --check-only    # download + guard only
.venv\Scripts\python.exe etl\scheduled_refresh.py --no-download   # use the files already in data/raw
.venv\Scripts\python.exe etl\schema_guard.py                      # guard on its own
```

The guard ignores numbers in headings, so a new edition with new years (`Oct-25` → `Oct-26`) passes, while a renamed, added, removed or reordered column fails. A real example it catches: CMHC renamed the "Bachelor" column to "Studio" between the 2024 and 2025 Windsor workbooks.

**When the guard fails:** read the reported change, update the extract script that reads that file, check its output, then accept the new structure with:
```
.venv\Scripts\python.exe etl\schema_guard.py --update
```
Also run `--update` after adding a new edition's workbook to `schema_guard.SOURCES`.

**Schedule it weekly.** On Windows (Monday 06:00 by default; Docker Desktop must be running then):
```
powershell -ExecutionPolicy Bypass -File etl\register_weekly_refresh.ps1
```
On a Linux server, add to the deploying user's crontab (`crontab -e`), Mondays at 06:00:
```
0 6 * * 1 cd /srv/windsor-housing && .venv/bin/python etl/scheduled_refresh.py >> logs/cron.log 2>&1
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
