"""
Shared constants and helpers for the Story 5 cross-dataset CMA staging layer.

Design source (approved): docs/STORY5_CROSS_DATASET_AUDIT.md, decisions D1-D3.
Everything here is additive: it reads raw files in place, never writes to
data/raw/, and never touches the existing verified staging outputs.

Geography matching is deterministic only:
  Rule A  exact_after_cma_suffix  strip the literal trailing " CMA" from the
          CMHC centre name; the rest must equal a StatsCan GEO_NAME exactly
          (case- and accent-sensitive) at GEO_LEVEL 'Census metropolitan area'.
  Rule B  explicit_lookup         the audited table EXPLICIT_LOOKUP below,
          keyed by the exact CMHC string, giving the target DGUID.
No other matching is attempted; an unmapped CMHC CMA stops the run.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from cleaning_common import RAW_DIR, STAGING_DIR, normalize_text, sha256_file

ETL_DIR = Path(__file__).resolve().parent

# --- raw sources (relative to data/raw/) -------------------------------------
CENSUS_ZIP = "statcan/98-401-X2021002_eng_CSV.zip"
CENSUS_CSV_MEMBER = "98-401-X2021002_English_CSV_data.csv"
CMHC_CANADA = {y: f"cmhc/canada_history/rmr-canada-{y}-en.xlsx" for y in range(2019, 2025)}
CMHC_CANADA[2025] = "cmhc/rmr-canada-2025-en.xlsx"   # already covered by etl/raw_manifest.json
NEW_HISTORY_WORKBOOKS = {y: CMHC_CANADA[y] for y in range(2019, 2025)}

CANADA_HISTORY_MANIFEST = ETL_DIR / "raw_canada_history_manifest.json"
GEOGRAPHY_MAP_PATH = ETL_DIR / "cma_geography_map.csv"
STAGING_BASELINE_PATH = ETL_DIR / "story5_pre_staging_baseline.json"

OUTPUTS = {
    "rental_history": "canada_cma_rental_history.csv",
    "housing_profile": "canada_cma_housing_profile.csv",
    "rental_universe": "canada_cma_rental_universe.csv",
}
# Existing verified staging outputs that Story 5 must never change.
EXISTING_STAGING = [
    "windsor_census_profile.csv", "windsor_shelter_cost.csv", "windsor_rental_market.csv",
    "windsor_starts_completions.csv", "canada_rental_market_comparison.csv",
    "windsor_rental_market_history.csv",
]

YEARS = list(range(2019, 2026))
METRICS = ["vacancy_rate", "average_rent_2br", "turnover_rate", "fixed_sample_rent_change_2br"]

# --- geography -------------------------------------------------------------
CMA_LEVELS = ("Census metropolitan area", "Census metropolitan area part")

# Audited explicit lookups (audit section 4.2): exact CMHC string -> (DGUID, reason, boundary_changed)
EXPLICIT_LOOKUP = {
    "Kitchener-Cambridge-Waterloo CMA": ("2021S0503541", "hyphen spacing", False),
    "St. Catharines-Niagara CMA": ("2021S0503539", "hyphen spacing", False),
    "Abbotsford-Mission CMA": ("2021S0503932", "hyphen spacing", False),
    "Greater Sudbury/Grand Sudbury CMA": ("2021S0503580", "slash spacing", False),
    "Ottawa-Gatineau CMA (Ont. part)": ("2021S050535505", "CMA part; abbreviation", False),
    "Ottawa-Gatineau CMA (Qué. part)": ("2021S050524505", "CMA part; abbreviation", False),
    "Belleville - Quinte West CMA": ("2021S0503522", "exact name (2023+ editions)", False),
    "Belleville CMA": ("2021S0503522", "renamed and redefined (2016 -> 2021 census CMA)", True),
}
FOCUS_PEER_DGUIDS = {
    "2021S0503559": "Windsor",
    "2021S0503555": "London",
    "2021S0503537": "Hamilton",
    "2021S0503541": "Kitchener-Cambridge-Waterloo",
    "2021S0503535": "Toronto",
}

# Non-CMA centre labels that legitimately appear in CMHC column A and are
# excluded by design (provinces, national aggregates, the one CA, legend lines).
def is_known_non_cma(label: str) -> bool:
    return (label.endswith(" 10,000+") or label in {"Canada CMAs", "Canada CMAs 1", "Charlottetown CA"}
            or label.startswith("N/A"))


def is_cmhc_cma_label(label: str) -> bool:
    return label.endswith(" CMA") or " CMA (" in label


# --- CMHC markers (Canada RMR legend) -------------------------------------
VALUE_MARKERS = {"**": "suppressed", "++": "change_not_significant"}
RELIABILITY_CODES = {"a", "b", "c", "d"}
TREND = {"↑": "significant_increase", "↓": "significant_decrease",
         "-": "not_significant", "–": "not_significant", "−": "not_significant"}  # 2019 uses U+2212

# --- StatsCan allowlist (audit section 9.2): id -> unit of count_total ----
CENSUS_ALLOWLIST = {
    1: "persons", 41: "dwellings", 46: "dwellings", 47: "dwellings", 50: "households",
    243: "dollars_annual", 244: "dollars_annual", 252: "dollars_annual",
    1414: "households", 1415: "households", 1416: "households", 1417: "households",
    1484: "percent", 1490: "households", 1491: "percent", 1492: "percent", 1493: "percent",
    1494: "dollars_monthly", 1495: "dollars_monthly",
}

GEOGRAPHY_CAVEAT_2021 = ("CMHC October 2021 values use 2016-census CMA boundaries (pre_2021_census); "
                         "Census 2021 values use 2021-census CMA boundaries.")


def raw_path(rel: str, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / rel


def census_rows(raw_dir: Path = RAW_DIR):
    """Yield the Census Profile data rows as lists (columns read by position:
    the SYMBOL header repeats six times)."""
    with zipfile.ZipFile(raw_path(CENSUS_ZIP, raw_dir)) as z:
        with z.open(CENSUS_CSV_MEMBER) as fh:
            reader = csv.reader(io.TextIOWrapper(fh, encoding="cp1252", newline=""))
            header = next(reader)
            if header[:11] != ["CENSUS_YEAR", "DGUID", "ALT_GEO_CODE", "GEO_LEVEL", "GEO_NAME", "TNR_SF",
                               "TNR_LF", "DATA_QUALITY_FLAG", "CHARACTERISTIC_ID", "CHARACTERISTIC_NAME",
                               "CHARACTERISTIC_NOTE"] or header[11] != "C1_COUNT_TOTAL" \
                    or header[17] != "C10_RATE_TOTAL":
                raise ValueError(f"Unexpected Census Profile header: {header}")
            yield from reader


def census_cma_geographies(raw_dir: Path = RAW_DIR) -> dict[str, dict]:
    """DGUID -> {geo_name, geo_level, alt_geo_code} for the 43 CMA-level geographies."""
    geos = {}
    for row in census_rows(raw_dir):
        if row[3] in CMA_LEVELS and row[1] not in geos:
            geos[row[1]] = {"geo_name": row[4], "geo_level": row[3], "alt_geo_code": row[2]}
    return geos


def load_geography_map(path: Path = GEOGRAPHY_MAP_PATH) -> dict[str, dict]:
    """Exact CMHC centre string -> map row. Fails on duplicate keys."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    if df["cmhc_centre_name"].duplicated().any():
        raise ValueError("Duplicate cmhc_centre_name in geography map")
    return {r["cmhc_centre_name"]: r for r in df.to_dict("records")}


def lookup(geo_map: dict, centre: str) -> dict:
    if centre not in geo_map:
        raise ValueError(f"Unmapped CMHC centre (no fuzzy matching allowed): {centre!r}")
    return geo_map[centre]


def snapshot_files(rels: dict | list, base: Path) -> dict:
    items = rels.values() if isinstance(rels, dict) else rels
    return {rel: {"sha256": sha256_file(base / rel), "bytes": (base / rel).stat().st_size} for rel in items}


def verify_snapshot(path: Path, base: Path) -> list[str]:
    if not path.exists():
        return [f"baseline not found: {path}"]
    expected = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for rel, meta in expected.items():
        p = base / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
        elif {"sha256": sha256_file(p), "bytes": p.stat().st_size} != meta:
            problems.append(f"{rel}: changed")
    return problems


def text(value) -> str | None:
    return normalize_text(value)


def header_row(ws, must_have: dict[int, str] | None = None) -> int:
    """1-based row whose column A is 'Centre' (and, if given, whose other
    columns {col_index_0based: text} match). Exactly one must qualify."""
    hits = []
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=40, values_only=True), 1):
        if text(row[0]) != "Centre":
            continue
        if must_have and any(text(row[c] if c < len(row) else None) != text(v) for c, v in must_have.items()):
            continue
        hits.append(i)
    if len(hits) != 1:
        raise ValueError(f"{ws.title}: expected one 'Centre' header row, found {hits}")
    return hits[0]


def data_rows(ws, hdr: int):
    """(row_number, centre_label, row_values) from the row after the header
    until the first row with an empty column A. Every label must be a CMHC
    CMA label or a known non-CMA label; anything else stops the run."""
    for i, row in enumerate(ws.iter_rows(min_row=hdr + 1, values_only=True), hdr + 1):
        label = text(row[0])
        if label is None:
            return
        if not (is_cmhc_cma_label(label) or is_known_non_cma(label)):
            raise ValueError(f"{ws.title} row {i}: unrecognised centre label {label!r}")
        yield i, label, row


def universe_header(ws) -> int:
    return header_row(ws, {2: "Units in arrears", 4: "Universe"})


__all__ = [n for n in dir() if not n.startswith("_")] + ["RAW_DIR", "STAGING_DIR"]
