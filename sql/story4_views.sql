-- SQL views for Story 4 ("How does Windsor compare to similar markets?"):
-- Windsor vs. comparator CMA rents, vacancy, and affordability-gap index
-- values. Built on top of warehouse.fact_rental_market (the real,
-- verified data from etl/load_rental_market_facts() and
-- etl/load_rms_canada_comparison_facts() -- see
-- docs/conceptual_er_model.md and docs/affordability_gap_index.md).
--
-- All 4 markets (Windsor + the 3 comparator CMAs) are reported here at
-- the same scope -- apartment-only, Oct-24/Oct-25 -- so the comparison is
-- apples-to-apples. Windsor's richer Combined-dwelling-type /
-- all-bedroom-type data (zone-level, Table 3.1.8 quintile bridge, etc.)
-- is still in fact_rental_market but is NOT what these views surface --
-- that data has no equivalent for the comparator CMAs, so mixing it in
-- here would make Windsor look artificially different from the
-- comparators rather than genuinely different.

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
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'vacancy_rate'
  AND z.zone_level IN ('cma_total', 'comparator_cma')
  AND b.bedroom_type_label = 'Total'
  AND d.dwelling_type_label = 'Apartment';

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
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'average_rent'
  AND z.zone_level IN ('cma_total', 'comparator_cma')
  AND b.bedroom_type_label = '2 Bedroom'
  AND d.dwelling_type_label = 'Apartment';

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
FROM warehouse.fact_rental_market f
JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
JOIN warehouse.dim_period p ON p.period_key = f.period_key
JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
WHERE f.metric_type = 'pct_change_rent'
  AND z.zone_level IN ('cma_total', 'comparator_cma')
  AND b.bedroom_type_label = '2 Bedroom'
  AND d.dwelling_type_label = 'Apartment'
  AND p.period_label = 'Oct-25';  -- the Oct-24-to-25 change, tagged to its ending period
