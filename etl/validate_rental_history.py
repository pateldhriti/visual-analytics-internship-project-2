"""
Validate data/staging/windsor_rental_market_history.csv and write
docs/HISTORICAL_RENTAL_VALIDATION.md, whose first line is exactly
"HISTORICAL RENTAL STATUS: PASS" or "HISTORICAL RENTAL STATUS: FAIL".

    .venv\\Scripts\\python.exe etl\\validate_rental_history.py

Exit code 0 = PASS, 1 = FAIL. Read-only. Source reconciliation does not reuse
the cleaner's layout code: it opens each workbook, goes straight to the
recorded source_cell, and independently checks the row label, the period
header above the cell, the bedroom group the column belongs to, and the value
(own comma-stripping parser). 2025 (and 2024) are also reconciled with the
already validated data/staging/windsor_rental_market.csv.
"""

from __future__ import annotations

import datetime
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

from cleaning_common import PROJECT_ROOT, RAW_DIR, STAGING_DIR
from clean_windsor_rental_history import (
    EDITIONS, METRICS, OUTPUT_NAME, HISTORY_MANIFEST_PATH, verify_history_manifest,
)

REPORT_PATH = PROJECT_ROOT / "docs" / "HISTORICAL_RENTAL_VALIDATION.md"
EXISTING_RENTAL = "windsor_rental_market.csv"
EXPECTED_YEARS = list(range(2019, 2026))
GRAIN = ["year", "metric", "geography_basis"]
REQUIRED = ["year", "period_label", "geography", "geography_basis", "is_primary_series", "dwelling_scope",
            "bedroom_type", "metric", "unit", "value", "raw_value", "value_status", "reliability_code", "yoy_trend",
            "source_edition_year", "source_column_role", "source_workbook", "source_table", "source_cell"]
RANGES = {"vacancy_rate": (0, 100), "turnover_rate": (0, 100), "average_rent": (0, None), "rental_universe": (0, None)}


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def plain_number(raw) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip().replace(",", ""))


def load(staging_dir: Path) -> pd.DataFrame | None:
    path = staging_dir / OUTPUT_NAME
    if not path.exists():
        return None
    return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={"raw_value": str})


def group_label(ws, header_row: int, col: int) -> str | None:
    """Bedroom group of a column: nearest non-empty cell to the left on the group row."""
    for c in range(col, 1, -1):
        v = ws.cell(header_row - 1, c).value
        if v not in (None, ""):
            return str(v).strip()
    return None


def reconcile_sources(df: pd.DataFrame, raw_dir: Path) -> tuple[int, list[str]]:
    problems, books = [], {}
    for r in df.itertuples(index=False):
        rel = r.source_workbook.removeprefix("data/raw/")
        if rel not in books:
            books[rel] = openpyxl.load_workbook(raw_dir / rel, data_only=True)
        sheet, ref = r.source_cell.split("!")
        if sheet != r.source_table:
            problems.append(f"{r.year} {r.metric}: source_cell sheet {sheet} != source_table {r.source_table}")
            continue
        ws = books[rel][sheet]
        letters, row = coordinate_from_string(ref)
        col = column_index_from_string(letters)
        header = next((h for h in range(1, 15) if str(ws.cell(h, 1).value or "").strip() == "Zone"), None)
        issues = []
        if str(ws.cell(row, 1).value).strip() != "Windsor CMA":
            issues.append(f"row label {ws.cell(row, 1).value!r}")
        if header is None or str(ws.cell(header, col).value).strip() != r.period_label:
            issues.append(f"period header {ws.cell(header, col).value if header else None!r} != {r.period_label}")
        elif group_label(ws, header, col) not in (r.bedroom_type,):
            issues.append(f"bedroom group {group_label(ws, header, col)!r} != {r.bedroom_type}")
        raw = ws.cell(row, col).value
        if str(raw).strip() == "**":
            if r.value_status != "suppressed" or not math.isnan(r.value):
                issues.append(f"source suppressed but CSV has {r.value} / {r.value_status}")
        elif r.value_status != "published" or plain_number(raw) != r.value:
            issues.append(f"source {raw!r} vs CSV {r.value} / {r.value_status}")
        if issues:
            problems.append(f"{r.year} {r.metric} {r.source_workbook} {r.source_cell}: " + "; ".join(issues))
    for wb in books.values():
        wb.close()
    return len(df), problems


def run_checks(staging_dir: Path = STAGING_DIR, raw_dir: Path = RAW_DIR,
               manifest_path: Path = HISTORY_MANIFEST_PATH) -> list[Check]:
    checks = []
    problems = verify_history_manifest(raw_dir, manifest_path)
    checks.append(Check("source workbooks unchanged (SHA-256 vs etl/raw_history_manifest.json)", not problems,
                        "; ".join(problems) or f"{len(EDITIONS)} workbooks match"))
    df = load(staging_dir)
    if df is None:
        checks.append(Check("history CSV exists", False, f"missing: {staging_dir / OUTPUT_NAME}"))
        return checks
    checks.append(Check("history CSV exists and loads", len(df) > 0, f"{len(df)} rows × {df.shape[1]} columns"))
    missing = [c for c in REQUIRED if c not in df.columns]
    checks.append(Check("required lineage columns present", not missing, ", ".join(missing) or "all present"))
    if missing:
        return checks

    years = sorted(df["year"].unique().tolist())
    checks.append(Check("years are exactly 2019-2025", years == EXPECTED_YEARS, f"{years}"))
    primary = df[df["is_primary_series"]]
    per_metric = primary.groupby("metric")["year"].apply(sorted).to_dict()
    bad = {m: y for m, y in per_metric.items() if y != EXPECTED_YEARS}
    checks.append(Check("each metric has one primary-series row for every year 2019-2025",
                        not bad and set(per_metric) == set(METRICS) and not primary.duplicated(["year", "metric"]).any(),
                        "; ".join(f"{m}: {len(y)} years" for m, y in sorted(per_metric.items())) + (f"; bad {bad}" if bad else "")))
    checks.append(Check("Windsor CMA only", set(df["geography"]) == {"Windsor CMA"}, f"{sorted(set(df['geography']))}"))
    checks.append(Check("apartment scope only", set(df["dwelling_scope"]) == {"apartment"}, f"{sorted(set(df['dwelling_scope']))}"))
    dupes = int(df.duplicated(GRAIN).sum())
    checks.append(Check("unique at declared grain (year × metric × geography_basis)", dupes == 0, f"{dupes} duplicates"))
    want_bedroom = {m: v[2] for m, v in METRICS.items()}
    bad = df[df.apply(lambda r: want_bedroom.get(r.metric) != r.bedroom_type or METRICS[r.metric][3] != r.unit
                      or METRICS[r.metric][0] != r.source_table, axis=1)]
    checks.append(Check("metric ↔ table / bedroom / unit mapping is the audited one", bad.empty, f"{len(bad)} rows off"))
    checks.append(Check("period_label matches year", (df["period_label"] == df["year"].map(lambda y: f"Oct-{y % 100:02d}")).all(),
                        "Oct-YY for every row"))

    # Geography basis and the 2022 bridge
    expected_basis = df["year"].map(lambda y: "pre_2021_census" if y <= 2021 else "2021_census")
    single = df[df["year"] != 2022]
    two = df[df["year"] == 2022]
    checks.append(Check("geography_basis: pre_2021_census for 2019-2021, 2021_census for 2023-2025",
                        (single["geography_basis"] == expected_basis[single.index]).all(),
                        f"{single.groupby('geography_basis')['year'].agg(lambda s: sorted(set(s))).to_dict()}"))
    ok = (len(two) == 8 and two.groupby("metric")["geography_basis"].apply(set).eq({"pre_2021_census", "2021_census"}).all()
          and (two[two["geography_basis"] == "2021_census"]["is_primary_series"]).all()
          and not two[two["geography_basis"] == "pre_2021_census"]["is_primary_series"].any()
          and set(two[two["geography_basis"] == "2021_census"]["source_edition_year"]) == {2023}
          and set(two[two["geography_basis"] == "pre_2021_census"]["source_edition_year"]) == {2022})
    checks.append(Check("2022 kept on both bases; 2021-census row (2023 edition) is primary", ok,
                        f"{len(two)} rows for 2022"))
    others_ok = (df[df["year"] != 2022]["is_primary_series"]).all() and (df[df["year"] != 2022]["source_edition_year"] == df[df["year"] != 2022]["year"]).all()
    checks.append(Check("other years: one row each, from that year's own edition", bool(others_ok), "edition year = data year"))

    # Values, ranges, suppression
    status_ok = df["value_status"].isin(["published", "suppressed"]).all()
    nan_ok = (df["value"].isna() == (df["value_status"] != "published")).all()
    sup = df[df["value_status"] == "suppressed"]
    checks.append(Check("suppression handling: NaN ⇔ suppressed, raw '**', never 0",
                        bool(status_ok and nan_ok and (sup["raw_value"] == "**").all()),
                        f"{(df['value_status'] == 'published').sum()} published, {len(sup)} suppressed"))
    bad = []
    for m, (lo, hi) in RANGES.items():
        v = df[(df["metric"] == m) & df["value"].notna()]["value"]
        if (v <= lo).any() if m in ("average_rent", "rental_universe") else (v < lo).any():
            bad.append(m)
        if hi is not None and (v > hi).any():
            bad.append(m)
    uni = df[(df["metric"] == "rental_universe") & df["value"].notna()]["value"]
    checks.append(Check("numeric ranges: rates 0-100, rents > 0, universe > 0 and whole",
                        not bad and (uni % 1 == 0).all(),
                        "; ".join(f"{m}: {df[df.metric == m]['value'].min()}–{df[df.metric == m]['value'].max()}" for m in sorted(RANGES))))
    checks.append(Check("reliability codes valid (none for universe)",
                        df["reliability_code"].dropna().isin(list("abcd")).all()
                        and df[df["metric"] == "rental_universe"]["reliability_code"].isna().all(),
                        f"{df['reliability_code'].value_counts().to_dict()}"))
    checks.append(Check("trend only on current-column vacancy/turnover rows",
                        df[(df["source_column_role"] == "previous") | df["metric"].isin(["average_rent", "rental_universe"])]["yoy_trend"].isna().all(),
                        f"{df['yoy_trend'].notna().sum()} trend values"))

    # Source reconciliation (no invented values)
    n, problems = reconcile_sources(df, raw_dir)
    checks.append(Check("every row reconciles to its source cell (label, period, bedroom, value)", not problems,
                        f"{n} cells re-read, {len(problems)} problems" + (": " + "; ".join(problems[:5]) if problems else "")))
    cells = df["source_workbook"] + "|" + df["source_cell"]
    checks.append(Check("no two rows share a source cell", not cells.duplicated().any(), f"{cells.nunique()} distinct cells"))

    # Same-October overlap between consecutive editions (revision check)
    issues = []
    books = {e: openpyxl.load_workbook(raw_dir / rel, data_only=True) for e, rel in EDITIONS.items()}
    for r in df.itertuples(index=False):
        if r.source_column_role != "current" or r.year == 2025:
            continue
        later = books[r.year + 1][r.source_table]
        letters, row = coordinate_from_string(r.source_cell.split("!")[1])
        header = next(h for h in range(1, 15) if str(later.cell(h, 1).value or "").strip() == "Zone")
        crow = next(x for x in range(header + 1, later.max_row + 1) if str(later.cell(x, 1).value or "").strip() == "Windsor CMA")
        col = next(c for c in range(2, later.max_column + 1)
                   if str(later.cell(header, c).value or "").strip() == r.period_label and group_label(later, header, c) == r.bedroom_type)
        v = later.cell(crow, col).value
        same = (str(v).strip() == "**" and r.value_status == "suppressed") or (r.value_status == "published" and plain_number(v) == r.value)
        if not same and r.year != 2022:
            issues.append(f"{r.period_label} {r.metric}: edition {r.year} {r.value} vs edition {r.year + 1} {v}")
    for wb in books.values():
        wb.close()
    checks.append(Check("no silent revisions: each October equals the next edition's copy (2022 excepted: geography revision)",
                        not issues, "; ".join(issues) or "18 overlaps identical"))

    # Reconcile with the existing validated 2025 pipeline output
    existing_path = staging_dir / EXISTING_RENTAL
    if not existing_path.exists():
        checks.append(Check("reconciles with existing windsor_rental_market.csv", False, f"missing {existing_path}"))
        return checks
    ex = pd.read_csv(existing_path, keep_default_na=False, na_values=[""], dtype={"raw_value": str})
    bad, compared = [], 0
    for r in df[df["year"].isin([2024, 2025]) & df["is_primary_series"]].itertuples(index=False):
        m = ex[(ex["source_table"] == r.source_table) & (ex["zone"] == "Windsor CMA") & (ex["bedroom_type"] == r.bedroom_type)
               & (ex["metric"] == r.metric) & (ex["period_label"] == r.period_label)]
        compared += 1
        if len(m) != 1:
            bad.append(f"{r.year} {r.metric}: {len(m)} matches")
            continue
        e = m.iloc[0]
        rel_a = None if pd.isna(r.reliability_code) else r.reliability_code
        rel_b = None if pd.isna(e["reliability_code"]) else e["reliability_code"]
        same_value = (pd.isna(r.value) and pd.isna(e["value"])) or r.value == e["value"]
        if not (same_value and r.value_status == e["value_status"] and rel_a == rel_b):
            bad.append(f"{r.year} {r.metric}: history {r.value}/{r.value_status}/{rel_a} vs existing {e['value']}/{e['value_status']}/{rel_b}")
    checks.append(Check("2024-2025 reconcile with validated windsor_rental_market.csv (value, status, reliability)",
                        not bad and compared == 8, f"{compared} rows compared" + (": " + "; ".join(bad) if bad else ", all equal")))
    return checks


def render(checks: list[Check]) -> str:
    failed = [c for c in checks if not c.passed]
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [f"HISTORICAL RENTAL STATUS: {'FAIL' if failed else 'PASS'}", "",
             "# Historical Rental Market Validation — Windsor CMA 2019–2025", "",
             f"Generated by `etl/validate_rental_history.py` on {now} for `data/staging/{OUTPUT_NAME}`.",
             f"**{len(checks) - len(failed)} of {len(checks)} checks passed.** Source audit: "
             "[HISTORICAL_RENTAL_SOURCE_AUDIT.md](HISTORICAL_RENTAL_SOURCE_AUDIT.md).", ""]
    if failed:
        lines += ["## Failed checks", "", "| Check | Detail |", "|---|---|"]
        lines += [f"| {c.name} | {c.detail} |" for c in failed] + [""]
    lines += ["## All checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {c.name} | {'PASS' if c.passed else '**FAIL**'} | {c.detail.replace('|', chr(92) + '|')} |" for c in checks]
    return "\n".join(lines) + "\n"


def main() -> int:
    checks = run_checks()
    REPORT_PATH.write_text(render(checks), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    for c in failed:
        print(f"FAIL  {c.name} -- {c.detail}")
    print(f"HISTORICAL RENTAL STATUS: {'FAIL' if failed else 'PASS'} ({len(checks) - len(failed)}/{len(checks)} checks passed)")
    print(f"Report written: {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
