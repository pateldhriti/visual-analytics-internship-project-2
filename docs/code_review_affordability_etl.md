# Code Review: Affordability ETL (`etl/run_affordability_etl.py`)

**Scope:** `etl/run_affordability_etl.py`, `etl/reshape_shelter_cost_long.py`, `etl/load_warehouse_facts.py`'s `load_shelter_cost_facts()`, and `etl/load_windsor_shelter_cost_to_postgres.py` — Dhritiben's production job for Story 1's affordability pipeline (StatCan 98-10-0252-01), reviewed as it stands on `main` today.

**Method:** read every line of the 4 files above end to end, then verified each finding empirically against the real database and the real staging data rather than reasoning about the code in the abstract.

## Result: the pipeline is correct and well-tested, with one real reliability gap

Re-ran the job end to end on a fresh schema: 30,240 extracted -> 90,720 reshaped -> 90,720 loaded, 0 unmatched dimension keys, the reshape's own 4 built-in integrity checks all pass, and the known Owner 30%+ burden value (13,005) checks out against the reloaded table. The 15-case unit test suite (`etl/test_affordability_etl.py`) passes. Found one real finding worth fixing and two smaller ones worth a second look.

## Finding 1: truncate and load aren't one atomic operation (moderate)

`run_affordability_etl.py` truncates `fact_shelter_cost` in its own transaction (`etl/run_affordability_etl.py:64-65`, a separate `engine.begin()` block that commits on exit), then calls `load_shelter_cost_facts()`, which loads via `copy_dataframe()` on a **different** connection (`etl/load_warehouse_facts.py:63-71`, its own `raw_connection()` with its own `commit()`).

Confirmed these are genuinely two separate transactions, not one: a failure partway through the `COPY` (a constraint violation, a dropped connection, anything) rolls back only the `COPY` itself — the truncate has already committed and stays committed. A transient failure during load leaves `fact_shelter_cost` **empty**, not restored to its last successful state. For a table Superset queries directly, that's a real production risk: a bad run doesn't just fail, it takes the dashboard down until the next successful run.

**Suggested fix:** wrap the truncate and the `COPY` in one transaction — either have `copy_dataframe()` accept an existing connection instead of opening its own, or move the truncate inside `load_shelter_cost_facts()` on the same `raw_connection()` the `COPY` already uses.

## Finding 2: a comma-formatted number would silently become an unflagged NULL (low-moderate, latent)

`reshape_shelter_cost_long.py`'s `part["value"] = pd.to_numeric(part[value_col], errors="coerce")` turns anything it can't parse into `NaN`, with no distinction between "StatCan published a symbol here" and "this string just didn't parse." Checked what that means for a thousands-separator value directly:

```
pd.to_numeric(pd.Series(['13,005']), errors='coerce')
0   NaN
```

**Not an active bug** — checked the real staging CSV directly, and none of the 3 tenure value columns contain comma-formatted numbers today. But it's a real latent risk: if a future refresh of this source (or a different StatCan table reused with this pattern) ever publishes with thousands separators, the value would silently become `NULL` with **no symbol and no `data_quality_flag`** — indistinguishable from a genuinely blank StatCan cell, not caught as an error.

Worth noting this wouldn't be caught by the existing integrity checks either: `verify_preserves_original()`'s `non_null_value_count_preserved` check compares the wide-table's `pd.to_numeric(...)` count against the long table's — since both sides run the *same* coercion, a comma-formatting issue would be consistently "correct" on both sides of that comparison, not flagged.

**Suggested fix (not urgent given today's data is clean):** strip thousands separators before coercion (`.str.replace(",", "")`) the same way `etl/extract_rms_canada_comparison.py`'s `clean_value()` already does for a different source, so a future format change fails loud instead of silently nulling data.

## Finding 3: the unmatched-dimension-key check is unreachable for this table (minor, informational)

`run_affordability_etl.py` checks `if any(load_stats["unmatched_dimension_keys"].values()): raise RuntimeError(...)` after calling `load_shelter_cost_facts()`. For `fact_shelter_cost` specifically, every foreign-key column (`geography_key`, `period_key`, `income_band_key`, `household_type_key`, `tenure_key`) is `NOT NULL` in the schema (`sql/warehouse_schema.sql`) — so an unmatched key (which merges in as `NaN`) would already fail the `COPY` itself with a `NOT NULL` violation before this check ever runs. Not a bug, just dead code as written today for this specific table. Flagging it because it reads as a real safety check but isn't currently exercised — it would only do real work if this function were reused for a fact table with a nullable FK (e.g. `fact_rental_market`'s `income_band_key`), which it isn't.

## What's solid

- The symbol-to-flag mapping (`SYMBOL_FLAG_MAP`) fails loud on any unrecognized symbol rather than passing it through silently — good defensive design, and genuinely exercised by `etl/test_affordability_etl.py::test_unrecognized_symbol_raises`.
- Both bugs from the earlier peer test (`docs/peer_test_affordability_etl.md`) are confirmed fixed: the wide table's 3 value columns load as `NUMERIC` now, and the long table's `REF_DATE`/`GEO`/`DGUID`/`Coordinate` columns are renamed to snake_case.
- Row-count and known-value verification is real, not just claimed — re-ran it independently rather than trusting the docstring.
