"""
Populate the warehouse fact tables for real, from the already-reshaped
staging CSVs. Until now sql/warehouse_schema.sql + create_warehouse_schema.py
only proved the schema works via a single rolled-back smoke-test row per
fact table (see docs/conceptual_er_model.md) -- this script does the actual
bulk load.

Loads all six fact tables, from seven staging CSVs -- one table per
source, per this project's schema rule (sql/warehouse_schema.sql):
  - fact_shelter_cost   <- data/staging/windsor_shelter_cost_long.csv (90,720 rows)
  - fact_census_profile <- data/staging/windsor_census_profile_long.csv (360 rows)
  - fact_rental_market  <- data/staging/windsor_rental_market.csv (1,395 rows), from
      etl/extract_windsor_rms.py's 9 Windsor-specific sheets.
      income_band_key is only set for Table 3.1.8's quintile rows
      (metric_type 'quintile_universe' / 'quintile_vacancy_rate'); every
      other metric_type has it NULL -- "not applicable", not missing.
  - fact_rental_market_comparison <- data/staging/rms_canada_comparison.csv
      (40 rows extracted, 36 loaded), from etl/extract_rms_canada_comparison.py
      -- a separate CMHC workbook (Canada RMS 2025, Table 1.0), so it gets
      its own fact table rather than being merged into fact_rental_market.
      4 comparator CMAs (London, Kitchener-Cambridge-Waterloo, Hamilton,
      St. Catharines-Niagara) in full, plus Windsor's turnover_rate and
      pct_change_rent rows only (not vacancy_rate/average_rent, which
      duplicate the Windsor-specific workbook's own Apartment-scope
      tables) -- see load_rms_canada_comparison_facts()'s docstring for
      exactly why.
  Tenure is always 'Renter' for both rental-market sources (this data is
  rental-only, per docs/conceptual_er_model.md).
  - fact_starts_completions <- data/staging/ontario_canada_starts_completions.csv
      (CMHC quarterly workbook, Ontario/Canada).
  - fact_windsor_starts_completions <-
      data/staging/windsor_starts_completions_monthly.csv (1,935 rows,
      Jan-2016 to Sep-2026), from etl/extract_windsor_starts_completions.py
      -- StatCan 34-10-0154-01, Windsor CMA monthly.

Every dimension key is resolved by joining on real values already verified
to match the seeded dimension tables exactly (geography DGUID, period
label, income-band label text, tenure name, zone label, bedroom-type
label) -- not assumed or guessed.

Safe to re-run: every fact table is truncated before loading.

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
RENTAL_MARKET_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_rental_market.csv"
RENTAL_MARKET_HISTORICAL_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_rental_market_historical.csv"
RMS_CANADA_COMPARISON_CSV = PROJECT_ROOT / "data" / "staging" / "rms_canada_comparison.csv"
STARTS_COMPLETIONS_CSV = PROJECT_ROOT / "data" / "staging" / "ontario_canada_starts_completions.csv"
WINDSOR_STARTS_COMPLETIONS_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_starts_completions_monthly.csv"


def fetch_dim(engine, table: str, key_col: str, *value_cols: str) -> pd.DataFrame:
    cols = ", ".join([key_col, *value_cols])
    return pd.read_sql(f"SELECT {cols} FROM warehouse.{table}", engine)


def copy_dataframe(engine, df: pd.DataFrame, table: str, raw_conn=None) -> int:
    """Bulk-load via Postgres COPY -- the only tractable approach at
    90k+ rows (see load_raw_files_to_postgres.py's load_csv_fast docstring
    for why row-by-row/batched INSERT is far too slow at this scale).

    If `raw_conn` is given, the COPY runs on that connection and the caller
    owns commit/rollback/close (so a truncate done earlier on the same
    connection rolls back together with a failed COPY, instead of a
    separately-committed truncate surviving a load failure -- see
    docs/code_review_affordability_etl.md finding 1). With no `raw_conn`,
    behaves exactly as before: opens, commits, and closes its own
    connection, for every other existing call site.
    """
    owns_conn = raw_conn is None
    if owns_conn:
        raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False)
        buf.seek(0)
        cols = ", ".join(f'"{c}"' for c in df.columns)
        cur.copy_expert(f'COPY warehouse."{table}" ({cols}) FROM STDIN WITH (FORMAT csv)', buf)
        if owns_conn:
            raw_conn.commit()
    finally:
        if owns_conn:
            raw_conn.close()
    return len(df)


def load_shelter_cost_facts(engine, raw_conn=None) -> dict:
    """`raw_conn`, if given, is forwarded to copy_dataframe() so the COPY
    shares a connection/transaction with whatever the caller already did on
    it (e.g. a truncate) -- see copy_dataframe()'s docstring."""
    source = pd.read_csv(SHELTER_COST_LONG_CSV, dtype=str)

    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    tenure = fetch_dim(engine, "dim_tenure", "tenure_key", "tenure_name")
    income_band = fetch_dim(engine, "dim_income_band", "income_band_key", "scheme", "band_label")
    income_band = income_band[income_band["scheme"] == "statcan_bracket"]

    df = source.copy()
    df = df.merge(period, left_on="ref_date", right_on="period_label", how="left")
    df = df.merge(tenure, left_on="tenure", right_on="tenure_name", how="left")
    df = df.merge(income_band, left_on="income_group", right_on="band_label", how="left")

    unmatched = {
        "period": int(df["period_key"].isna().sum()),
        "tenure": int(df["tenure_key"].isna().sum()),
        "income_band": int(df["income_band_key"].isna().sum()),
    }

    out = pd.DataFrame({
        "geography_key": df["dguid"],
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
        "data_quality_flag": df["data_quality_flag"],
        "source_coordinate": df["source_coordinate"],
    })

    rows = copy_dataframe(engine, out, "fact_shelter_cost", raw_conn=raw_conn)
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


def load_rental_market_facts(engine) -> dict:
    # keep_default_na=False + na_values=[''] : pandas' default na_values
    # list includes the literal string "N/A", which is also a real
    # dim_income_band label here (Table 3.1.8's "N/A" quintile row) -- left
    # at the default, read_csv silently turns that label into a true NaN,
    # breaking its income_band_key join. Only an actually-empty field
    # should become NaN.
    source = pd.read_csv(RENTAL_MARKET_CSV, dtype=str, keep_default_na=False, na_values=[""])

    zone = fetch_dim(engine, "dim_zone", "zone_key", "zone_label")
    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    bedroom_type = fetch_dim(engine, "dim_bedroom_type", "bedroom_type_key", "bedroom_type_label")
    dwelling_type = fetch_dim(engine, "dim_dwelling_type", "dwelling_type_key", "dwelling_type_label")
    tenure = fetch_dim(engine, "dim_tenure", "tenure_key", "tenure_name")
    renter_key = int(tenure.loc[tenure["tenure_name"] == "Renter", "tenure_key"].iloc[0])
    income_band = fetch_dim(engine, "dim_income_band", "income_band_key", "scheme", "band_label")
    income_band = income_band[income_band["scheme"] == "cmhc_quintile"]

    df = source.copy()
    df = df.merge(zone, left_on="zone", right_on="zone_label", how="left")
    df = df.merge(period, left_on="period_label", right_on="period_label", how="left")
    df = df.merge(bedroom_type, left_on="bedroom_type", right_on="bedroom_type_label", how="left")
    df = df.merge(dwelling_type, left_on="dwelling_type", right_on="dwelling_type_label", how="left")
    # income_quintile is only populated for Table 3.1.8 rows (quintile_universe /
    # quintile_vacancy_rate); every other metric_type has NaN here, which
    # correctly produces a NaN income_band_key (NULL) via the left merge --
    # "not applicable to this metric", not an unmatched/missing value.
    df = df.merge(income_band, left_on="income_quintile", right_on="band_label", how="left")
    # Nullable integer dtype: a plain float column would write NaN rows as
    # "16.0" to the COPY buffer, which Postgres rejects for an INT column --
    # Int64 writes a true blank field (-> SQL NULL) instead.
    df["income_band_key"] = df["income_band_key"].astype("Int64")
    is_quintile_metric = df["income_quintile"].notna()

    unmatched = {
        "zone": int(df["zone_key"].isna().sum()),
        "period": int(df["period_key"].isna().sum()),
        "bedroom_type": int(df["bedroom_type_key"].isna().sum()),
        "dwelling_type": int(df["dwelling_type_key"].isna().sum()),
        "income_band (quintile rows only)": int((is_quintile_metric & df["income_band_key"].isna()).sum()),
    }

    out = pd.DataFrame({
        "zone_key": df["zone_key"],
        "period_key": df["period_key"],
        "bedroom_type_key": df["bedroom_type_key"],
        "dwelling_type_key": df["dwelling_type_key"],
        "tenure_key": renter_key,
        "income_band_key": df["income_band_key"],
        "metric_type": df["metric_type"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
        "reliability_letter": df["reliability_letter"],
        "yoy_trend": df["yoy_trend"],
    })

    rows = copy_dataframe(engine, out, "fact_rental_market")
    return {"source_rows": len(source), "loaded_rows": rows, "unmatched_dimension_keys": unmatched}


def load_historical_rental_market_facts(engine) -> dict:
    """Oct-20 through Oct-23, from etl/extract_windsor_rms_historical.py --
    same fact_rental_market table, same 6 metric_types as the 2025-edition
    loader above, no income_quintile column (that script only extracts the
    6 time-series sheets, not Table 3.1.8). tenure is always 'Renter', same
    reasoning as load_rental_market_facts()."""
    source = pd.read_csv(RENTAL_MARKET_HISTORICAL_CSV, dtype=str)

    zone = fetch_dim(engine, "dim_zone", "zone_key", "zone_label")
    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    bedroom_type = fetch_dim(engine, "dim_bedroom_type", "bedroom_type_key", "bedroom_type_label")
    dwelling_type = fetch_dim(engine, "dim_dwelling_type", "dwelling_type_key", "dwelling_type_label")
    tenure = fetch_dim(engine, "dim_tenure", "tenure_key", "tenure_name")
    renter_key = int(tenure.loc[tenure["tenure_name"] == "Renter", "tenure_key"].iloc[0])

    df = source.copy()
    df = df.merge(zone, left_on="zone", right_on="zone_label", how="left")
    df = df.merge(period, left_on="period_label", right_on="period_label", how="left")
    df = df.merge(bedroom_type, left_on="bedroom_type", right_on="bedroom_type_label", how="left")
    df = df.merge(dwelling_type, left_on="dwelling_type", right_on="dwelling_type_label", how="left")

    unmatched = {
        "zone": int(df["zone_key"].isna().sum()),
        "period": int(df["period_key"].isna().sum()),
        "bedroom_type": int(df["bedroom_type_key"].isna().sum()),
        "dwelling_type": int(df["dwelling_type_key"].isna().sum()),
    }

    out = pd.DataFrame({
        "zone_key": df["zone_key"],
        "period_key": df["period_key"],
        "bedroom_type_key": df["bedroom_type_key"],
        "dwelling_type_key": df["dwelling_type_key"],
        "tenure_key": renter_key,
        "income_band_key": None,
        "metric_type": df["metric_type"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
        "reliability_letter": df["reliability_letter"],
        "yoy_trend": df["yoy_trend"],
    })

    rows = copy_dataframe(engine, out, "fact_rental_market")
    return {"source_rows": len(source), "loaded_rows": rows, "unmatched_dimension_keys": unmatched}


def load_rms_canada_comparison_facts(engine) -> dict:
    """Windsor (partially) + the 4 comparator CMAs from the national RMS
    workbook's Table 1.0, into fact_rental_market_comparison -- a separate
    table from fact_rental_market since this is a separate source
    workbook. zone_key resolves to dim_zone's zone_level='comparator_cma'
    rows (or the existing 'Windsor CMA' cma_total row).

    Windsor's vacancy_rate and average_rent rows here ARE genuine
    duplicates of Windsor-specific extraction already loaded
    (etl/extract_windsor_rms.py's Table 1.1.1/1.1.2, same Apartment scope)
    -- excluded, so the real metric isn't double-counted.

    Windsor's turnover_rate and pct_change_rent rows here are NOT
    duplicates: etl/extract_windsor_rms.py never extracted an
    apartment-only turnover table for Windsor (no Table 1.1.6 in its
    SHEETS config) or any percentage-change-of-rent table at all (1.1.5/
    2.1.5/3.1.5 were explicitly out of scope -- see
    docs/cmhc_rms_sheet_catalogue.md). Excluding ALL of Windsor's rows
    here (an earlier version of this function did) silently dropped these
    two real, unique metrics -- caught because
    warehouse.v_story4_affordability_gap (sql/story4_views.sql) came back
    with no Windsor row at all."""
    source = pd.read_csv(RMS_CANADA_COMPARISON_CSV, dtype=str)
    duplicated_for_windsor = source["metric_type"].isin(["vacancy_rate", "average_rent"])
    source = source[~((source["centre"] == "Windsor CMA") & duplicated_for_windsor)]

    zone = fetch_dim(engine, "dim_zone", "zone_key", "zone_label")
    period = fetch_dim(engine, "dim_period", "period_key", "period_label")
    bedroom_type = fetch_dim(engine, "dim_bedroom_type", "bedroom_type_key", "bedroom_type_label")
    dwelling_type = fetch_dim(engine, "dim_dwelling_type", "dwelling_type_key", "dwelling_type_label")
    tenure = fetch_dim(engine, "dim_tenure", "tenure_key", "tenure_name")
    renter_key = int(tenure.loc[tenure["tenure_name"] == "Renter", "tenure_key"].iloc[0])

    df = source.copy()
    df = df.merge(zone, left_on="centre", right_on="zone_label", how="left")
    df = df.merge(period, left_on="period_label", right_on="period_label", how="left")
    df = df.merge(bedroom_type, left_on="bedroom_type", right_on="bedroom_type_label", how="left")
    df = df.merge(dwelling_type, left_on="dwelling_type", right_on="dwelling_type_label", how="left")

    unmatched = {
        "zone": int(df["zone_key"].isna().sum()),
        "period": int(df["period_key"].isna().sum()),
        "bedroom_type": int(df["bedroom_type_key"].isna().sum()),
        "dwelling_type": int(df["dwelling_type_key"].isna().sum()),
    }

    out = pd.DataFrame({
        "zone_key": df["zone_key"],
        "period_key": df["period_key"],
        "bedroom_type_key": df["bedroom_type_key"],
        "dwelling_type_key": df["dwelling_type_key"],
        "tenure_key": renter_key,
        "metric_type": df["metric_type"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
        "reliability_letter": df["reliability_letter"],
        "yoy_trend": df["yoy_trend"],
    })

    rows = copy_dataframe(engine, out, "fact_rental_market_comparison")
    return {"source_rows": len(source), "loaded_rows": rows, "unmatched_dimension_keys": unmatched}


def load_starts_completions_facts(engine) -> dict:
    """No dimension keys to resolve -- province and dwelling_type are both
    degenerate text columns on fact_starts_completions (see
    sql/warehouse_schema.sql for why), so this is a straight copy, not a
    join-and-resolve like the other loaders."""
    source = pd.read_csv(STARTS_COMPLETIONS_CSV, dtype=str)

    out = pd.DataFrame({
        "province": source["province"],
        "period_type": source["period_type"],
        "period_label": source["period_label"],
        "activity": source["activity"],
        "dwelling_type": source["dwelling_type"],
        "units": pd.to_numeric(source["units"], errors="coerce"),
    })

    rows = copy_dataframe(engine, out, "fact_starts_completions")
    return {"source_rows": len(source), "loaded_rows": rows}


def load_windsor_starts_completions_facts(engine) -> dict:
    """Straight copy, same as load_starts_completions_facts() -- the
    extract already mapped StatCan's labels to this table's own
    activity/dwelling_type values (etl/extract_windsor_starts_completions.py)."""
    source = pd.read_csv(WINDSOR_STARTS_COMPLETIONS_CSV, dtype=str)

    out = pd.DataFrame({
        "dguid": source["dguid"],
        "ref_month": source["ref_month"],
        "period_year": source["period_year"].astype(int),
        "period_month": source["period_month"].astype(int),
        "activity": source["activity"],
        "dwelling_type": source["dwelling_type"],
        "units": pd.to_numeric(source["units"], errors="coerce"),
    })

    rows = copy_dataframe(engine, out, "fact_windsor_starts_completions")
    return {"source_rows": len(source), "loaded_rows": rows}


if __name__ == "__main__":
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE warehouse.fact_shelter_cost, warehouse.fact_census_profile, "
            "warehouse.fact_rental_market, warehouse.fact_rental_market_comparison, "
            "warehouse.fact_starts_completions, warehouse.fact_windsor_starts_completions"
        ))

    print("Loading fact_shelter_cost...")
    shelter_stats = load_shelter_cost_facts(engine)
    for key, value in shelter_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_census_profile...")
    census_stats = load_census_profile_facts(engine)
    for key, value in census_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_rental_market (Windsor)...")
    rental_stats = load_rental_market_facts(engine)
    for key, value in rental_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_rental_market_comparison...")
    comparison_stats = load_rms_canada_comparison_facts(engine)
    for key, value in comparison_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_rental_market (historical Windsor, Oct-20 to Oct-23)...")
    historical_stats = load_historical_rental_market_facts(engine)
    for key, value in historical_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_starts_completions...")
    starts_stats = load_starts_completions_facts(engine)
    for key, value in starts_stats.items():
        print(f"  {key}: {value}")

    print("Loading fact_windsor_starts_completions...")
    windsor_starts_stats = load_windsor_starts_completions_facts(engine)
    for key, value in windsor_starts_stats.items():
        print(f"  {key}: {value}")

    print()
    with engine.connect() as conn:
        for table in ("fact_shelter_cost", "fact_census_profile", "fact_rental_market",
                      "fact_rental_market_comparison", "fact_starts_completions",
                      "fact_windsor_starts_completions"):
            count = conn.execute(text(f'SELECT COUNT(*) FROM warehouse."{table}"')).scalar()
            print(f"warehouse.{table}: {count} rows")

    # Validation report produced on every load, not a separate manual step --
    # etl/validate_rental_market_data.py re-checks the tables that were just
    # loaded (row counts, rent/vacancy ranges, duplicate keys, reliability
    # letters) and writes its sections of docs/data_quality_report.md.
    print()
    print("Running rental-market data-quality checks...")
    import validate_rental_market_data as rmv

    live_rental_df = rmv.fetch_live_fact_rental_market(engine)
    rmv.update_report(rmv.render_section(
        rmv.check_row_counts(live_rental_df, rmv.STAGING_SOURCES),
        rmv.check_ranges(live_rental_df),
        rmv.check_duplicate_keys(live_rental_df),
        rmv.check_reliability_letters(live_rental_df),
        rmv.SECTION_MARKER_START, rmv.SECTION_MARKER_END,
        "## Rental market tables (CMHC RMS -- Windsor, historical)",
        "Source: `warehouse.fact_rental_market` (2 staging sources -> 1 table)",
    ), rmv.SECTION_MARKER_START, rmv.SECTION_MARKER_END)

    live_comparison_df = rmv.fetch_live_fact_rental_market_comparison(engine)
    rmv.update_report(rmv.render_section(
        rmv.check_row_counts(live_comparison_df, rmv.COMPARISON_STAGING_SOURCES, rmv.COMPARISON_KNOWN_EXCLUSIONS),
        rmv.check_ranges(live_comparison_df),
        rmv.check_duplicate_keys(live_comparison_df),
        rmv.check_reliability_letters(live_comparison_df),
        rmv.COMPARISON_SECTION_MARKER_START, rmv.COMPARISON_SECTION_MARKER_END,
        "## Rental market comparison table (CMHC Canada RMS 2025)",
        "Source: `warehouse.fact_rental_market_comparison` (1 staging source -> 1 table)",
    ), rmv.COMPARISON_SECTION_MARKER_START, rmv.COMPARISON_SECTION_MARKER_END)
    print(f"  Written: {rmv.REPORT_MD}")
