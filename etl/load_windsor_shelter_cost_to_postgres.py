"""
Load the Windsor shelter-cost staging extract into PostgreSQL.

Reads data/staging/windsor_shelter_cost.csv (already filtered to Windsor CMA
by extract_windsor_shelter_cost.py) and loads it into a single staging table.
No aggregation, filtering or deduplication is done here -- that belongs in
SQL views built on top of this table, not in the load step.

Requires a running Postgres instance (see docker/docker-compose.yml) and a
.env file with POSTGRES_HOST/PORT/DB/USER/PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\load_windsor_shelter_cost_to_postgres.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost.csv"
TABLE_NAME = "windsor_shelter_cost"
CHUNK_SIZE = 10_000

# Explicit rename map (source CSV header -> SQL-friendly column name). This
# script is specific to this one table's known columns, so an explicit map is
# clearer and less error-prone than a generic sanitizing regex.
COLUMN_RENAME = {
    "REF_DATE": "ref_date",
    "GEO": "geo",
    "DGUID": "dguid",
    "Household total income groups (14)": "income_group",
    "Household type including census family structure (16)": "household_type",
    "Housing suitability (3)": "housing_suitability",
    "Dwelling condition (3)": "dwelling_condition",
    "Statistics (3C)": "statistic",
    "Shelter-cost-to-income ratio (5)": "shelter_cost_ratio",
    "Coordinate": "coordinate",
    "Tenure (3):Total - Tenure[1]": "tenure_total",
    "Symbol": "tenure_total_symbol",
    "Tenure (3):Owner[2]": "tenure_owner",
    "Symbol.1": "tenure_owner_symbol",
    "Tenure (3):Renter[3]": "tenure_renter",
    "Symbol.2": "tenure_renter_symbol",
}


def get_engine():
    load_dotenv(PROJECT_ROOT / ".env")
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    db = os.environ["POSTGRES_DB"]
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def load(csv_path: Path = STAGING_CSV, table_name: str = TABLE_NAME) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(f"Staging CSV not found: {csv_path}")

    engine = get_engine()
    total_rows = 0

    reader = pd.read_csv(csv_path, dtype=str, encoding="utf-8", chunksize=CHUNK_SIZE)
    for i, chunk in enumerate(reader):
        chunk = chunk.rename(columns=COLUMN_RENAME)
        chunk.to_sql(
            table_name,
            engine,
            if_exists="replace" if i == 0 else "append",
            index=False,
        )
        total_rows += len(chunk)

    with engine.connect() as conn:
        db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

    return {
        "rows_loaded_from_csv": total_rows,
        "rows_in_database_table": db_count,
        "table_name": table_name,
    }


if __name__ == "__main__":
    stats = load()
    print("Load complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
