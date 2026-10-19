-- =============================================================================
-- STORY 4 -- CMA RENTAL MARKET COMPARISON (CMHC RMS 2025, Table 1.0)
-- Source: clean.rental_market_canada only: 42 CMA rows (Windsor CMA included),
-- no province, CA or national rows.
--
-- Scope: APARTMENT ONLY (privately initiated apartment structures of 3+ units).
-- Windsor is compared using its own row in this national table, never with
-- Windsor's row_and_apartment figures from clean.rental_market_windsor.
-- Rent and rent growth are 2-bedroom; vacancy and turnover are all bedrooms.
--
-- All 42 CMAs are kept; no comparator subset is chosen. Ottawa-Gatineau is
-- listed by CMHC as two parts (Ont. / Qué.) and each part is ranked as a row.
-- Ranks use published values only; suppressed / not-significant values are
-- NULL, unranked, and reduce cmas_ranked for that metric.
-- The old affordability-gap index is NOT computed (no renter-income growth data).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- analysis.story4_cma_metric_ranking
-- Question: where does each CMA sit for each indicator in the latest period?
-- Grain: one row per CMA x metric, latest period of that metric (Oct-25 for
-- levels, 'Oct-24 to Oct-25' for rent growth). rank_highest_first: 1 = highest
-- value (ties share a rank). Previous-period value kept for context.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story4_cma_metric_ranking AS
WITH periods AS (
    SELECT
        period_label,
        CASE WHEN period_label LIKE '% to %' THEN 'rent_change' ELSE 'survey' END AS period_kind,
        2000 + right(period_label, 2)::int AS end_year
    FROM (SELECT DISTINCT period_label FROM clean.rental_market_canada) d
),
flagged AS (
    SELECT
        period_label,
        period_kind,
        end_year = max(end_year) OVER (PARTITION BY period_kind)     AS is_latest,
        end_year = max(end_year) OVER (PARTITION BY period_kind) - 1 AS is_previous
    FROM periods
),
latest AS (
    SELECT c.*
    FROM clean.rental_market_canada c
    JOIN flagged f ON f.period_label = c.period_label AND f.is_latest
),
previous AS (
    SELECT c.*
    FROM clean.rental_market_canada c
    JOIN flagged f ON f.period_label = c.period_label AND f.is_previous
)
SELECT
    l.source_table,
    'apartment'::text   AS dwelling_scope,
    l.centre,
    l.geography_level,
    l.centre = 'Windsor CMA' AS is_windsor,
    l.metric,
    l.unit,
    l.period_label,
    l.value,
    l.value_status,
    l.reliability_code,
    l.yoy_trend,
    p.period_label      AS previous_period_label,
    p.value             AS previous_value,
    p.value_status      AS previous_value_status,
    CASE WHEN l.value IS NOT NULL
         THEN rank() OVER (PARTITION BY l.metric ORDER BY l.value DESC NULLS LAST) END AS rank_highest_first,
    count(l.value) OVER (PARTITION BY l.metric)                                     AS cmas_ranked,
    count(*)       OVER (PARTITION BY l.metric)                                     AS cmas_in_source,
    l.source_cell
FROM latest l
LEFT JOIN previous p
       ON p.centre = l.centre
      AND p.metric = l.metric;

COMMENT ON VIEW analysis.story4_cma_metric_ranking IS
    'Grain: CMA x metric (latest period, apartment only). Value, rank among published CMAs (1 = highest), previous value.';


-- -----------------------------------------------------------------------------
-- Per-indicator comparison views. Grain: one row per CMA (42), latest period.
-- -----------------------------------------------------------------------------

-- Question: how does Windsor's apartment vacancy rate compare with other CMAs?
CREATE VIEW analysis.story4_cma_vacancy_comparison AS
SELECT * FROM analysis.story4_cma_metric_ranking WHERE metric = 'vacancy_rate';

COMMENT ON VIEW analysis.story4_cma_vacancy_comparison IS
    'Grain: CMA. Apartment vacancy rate (%), Oct-25, with rank and Oct-24 value.';

-- Question: how does Windsor's 2-bedroom apartment rent compare?
CREATE VIEW analysis.story4_cma_rent_2br_comparison AS
SELECT * FROM analysis.story4_cma_metric_ranking WHERE metric = 'average_rent_2br';

COMMENT ON VIEW analysis.story4_cma_rent_2br_comparison IS
    'Grain: CMA. Average 2-bedroom apartment rent ($), Oct-25, with rank and Oct-24 value.';

-- Question: how does Windsor's apartment turnover rate compare?
CREATE VIEW analysis.story4_cma_turnover_comparison AS
SELECT * FROM analysis.story4_cma_metric_ranking WHERE metric = 'turnover_rate';

COMMENT ON VIEW analysis.story4_cma_turnover_comparison IS
    'Grain: CMA. Apartment turnover rate (%), Oct-25, with rank and Oct-24 value.';

-- Question: how does Windsor's 2-bedroom rent growth (same sample) compare?
CREATE VIEW analysis.story4_cma_rent_growth_comparison AS
SELECT * FROM analysis.story4_cma_metric_ranking WHERE metric = 'rent_pct_change_2br';

COMMENT ON VIEW analysis.story4_cma_rent_growth_comparison IS
    'Grain: CMA. CMHC same-sample % change in 2-bedroom apartment rent, Oct-24 to Oct-25, with rank.';


-- -----------------------------------------------------------------------------
-- analysis.story4_windsor_position
-- Question: where does Windsor rank among the available CMAs?
-- Grain: one row per metric (latest period). Distribution statistics use
-- published CMA values only; percentile_rank_pct = share of other ranked CMAs
-- with a lower value (0 = lowest, 100 = highest).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story4_windsor_position AS
WITH dist AS (
    SELECT
        metric,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY value) AS cma_median_value,
        min(value) AS cma_min_value,
        max(value) AS cma_max_value
    FROM analysis.story4_cma_metric_ranking
    WHERE value IS NOT NULL
    GROUP BY metric
),
pct AS (
    SELECT
        centre,
        metric,
        round((100.0 * percent_rank() OVER (PARTITION BY metric ORDER BY value))::numeric, 4) AS percentile_rank_pct
    FROM analysis.story4_cma_metric_ranking
    WHERE value IS NOT NULL
)
SELECT
    r.dwelling_scope,
    r.metric,
    r.unit,
    r.period_label,
    r.value               AS windsor_value,
    r.value_status        AS windsor_value_status,
    r.reliability_code    AS windsor_reliability_code,
    r.rank_highest_first  AS windsor_rank_highest_first,
    r.cmas_ranked,
    r.cmas_in_source,
    p.percentile_rank_pct AS windsor_percentile_rank_pct,
    d.cma_median_value::numeric AS cma_median_value,
    d.cma_min_value,
    d.cma_max_value,
    r.value - d.cma_median_value::numeric AS windsor_minus_median,
    r.source_cell
FROM analysis.story4_cma_metric_ranking r
JOIN dist d ON d.metric = r.metric
LEFT JOIN pct p ON p.centre = r.centre AND p.metric = r.metric
WHERE r.is_windsor;

COMMENT ON VIEW analysis.story4_windsor_position IS
    'Grain: metric. Windsor CMA value, rank, percentile and the median/min/max across published CMAs (apartment only).';
