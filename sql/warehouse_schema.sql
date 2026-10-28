-- Conceptual ER model: conformed dimensions + one fact table per source.
--
-- Scope: the 4 sources profiled so far (StatCan shelter-cost 98-10-0252-01,
-- CMHC Windsor RMS 2025, StatCan Census Profile 98-401-X2021002, CMHC
-- Quarterly Starts/Completions/Under Construction by Canada-Provinces).
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
    period_type  TEXT NOT NULL CHECK (period_type IN ('census_year', 'survey_month')),
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
    zone_level TEXT NOT NULL
        CHECK (zone_level IN ('zone', 'city_subtotal', 'cma_total', 'comparator_cma'))
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
    symbol              TEXT,  -- raw StatCan symbol, kept as-is for traceability
    data_quality_flag   TEXT   -- symbol translated to a standard label; NULL when symbol is NULL
        CHECK (data_quality_flag IN ('not_available', 'not_applicable', 'use_with_caution',
                                      'too_unreliable', 'revised', 'suppressed')),
    source_coordinate   TEXT,  -- original StatCan Coordinate, for traceability
    -- Enforces this table's own documented grain (see comment above): guards
    -- against the loader ever double-inserting the same combination. Verified
    -- against 0 drops needed on the real 90,720-row load before adding this.
    UNIQUE (geography_key, period_key, income_band_key, household_type_key, tenure_key,
            housing_suitability, dwelling_condition, statistic, shelter_cost_ratio)
);

-- One index per FK column: Postgres indexes a FOREIGN KEY's *referenced*
-- (dimension-side) column automatically via that column's PRIMARY KEY, but
-- never the *referencing* (fact-side) column itself -- without these, every
-- join or filter from a fact table back to one dimension (e.g. "all rows
-- for tenure = Renter") would be a full table scan.
CREATE INDEX idx_fact_shelter_cost_geography ON warehouse.fact_shelter_cost (geography_key);
CREATE INDEX idx_fact_shelter_cost_period ON warehouse.fact_shelter_cost (period_key);
CREATE INDEX idx_fact_shelter_cost_income_band ON warehouse.fact_shelter_cost (income_band_key);
CREATE INDEX idx_fact_shelter_cost_household_type ON warehouse.fact_shelter_cost (household_type_key);
CREATE INDEX idx_fact_shelter_cost_tenure ON warehouse.fact_shelter_cost (tenure_key);

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
    -- Not CHECK-constrained, unlike this schema's other categorical columns:
    -- genuinely open-ended by design, not an oversight. Only 12 of the RMS
    -- workbook's 29 sheets are extracted so far (docs/cmhc_rms_sheet_
    -- catalogue.md); every additional sheet adds a new real metric_type
    -- value, so a fixed CHECK list here would need editing on every future
    -- extraction rather than actually catching bad data.
    metric_type        TEXT NOT NULL,
    value               NUMERIC,
    reliability_letter  TEXT,
    yoy_trend           TEXT,
    -- income_band_key is nullable (NULL for every metric_type except the
    -- Table 3.1.8 quintile rows) -- SQL's standard UNIQUE semantics treat
    -- every NULL as distinct from every other NULL, so this constraint does
    -- NOT catch a duplicate among same-NULL rows. Documented, not a gap
    -- introduced here: the real loader-level duplicate check is
    -- etl/load_warehouse_facts.py's own row-count verification against the
    -- source CSV, which this schema change doesn't replace.
    UNIQUE (zone_key, period_key, bedroom_type_key, dwelling_type_key, tenure_key,
            income_band_key, metric_type)
);

CREATE INDEX idx_fact_rental_market_zone ON warehouse.fact_rental_market (zone_key);
CREATE INDEX idx_fact_rental_market_period ON warehouse.fact_rental_market (period_key);
CREATE INDEX idx_fact_rental_market_bedroom_type ON warehouse.fact_rental_market (bedroom_type_key);
CREATE INDEX idx_fact_rental_market_dwelling_type ON warehouse.fact_rental_market (dwelling_type_key);
CREATE INDEX idx_fact_rental_market_tenure ON warehouse.fact_rental_market (tenure_key);
CREATE INDEX idx_fact_rental_market_income_band ON warehouse.fact_rental_market (income_band_key);

-- Source: CMHC Canada RMS 2025 (Table 1.0, apartment-only, national
-- comparator CMAs) -- a genuinely separate workbook from CMHC Windsor RMS
-- 2025 above, so it gets its own fact table per this schema's "one table
-- per source" rule (see fact_rental_market's comment), rather than being
-- merged into fact_rental_market by zone_level as an earlier version of
-- this schema did.
-- Grain: one row per (zone, period, bedroom_type, dwelling_type, tenure,
--        metric_type) combination -- same shape as fact_rental_market,
--        minus income_band (Table 1.0 has no quintile breakdown).
-- zone_key is always either dim_zone's 'cma_total' row (Windsor) or one of
-- its 'comparator_cma' rows -- never a Windsor sub-zone, since Table 1.0
-- only reports whole-CMA figures.
-- Windsor's rows here are deliberately partial: only turnover_rate and
-- pct_change_rent (metrics the Windsor-specific workbook never extracted);
-- Windsor's vacancy_rate/average_rent are excluded to avoid duplicating
-- the real metric already loaded into fact_rental_market from the
-- Windsor-specific Apartment-scope tables. See
-- etl/load_warehouse_facts.py's load_rms_canada_comparison_facts().
CREATE TABLE warehouse.fact_rental_market_comparison (
    fact_id            BIGSERIAL PRIMARY KEY,
    zone_key           INT  NOT NULL REFERENCES warehouse.dim_zone (zone_key),
    period_key         INT  NOT NULL REFERENCES warehouse.dim_period (period_key),
    bedroom_type_key   INT  NOT NULL REFERENCES warehouse.dim_bedroom_type (bedroom_type_key),
    dwelling_type_key  INT  NOT NULL REFERENCES warehouse.dim_dwelling_type (dwelling_type_key),
    tenure_key         INT  NOT NULL REFERENCES warehouse.dim_tenure (tenure_key),
    metric_type        TEXT NOT NULL,
    value               NUMERIC,
    reliability_letter  TEXT,
    yoy_trend           TEXT,
    UNIQUE (zone_key, period_key, bedroom_type_key, dwelling_type_key, tenure_key, metric_type)
);

CREATE INDEX idx_fact_rental_market_comparison_zone ON warehouse.fact_rental_market_comparison (zone_key);
CREATE INDEX idx_fact_rental_market_comparison_period ON warehouse.fact_rental_market_comparison (period_key);
CREATE INDEX idx_fact_rental_market_comparison_bedroom_type ON warehouse.fact_rental_market_comparison (bedroom_type_key);
CREATE INDEX idx_fact_rental_market_comparison_dwelling_type ON warehouse.fact_rental_market_comparison (dwelling_type_key);
CREATE INDEX idx_fact_rental_market_comparison_tenure ON warehouse.fact_rental_market_comparison (tenure_key);

-- Source: StatCan 98-401-X2021002 (Census Profile, 2021 - CMAs and CAs)
-- Grain: one row per (geography, period, characteristic, measure_type, sex)
-- combination. characteristic_id/characteristic_name are degenerate
-- dimensions (local attributes): unlike tenure/income_band in the other two
-- fact tables, this source's "Owner"/"Renter"/income-bracket breakdowns are
-- each their own CHARACTERISTIC_ID row (e.g. "Owner" and "Renter" are two
-- separate characteristics under one "by tenure" total), not a column that
-- varies against a shared dim_tenure/dim_income_band -- so no FK to either
-- dimension here, to avoid forcing a false conformance (same reasoning as
-- the income_band `scheme` column and the dwelling_condition/dwelling_type
-- distinction noted above). measure_type ('count' | 'rate') and sex
-- ('total' | 'men' | 'women') come from melting the source's 6 value/symbol
-- column pairs; most characteristics only populate sex = 'total' (no sex
-- breakdown exists for household-level stats like income or tenure), which
-- is reflected as a null value + symbol '...' row rather than being dropped.
CREATE TABLE warehouse.fact_census_profile (
    fact_id              BIGSERIAL PRIMARY KEY,
    geography_key        TEXT NOT NULL REFERENCES warehouse.dim_geography (geography_key),
    period_key           INT  NOT NULL REFERENCES warehouse.dim_period (period_key),
    characteristic_id    INT  NOT NULL,
    characteristic_name  TEXT NOT NULL,
    measure_type         TEXT NOT NULL CHECK (measure_type IN ('count', 'rate')),
    sex                  TEXT NOT NULL CHECK (sex IN ('total', 'men', 'women')),
    value                NUMERIC,
    symbol               TEXT,
    UNIQUE (geography_key, period_key, characteristic_id, measure_type, sex)
);

CREATE INDEX idx_fact_census_profile_geography ON warehouse.fact_census_profile (geography_key);
CREATE INDEX idx_fact_census_profile_period ON warehouse.fact_census_profile (period_key);

-- Source: CMHC Quarterly Starts, Completions, Units Under Construction by
-- (Canada, Provinces) -- etl/extract_cmhc_starts_completions.py
-- Grain: one row per (province, period_type, period_label, activity,
-- dwelling_type) combination.
-- province and dwelling_type are both degenerate (local text) columns,
-- deliberately NOT FKs to dim_zone or dim_dwelling_type:
--   - This source has no CMA-level or DGUID-level geography at all (only
--     Ontario/Canada provincial-national totals) -- not the same grain as
--     dim_zone's CMHC sub-CMA zones or dim_geography's StatCan CMAs.
--     Forcing a shared dimension here would be a false conformance, same
--     reasoning as this schema's other local-attribute decisions.
--   - dwelling_type here ('Singles' | 'Semis' | 'Row' | 'Apartment and
--     Other' | 'Total') is a DIFFERENT classification scheme than
--     dim_dwelling_type's CMHC RMS categories ('Apartment' | 'Row
--     (Townhouse)' | 'Combined') -- different category boundaries, not
--     the same taxonomy despite the similar name.
CREATE TABLE warehouse.fact_starts_completions (
    fact_id       BIGSERIAL PRIMARY KEY,
    province      TEXT NOT NULL CHECK (province IN ('Ontario', 'Canada')),
    period_type   TEXT NOT NULL CHECK (period_type IN ('quarter', 'ytd')),
    period_label  TEXT NOT NULL,  -- e.g. 'Second Quarter 2026'
    activity      TEXT NOT NULL
        CHECK (activity IN ('Starts', 'Completions', 'Under Construction')),
    dwelling_type TEXT NOT NULL,
    units         NUMERIC,
    -- No FK columns to index here -- province/dwelling_type are deliberately
    -- local text, not references to dim_zone/dim_dwelling_type (see comment
    -- above on why forcing that conformance would be false).
    UNIQUE (province, period_type, period_label, activity, dwelling_type)
);
