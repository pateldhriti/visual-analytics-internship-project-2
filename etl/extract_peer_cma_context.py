"""
Extract Windsor's and its four comparison cities' rows from three StatCan
files the project already downloads, for the combined Story 5 views.

    98-10-0252-01  shelter cost by income and tenure (2021 Census, incomes for 2020)
                   -> renter households by income band, median renter income,
                      renters spending 30%+ of income on shelter
    98-401-X2021002 Census Profile (2021)
                   -> population in 2016 and 2021, private households and the
                      people in them, renter households, median household
                      income, % of tenants spending 30%+, median rent paid
    34-10-0154-01  monthly housing starts and completions
                   -> yearly starts and completions (total and apartments),
                      full calendar years from 2016

The Story 1-4 extracts keep only Windsor; Story 4's rents already cover the
four comparison cities (CMHC Rental Market Survey). This script adds the
same cities' incomes, households and construction, so Windsor can be
compared with them on more than rent.

Cities are matched by the 3-digit CMA code that ends every DGUID
(2021S0503559, and 2011S0503559 in the starts table), not by name, because
each file spells the names differently.

Output: data/staging/peer_cma_context.csv, long format
(cma_code, cma_name, source_table, indicator, tenure, category,
period_year, value). Loaded by etl/load_peer_cma_context.py.

Licence: Statistics Canada Open Licence
(https://www.statcan.gc.ca/en/reference/licence).

Run from the project virtual environment (the 1.3 GB shelter-cost file is
streamed in chunks; it takes a few minutes):
    .venv\\Scripts\\python.exe etl\\extract_peer_cma_context.py
"""

import csv
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
SHELTER_CSV = RAW / "shelter_cost" / "98100252.csv"
PROFILE_CSV = RAW / "statcan" / "98-401-X2021002_English_CSV_data.csv"
STARTS_ZIP = RAW / "statcan" / "34100154-eng.zip"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "peer_cma_context.csv"

# CMA code -> the name used by Story 4 (warehouse.v_story4_rent_comparison).
CMAS = {
    "559": "Windsor CMA",
    "555": "London CMA",
    "537": "Hamilton CMA",
    "539": "St. Catharines-Niagara CMA",
    "541": "Kitchener-Cambridge-Waterloo CMA",
}

FIRST_START_YEAR = 2016
CHUNK_SIZE = 200_000

COLUMNS = ["cma_code", "cma_name", "source_table", "indicator", "tenure", "category", "period_year", "value"]

# --- 98-10-0252-01 -----------------------------------------------------------
SHELTER_TOTALS = {
    "Household type including census family structure (16)": "Total - Household type including census family structure",
    "Housing suitability (3)": "Total - Housing suitability",
    "Dwelling condition (3)": "Total - Dwelling condition",
    "Statistics (3C)": "Number of private households",
}
INCOME_COL = "Household total income groups (14)"
RATIO_COL = "Shelter-cost-to-income ratio (5)"
TENURE_COLS = {"Tenure (3):Total - Tenure[1]": "Total", "Tenure (3):Renter[3]": "Renter"}

# --- 98-401-X2021002 ---------------------------------------------------------
# CHARACTERISTIC_ID -> (indicator, tenure). IDs checked against the 2021
# release's characteristic names; a name check below guards against a
# re-numbered release.
PROFILE_ITEMS = {
    1: ("population_2021", "Total", "Population, 2021"),
    2: ("population_2016", "Total", "Population, 2016"),
    50: ("private_households", "Total", "Total - Private households by household size"),
    56: ("persons_in_private_households", "Total", "Number of persons in private households"),
    1416: ("renter_households", "Renter", "Renter"),
    243: ("median_household_income", "Total", "Median total income of household in 2020"),
    1492: ("pct_spending_30pct_plus", "Renter", "% of tenant households spending 30% or more"),
    1494: ("median_monthly_shelter_cost", "Renter", "Median monthly shelter costs for rented dwellings"),
}

# --- 34-10-0154-01 -----------------------------------------------------------
ACTIVITIES = {"Housing starts": "starts", "Housing completions": "completions"}
UNIT_TYPES = {"Total units": "Total", "Apartment and other unit types": "Apartment and Other"}


def cma_code(dguid: str) -> str | None:
    """'2021S0503559' -> '559' when it is one of the five CMAs."""
    if not isinstance(dguid, str) or "S0503" not in dguid:
        return None
    code = dguid[-3:]
    return code if code in CMAS else None


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_shelter_cost(path: Path = SHELTER_CSV) -> list[dict]:
    rows = []
    reader = pd.read_csv(path, dtype=str, encoding="utf-8-sig", chunksize=CHUNK_SIZE, low_memory=False)
    for chunk in reader:
        codes = chunk["DGUID"].map(cma_code)
        keep = codes.notna()
        for col, val in SHELTER_TOTALS.items():
            keep &= chunk[col] == val
        part = chunk[keep].assign(code=codes[keep])
        for _, r in part.iterrows():
            band, ratio = r[INCOME_COL], r[RATIO_COL]
            for col, tenure in TENURE_COLS.items():
                value = number(r[col])
                if value is None:
                    continue
                if band.startswith(("Median", "Average")):
                    if ratio != "Total - Shelter-cost-to-income ratio":
                        continue
                    indicator = "median_household_income" if band.startswith("Median") else "average_household_income"
                    category = None
                elif ratio == "Total - Shelter-cost-to-income ratio":
                    indicator, category = "households", band
                elif ratio == "Spending 30% or more of income on shelter costs":
                    indicator, category = "households_30pct_plus", band
                else:
                    continue
                rows.append(_row(r["code"], "98-10-0252-01", indicator, tenure, category, 2021, value))
    return rows


def extract_census_profile(path: Path = PROFILE_CSV) -> list[dict]:
    rows = []
    with open(path, encoding="latin-1", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for rec in reader:
            if rec[3] != "Census metropolitan area":
                continue
            code = cma_code(rec[1])
            if code is None:
                continue
            item = PROFILE_ITEMS.get(int(rec[8]))
            if item is None:
                continue
            indicator, tenure, expected_name = item
            if expected_name not in rec[9]:
                raise ValueError(f"Census Profile characteristic {rec[8]} is now {rec[9]!r}; update PROFILE_ITEMS")
            value = number(rec[11])
            if value is not None:
                rows.append(_row(code, "98-401-X2021002", indicator, tenure, None, 2021, value))
    return rows


def extract_starts(path: Path = STARTS_ZIP) -> list[dict]:
    with zipfile.ZipFile(path) as zf, zf.open("34100154.csv") as fh:
        chunks = pd.read_csv(fh, dtype=str, encoding="utf-8-sig", chunksize=CHUNK_SIZE)
        df = pd.concat(
            chunk[
                chunk["DGUID"].map(cma_code).notna()
                & chunk["Housing estimates"].isin(ACTIVITIES)
                & chunk["Type of unit"].isin(UNIT_TYPES)
            ]
            for chunk in chunks
        )
    df["code"] = df["DGUID"].map(cma_code)
    df["year"] = df["REF_DATE"].str[:4].astype(int)
    df["value"] = pd.to_numeric(df["VALUE"], errors="coerce")
    df = df[df["year"] >= FIRST_START_YEAR]
    yearly = df.groupby(["code", "Housing estimates", "Type of unit", "year"]).agg(
        value=("value", "sum"), months=("value", "count")
    )
    rows = []
    for (code, activity, unit, year), r in yearly.iterrows():
        if r["months"] < 12:  # partial year (the current one): leave out
            continue
        rows.append(
            _row(code, "34-10-0154-01", ACTIVITIES[activity], None, UNIT_TYPES[unit], int(year), float(r["value"]))
        )
    return rows


def _row(code, source, indicator, tenure, category, year, value) -> dict:
    return {
        "cma_code": code,
        "cma_name": CMAS[code],
        "source_table": source,
        "indicator": indicator,
        "tenure": tenure,
        "category": category,
        "period_year": year,
        "value": value,
    }


def check(rows: list[dict]) -> None:
    """Every city must have every source, or a view would silently drop it."""
    have = {(r["cma_code"], r["source_table"]) for r in rows}
    missing = [(CMAS[c], s) for c in CMAS for s in ("98-10-0252-01", "98-401-X2021002", "34-10-0154-01") if (c, s) not in have]
    if missing:
        raise ValueError(f"No rows extracted for: {missing}")


def main() -> pd.DataFrame:
    rows = extract_census_profile() + extract_starts() + extract_shelter_cost()
    check(rows)
    out = pd.DataFrame(rows, columns=COLUMNS)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(out):,} rows to {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(out.groupby(["source_table", "cma_name"]).size().unstack(0).to_string())
    return out


if __name__ == "__main__":
    main()
