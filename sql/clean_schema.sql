-- =============================================================================
-- clean schema: the five validated staging CSVs in data/staging/, one table each.
--
-- Source of truth: data/staging/*.csv (built by etl/run_cleaning_pipeline.py and
-- validated by etl/validate_cleaned_data.py). Column names and order match the
-- CSV headers exactly; etl/load_cleaned_to_postgres.py refuses to load if they
-- differ.
--
-- Applied by etl/load_cleaned_to_postgres.py inside one transaction, followed by
-- the data load. Safe to re-run: each table is dropped and recreated, so rows are
-- never duplicated. DROP TABLE is deliberately NOT CASCADE -- if a later phase
-- builds views on these tables, a reload stops with a clear error instead of
-- silently dropping those views.
--
-- Conventions
--   * Measured values are NUMERIC (exact, so 4.3 stays 4.3). Identifiers, years,
--     member ids and unit counts are INTEGER. Labels and status codes are TEXT.
--   * NULL = no number published. The reason is always in the matching status
--     column; CHECK constraints enforce "NULL value <=> non-published status".
--   * The tables are not linked by foreign keys: their geographies and periods
--     differ (Census 2021, RMS Oct-24/Oct-25, starts Aug 2026; Canada = all CMAs).
--   * No KPIs, no analytical views.
--
-- Old SQL (sql/warehouse_schema.sql, sql/warehouse_seed_dimensions.sql,
-- sql/story3_views.sql, sql/story4_views.sql) belongs to the previous pipeline
-- and is not used here.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS clean;

DROP TABLE IF EXISTS clean.census_profile;
DROP TABLE IF EXISTS clean.shelter_cost;
DROP TABLE IF EXISTS clean.rental_market_windsor;
DROP TABLE IF EXISTS clean.starts_completions_windsor;
DROP TABLE IF EXISTS clean.rental_market_canada;


-- -----------------------------------------------------------------------------
-- clean.census_profile  <-  data/staging/windsor_census_profile.csv
-- One row per Census Profile 2021 characteristic, Windsor CMA, topic subset.
-- rate_* is StatCan's "rate" column; for some characteristics it holds a
-- non-percentage figure, so no 0-100 range is enforced on it.
-- -----------------------------------------------------------------------------
CREATE TABLE clean.census_profile (
    census_year                 INTEGER  NOT NULL CHECK (census_year = 2021),
    geography                   TEXT     NOT NULL CHECK (geography = 'Windsor CMA'),
    dguid                       TEXT     NOT NULL CHECK (dguid = '2021S0503559'),
    alt_geo_code                INTEGER  NOT NULL,
    geo_level                   TEXT     NOT NULL CHECK (geo_level = 'Census metropolitan area'),
    tnr_sf                      NUMERIC  NOT NULL,
    tnr_lf                      NUMERIC  NOT NULL,
    data_quality_flag           INTEGER  NOT NULL,
    topic                       TEXT     NOT NULL CHECK (topic IN ('population', 'dwellings_housing', 'household',
                                                                   'income', 'labour_employment')),
    characteristic_id           INTEGER  PRIMARY KEY,
    characteristic_name         TEXT     NOT NULL,
    characteristic_indent_level INTEGER  NOT NULL CHECK (characteristic_indent_level >= 0),
    characteristic_note         INTEGER,
    unit_marker                 TEXT     CHECK (unit_marker IN ('$', '%')),
    count_total                 NUMERIC,
    count_total_status          TEXT     NOT NULL,
    count_men                   NUMERIC,
    count_men_status            TEXT     NOT NULL,
    count_women                 NUMERIC,
    count_women_status          TEXT     NOT NULL,
    rate_total                  NUMERIC,
    rate_total_status           TEXT     NOT NULL,
    rate_men                    NUMERIC,
    rate_men_status             TEXT     NOT NULL,
    rate_women                  NUMERIC,
    rate_women_status           TEXT     NOT NULL,

    -- StatCan symbol legend; published / use_with_caution / revised keep their number.
    CONSTRAINT census_profile_status_codes CHECK (
        count_total_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
        AND count_men_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
        AND count_women_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
        AND rate_total_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
        AND rate_men_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
        AND rate_women_status IN ('published', 'suppressed', 'not_applicable', 'not_available', 'too_unreliable', 'use_with_caution', 'revised')
    ),
    CONSTRAINT census_profile_null_matches_status CHECK (
        (count_total IS NULL) = (count_total_status NOT IN ('published', 'use_with_caution', 'revised'))
        AND (count_men IS NULL) = (count_men_status NOT IN ('published', 'use_with_caution', 'revised'))
        AND (count_women IS NULL) = (count_women_status NOT IN ('published', 'use_with_caution', 'revised'))
        AND (rate_total IS NULL) = (rate_total_status NOT IN ('published', 'use_with_caution', 'revised'))
        AND (rate_men IS NULL) = (rate_men_status NOT IN ('published', 'use_with_caution', 'revised'))
        AND (rate_women IS NULL) = (rate_women_status NOT IN ('published', 'use_with_caution', 'revised'))
    )
);

CREATE INDEX census_profile_geography_year_idx ON clean.census_profile (geography, census_year);
CREATE INDEX census_profile_topic_idx ON clean.census_profile (topic);


-- -----------------------------------------------------------------------------
-- clean.shelter_cost  <-  data/staging/windsor_shelter_cost.csv
-- StatCan 98-10-0252-01, Windsor CMA, 2021. One row per source row (2,389);
-- combinations absent from the source are not created. Household type has 16
-- members but 14 labels, so *_member_id (from coordinate) tells them apart.
-- Dollar rows (Median/Average income) can be negative; household counts cannot.
-- -----------------------------------------------------------------------------
CREATE TABLE clean.shelter_cost (
    ref_year                      INTEGER  NOT NULL CHECK (ref_year = 2021),
    geography                     TEXT     NOT NULL CHECK (geography = 'Windsor CMA'),
    source_geography_label        TEXT     NOT NULL CHECK (source_geography_label = 'Windsor (CMA), Ont.'),
    dguid                         TEXT     NOT NULL CHECK (dguid = '2021S0503559'),
    income_group                  TEXT     NOT NULL,
    income_group_member_id        INTEGER  NOT NULL CHECK (income_group_member_id > 0),
    household_type                TEXT     NOT NULL,
    household_type_member_id      INTEGER  NOT NULL CHECK (household_type_member_id > 0),
    housing_suitability           TEXT     NOT NULL,
    housing_suitability_member_id INTEGER  NOT NULL CHECK (housing_suitability_member_id > 0),
    dwelling_condition            TEXT     NOT NULL,
    dwelling_condition_member_id  INTEGER  NOT NULL CHECK (dwelling_condition_member_id > 0),
    statistic                     TEXT     NOT NULL,
    statistic_member_id           INTEGER  NOT NULL CHECK (statistic_member_id > 0),
    shelter_cost_ratio            TEXT     NOT NULL,
    shelter_cost_ratio_member_id  INTEGER  NOT NULL CHECK (shelter_cost_ratio_member_id > 0),
    tenure                        TEXT     NOT NULL CHECK (tenure IN ('Total - Tenure', 'Owner', 'Renter')),
    tenure_member_id              INTEGER  NOT NULL CHECK (tenure_member_id > 0),
    coordinate                    TEXT     PRIMARY KEY,
    measure_kind                  TEXT     NOT NULL CHECK (measure_kind IN ('household_count', 'dollars')),
    value                         NUMERIC,
    raw_value                     TEXT,
    status_code                   TEXT,
    value_status                  TEXT     NOT NULL CHECK (value_status IN ('published', 'suppressed', 'not_applicable',
                                                                            'not_available', 'too_unreliable',
                                                                            'use_with_caution', 'revised')),

    CONSTRAINT shelter_cost_member_ids_unique UNIQUE (income_group_member_id, household_type_member_id,
                                                      housing_suitability_member_id, dwelling_condition_member_id,
                                                      statistic_member_id, shelter_cost_ratio_member_id,
                                                      tenure_member_id),
    CONSTRAINT shelter_cost_null_matches_status CHECK (
        (value IS NULL) = (value_status NOT IN ('published', 'use_with_caution', 'revised'))
    ),
    CONSTRAINT shelter_cost_counts_non_negative CHECK (measure_kind <> 'household_count' OR value IS NULL OR value >= 0)
);

CREATE INDEX shelter_cost_geography_year_idx ON clean.shelter_cost (geography, ref_year);
CREATE INDEX shelter_cost_tenure_idx ON clean.shelter_cost (tenure);
CREATE INDEX shelter_cost_income_group_idx ON clean.shelter_cost (income_group);
CREATE INDEX shelter_cost_household_type_idx ON clean.shelter_cost (household_type);
CREATE INDEX shelter_cost_ratio_idx ON clean.shelter_cost (shelter_cost_ratio);
CREATE INDEX shelter_cost_measure_kind_idx ON clean.shelter_cost (measure_kind);


-- -----------------------------------------------------------------------------
-- clean.rental_market_windsor  <-  data/staging/windsor_rental_market.csv
-- CMHC Rental Market Survey 2025, Windsor workbook, 20 tables, one row per cell.
-- income_quintile is only filled for Table 3.1.8, so the natural key uses
-- UNIQUE NULLS NOT DISTINCT (PostgreSQL 15+).
-- -----------------------------------------------------------------------------
CREATE TABLE clean.rental_market_windsor (
    source_table            TEXT     NOT NULL,
    dwelling_scope          TEXT     NOT NULL CHECK (dwelling_scope IN ('apartment', 'row_townhouse', 'row_and_apartment')),
    geography               TEXT     NOT NULL CHECK (geography = 'Windsor CMA'),
    zone                    TEXT     NOT NULL,
    zone_level              TEXT     NOT NULL CHECK (zone_level IN ('zone', 'city_subtotal', 'cma_total')),
    bedroom_type            TEXT     NOT NULL,
    metric                  TEXT     NOT NULL,
    unit                    TEXT     NOT NULL CHECK (unit IN ('percent', 'dollars', 'units')),
    period_label            TEXT     NOT NULL CHECK (period_label IN ('Oct-24', 'Oct-25', 'Oct-23 to Oct-24', 'Oct-24 to Oct-25')),
    value                   NUMERIC,
    raw_value               TEXT     NOT NULL,
    value_status            TEXT     NOT NULL CHECK (value_status IN ('published', 'suppressed', 'change_not_significant')),
    reliability_code        TEXT     CHECK (reliability_code IN ('a', 'b', 'c', 'd')),
    yoy_trend               TEXT     CHECK (yoy_trend IN ('significant_increase', 'significant_decrease', 'not_significant')),
    vacant_rent_higher_flag TEXT     CHECK (vacant_rent_higher_flag IN ('Y', 'N', 'suppressed')),
    income_quintile         TEXT,
    renter_income_range     TEXT,
    affordable_rent_range   TEXT,
    source_cell             TEXT     PRIMARY KEY,

    CONSTRAINT rental_market_windsor_natural_key UNIQUE NULLS NOT DISTINCT
        (source_table, zone, bedroom_type, metric, period_label, income_quintile),
    CONSTRAINT rental_market_windsor_null_matches_status CHECK ((value IS NULL) = (value_status <> 'published')),
    CONSTRAINT rental_market_windsor_rent_positive CHECK (unit <> 'dollars' OR value IS NULL OR value > 0),
    CONSTRAINT rental_market_windsor_units_non_negative CHECK (unit <> 'units' OR value IS NULL OR value >= 0),
    CONSTRAINT rental_market_windsor_percent_range CHECK (
        unit <> 'percent' OR value IS NULL
        OR (metric LIKE '%pct_change' AND value BETWEEN -100 AND 100)
        OR (metric NOT LIKE '%pct_change' AND value BETWEEN 0 AND 100)
    )
);

CREATE INDEX rental_market_windsor_geography_period_idx ON clean.rental_market_windsor (geography, period_label);
CREATE INDEX rental_market_windsor_metric_idx ON clean.rental_market_windsor (metric);
CREATE INDEX rental_market_windsor_zone_idx ON clean.rental_market_windsor (zone);
CREATE INDEX rental_market_windsor_bedroom_type_idx ON clean.rental_market_windsor (bedroom_type);
CREATE INDEX rental_market_windsor_dwelling_scope_idx ON clean.rental_market_windsor (dwelling_scope);
CREATE INDEX rental_market_windsor_source_table_idx ON clean.rental_market_windsor (source_table);


-- -----------------------------------------------------------------------------
-- clean.starts_completions_windsor  <-  data/staging/windsor_starts_completions.csv
-- CMHC August 2026 edition, Windsor row of Tables A4_1, A5_1, A6_1.
-- CMHC '-' (Nil or Zero) is stored as units = 0 with value_flag = 'nil_or_zero'.
-- -----------------------------------------------------------------------------
CREATE TABLE clean.starts_completions_windsor (
    geography              TEXT     NOT NULL CHECK (geography = 'Windsor CMA'),
    source_geography_label TEXT     NOT NULL CHECK (source_geography_label = 'Windsor'),
    source_table           TEXT     NOT NULL,
    activity               TEXT     NOT NULL CHECK (activity IN ('Starts', 'Completions', 'Under Construction')),
    dwelling_type          TEXT     NOT NULL CHECK (dwelling_type IN ('Singles', 'Semis', 'Row', 'Apt. and Other', 'Total')),
    period_label           TEXT     NOT NULL CHECK (period_label IN ('August 2026', 'January to August 2026')),
    period_type            TEXT     NOT NULL CHECK (period_type IN ('month', 'year_to_date', 'stock_at_month_end')),
    units                  INTEGER  CHECK (units >= 0),
    raw_value              TEXT     NOT NULL,
    value_flag             TEXT     NOT NULL CHECK (value_flag IN ('published', 'nil_or_zero', 'not_available',
                                                                   'infinity', 'too_small_to_express')),
    source_cell            TEXT     PRIMARY KEY,

    CONSTRAINT starts_completions_windsor_natural_key UNIQUE (source_table, activity, dwelling_type),
    CONSTRAINT starts_completions_windsor_null_matches_flag CHECK (
        (units IS NULL) = (value_flag NOT IN ('published', 'nil_or_zero'))
    ),
    CONSTRAINT starts_completions_windsor_nil_is_zero CHECK (value_flag <> 'nil_or_zero' OR units = 0)
);

CREATE INDEX starts_completions_windsor_geography_period_idx ON clean.starts_completions_windsor (geography, period_label);
CREATE INDEX starts_completions_windsor_activity_idx ON clean.starts_completions_windsor (activity);
CREATE INDEX starts_completions_windsor_dwelling_type_idx ON clean.starts_completions_windsor (dwelling_type);


-- -----------------------------------------------------------------------------
-- clean.rental_market_canada  <-  data/staging/canada_rental_market_comparison.csv
-- CMHC RMS 2025 national workbook, Table 1.0, CMA rows only (Windsor included).
-- Apartment-only scope: compare with rental_market_windsor where
-- dwelling_scope = 'apartment'.
-- -----------------------------------------------------------------------------
CREATE TABLE clean.rental_market_canada (
    source_table     TEXT     NOT NULL CHECK (source_table = 'Table 1.0'),
    centre           TEXT     NOT NULL CHECK (centre ~ '\mCMA\M'),
    geography_level  TEXT     NOT NULL CHECK (geography_level = 'cma'),
    metric           TEXT     NOT NULL CHECK (metric IN ('vacancy_rate', 'turnover_rate', 'average_rent_2br', 'rent_pct_change_2br')),
    unit             TEXT     NOT NULL CHECK (unit IN ('percent', 'dollars')),
    period_label     TEXT     NOT NULL CHECK (period_label IN ('Oct-24', 'Oct-25', 'Oct-23 to Oct-24', 'Oct-24 to Oct-25')),
    value            NUMERIC,
    raw_value        TEXT     NOT NULL,
    value_status     TEXT     NOT NULL CHECK (value_status IN ('published', 'suppressed', 'change_not_significant')),
    reliability_code TEXT     CHECK (reliability_code IN ('a', 'b', 'c', 'd')),
    yoy_trend        TEXT     CHECK (yoy_trend IN ('significant_increase', 'significant_decrease', 'not_significant')),
    source_cell      TEXT     PRIMARY KEY,

    CONSTRAINT rental_market_canada_natural_key UNIQUE (centre, metric, period_label),
    CONSTRAINT rental_market_canada_null_matches_status CHECK ((value IS NULL) = (value_status <> 'published')),
    CONSTRAINT rental_market_canada_rent_positive CHECK (unit <> 'dollars' OR value IS NULL OR value > 0),
    CONSTRAINT rental_market_canada_percent_range CHECK (
        unit <> 'percent' OR value IS NULL
        OR (metric = 'rent_pct_change_2br' AND value BETWEEN -100 AND 100)
        OR (metric <> 'rent_pct_change_2br' AND value BETWEEN 0 AND 100)
    )
);

CREATE INDEX rental_market_canada_centre_idx ON clean.rental_market_canada (centre);
CREATE INDEX rental_market_canada_metric_idx ON clean.rental_market_canada (metric);
CREATE INDEX rental_market_canada_period_idx ON clean.rental_market_canada (period_label);
