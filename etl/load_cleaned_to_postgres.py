"""
Load the five validated staging CSVs into the `clean` schema of PostgreSQL.

    .venv\\Scripts\\python.exe etl\\load_cleaned_to_postgres.py

Steps, all in ONE transaction (any failure rolls everything back and leaves
the database as it was):
  1. apply sql/clean_schema.sql (creates schema `clean`, drops and recreates
     the five tables -- so re-running never duplicates rows)
  2. for each table: check the CSV header against the table's columns (stops
     on any missing or unexpected column), convert, COPY, count rows
  3. commit, then write docs/POSTGRES_LOAD_REPORT.md

Reads only the five canonical files in data/staging/. Connection settings come
from .env (POSTGRES_HOST/PORT/DB/USER/PASSWORD). Refuses to run against the
Superset metadata database.

NULLs: an empty CSV field is NULL (the same rule etl/validate_cleaned_data.py
uses). Values are loaded from the CSV text, not re-formatted floats, so
NUMERIC columns hold exactly what the staging file says.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import io
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from cleaning_common import OUTPUT_FILES, PROJECT_ROOT, STAGING_DIR

SCHEMA = "clean"
SCHEMA_SQL = PROJECT_ROOT / "sql" / "clean_schema.sql"
REPORT_PATH = PROJECT_ROOT / "docs" / "POSTGRES_LOAD_REPORT.md"

# staging dataset key (cleaning_common.OUTPUT_FILES) -> table in schema `clean`
TABLES = {
    "census_profile": "census_profile",
    "shelter_cost": "shelter_cost",
    "rental_market": "rental_market_windsor",
    "starts_completions": "starts_completions_windsor",
    "canada_rental_market": "rental_market_canada",
}

INTEGER_TYPES = {"integer", "bigint", "smallint"}
_INTEGER_TEXT = re.compile(r"^-?\d+(\.0+)?$")


class LoadError(RuntimeError):
    pass


def connect():
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        dbname = os.environ["POSTGRES_DB"]
        params = dict(host=os.environ["POSTGRES_HOST"], port=os.environ["POSTGRES_PORT"], dbname=dbname,
                      user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
    except KeyError as missing:
        raise LoadError(f"{missing.args[0]} is not set (see .env.example)") from None
    if dbname == os.environ.get("SUPERSET_METADATA_DB"):
        raise LoadError(f"POSTGRES_DB={dbname} is the Superset metadata database; refusing to use it")
    return psycopg2.connect(**params)


def read_staging(path: Path) -> pd.DataFrame:
    """Every column as text, exactly as written; empty field -> ''."""
    if not path.exists():
        raise LoadError(f"Staging file not found: {path}. Run etl/run_cleaning_pipeline.py first.")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def table_columns(cur, table: str) -> dict[str, str]:
    """column name -> information_schema data_type, in table order."""
    cur.execute("SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position", (SCHEMA, table))
    return dict(cur.fetchall())


def check_header(csv_columns: list[str], columns: dict[str, str], label: str) -> None:
    missing = [c for c in columns if c not in csv_columns]
    unexpected = [c for c in csv_columns if c not in columns]
    if missing or unexpected:
        raise LoadError(f"{label}: CSV header does not match {SCHEMA} table. "
                        f"Missing from CSV: {missing or 'none'}. Not in table: {unexpected or 'none'}.")


def convert_cell(text: str, data_type: str, where: str):
    """CSV text -> value for COPY. '' -> None (NULL); numbers are checked, not rounded."""
    if text == "":
        return None
    if data_type in INTEGER_TYPES:
        if not _INTEGER_TEXT.match(text):
            raise LoadError(f"{where}: {text!r} is not a whole number")
        return text.split(".")[0]
    if data_type == "numeric":
        try:
            Decimal(text)
        except InvalidOperation:
            raise LoadError(f"{where}: {text!r} is not a number") from None
    return text


def prepare_rows(df: pd.DataFrame, columns: dict[str, str], label: str) -> list[list]:
    check_header(list(df.columns), columns, label)
    ordered = df[list(columns)]
    rows = []
    for i, record in enumerate(ordered.itertuples(index=False), start=2):  # line 1 is the header
        rows.append([convert_cell(text, columns[col], f"{label} line {i}, {col}")
                     for col, text in zip(columns, record)])
    return rows


def copy_rows(cur, table: str, columns: list[str], rows: list[list]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)  # None -> unquoted empty field -> NULL below
    buffer.seek(0)
    column_list = ", ".join(columns)
    cur.copy_expert(f"COPY {SCHEMA}.{table} ({column_list}) FROM STDIN WITH (FORMAT csv, NULL '')", buffer)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(conn, staging_dir: Path = STAGING_DIR) -> list[dict]:
    results = []
    with conn:  # commit on success, roll back on any exception
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
            for key, table in TABLES.items():
                path = staging_dir / OUTPUT_FILES[key]
                df = read_staging(path)
                columns = table_columns(cur, table)
                if not columns:
                    raise LoadError(f"{SCHEMA}.{table} was not created by {SCHEMA_SQL.name}")
                rows = prepare_rows(df, columns, OUTPUT_FILES[key])
                copy_rows(cur, table, list(columns), rows)
                cur.execute(f"SELECT count(*) FROM {SCHEMA}.{table}")
                loaded = cur.fetchone()[0]
                if loaded != len(df):
                    raise LoadError(f"{SCHEMA}.{table}: loaded {loaded} rows but {path.name} has {len(df)}")
                print(f"  {SCHEMA}.{table:28} {loaded:6,} rows  <- data/staging/{path.name}")
                results.append({"table": table, "csv": path.name, "csv_rows": len(df), "loaded_rows": loaded,
                                "csv_sha256": sha256(path), "columns": columns})
    return results


def catalog(conn) -> dict:
    """Indexes and constraints of the clean schema, for the report."""
    with conn.cursor() as cur:
        cur.execute("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = %s "
                    "ORDER BY tablename, indexname", (SCHEMA,))
        indexes = cur.fetchall()
        cur.execute("""
            SELECT rel.relname, con.conname, con.contype, pg_get_constraintdef(con.oid)
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = %s
            ORDER BY rel.relname, con.contype, con.conname""", (SCHEMA,))
        constraints = cur.fetchall()
        cur.execute("SELECT current_database(), version()")
        database, version = cur.fetchone()
    return {"indexes": indexes, "constraints": constraints, "database": database, "version": version}


CONSTRAINT_TYPES = {"p": "PRIMARY KEY", "u": "UNIQUE", "c": "CHECK", "f": "FOREIGN KEY"}


def render_report(results: list[dict], cat: dict) -> str:
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# PostgreSQL Load Report",
        "",
        f"Generated by `etl/load_cleaned_to_postgres.py` on {now}.",
        f"Database: `{cat['database']}` ({cat['version'].split(',')[0]}). Schema: `{SCHEMA}`, "
        f"defined in `sql/clean_schema.sql`.",
        "Validation results are in [POSTGRES_VALIDATION.md](POSTGRES_VALIDATION.md).",
        "",
        "Scope: cleaned staging CSVs → PostgreSQL. No KPIs, no analytical views, no foreign keys between",
        "datasets (their geographies and periods differ). The old `sql/warehouse_*.sql` and",
        "`sql/story*_views.sql` files were not used.",
        "",
        "The schema and all five tables are rebuilt in one transaction on every run, so re-running",
        "replaces the data instead of duplicating it. An empty CSV field is loaded as NULL.",
        "",
        "## Tables loaded",
        "",
        "| Table | Source (`data/staging/`) | CSV rows | Loaded rows | CSV SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| `{SCHEMA}.{r['table']}` | `{r['csv']}` | {r['csv_rows']:,} | {r['loaded_rows']:,} | "
                     f"`{r['csv_sha256'][:16]}…` |")

    lines += ["", "## Columns", ""]
    for r in results:
        lines.append(f"### {SCHEMA}.{r['table']}")
        lines.append("")
        lines.append("| Column | Type |")
        lines.append("|---|---|")
        lines += [f"| `{c}` | {t} |" for c, t in r["columns"].items()]
        lines.append("")

    lines += ["## Indexes", "", "| Table | Index | Definition |", "|---|---|---|"]
    for table, name, definition in cat["indexes"]:
        lines.append(f"| `{table}` | `{name}` | `{definition.split(' USING ')[1]}` |")

    lines += ["", "## Constraints", "", "| Table | Constraint | Type | Definition |", "|---|---|---|---|"]
    for table, name, kind, definition in cat["constraints"]:
        definition = definition.replace("|", "\\|")
        lines.append(f"| `{table}` | `{name}` | {CONSTRAINT_TYPES.get(kind, kind)} | `{definition}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        print(f"Cannot connect to PostgreSQL: {exc}")
        return 1
    try:
        print(f"Loading data/staging/ into schema '{SCHEMA}'")
        results = load(conn)
        REPORT_PATH.write_text(render_report(results, catalog(conn)), encoding="utf-8")
        print(f"Committed. Report written: {REPORT_PATH}")
    except (LoadError, psycopg2.Error) as exc:
        print(f"LOAD FAILED (rolled back, database unchanged): {exc}")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
