-- SQL views for Dashboard 1 ("Windsor Housing Executive Overview"): a
-- combined view across Stories 1-4, not a new story of its own. Built to
-- match the shape of a dashboard a teammate built directly in a separate
-- Superset environment -- the content is reproduced here against this
-- project's own real, already-loaded data, not copied from that
-- environment (which this project has no access to).
--
-- The Housing Affordability section reuses Story 1's existing charts
-- directly (same Superset chart objects, added to this dashboard too) --
-- no new view needed there. Housing Supply reuses
-- warehouse.v_story3_starts_completions_by_dwelling_type as-is (Ontario/
-- Canada scope -- no Windsor-specific starts/completions figure exists in
-- CMHC's source table). Only the 2 views below are new.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- v_dashboard1_rental_yoy
-- One row per metric: Oct-24 vs Oct-25, Windsor CMA. Rent and vacancy are
-- Apartment-scope (that's what CMHC's workbook publishes a Total-bedroom
-- figure for, Oct-24/Oct-25, matching the KPI tiles elsewhere on this
-- project's site). Turnover and rental-stock (universe) are Combined-scope
-- instead -- the Apartment scope has no turnover/universe figure at all
-- in this project's data, only Combined does (confirmed directly against
-- fact_rental_market; not assumed to exist under Apartment just because
-- rent and vacancy do). dwelling_type_label is included in the output so
-- that scope difference is visible, not hidden behind one blanket
-- "Apartment" label.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_dashboard1_rental_yoy AS
WITH metrics AS (
    SELECT
        f.metric_type,
        d.dwelling_type_label,
        p.period_label,
        f.value
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_label = 'Windsor CMA'
      AND b.bedroom_type_label = 'Total'
      AND p.period_label IN ('Oct-24', 'Oct-25')
      AND (
          (f.metric_type IN ('average_rent', 'vacancy_rate') AND d.dwelling_type_label = 'Apartment')
          OR (f.metric_type IN ('turnover_rate', 'universe') AND d.dwelling_type_label = 'Combined')
      )
)
SELECT
    m1.metric_type AS metric,
    m1.dwelling_type_label,
    'Oct-24' AS previous_period_label,
    m1.value AS previous_value,
    'Oct-25' AS latest_period_label,
    m2.value AS latest_value,
    ROUND(m2.value - m1.value, 1) AS change_value,
    CASE WHEN m1.metric_type IN ('average_rent', 'universe') THEN 'units' ELSE 'percentage_points' END
        AS change_unit
FROM metrics m1
JOIN metrics m2
    ON m2.metric_type = m1.metric_type AND m2.period_label = 'Oct-25'
WHERE m1.period_label = 'Oct-24';

-- ============================================================
-- v_dashboard1_cma_benchmark
-- One row per metric: Windsor vs. the median of this project's 4 real
-- comparator CMAs (not a national ranking -- this project's own
-- extraction covers only Windsor + 4 size-comparable Ontario CMAs, see
-- docs/comparator_cmas_justification.md; a "ranked among 42 CMAs" figure
-- would need a full national extraction this project doesn't have).
-- cmas_ranked is always 5 (Windsor + 4 comparators), stated explicitly
-- rather than left to be misread as a bigger universe.
--
-- Windsor's own vacancy_rate/average_rent are NOT in
-- fact_rental_market_comparison at all -- confirmed directly (excluded
-- at load time to avoid duplicating fact_rental_market). Only
-- pct_change_rent/turnover_rate have a genuine Windsor row there. So
-- Windsor's vacancy_rate/average_rent are pulled from fact_rental_market
-- instead (the same table Windsor's own site KPIs already use) and
-- unioned in -- not assumed to exist somewhere they don't.
-- (v_story4_vacancy_comparison/v_story4_rent_comparison had the same gap
-- and are now fixed the same way -- see sql/story4_views.sql. This view
-- keeps its own independent union rather than depending on those, since
-- it already existed before that fix and queries fact_rental_market_comparison
-- directly for other metrics too.)
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_dashboard1_cma_benchmark AS
WITH comparator_metrics AS (
    SELECT
        f.metric_type,
        z.zone_label,
        z.zone_level,
        p.period_label,
        f.value
    FROM warehouse.fact_rental_market_comparison f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_level IN ('cma_total', 'comparator_cma')
      AND d.dwelling_type_label = 'Apartment'
      AND (
          (f.metric_type IN ('vacancy_rate', 'turnover_rate') AND b.bedroom_type_label = 'Total')
          OR (f.metric_type IN ('average_rent', 'pct_change_rent') AND b.bedroom_type_label = '2 Bedroom')
      )
),
windsor_own_metrics AS (
    SELECT
        f.metric_type,
        z.zone_label,
        'cma_total' AS zone_level,
        p.period_label,
        f.value
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_label = 'Windsor CMA'
      AND d.dwelling_type_label = 'Apartment'
      AND f.metric_type IN ('vacancy_rate', 'average_rent')
      AND (
          (f.metric_type = 'vacancy_rate' AND b.bedroom_type_label = 'Total')
          OR (f.metric_type = 'average_rent' AND b.bedroom_type_label = '2 Bedroom')
      )
      AND p.period_label IN ('Oct-24', 'Oct-25')
),
metrics AS (
    SELECT * FROM comparator_metrics
    UNION ALL
    SELECT * FROM windsor_own_metrics
),
ranked AS (
    SELECT
        metric_type,
        zone_label,
        zone_level,
        period_label,
        value,
        RANK() OVER (PARTITION BY metric_type, period_label ORDER BY value DESC) AS rank_highest_first,
        COUNT(*) OVER (PARTITION BY metric_type, period_label) AS cmas_ranked
    FROM metrics
),
comparator_medians AS (
    SELECT
        metric_type,
        period_label,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) AS comparator_median
    FROM metrics
    WHERE zone_level = 'comparator_cma'
    GROUP BY metric_type, period_label
)
SELECT
    r.metric_type AS metric,
    r.period_label,
    r.value AS windsor_value,
    ROUND(cm.comparator_median::numeric, 1) AS cma_median_value,
    ROUND((r.value - cm.comparator_median)::numeric, 1) AS windsor_minus_median,
    r.rank_highest_first AS windsor_rank_highest_first,
    r.cmas_ranked
FROM ranked r
JOIN comparator_medians cm
    ON cm.metric_type = r.metric_type AND cm.period_label = r.period_label
WHERE r.zone_level = 'cma_total';
