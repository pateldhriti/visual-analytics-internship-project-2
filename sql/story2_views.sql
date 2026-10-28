-- SQL views for Story 2 ("What is happening in Windsor's rental market?"):
-- rent year-over-year change, multi-year rent growth rate, vacancy trend,
-- turnover by bedroom type, and rent by zone and bedroom type. Built on
-- warehouse.fact_rental_market's historical rows (etl/load_warehouse_facts.py's
-- load_historical_rental_market_facts(), 6 real CMHC RMS editions -- see
-- docs/rms_historical_extraction.md), not estimated or interpolated.
--
-- The first 4 views are scoped to Windsor CMA (zone_label = 'Windsor CMA') --
-- the historical extraction only covers Windsor, not the Story 4
-- comparator CMAs, so a wider geography here would be silently wrong.
-- v_story2_rent_by_zone_bedroom (the 5th, at the bottom of this file) is
-- the one deliberate exception -- it exists specifically to break rent out
-- by Windsor's own 7 internal zones, which the CMA rollup can't show.
--
-- On "10-year growth rate": the real CMHC Windsor RMS data this project
-- has loaded only spans Oct-20 to Oct-25 -- 5 years, not 10. Rather than
-- label a 5-year figure as a 10-year one, or fabricate 5 years of data
-- that were never extracted, v_story2_rent_growth reports the real span
-- it has (5 years) and says so explicitly in its own data_note column.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- v_story2_rent_yoy_change
-- One row per (bedroom type, period): average rent and the year-over-year
-- change vs. the previous October survey, computed directly from the
-- historical series (LAG), not from CMHC's own same-sample rent-change
-- table (metric_type = 'pct_change_rent'), which only covers 2 Bedroom
-- Apartment for Oct-24/Oct-25 -- too narrow to answer this question for
-- every bedroom type across all 6 years on its own.
-- The first year (Oct-20) has no prior year in this dataset, so its
-- change columns are NULL -- a real gap, not a computed zero.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_rent_yoy_change AS
SELECT
    b.bedroom_type_label,
    p.period_label,
    p.period_year,
    f.value AS average_rent,
    LAG(f.value) OVER (PARTITION BY b.bedroom_type_label ORDER BY p.period_year)
        AS prior_year_rent,
    ROUND(
        f.value - LAG(f.value) OVER (PARTITION BY b.bedroom_type_label ORDER BY p.period_year),
        2
    ) AS yoy_change_dollars,
    ROUND(
        100.0 * (f.value - LAG(f.value) OVER (PARTITION BY b.bedroom_type_label ORDER BY p.period_year))
            / NULLIF(LAG(f.value) OVER (PARTITION BY b.bedroom_type_label ORDER BY p.period_year), 0),
        1
    ) AS yoy_change_pct,
    f.reliability_letter
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'average_rent'
  AND z.zone_label = 'Windsor CMA'
  AND d.dwelling_type_label = 'Combined';

-- ============================================================
-- v_story2_rent_growth
-- One row per bedroom type: total rent growth from the first to the last
-- period this project has real data for -- a real N-year rate, with
-- years_span and data_note stating exactly how many years that is (5,
-- Oct-20 to Oct-25), not assumed to be any particular round number.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_rent_growth AS
WITH windsor_rent AS (
    SELECT
        b.bedroom_type_label,
        p.period_year,
        p.period_label,
        f.value AS average_rent
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE f.metric_type = 'average_rent'
      AND z.zone_label = 'Windsor CMA'
      AND d.dwelling_type_label = 'Combined'
),
bounds AS (
    SELECT bedroom_type_label, MIN(period_year) AS first_year, MAX(period_year) AS last_year
    FROM windsor_rent
    GROUP BY bedroom_type_label
)
SELECT
    bnd.bedroom_type_label,
    r_first.period_label AS first_period_label,
    r_first.average_rent AS first_period_rent,
    r_last.period_label AS last_period_label,
    r_last.average_rent AS last_period_rent,
    (bnd.last_year - bnd.first_year) AS years_span,
    ROUND(r_last.average_rent - r_first.average_rent, 2) AS growth_dollars,
    ROUND(
        100.0 * (r_last.average_rent - r_first.average_rent) / NULLIF(r_first.average_rent, 0),
        1
    ) AS growth_pct,
    'Real span is ' || (bnd.last_year - bnd.first_year) || ' years (' || r_first.period_label
        || ' to ' || r_last.period_label
        || ') -- a 10-year rate is not computable, this project has no Windsor RMS data before Oct-20'
        AS data_note
FROM bounds bnd
JOIN windsor_rent r_first
    ON r_first.bedroom_type_label = bnd.bedroom_type_label AND r_first.period_year = bnd.first_year
JOIN windsor_rent r_last
    ON r_last.bedroom_type_label = bnd.bedroom_type_label AND r_last.period_year = bnd.last_year;

-- ============================================================
-- v_story2_vacancy_trend
-- One row per (dwelling type, bedroom type, period): vacancy rate across
-- all 6 real survey periods (Oct-20 through Oct-25), both dwelling-type
-- scopes this project has (Apartment and Combined).
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_vacancy_trend AS
SELECT
    d.dwelling_type_label,
    b.bedroom_type_label,
    p.period_label,
    p.period_year,
    f.value AS vacancy_rate_pct,
    f.reliability_letter,
    f.yoy_trend
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'vacancy_rate'
  AND z.zone_label = 'Windsor CMA';

-- ============================================================
-- v_story2_turnover_by_bedroom
-- One row per (dwelling type, bedroom type, period): turnover rate. The
-- Combined scope has all 5 bedroom types across all 6 years; the
-- Apartment scope only publishes a Total-bedroom turnover figure, and
-- only for Oct-24/Oct-25 -- both real gaps in CMHC's own workbook, shown
-- as-is rather than filtered out or filled in.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_turnover_by_bedroom AS
SELECT
    d.dwelling_type_label,
    b.bedroom_type_label,
    p.period_label,
    p.period_year,
    f.value AS turnover_rate_pct,
    f.reliability_letter,
    f.yoy_trend
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'turnover_rate'
  AND z.zone_label = 'Windsor CMA';

-- ============================================================
-- v_story2_rent_by_zone_bedroom
-- One row per (zone, bedroom type): average rent for the most recent
-- real survey period (Oct-25), broken out by Windsor's 7 real zones --
-- a gap the 4 views above don't cover, since every one of them is
-- scoped to the Windsor CMA rollup only (`z.zone_label = 'Windsor CMA'`)
-- and never breaks out by individual zone. The per-zone rows exist in
-- `fact_rental_market` already (same historical load as the other 4
-- views); this just gives them their own queryable shape.
-- Excludes the 2 rollup rows ('Windsor CMA', 'Windsor City
-- (Zones 1-4)') -- including them in a per-zone chart would double-count
-- against the 7 real zones. Zone 7 only has real data from Oct-23
-- onward (see docs/rms_historical_extraction.md), which doesn't affect
-- this view since it's scoped to the latest period only.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_rent_by_zone_bedroom AS
SELECT
    z.zone_label,
    b.bedroom_type_label,
    p.period_label,
    f.value AS average_rent,
    f.reliability_letter
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'average_rent'
  AND d.dwelling_type_label = 'Combined'
  AND p.period_label = 'Oct-25'
  AND z.zone_label NOT IN ('Windsor CMA', 'Windsor City (Zones 1-4)');
