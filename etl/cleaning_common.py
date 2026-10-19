"""
Shared helpers for the raw -> cleaned staging pipeline (etl/run_cleaning_pipeline.py).

Everything source-specific lives in the five etl/clean_*.py modules; this
file only holds what more than one of them needs:
  - raw-file integrity (SHA-256 manifest) so the pipeline can prove it never
    changed anything under data/raw/
  - text normalisation and snake_case column names
  - the published StatCan / CMHC marker legends, mapped to readable
    value_status labels -- an unknown marker raises instead of passing through
  - a header assertion used before parsing any fixed-layout Excel sheet, so a
    workbook with a different layout stops the run instead of being misread
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
MANIFEST_PATH = Path(__file__).resolve().parent / "raw_manifest.json"

# The five official source files, relative to data/raw/.
RAW_FILES = {
    "census_profile_zip": "statcan/98-401-X2021002_eng_CSV.zip",
    "shelter_cost_csv": "statcan/9810025201_databaseLoadingData (1).csv",
    "windsor_rms_xlsx": "cmhc/rmr-windsor-2025-en.xlsx",
    "canada_rms_xlsx": "cmhc/rmr-canada-2025-en.xlsx",
    "starts_completions_xlsx": "cmhc/provincial-starts-completions-dwelling-type-08-26-en.xlsx",
}

OUTPUT_FILES = {
    "census_profile": "windsor_census_profile.csv",
    "shelter_cost": "windsor_shelter_cost.csv",
    "rental_market": "windsor_rental_market.csv",
    "starts_completions": "windsor_starts_completions.csv",
    "canada_rental_market": "canada_rental_market_comparison.csv",
}

# ---------------------------------------------------------------------------
# Marker legends (each one taken from the source's own legend/footer)
# ---------------------------------------------------------------------------

# StatCan symbol legend (98-10-0252-01 metadata; same set across bulk CSVs).
# Values with these symbols are not published numbers -> NaN, except 'r'
# (revised) and 'E' (use with caution), which still carry a real number.
STATCAN_STATUS = {
    "": "published",
    "x": "suppressed",
    "...": "not_applicable",
    "..": "not_available",
    "F": "too_unreliable",
    "E": "use_with_caution",
    "r": "revised",
}
STATCAN_KEEPS_VALUE = {"published", "use_with_caution", "revised"}

# CMHC Rental Market Survey footers ("Quality Indicators" / "Other Indicators").
CMHC_RELIABILITY = {"a": "excellent", "b": "very_good", "c": "good", "d": "poor_use_with_caution"}
CMHC_RMS_VALUE_MARKERS = {
    "**": "suppressed",
    "++": "change_not_significant",  # % change of rent tables only: change not different from zero
}
CMHC_TREND = {
    "↑": "significant_increase",
    "↓": "significant_decrease",
    "-": "not_significant",
    "–": "not_significant",
}

# CMHC Housing Information Monthly "Symbols" sheet (starts/completions workbook).
# '-' is "Nil or Zero": stored as 0 with flag nil_or_zero (the dwelling-type
# components only sum to the published Total when read this way).
CMHC_STARTS_MARKERS = {
    "-": ("nil_or_zero", 0.0),
    "**": ("not_available", math.nan),
    "***": ("infinity", math.nan),
    "--": ("too_small_to_express", math.nan),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def snapshot_raw(raw_dir: Path = RAW_DIR) -> dict:
    """SHA-256 + size of each official raw file, keyed by its relative path."""
    snap = {}
    for rel in RAW_FILES.values():
        path = raw_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"Official raw file missing: {path}")
        snap[rel] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return snap


def write_manifest(raw_dir: Path = RAW_DIR, manifest_path: Path = MANIFEST_PATH) -> dict:
    snap = snapshot_raw(raw_dir)
    manifest_path.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return snap


def verify_raw_manifest(raw_dir: Path = RAW_DIR, manifest_path: Path = MANIFEST_PATH) -> list[str]:
    """Return a list of problems (empty list = every raw file matches the manifest)."""
    if not manifest_path.exists():
        return [f"Raw manifest not found: {manifest_path}"]
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = snapshot_raw(raw_dir)
    problems = []
    for rel, meta in expected.items():
        if rel not in actual:
            problems.append(f"{rel}: missing")
        elif actual[rel] != meta:
            problems.append(f"{rel}: changed (expected {meta['sha256'][:12]}, got {actual[rel]['sha256'][:12]})")
    return problems


# ---------------------------------------------------------------------------
# Text and numbers
# ---------------------------------------------------------------------------

def normalize_text(value) -> str | None:
    """NFC-normalise, collapse internal whitespace, trim. Empty -> None."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = unicodedata.normalize("NFC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def snake_case(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"\s*\(\d+C?\)\s*$", "", name)  # StatCan dimension counts, e.g. "Tenure (3)"
    name = name.replace("+", "_plus").replace("%", "pct").replace("$", "dollars")
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return re.sub(r"_+", "_", name)


def parse_number(raw) -> float:
    """'1,058' -> 1058.0, 4.3 -> 4.3. Raises ValueError on anything non-numeric
    (markers must be handled by the caller before this is reached)."""
    if isinstance(raw, bool):
        raise ValueError(f"Not a number: {raw!r}")
    if isinstance(raw, (int, float)):
        return float(raw)
    text = normalize_text(raw)
    if text is None:
        raise ValueError("Empty value")
    return float(text.replace(",", ""))


def parse_cmhc_rms_value(raw) -> tuple[float, str]:
    """A CMHC RMS value cell -> (value, value_status)."""
    text = normalize_text(raw)
    if text is None:
        return math.nan, "blank"
    if text in CMHC_RMS_VALUE_MARKERS:
        return math.nan, CMHC_RMS_VALUE_MARKERS[text]
    try:
        return parse_number(raw), "published"
    except ValueError:
        raise ValueError(f"Unrecognised CMHC RMS value: {raw!r}") from None


def parse_cmhc_reliability(raw) -> str | None:
    text = normalize_text(raw)
    if text is None:
        return None
    if text not in CMHC_RELIABILITY:
        raise ValueError(f"Unrecognised CMHC reliability code: {raw!r}")
    return text


def parse_cmhc_trend(raw) -> str | None:
    text = normalize_text(raw)
    if text is None:
        return None
    if text not in CMHC_TREND:
        raise ValueError(f"Unrecognised CMHC trend marker: {raw!r}")
    return CMHC_TREND[text]


def parse_cmhc_starts_value(raw) -> tuple[float, str]:
    """A starts/completions cell -> (units, value_flag)."""
    text = normalize_text(raw)
    if text is None:
        return math.nan, "blank"
    if text in CMHC_STARTS_MARKERS:
        flag, value = CMHC_STARTS_MARKERS[text]
        return value, flag
    try:
        return parse_number(raw), "published"
    except ValueError:
        raise ValueError(f"Unrecognised CMHC starts value: {raw!r}") from None


def statcan_status(raw_symbol) -> str:
    code = normalize_text(raw_symbol) or ""
    if code not in STATCAN_STATUS:
        raise ValueError(f"Unrecognised StatCan symbol/status: {raw_symbol!r}")
    return STATCAN_STATUS[code]


def raw_text(raw) -> str | None:
    """The raw cell as text, for the raw_value traceability column."""
    if raw is None:
        return None
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw))
    return str(raw)


# ---------------------------------------------------------------------------
# Excel layout guard
# ---------------------------------------------------------------------------

def assert_cells(ws, expected: dict[str, str]) -> None:
    """Stop if any header cell (e.g. {'B7': 'Oct-24'}) differs from the layout
    this parser was written for. Compared after whitespace normalisation."""
    mismatches = []
    for ref, want in expected.items():
        got = normalize_text(ws[ref].value)
        if got != normalize_text(want):
            mismatches.append(f"{ref}: expected {want!r}, found {ws[ref].value!r}")
    if mismatches:
        raise ValueError(f"Unexpected layout in sheet {ws.title!r}: " + "; ".join(mismatches))
