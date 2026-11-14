-- =============================================================================
-- STORY 2 (HISTORY) -- WINDSOR RENTAL MARKET 2019-2025 (ADDITIVE)
-- Source: clean.rental_market_windsor_history only (Windsor CMA, private
-- apartments, CMHC RMS October surveys).
--
-- Applied on its own by etl/load_rental_history_to_postgres.py (CREATE OR
-- REPLACE: never drops the schema or the 31 existing views), and also run as
-- the last file of a full rebuild by etl/build_analysis_views.py.
--
-- Geography break: Windsor CMA is on the pre-2021-census boundary for
-- 2019-2021 and the 2021-census boundary for 2022-2025 (2022 is published on
-- both). Continuous series use is_primary_series = true only. A year-over-year
-- change is calculated only between two years on the SAME boundary; the
-- 2021 -> 2022 step crosses the break, so its change is NULL and flagged
-- (the like-for-like old-boundary 2021 -> 2022 change is given separately).
-- Rates: change in percentage points. Suppressed values stay NULL.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- analysis.story2_historical_series
-- Question: what does the full validated history contain, including both 2022
-- boundary versions and the rental universe?
-- Grain: one row per year x metric x geography_basis (all 32 rows).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW analysis.story2_historical_series AS
SELECT
    year,
    period_label,
    geography,
    geography_basis,
    is_primary_series,
    year = 2022                                AS is_geography_bridge_year,
    dwelling_scope,
    bedroom_type,
    metric,
    unit,
    value,
    value_status,
    reliability_code,
    yoy_trend,
    source_edition_year,
    source_workbook,
    source_table,
    source_cell
FROM clean.rental_market_windsor_history;

COMMENT ON VIEW analysis.story2_historical_series IS
    'Grain: year x metric x geography_basis (all rows, both 2022 boundaries). Full Windsor apartment history 2019-2025 with lineage.';


-- -----------------------------------------------------------------------------
-- Shared shape of the three continuous-series views (rent, vacancy, turnover).
-- Grain: one row per year (2019-2025), primary series only.
-- -----------------------------------------------------------------------------

-- Question: how has the average 2-bedroom apartment rent changed 2019-2025?
CREATE OR REPLACE VIEW analysis.story2_historical_rent AS
SELECT
    h.year,
    h.period_label,
    h.geography,
    h.geography_basis,
    h.value                         AS average_rent_2br,
    h.value_status,
    h.reliability_code,
    p.year                          AS previous_year,
    p.value                         AS previous_average_rent_2br,
    (p.geography_basis = h.geography_basis) AS comparable_with_previous_year,
    CASE WHEN p.geography_basis = h.geography_basis THEN h.value - p.value END AS change_dollars,
    CASE WHEN p.geography_basis = h.geography_basis
         THEN round(100.0 * (h.value - p.value) / NULLIF(p.value, 0), 4) END   AS change_pct,
    b.value                         AS same_boundary_previous_year_value,
    o.value - b.value               AS old_boundary_change_dollars,
    h.source_workbook,
    h.source_cell
FROM clean.rental_market_windsor_history h
LEFT JOIN clean.rental_market_windsor_history p
       ON p.metric = h.metric AND p.year = h.year - 1 AND p.is_primary_series
LEFT JOIN clean.rental_market_windsor_history o
       ON o.metric = h.metric AND o.year = h.year AND o.geography_basis = 'pre_2021_census'
      AND h.year = 2022
LEFT JOIN clean.rental_market_windsor_history b
       ON b.metric = h.metric AND b.year = h.year - 1 AND b.geography_basis = 'pre_2021_census'
      AND h.year = 2022
WHERE h.metric = 'average_rent'
  AND h.is_primary_series;

COMMENT ON VIEW analysis.story2_historical_rent IS
    'Grain: year (primary series). Windsor CMA average 2-bedroom apartment rent 2019-2025; change only within one geography boundary.';


-- Question: how has the overall apartment vacancy rate changed 2019-2025?
CREATE OR REPLACE VIEW analysis.story2_historical_vacancy AS
SELECT
    h.year,
    h.period_label,
    h.geography,
    h.geography_basis,
    h.value                         AS vacancy_rate_pct,
    h.value_status,
    h.reliability_code,
    h.yoy_trend                     AS cmhc_yoy_trend,
    p.year                          AS previous_year,
    p.value                         AS previous_vacancy_rate_pct,
    (p.geography_basis = h.geography_basis) AS comparable_with_previous_year,
    CASE WHEN p.geography_basis = h.geography_basis THEN h.value - p.value END AS change_pct_points,
    b.value                         AS same_boundary_previous_year_value,
    o.value - b.value               AS old_boundary_change_pct_points,
    h.source_workbook,
    h.source_cell
FROM clean.rental_market_windsor_history h
LEFT JOIN clean.rental_market_windsor_history p
       ON p.metric = h.metric AND p.year = h.year - 1 AND p.is_primary_series
LEFT JOIN clean.rental_market_windsor_history o
       ON o.metric = h.metric AND o.year = h.year AND o.geography_basis = 'pre_2021_census'
      AND h.year = 2022
LEFT JOIN clean.rental_market_windsor_history b
       ON b.metric = h.metric AND b.year = h.year - 1 AND b.geography_basis = 'pre_2021_census'
      AND h.year = 2022
WHERE h.metric = 'vacancy_rate'
  AND h.is_primary_series;

COMMENT ON VIEW analysis.story2_historical_vacancy IS
    'Grain: year (primary series). Windsor CMA apartment vacancy rate (%) 2019-2025; change in pct points within one boundary.';


-- Question: how has apartment turnover changed 2019-2025?
CREATE OR REPLACE VIEW analysis.story2_historical_turnover AS
SELECT
    h.year,
    h.period_label,
    h.geography,
    h.geography_basis,
    h.value                         AS turnover_rate_pct,
    h.value_status,
    h.reliability_code,
    h.yoy_trend                     AS cmhc_yoy_trend,
    p.year                          AS previous_year,
    p.value                         AS previous_turnover_rate_pct,
    (p.geography_basis = h.geography_basis) AS comparable_with_previous_year,
    CASE WHEN p.geography_basis = h.geography_basis THEN h.value - p.value END AS change_pct_points,
    b.value                         AS same_boundary_previous_year_value,
    o.value - b.value               AS old_boundary_change_pct_points,
    h.source_workbook,
    h.source_cell
FROM clean.rental_market_windsor_history h
LEFT JOIN clean.rental_market_windsor_history p
       ON p.metric = h.metric AND p.year = h.year - 1 AND p.is_primary_series
LEFT JOIN clean.rental_market_windsor_history o
       ON o.metric = h.metric AND o.year = h.year AND o.geography_basis = 'pre_2021_census'
      AND h.year = 2022
LEFT JOIN clean.rental_market_windsor_history b
       ON b.metric = h.metric AND b.year = h.year - 1 AND b.geography_basis = 'pre_2021_census'
      AND h.year = 2022
WHERE h.metric = 'turnover_rate'
  AND h.is_primary_series;

COMMENT ON VIEW analysis.story2_historical_turnover IS
    'Grain: year (primary series). Windsor CMA apartment turnover rate (%) 2019-2025; change in pct points within one boundary.';


-- -----------------------------------------------------------------------------
-- analysis.story2_historical_rental_universe
-- Question: how large was the apartment rental stock on each boundary?
-- Grain: one row per year x geography_basis (both 2022 rows kept).
-- NOT a continuous series: the 2022 boundary change alone adds ~10% to the
-- count. Changes are only calculated within one boundary.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW analysis.story2_historical_rental_universe AS
SELECT
    h.year,
    h.period_label,
    h.geography,
    h.geography_basis,
    h.is_primary_series,
    h.year = 2022                   AS is_geography_bridge_year,
    h.value                         AS rental_universe_units,
    h.value_status,
    p.value                         AS previous_year_same_boundary_units,
    h.value - p.value               AS change_units_same_boundary,
    round(100.0 * (h.value - p.value) / NULLIF(p.value, 0), 4) AS change_pct_same_boundary,
    'not continuous across the 2022 geography boundary change'::text AS series_note,
    h.source_workbook,
    h.source_cell
FROM clean.rental_market_windsor_history h
LEFT JOIN clean.rental_market_windsor_history p
       ON p.metric = h.metric AND p.year = h.year - 1 AND p.geography_basis = h.geography_basis
WHERE h.metric = 'rental_universe';

COMMENT ON VIEW analysis.story2_historical_rental_universe IS
    'Grain: year x geography_basis. Apartment rental universe on each boundary; changes only within a boundary (not a continuous trend).';


-- -----------------------------------------------------------------------------
-- analysis.story2_historical_period_summary
-- Question: how do 2019-2021 conditions compare descriptively with 2022-2025?
-- Grain: one row per metric (rent, vacancy, turnover) x era. Primary series
-- only. Descriptive statistics of the published annual values (simple mean of
-- annual values, min, max, first, last). The two eras are on different
-- geography boundaries (era_geography_basis), so differences between eras are
-- descriptive, not like-for-like. The rental universe is excluded (not
-- comparable across the boundary change).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW analysis.story2_historical_period_summary AS
WITH eras AS (
    SELECT
        h.*,
        CASE WHEN h.year <= 2021 THEN '2019-2021' ELSE '2022-2025' END AS era,
        CASE WHEN h.year <= 2021 THEN 1 ELSE 2 END                       AS era_order
    FROM clean.rental_market_windsor_history h
    WHERE h.is_primary_series
      AND h.metric IN ('average_rent', 'vacancy_rate', 'turnover_rate')
)
SELECT
    metric,
    unit,
    era,
    era_order,
    min(year)                                   AS first_year,
    max(year)                                   AS last_year,
    count(*)                                    AS years_in_era,
    count(value)                                AS published_years,
    string_agg(DISTINCT geography_basis, ', ')  AS era_geography_basis,
    round(avg(value), 4)                        AS mean_of_annual_values,
    min(value)                                  AS min_value,
    max(value)                                  AS max_value,
    (array_agg(value ORDER BY year))[1]         AS first_year_value,
    (array_agg(value ORDER BY year DESC))[1]    AS last_year_value
FROM eras
GROUP BY metric, unit, era, era_order;

COMMENT ON VIEW analysis.story2_historical_period_summary IS
    'Grain: metric x era (2019-2021 vs 2022-2025), primary series. Descriptive mean/min/max/first/last; eras are on different boundaries.';
