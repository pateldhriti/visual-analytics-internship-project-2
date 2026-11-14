"""
ADDITIVE load of data/staging/windsor_rental_market_history.csv into
clean.rental_market_windsor_history, plus the Story 2 historical views.

    .venv\\Scripts\\python.exe etl\\load_rental_history_to_postgres.py

All in ONE transaction (any failure rolls back and leaves the database as it was):
  1. apply sql/migrations/001_clean_rental_market_windsor_history.sql
     (CREATE TABLE IF NOT EXISTS -- never touches the five existing clean tables)
  2. check the CSV header against the table, TRUNCATE the history table and
     COPY the 32 rows (re-running replaces, never duplicates, and does not drop
     the views that depend on the table)
  3. apply sql/analysis/05_story2_rental_history.sql (CREATE OR REPLACE VIEW --
     the analysis schema and its 31 existing views are not dropped)

Before the first run it records etl/postgres_pre_history_baseline.json: the
definition and content hash of the five existing clean tables and the
definition of every existing analysis view. etl/validate_rental_history_postgres.py
compares against it to prove nothing existing was changed. The baseline is
never overwritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg2

from cleaning_common import PROJECT_ROOT, STAGING_DIR
from clean_windsor_rental_history import OUTPUT_NAME
from load_cleaned_to_postgres import TABLES as EXISTING_CLEAN_TABLES
from load_cleaned_to_postgres import LoadError, connect, copy_rows, prepare_rows, read_staging, table_columns

TABLE = "rental_market_windsor_history"
MIGRATION_SQL = PROJECT_ROOT / "sql" / "migrations" / "001_clean_rental_market_windsor_history.sql"
VIEWS_SQL = PROJECT_ROOT / "sql" / "analysis" / "05_story2_rental_history.sql"
BASELINE_PATH = Path(__file__).resolve().parent / "postgres_pre_history_baseline.json"
HISTORY_VIEWS = ["story2_historical_series", "story2_historical_rent", "story2_historical_vacancy",
                 "story2_historical_turnover", "story2_historical_rental_universe",
                 "story2_historical_period_summary"]


def fingerprint(cur) -> dict:
    """Definitions + content hashes of the pre-existing clean tables and analysis views."""
    tables = {}
    for table in EXISTING_CLEAN_TABLES.values():
        cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'clean' AND table_name = %s ORDER BY ordinal_position", (table,))
        columns = [list(r) for r in cur.fetchall()]
        cur.execute(f"SELECT count(*), md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) "
                    f"FROM clean.{table} t")
        rows, content_md5 = cur.fetchone()
        cur.execute("""SELECT con.conname, pg_get_constraintdef(con.oid) FROM pg_constraint con
                       JOIN pg_class rel ON rel.oid = con.conrelid JOIN pg_namespace n ON n.oid = rel.relnamespace
                       WHERE n.nspname = 'clean' AND rel.relname = %s ORDER BY 1""", (table,))
        constraints = [list(r) for r in cur.fetchall()]
        cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'clean' AND tablename = %s "
                    "ORDER BY 1", (table,))
        indexes = [list(r) for r in cur.fetchall()]
        tables[table] = {"columns": columns, "rows": rows, "content_md5": content_md5,
                         "constraints": constraints, "indexes": indexes}
    cur.execute("""SELECT c.relname, md5(pg_get_viewdef(c.oid, true)) FROM pg_class c
                   JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = 'analysis' AND c.relkind = 'v' AND NOT (c.relname = ANY(%s))
                   ORDER BY 1""", (HISTORY_VIEWS,))
    views = dict(cur.fetchall())
    return {"clean_tables": tables, "analysis_views": views}


def record_baseline(conn) -> bool:
    if BASELINE_PATH.exists():
        return False
    with conn.cursor() as cur:
        snap = fingerprint(cur)
    conn.rollback()
    BASELINE_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return True


def load(conn, staging_dir: Path = STAGING_DIR) -> dict:
    df = read_staging(staging_dir / OUTPUT_NAME)
    with conn:  # one transaction
        with conn.cursor() as cur:
            cur.execute(MIGRATION_SQL.read_text(encoding="utf-8"))
            columns = table_columns(cur, TABLE)
            rows = prepare_rows(df, columns, OUTPUT_NAME)  # stops on any missing / unexpected column
            cur.execute(f"TRUNCATE clean.{TABLE}")
            copy_rows(cur, TABLE, list(columns), rows)
            cur.execute(f"SELECT count(*) FROM clean.{TABLE}")
            loaded = cur.fetchone()[0]
            if loaded != len(df):
                raise LoadError(f"clean.{TABLE}: loaded {loaded} rows but {OUTPUT_NAME} has {len(df)}")
            cur.execute(VIEWS_SQL.read_text(encoding="utf-8"))
            cur.execute("SELECT count(*) FROM information_schema.views WHERE table_schema = 'analysis'")
            total_views = cur.fetchone()[0]
    return {"csv_rows": len(df), "loaded_rows": loaded, "analysis_views": total_views}


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        print(f"Cannot connect to PostgreSQL: {exc}")
        return 1
    try:
        if record_baseline(conn):
            print(f"Baseline of existing clean tables / analysis views written: {BASELINE_PATH}")
        result = load(conn)
        print(f"clean.{TABLE}: {result['loaded_rows']} rows <- data/staging/{OUTPUT_NAME}")
        print(f"Applied {VIEWS_SQL.relative_to(PROJECT_ROOT).as_posix()} "
              f"({len(HISTORY_VIEWS)} history views; {result['analysis_views']} views in analysis). Committed.")
    except (LoadError, psycopg2.Error) as exc:
        print(f"LOAD FAILED (rolled back, database unchanged): {exc}")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
