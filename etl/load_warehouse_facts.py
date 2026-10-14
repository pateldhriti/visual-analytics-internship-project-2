"""
Populate the warehouse fact tables for real, from the already-reshaped
staging CSVs. Until now sql/warehouse_schema.sql + create_warehouse_schema.py
only proved the schema works via a single rolled-back smoke-test row per
fact table (see docs/conceptual_er_model.md) -- this script does the actual
bulk load.

Loads two of the three fact tables (the ones with reshaped staging data
ready):
  - fact_shelter_cost  <- data/staging/windsor_shelter_cost_long.csv (90,720 rows)
  - fact_census_profile <- data/staging/windsor_census_profile_long.csv (360 rows)

fact_rental_market is NOT loaded here: the CMHC Windsor RMS workbook has
been profiled (docs/cmhc_rms_sheet_catalogue.md) but never actually
extracted into a clean staging file -- that's a separate, larger task
(29 sheets, several different layouts), not something to improvise as a
side effect of this script.

Every dimension key is resolved by joining on real values already verified
to match the seeded dimension tables exactly (geography DGUID, period
label, income-band label text, tenure name) -- not assumed or guessed.

Safe to re-run: both fact tables are truncated before loading.

Run from the project virtual environment (after etl/create_warehouse_schema.py):
    .venv\\Scripts\\python.exe etl\\load_warehouse_facts.py
"""

import io
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHELTER_COST_LONG_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost_long.csv"
CENSUS_PROFILE_LONG_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_census_profile_long.csv"


def fetch_dim(engine, table: str, key_col: str, *value_cols: str) -> pd.DataFrame:
    cols = ", ".join([key_col, *value_cols])
    return pd.read_sql(f"SELECT {cols} FROM warehouse.{table}", engine)


def copy_dataframe(engine, df: pd.DataFrame, table: str) -> int:
    """Bulk-load via Postgres COPY -- the only tractable approach at
    90k+ rows (see load_raw_files_to_postgres.py's load_csv_fast docstring
    for why row-by-row/batched INSERT is far too slow at this scale)."""
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False)
        buf.seek(0)
        cols = ", ".join(f'"{c}"' for c in df.columns)
        cur.copy_expert(f'COPY warehouse."{table}" ({cols}) FROM STDIN WITH (FORMAT csv)', buf)
        raw_conn.commit()
    finally:
        raw_conn.close()
    return len(df)


def load_shelter_cost_facts(engine) -> dict:
    source = pd.read_csv(SHELTER_COST_LONG_CSV, dtype=str)

    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    tenure = fetch_dim(engine, "dim_tenure", "tenure_key", "tenure_name")
    income_band = fetch_dim(engine, "dim_income_band", "income_band_key", "scheme", "band_label")
    income_band = income_band[income_band["scheme"] == "statcan_bracket"]

    df = source.copy()
    df = df.merge(period, left_on="REF_DATE", right_on="period_label", how="left")
    df = df.merge(tenure, left_on="tenure", right_on="tenure_name", how="left")
    df = df.merge(income_band, left_on="income_group", right_on="band_label", how="left")

    unmatched = {
        "period": int(df["period_key"].isna().sum()),
        "tenure": int(df["tenure_key"].isna().sum()),
        "income_band": int(df["income_band_key"].isna().sum()),
    }

    out = pd.DataFrame({
        "geography_key": df["DGUID"],
        "period_key": df["period_key"],
        "income_band_key": df["income_band_key"],
        "household_type_key": df["household_type_member_id"],
        "tenure_key": df["tenure_key"],
        "housing_suitability": df["housing_suitability"],
        "dwelling_condition": df["dwelling_condition"],
        "statistic": df["statistic"],
        "shelter_cost_ratio": df["shelter_cost_ratio"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
        "symbol": df["symbol"],
        "source_coordinate": df["Coordinate"],
    })

    rows = copy_dataframe(engine, out, "fact_shelter_cost")
    return {"source_rows": len(source), "loaded_rows": rows, "unmatched_dimension_keys": unmatched}


def load_census_profile_facts(engine) -> dict:
    source = pd.read_csv(CENSUS_PROFILE_LONG_CSV, dtype=str)

    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    df = source.merge(period, left_on="CENSUS_YEAR", right_on="period_label", how="left")

    unmatched = {"period": int(df["period_key"].isna().sum())}

    out = pd.DataFrame({
        "geography_key": df["DGUID"],
        "period_key": df["period_key"],
        "characteristic_id": df["CHARACTERISTIC_ID"],
        "characteristic_name": df["CHARACTERISTIC_NAME"],
        "measure_type": df["measure_type"],
        "sex": df["sex"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
        "symbol": df["symbol"],
    })

    rows = copy_dataframe(engine, out, "fact_census_profile")
    return {"source_rows": len(source), "loaded_rows": rows, "unmatched_dimension_keys": unmatched}


if __name__ == "__main__":
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE warehouse.fact_shelter_cost, warehouse.fact_census_profile"))

    print("Loading fact_shelter_cost...")
    shelter_stats = load_shelter_cost_facts(engine)
    for key, value in shelter_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_census_profile...")
    census_stats = load_census_profile_facts(engine)
    for key, value in census_stats.items():
        print(f"  {key}: {value}")

    print()
    with engine.connect() as conn:
        for table in ("fact_shelter_cost", "fact_census_profile", "fact_rental_market"):
            count = conn.execute(text(f'SELECT COUNT(*) FROM warehouse."{table}"')).scalar()
            print(f"warehouse.{table}: {count} rows")
