"""
Load every raw source file under data/raw/ (CSV and Excel) into a Postgres
`staging` schema, as-is -- no cleaning, filtering, or column interpretation.

This is the raw landing layer: every row/sheet lands with generic column
names (col_1, col_2, ...) plus _source_file (and _source_sheet for Excel)
and _loaded_at tagging columns, so later cleaning scripts always have an
untouched copy of exactly what was downloaded to fall back on -- independent
of whatever filtering/renaming a specific extraction script (like
extract_windsor_shelter_cost.py) applies.

Two load strategies per CSV:
- Fast path: pandas (chunked read) + Postgres COPY (bulk load), for
  well-formed CSVs (every row has the same column count). Used for the
  1.28GB national shelter-cost file -- COPY, not row-by-row/batched INSERT,
  is what makes a file that size tractable.
- Lenient fallback: Python's csv module (which never raises on ragged rows,
  unlike pandas' C engine), padding short rows to the file's max column
  count. Used for 98100252_MetaData.csv, which concatenates several
  differently-shaped sections in one file.
  Guarded by a size threshold: the lenient path reads the whole file into
  memory, so it is only attempted for files under LENIENT_MAX_BYTES. A large
  file that fails the fast path is skipped with a clear error instead of
  risking an out-of-memory read.

Safe to re-run: every table is dropped and recreated (if_exists="replace")
on each run, so re-running just refreshes the data and the _loaded_at tag --
never duplicates or errors on a second run.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\load_raw_staging.py
"""

import csv
import datetime
import io
import re
from pathlib import Path

import openpyxl
import pandas as pd
from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA = "staging"
READ_CHUNK_SIZE = 200_000
# Postgres caps a single query at 65,535 bound parameters. The widest table
# here has ~30 columns after tagging, so 1,000 rows/batch (~30,000 params)
# stays safely under that regardless of which file is being loaded.
INSERT_CHUNK_SIZE = 1_000
LENIENT_MAX_BYTES = 200 * 1024 * 1024  # 200MB -- lenient path loads the whole file into memory


def sanitize_table_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    name = re.sub(r"_+", "_", name).strip("_")
    if name[:1].isdigit():
        name = "t_" + name
    return name[:63]  # Postgres identifier limit


def ensure_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))


def load_csv_fast(path: Path, engine, table_name: str, loaded_at: str) -> int:
    """Well-formed CSV: read in chunks, bulk-load via Postgres COPY.

    Row-by-row/multi-row INSERT (even batched) is far too slow for a
    multi-million-row file -- an earlier version of this script used
    to_sql(method="multi") and was still only 12% through the 5M-row
    shelter-cost file after 16 minutes of CPU time. COPY is the correct,
    standard tool for bulk-loading into Postgres and is orders of magnitude
    faster.
    """
    total = 0
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        reader = pd.read_csv(path, dtype=str, encoding="utf-8-sig", chunksize=READ_CHUNK_SIZE)
        table_created = False
        for chunk in reader:
            chunk["_source_file"] = path.name
            chunk["_loaded_at"] = loaded_at
            if not table_created:
                chunk.head(0).to_sql(table_name, engine, schema=SCHEMA, if_exists="replace", index=False)
                table_created = True
            buf = io.StringIO()
            chunk.to_csv(buf, index=False, header=False)
            buf.seek(0)
            cols = ", ".join(f'"{c}"' for c in chunk.columns)
            cur.copy_expert(f'COPY {SCHEMA}.{table_name} ({cols}) FROM STDIN WITH (FORMAT csv)', buf)
            total += len(chunk)
        raw_conn.commit()
    finally:
        raw_conn.close()
    return total


def load_csv_lenient(path: Path, engine, table_name: str, loaded_at: str) -> int:
    """Ragged CSV fallback: every row as raw fields via the csv module, padded
    to the file's max column count, generic column names. Loads the whole
    file into memory -- only called for files under LENIENT_MAX_BYTES."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    max_cols = max((len(r) for r in rows), default=0)
    col_names = [f"col_{i + 1}" for i in range(max_cols)]
    padded = [r + [None] * (max_cols - len(r)) for r in rows]
    df = pd.DataFrame(padded, columns=col_names)
    df["_source_file"] = path.name
    df["_loaded_at"] = loaded_at
    df.to_sql(table_name, engine, schema=SCHEMA, if_exists="replace", index=False,
              method="multi", chunksize=INSERT_CHUNK_SIZE)
    return len(df)


def load_csv(path: Path, engine, loaded_at: str) -> dict:
    table_name = sanitize_table_name(path.stem)
    try:
        rows = load_csv_fast(path, engine, table_name, loaded_at)
        return {"file": str(path.relative_to(PROJECT_ROOT)), "table": f"{SCHEMA}.{table_name}",
                "rows": rows, "method": "fast (well-formed)"}
    except Exception as exc:
        if path.stat().st_size > LENIENT_MAX_BYTES:
            return {"file": str(path.relative_to(PROJECT_ROOT)), "table": None,
                     "rows": 0, "method": f"SKIPPED -- fast path failed ({exc}) and file "
                     f"exceeds {LENIENT_MAX_BYTES // (1024*1024)}MB, too large for the "
                     f"whole-file-in-memory lenient fallback"}
        rows = load_csv_lenient(path, engine, table_name, loaded_at)
        return {"file": str(path.relative_to(PROJECT_ROOT)), "table": f"{SCHEMA}.{table_name}",
                "rows": rows, "method": "lenient (ragged rows)"}


def load_excel(path: Path, engine, loaded_at: str) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    results = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = [list(row) for row in ws.iter_rows(values_only=True)]
        max_cols = max((len(r) for r in rows), default=0)
        col_names = [f"col_{i + 1}" for i in range(max_cols)]
        padded = [list(r) + [None] * (max_cols - len(r)) for r in rows]
        df = pd.DataFrame(padded, columns=col_names)
        df["_source_file"] = path.name
        df["_source_sheet"] = sheet_name
        df["_loaded_at"] = loaded_at
        table_name = sanitize_table_name(f"{path.stem}_{sheet_name}")
        df.to_sql(table_name, engine, schema=SCHEMA, if_exists="replace", index=False,
                  method="multi", chunksize=INSERT_CHUNK_SIZE)
        results.append({"file": str(path.relative_to(PROJECT_ROOT)), "sheet": sheet_name,
                         "table": f"{SCHEMA}.{table_name}", "rows": len(df)})
    wb.close()
    return results


if __name__ == "__main__":
    engine = get_engine()
    ensure_schema(engine)
    loaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    csv_files = sorted(RAW_DIR.rglob("*.csv"))
    excel_files = sorted(RAW_DIR.rglob("*.xlsx"))

    print(f"Found {len(csv_files)} CSV file(s) and {len(excel_files)} Excel file(s) under {RAW_DIR}")
    print()

    summary = []
    for path in csv_files:
        result = load_csv(path, engine, loaded_at)
        summary.append(result)
        print(f"  {result['file']} -> {result['table']} ({result['rows']} rows, {result['method']})")

    for path in excel_files:
        for result in load_excel(path, engine, loaded_at):
            summary.append(result)
            print(f"  {result['file']} [{result['sheet']}] -> {result['table']} ({result['rows']} rows)")

    print()
    print(f"Loaded {sum(1 for r in summary if r['table'])} tables into schema '{SCHEMA}' "
          f"({sum(1 for r in summary if not r['table'])} skipped).")
