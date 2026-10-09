# Data Architecture — Current State

This project's Postgres database currently has **three schemas**, built at different points for different purposes. Nothing below is a final decision — it's a snapshot of what exists today, written down so the next person doesn't have to reverse-engineer it from script names. Which of these (if any) Superset should query long-term is a real open question for the team, not something settled here.

## The three schemas

| Schema | Purpose | Built by | Populated? |
|---|---|---|---|
| `public` | Cleaned, filtered, analysis-ready tables for one specific extract (Windsor-only shelter-cost data, wide and long format) | `etl/load_windsor_shelter_cost_to_postgres.py`, `etl/load_windsor_shelter_cost_long_to_postgres.py` | Yes — 30,240 / 90,720 rows. **This is what the Superset chart actually queries today.** |
| `raw` | Every raw source file (CSV + Excel), loaded as-is, no cleaning, tagged with source filename + load timestamp | `etl/load_raw_files_to_postgres.py` | Yes — 31 tables (the full 5M-row national StatCan file, its metadata, all 29 CMHC workbook sheets) |
| `warehouse` | Conceptual star schema: 8 conformed dimensions + one fact table per profiled source | `etl/create_warehouse_schema.py` | Dimensions yes (real category values); fact tables no (schema verified via a smoke-test insert + rollback, not actually loaded) |

## Why three, and why this isn't necessarily wrong

This maps to a fairly standard layered pattern:
- **`raw`** = bronze layer — exactly what was downloaded, nothing interpreted
- **`public`**'s current tables = an ad-hoc silver layer — cleaned, but built for one specific task (the shelter-cost extract) before the `warehouse` schema existed
- **`warehouse`** = the intended gold layer — conformed dimensions or a proper star schema, meant to eventually serve all sources, not just one

The gap: `public`'s tables were built first (earlier in the project) and nothing has gone back to make them consistent with the `warehouse` model that came later. Right now a new team member has no single documented answer to "which table do I query for X" — that's the real problem this doc exists to name, not yet to solve.

## What a full reconciliation would involve (not done here)

1. Decide whether `public`'s existing Windsor extract tables get migrated into `warehouse`'s fact tables, or stay as a separate convenience layer.
2. Actually populate `warehouse.fact_shelter_cost` and `warehouse.fact_rental_market` from `raw` (or from `public`, if that stays the cleaning layer).
3. Point Superset at whichever schema the team settles on as "the" analysis layer.
4. This is exactly the kind of decision the ER model's "reviewed with Pavan" step exists for — intentionally left for that conversation rather than decided unilaterally here.

## Quick reference: what to run, in order, for a fresh database

```
.venv\Scripts\python.exe etl\load_windsor_shelter_cost_to_postgres.py
.venv\Scripts\python.exe etl\load_windsor_shelter_cost_long_to_postgres.py
.venv\Scripts\python.exe etl\load_raw_files_to_postgres.py
.venv\Scripts\python.exe etl\create_warehouse_schema.py
.venv\Scripts\python.exe etl\setup_superset_dashboard.py
```

All five are safe to re-run (each drops/replaces its own tables first).
