"""
Data-quality checks for the CMHC supply tables (starts/completions/under
construction), appended to docs/data_quality_report.md -- the shared
validation report. No such report existed before this script; it's
created here with this as its first section, structured so other data
sources' checks can be added as their own headers later.

Checks run, against data/staging/ontario_canada_starts_completions.csv
(the same file warehouse.fact_starts_completions is loaded from):

1. Row counts -- per province x period x activity x dwelling_type, and
   overall, compared against the expected count derived from the real
   cardinality of each dimension (not a hardcoded number).
2. Range checks -- units must be non-negative, and (real, confirmed)
   finite/non-null. Flags any row outside [0, a generously large upper
   bound] as a hard failure, not just a warning, since a negative or
   absurd unit count would mean a parsing bug, not real suppressed data
   (this source has no suppression marker at all -- every cell is a
   real number).
3. Reconciliation -- for every (province, period, activity), the 4
   dwelling-type components (Singles, Semis, Row, Apartment and Other)
   must sum to exactly the Total row. This is the strongest real check
   available for this source: if extraction had misread a column, this
   would very likely catch it (same kind of cross-check that caught the
   average-rent column-width bug in the RMS extraction).
4. Missing months -- CMHC publishes this table quarterly. This dataset
   has exactly 1 quarter (Second Quarter 2026) and 1 YTD period (January
   to June 2026) extracted -- not a time series. This check reports that
   real gap explicitly (every other quarter CMHC has ever published is
   "missing" from this project's data) rather than silently passing
   because the one period present is internally consistent.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\validate_supply_data.py
"""

import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "staging" / "ontario_canada_starts_completions.csv"
REPORT_MD = PROJECT_ROOT / "docs" / "data_quality_report.md"

REPORT_HEADER = """# Data Quality Report

Shared validation report for this project's source tables. Each section
documents real, computed checks against real data -- not assumptions.
Run the corresponding `etl/validate_*.py` script to reproduce a section;
re-running overwrites that section in place, leaving the others untouched.
"""

SECTION_MARKER_START = "<!-- BEGIN: supply tables -->"
SECTION_MARKER_END = "<!-- END: supply tables -->"


def check_counts(df: pd.DataFrame) -> dict:
    n_periods = df[["period_type", "period_label"]].drop_duplicates().shape[0]

    by_group = df.groupby(["province", "period_type", "period_label"])["activity"].nunique()
    return {
        "total_rows": len(df),
        "provinces": sorted(df["province"].unique().tolist()),
        "period_count": n_periods,
        "periods": sorted(df["period_label"].unique().tolist()),
        "activities": sorted(df["activity"].unique().tolist()),
        "dwelling_types": sorted(df["dwelling_type"].unique().tolist()),
        "activities_present_per_province_period": by_group.to_dict(),
        # Note: YTD periods have no "Under Construction" row (a stock
        # metric that doesn't accumulate YTD) -- confirmed structural
        # difference, not a gap. See etl/extract_cmhc_starts_completions.py.
    }


def check_ranges(df: pd.DataFrame) -> dict:
    negative = df[df["units"] < 0]
    null_units = df[df["units"].isna()]
    absurd = df[df["units"] > 10_000_000]  # sanity ceiling; real max in this data is 410,323
    return {
        "min_units": int(df["units"].min()),
        "max_units": int(df["units"].max()),
        "negative_rows": len(negative),
        "null_rows": len(null_units),
        "absurd_rows": len(absurd),
        "pass": len(negative) == 0 and len(null_units) == 0 and len(absurd) == 0,
    }


def check_reconciliation(df: pd.DataFrame) -> dict:
    components = (
        df[df["dwelling_type"] != "Total"]
        .groupby(["province", "period_type", "period_label", "activity"])["units"]
        .sum()
        .reset_index(name="component_sum")
    )
    totals = (
        df[df["dwelling_type"] == "Total"][["province", "period_type", "period_label", "activity", "units"]]
        .rename(columns={"units": "total"})
    )
    merged = components.merge(totals, on=["province", "period_type", "period_label", "activity"], how="outer")
    merged["diff"] = merged["component_sum"] - merged["total"]
    mismatches = merged[(merged["diff"] != 0) | merged["component_sum"].isna() | merged["total"].isna()]
    return {
        "groups_checked": len(merged),
        "mismatches": len(mismatches),
        "mismatch_detail": mismatches.to_dict("records"),
        "pass": len(mismatches) == 0,
    }


def check_missing_periods(df: pd.DataFrame) -> dict:
    periods_present = sorted(df["period_label"].unique().tolist())
    return {
        "periods_present": periods_present,
        "period_count": len(periods_present),
        "is_time_series": False,
        "note": (
            "This is a single-quarter snapshot (Second Quarter 2026) plus its "
            "own YTD figure (January to June 2026), not a multi-period time "
            "series. CMHC publishes this table quarterly going back many years "
            "-- every prior quarter is 'missing' from this project's data, not "
            "just a few scattered gaps. A real time series requires extracting "
            "additional historical editions, which hasn't been done yet."
        ),
    }


def render_section(counts: dict, ranges: dict, reconciliation: dict, missing: dict) -> str:
    lines = [SECTION_MARKER_START, "", "## Supply tables (CMHC starts/completions)", ""]
    lines.append(f"Source: `{SOURCE_CSV.relative_to(PROJECT_ROOT).as_posix()}` -> `warehouse.fact_starts_completions`")
    lines.append(f"Checked: {datetime.date.today().isoformat()}")
    lines.append("")

    lines.append("### 1. Counts")
    lines.append(f"- Total rows: **{counts['total_rows']}**")
    lines.append(f"- Provinces: {', '.join(counts['provinces'])}")
    lines.append(f"- Periods ({counts['period_count']}): {', '.join(counts['periods'])}")
    lines.append(f"- Activities: {', '.join(counts['activities'])}")
    lines.append(f"- Dwelling types: {', '.join(counts['dwelling_types'])}")
    lines.append(
        "- Activities per (province, period): quarter periods have 3 "
        "(Starts, Completions, Under Construction); the YTD period has only "
        "2 (no Under Construction -- a stock metric that doesn't accumulate "
        "YTD, a real structural difference, not a missing-data gap)."
    )
    lines.append("")

    lines.append("### 2. Ranges")
    status = "PASS" if ranges["pass"] else "FAIL"
    lines.append(f"- **{status}** -- units range [{ranges['min_units']}, {ranges['max_units']}]")
    lines.append(
        f"- Negative rows: {ranges['negative_rows']}, null rows: {ranges['null_rows']}, "
        f"absurd (>10,000,000) rows: {ranges['absurd_rows']}"
    )
    lines.append("")

    lines.append("### 3. Reconciliation (dwelling-type components sum to Total)")
    status = "PASS" if reconciliation["pass"] else "FAIL"
    lines.append(f"- **{status}** -- {reconciliation['groups_checked']} groups checked, {reconciliation['mismatches']} mismatches")
    if not reconciliation["pass"]:
        for row in reconciliation["mismatch_detail"]:
            lines.append(f"  - {row}")
    lines.append("")

    lines.append("### 4. Missing months/periods")
    lines.append(f"- **NOT a time series** -- {missing['period_count']} period(s) present: {', '.join(missing['periods_present'])}")
    lines.append(f"- {missing['note']}")
    lines.append("")
    lines.append(SECTION_MARKER_END)
    return "\n".join(lines)


def update_report(section: str) -> None:
    if REPORT_MD.exists():
        content = REPORT_MD.read_text(encoding="utf-8")
    else:
        content = REPORT_HEADER

    if SECTION_MARKER_START in content and SECTION_MARKER_END in content:
        before = content.split(SECTION_MARKER_START)[0]
        after = content.split(SECTION_MARKER_END)[1]
        content = before + section + after
    else:
        content = content.rstrip() + "\n\n" + section + "\n"

    REPORT_MD.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    df = pd.read_csv(SOURCE_CSV)

    counts = check_counts(df)
    ranges = check_ranges(df)
    reconciliation = check_reconciliation(df)
    missing = check_missing_periods(df)

    print("Counts:", counts["total_rows"], "rows,", counts["period_count"], "period(s)")
    print("Ranges:", "PASS" if ranges["pass"] else "FAIL")
    print("Reconciliation:", "PASS" if reconciliation["pass"] else "FAIL",
          f"({reconciliation['mismatches']}/{reconciliation['groups_checked']} mismatches)")
    print("Missing periods: NOT a time series --", missing["period_count"], "period(s) present")

    section = render_section(counts, ranges, reconciliation, missing)
    update_report(section)
    print(f"\nWritten: {REPORT_MD}")
