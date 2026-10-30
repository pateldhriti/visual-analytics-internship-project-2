-- SQL views for Story 3 ("Is Windsor building enough housing?"):
-- starts/completions by dwelling type per year, and supply per 1,000
-- households using census households. Built on top of
-- warehouse.fact_starts_completions (etl/extract_cmhc_starts_completions.py,
-- etl/load_warehouse_facts.py) and warehouse.fact_census_profile.
--
-- Two real data limits affect both views -- documented here and in each
-- view's own comment, not glossed over:
--   1. The source table is Ontario/Canada only -- CMHC's "Quarterly
--      Starts, Completions, Units Under Construction by (Canada,
--      Provinces)" has no CMA-level breakdown, so there is no
--      Windsor-specific starts/completions figure anywhere in this
--      project's data yet. A CMA-level CMHC table (e.g. "Starts,
--      Completions, and Units Under Construction by Geography") would be
--      needed to get Windsor specifically.
--   2. Only one quarter (Second Quarter 2026) and one YTD period (January
--      to June 2026) have been extracted -- not a multi-year annual
--      series. "Per year" in the task description cannot be built from a
--      single half-year snapshot; this view reports what's real (the one
--      period available) rather than fabricating prior years.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- v_story3_starts_completions_by_dwelling_type
-- One row per (province, period, activity, dwelling_type): real data,
-- Ontario + Canada, Second Quarter 2026 and YTD January-June 2026.
-- NOT a multi-year annual series -- see the limits above.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story3_starts_completions_by_dwelling_type AS
SELECT
    province,
    period_type,
    period_label,
    activity,
    dwelling_type,
    units
FROM warehouse.fact_starts_completions;

-- ============================================================
-- v_story3_supply_per_1000_households
-- Intended grain: one row per (province, period, dwelling_type) with
-- starts per 1,000 households. NOT computable with real data right now:
-- the only households figure in this project (fact_census_profile,
-- characteristic_id 50, "Total - Private households by household size")
-- is Windsor-CMA-specific (165,665 households, 2021 Census), while
-- fact_starts_completions is Ontario/Canada-only -- there is no
-- households count at a geography that matches the starts data, and no
-- starts data at Windsor's geography. Dividing Windsor's household count
-- into Ontario's starts count would produce a number that LOOKS like a
-- real per-1,000-households supply rate but measures nothing real --
-- worse than leaving it NULL.
--
-- This view reports the real starts total (province-level, matching
-- fact_starts_completions' actual geography) alongside an explicit NULL
-- households_total and supply_per_1000_households, with a data_note
-- explaining why, so a Superset chart built on this view shows an honest
-- gap rather than a fabricated rate.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story3_supply_per_1000_households AS
SELECT
    province,
    period_type,
    period_label,
    dwelling_type,
    units AS starts_total,
    CAST(NULL AS NUMERIC) AS households_total,
    CAST(NULL AS NUMERIC) AS supply_per_1000_households,
    'No households figure exists at this geography (Ontario/Canada) -- '
        || 'fact_census_profile only has Windsor CMA households. See '
        || 'sql/story3_views.sql for what would close this gap.' AS data_note
FROM warehouse.fact_starts_completions
WHERE activity = 'Starts';

-- ============================================================
-- Windsor CMA supply (StatCan 34-10-0154-01)
-- ============================================================
-- The two views below close both gaps described at the top of this file
-- for Windsor itself: warehouse.fact_windsor_starts_completions
-- (etl/extract_windsor_starts_completions.py) is Windsor-CMA-specific
-- and monthly from January 2016, so there is now a real multi-year series
-- and a geography that matches the Census households figure. The two
-- Ontario/Canada views above are left as they are -- Dashboard 1's
-- Housing Supply section still uses the provincial figures.

-- ============================================================
-- v_story3_windsor_supply_annual
-- One row per (year, activity, dwelling_type), Windsor CMA.
--   - Starts and Completions are flows: the year's monthly values summed.
--   - Under Construction is a stock (units in progress at a point in
--     time), so summing months would count the same unit up to 12 times.
--     It takes the value at the year's last available month instead
--     (December, or the latest month of a partial year).
-- The current year is partial (months_covered < 12); year_label says so
-- ("2026 (Jan-Sep)") so it can't be mistaken for a full-year total, and
-- is_partial_year lets a chart leave it out of a full-year trend.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story3_windsor_supply_annual AS
WITH coverage AS (
    SELECT period_year, MAX(period_month) AS last_month, COUNT(DISTINCT period_month) AS months_covered
    FROM warehouse.fact_windsor_starts_completions
    GROUP BY period_year
)
SELECT
    f.period_year,
    CASE
        WHEN c.months_covered = 12 THEN f.period_year::TEXT
        ELSE f.period_year || ' (Jan-' || TO_CHAR(TO_DATE(c.last_month::TEXT, 'MM'), 'Mon') || ')'
    END AS year_label,
    c.months_covered,
    (c.months_covered < 12) AS is_partial_year,
    f.activity,
    f.dwelling_type,
    CASE
        WHEN f.activity = 'Under Construction'
            THEN MAX(f.units) FILTER (WHERE f.period_month = c.last_month)
        ELSE SUM(f.units)
    END AS units
FROM warehouse.fact_windsor_starts_completions f
JOIN coverage c ON c.period_year = f.period_year
GROUP BY f.period_year, c.months_covered, c.last_month, f.activity, f.dwelling_type;

-- ============================================================
-- v_story3_windsor_supply_per_1000_households
-- One row per full calendar year: Windsor CMA starts and completions
-- (Total, all dwelling types) per 1,000 private households.
-- Denominator: the 2021 Census count of private households in the
-- Windsor CMA (fact_census_profile characteristic 50, 165,665) -- the only
-- households figure this project has, applied to every year. That makes
-- this a rate against a fixed 2021 base, not against each year's own
-- household count (no annual household estimate exists in this project's
-- data); data_note states this on every row. Partial years are left out:
-- 9 months of starts against a full household base would read as a
-- slowdown that isn't real.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story3_windsor_supply_per_1000_households AS
WITH households AS (
    SELECT value AS households_2021
    FROM warehouse.fact_census_profile
    WHERE characteristic_id = 50
      AND measure_type = 'count'
      AND sex = 'total'
      AND geography_key = '2021S0503559'
),
annual AS (
    SELECT
        period_year,
        year_label,
        SUM(units) FILTER (WHERE activity = 'Starts') AS starts_total,
        SUM(units) FILTER (WHERE activity = 'Completions') AS completions_total
    FROM warehouse.v_story3_windsor_supply_annual
    WHERE dwelling_type = 'Total'
      AND NOT is_partial_year
    GROUP BY period_year, year_label
)
SELECT
    a.period_year,
    a.year_label,
    a.starts_total,
    a.completions_total,
    h.households_2021,
    ROUND(1000.0 * a.starts_total / NULLIF(h.households_2021, 0), 2) AS starts_per_1000_households,
    ROUND(1000.0 * a.completions_total / NULLIF(h.households_2021, 0), 2)
        AS completions_per_1000_households,
    'Rate uses the 2021 Census private-household count (165,665) for every year -- '
        || 'no annual household estimate exists in this project''s data.' AS data_note
FROM annual a
CROSS JOIN households h;
