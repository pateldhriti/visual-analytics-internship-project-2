"""
Clean StatCan table 98-10-0252-01 (shelter-cost-to-income ratio by tenure),
from the actual 2,389-row Windsor CMA database-loading extract.

Source: data/raw/statcan/9810025201_databaseLoadingData (1).csv
  - long format already: one row per (income group x household type x
    suitability x dwelling condition x statistic x ratio x tenure)
  - only the Total suitability / Total dwelling condition / "Number of private
    households" slices are present in this extract
  - suppression lives in STATUS ('x' = suppressed, value blank; '...' = not
    applicable, value published as 0); SYMBOL is empty throughout

Output: data/staging/windsor_shelter_cost.csv -- one row per source row, no
aggregation and no percentages (those belong to the later SQL phase).

Household type has 16 categories but only 14 distinct labels (two "Without
children" / "With children" pairs under different parents), so every
dimension keeps the StatCan member id parsed from COORDINATE
(geo.income.household.suitability.dwelling.statistic.ratio.tenure).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cleaning_common import RAW_DIR, RAW_FILES, STAGING_DIR, STATCAN_KEEPS_VALUE, normalize_text, statcan_status

OUTPUT_NAME = "windsor_shelter_cost.csv"
EXPECTED_GEO = "Windsor (CMA), Ont."

DIMENSIONS = {
    # raw column -> (clean column, COORDINATE segment index)
    "Household total income groups (14)": ("income_group", 1),
    "Household type including census family structure (16)": ("household_type", 2),
    "Housing suitability (3)": ("housing_suitability", 3),
    "Dwelling condition (3)": ("dwelling_condition", 4),
    "Statistics (3C)": ("statistic", 5),
    "Shelter-cost-to-income ratio (5)": ("shelter_cost_ratio", 6),
    "Tenure (3)": ("tenure", 7),
}

# Source columns that carry no information in this extract (constant or empty
# for every row); dropped, and checked to still be constant on every run.
CONSTANT_COLUMNS = ["UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR", "SYMBOL", "TERMINATED", "DECIMALS"]

# Income "groups" that are dollar statistics rather than household-count brackets.
DOLLAR_INCOME_ROWS = {"Median total income of household ($)", "Average total income of household ($)"}


def read_raw(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    return pd.read_csv(raw_dir / RAW_FILES["shelter_cost_csv"], dtype=str, encoding="utf-8-sig", keep_default_na=False)


def clean_rows(raw: pd.DataFrame) -> pd.DataFrame:
    not_constant = [c for c in CONSTANT_COLUMNS if raw[c].nunique() > 1]
    if not_constant:
        raise ValueError(f"Columns expected to be constant now vary: {not_constant}")
    geos = set(raw["GEO"].map(normalize_text))
    if geos != {EXPECTED_GEO}:
        raise ValueError(f"Unexpected geography in shelter-cost file: {sorted(geos)}")

    segments = raw["COORDINATE"].str.strip().str.split(".", expand=True)
    out = pd.DataFrame({
        "ref_year": pd.to_numeric(raw["REF_DATE"]).astype(int),
        "geography": "Windsor CMA",
        "source_geography_label": raw["GEO"].map(normalize_text),
        "dguid": raw["DGUID"].str.strip(),
    })
    for raw_col, (clean_col, seg) in DIMENSIONS.items():
        out[clean_col] = raw[raw_col].map(normalize_text)
        out[f"{clean_col}_member_id"] = segments[seg].astype(int)

    out["coordinate"] = raw["COORDINATE"].str.strip()
    out["measure_kind"] = out["income_group"].map(lambda g: "dollars" if g in DOLLAR_INCOME_ROWS else "household_count")
    out["raw_value"] = raw["VALUE"]
    out["status_code"] = raw["STATUS"].map(normalize_text)
    out["value_status"] = raw["STATUS"].map(statcan_status)
    numeric = pd.to_numeric(raw["VALUE"].replace("", None), errors="raise")
    # '...' rows publish a 0 that means "not applicable", not zero households.
    out["value"] = numeric.where(out["value_status"].isin(STATCAN_KEEPS_VALUE))

    cols = ["ref_year", "geography", "source_geography_label", "dguid"]
    for _, (clean_col, _) in DIMENSIONS.items():
        cols += [clean_col, f"{clean_col}_member_id"]
    cols += ["coordinate", "measure_kind", "value", "raw_value", "status_code", "value_status"]
    return out[cols]


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR) -> dict:
    raw = read_raw(raw_dir)
    cleaned = clean_rows(raw)
    duplicates = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates()

    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(out_dir / OUTPUT_NAME, index=False, encoding="utf-8")
    return {
        "output": OUTPUT_NAME,
        "raw_rows": len(raw),
        "cleaned_rows": len(cleaned),
        "exact_duplicates_removed": duplicates,
        "dropped_constant_columns": CONSTANT_COLUMNS,
        "value_status_counts": cleaned["value_status"].value_counts().to_dict(),
        "full_cross_product_size": int(
            cleaned[[f"{c}_member_id" for c, _ in DIMENSIONS.values()]].nunique().prod()
        ),
    }


if __name__ == "__main__":
    for key, value in clean().items():
        print(f"{key}: {value}")
