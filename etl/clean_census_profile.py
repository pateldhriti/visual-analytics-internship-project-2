"""
Clean the 2021 Census Profile (98-401-X2021002, CMAs and CAs) for Windsor CMA.

Source: data/raw/statcan/98-401-X2021002_eng_CSV.zip -- read directly from
the archive (nothing is extracted to disk, the ZIP is never modified).
The data CSV inside is cp1252-encoded, one row per (geography, characteristic).

Output: data/staging/windsor_census_profile.csv -- one row per kept Windsor
characteristic, the six published value columns kept side by side (count and
rate, each for total / men+ / women+), each with its own *_status column.

Topic subset (agreed scope): only these top-level sections of the profile are
kept, identified by the source's own CHARACTERISTIC_ID ranges (each range
starts at a "Total - ..." section header in the source):
  population           1-3, 6-7, 8-40 (population, density, land area, age)
  dwellings_housing    4-5, 41-49, 1414-1499 (dwelling counts and type, tenure,
                       condo, bedrooms, rooms, crowding, suitability, period
                       built, condition, maintainers, shelter cost, core need)
  household            50-57, 71-110 (household size, families, household type)
  income               111-382 (individual/household/family income, low income,
                       inequality)
  labour_employment    2223-2281 (labour force status, work activity, class of
                       worker, occupation, industry)
Everything else (marital status, languages, Indigenous identity, ancestry,
immigration, visible minority, religion, mobility, education, commuting,
language at work, minority-language rights) is out of scope and dropped.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from cleaning_common import RAW_DIR, RAW_FILES, STAGING_DIR, STATCAN_KEEPS_VALUE, normalize_text, statcan_status

DATA_MEMBER = "98-401-X2021002_English_CSV_data.csv"
ENCODING = "cp1252"
WINDSOR = {"GEO_NAME": "Windsor", "GEO_LEVEL": "Census metropolitan area", "DGUID": "2021S0503559"}
OUTPUT_NAME = "windsor_census_profile.csv"

TOPIC_RANGES = [
    ("population", 1, 3),
    ("dwellings_housing", 4, 5),
    ("population", 6, 7),
    ("population", 8, 40),
    ("dwellings_housing", 41, 49),
    ("household", 50, 57),
    ("household", 71, 110),
    ("income", 111, 382),
    ("dwellings_housing", 1414, 1499),
    ("labour_employment", 2223, 2281),
]

# raw value column -> (clean name, raw symbol column)
VALUE_COLUMNS = {
    "C1_COUNT_TOTAL": ("count_total", "SYMBOL"),
    "C2_COUNT_MEN+": ("count_men", "SYMBOL.1"),
    "C3_COUNT_WOMEN+": ("count_women", "SYMBOL.2"),
    "C10_RATE_TOTAL": ("rate_total", "SYMBOL.3"),
    "C11_RATE_MEN+": ("rate_men", "SYMBOL.4"),
    "C12_RATE_WOMEN+": ("rate_women", "SYMBOL.5"),
}


def topic_for(characteristic_id: int) -> str | None:
    for topic, lo, hi in TOPIC_RANGES:
        if lo <= characteristic_id <= hi:
            return topic
    return None


def unit_marker(name: str) -> str | None:
    """Only what the characteristic name itself states -- no guessing."""
    if re.search(r"\(\$\)", name):
        return "$"
    if re.search(r"\(%\)", name):
        return "%"
    return None


def read_raw(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    with zipfile.ZipFile(raw_dir / RAW_FILES["census_profile_zip"]) as z, z.open(DATA_MEMBER) as f:
        return pd.read_csv(io.TextIOWrapper(f, encoding=ENCODING), dtype=str, keep_default_na=False)


def select_windsor(raw: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=raw.index)
    for col, want in WINDSOR.items():
        mask &= raw[col].str.strip() == want
    return raw[mask]


def clean_rows(windsor: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "census_year": pd.to_numeric(windsor["CENSUS_YEAR"]).astype(int),
        "geography": "Windsor CMA",
        "dguid": windsor["DGUID"].str.strip(),
        "alt_geo_code": windsor["ALT_GEO_CODE"].str.strip(),
        "geo_level": windsor["GEO_LEVEL"].map(normalize_text),
        "tnr_sf": pd.to_numeric(windsor["TNR_SF"]),
        "tnr_lf": pd.to_numeric(windsor["TNR_LF"]),
        "data_quality_flag": windsor["DATA_QUALITY_FLAG"].str.strip(),
        "characteristic_id": pd.to_numeric(windsor["CHARACTERISTIC_ID"]).astype(int),
    })
    names = windsor["CHARACTERISTIC_NAME"]
    indent = names.str.len() - names.str.lstrip().str.len()
    out["topic"] = out["characteristic_id"].map(topic_for)
    out["characteristic_name"] = names.map(normalize_text)
    # The source indents each hierarchy level by exactly 2 spaces.
    out["characteristic_indent_level"] = (indent // 2).astype(int)
    out["characteristic_note"] = pd.to_numeric(windsor["CHARACTERISTIC_NOTE"].replace("", None)).astype("Int64")
    out["unit_marker"] = out["characteristic_name"].map(unit_marker)

    for raw_col, (clean_col, symbol_col) in VALUE_COLUMNS.items():
        status = windsor[symbol_col].map(statcan_status)
        value = pd.to_numeric(windsor[raw_col].replace("", None), errors="raise")
        out[clean_col] = value.where(status.isin(STATCAN_KEEPS_VALUE))
        out[f"{clean_col}_status"] = status

    out = out[out["topic"].notna()].reset_index(drop=True)
    cols = [
        "census_year", "geography", "dguid", "alt_geo_code", "geo_level", "tnr_sf", "tnr_lf",
        "data_quality_flag", "topic", "characteristic_id", "characteristic_name",
        "characteristic_indent_level", "characteristic_note", "unit_marker",
    ]
    for _, (clean_col, _) in VALUE_COLUMNS.items():
        cols += [clean_col, f"{clean_col}_status"]
    return out[cols]


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR) -> dict:
    raw = read_raw(raw_dir)
    windsor = select_windsor(raw)
    if windsor.empty:
        raise ValueError("No Windsor CMA rows found in the Census Profile")
    cleaned = clean_rows(windsor)
    duplicates = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates()

    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(out_dir / OUTPUT_NAME, index=False, encoding="utf-8")
    return {
        "output": OUTPUT_NAME,
        "raw_rows": len(raw),
        "raw_windsor_rows": len(windsor),
        "cleaned_rows": len(cleaned),
        "exact_duplicates_removed": duplicates,
        "rows_dropped_out_of_topic_scope": len(windsor) - len(cleaned) - duplicates,
        "rows_by_topic": cleaned["topic"].value_counts().sort_index().to_dict(),
    }


if __name__ == "__main__":
    for key, value in clean().items():
        print(f"{key}: {value}")
