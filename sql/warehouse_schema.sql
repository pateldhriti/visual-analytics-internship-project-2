-- Conceptual ER model: conformed dimensions + one fact table per source.
--
-- Scope: only the 2 sources actually profiled so far (StatCan shelter-cost
-- 98-10-0252-01, CMHC Windsor RMS 2025). The Census Profile (98-401) and
-- CMHC starts/completions sources from the proposal are not modeled here --
-- nobody has downloaded/profiled those files yet, so their fact table
-- schemas would be guesses, not a real model.
--
-- Not every one of the 8 listed dimensions applies to every source --
-- that's a real property of these two surveys, not an omission:
--   - household_type and income_band (StatCan bracket scheme) only exist
--     in the shelter-cost table; CMHC RMS has neither.
--   - bedroom_type, zone and dwelling_type only exist in CMHC RMS; the
--     shelter-cost table has none of them.
--   - geography (StatCan CMA-level, DGUID-based) and zone (CMHC sub-CMA)
--     are different grains from different sources, not the same thing
--     renamed -- kept as two separate dimensions.
--   - tenure applies to both: shelter-cost data varies by tenure;
--     CMHC RMS data is rental-only, so every CMHC fact row is implicitly
--     tenure = 'Renter'.
--   - income_band's StatCan dollar-bracket scheme and CMHC's income-quintile
--     scheme (used only in CMHC Table 3.1.8) are different classifications,
--     not directly comparable -- modeled as one dimension table with a
--     `scheme` column distinguishing them, rather than forcing a false
--     conformance.
--   - StatCan's "Dwelling condition" (needs repair, yes/no) is NOT the same
--     concept as this model's dwelling_type (Apartment/Row/Combined, from
--     CMHC) despite the similar name -- kept as a local attribute on
--     fact_shelter_cost, not merged into dim_dwelling_type.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- Dimensions
-- ============================================================

CREATE TABLE warehouse.dim_geography (
    geography_key   TEXT PRIMARY KEY,  -- StatCan DGUID
    geography_name  TEXT NOT NULL,
    geography_level TEXT NOT NULL      -- e.g. 'CMA'
);

CREATE TABLE warehouse.dim_period (
    period_key   SERIAL PRIMARY KEY,
    period_label TEXT NOT NULL UNIQUE, -- e.g. '2021', 'Oct-24'
    period_type  TEXT NOT NULL,        -- 'census_year' | 'survey_month'
    period_year  INT NOT NULL,
    period_month INT                   -- NULL for census_year rows
);

CREATE TABLE warehouse.dim_tenure (
    tenure_key  SERIAL PRIMARY KEY,
    tenure_name TEXT NOT NULL UNIQUE   -- 'Total' | 'Owner' | 'Renter'
);

CREATE TABLE warehouse.dim_income_band (
    income_band_key SERIAL PRIMARY KEY,
    scheme          TEXT NOT NULL,     -- 'statcan_bracket' | 'cmhc_quintile'
    member_id       INT NOT NULL,      -- source's own member ordering
    band_label      TEXT NOT NULL,
    UNIQUE (scheme, member_id)
);

CREATE TABLE warehouse.dim_household_type (
    household_type_key INT PRIMARY KEY,  -- StatCan's own member_id (1-16)
    household_type_label TEXT NOT NULL,
    parent_member_id    INT              -- self-referencing hierarchy; NULL for the root
        REFERENCES warehouse.dim_household_type (household_type_key)
);

CREATE TABLE warehouse.dim_bedroom_type (
    bedroom_type_key   SERIAL PRIMARY KEY,
    bedroom_type_label TEXT NOT NULL UNIQUE
);

CREATE TABLE warehouse.dim_zone (
    zone_key   SERIAL PRIMARY KEY,
    zone_label TEXT NOT NULL UNIQUE,
    zone_level TEXT NOT NULL  -- 'zone' | 'city_subtotal' | 'cma_total'
);

CREATE TABLE warehouse.dim_dwelling_type (
    dwelling_type_key   SERIAL PRIMARY KEY,
    dwelling_type_label TEXT NOT NULL UNIQUE  -- 'Apartment' | 'Row (Townhouse)' | 'Combined'
);

-- ============================================================
-- Fact tables -- one per source
-- ============================================================

-- Source: StatCan 98-10-0252-01 (Shelter-cost-to-income ratio by tenure)
-- Grain: one row per (geography, period, income_band, household_type,
--        housing_suitability, dwelling_condition, statistic,
--        shelter_cost_ratio, tenure) combination.
-- housing_suitability / dwelling_condition / statistic / shelter_cost_ratio
-- are degenerate dimensions (kept as local text attributes): none of them
-- are among this task's 8 listed shared dimensions.
CREATE TABLE warehouse.fact_shelter_cost (
    fact_id             BIGSERIAL PRIMARY KEY,
    geography_key       TEXT NOT NULL REFERENCES warehouse.dim_geography (geography_key),
    period_key          INT  NOT NULL REFERENCES warehouse.dim_period (period_key),
    income_band_key     INT  NOT NULL REFERENCES warehouse.dim_income_band (income_band_key),
    household_type_key  INT  NOT NULL REFERENCES warehouse.dim_household_type (household_type_key),
    tenure_key          INT  NOT NULL REFERENCES warehouse.dim_tenure (tenure_key),
    housing_suitability TEXT NOT NULL,
    dwelling_condition  TEXT NOT NULL,
    statistic           TEXT NOT NULL,
    shelter_cost_ratio  TEXT NOT NULL,
    value               NUMERIC,
    symbol              TEXT,
    source_coordinate   TEXT  -- original StatCan Coordinate, for traceability
);

-- Source: CMHC Windsor RMS 2025
-- Grain: one row per (zone, period, bedroom_type, dwelling_type, tenure,
--        metric_type) combination. metric_type distinguishes vacancy rate /
--        average rent / universe / turnover / etc. -- the task asks for one
--        fact table per source, so CMHC's several metric tables are unified
--        here via metric_type rather than split into separate fact tables.
-- income_band_key is nullable: only Table 3.1.8-sourced rows (vacancy by
-- income quintile) populate it: NULL means "not applicable to this metric".
CREATE TABLE warehouse.fact_rental_market (
    fact_id            BIGSERIAL PRIMARY KEY,
    zone_key           INT  NOT NULL REFERENCES warehouse.dim_zone (zone_key),
    period_key         INT  NOT NULL REFERENCES warehouse.dim_period (period_key),
    bedroom_type_key   INT  NOT NULL REFERENCES warehouse.dim_bedroom_type (bedroom_type_key),
    dwelling_type_key  INT  NOT NULL REFERENCES warehouse.dim_dwelling_type (dwelling_type_key),
    tenure_key         INT  NOT NULL REFERENCES warehouse.dim_tenure (tenure_key),
    income_band_key    INT  REFERENCES warehouse.dim_income_band (income_band_key),
    metric_type        TEXT NOT NULL,  -- 'vacancy_rate' | 'average_rent' | 'universe' | 'turnover' | ...
    value               NUMERIC,
    reliability_letter  TEXT,
    yoy_trend           TEXT
);
