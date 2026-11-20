# Data Architecture: database layers

The project's PostgreSQL database has four schemas. Data moves from the government files to the dashboards through them in one direction. This page says what each layer holds and which one to query; for the whole system see [architecture.md](architecture.md), and for every table and view, [data_dictionary.md](data_dictionary.md).

*Updated 19 November 2026. The October version of this page described an unfinished state (the warehouse not yet loaded, Superset reading `public`); that is resolved, as below.*

## The layers

| Schema | Holds | Built by | Query it? |
|---|---|---|---|
| `raw` | Every source file loaded as-is, tagged with its file name and load time (48 tables, about 5 million rows), plus `raw.load_audit`, one row per framework load | `etl/load_raw_files_to_postgres.py` (optional), `etl/run_framework_loads.py` (audit) | Only to trace a figure back to its file |
| `staging` | Cleaned copies of the `raw` tables with the same names (48 tables) | `etl/run_framework_loads.py` | No: intermediate |
| `public` | Story 1's tidy shelter-cost tables (`windsor_shelter_cost_long` and its wide form), loaded through the ETL framework | `etl/run_framework_loads.py` (`etl/configs/*.yaml`) | Story 1's tenure bar only |
| `warehouse` | **The analysis layer.** 8 dimensions, 9 fact tables and 59 views | `sql/warehouse_schema.sql` (via `etl/create_warehouse_schema.py`), `etl/load_warehouse_facts.py`, `etl/apply_sql_views.py` | **Yes: dashboards and the website read only its views** |

The layers follow the usual bronze / silver / gold pattern: `raw` is exactly what was downloaded, `staging` and the extracts' CSVs in `data/staging/` are cleaned, and `warehouse` is modelled for analysis.

## Rules that keep the layers consistent

1. **Measures live in views, nowhere else.** A dashboard chart or a website figure reads a `warehouse.v_*` view; no chart has its own SQL formula for a measure. Change a measure in its `sql/story*_views.sql` file and both the dashboards and the website follow.
2. **Facts are reloaded, not edited.** `etl/load_warehouse_facts.py` truncates and reloads every fact table from `data/staging/`; nothing in `warehouse` is edited by hand.
3. **Only `warehouse` goes to the university.** `etl/export_for_shared_db.py` packages the `warehouse` schema plus Story 1's one `public` table, moved into `warehouse` (ordinary users cannot create tables in `public` there). `raw` and `staging` stay on the laptops: they are large and are rebuilt from `data/raw/`.

## Fresh database, in order

The one-command way is `etl\scheduled_refresh.py` (download, check, extract, load); see [setup_guide.md](setup_guide.md). Step by step:

```
.venv\Scripts\python.exe etl\fetch_raw_data.py            # data/raw (plus the files saved by hand)
.venv\Scripts\python.exe etl\schema_guard.py              # every file matches its saved structure
.venv\Scripts\python.exe etl\extract_<source>.py          # each extract, see etl/README.md
.venv\Scripts\python.exe etl\refresh_all.py               # warehouse schema, facts, framework loads, views, Superset datasets
.venv\Scripts\python.exe etl\load_raw_files_to_postgres.py  # optional: the raw layer, for tracing only
```
