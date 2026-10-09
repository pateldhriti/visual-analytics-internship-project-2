"""
Reshape the Windsor shelter-cost extract from wide to long: one row per
(income band x household type x tenure x shelter-cost-to-income band).

The source table has more than these 4 dimensions (housing suitability,
dwelling condition, statistics all vary too -- see docs/shelter_cost_audit.md).
To get one row per combination of exactly the 4 requested dimensions, this
script first restricts to the single baseline slice recommended in the audit
note -- Total housing suitability, Total dwelling condition, and the
"Number of private households" point-estimate statistic -- then melts tenure
(currently 3 separate columns: Total/Owner/Renter) into rows. Without that
restriction, the suitability/dwelling/statistics dimensions would multiply
the row count 27x beyond what "one row per income x household x tenure x
ratio combination" means, and the row-count check below would be comparing
against the wrong expectation.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\reshape_shelter_cost_long.py
"""

from pathlib import Path

import pandas as pd

from statcan_profiling import read_statcan_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost_long.csv"

INCOME_COL = "Household total income groups (14)"
HOUSEHOLD_COL = "Household type including census family structure (16)"
SUITABILITY_COL = "Housing suitability (3)"
DWELLING_COL = "Dwelling condition (3)"
STATISTIC_COL = "Statistics (3C)"
RATIO_COL = "Shelter-cost-to-income ratio (5)"

# tenure label -> (value column, symbol column) in the wide source
TENURE_COLUMNS = {
    "Total": ("Tenure (3):Total - Tenure[1]", "Symbol"),
    "Owner": ("Tenure (3):Owner[2]", "Symbol.1"),
    "Renter": ("Tenure (3):Renter[3]", "Symbol.2"),
}


def load_baseline(source_csv: Path = SOURCE_CSV) -> pd.DataFrame:
    """Load the wide extract, restricted to the Total-suitability /
    Total-dwelling-condition / point-estimate-statistic baseline slice."""
    df = read_statcan_csv(source_csv)
    baseline = df[
        (df[SUITABILITY_COL] == "Total - Housing suitability")
        & (df[DWELLING_COL] == "Total - Dwelling condition")
        & (df[STATISTIC_COL] == "Number of private households")
    ].copy()
    # Household type has 16 real categories but only 14 distinct text labels
    # (two pairs of categories share identical wording under different
    # branches -- see docs/shelter_cost_audit.md). Coordinate's 3rd segment
    # is the true StatCan household-type member ID and disambiguates them.
    baseline["household_type_member_id"] = baseline["Coordinate"].str.split(".").str[2]
    return baseline


def reshape_long(baseline: pd.DataFrame) -> pd.DataFrame:
    """Melt the 3 tenure columns into rows, one per tenure per source row."""
    id_cols = [
        "REF_DATE", "GEO", "DGUID",
        INCOME_COL, HOUSEHOLD_COL, "household_type_member_id", RATIO_COL,
        "Coordinate",
    ]
    frames = []
    for tenure_label, (value_col, symbol_col) in TENURE_COLUMNS.items():
        part = baseline[id_cols + [value_col, symbol_col]].copy()
        part["tenure"] = tenure_label
        part["value"] = pd.to_numeric(part[value_col], errors="coerce")
        part["symbol"] = part[symbol_col]
        part = part.drop(columns=[value_col, symbol_col])
        frames.append(part)

    long_df = pd.concat(frames, ignore_index=True)
    return long_df.rename(
        columns={
            INCOME_COL: "income_group",
            HOUSEHOLD_COL: "household_type",
            RATIO_COL: "shelter_cost_ratio",
        }
    )


def expected_row_count(baseline: pd.DataFrame) -> tuple[int, dict]:
    """Product of the 4 dimensions' true cardinalities, verified from the
    actual data rather than assumed from metadata."""
    n_income = baseline[INCOME_COL].nunique()
    n_household = baseline["household_type_member_id"].nunique()
    n_tenure = len(TENURE_COLUMNS)
    n_ratio = baseline[RATIO_COL].nunique()
    return n_income * n_household * n_tenure * n_ratio, {
        "income": n_income, "household_type": n_household,
        "tenure": n_tenure, "ratio": n_ratio,
    }


def verify_preserves_original(baseline: pd.DataFrame, long_df: pd.DataFrame) -> dict:
    """Check the reshape didn't drop, duplicate, or corrupt any values."""
    results = {}

    # 1. Value-count preservation: every wide tenure cell should appear
    #    exactly once in the long table (null or not).
    wide_value_count = sum(len(baseline) for _ in TENURE_COLUMNS)
    results["cell_count_preserved"] = wide_value_count == len(long_df)

    # 2. Non-null value preservation: same count of actual numbers, not just rows.
    wide_non_null = sum(
        pd.to_numeric(baseline[value_col], errors="coerce").notna().sum()
        for value_col, _ in TENURE_COLUMNS.values()
    )
    results["non_null_value_count_preserved"] = wide_non_null == long_df["value"].notna().sum()

    # 3. Symbol preservation: same count of non-null symbols.
    wide_symbols = sum(baseline[symbol_col].notna().sum() for _, symbol_col in TENURE_COLUMNS.values())
    results["symbol_count_preserved"] = wide_symbols == long_df["symbol"].notna().sum()

    # 4. Round-trip spot check: reconstruct a few wide rows from the long
    #    table and compare to the original, cell by cell.
    sample = baseline.sample(n=min(20, len(baseline)), random_state=0)
    mismatches = []
    for _, row in sample.iterrows():
        for tenure_label, (value_col, symbol_col) in TENURE_COLUMNS.items():
            match = long_df[
                (long_df["Coordinate"] == row["Coordinate"]) & (long_df["tenure"] == tenure_label)
            ]
            if len(match) != 1:
                mismatches.append((row["Coordinate"], tenure_label, "missing or duplicated"))
                continue
            long_value = match.iloc[0]["value"]
            wide_value = pd.to_numeric(row[value_col], errors="coerce")
            same = (pd.isna(long_value) and pd.isna(wide_value)) or long_value == wide_value
            if not same:
                mismatches.append((row["Coordinate"], tenure_label, f"wide={wide_value} long={long_value}"))
    results["round_trip_spot_check_rows"] = len(sample)
    results["round_trip_mismatches"] = mismatches

    return results


if __name__ == "__main__":
    baseline = load_baseline()
    long_df = reshape_long(baseline)

    expected, dim_counts = expected_row_count(baseline)
    actual = len(long_df)

    print("Baseline wide rows (Total suitability, Total dwelling condition, point estimate):", len(baseline))
    print("Dimension cardinalities (verified from data):", dim_counts)
    print(f"Expected long rows (income x household_type x tenure x ratio): {expected}")
    print(f"Actual long rows: {actual}")
    print(f"Match: {expected == actual}")
    print()

    checks = verify_preserves_original(baseline, long_df)
    print("Preservation checks:")
    for key, value in checks.items():
        if key != "round_trip_mismatches":
            print(f"  {key}: {value}")
    print(f"  round_trip_mismatches: {len(checks['round_trip_mismatches'])}")
    if checks["round_trip_mismatches"]:
        for m in checks["round_trip_mismatches"][:10]:
            print("    ", m)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(OUTPUT_CSV, index=False)
    print()
    print(f"Written: {OUTPUT_CSV} ({len(long_df)} rows)")
