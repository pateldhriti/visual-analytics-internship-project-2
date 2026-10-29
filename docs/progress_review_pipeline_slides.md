# Progress Review — Pipeline Section

**Presenter:** Romit Patel
**Covers:** the ETL flow (extract → load → views/Superset) and the data-quality checks run against
it. One slide per `##` heading below -- paste each section as its own slide. All figures are real,
pulled from this repo's own code and docs (`etl/README.md`, `docs/data_quality_report.md`,
`docs/sprint2_status_note.md`), not estimated for this review.

## Slide 1: Pipeline at a glance

Three stages, each idempotent (safe to re-run):

1. **Extract** — raw source file → staging CSV (`data/staging/`)
2. **Load** — staging CSV → Postgres (`warehouse` schema + `raw.load_audit`)
3. **Views** — SQL views on the warehouse → registered as Superset datasets

One command (`etl/refresh_all.py`) runs stages 2-3 end to end and stops at the first failing step.
Verified today by running it twice in a row: identical row counts both times, zero errors, zero
duplication.

## Slide 2: Extract stage — 6 real sources

| Source | Script | Output |
|---|---|---|
| Windsor shelter cost (StatCan) | `extract_windsor_shelter_cost.py` + `reshape_shelter_cost_long.py` | `windsor_shelter_cost(_long).csv` |
| Windsor census profile (StatCan) | `extract_windsor_census_profile.py` + `reshape_census_profile_long.py` | `windsor_census_profile_long.csv` |
| Windsor rental market, current (CMHC RMS) | `extract_windsor_rms.py` | `windsor_rental_market.csv` |
| Windsor rental market, historical (CMHC RMS) | `extract_windsor_rms_historical.py` | `windsor_rental_market_historical.csv` (Oct-20 to Oct-23) |
| Comparator CMAs (CMHC RMS) | `extract_rms_canada_comparison.py` | `rms_canada_comparison.csv` |
| Starts/completions (CMHC) | `extract_cmhc_starts_completions.py` | `ontario_canada_starts_completions.csv` |

Deliberately not part of the one-command refresh — these hit real external sources over the
network, so re-running them on every refresh would add unnecessary repeat load on CMHC/StatCan for
data that doesn't change run to run.

## Slide 3: Load stage — two different loader paths, by design

- **Star-schema path** (`load_warehouse_facts.py`) — joins each staging row to its real dimension
  (geography, period, zone) and appends to one of 4 fact tables. Used for the rental-market,
  shelter-cost, census, and starts/completions data that need to combine across dimensions.
- **Schema-validated flat path** (`run_framework_loads.py` + `etl/configs/*.yaml`) — validates a
  CSV's columns exactly match an expected set before loading, and records every attempt (success or
  failure) in `raw.load_audit`. Used where a reliable, audited load matters more than joining into
  the star schema.

Both are safe to re-run: fact tables are truncated first; framework loads overwrite their target
table per config.

## Slide 4: Views + Superset stage

`apply_sql_views.py` applies all 5 SQL view files (`story1` through `story4`, plus `dashboard1`) —
every view is `CREATE OR REPLACE`, so applying them is naturally idempotent.
`register_superset_datasets.py` then registers all **16 views** as Superset datasets with saved
metrics, so chart-builders pick a named metric from a dropdown instead of retyping SQL per chart.

## Slide 5: Data checks — rental market table

Source: `warehouse.fact_rental_market` (2 staging sources → 1 table). Checked 2026-10-29.

- **Row counts vs. source** — PASS: 2,385 live rows = 1,395 (current) + 990 (historical)
- **Rent/vacancy ranges** — PASS: 0 values outside their metric's real bound, across all 12 metric
  types this table carries
- **Duplicate keys** — PASS: 2,385 rows checked, 0 in a duplicate (zone, period, bedroom type,
  dwelling type, income band, metric type) group
- **Reliability letters** — PASS: only the 4 valid CMHC grades (a/b/c/d) appear

## Slide 6: Data checks — supply tables (with an honest gap flagged)

Source: `data/staging/ontario_canada_starts_completions.csv` → `warehouse.fact_starts_completions`.

- **Ranges** — PASS: units in [284, 410,323], 0 negative/null/absurd rows
- **Reconciliation** — PASS: dwelling-type components sum to Total across 10 groups, 0 mismatches
- **Not a time series** — flagged, not hidden: only 2 periods exist (one quarter snapshot + its own
  YTD figure), not a multi-period series. Every prior CMHC quarter is genuinely missing from this
  project's data, not a handful of scattered gaps.

## Slide 7: Real bugs found and fixed this sprint, by actually testing against live state

- **Reliability-letter data bug** — 43 rental-market rows had a stray space instead of a valid
  letter, traced back to the raw CMHC workbook; found by the automated check above, fixed at load
  time.
- **Superset `find_existing()` pagination bug** — the dataset/chart/dashboard lookup used by every
  Superset-building script only checked the API's unpaginated default page (20 rows). Once this
  project's chart count passed 20, it silently missed real existing charts and created duplicates on
  rebuild instead of updating them in place — caught by rebuilding the Story 2 dashboard and noticing
  4 unexpected duplicate chart ids, not by reasoning about the code. Fixed by paginating through every
  page; re-verified by running the same rebuild twice with identical chart ids both times.

## Slide 8: Known real gaps (flagged honestly, not hidden)

- Story 3 (supply) is Ontario/Canada-only — no Windsor-specific starts/completions figure exists in
  CMHC's source table.
- Affordability-gap index's rent-growth side is real and tested; the renter-income-growth side is
  `NULL` everywhere — no source extracted so far contains that series.
- Historical rental data covers a real 5-year span (Oct-20 to Oct-25), not 10 — stated explicitly
  rather than assumed.

## Slide 9: Next steps

- Extend the automated data-quality checks to the remaining fact tables (shelter cost, census
  profile) the same way the rental-market and supply tables already have them.
- Revisit whether a Windsor-specific supply figure can be sourced to close the Story 3 gap.
- Keep re-running `refresh_all.py` as the standard pre-demo check before each milestone review.
