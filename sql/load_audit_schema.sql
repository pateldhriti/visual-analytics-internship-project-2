-- Load-audit table for etl/etl_framework.py's shared, config-driven loader.
-- One row per load attempt (success or failed), across every dataset the
-- framework loads -- independent of warehouse_schema.sql's star schema and
-- of the raw-landing load_raw_files_to_postgres.py (which tags file/load
-- date on every DATA row instead; this table tracks load RUNS, not rows).
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.load_audit (
    audit_id      BIGSERIAL PRIMARY KEY,
    dataset_name  TEXT NOT NULL,        -- DatasetConfig.name
    file_name     TEXT NOT NULL,        -- source CSV, relative to project root
    target_table  TEXT NOT NULL,        -- "<schema>.<table>" actually loaded into
    rows_loaded   INT,                  -- NULL if the load failed before counting rows
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ NOT NULL,
    status        TEXT NOT NULL,        -- 'success' | 'failed'
    error_message TEXT                  -- NULL on success
);
