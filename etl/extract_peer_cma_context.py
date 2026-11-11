"""
Extract Windsor's and its four comparison cities' rows from four StatCan
files and CMHC's five city rental workbooks, for the combined Story 5 views.

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
    98-10-0241-01  housing indicators by age of primary household maintainer
                   and tenure (2021 Census)
                   -> households, households spending 30%+ of income on
                      shelter, and households in core housing need, by age
                      group (category), for all households and renters;
                      downloaded on first run (62 MB zip)
    CMHC Rental Market Survey, October 2025, one workbook per city
                   -> Table 3.1.3: purpose-built rental units (apartments and
                      row houses, all unit sizes) in October 2024 and 2025;
                      downloaded on first run to data/raw/cmhc/peer_rms_2025/

The Story 1-4 extracts keep only Windsor; Story 4's rents already cover the
four comparison cities (CMHC Rental Market Survey). This script adds the
same cities' incomes, households and construction, so Windsor can be
compared with them on more than rent.

Cities are matched by the 3-digit CMA code that ends every DGUID
(2021S0503559, and 2011S0503559 in the starts table), not by name, because
each file spells the names differently.

Output: data/staging/peer_cma_context.csv, long format
(cma_code, cma_name, source_table, indicator, tenure, category,
period_year, value). Loaded by etl/load_warehouse_facts.py.

Licence: Statistics Canada Open Licence
(https://www.statcan.gc.ca/en/reference/licence).

Run from the project virtual environment (the 1.3 GB shelter-cost file and
the 1.5 GB housing-indicators file are streamed in chunks; it takes a few
minutes):
    .venv\\Scripts\\python.exe etl\\extract_peer_cma_context.py
"""

import csv
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
SHELTER_CSV = RAW / "shelter_cost" / "98100252.csv"
PROFILE_CSV = RAW / "statcan" / "98-401-X2021002_English_CSV_data.csv"
STARTS_ZIP = RAW / "statcan" / "34100154-eng.zip"
INDICATORS_ZIP = RAW / "statcan" / "98100241-eng.zip"
INDICATORS_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/98100241-eng.zip"
RMS_DIR = RAW / "cmhc" / "peer_rms_2025"
RMS_URL = (
    "https://assets.cmhc-schl.gc.ca/sites/cmhc/professional/housing-markets-data-and-research/"
    "housing-data-tables/rental-market/rental-market-report-data-tables/2025/{slug}.xlsx"
)
# CMA code -> CMHC's file name for the city's 2025 Rental Market Survey tables.
RMS_FILES = {
    "559": "rmr-windsor-2025-en",
    "555": "rmr-london-2025-en",
    "537": "rmr-hamilton-2025-en",
    "539": "rmr-st-catharines-niagara-2025-en",
    "541": "rmr-kitchener-cambridge-waterloo-2025-en",
}
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

# --- 98-10-0241-01 -----------------------------------------------------------
AGE_COL = "Age of primary household maintainer (9)"
INDICATOR_COL = "Housing indicators (6)"
INDICATOR_TOTALS = {
    "Household type including census family structure (16)": "Total - Household type including census family structure",
    "Period of construction (13)": "Total - Period of construction",
    "Statistics (3C)": "Number of private households",
}
HOUSING_INDICATORS = {
    "Total - Housing indicators": "households",
    "Affordability: 30% or more of household income is spent on shelter costs": "households_30pct_plus",
    "In core need": "households_core_need",
}
INDICATOR_TENURE_COLS = {
    "Tenure including presence of mortgage payments and subsidized housing (7):"
    "Total - Tenure including presence of mortgage payments and subsidized housing[1]": "Total",
    "Tenure including presence of mortgage payments and subsidized housing (7):Renter[5]": "Renter",
}


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


def download_indicators(path: Path = INDICATORS_ZIP) -> Path:
    """The table is not part of the other Story 1-4 downloads; fetch it once."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(INDICATORS_URL, timeout=300)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return path


def extract_housing_indicators_by_age(path: Path = INDICATORS_ZIP) -> list[dict]:
    rows = []
    with zipfile.ZipFile(path) as zf, zf.open("98100241.csv") as fh:
        for chunk in pd.read_csv(fh, dtype=str, encoding="utf-8-sig", chunksize=CHUNK_SIZE, low_memory=False):
            codes = chunk["DGUID"].map(cma_code)
            keep = codes.notna() & chunk[INDICATOR_COL].isin(HOUSING_INDICATORS)
            for col, val in INDICATOR_TOTALS.items():
                keep &= chunk[col] == val
            for _, r in chunk[keep].assign(code=codes[keep]).iterrows():
                for col, tenure in INDICATOR_TENURE_COLS.items():
                    value = number(r[col])
                    if value is not None:
                        rows.append(
                            _row(r["code"], "98-10-0241-01", HOUSING_INDICATORS[r[INDICATOR_COL]], tenure,
                                 r[AGE_COL], 2021, value)
                        )
    return rows


def download_rms(directory: Path = RMS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for slug in RMS_FILES.values():
        path = directory / f"{slug}.xlsx"
        if not path.exists():
            resp = requests.get(RMS_URL.format(slug=slug), timeout=120)
            resp.raise_for_status()
            path.write_bytes(resp.content)
    return directory


def _cma_label(text) -> str:
    """'Kitchener - Cambridge - Waterloo CMA' -> 'Kitchener-Cambridge-Waterloo CMA'."""
    return " ".join(str(text).replace(" - ", "-").split())


def extract_rental_universe(directory: Path = RMS_DIR) -> list[dict]:
    """Table 3.1.3's CMA total row: [label, 4 unit sizes x (Oct-24, Oct-25),
    Total Oct-24, Total Oct-25]. The title row also names the CMA, so the
    total row is the one whose first cell is exactly the CMA's name."""
    rows = []
    for code, slug in RMS_FILES.items():
        wb = openpyxl.load_workbook(directory / f"{slug}.xlsx", read_only=True, data_only=True)
        total = [
            r for r in wb["Table 3.1.3"].iter_rows(values_only=True)
            if r and r[0] and _cma_label(r[0]) == CMAS[code]
        ]
        if len(total) != 1:
            raise ValueError(f"{slug}: expected one '{CMAS[code]}' row in Table 3.1.3, found {len(total)}")
        values = [number(str(v).replace(",", "")) for v in total[0][1:] if v is not None]
        if len(values) != 10:
            raise ValueError(f"{slug}: Table 3.1.3 total row has {len(values)} values, expected 10")
        for year, value in ((2024, values[-2]), (2025, values[-1])):
            rows.append(_row(code, "CMHC RMS 3.1.3", "rental_universe", None, "Total", year, value))
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


SOURCES = ("98-10-0252-01", "98-401-X2021002", "34-10-0154-01", "98-10-0241-01", "CMHC RMS 3.1.3")


def check(rows: list[dict]) -> None:
    """Every city must have every source, or a view would silently drop it."""
    have = {(r["cma_code"], r["source_table"]) for r in rows}
    missing = [(CMAS[c], s) for c in CMAS for s in SOURCES if (c, s) not in have]
    if missing:
        raise ValueError(f"No rows extracted for: {missing}")


def main() -> pd.DataFrame:
    rows = (
        extract_census_profile()
        + extract_starts()
        + extract_shelter_cost()
        + extract_housing_indicators_by_age(download_indicators())
        + extract_rental_universe(download_rms())
    )
    check(rows)
    out = pd.DataFrame(rows, columns=COLUMNS)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(out):,} rows to {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(out.groupby(["source_table", "cma_name"]).size().unstack(0).to_string())
    return out


if __name__ == "__main__":
    main()
