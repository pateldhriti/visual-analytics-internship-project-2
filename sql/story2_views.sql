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
    f.reliability_letter,
    -- The survey month as a real date, for Superset's trendline KPI tiles.
    MAKE_DATE(p.period_year, 10, 1) AS period_date
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
    f.yoy_trend,
    -- The survey month as a real date, for Superset's trendline KPI tiles.
    MAKE_DATE(p.period_year, 10, 1) AS period_date
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

-- ============================================================
-- v_story2_zone_snapshot
-- One row per real Windsor zone (zone_level = 'zone', so the CMA and
-- Windsor City rollups and the Story 4 comparator CMAs are excluded by
-- the dimension's own classification, not a hand-maintained name list):
-- average rent, vacancy rate, rental stock (universe) and turnover for
-- the latest survey (Oct-25), Combined dwelling types, Total bedroom type.
-- Built for Dashboard 3's zone-level section -- the 4 metrics side by
-- side, so a zone's rent can be read against its vacancy and size rather
-- than in isolation. share_of_zone_stock_pct is each zone's share of the
-- 7 zones' combined universe (they sum to the CMA total). Universe rows
-- carry no CMHC reliability letter (a count, not a sampled estimate);
-- rent and vacancy keep theirs so a 'd'-rated figure can be flagged.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_zone_snapshot AS
WITH zone_metrics AS (
    SELECT
        z.zone_label,
        p.period_label,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent') AS average_rent,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'average_rent') AS rent_reliability,
        MAX(f.value) FILTER (WHERE f.metric_type = 'vacancy_rate') AS vacancy_rate_pct,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'vacancy_rate') AS vacancy_reliability,
        MAX(f.value) FILTER (WHERE f.metric_type = 'universe') AS rental_universe,
        MAX(f.value) FILTER (WHERE f.metric_type = 'turnover_rate') AS turnover_rate_pct
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_level = 'zone'
      AND p.period_label = 'Oct-25'
      AND d.dwelling_type_label = 'Combined'
      AND b.bedroom_type_label = 'Total'
      AND f.metric_type IN ('average_rent', 'vacancy_rate', 'universe', 'turnover_rate')
    GROUP BY z.zone_label, p.period_label
)
SELECT
    zone_label,
    period_label,
    average_rent,
    rent_reliability,
    vacancy_rate_pct,
    vacancy_reliability,
    rental_universe,
    ROUND(100.0 * rental_universe / NULLIF(SUM(rental_universe) OVER (), 0), 1)
        AS share_of_zone_stock_pct,
    turnover_rate_pct
FROM zone_metrics;

-- ============================================================
-- v_story2_vacancy_by_zone_trend
-- One row per (zone, period): vacancy rate across the real 6-year span,
-- Combined dwelling types, Total bedroom type. Zone 7 (South Essex
-- County) has no rows before Oct-23 -- CMHC only began publishing it
-- then (docs/rms_historical_extraction.md) -- so its earlier periods are
-- absent, not zero. Zone 5 (Amherstburg) has NULL vacancy for Oct-22 and
-- Oct-24 (suppressed by CMHC for sample size); those rows stay NULL so a
-- chart shows a gap rather than a fabricated 0.0.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_vacancy_by_zone_trend AS
SELECT
    z.zone_label,
    p.period_label,
    p.period_year,
    f.value AS vacancy_rate_pct,
    f.reliability_letter
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'vacancy_rate'
  AND z.zone_level = 'zone'
  AND d.dwelling_type_label = 'Combined'
  AND b.bedroom_type_label = 'Total';

-- ============================================================
-- v_story2_zone_explanation
-- One row per zone (Oct-25, Combined dwelling types, Total bedroom type):
-- the zone's own figures, the same figures for Windsor CMA, the zone's
-- rank, and plain-language sentences built from those numbers. Feeds the
-- Story 2 dashboard's explanation panel (a Handlebars chart). Because it
-- has a zone_label column, the panel is filtered by the Zone native filter
-- and by cross-filters from the zone charts, so it describes whatever zone
-- the user selected; with no selection it receives all 7 rows and shows
-- the Windsor-wide overview instead.
--
-- Every number and every comparison word ("above", "tighter", ...) is
-- computed here from fact_rental_market; nothing is typed in by hand.
-- "About the same" bands: +/-2% for rent, +/-0.3 points for vacancy and
-- turnover, so rounding noise is not described as a difference.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_zone_explanation AS
WITH base AS (
    SELECT
        z.zone_label,
        z.zone_level,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-25') AS rent,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-24') AS rent_prev,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-25') AS rent_grade,
        MAX(f.value) FILTER (WHERE f.metric_type = 'vacancy_rate' AND p.period_label = 'Oct-25') AS vacancy,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'vacancy_rate' AND p.period_label = 'Oct-25') AS vacancy_grade,
        MAX(f.value) FILTER (WHERE f.metric_type = 'universe' AND p.period_label = 'Oct-25') AS units,
        MAX(f.value) FILTER (WHERE f.metric_type = 'turnover_rate' AND p.period_label = 'Oct-25') AS turnover
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_level IN ('zone', 'cma_total')
      AND d.dwelling_type_label = 'Combined'
      AND b.bedroom_type_label = 'Total'
      AND p.period_label IN ('Oct-24', 'Oct-25')
      AND f.metric_type IN ('average_rent', 'vacancy_rate', 'universe', 'turnover_rate')
    GROUP BY z.zone_label, z.zone_level
),
cma AS (
    SELECT rent AS cma_rent, vacancy AS cma_vacancy, units AS cma_units, turnover AS cma_turnover
    FROM base WHERE zone_level = 'cma_total'
),
zones AS (
    SELECT
        b.*,
        c.*,
        RANK() OVER (ORDER BY b.rent DESC NULLS LAST) AS rent_rank,
        COUNT(*) OVER () AS zone_count,
        FIRST_VALUE(b.zone_label) OVER (ORDER BY b.rent DESC NULLS LAST) AS priciest_zone,
        FIRST_VALUE(b.rent) OVER (ORDER BY b.rent DESC NULLS LAST) AS priciest_rent,
        FIRST_VALUE(b.zone_label) OVER (ORDER BY b.rent ASC NULLS LAST) AS cheapest_zone,
        FIRST_VALUE(b.rent) OVER (ORDER BY b.rent ASC NULLS LAST) AS cheapest_rent,
        FIRST_VALUE(b.zone_label) OVER (ORDER BY b.vacancy ASC NULLS LAST) AS tightest_zone,
        FIRST_VALUE(b.vacancy) OVER (ORDER BY b.vacancy ASC NULLS LAST) AS tightest_vacancy,
        FIRST_VALUE(b.zone_label) OVER (ORDER BY b.units DESC NULLS LAST) AS largest_zone,
        FIRST_VALUE(b.units) OVER (ORDER BY b.units DESC NULLS LAST) AS largest_units
    FROM base b CROSS JOIN cma c
    WHERE b.zone_level = 'zone'
)
SELECT
    zone_label,
    'Oct-25'::text AS period_label,
    rent AS average_rent,
    vacancy AS vacancy_rate_pct,
    units AS rental_units,
    turnover AS turnover_rate_pct,
    rent_grade,
    vacancy_grade,
    rent_rank,
    zone_count,
    -- Display text, formatted here so the panel template needs no helpers.
    TO_CHAR(rent, 'FM$9,999') AS rent_text,
    TO_CHAR(vacancy, 'FM990.0') || '%' AS vacancy_text,
    TO_CHAR(units, 'FM99,999') AS units_text,
    TO_CHAR(ROUND(100.0 * units / NULLIF(cma_units, 0), 1), 'FM990.0') || '%' AS share_text,
    TO_CHAR(turnover, 'FM990.0') || '%' AS turnover_text,
    TO_CHAR(cma_rent, 'FM$9,999') AS cma_rent_text,
    TO_CHAR(cma_vacancy, 'FM990.0') || '%' AS cma_vacancy_text,
    TO_CHAR(cma_units, 'FM99,999') AS cma_units_text,
    TO_CHAR(cma_turnover, 'FM990.0') || '%' AS cma_turnover_text,
    priciest_zone,
    TO_CHAR(priciest_rent, 'FM$9,999') AS priciest_rent_text,
    cheapest_zone,
    TO_CHAR(cheapest_rent, 'FM$9,999') AS cheapest_rent_text,
    tightest_zone,
    TO_CHAR(tightest_vacancy, 'FM990.0') || '%' AS tightest_vacancy_text,
    largest_zone,
    TO_CHAR(largest_units, 'FM99,999') AS largest_units_text,

    CASE
        WHEN rent IS NULL THEN 'CMHC did not publish an average rent for this zone.'
        WHEN rent > cma_rent * 1.02 THEN
            'Rent averages ' || TO_CHAR(rent, 'FM$9,999') || ' a month, ' || TO_CHAR(rent - cma_rent, 'FM$9,999')
            || ' (' || TO_CHAR(ROUND(100.0 * (rent - cma_rent) / cma_rent), 'FM990') || '%) above the Windsor average of '
            || TO_CHAR(cma_rent, 'FM$9,999') || '.'
        WHEN rent < cma_rent * 0.98 THEN
            'Rent averages ' || TO_CHAR(rent, 'FM$9,999') || ' a month, ' || TO_CHAR(cma_rent - rent, 'FM$9,999')
            || ' (' || TO_CHAR(ROUND(100.0 * (cma_rent - rent) / cma_rent), 'FM990') || '%) below the Windsor average of '
            || TO_CHAR(cma_rent, 'FM$9,999') || '.'
        ELSE
            'Rent averages ' || TO_CHAR(rent, 'FM$9,999') || ' a month, about the same as the Windsor average of '
            || TO_CHAR(cma_rent, 'FM$9,999') || '.'
    END
    || CASE
        WHEN rent IS NULL THEN ''
        WHEN rent_rank = 1 THEN ' It is the most expensive of the ' || zone_count || ' zones.'
        WHEN rent_rank = zone_count THEN ' It is the least expensive of the ' || zone_count || ' zones.'
        ELSE ' It ranks ' || rent_rank || ' of ' || zone_count || ' zones, from most to least expensive.'
    END AS rent_sentence,

    CASE
        WHEN rent IS NULL OR rent_prev IS NULL THEN ''
        WHEN rent > rent_prev THEN
            'That average is ' || TO_CHAR(rent - rent_prev, 'FM$9,999') || ' ('
            || TO_CHAR(ROUND(100.0 * (rent - rent_prev) / rent_prev, 1), 'FM990.0') || '%) higher than in October 2024.'
        WHEN rent < rent_prev THEN
            'That average is ' || TO_CHAR(rent_prev - rent, 'FM$9,999') || ' ('
            || TO_CHAR(ROUND(100.0 * (rent_prev - rent) / rent_prev, 1), 'FM990.0') || '%) lower than in October 2024.'
        ELSE 'That average is unchanged from October 2024.'
    END AS rent_change_sentence,

    CASE
        WHEN vacancy IS NULL THEN 'CMHC did not publish a vacancy rate for this zone.'
        WHEN vacancy < cma_vacancy - 0.3 THEN
            TO_CHAR(vacancy, 'FM990.0') || '% of units were vacant, below the Windsor rate of '
            || TO_CHAR(cma_vacancy, 'FM990.0') || '%: a tighter market, with fewer units free for people looking to move.'
        WHEN vacancy > cma_vacancy + 0.3 THEN
            TO_CHAR(vacancy, 'FM990.0') || '% of units were vacant, above the Windsor rate of '
            || TO_CHAR(cma_vacancy, 'FM990.0') || '%: more units are free here, so renters have more choice.'
        ELSE
            TO_CHAR(vacancy, 'FM990.0') || '% of units were vacant, about the same as the Windsor rate of '
            || TO_CHAR(cma_vacancy, 'FM990.0') || '%.'
    END AS vacancy_sentence,

    'The zone has ' || TO_CHAR(units, 'FM99,999') || ' purpose-built rental units, '
        || TO_CHAR(ROUND(100.0 * units / NULLIF(cma_units, 0), 1), 'FM990.0') || '% of Windsor''s '
        || TO_CHAR(cma_units, 'FM99,999') || '.' AS stock_sentence,

    CASE
        WHEN turnover IS NULL THEN ''
        WHEN turnover > cma_turnover + 0.3 THEN
            TO_CHAR(turnover, 'FM990.0') || '% of units changed tenants in the past year, more often than the Windsor rate of '
            || TO_CHAR(cma_turnover, 'FM990.0') || '%.'
        WHEN turnover < cma_turnover - 0.3 THEN
            TO_CHAR(turnover, 'FM990.0') || '% of units changed tenants in the past year, less often than the Windsor rate of '
            || TO_CHAR(cma_turnover, 'FM990.0') || '%: tenants here tend to stay longer.'
        ELSE
            TO_CHAR(turnover, 'FM990.0') || '% of units changed tenants in the past year, about the Windsor rate of '
            || TO_CHAR(cma_turnover, 'FM990.0') || '%.'
    END AS turnover_sentence,

    CASE
        WHEN rent_grade = 'd' OR vacancy_grade = 'd' THEN
            'CMHC grades at least one of these figures "d" (fair): read it with caution.'
        ELSE ''
    END AS reliability_note,

    -- ---- Added for the restructured panel (appended so existing columns keep their order) ----
    -- Short "vs Windsor" labels for the Key Numbers tiles.
    CASE
        WHEN rent IS NULL THEN 'no figure'
        WHEN rent > cma_rent THEN '+' || TO_CHAR(rent - cma_rent, 'FM$9,999') || ' vs Windsor'
        WHEN rent < cma_rent THEN '−' || TO_CHAR(cma_rent - rent, 'FM$9,999') || ' vs Windsor'
        ELSE 'same as Windsor'
    END AS rent_vs_text,
    CASE
        WHEN vacancy IS NULL THEN 'no figure'
        WHEN vacancy > cma_vacancy THEN '+' || TO_CHAR(vacancy - cma_vacancy, 'FM990.0') || ' pts vs Windsor'
        WHEN vacancy < cma_vacancy THEN '−' || TO_CHAR(cma_vacancy - vacancy, 'FM990.0') || ' pts vs Windsor'
        ELSE 'same as Windsor'
    END AS vacancy_vs_text,
    CASE
        WHEN turnover IS NULL THEN 'no figure'
        WHEN turnover > cma_turnover THEN '+' || TO_CHAR(turnover - cma_turnover, 'FM990.0') || ' pts vs Windsor'
        WHEN turnover < cma_turnover THEN '−' || TO_CHAR(cma_turnover - turnover, 'FM990.0') || ' pts vs Windsor'
        ELSE 'same as Windsor'
    END AS turnover_vs_text,
    TO_CHAR(ROUND(100.0 * units / NULLIF(cma_units, 0), 1), 'FM990.0') || '% of Windsor''s units' AS units_vs_text,
    -- Rank labels for the Zone Overview.
    CASE
        WHEN rent IS NULL THEN 'Rent not published'
        WHEN rent_rank = 1 THEN 'Most expensive of ' || zone_count || ' zones'
        WHEN rent_rank = zone_count THEN 'Least expensive of ' || zone_count || ' zones'
        ELSE 'Rent rank ' || rent_rank || ' of ' || zone_count
    END AS rank_text,
    RANK() OVER (ORDER BY units DESC NULLS LAST) || ' of ' || zone_count || ' by number of rental units' AS size_rank_text,
    -- Short bullets for What This Means.
    CASE
        WHEN rent IS NULL THEN 'CMHC did not publish an average rent for this zone.'
        WHEN rent > cma_rent * 1.02 THEN 'Rent is ' || TO_CHAR(ROUND(100.0 * (rent - cma_rent) / cma_rent), 'FM990') || '% above the Windsor average.'
        WHEN rent < cma_rent * 0.98 THEN 'Rent is ' || TO_CHAR(ROUND(100.0 * (cma_rent - rent) / cma_rent), 'FM990') || '% below the Windsor average.'
        ELSE 'Rent is about the Windsor average.'
    END AS rent_short,
    CASE
        WHEN rent IS NULL OR rent_prev IS NULL THEN ''
        WHEN rent > rent_prev THEN 'Up ' || TO_CHAR(ROUND(100.0 * (rent - rent_prev) / rent_prev, 1), 'FM990.0') || '% from October 2024.'
        WHEN rent < rent_prev THEN 'Down ' || TO_CHAR(ROUND(100.0 * (rent_prev - rent) / rent_prev, 1), 'FM990.0') || '% from October 2024.'
        ELSE 'Unchanged from October 2024.'
    END AS rent_change_short,
    CASE
        WHEN vacancy IS NULL THEN 'CMHC did not publish a vacancy rate for this zone.'
        WHEN vacancy < cma_vacancy - 0.3 THEN 'Tighter than average: fewer units are free to rent.'
        WHEN vacancy > cma_vacancy + 0.3 THEN 'Looser than average: renters have more units to choose from.'
        ELSE 'Vacancy is about the Windsor average.'
    END AS vacancy_short,
    CASE
        WHEN turnover IS NULL THEN ''
        WHEN turnover > cma_turnover + 0.3 THEN 'Tenants move more often than average.'
        WHEN turnover < cma_turnover - 0.3 THEN 'Tenants stay longer than average.'
        ELSE 'Tenants move about as often as the Windsor average.'
    END AS turnover_short,
    -- One-line Key Takeaway, from the rent and vacancy comparisons.
    CASE
        WHEN rent IS NULL OR vacancy IS NULL THEN
            'Some figures for this zone are not published, so compare it with care.'
        WHEN rent > cma_rent * 1.02 AND vacancy < cma_vacancy - 0.3 THEN
            'Pricier and tighter than Windsor overall: harder for renters to find a unit at the average rent.'
        WHEN rent > cma_rent * 1.02 AND vacancy > cma_vacancy + 0.3 THEN
            'Pricier than Windsor overall, but with more vacant units to choose from.'
        WHEN rent > cma_rent * 1.02 THEN
            'Pricier than Windsor overall, with about average vacancy.'
        WHEN rent < cma_rent * 0.98 AND vacancy > cma_vacancy + 0.3 THEN
            'Cheaper and easier to find a unit than in Windsor overall.'
        WHEN rent < cma_rent * 0.98 AND vacancy < cma_vacancy - 0.3 THEN
            'Cheaper than Windsor overall, but units are scarce.'
        WHEN rent < cma_rent * 0.98 THEN
            'Cheaper than Windsor overall, with about average vacancy.'
        WHEN vacancy < cma_vacancy - 0.3 THEN
            'Average rent, but tighter than Windsor overall.'
        WHEN vacancy > cma_vacancy + 0.3 THEN
            'Average rent, with more vacant units than Windsor overall.'
        ELSE 'Close to the Windsor average on both rent and vacancy.'
    END AS takeaway,
    -- Windsor-wide takeaway for the overview (same on every row).
    'Rents range from ' || TO_CHAR(cheapest_rent, 'FM$9,999') || ' in ' || cheapest_zone || ' to '
        || TO_CHAR(priciest_rent, 'FM$9,999') || ' in ' || priciest_zone || ', a gap of '
        || TO_CHAR(priciest_rent - cheapest_rent, 'FM$9,999') || ' a month.' AS overview_takeaway
FROM zones;

-- ============================================================
-- v_story2_zone_bedroom_explanation
-- The explanation-panel figures for every zone AND unit size (Studio,
-- 1 Bedroom, 2 Bedroom, 3 Bedroom +, and Total = all unit sizes), October
-- 2025, apartments and row houses combined. Each zone is compared with
-- Windsor CMA's figure for the SAME unit size, and ranks are within that
-- unit size. Same rules as v_story2_zone_explanation (which it extends to
-- unit sizes; that view is unchanged): every number, comparison word and
-- takeaway is computed here from fact_rental_market. CMHC suppresses many
-- zone x unit-size cells; those come through as NULL and the text says
-- "not published" instead of guessing.
--
-- The Story 2 panel reads it through a small Superset virtual dataset
-- (story2_panel_by_unit_size, built by etl/build_story2_dashboard.py)
-- that keeps the unit size chosen in the Bedroom Type filter, or 'Total'
-- when none is chosen, so the panel recalculates when the filter changes.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story2_zone_bedroom_explanation AS
WITH base AS (
    SELECT
        z.zone_label,
        z.zone_level,
        b.bedroom_type_label,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-25') AS rent,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-24') AS rent_prev,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'average_rent' AND p.period_label = 'Oct-25') AS rent_grade,
        MAX(f.value) FILTER (WHERE f.metric_type = 'vacancy_rate' AND p.period_label = 'Oct-25') AS vacancy,
        MAX(f.reliability_letter) FILTER (WHERE f.metric_type = 'vacancy_rate' AND p.period_label = 'Oct-25') AS vacancy_grade,
        MAX(f.value) FILTER (WHERE f.metric_type = 'universe' AND p.period_label = 'Oct-25') AS units,
        MAX(f.value) FILTER (WHERE f.metric_type = 'turnover_rate' AND p.period_label = 'Oct-25') AS turnover
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_level IN ('zone', 'cma_total')
      AND d.dwelling_type_label = 'Combined'
      AND p.period_label IN ('Oct-24', 'Oct-25')
      AND f.metric_type IN ('average_rent', 'vacancy_rate', 'universe', 'turnover_rate')
      AND f.income_band_key IS NULL
    GROUP BY z.zone_label, z.zone_level, b.bedroom_type_label
),
cma AS (
    SELECT bedroom_type_label,
           rent AS cma_rent, vacancy AS cma_vacancy, units AS cma_units, turnover AS cma_turnover
    FROM base WHERE zone_level = 'cma_total'
),
zones AS (
    SELECT
        b.*,
        c.cma_rent, c.cma_vacancy, c.cma_units, c.cma_turnover,
        CASE WHEN b.rent IS NULL THEN NULL
             ELSE RANK() OVER (PARTITION BY b.bedroom_type_label, b.rent IS NULL ORDER BY b.rent DESC) END AS rent_rank,
        COUNT(b.rent) OVER (PARTITION BY b.bedroom_type_label) AS rent_zone_count,
        RANK() OVER (PARTITION BY b.bedroom_type_label ORDER BY b.units DESC NULLS LAST) AS size_rank,
        COUNT(*) OVER (PARTITION BY b.bedroom_type_label) AS zone_count,
        FIRST_VALUE(b.zone_label) OVER w_rent_desc AS priciest_zone,
        FIRST_VALUE(b.rent) OVER w_rent_desc AS priciest_rent,
        FIRST_VALUE(b.zone_label) OVER w_rent_asc AS cheapest_zone,
        FIRST_VALUE(b.rent) OVER w_rent_asc AS cheapest_rent,
        FIRST_VALUE(b.zone_label) OVER w_vac_asc AS tightest_zone,
        FIRST_VALUE(b.vacancy) OVER w_vac_asc AS tightest_vacancy,
        FIRST_VALUE(b.zone_label) OVER w_units_desc AS largest_zone,
        FIRST_VALUE(b.units) OVER w_units_desc AS largest_units
    FROM base b
    JOIN cma c ON c.bedroom_type_label = b.bedroom_type_label
    WHERE b.zone_level = 'zone'
    WINDOW
        w_rent_desc AS (PARTITION BY b.bedroom_type_label ORDER BY b.rent DESC NULLS LAST),
        w_rent_asc AS (PARTITION BY b.bedroom_type_label ORDER BY b.rent ASC NULLS LAST),
        w_vac_asc AS (PARTITION BY b.bedroom_type_label ORDER BY b.vacancy ASC NULLS LAST),
        w_units_desc AS (PARTITION BY b.bedroom_type_label ORDER BY b.units DESC NULLS LAST)
)
SELECT
    zone_label,
    bedroom_type_label,
    CASE WHEN bedroom_type_label = 'Total' THEN 'all unit sizes'
         WHEN bedroom_type_label = 'Studio' THEN 'studio units'
         WHEN bedroom_type_label = '3 Bedroom +' THEN '3-bedroom+ units'
         ELSE LOWER(REPLACE(bedroom_type_label, ' Bedroom', '-bedroom')) || ' units' END AS unit_label,
    rent AS average_rent,
    -- Display text (formatted here so the panel template needs no helpers).
    COALESCE(TO_CHAR(rent, 'FM$9,999'), 'n/p') AS rent_text,
    COALESCE(TO_CHAR(vacancy, 'FM990.0') || '%', 'n/p') AS vacancy_text,
    COALESCE(TO_CHAR(units, 'FM99,999'), 'n/p') AS units_text,
    COALESCE(TO_CHAR(turnover, 'FM990.0') || '%', 'n/p') AS turnover_text,
    COALESCE(TO_CHAR(cma_rent, 'FM$9,999'), 'n/p') AS cma_rent_text,
    COALESCE(TO_CHAR(cma_vacancy, 'FM990.0') || '%', 'n/p') AS cma_vacancy_text,
    COALESCE(TO_CHAR(cma_units, 'FM99,999'), 'n/p') AS cma_units_text,
    COALESCE(TO_CHAR(cma_turnover, 'FM990.0') || '%', 'n/p') AS cma_turnover_text,
    COALESCE(priciest_zone, 'not published') AS priciest_zone,
    COALESCE(TO_CHAR(priciest_rent, 'FM$9,999'), 'n/p') AS priciest_rent_text,
    COALESCE(cheapest_zone, 'not published') AS cheapest_zone,
    COALESCE(TO_CHAR(cheapest_rent, 'FM$9,999'), 'n/p') AS cheapest_rent_text,
    COALESCE(tightest_zone, 'not published') AS tightest_zone,
    COALESCE(TO_CHAR(tightest_vacancy, 'FM990.0') || '%', 'n/p') AS tightest_vacancy_text,
    largest_zone,
    TO_CHAR(largest_units, 'FM99,999') AS largest_units_text,

    -- "vs Windsor" labels for the Key Numbers tiles
    CASE
        WHEN rent IS NULL OR cma_rent IS NULL THEN 'not published'
        WHEN rent > cma_rent THEN '+' || TO_CHAR(rent - cma_rent, 'FM$9,999') || ' vs Windsor'
        WHEN rent < cma_rent THEN '−' || TO_CHAR(cma_rent - rent, 'FM$9,999') || ' vs Windsor'
        ELSE 'same as Windsor'
    END AS rent_vs_text,
    CASE
        WHEN vacancy IS NULL OR cma_vacancy IS NULL THEN 'not published'
        WHEN vacancy > cma_vacancy THEN '+' || TO_CHAR(vacancy - cma_vacancy, 'FM990.0') || ' pts vs Windsor'
        WHEN vacancy < cma_vacancy THEN '−' || TO_CHAR(cma_vacancy - vacancy, 'FM990.0') || ' pts vs Windsor'
        ELSE 'same as Windsor'
    END AS vacancy_vs_text,
    CASE
        WHEN turnover IS NULL OR cma_turnover IS NULL THEN 'not published'
        WHEN turnover > cma_turnover THEN '+' || TO_CHAR(turnover - cma_turnover, 'FM990.0') || ' pts vs Windsor'
        WHEN turnover < cma_turnover THEN '−' || TO_CHAR(cma_turnover - turnover, 'FM990.0') || ' pts vs Windsor'
        ELSE 'same as Windsor'
    END AS turnover_vs_text,
    COALESCE(TO_CHAR(ROUND(100.0 * units / NULLIF(cma_units, 0), 1), 'FM990.0') || '% of Windsor''s units', 'share not published') AS units_vs_text,
    CASE
        WHEN rent IS NULL THEN 'Rent not published'
        WHEN rent_rank = 1 THEN 'Most expensive of ' || rent_zone_count || ' zones'
        WHEN rent_rank = rent_zone_count THEN 'Least expensive of ' || rent_zone_count || ' zones'
        ELSE 'Rent rank ' || rent_rank || ' of ' || rent_zone_count
    END AS rank_text,
    size_rank || ' of ' || zone_count || ' by number of units' AS size_rank_text,

    -- What This Means: one bullet per measure, each with its numbers
    CASE
        WHEN rent IS NULL THEN 'Rent: CMHC did not publish an average rent here.'
        WHEN cma_rent IS NULL THEN 'Rent: ' || TO_CHAR(rent, 'FM$9,999') || ' a month (no Windsor figure to compare).'
        WHEN rent > cma_rent * 1.02 THEN 'Rent: ' || TO_CHAR(rent, 'FM$9,999') || ' a month, '
            || TO_CHAR(ROUND(100.0 * (rent - cma_rent) / cma_rent), 'FM990') || '% above Windsor''s ' || TO_CHAR(cma_rent, 'FM$9,999') || '.'
        WHEN rent < cma_rent * 0.98 THEN 'Rent: ' || TO_CHAR(rent, 'FM$9,999') || ' a month, '
            || TO_CHAR(ROUND(100.0 * (cma_rent - rent) / cma_rent), 'FM990') || '% below Windsor''s ' || TO_CHAR(cma_rent, 'FM$9,999') || '.'
        ELSE 'Rent: ' || TO_CHAR(rent, 'FM$9,999') || ' a month, about Windsor''s ' || TO_CHAR(cma_rent, 'FM$9,999') || '.'
    END
    || CASE
        WHEN rent IS NULL OR rent_prev IS NULL THEN ''
        WHEN rent > rent_prev THEN ' Up ' || TO_CHAR(ROUND(100.0 * (rent - rent_prev) / rent_prev, 1), 'FM990.0') || '% since Oct 2024.'
        WHEN rent < rent_prev THEN ' Down ' || TO_CHAR(ROUND(100.0 * (rent_prev - rent) / rent_prev, 1), 'FM990.0') || '% since Oct 2024.'
        ELSE ' Unchanged since Oct 2024.'
    END AS rent_bullet,
    CASE
        WHEN vacancy IS NULL THEN 'Vacancy: CMHC did not publish a vacancy rate here.'
        WHEN cma_vacancy IS NULL THEN 'Vacancy: ' || TO_CHAR(vacancy, 'FM990.0') || '% (no Windsor figure to compare).'
        WHEN vacancy < cma_vacancy - 0.3 THEN 'Vacancy: ' || TO_CHAR(vacancy, 'FM990.0') || '% vs Windsor''s '
            || TO_CHAR(cma_vacancy, 'FM990.0') || '%: tighter, fewer units free to rent.'
        WHEN vacancy > cma_vacancy + 0.3 THEN 'Vacancy: ' || TO_CHAR(vacancy, 'FM990.0') || '% vs Windsor''s '
            || TO_CHAR(cma_vacancy, 'FM990.0') || '%: looser, more choice for renters.'
        ELSE 'Vacancy: ' || TO_CHAR(vacancy, 'FM990.0') || '%, about Windsor''s ' || TO_CHAR(cma_vacancy, 'FM990.0') || '%.'
    END AS vacancy_bullet,
    CASE
        WHEN units IS NULL THEN 'Stock: CMHC did not publish a unit count here.'
        ELSE 'Stock: ' || TO_CHAR(units, 'FM99,999') || ' units, '
            || TO_CHAR(ROUND(100.0 * units / NULLIF(cma_units, 0), 1), 'FM990.0') || '% of Windsor''s '
            || TO_CHAR(cma_units, 'FM99,999') || ' (' || size_rank || ' of ' || zone_count || ' zones).'
    END AS stock_bullet,
    CASE
        WHEN turnover IS NULL THEN 'Turnover: CMHC did not publish a turnover rate here.'
        WHEN cma_turnover IS NULL THEN 'Turnover: ' || TO_CHAR(turnover, 'FM990.0') || '% (no Windsor figure to compare).'
        WHEN turnover > cma_turnover + 0.3 THEN 'Turnover: ' || TO_CHAR(turnover, 'FM990.0') || '% vs Windsor''s '
            || TO_CHAR(cma_turnover, 'FM990.0') || '%: tenants move more often.'
        WHEN turnover < cma_turnover - 0.3 THEN 'Turnover: ' || TO_CHAR(turnover, 'FM990.0') || '% vs Windsor''s '
            || TO_CHAR(cma_turnover, 'FM990.0') || '%: tenants stay longer.'
        ELSE 'Turnover: ' || TO_CHAR(turnover, 'FM990.0') || '%, about Windsor''s ' || TO_CHAR(cma_turnover, 'FM990.0') || '%.'
    END AS turnover_bullet,
    CASE
        WHEN rent_grade = 'd' OR vacancy_grade = 'd' THEN
            'CMHC grades at least one of these figures "d" (fair): read it with caution.'
        ELSE ''
    END AS reliability_note,

    -- Key Takeaway, from the rent and vacancy comparisons
    CASE
        WHEN rent IS NULL OR vacancy IS NULL OR cma_rent IS NULL OR cma_vacancy IS NULL THEN
            'Some figures for these units are not published, so compare this zone with care.'
        WHEN rent > cma_rent * 1.02 AND vacancy < cma_vacancy - 0.3 THEN
            'Pricier and tighter than Windsor overall: harder for renters to find a unit at the average rent.'
        WHEN rent > cma_rent * 1.02 AND vacancy > cma_vacancy + 0.3 THEN
            'Pricier than Windsor overall, but with more vacant units to choose from.'
        WHEN rent > cma_rent * 1.02 THEN 'Pricier than Windsor overall, with about average vacancy.'
        WHEN rent < cma_rent * 0.98 AND vacancy > cma_vacancy + 0.3 THEN
            'Cheaper and easier to find a unit than in Windsor overall.'
        WHEN rent < cma_rent * 0.98 AND vacancy < cma_vacancy - 0.3 THEN
            'Cheaper than Windsor overall, but units are scarce.'
        WHEN rent < cma_rent * 0.98 THEN 'Cheaper than Windsor overall, with about average vacancy.'
        WHEN vacancy < cma_vacancy - 0.3 THEN 'Average rent, but tighter than Windsor overall.'
        WHEN vacancy > cma_vacancy + 0.3 THEN 'Average rent, with more vacant units than Windsor overall.'
        ELSE 'Close to the Windsor average on both rent and vacancy.'
    END AS takeaway,
    CASE
        WHEN priciest_rent IS NULL THEN 'CMHC did not publish zone rents for these units.'
        WHEN priciest_zone = cheapest_zone THEN 'Only one zone has a published rent for these units.'
        ELSE 'Rents range from ' || TO_CHAR(cheapest_rent, 'FM$9,999') || ' in ' || cheapest_zone || ' to '
            || TO_CHAR(priciest_rent, 'FM$9,999') || ' in ' || priciest_zone || ', a gap of '
            || TO_CHAR(priciest_rent - cheapest_rent, 'FM$9,999') || ' a month.'
    END AS overview_takeaway
FROM zones;
