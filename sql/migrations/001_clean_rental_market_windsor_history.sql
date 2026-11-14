-- =============================================================================
-- Migration 001 (ADDITIVE): clean.rental_market_windsor_history
--   <- data/staging/windsor_rental_market_history.csv
--
-- Windsor CMA private apartments, October surveys 2019-2025: vacancy rate,
-- 2-bedroom average rent, rental universe, turnover rate (CMHC RMS tables
-- 1.1.1 / 1.1.2 / 1.1.3 / 1.1.6). Built by etl/clean_windsor_rental_history.py,
-- validated by etl/validate_rental_history.py.
--
-- Additive only: creates one new table if it does not exist. It never drops or
-- alters the five existing clean.* tables or anything in analysis.*.
-- Applied by etl/load_rental_history_to_postgres.py, which then TRUNCATEs and
-- reloads this table in the same transaction (re-runs never duplicate rows and
-- never drop the views built on it).
--
-- Grain: year x metric x geography_basis (32 rows). 2022 appears twice: once on
-- the pre-2021-census Windsor CMA boundary (2022 edition) and once on the
-- 2021-census boundary (2023 edition revision). Both rows are kept;
-- is_primary_series picks exactly one row per year x metric for a continuous
-- series (the 2021-census row where both exist).
-- Column names and order match the CSV header exactly.
-- =============================================================================

CREATE TABLE IF NOT EXISTS clean.rental_market_windsor_history (
    year                INTEGER  NOT NULL CHECK (year BETWEEN 2019 AND 2025),
    period_label        TEXT     NOT NULL CHECK (period_label = 'Oct-' || lpad((year % 100)::text, 2, '0')),
    geography           TEXT     NOT NULL CHECK (geography = 'Windsor CMA'),
    geography_basis     TEXT     NOT NULL CHECK (geography_basis IN ('pre_2021_census', '2021_census')),
    is_primary_series   BOOLEAN  NOT NULL,
    dwelling_scope      TEXT     NOT NULL CHECK (dwelling_scope = 'apartment'),
    bedroom_type        TEXT     NOT NULL CHECK (bedroom_type IN ('Total', '2 Bedroom')),
    metric              TEXT     NOT NULL CHECK (metric IN ('vacancy_rate', 'average_rent', 'rental_universe', 'turnover_rate')),
    unit                TEXT     NOT NULL CHECK (unit IN ('percent', 'dollars', 'units')),
    value               NUMERIC,
    raw_value           TEXT,
    value_status        TEXT     NOT NULL CHECK (value_status IN ('published', 'suppressed')),
    reliability_code    TEXT     CHECK (reliability_code IN ('a', 'b', 'c', 'd')),
    yoy_trend           TEXT     CHECK (yoy_trend IN ('significant_increase', 'significant_decrease', 'not_significant')),
    source_edition_year INTEGER  NOT NULL CHECK (source_edition_year BETWEEN 2019 AND 2025),
    source_column_role  TEXT     NOT NULL CHECK (source_column_role IN ('current', 'previous')),
    source_workbook     TEXT     NOT NULL,
    source_table        TEXT     NOT NULL,
    source_cell         TEXT     NOT NULL,

    CONSTRAINT rental_market_windsor_history_pkey PRIMARY KEY (year, metric, geography_basis),
    CONSTRAINT rental_market_windsor_history_source_unique UNIQUE (source_workbook, source_cell),
    -- suppressed ('**') stays NULL, never 0
    CONSTRAINT rental_market_windsor_history_null_matches_status CHECK ((value IS NULL) = (value_status <> 'published')),
    CONSTRAINT rental_market_windsor_history_rate_range CHECK (unit <> 'percent' OR value IS NULL OR value BETWEEN 0 AND 100),
    CONSTRAINT rental_market_windsor_history_positive CHECK (unit = 'percent' OR value IS NULL OR value > 0),
    CONSTRAINT rental_market_windsor_history_metric_mapping CHECK (
        (metric = 'vacancy_rate'    AND unit = 'percent' AND bedroom_type = 'Total'     AND source_table = 'Table 1.1.1') OR
        (metric = 'average_rent'    AND unit = 'dollars' AND bedroom_type = '2 Bedroom' AND source_table = 'Table 1.1.2') OR
        (metric = 'rental_universe' AND unit = 'units'   AND bedroom_type = 'Total'     AND source_table = 'Table 1.1.3') OR
        (metric = 'turnover_rate'   AND unit = 'percent' AND bedroom_type = 'Total'     AND source_table = 'Table 1.1.6')
    ),
    -- geography break: 2019-2021 old boundary, 2023-2025 new boundary, 2022 either
    CONSTRAINT rental_market_windsor_history_basis_by_year CHECK (
        (year <= 2021 AND geography_basis = 'pre_2021_census') OR
        (year >= 2023 AND geography_basis = '2021_census') OR
        year = 2022
    ),
    CONSTRAINT rental_market_windsor_history_primary_rule CHECK (
        is_primary_series = (year <> 2022 OR geography_basis = '2021_census')
    )
);

-- exactly one primary-series row per year x metric
CREATE UNIQUE INDEX IF NOT EXISTS rental_market_windsor_history_primary_idx
    ON clean.rental_market_windsor_history (year, metric) WHERE is_primary_series;
CREATE INDEX IF NOT EXISTS rental_market_windsor_history_metric_idx
    ON clean.rental_market_windsor_history (metric);
CREATE INDEX IF NOT EXISTS rental_market_windsor_history_basis_idx
    ON clean.rental_market_windsor_history (geography_basis);

COMMENT ON TABLE clean.rental_market_windsor_history IS
    'Windsor CMA apartment rental history 2019-2025 (CMHC RMS). Grain: year x metric x geography_basis; 2022 kept on both boundaries; use is_primary_series for continuous series.';
