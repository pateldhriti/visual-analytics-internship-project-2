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
