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
-- data); data_note states this on every row. The current partial year is
-- included, flagged by is_partial_year, so the At a Glance tile has a value
-- when that year is picked in the Year filter; the yearly chart leaves it
-- out, since 9 months of starts against a full household base would read
-- as a slowdown that isn't real.
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
        SUM(units) FILTER (WHERE activity = 'Completions') AS completions_total,
        BOOL_OR(is_partial_year) AS is_partial_year
    FROM warehouse.v_story3_windsor_supply_annual
    WHERE dwelling_type = 'Total'
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
        || 'no annual household estimate exists in this project''s data.' AS data_note,
    a.is_partial_year
FROM annual a
CROSS JOIN households h;

-- ---------------------------------------------------------------------------
-- v_story3_period_comparison
-- Windsor's building before and from the pandemic: the yearly average of
-- starts and completions, by dwelling type, in 2016-2020 and in 2021-2025
-- (five full calendar years each), and each type's share of the period's
-- total. Partial years are left out, so a period is only reported once all
-- five of its years are complete (n_years shows how many were averaged).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story3_period_comparison AS
WITH yearly AS (
    SELECT
        CASE WHEN period_year BETWEEN 2016 AND 2020 THEN '2016 to 2020'
             WHEN period_year BETWEEN 2021 AND 2025 THEN '2021 to 2025' END AS period,
        period_year,
        activity,
        dwelling_type,
        units
    FROM warehouse.v_story3_windsor_supply_annual
    WHERE activity IN ('Starts', 'Completions')
      AND NOT is_partial_year
      AND period_year BETWEEN 2016 AND 2025
),
averaged AS (
    SELECT period, activity, dwelling_type,
           COUNT(DISTINCT period_year) AS n_years,
           SUM(units) AS total_units,
           ROUND(AVG(units), 0) AS avg_units_per_year
    FROM yearly
    GROUP BY period, activity, dwelling_type
)
SELECT
    a.period,
    a.activity,
    a.dwelling_type,
    a.n_years,
    a.total_units,
    a.avg_units_per_year,
    ROUND(100.0 * a.total_units / NULLIF(t.total_units, 0), 1) AS pct_of_total
FROM averaged a
JOIN averaged t
  ON t.period = a.period AND t.activity = a.activity AND t.dwelling_type = 'Total'
WHERE a.n_years = 5;


-- ---------------------------------------------------------------------------
-- Story 3 tabs "This Year So Far" and "This Year's Mix": the latest year's
-- months so far (January to the latest month StatCan has published),
-- compared with the same months of earlier years. Windsor CMA, StatCan
-- 34-10-0154-01 (CMHC Starts and Completions Survey). As of January 2023 CMHC
-- uses 2021 Census geography for Windsor, so 2021-2022 and 2023 onward are
-- not strictly like for like.
-- ---------------------------------------------------------------------------

-- v_story3_ytd_by_year: starts and completions from January to the latest
-- published month, for every year since 2021, by dwelling type, with the
-- multi-unit share (everything but single-detached houses).
CREATE OR REPLACE VIEW warehouse.v_story3_ytd_by_year AS
WITH latest AS (
    SELECT MAX(period_year) AS year,
           MAX(period_month) FILTER (WHERE period_year = (SELECT MAX(period_year)
                                                         FROM warehouse.fact_windsor_starts_completions)) AS month
    FROM warehouse.fact_windsor_starts_completions
),
ytd AS (
    SELECT f.period_year, f.activity, f.dwelling_type, SUM(f.units) AS units
    FROM warehouse.fact_windsor_starts_completions f, latest l
    WHERE f.activity IN ('Starts', 'Completions') AND f.period_year >= 2021 AND f.period_month <= l.month
    GROUP BY f.period_year, f.activity, f.dwelling_type
)
SELECT
    y.period_year,
    y.activity,
    y.dwelling_type,
    y.units AS ytd_units,
    l.month AS through_month,
    TO_CHAR(MAKE_DATE(2000, l.month, 1), 'Mon') AS through_month_name,
    ROUND(100.0 * (t.units - s.units) / NULLIF(t.units, 0), 1) AS multi_unit_share_pct,
    (y.period_year = l.year) AS is_latest_year
FROM ytd y
CROSS JOIN latest l
JOIN ytd t ON t.period_year = y.period_year AND t.activity = y.activity AND t.dwelling_type = 'Total'
JOIN ytd s ON s.period_year = y.period_year AND s.activity = y.activity AND s.dwelling_type = 'Singles';

-- v_story3_ytd_shortfall: how far the latest year's starts and completions
-- so far are below the same months of each of the three previous years
-- (positive = behind).
CREATE OR REPLACE VIEW warehouse.v_story3_ytd_shortfall AS
SELECT
    p.period_year AS comparison_year,
    p.activity,
    c.ytd_units AS latest_ytd_units,
    p.ytd_units AS comparison_ytd_units,
    ROUND(100.0 * (p.ytd_units - c.ytd_units) / NULLIF(p.ytd_units, 0), 1) AS shortfall_pct
FROM warehouse.v_story3_ytd_by_year p
JOIN warehouse.v_story3_ytd_by_year c
  ON c.activity = p.activity AND c.dwelling_type = 'Total' AND c.is_latest_year
WHERE p.dwelling_type = 'Total' AND NOT p.is_latest_year
  AND p.period_year >= c.period_year - 3;

-- v_story3_pipeline: the latest year's starts and completions so far and the
-- homes under construction at the end of the latest month, by dwelling type,
-- with each type's share of that stage's total.
CREATE OR REPLACE VIEW warehouse.v_story3_pipeline AS
WITH latest AS (
    SELECT period_year AS year, MAX(period_month) AS month
    FROM warehouse.fact_windsor_starts_completions
    WHERE period_year = (SELECT MAX(period_year) FROM warehouse.fact_windsor_starts_completions)
    GROUP BY period_year
),
stages AS (
    SELECT 'Starts so far' AS stage, 1 AS stage_sort_order, dwelling_type, ytd_units AS units
    FROM warehouse.v_story3_ytd_by_year WHERE is_latest_year AND activity = 'Starts'
    UNION ALL
    SELECT 'Completions so far', 2, dwelling_type, ytd_units
    FROM warehouse.v_story3_ytd_by_year WHERE is_latest_year AND activity = 'Completions'
    UNION ALL
    SELECT 'Under construction', 3, f.dwelling_type, f.units
    FROM warehouse.fact_windsor_starts_completions f
    JOIN latest l ON f.period_year = l.year AND f.period_month = l.month
    WHERE f.activity = 'Under Construction'
)
SELECT
    s.stage,
    s.stage_sort_order,
    s.dwelling_type,
    s.units,
    ROUND(100.0 * s.units / NULLIF(t.units, 0), 1) AS pct_of_stage
FROM stages s
JOIN stages t ON t.stage = s.stage AND t.dwelling_type = 'Total'
WHERE s.dwelling_type <> 'Total';

-- v_story3_latest_month: the headline figures for the latest year so far and
-- the latest month, with readable labels ("Jan-Sep 2026", "Sep 2026").
CREATE OR REPLACE VIEW warehouse.v_story3_latest_month AS
WITH latest AS (
    SELECT period_year AS year, MAX(period_month) AS month
    FROM warehouse.fact_windsor_starts_completions
    WHERE period_year = (SELECT MAX(period_year) FROM warehouse.fact_windsor_starts_completions)
    GROUP BY period_year
)
SELECT
    l.year,
    l.month,
    'Jan-' || TO_CHAR(MAKE_DATE(l.year, l.month, 1), 'Mon YYYY') AS ytd_label,
    TO_CHAR(MAKE_DATE(l.year, l.month, 1), 'Mon YYYY') AS month_label,
    SUM(f.units) FILTER (WHERE f.activity = 'Starts') AS ytd_starts,
    SUM(f.units) FILTER (WHERE f.activity = 'Completions') AS ytd_completions,
    SUM(f.units) FILTER (WHERE f.activity = 'Starts' AND f.period_month = l.month) AS month_starts,
    SUM(f.units) FILTER (WHERE f.activity = 'Completions' AND f.period_month = l.month) AS month_completions,
    SUM(f.units) FILTER (WHERE f.activity = 'Under Construction' AND f.period_month = l.month) AS under_construction,
    SUM(f.units) FILTER (WHERE f.activity = 'Under Construction' AND f.period_month = l.month - 1)
        AS under_construction_previous_month
FROM warehouse.fact_windsor_starts_completions f
JOIN latest l ON f.period_year = l.year
WHERE f.dwelling_type = 'Total' AND f.period_month <= l.month
GROUP BY l.year, l.month;

-- ---------------------------------------------------------------------------
-- v_story3_intended_market: Windsor housing starts and completions by the
-- market they are built for (CMHC Housing Market Information Portal), each
-- full year and the current year so far (is_ytd), with each market's share
-- of the period's total. market_label uses the portal's display names
-- (Homeownership, Co-op, Not Available) in its order (market_sort_order).
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS warehouse.v_story3_intended_market;
CREATE VIEW warehouse.v_story3_intended_market AS
WITH totals AS (
    SELECT period_label, activity, units AS total_units
    FROM warehouse.fact_windsor_intended_market
    WHERE intended_market = 'All'
)
SELECT
    f.period_label,
    f.is_ytd,
    f.activity,
    f.intended_market,
    CASE f.intended_market WHEN 'Homeowner' THEN 'Homeownership' WHEN 'Co-Op' THEN 'Co-op'
                           WHEN 'Unknown' THEN 'Not Available' ELSE f.intended_market END AS market_label,
    CASE f.intended_market WHEN 'Homeowner' THEN 1 WHEN 'Rental' THEN 2 WHEN 'Co-Op' THEN 3
                           WHEN 'Condo' THEN 4 ELSE 5 END AS market_sort_order,
    f.units,
    t.total_units,
    ROUND(100.0 * f.units / NULLIF(t.total_units, 0), 1) AS share_pct
FROM warehouse.fact_windsor_intended_market f
JOIN totals t ON t.period_label = f.period_label AND t.activity = f.activity
WHERE f.intended_market <> 'All';
