-- =============================================================================
-- analysis schema: analytical views over the validated clean.* tables.
--
-- Executed first by etl/build_analysis_views.py, followed by 01..04 in file-name
-- order, all in ONE transaction. The schema is dropped and recreated each run,
-- so the build is repeatable and never leaves stale views behind.
-- etl/build_analysis_views.py refuses to run if anything other than views
-- exists in `analysis` (nothing but views may live here).
--
-- Rules for every view in this schema:
--   * reads only clean.* (no warehouse.*, no old sql/story*_views.sql)
--   * plain views only (no materialized views, no tables)
--   * suppressed / unpublished values stay NULL and are excluded from arithmetic;
--     NULL is never replaced with 0 (the one documented exception is the Story 1
--     'not applicable' count for income bands of $10,000 and over -- see 01)
--   * every division is protected with NULLIF(denominator, 0)
--   * datasets are not joined to each other unless geography, period and scope
--     are the same (only the Story 1 Census cross-check does this)
--   * percentages are on a 0-100 scale, rounded to 4 decimals
-- =============================================================================

DROP SCHEMA IF EXISTS analysis CASCADE;
CREATE SCHEMA analysis;

COMMENT ON SCHEMA analysis IS
    'Analytical views derived only from clean.* (built by etl/build_analysis_views.py from sql/analysis/).';
