"""
Load the long-format Windsor shelter-cost extract into PostgreSQL.

Reads data/staging/windsor_shelter_cost_long.csv (produced by
reshape_shelter_cost_long.py) and loads it into a single table. This is the
table Superset should query for dashboard charts -- one row per
(income x household_type x suitability x dwelling_condition x statistic x
ratio x tenure) combination, with no further filtering done here.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\load_windsor_shelter_cost_long_to_postgres.py
"""

from pathlib import Path

import pandas as pd

from load_windsor_shelter_cost_to_postgres import get_engine
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost_long.csv"
TABLE_NAME = "windsor_shelter_cost_long"
CHUNK_SIZE = 20_000


def load(csv_path: Path = STAGING_CSV, table_name: str = TABLE_NAME) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(f"Staging CSV not found: {csv_path}. Run reshape_shelter_cost_long.py first.")

    engine = get_engine()
    total_rows = 0

    reader = pd.read_csv(csv_path, dtype=str, encoding="utf-8", chunksize=CHUNK_SIZE)
    for i, chunk in enumerate(reader):
        chunk["value"] = pd.to_numeric(chunk["value"], errors="coerce")
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
