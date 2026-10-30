"""
Extract Windsor CMA housing starts, completions and units under
construction by dwelling type, monthly, from Statistics Canada table
34-10-0154-01 ("Canada Mortgage and Housing Corporation, housing starts,
under construction and completions in selected census metropolitan
areas, monthly").

This closes the gap sql/story3_views.sql documented for Story 3: CMHC's
own quarterly workbook (etl/extract_cmhc_starts_completions.py) is
Canada/provinces only, so there was no Windsor-specific supply figure and
no multi-year series. StatCan republishes CMHC's Starts and Completions
Survey at CMA level in this table, Windsor included, monthly since 1972,
with the same 5 dwelling-type categories as the CMHC workbook (mapped to
the workbook's own labels below so both sources read the same way).

Keeps January 2016 onward: 10 full years (2016-2025) plus the current
partial year, which is enough for a decade-long trend and lines up with
the 2021 Census households figure used for the per-1,000-households rate
(sql/story3_views.sql). Older months are in the source if ever needed --
change FIRST_YEAR.

The full StatCan table is ~55 MB unzipped (every CMA), so the zip is
downloaded once to data/raw/statcan/ and only Windsor's rows are written
to staging. Re-running reuses the downloaded zip; pass --refresh to fetch
the latest release.

Licence: Statistics Canada Open Licence
(https://www.statcan.gc.ca/en/reference/licence).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_windsor_starts_completions.py
    .venv\\Scripts\\python.exe etl\\extract_windsor_starts_completions.py --refresh
"""

import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_ID = "34100154"
SOURCE_URL = f"https://www150.statcan.gc.ca/n1/tbl/csv/{TABLE_ID}-eng.zip"
SOURCE_ZIP = PROJECT_ROOT / "data" / "raw" / "statcan" / f"{TABLE_ID}-eng.zip"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_starts_completions_monthly.csv"

GEO = "Windsor, Ontario"
FIRST_YEAR = 2016

ACTIVITY_LABELS = {
    "Housing starts": "Starts",
    "Housing completions": "Completions",
    "Housing under construction": "Under Construction",
}

# StatCan's labels -> the CMHC workbook's own column names, so Story 3's
# Ontario and Windsor figures use one vocabulary.
DWELLING_TYPE_LABELS = {
    "Single-detached units": "Singles",
    "Semi-detached units": "Semis",
    "Row units": "Row",
    "Apartment and other unit types": "Apartment and Other",
    "Total units": "Total",
}


def download_source(refresh: bool) -> Path:
    if SOURCE_ZIP.exists() and not refresh:
        return SOURCE_ZIP
    SOURCE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(SOURCE_URL, timeout=120)
    resp.raise_for_status()
    SOURCE_ZIP.write_bytes(resp.content)
    return SOURCE_ZIP


def read_windsor_rows(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf, zf.open(f"{TABLE_ID}.csv") as fh:
        chunks = pd.read_csv(fh, dtype=str, encoding="utf-8-sig", chunksize=200_000)
        return pd.concat(chunk[chunk["GEO"] == GEO] for chunk in chunks)


def reshape(source: pd.DataFrame) -> pd.DataFrame:
    df = source.copy()
    df["period_year"] = df["REF_DATE"].str[:4].astype(int)
    df["period_month"] = df["REF_DATE"].str[5:7].astype(int)
    df = df[df["period_year"] >= FIRST_YEAR]

    unknown_activity = set(df["Housing estimates"]) - set(ACTIVITY_LABELS)
    unknown_dwelling = set(df["Type of unit"]) - set(DWELLING_TYPE_LABELS)
    if unknown_activity or unknown_dwelling:
        # Fail loud on a renamed category rather than silently dropping it.
        raise ValueError(f"Unmapped labels: activity={unknown_activity}, dwelling={unknown_dwelling}")

    return pd.DataFrame({
        "geography": "Windsor CMA",
        "dguid": df["DGUID"],
        "ref_month": df["REF_DATE"],
        "period_year": df["period_year"],
        "period_month": df["period_month"],
        "activity": df["Housing estimates"].map(ACTIVITY_LABELS),
        "dwelling_type": df["Type of unit"].map(DWELLING_TYPE_LABELS),
        "units": pd.to_numeric(df["VALUE"], errors="coerce"),
        "status": df["STATUS"].fillna(""),
    }).sort_values(["ref_month", "activity", "dwelling_type"])


def main(refresh: bool = False) -> pd.DataFrame:
    zip_path = download_source(refresh)
    out = reshape(read_windsor_rows(zip_path))
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)

    print(f"Wrote {len(out)} rows to {OUTPUT_CSV}")
    print(f"  months: {out['ref_month'].min()} to {out['ref_month'].max()}")
    print(f"  null units: {int(out['units'].isna().sum())}")
    return out


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
