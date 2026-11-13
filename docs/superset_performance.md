# Superset Performance: Cache Settings and Indexes

**Date:** 6 November 2026
**Environment:** local Docker stack (PostgreSQL 16, Redis 7, Superset 3.1.0) on the development laptop.

## What was slow

Each warehouse view was timed with `EXPLAIN ANALYZE` (average of 3 runs). The slowest were the three Story 1 views: they read `fact_shelter_cost` (90,720 rows) and filter on four text columns that had no index. Each dashboard was also timed in a real browser from navigation until every chart query had finished.

## Changes

1. **Partial index on `fact_shelter_cost`** covering only the rows every Story 1 view reads (point estimates at total housing suitability and total dwelling condition, about 1/27 of the table).
2. **Index on `fact_rental_market (metric_type, period_key, zone_key)`** for the Story 2 and Dashboard 1 views.
   Both are in `sql/warehouse_schema.sql`, so a rebuild recreates them.
3. **Chart-result cache kept for 24 hours instead of 5 minutes.** The data only changes when the weekly refresh runs, so a 5-minute cache made almost every visit recompute every chart. Results now sit in their own Redis database (DB 4, `DATA_CACHE_CONFIG` in `docker/superset_config.py`).
4. **The cache is cleared after each data reload** (`etl/refresh_all.py`), so visitors never see old figures. Superset 3.1's cache-invalidation API was not used: it only clears keys recorded in the metadata database, which this setup does not record.

## Results

### Query time per view (milliseconds, average of 3 runs)

| View | Before | After |
|---|---|---|
| v_story1_burden_severity_breakdown | 26.1 | 1.2 |
| v_story1_burden_by_income_band | 16.5 | 0.5 |
| v_story1_burden_by_household_type | 14.4 | 0.5 |
| v_dashboard1_cma_benchmark | 10.2 | 2.0 |
| v_story2_rent_growth | 6.0 | 0.6 |
| v_story2_rent_yoy_change | 4.8 | 0.7 |
| v_story2_zone_snapshot | 3.5 | 0.8 |
| v_story2_vacancy_trend | 1.8 | 0.9 |

The slowest views are 10–30× faster; results are unchanged (indexes only change how rows are found).

### Cache lifetime

| | Before | After |
|---|---|---|
| Time a cached chart result is kept | 300 s (5 min) | 86,400 s (24 h), checked with `redis-cli TTL` |
| Cached results after visiting all six dashboards | expire 5 minutes later | 58 kept for 24 h, cleared after a refresh |

### Dashboard load time in the browser (seconds, until the last chart query finishes)

Cold = chart cache emptied first; warm = second visit.

| Dashboard | Before cold | Before warm | After cold (average of runs) | After warm |
|---|---|---|---|---|
| Executive Overview (5) | 10.6 | 5.6 | 5.5 (6.3, 6.1, 5.0, 4.7) | 5.8 |
| Story 1 (3) | 8.4 | 4.9 | 6.3 (8.2, 4.7, 7.0, 5.3) | 6.4 |
| Story 2 (4) | 8.2 | 5.9 | 8.8 (12.6, 6.7, 7.8, 8.2) | 7.8 |
| Story 3 (7) | 6.4 | 6.9 | 5.8 | 5.2 |
| Story 4 (6) | 4.7 | 6.4 | 4.4 | 3.3 |
| Story 5 (8) | 5.7 | 4.6 | 4.7 | 3.4 |

**How to read this honestly:** repeated cold loads of the same dashboard varied by 2–4 seconds on this laptop (it was short of memory during testing), so differences of that size are noise. Most of a page load is the browser drawing the charts, not the database: even the slowest query now takes about 5 ms. The clear gains are the query times and the cache lifetime; dashboard-level times improved for the Executive Overview and Story 1 (the dashboards that used the slow Story 1 views) and did not measurably change for Story 2, whose 17 charts are limited by drawing time. A hosted server with more memory should show less variation.

## How to repeat the measurements

```
# query times
docker exec windsor_housing_postgres psql -U <user> -d housing_windsor \
  -c "EXPLAIN ANALYZE SELECT * FROM warehouse.v_story1_burden_by_income_band"
# empty the chart cache before a cold measurement
docker exec windsor_housing_redis redis-cli -n 4 FLUSHDB
# cache lifetime of a stored chart result
docker exec windsor_housing_redis redis-cli -n 4 --scan | head -1   # then: redis-cli -n 4 TTL <key>
```

## Re-check, 13 November 2026

Since 6 November, several views were added: the ten-year Story 4 views, the period comparisons, the Overview trend and the Story 5 city profile and radar. All 37 views were timed again the same way (`EXPLAIN ANALYZE`, average of 3 runs after one warm-up).

**Slowest view found:** `v_story5_windsor_vs_peers`, behind the Story 5 overview radar, took **63.0 ms**, more than six times the next slowest view. It reads `v_story5_city_profile` (6.9 ms) twice, once for Windsor and once for the comparison average. PostgreSQL pushed the Windsor filter into the profile and planned that copy far worse than the profile itself. The view now computes the profile once (`WITH p AS MATERIALIZED`) and reads both rows from it. It returns the same two rows, and now takes **about 6-9 ms** (runs of 9.6, 7.1, 15.5 and 6.1 ms).

| View | Before | After |
|---|---|---|
| v_story5_windsor_vs_peers | 63.0 | ~7 (6.1-9.6, one run 15.5) |
| v_story2_zone_bedroom_explanation | 9.7 | unchanged: builds comparison sentences for 35 zone × unit-size rows |
| v_story5_city_profile | 6.9 | unchanged: joins five sources for five cities |
| every other view (34) | 0.5-3.5 | unchanged |

No new index is needed: the remaining views read small tables (at most about 2,400 rows) or use the indexes from 6 November.

**Chart cache:** still 24 hours. After visiting the dashboards, Redis DB 4 held 325 cached chart results, and a sampled key had 86,007 seconds left.
