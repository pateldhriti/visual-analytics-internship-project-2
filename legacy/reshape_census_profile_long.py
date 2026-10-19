"""
Reshape the Windsor Census Profile extract from wide to long: one row per
(characteristic x measure_type x sex), instead of one row per characteristic
with 6 separate value/symbol column pairs.

The source has 2 dimensions packed into column names rather than rows --
measure_type (COUNT vs RATE) and sex (Total / Men+ / Women+). This script
melts both out: each of the 60 wide rows becomes exactly 6 long rows (one
per measure_type x sex combination), whether or not that combination is
populated for a given characteristic -- a null value with symbol "..."
means "not applicable" for that characteristic (e.g. most household-level
characteristics have no sex breakdown), not a dropped row.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\reshape_census_profile_long.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_census_profile.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_census_profile_long.csv"

ID_COLS = [
    "CENSUS_YEAR", "DGUID", "ALT_GEO_CODE", "GEO_LEVEL", "GEO_NAME",
    "TNR_SF", "TNR_LF", "DATA_QUALITY_FLAG",
    "CHARACTERISTIC_ID", "CHARACTERISTIC_NAME", "CHARACTERISTIC_NOTE",
]

# (measure_type, sex) -> (value column, symbol column) in the wide source
MELT_COLUMNS = {
    ("count", "total"): ("C1_COUNT_TOTAL", "SYMBOL"),
    ("count", "men"): ("C2_COUNT_MEN+", "SYMBOL.1"),
    ("count", "women"): ("C3_COUNT_WOMEN+", "SYMBOL.2"),
    ("rate", "total"): ("C10_RATE_TOTAL", "SYMBOL.3"),
    ("rate", "men"): ("C11_RATE_MEN+", "SYMBOL.4"),
    ("rate", "women"): ("C12_RATE_WOMEN+", "SYMBOL.5"),
}


def load_source(source_csv: Path = SOURCE_CSV) -> pd.DataFrame:
    """Load the full wide extract (all 60 rows, no filtering), every column
    as a string so published values and symbols are preserved exactly."""
    if not source_csv.exists():
        raise FileNotFoundError(f"Source CSV not found: {source_csv}")
    return pd.read_csv(source_csv, dtype=str)


def reshape_long(source: pd.DataFrame) -> pd.DataFrame:
    """Melt the 6 (measure_type, sex) column pairs into rows; every other
    column stays as-is on every resulting row."""
    frames = []
    for (measure_type, sex), (value_col, symbol_col) in MELT_COLUMNS.items():
        part = source[ID_COLS + [value_col, symbol_col]].copy()
        part["measure_type"] = measure_type
        part["sex"] = sex
        part["value"] = pd.to_numeric(part[value_col], errors="coerce")
        part["symbol"] = part[symbol_col]
        part = part.drop(columns=[value_col, symbol_col])
        frames.append(part)

    return pd.concat(frames, ignore_index=True)


def verify_preserves_original(source: pd.DataFrame, long_df: pd.DataFrame) -> dict:
    """Check the reshape didn't drop, duplicate, or corrupt any values."""
    results = {}

    # 1. Row-count preservation: every wide characteristic x melt-column
    #    pair should appear exactly once in the long table.
    expected_rows = len(source) * len(MELT_COLUMNS)
    results["expected_long_rows"] = expected_rows
    results["actual_long_rows"] = len(long_df)
    results["row_count_preserved"] = expected_rows == len(long_df)

    # 2. Non-null value preservation: same count of actual numbers, not just rows.
    wide_non_null = sum(
        pd.to_numeric(source[value_col], errors="coerce").notna().sum()
        for value_col, _ in MELT_COLUMNS.values()
    )
    results["non_null_value_count_preserved"] = wide_non_null == long_df["value"].notna().sum()

    # 3. Symbol preservation: same count of non-null symbols.
    wide_symbols = sum(source[symbol_col].notna().sum() for _, symbol_col in MELT_COLUMNS.values())
    results["symbol_count_preserved"] = wide_symbols == long_df["symbol"].notna().sum()

    # 4. Round-trip spot check: reconstruct every wide row from the long
    #    table (small source, so check all of it rather than sampling) and
    #    compare to the original, cell by cell.
    mismatches = []
    for _, row in source.iterrows():
        for (measure_type, sex), (value_col, symbol_col) in MELT_COLUMNS.items():
            match = long_df[
                (long_df["CHARACTERISTIC_ID"] == row["CHARACTERISTIC_ID"])
                & (long_df["measure_type"] == measure_type)
                & (long_df["sex"] == sex)
            ]
            if len(match) != 1:
                mismatches.append((row["CHARACTERISTIC_ID"], measure_type, sex, "missing or duplicated"))
                continue
            long_value = match.iloc[0]["value"]
            wide_value = pd.to_numeric(row[value_col], errors="coerce")
            same = (pd.isna(long_value) and pd.isna(wide_value)) or long_value == wide_value
            if not same:
                mismatches.append((row["CHARACTERISTIC_ID"], measure_type, sex, f"wide={wide_value} long={long_value}"))
    results["round_trip_checked_rows"] = len(source)
    results["round_trip_mismatches"] = mismatches

    return results


if __name__ == "__main__":
    source = load_source()
    long_df = reshape_long(source)
    checks = verify_preserves_original(source, long_df)

    print("Source wide rows:", len(source))
    print("Melt columns (measure_type x sex):", len(MELT_COLUMNS))
    print(f"Expected long rows: {checks['expected_long_rows']}")
    print(f"Actual long rows: {checks['actual_long_rows']}")
    print(f"Match: {checks['row_count_preserved']}")
    print()

    print("Preservation checks:")
    for key, value in checks.items():
        if key not in ("round_trip_mismatches", "expected_long_rows", "actual_long_rows"):
            print(f"  {key}: {value}")
    print(f"  round_trip_mismatches: {len(checks['round_trip_mismatches'])}")
    if checks["round_trip_mismatches"]:
        for m in checks["round_trip_mismatches"][:10]:
            print("    ", m)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(OUTPUT_CSV, index=False)
    print()
    print(f"Written: {OUTPUT_CSV} ({len(long_df)} rows)")
