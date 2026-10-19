"""
Validate the five cleaned staging files against the raw sources and write
docs/DATA_CLEANING_VALIDATION.md, whose first line is exactly
"DATA CLEANING STATUS: PASS" or "DATA CLEANING STATUS: FAIL".

    .venv\\Scripts\\python.exe etl\\validate_cleaned_data.py

Exit code 0 = PASS, 1 = FAIL. Reconciliation checks re-read the raw files
directly (by source_cell, COORDINATE or CHARACTERISTIC_ID) rather than trusting
the cleaners' own output.
"""

from __future__ import annotations

import datetime
import io
import math
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pandas as pd

from cleaning_common import MANIFEST_PATH, OUTPUT_FILES, PROJECT_ROOT, RAW_DIR, RAW_FILES, STAGING_DIR, verify_raw_manifest

REPORT_PATH = PROJECT_ROOT / "docs" / "DATA_CLEANING_VALIDATION.md"

# Values that are NaN on purpose carry one of these statuses; every other
# status must come with a real number.
NAN_STATUSES = {"suppressed", "not_applicable", "not_available", "too_unreliable", "change_not_significant",
                "blank", "infinity", "too_small_to_express"}

REQUIRED_COLUMNS = {
    "census_profile": ["census_year", "geography", "dguid", "topic", "characteristic_id", "characteristic_name",
                       "count_total", "count_total_status", "rate_total", "rate_total_status"],
    "shelter_cost": ["ref_year", "geography", "dguid", "income_group", "household_type", "household_type_member_id",
                     "tenure", "shelter_cost_ratio", "coordinate", "measure_kind", "value", "raw_value",
                     "status_code", "value_status"],
    "rental_market": ["source_table", "dwelling_scope", "geography", "zone", "bedroom_type", "metric", "unit",
                      "period_label", "value", "raw_value", "value_status", "reliability_code", "yoy_trend",
                      "source_cell"],
    "starts_completions": ["geography", "source_table", "activity", "dwelling_type", "period_label", "period_type",
                           "units", "raw_value", "value_flag", "source_cell"],
    "canada_rental_market": ["source_table", "centre", "geography_level", "metric", "unit", "period_label", "value",
                             "raw_value", "value_status", "reliability_code", "source_cell"],
}
NUMERIC_COLUMNS = {
    "census_profile": ["census_year", "characteristic_id", "count_total", "count_men", "count_women",
                       "rate_total", "rate_men", "rate_women"],
    "shelter_cost": ["ref_year", "value", "income_group_member_id", "household_type_member_id", "tenure_member_id"],
    "rental_market": ["value"],
    "starts_completions": ["units"],
    "canada_rental_market": ["value"],
}
NATURAL_KEYS = {
    "census_profile": ["characteristic_id"],
    "shelter_cost": ["coordinate"],
    "rental_market": ["source_table", "zone", "bedroom_type", "metric", "period_label", "income_quintile"],
    "starts_completions": ["source_table", "activity", "dwelling_type"],
    "canada_rental_market": ["centre", "metric", "period_label"],
}
# (value column, status column) pairs whose NaN/status consistency is checked
VALUE_STATUS_PAIRS = {
    "census_profile": [(c, f"{c}_status") for c in
                       ["count_total", "count_men", "count_women", "rate_total", "rate_men", "rate_women"]],
    "shelter_cost": [("value", "value_status")],
    "rental_market": [("value", "value_status")],
    "starts_completions": [("units", "value_flag")],
    "canada_rental_market": [("value", "value_status")],
}
VALID_PERIODS = {
    "rental_market": {"Oct-24", "Oct-25", "Oct-23 to Oct-24", "Oct-24 to Oct-25"},
    "starts_completions": {"August 2026", "January to August 2026"},
    "canada_rental_market": {"Oct-24", "Oct-25", "Oct-23 to Oct-24", "Oct-24 to Oct-25"},
}
EXPECTED = {"census_population_2021": 422_630, "shelter_owner_30_plus": 13_005, "shelter_renter_30_plus": 15_735}


@dataclass
class Check:
    dataset: str
    name: str
    passed: bool
    detail: str


def load_outputs(staging_dir: Path) -> dict[str, pd.DataFrame | None]:
    frames = {}
    for key, name in OUTPUT_FILES.items():
        path = staging_dir / name
        # keep_default_na=False: labels such as the 'N/A' income quintile must stay text.
        frames[key] = pd.read_csv(path, keep_default_na=False, na_values=[""],
                                  dtype={"raw_value": str, "status_code": str}) if path.exists() else None
    return frames


def plain_number(raw) -> float:
    """Independent of the cleaners' parser: strip commas, float()."""
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip().replace(",", ""))


def same(a, b) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Generic checks
# ---------------------------------------------------------------------------

def generic_checks(frames: dict, staging_dir: Path) -> list[Check]:
    checks = []
    for key, df in frames.items():
        name = OUTPUT_FILES[key]
        if df is None:
            checks.append(Check(name, "file exists and loads", False, f"missing: {staging_dir / name}"))
            continue
        checks.append(Check(name, "file exists and loads", True, f"{len(df):,} rows × {df.shape[1]} columns"))
        checks.append(Check(name, "row count > 0", len(df) > 0, f"{len(df):,} rows"))

        missing = [c for c in REQUIRED_COLUMNS[key] if c not in df.columns]
        checks.append(Check(name, "required columns present", not missing, f"missing: {missing}" if missing else "all present"))

        bad = [c for c in NUMERIC_COLUMNS[key] if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]
        checks.append(Check(name, "numeric columns are numeric", not bad, f"non-numeric: {bad}" if bad else
                            ", ".join(NUMERIC_COLUMNS[key])))

        keys = NATURAL_KEYS[key]
        dups = int(df.duplicated(subset=keys).sum())
        exact = int(df.duplicated().sum())
        checks.append(Check(name, "no duplicate natural keys", dups == 0,
                            f"key ({', '.join(keys)}): {dups} duplicates; exact duplicate rows: {exact}"))

        problems = []
        for value_col, status_col in VALUE_STATUS_PAIRS[key]:
            nan_with_value_status = df[value_col].isna() & ~df[status_col].isin(NAN_STATUSES)
            value_with_nan_status = df[value_col].notna() & df[status_col].isin(NAN_STATUSES)
            if nan_with_value_status.any() or value_with_nan_status.any():
                problems.append(f"{value_col}: {int(nan_with_value_status.sum())} NaN without a missing-status, "
                                f"{int(value_with_nan_status.sum())} values with a missing-status")
        checks.append(Check(name, "suppressed/missing values represented as NaN with a status", not problems,
                            "; ".join(problems) if problems else "every NaN has a missing-status and vice versa"))
    return checks


def missing_value_summary(frames: dict) -> dict[str, pd.DataFrame]:
    out = {}
    for key, df in frames.items():
        if df is None:
            continue
        rows = []
        for value_col, status_col in VALUE_STATUS_PAIRS[key]:
            counts = df[status_col].value_counts().to_dict()
            rows.append({"column": value_col, "rows": len(df), "nan": int(df[value_col].isna().sum()),
                         "statuses": ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))})
        out[OUTPUT_FILES[key]] = pd.DataFrame(rows)
    return out


# ---------------------------------------------------------------------------
# Dataset-specific checks
# ---------------------------------------------------------------------------

def census_checks(df: pd.DataFrame, raw_dir: Path) -> list[Check]:
    name = OUTPUT_FILES["census_profile"]
    checks = [
        Check(name, "Windsor CMA only", set(df["geography"]) == {"Windsor CMA"} and set(df["dguid"]) == {"2021S0503559"},
              f"geography={sorted(set(df['geography']))}, dguid={sorted(set(df['dguid']))}"),
        Check(name, "census year valid (2021)", set(df["census_year"]) == {2021}, f"years={sorted(set(df['census_year']))}"),
    ]
    pop = df.loc[df["characteristic_id"] == 1, "count_total"]
    got = pop.iloc[0] if len(pop) == 1 else None
    checks.append(Check(name, "Windsor population 2021 = 422,630", got == EXPECTED["census_population_2021"],
                        f"characteristic_id 1 count_total = {got}"))

    with zipfile.ZipFile(raw_dir / RAW_FILES["census_profile_zip"]) as z, z.open("98-401-X2021002_English_CSV_data.csv") as f:
        raw = pd.read_csv(io.TextIOWrapper(f, encoding="cp1252"), dtype=str, keep_default_na=False)
    raw = raw[(raw["DGUID"] == "2021S0503559") & (raw["GEO_LEVEL"] == "Census metropolitan area")]
    raw = raw.set_index(raw["CHARACTERISTIC_ID"].astype(int))
    pairs = {"count_total": ("C1_COUNT_TOTAL", "SYMBOL"), "count_men": ("C2_COUNT_MEN+", "SYMBOL.1"),
             "count_women": ("C3_COUNT_WOMEN+", "SYMBOL.2"), "rate_total": ("C10_RATE_TOTAL", "SYMBOL.3"),
             "rate_men": ("C11_RATE_MEN+", "SYMBOL.4"), "rate_women": ("C12_RATE_WOMEN+", "SYMBOL.5")}
    mismatches = 0
    for _, row in df.iterrows():
        src = raw.loc[row["characteristic_id"]]
        for clean_col, (raw_col, sym_col) in pairs.items():
            raw_val = src[raw_col]
            expected = math.nan if (raw_val == "" or src[sym_col].strip() in ("...", "x", "..", "F")) else plain_number(raw_val)
            if not same(row[clean_col], expected):
                mismatches += 1
    checks.append(Check(name, "values reconcile to raw ZIP (every kept characteristic, all 6 columns)",
                        mismatches == 0, f"{len(df) * 6:,} cells compared, {mismatches} mismatches"))
    return checks


def shelter_checks(df: pd.DataFrame, raw_dir: Path) -> list[Check]:
    name = OUTPUT_FILES["shelter_cost"]
    raw = pd.read_csv(raw_dir / RAW_FILES["shelter_cost_csv"], dtype=str, encoding="utf-8-sig", keep_default_na=False)
    checks = [
        Check(name, "Windsor CMA only", set(df["geography"]) == {"Windsor CMA"} and set(df["dguid"]) == {"2021S0503559"},
              f"geography={sorted(set(df['geography']))}, dguid={sorted(set(df['dguid']))}"),
        Check(name, "reference year valid (2021)", set(df["ref_year"]) == {2021}, f"years={sorted(set(df['ref_year']))}"),
        Check(name, "row count equals raw file", len(df) == len(raw), f"cleaned {len(df):,} vs raw {len(raw):,}"),
    ]
    raw_status = raw["STATUS"].str.strip().replace("", "(none)").value_counts().to_dict()
    clean_status = df["status_code"].fillna("(none)").value_counts().to_dict()
    checks.append(Check(name, "status/suppression counts equal raw file", raw_status == clean_status,
                        f"raw {raw_status} vs cleaned {clean_status}"))

    merged = df.merge(raw[["COORDINATE", "VALUE", "STATUS"]], left_on="coordinate", right_on="COORDINATE", how="left")
    mismatches = 0
    for _, row in merged.iterrows():
        expected = math.nan if row["STATUS"].strip() in ("x", "...") or row["VALUE"] == "" else plain_number(row["VALUE"])
        if not same(row["value"], expected):
            mismatches += 1
    checks.append(Check(name, "values reconcile to raw file (by COORDINATE)", mismatches == 0,
                        f"{len(merged):,} rows compared, {mismatches} mismatches"))

    published = raw[raw["STATUS"].str.strip() == ""]
    raw_total = published["VALUE"].astype(float).sum()
    clean_total = df.loc[df["value_status"] == "published", "value"].sum()
    checks.append(Check(name, "sum of published values equals raw file", same(raw_total, clean_total),
                        f"raw {raw_total:,.0f} vs cleaned {clean_total:,.0f}"))

    checks.append(Check(name, "household counts are non-negative",
                        bool((df.loc[df["measure_kind"] == "household_count", "value"].dropna() >= 0).all()),
                        f"min = {df.loc[df['measure_kind'] == 'household_count', 'value'].min()}"))

    base = df[(df["income_group"] == "Total - Total income of household")
              & (df["household_type"] == "Total - Household type including census family structure")
              & (df["shelter_cost_ratio"] == "Spending 30% or more of income on shelter costs")]
    for tenure, key in (("Owner", "shelter_owner_30_plus"), ("Renter", "shelter_renter_30_plus")):
        vals = base.loc[base["tenure"] == tenure, "value"]
        got = vals.iloc[0] if len(vals) == 1 else None
        checks.append(Check(name, f"{tenure} households spending 30%+ = {EXPECTED[key]:,}", got == EXPECTED[key],
                            f"found {got}"))
    return checks


def workbook_reconcile(df: pd.DataFrame, raw_path: Path) -> tuple[int, int]:
    """Re-open the workbook and compare every row's raw_value/value to its source_cell."""
    wb = openpyxl.load_workbook(raw_path, data_only=True)
    value_col = "units" if "units" in df.columns else "value"
    mismatches = 0
    for _, row in df.iterrows():
        sheet, ref = row["source_cell"].split("!")
        cell = wb[sheet][ref].value
        cell_text = None if cell is None else (str(int(cell)) if isinstance(cell, float) and cell.is_integer() else str(cell))
        raw_ok = (pd.isna(row["raw_value"]) and cell_text is None) or str(row["raw_value"]) == cell_text
        try:
            expected = plain_number(cell)
        except (TypeError, ValueError):
            expected = 0.0 if str(cell).strip() == "-" and value_col == "units" else math.nan
        if not raw_ok or not same(row[value_col], expected):
            mismatches += 1
    wb.close()
    return len(df), mismatches


def rental_checks(df: pd.DataFrame, raw_dir: Path) -> list[Check]:
    name = OUTPUT_FILES["rental_market"]
    checks = [
        Check(name, "Windsor CMA only", set(df["geography"]) == {"Windsor CMA"}, f"geography={sorted(set(df['geography']))}"),
        Check(name, "periods valid", set(df["period_label"]) <= VALID_PERIODS["rental_market"],
              f"periods={sorted(set(df['period_label']))}"),
    ]
    rents = df.loc[df["unit"] == "dollars", "value"].dropna()
    checks.append(Check(name, "rents > 0 where present", bool((rents > 0).all()),
                        f"{len(rents):,} rent values, min = {rents.min()}"))
    rates = df.loc[df["metric"].isin(["vacancy_rate", "turnover_rate", "new_stock_vacancy_rate", "quintile_vacancy_rate"]), "value"].dropna()
    checks.append(Check(name, "vacancy/turnover rates within 0-100%", bool(rates.between(0, 100).all()),
                        f"{len(rates):,} values, range [{rates.min()}, {rates.max()}]"))
    changes = df.loc[df["metric"] == "average_rent_pct_change", "value"].dropna()
    checks.append(Check(name, "% rent change within -100..100", bool(changes.between(-100, 100).all()),
                        f"{len(changes):,} values, range [{changes.min()}, {changes.max()}]"))
    units = df.loc[df["unit"] == "units", "value"].dropna()
    checks.append(Check(name, "universe counts non-negative", bool((units >= 0).all()), f"min = {units.min()}"))
    n, bad = workbook_reconcile(df, raw_dir / RAW_FILES["windsor_rms_xlsx"])
    checks.append(Check(name, "values reconcile to raw workbook (every row, by source_cell)", bad == 0,
                        f"{n:,} cells compared, {bad} mismatches"))
    return checks


def starts_checks(df: pd.DataFrame, raw_dir: Path) -> list[Check]:
    name = OUTPUT_FILES["starts_completions"]
    checks = [
        Check(name, "Windsor CMA only", set(df["geography"]) == {"Windsor CMA"}
              and set(df["source_geography_label"]) == {"Windsor"}, f"geography={sorted(set(df['geography']))}"),
        Check(name, "periods valid", set(df["period_label"]) <= VALID_PERIODS["starts_completions"],
              f"periods={sorted(set(df['period_label']))}"),
        Check(name, "units cannot be negative", bool((df["units"].dropna() >= 0).all()), f"min = {df['units'].min()}"),
    ]
    bad = []
    for (table, activity), grp in df.groupby(["source_table", "activity"]):
        parts = grp.loc[grp["dwelling_type"] != "Total", "units"].sum()
        total = grp.loc[grp["dwelling_type"] == "Total", "units"].iloc[0]
        if not same(parts, total):
            bad.append(f"{table}/{activity}: components {parts} vs Total {total}")
    checks.append(Check(name, "dwelling-type components sum to published Total", not bad,
                        "; ".join(bad) if bad else f"{df.groupby(['source_table', 'activity']).ngroups} groups reconcile"))
    n, mism = workbook_reconcile(df, raw_dir / RAW_FILES["starts_completions_xlsx"])
    checks.append(Check(name, "values reconcile to raw workbook (every row, by source_cell)", mism == 0,
                        f"{n} cells compared, {mism} mismatches"))
    return checks


def canada_checks(df: pd.DataFrame, raw_dir: Path) -> list[Check]:
    name = OUTPUT_FILES["canada_rental_market"]
    checks = [
        Check(name, "contains Windsor CMA", "Windsor CMA" in set(df["centre"]),
              f"{df['centre'].nunique()} CMAs"),
        Check(name, "CMA rows only", set(df["geography_level"]) == {"cma"} and df["centre"].str.contains(r"\bCMA\b").all(),
              f"levels={sorted(set(df['geography_level']))}"),
        Check(name, "periods valid", set(df["period_label"]) <= VALID_PERIODS["canada_rental_market"],
              f"periods={sorted(set(df['period_label']))}"),
    ]
    rents = df.loc[df["metric"] == "average_rent_2br", "value"].dropna()
    checks.append(Check(name, "rents > 0 where present", bool((rents > 0).all()), f"{len(rents)} values, min = {rents.min()}"))
    rates = df.loc[df["metric"].isin(["vacancy_rate", "turnover_rate"]), "value"].dropna()
    checks.append(Check(name, "vacancy/turnover rates within 0-100%", bool(rates.between(0, 100).all()),
                        f"{len(rates)} values, range [{rates.min()}, {rates.max()}]"))
    changes = df.loc[df["metric"] == "rent_pct_change_2br", "value"].dropna()
    checks.append(Check(name, "% rent change within -100..100", bool(changes.between(-100, 100).all()),
                        f"{len(changes)} values, range [{changes.min()}, {changes.max()}]"))
    n, bad = workbook_reconcile(df, raw_dir / RAW_FILES["canada_rms_xlsx"])
    checks.append(Check(name, "values reconcile to raw workbook (every row, by source_cell)", bad == 0,
                        f"{n} cells compared, {bad} mismatches"))
    return checks


SPECIFIC = {
    "census_profile": census_checks,
    "shelter_cost": shelter_checks,
    "rental_market": rental_checks,
    "starts_completions": starts_checks,
    "canada_rental_market": canada_checks,
}


def run_checks(raw_dir: Path = RAW_DIR, staging_dir: Path = STAGING_DIR,
               manifest_path: Path = MANIFEST_PATH) -> tuple[list[Check], dict]:
    problems = verify_raw_manifest(raw_dir, manifest_path)
    checks = [Check("data/raw/", "raw files unchanged (SHA-256 vs etl/raw_manifest.json)", not problems,
                    "; ".join(problems) if problems else f"{len(RAW_FILES)} files match")]
    frames = load_outputs(staging_dir)
    checks += generic_checks(frames, staging_dir)
    for key, func in SPECIFIC.items():
        if frames[key] is None:
            continue
        try:
            checks += func(frames[key], raw_dir)
        except Exception as exc:  # a crash in a check is a failed check, never a silent pass
            checks.append(Check(OUTPUT_FILES[key], "dataset-specific checks ran", False, f"{type(exc).__name__}: {exc}"))
    return checks, missing_value_summary(frames)


def render(checks: list[Check], missing: dict) -> str:
    passed = all(c.passed for c in checks)
    failed = [c for c in checks if not c.passed]
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"DATA CLEANING STATUS: {'PASS' if passed else 'FAIL'}",
        "",
        "# Data Cleaning Validation",
        "",
        f"Generated by `etl/validate_cleaned_data.py` on {now}. "
        f"{len(checks) - len(failed)} of {len(checks)} checks passed.",
        "",
    ]
    if failed:
        lines += ["## Failed checks", ""]
        for c in failed:
            lines.append(f"- **{c.dataset}: {c.name}**: {c.detail}")
        lines.append("")
    lines += ["## All checks", "", "| Dataset | Check | Result | Detail |", "|---|---|---|---|"]
    for c in checks:
        detail = c.detail.replace("|", "\\|")
        lines.append(f"| `{c.dataset}` | {c.name} | {'PASS' if c.passed else '**FAIL**'} | {detail} |")
    lines += ["", "## Missing and suppressed values", "",
              "NaN counts per value column, with the status recorded for every row.", ""]
    for name, table in missing.items():
        lines += [f"### {name}", "", "| Column | Rows | NaN | Status counts |", "|---|---|---|---|"]
        for _, r in table.iterrows():
            lines.append(f"| `{r['column']}` | {r['rows']:,} | {r['nan']:,} | {r['statuses']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    checks, missing = run_checks()
    REPORT_PATH.write_text(render(checks, missing), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    print(f"DATA CLEANING STATUS: {'PASS' if not failed else 'FAIL'} ({len(checks) - len(failed)}/{len(checks)} checks passed)")
    for c in failed:
        print(f"  FAIL  {c.dataset}: {c.name} -- {c.detail}")
    print(f"Report written: {REPORT_PATH}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
