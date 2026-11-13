"""
Windsor CMA historical rental market, 2019-2025 (additive extension).

Sources: one CMHC Rental Market Survey workbook per edition
  data/raw/cmhc/history/rmr-windsor-{2019..2024}-en.xlsx
  data/raw/cmhc/rmr-windsor-2025-en.xlsx   (same file the 2025 pipeline uses; read only)
Audit that justifies every choice below: docs/HISTORICAL_RENTAL_SOURCE_AUDIT.md

Retained indicators (Windsor CMA row, private apartment structures only):
  vacancy_rate     Table 1.1.1, bedroom 'Total'      percent
  average_rent     Table 1.1.2, bedroom '2 Bedroom'  dollars
  rental_universe  Table 1.1.3, bedroom 'Total'      units
  turnover_rate    Table 1.1.6, bedroom 'Total'      percent

Each edition holds two October surveys (previous and current). For year Y the
value comes from the Y edition's current column. CMHC switched Windsor CMA to
the 2021 census geographic definitions from the 2023 edition onwards, which
also republished Oct-22 on the new basis ("2022 data have been revised to
reflect these definitions"). So 2022 appears twice, once per geography_basis:
  pre_2021_census  2019-2022 (editions 2019-2022, current column)
  2021_census      2022 (edition 2023, previous column) and 2023-2025
is_primary_series marks the row to use for a continuous series (the
2021_census row where both exist). Values on different bases are not
comparable -- the rental universe in particular jumps ~10% at the break.

Grain: one row per year x metric x geography_basis (32 rows).
Every cell is located by its header text and the layout is asserted; a
workbook that differs from the audited layout stops the run. '**' (suppressed)
stays NaN with value_status 'suppressed' -- never 0.

Output: data/staging/windsor_rental_market_history.csv
Raw-file baseline: etl/raw_history_manifest.json (SHA-256 of the 7 workbooks;
created once with --init-manifest, never overwritten).

    .venv\\Scripts\\python.exe etl\\clean_windsor_rental_history.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from cleaning_common import (
    RAW_DIR, STAGING_DIR, normalize_text, parse_cmhc_reliability, parse_cmhc_rms_value, parse_cmhc_trend,
    raw_text, sha256_file,
)

OUTPUT_NAME = "windsor_rental_market_history.csv"
HISTORY_MANIFEST_PATH = Path(__file__).resolve().parent / "raw_history_manifest.json"
GEOGRAPHY = "Windsor CMA"
YEARS = range(2019, 2026)

# edition year -> workbook, relative to data/raw/
EDITIONS = {y: f"cmhc/history/rmr-windsor-{y}-en.xlsx" for y in range(2019, 2025)}
EDITIONS[2025] = "cmhc/rmr-windsor-2025-en.xlsx"

# metric -> (sheet, title prefix, bedroom group, unit, has reliability letter, has trend marker)
METRICS = {
    "vacancy_rate": ("Table 1.1.1", "1.1.1 Private Apartment Vacancy Rates (%)", "Total", "percent", True, True),
    "average_rent": ("Table 1.1.2", "1.1.2 Private Apartment Average Rents ($)", "2 Bedroom", "dollars", True, False),
    "rental_universe": ("Table 1.1.3", "1.1.3 Number of Private Apartment Units in the Universe", "Total", "units",
                        False, False),
    "turnover_rate": ("Table 1.1.6", "1.1.6 Private Apartment Turnover Rates (%)", "Total", "percent", True, True),
}
BASIS_NOTE = "based on the 2021 census geographic definitions"
# Audited: which editions carry the 2021-census note. A different result stops the run.
EXPECTED_BASIS = {2019: "pre_2021_census", 2020: "pre_2021_census", 2021: "pre_2021_census",
                  2022: "pre_2021_census", 2023: "2021_census", 2024: "2021_census", 2025: "2021_census"}
# The 2019 edition writes "no significant change" as U+2212 MINUS SIGN; later editions use '-'.
TREND_ALIASES = {"−": "-"}

COLUMNS = ["year", "period_label", "geography", "geography_basis", "is_primary_series", "dwelling_scope",
           "bedroom_type", "metric", "unit", "value", "raw_value", "value_status", "reliability_code", "yoy_trend",
           "source_edition_year", "source_column_role", "source_workbook", "source_table", "source_cell"]


def period_label(year: int) -> str:
    return f"Oct-{year % 100:02d}"


# ---------------------------------------------------------------------------
# Layout discovery (shared with the audit and the validator)
# ---------------------------------------------------------------------------

def sheet_title(ws) -> str:
    """The table title: first text cell of rows 1-4 (row 1 in 2019, row 3 from 2020)."""
    for row in ws.iter_rows(min_row=1, max_row=4):
        for cell in row:
            text = normalize_text(cell.value)
            if text and text[0].isdigit():
                return text
    raise ValueError(f"No table title in {ws.title!r}")


def sheet_notes(ws) -> list[str]:
    return [t for t in (normalize_text(ws.cell(r, 1).value) for r in range(1, ws.max_row + 1)) if t]


def locate(ws, edition: int, metric: str) -> dict:
    """Find the Windsor CMA row and the previous/current value columns of the
    metric's bedroom group, asserting the layout on the way."""
    sheet, title_prefix, bedroom, _, has_rel, has_trend = METRICS[metric]
    title = sheet_title(ws)
    if not title.startswith(title_prefix):
        raise ValueError(f"{edition} {sheet}: title {title!r} does not start with {title_prefix!r}")
    header = next((r for r in range(1, 15) if normalize_text(ws.cell(r, 1).value) == "Zone"), None)
    if header is None:
        raise ValueError(f"{edition} {sheet}: no 'Zone' header row")
    starts = {normalize_text(ws.cell(header - 1, c).value): c for c in range(2, ws.max_column + 1)
              if normalize_text(ws.cell(header - 1, c).value)}
    if bedroom not in starts:
        raise ValueError(f"{edition} {sheet}: bedroom group {bedroom!r} not in {list(starts)}")
    start = starts[bedroom]
    end = min([c for c in starts.values() if c > start], default=ws.max_column + 1)
    span = range(start, end)
    labels = {c: normalize_text(ws.cell(header, c).value) for c in span}
    periods = {lab: c for c, lab in labels.items() if lab}
    want = {period_label(edition - 1): "previous", period_label(edition): "current"}
    if set(periods) != set(want):
        raise ValueError(f"{edition} {sheet} {bedroom}: period headers {periods} != {sorted(want)}")
    rows = [r for r in range(header + 1, ws.max_row + 1) if normalize_text(ws.cell(r, 1).value) == GEOGRAPHY]
    if len(rows) != 1:
        raise ValueError(f"{edition} {sheet}: expected one {GEOGRAPHY!r} row, found {rows}")
    cols = {}
    for lab, role in want.items():
        c = periods[lab]
        rel = c + 1 if has_rel else None
        if rel is not None and (rel not in span or labels[rel]):
            raise ValueError(f"{edition} {sheet}: reliability column after {get_column_letter(c)} is not blank-headed")
        cols[role] = {"period_label": lab, "value_col": c, "rel_col": rel}
    trend = None
    if has_trend:
        trend = end - 1
        if labels[trend] or trend in (cols["current"]["value_col"], cols["current"]["rel_col"]):
            raise ValueError(f"{edition} {sheet}: trend column {get_column_letter(trend)} not where expected")
    cols["current"]["trend_col"] = trend
    cols["previous"]["trend_col"] = None
    return {"row": rows[0], "header_row": header, "group_start": start, "group_end": end - 1, "title": title,
            "columns": cols}


def geography_basis(wb, edition: int) -> str:
    notes = " ".join(" ".join(sheet_notes(wb[m[0]])) for m in METRICS.values())
    basis = "2021_census" if BASIS_NOTE in notes else "pre_2021_census"
    if basis != EXPECTED_BASIS[edition]:
        raise ValueError(f"edition {edition}: geography note gives {basis}, audit expected {EXPECTED_BASIS[edition]}")
    return basis


def read_cell(ws, edition: int, metric: str, role: str) -> dict:
    loc = locate(ws, edition, metric)
    col = loc["columns"][role]
    raw = ws.cell(loc["row"], col["value_col"]).value
    value, status = parse_cmhc_rms_value(raw)
    if status not in ("published", "suppressed"):
        raise ValueError(f"{edition} {ws.title}: unexpected value status {status!r} for {raw!r}")
    reliability = parse_cmhc_reliability(ws.cell(loc["row"], col["rel_col"]).value) if col["rel_col"] else None
    trend = None
    if col["trend_col"]:
        marker = ws.cell(loc["row"], col["trend_col"]).value
        marker = TREND_ALIASES.get(normalize_text(marker), marker)
        trend = parse_cmhc_trend(marker)
    return {"period_label": col["period_label"], "value": value, "raw_value": raw_text(raw), "value_status": status,
            "reliability_code": reliability, "yoy_trend": trend,
            "source_cell": f"{ws.title}!{get_column_letter(col['value_col'])}{loc['row']}"}


# ---------------------------------------------------------------------------
# Raw-file baseline
# ---------------------------------------------------------------------------

def snapshot(raw_dir: Path = RAW_DIR) -> dict:
    snap = {}
    for rel in EDITIONS.values():
        path = raw_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"Historical source missing: {path}")
        snap[rel] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return snap


def verify_history_manifest(raw_dir: Path = RAW_DIR, manifest_path: Path = HISTORY_MANIFEST_PATH) -> list[str]:
    if not manifest_path.exists():
        return [f"History manifest not found: {manifest_path}"]
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = snapshot(raw_dir)
    return [f"{rel}: {'missing' if rel not in actual else 'changed'}"
            for rel, meta in expected.items() if actual.get(rel) != meta]


# ---------------------------------------------------------------------------
# Cleaner
# ---------------------------------------------------------------------------

def build_rows(raw_dir: Path = RAW_DIR) -> list[dict]:
    records = []
    for edition, rel in EDITIONS.items():
        wb = openpyxl.load_workbook(raw_dir / rel, data_only=True)
        basis = geography_basis(wb, edition)
        roles = ["current"]
        # Bridge year: the first 2021-census edition republished the previous October on the new basis.
        if basis == "2021_census" and EXPECTED_BASIS[edition - 1] != basis:
            roles.append("previous")
        for metric, (sheet, _, bedroom, unit, _, _) in METRICS.items():
            for role in roles:
                cell = read_cell(wb[sheet], edition, metric, role)
                records.append({
                    "year": edition if role == "current" else edition - 1,
                    "geography": GEOGRAPHY,
                    "geography_basis": basis,
                    "dwelling_scope": "apartment",
                    "bedroom_type": bedroom,
                    "metric": metric,
                    "unit": unit,
                    "source_edition_year": edition,
                    "source_column_role": role,
                    "source_workbook": f"data/raw/{rel}",
                    "source_table": sheet,
                    **cell,
                })
        wb.close()
    df = pd.DataFrame(records)
    # Primary series: the 2021-census row where a year has both bases.
    n_basis = df.groupby(["year", "metric"])["geography_basis"].transform("nunique")
    df["is_primary_series"] = (n_basis == 1) | (df["geography_basis"] == "2021_census")
    return df[COLUMNS].sort_values(["metric", "year", "geography_basis"]).reset_index(drop=True)


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR,
          manifest_path: Path = HISTORY_MANIFEST_PATH) -> dict:
    problems = verify_history_manifest(raw_dir, manifest_path)
    if problems:
        raise RuntimeError("Historical workbooks do not match the manifest: " + "; ".join(problems))
    df = build_rows(raw_dir)
    duplicates = int(df.duplicated(["year", "metric", "geography_basis"]).sum())
    if duplicates:
        raise ValueError(f"{duplicates} duplicate year x metric x geography_basis rows")
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / OUTPUT_NAME, index=False, encoding="utf-8")
    problems = verify_history_manifest(raw_dir, manifest_path)
    if problems:
        raise RuntimeError("Historical workbooks changed during cleaning: " + "; ".join(problems))
    return {
        "output": OUTPUT_NAME,
        "cleaned_rows": len(df),
        "years": sorted(df["year"].unique().tolist()),
        "metrics": sorted(df["metric"].unique().tolist()),
        "value_status_counts": df["value_status"].value_counts().to_dict(),
        "primary_series_rows": int(df["is_primary_series"].sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init-manifest", action="store_true",
                        help="record the SHA-256 baseline of the 7 workbooks (only if no manifest exists)")
    args = parser.parse_args()
    if args.init_manifest:
        if HISTORY_MANIFEST_PATH.exists():
            print(f"Manifest already exists, not overwriting: {HISTORY_MANIFEST_PATH}")
            return 1
        snap = snapshot()
        HISTORY_MANIFEST_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
        print(f"Manifest written for {len(snap)} workbooks: {HISTORY_MANIFEST_PATH}")
        return 0
    for key, value in clean().items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
