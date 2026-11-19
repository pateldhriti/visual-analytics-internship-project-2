-- SQL views for Story 4 ("How does Windsor compare to similar markets?"):
-- Windsor vs. comparator CMA rents, vacancy, and affordability-gap index
-- values. Built on top of warehouse.fact_rental_market_comparison (the
-- real, verified data from etl/load_rms_canada_comparison_facts() --
-- see docs/conceptual_er_model.md and docs/affordability_gap_index.md).
-- This is its own fact table, separate from fact_rental_market, because
-- it comes from a separate source workbook (CMHC Canada RMS 2025, not
-- CMHC Windsor RMS 2025) -- see sql/warehouse_schema.sql's comment on
-- fact_rental_market_comparison for why.
--
-- All 5 markets (Windsor + the 4 comparator CMAs) are reported here at
-- the same scope -- apartment-only, Oct-24/Oct-25 -- so the comparison is
-- apples-to-apples. Windsor's richer Combined-dwelling-type /
-- all-bedroom-type data (zone-level, Table 3.1.8 quintile bridge, etc.)
-- is still in fact_rental_market but is NOT what these views surface --
-- that data has no equivalent for the comparator CMAs, so mixing it in
-- here would make Windsor look artificially different from the
-- comparators rather than genuinely different.
--
-- Real bug found and fixed here: Windsor's own vacancy_rate/average_rent
-- rows are deliberately EXCLUDED from fact_rental_market_comparison at
-- load time (etl/load_rms_canada_comparison_facts(), see
-- docs/data_quality_report.md's "Known exclusion" note) -- they'd
-- otherwise duplicate the same figures fact_rental_market already
-- carries. v_story4_vacancy_comparison and v_story4_rent_comparison were
-- querying fact_rental_market_comparison alone, so despite this header's
-- own "all 5 markets" claim, Windsor's row was silently absent from both
-- (confirmed directly: zone_level = 'cma_total' never appears in either
-- view's live output) -- the same gap class already fixed for
-- v_dashboard1_cma_benchmark, now fixed at its actual source instead of
-- worked around elsewhere. pct_change_rent and turnover_rate were never
-- affected -- those 2 metrics were NOT excluded for Windsor at load
-- time, so v_story4_affordability_gap already had its real Windsor row
-- all along (confirmed directly, not assumed).

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- v_story4_vacancy_comparison
-- One row per (market, period): apartment vacancy rate, Total bedroom type.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story4_vacancy_comparison AS
SELECT
    z.zone_label AS market,
    z.zone_level AS market_type,  -- 'cma_total' (Windsor) | 'comparator_cma'
    p.period_label,
    f.value AS vacancy_rate_pct,
    f.reliability_letter,
    f.yoy_trend
FROM warehouse.fact_rental_market_comparison f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'vacancy_rate'
  AND z.zone_level = 'comparator_cma'
  AND b.bedroom_type_label = 'Total'
  AND d.dwelling_type_label = 'Apartment'
UNION ALL
SELECT
    z.zone_label AS market,
    'cma_total' AS market_type,
    p.period_label,
    f.value AS vacancy_rate_pct,
    f.reliability_letter,
    f.yoy_trend
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'vacancy_rate'
  AND z.zone_label = 'Windsor CMA'
  AND b.bedroom_type_label = 'Total'
  AND d.dwelling_type_label = 'Apartment'
  AND p.period_label IN ('Oct-24', 'Oct-25');

-- ============================================================
-- v_story4_rent_comparison
-- One row per (market, period): average 2-bedroom apartment rent.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story4_rent_comparison AS
SELECT
    z.zone_label AS market,
    z.zone_level AS market_type,
    p.period_label,
    f.value AS average_rent_2br,
    f.reliability_letter
FROM warehouse.fact_rental_market_comparison f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'average_rent'
  AND z.zone_level = 'comparator_cma'
  AND b.bedroom_type_label = '2 Bedroom'
  AND d.dwelling_type_label = 'Apartment'
UNION ALL
SELECT
    z.zone_label AS market,
    'cma_total' AS market_type,
    p.period_label,
    f.value AS average_rent_2br,
    f.reliability_letter
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'average_rent'
  AND z.zone_label = 'Windsor CMA'
  AND b.bedroom_type_label = '2 Bedroom'
  AND d.dwelling_type_label = 'Apartment'
  AND p.period_label IN ('Oct-24', 'Oct-25');

-- ============================================================
-- v_story4_affordability_gap
-- One row per market: the real rent-growth side of the affordability-gap
-- index (docs/affordability_gap_index.md), Oct-24 -> Oct-25.
--
-- renter_income_growth_pct and affordability_gap_index are left as NULL,
-- NOT computed or estimated: no source this project has extracted
-- contains a renter/household income time series to compute a real
-- growth rate from (see docs/affordability_gap_index.md's "Limits"
-- section for exactly why, and what would close the gap). A placeholder
-- number here would be worse than an honest NULL -- it would look like
-- real data in a Superset chart with no way for a viewer to tell the
-- difference.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story4_affordability_gap AS
SELECT
    z.zone_label AS market,
    z.zone_level AS market_type,
    f.value AS rent_growth_pct,
    CAST(NULL AS NUMERIC) AS renter_income_growth_pct,
    CAST(NULL AS NUMERIC) AS affordability_gap_index,
    'Income growth not available -- see docs/affordability_gap_index.md' AS data_note
FROM warehouse.fact_rental_market_comparison f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'pct_change_rent'
  AND z.zone_level IN ('cma_total', 'comparator_cma')
  AND b.bedroom_type_label = '2 Bedroom'
  AND d.dwelling_type_label = 'Apartment'
  AND p.period_label = 'Oct-25';  -- the Oct-24-to-25 change, tagged to its ending period

-- ============================================================
-- v_story4_rent_history
-- One row per (city, year), 2015 onward: October average 2-bedroom rent
-- and vacancy rate (apartments and row houses, buildings of 3+ units),
-- Windsor and the four comparison cities. Source: CMHC's Rental Market
-- Survey as republished by StatCan (34-10-0133-01 rents, 34-10-0130-01
-- vacancy), loaded into fact_peer_cma_context by
-- etl/extract_peer_cma_context.py. CMHC's own Windsor download only goes
-- back to Oct-20, so these tables are what give the ten-year trend.
--
-- Scope differs from the Oct-25 bars above (apartments only, CMHC's
-- city-comparison workbook): rents here include row houses, so they are a
-- few dollars off those bars (Windsor Oct-25: $1,451 here, $1,454
-- apartments only). They match Story 2's Windsor figures, except Oct-22
-- ($1,194 here; Story 2 uses CMHC's later revision, $1,170).
-- rent_index_2015 = rent as % of the city's own 2015 rent, so cities
-- with different rent levels can be compared on growth alone.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story4_rent_history AS
WITH rent AS (
    SELECT cma_name, period_year, value AS average_rent_2br
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '34-10-0133-01' AND indicator = 'average_rent' AND category = '2 Bedroom'
),
vacancy AS (
    SELECT cma_name, period_year, value AS vacancy_rate
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '34-10-0130-01' AND indicator = 'vacancy_rate'
)
SELECT
    r.cma_name AS city,
    CASE r.cma_name
        WHEN 'Kitchener-Cambridge-Waterloo CMA' THEN 'Kitchener-Waterloo'
        WHEN 'St. Catharines-Niagara CMA' THEN 'St. Catharines'
        ELSE REPLACE(r.cma_name, ' CMA', '')
    END AS city_short,
    (r.cma_name = 'Windsor CMA') AS is_windsor,
    r.period_year,
    r.average_rent_2br,
    v.vacancy_rate,
    ROUND(100.0 * (r.average_rent_2br / LAG(r.average_rent_2br) OVER w - 1), 1) AS rent_change_pct,
    ROUND(100.0 * r.average_rent_2br / FIRST_VALUE(r.average_rent_2br) OVER w, 1) AS rent_index_2015,
    -- October of each survey year as a real date, for the trendline KPI tile.
    MAKE_DATE(r.period_year, 10, 1) AS period_date
FROM rent r
LEFT JOIN vacancy v ON v.cma_name = r.cma_name AND v.period_year = r.period_year
WINDOW w AS (PARTITION BY r.cma_name ORDER BY r.period_year);

-- ============================================================
-- v_story4_period_comparison
-- One row per city: the five years before the pandemic against the five
-- years from it (2015 to 2020 vs 2020 to 2025; each period is five
-- yearly rent increases). avg_rent_growth_* is the average yearly
-- increase (compound), so the two periods compare directly. Vacancy is
-- averaged over the Octobers in each period (2015-2020 and 2021-2025).
-- windsor_pct_of_peer_rent = Windsor's rent as % of the four comparison
-- cities' average (Windsor row only), to show whether the gap is closing.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story4_period_comparison AS
WITH h AS (
    SELECT * FROM warehouse.v_story4_rent_history
),
by_city AS (
    SELECT
        city,
        city_short,
        is_windsor,
        MAX(average_rent_2br) FILTER (WHERE period_year = 2015) AS rent_2015,
        MAX(average_rent_2br) FILTER (WHERE period_year = 2020) AS rent_2020,
        MAX(average_rent_2br) FILTER (WHERE period_year = 2025) AS rent_2025,
        ROUND(AVG(vacancy_rate) FILTER (WHERE period_year BETWEEN 2015 AND 2020), 1) AS avg_vacancy_2015_2020,
        ROUND(AVG(vacancy_rate) FILTER (WHERE period_year BETWEEN 2021 AND 2025), 1) AS avg_vacancy_2021_2025
    FROM h
    GROUP BY city, city_short, is_windsor
),
peer AS (
    SELECT AVG(rent_2015) AS peer_2015, AVG(rent_2025) AS peer_2025 FROM by_city WHERE NOT is_windsor
)
SELECT
    c.city,
    c.city_short,
    c.is_windsor,
    c.rent_2015,
    c.rent_2020,
    c.rent_2025,
    ROUND(100.0 * (POWER(c.rent_2020 / c.rent_2015, 1.0 / 5) - 1), 1) AS avg_rent_growth_2015_2020,
    ROUND(100.0 * (POWER(c.rent_2025 / c.rent_2020, 1.0 / 5) - 1), 1) AS avg_rent_growth_2020_2025,
    ROUND(100.0 * (c.rent_2025 / c.rent_2015 - 1), 1) AS rent_change_2015_2025,
    c.avg_vacancy_2015_2020,
    c.avg_vacancy_2021_2025,
    CASE WHEN c.is_windsor THEN ROUND(100.0 * c.rent_2015 / p.peer_2015, 1) END AS windsor_pct_of_peer_rent_2015,
    CASE WHEN c.is_windsor THEN ROUND(100.0 * c.rent_2025 / p.peer_2025, 1) END AS windsor_pct_of_peer_rent_2025
FROM by_city c
CROSS JOIN peer p;


-- ---------------------------------------------------------------------------
-- v_story4_cma_canada: every Canadian CMA in 2021 -- renter cost burden
-- (Census 2021, incomes for 2020), October 2021 2-bedroom apartment rent and
-- vacancy rate (apartments and row houses) -- for Story 4's "All Canadian
-- Cities, 2021" tab. Windsor and the four comparison cities are marked.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story4_cma_canada AS
SELECT
    cma_code,
    REPLACE(cma_name, ' - ', '-') AS city,
    CASE WHEN cma_code = '559' THEN 'Windsor'
         WHEN cma_code IN ('555', '537', '539', '541') THEN 'Comparison city'
         ELSE 'Other Canadian city' END AS city_group,
    (cma_code = '559') AS is_windsor,
    MAX(value) FILTER (WHERE indicator = 'renter_burden_pct') AS renter_burden_pct,
    -- CMHC Rental Market Survey, Canada, Table 1.0 (October 2021):
    -- 2-bedroom apartment rent and apartment vacancy
    MAX(value) FILTER (WHERE indicator = 'average_rent_2br_rms') AS rent_2br_apartments,
    MAX(value) FILTER (WHERE indicator = 'vacancy_rate_apartments') AS vacancy_rate_pct
FROM warehouse.fact_cma_canada
WHERE period_year = 2021
GROUP BY cma_code, cma_name
HAVING MAX(value) FILTER (WHERE indicator = 'average_rent_2br_rms') IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Story 4 tabs "Windsor in 2021" and "Since 2019, with Toronto". Rent:
-- October 2-bedroom, apartment structures (StatCan 34-10-0133-01); vacancy:
-- apartment structures, CMHC Rental Market Survey, Canada, 2019-2025
-- (Table 1.0); rental universe for 2021: the 2021 survey's Table 5.0;
-- renter households and renter cost burden: Census 2021. The 2019 lines
-- show Windsor, London, Hamilton, Kitchener-Waterloo and Toronto; the
-- 2021 table lists the same five.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story4_city_history AS
WITH cities AS (
    -- the short names of the ten-year lines (v_story4_rent_history.city_short)
    SELECT cma_code,
           CASE cma_code WHEN '541' THEN 'Kitchener-Waterloo' WHEN '539' THEN 'St. Catharines'
                         ELSE REPLACE(cma_name, ' - ', '-') END AS city
    FROM warehouse.fact_cma_canada
    WHERE cma_code IN ('559', '555', '537', '541', '535')
    GROUP BY cma_code, cma_name
),
yearly AS (
    SELECT c.city, c.cma_code, f.period_year,
           MAX(f.value) FILTER (WHERE f.indicator = 'average_rent_2br_rms') AS rent_2br_apartments,
           MAX(f.value) FILTER (WHERE f.indicator = 'vacancy_rate_apartments') AS vacancy_rate_pct
    FROM warehouse.fact_cma_canada f
    JOIN cities c ON c.cma_code = f.cma_code
    WHERE f.indicator IN ('average_rent_2br_rms', 'vacancy_rate_apartments') AND f.period_year >= 2019
    GROUP BY c.city, c.cma_code, f.period_year
)
SELECT
    city,
    (cma_code = '559') AS is_windsor,
    period_year,
    MAKE_DATE(period_year, 10, 1) AS period_date,
    rent_2br_apartments,
    ROUND(100.0 * rent_2br_apartments
          / FIRST_VALUE(rent_2br_apartments) OVER (PARTITION BY city ORDER BY period_year), 1)
        AS rent_index_2019,
    vacancy_rate_pct
FROM yearly;

CREATE OR REPLACE VIEW warehouse.v_story4_rental_supply_2021 AS
SELECT
    cma_name AS city,
    (cma_code = '559') AS is_windsor,
    MAX(value) FILTER (WHERE indicator = 'rental_universe') AS rental_universe,
    MAX(value) FILTER (WHERE indicator = 'renter_households') AS renter_households,
    ROUND(1000.0 * MAX(value) FILTER (WHERE indicator = 'rental_universe')
          / MAX(value) FILTER (WHERE indicator = 'renter_households'), 1) AS units_per_1000_renters,
    cma_code  -- the table's row order
FROM warehouse.fact_cma_canada
WHERE period_year = 2021 AND cma_code IN ('559', '555', '537', '541', '535')
GROUP BY cma_code, cma_name;

CREATE OR REPLACE VIEW warehouse.v_story4_windsor_2021 AS
SELECT
    MAX(value) FILTER (WHERE indicator = 'average_rent_2br_apartments') AS rent_2br_apartments,
    MAX(value) FILTER (WHERE indicator = 'renter_burden_pct') AS renter_burden_pct,
    MAX(value) FILTER (WHERE indicator = 'vacancy_rate_apartments' AND period_year = 2021)
        AS vacancy_rate_apartments_pct,
    ROUND(1000.0 * MAX(value) FILTER (WHERE indicator = 'rental_universe')
          / MAX(value) FILTER (WHERE indicator = 'renter_households'), 1) AS units_per_1000_renters
FROM warehouse.fact_cma_canada
WHERE cma_code = '559' AND period_year = 2021;
