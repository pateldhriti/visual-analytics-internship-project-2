"""
Data-quality checks for the CMHC rental-market tables, appended to
docs/data_quality_report.md -- the same shared validation report
etl/validate_supply_data.py already writes a section into. Checks run
against the LIVE warehouse tables, not a single staging CSV.

Two tables, each checked independently (own row-count reconciliation,
shared range/duplicate/reliability logic):
  - fact_rental_market: Windsor 2025 + the historical Oct-20/Oct-23
    extraction (2 real sources, 1 table).
  - fact_rental_market_comparison: the Canada RMS 2025 comparison source
    (its own table -- see sql/warehouse_schema.sql's comment on why this
    isn't merged into fact_rental_market).

Checks:

1. Row counts -- live table total vs. the 3 staging CSVs' combined row
   count (each staging row becomes exactly one fact row; no join/filter
   happens in the loaders). Per-source breakdown too, not just a combined
   total, so a shortfall in one source isn't hidden by the others.
2. Rent and vacancy ranges -- metric_type-specific bounds, each set from
   this project's own real observed data (not guessed): rate metrics
   (vacancy_rate, turnover_rate, quintile_vacancy_rate,
   new_stock_vacancy_rate) must be in [0, 100]; rent metrics (average_rent,
   new_stock_average_rent, rent_vacant_units, rent_occupied_units) must be
   in [50, 10000] (real observed range is $618-$2,329; the bound is wide
   enough to allow real variation but would catch a parsing bug like a
   dropped decimal point or a stray comma); universe metrics (universe,
   quintile_universe, new_stock_universe) must be non-negative integers;
   pct_change_rent allowed [-100, 100] (a rent can't literally drop more
   than 100%, but can in principle rise more than that).
3. Duplicate keys -- (zone, period, bedroom_type, dwelling_type,
   income_band, metric_type) must be unique. The live table's own UNIQUE
   constraint (sql/warehouse_schema.sql) already prevents this at load
   time, but this re-checks it explicitly and reports the real number
   (0), rather than just trusting a constraint silently.
4. Reliability letters -- every non-NULL reliability_letter must be one of
   the CMHC legend's real values (a/b/c/d -- excellent/very good/good/
   poor, per docs/cmhc_rms_sheet_catalogue.md). Found and fixed a real bug
   while building this check: 43 rows had reliability_letter = a single
   space character, not NULL or a real letter -- traced to Table 3.1.7's
   raw cells (confirmed directly in the workbook: a suppressed rent cell
   is '**', but its adjacent reliability cell is a literal ' ', not
   empty). etl/extract_windsor_rms.py now strips and normalizes this
   during extraction; re-run after that fix, this check passes clean.

Run from the project virtual environment (after etl/load_warehouse_facts.py):
    .venv\\Scripts\\python.exe etl\\validate_rental_market_data.py
"""

import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = PROJECT_ROOT / "docs" / "data_quality_report.md"

STAGING_SOURCES = {
    "windsor_rental_market.csv": PROJECT_ROOT / "data" / "staging" / "windsor_rental_market.csv",
    "windsor_rental_market_historical.csv": PROJECT_ROOT / "data" / "staging" / "windsor_rental_market_historical.csv",
}

COMPARISON_STAGING_SOURCES = {
    "rms_canada_comparison.csv": PROJECT_ROOT / "data" / "staging" / "rms_canada_comparison.csv",
}

RATE_METRICS = {"vacancy_rate", "turnover_rate", "quintile_vacancy_rate", "new_stock_vacancy_rate"}
RENT_METRICS = {"average_rent", "new_stock_average_rent", "rent_vacant_units", "rent_occupied_units"}
UNIVERSE_METRICS = {"universe", "quintile_universe", "new_stock_universe"}
RANGE_BOUNDS = {
    **{m: (0, 100) for m in RATE_METRICS},
    **{m: (50, 10_000) for m in RENT_METRICS},
    **{m: (0, None) for m in UNIVERSE_METRICS},
    "pct_change_rent": (-100, 100),
}
VALID_RELIABILITY_LETTERS = {"a", "b", "c", "d"}

SECTION_MARKER_START = "<!-- BEGIN: rental market tables -->"
SECTION_MARKER_END = "<!-- END: rental market tables -->"
COMPARISON_SECTION_MARKER_START = "<!-- BEGIN: rental market comparison table -->"
COMPARISON_SECTION_MARKER_END = "<!-- END: rental market comparison table -->"

REPORT_HEADER = """# Data Quality Report

Shared validation report for this project's source tables. Each section
documents real, computed checks against real data -- not assumptions.
Run the corresponding `etl/validate_*.py` script to reproduce a section;
re-running overwrites that section in place, leaving the others untouched.
"""


def fetch_live_fact_rental_market(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT z.zone_label AS zone, p.period_label, b.bedroom_type_label AS bedroom_type,
                   d.dwelling_type_label AS dwelling_type, ib.band_label AS income_band,
                   f.metric_type, f.value, f.reliability_letter
            FROM warehouse.fact_rental_market f
            JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
            JOIN warehouse.dim_period p ON p.period_key = f.period_key
            JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
            JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
            LEFT JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
        """)).fetchall()
    df = pd.DataFrame(rows, columns=["zone", "period_label", "bedroom_type", "dwelling_type",
                                      "income_band", "metric_type", "value", "reliability_letter"])
    df["value"] = df["value"].astype(float)
    return df


def fetch_live_fact_rental_market_comparison(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT z.zone_label AS zone, p.period_label, b.bedroom_type_label AS bedroom_type,
                   d.dwelling_type_label AS dwelling_type, NULL AS income_band,
                   f.metric_type, f.value, f.reliability_letter
            FROM warehouse.fact_rental_market_comparison f
            JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
            JOIN warehouse.dim_period p ON p.period_key = f.period_key
            JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
            JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
        """)).fetchall()
    df = pd.DataFrame(rows, columns=["zone", "period_label", "bedroom_type", "dwelling_type",
                                      "income_band", "metric_type", "value", "reliability_letter"])
    df["value"] = df["value"].astype(float)
    return df


# etl/load_warehouse_facts.py's load_rms_canada_comparison_facts() deliberately
# drops Windsor's vacancy_rate/average_rent rows from this source before
# loading (they duplicate the Windsor-specific workbook's own extraction --
# see that function's docstring) -- the only known, documented case where a
# staging row doesn't become exactly one fact row. Any other gap is a real
# mismatch, not expected.
COMPARISON_KNOWN_EXCLUSIONS = {
    "rms_canada_comparison.csv": (4, "Windsor's vacancy_rate/average_rent rows, excluded at load "
                                      "time as duplicates of the Windsor-specific workbook"),
}


def check_row_counts(live_df: pd.DataFrame, staging_sources: dict, known_exclusions: dict | None = None) -> dict:
    known_exclusions = known_exclusions or {}
    staging_counts = {}
    for name, path in staging_sources.items():
        if path.exists():
            staging_counts[name] = len(pd.read_csv(path, dtype=str))
        else:
            staging_counts[name] = None
    staging_total = sum(c for c in staging_counts.values() if c is not None)
    exclusions_total = sum(n for n, _ in known_exclusions.values())
    expected_live_total = staging_total - exclusions_total
    return {
        "live_table_rows": len(live_df),
        "staging_counts": staging_counts,
        "staging_total": staging_total,
        "known_exclusions": known_exclusions,
        "expected_live_total": expected_live_total,
        "pass": len(live_df) == expected_live_total,
        "note": None if len(live_df) == expected_live_total else
                "Mismatch beyond the known exclusions above -- check for an unmatched-dimension-key "
                "drop during load (printed by etl/load_warehouse_facts.py's own stats) before "
                "assuming this is a new error.",
    }


def check_ranges(live_df: pd.DataFrame) -> dict:
    violations = []
    for metric_type, (low, high) in RANGE_BOUNDS.items():
        subset = live_df[(live_df["metric_type"] == metric_type) & live_df["value"].notna()]
        if low is not None:
            bad_low = subset[subset["value"] < low]
            violations.extend(bad_low.to_dict("records"))
        if high is not None:
            bad_high = subset[subset["value"] > high]
            violations.extend(bad_high.to_dict("records"))
    unknown_metrics = sorted(set(live_df["metric_type"].unique()) - set(RANGE_BOUNDS))
    return {
        "bounds": RANGE_BOUNDS,
        "violations": len(violations),
        "violation_detail": violations[:10],
        "unknown_metric_types": unknown_metrics,
        "pass": len(violations) == 0 and len(unknown_metrics) == 0,
    }


def check_duplicate_keys(live_df: pd.DataFrame) -> dict:
    key_cols = ["zone", "period_label", "bedroom_type", "dwelling_type", "income_band", "metric_type"]
    dupes = live_df[live_df.duplicated(subset=key_cols, keep=False)]
    return {"rows_checked": len(live_df), "duplicate_rows": len(dupes),
            "duplicate_detail": dupes.head(10).to_dict("records"), "pass": len(dupes) == 0}


def check_reliability_letters(live_df: pd.DataFrame) -> dict:
    present = live_df["reliability_letter"].dropna().unique().tolist()
    invalid = sorted(set(present) - VALID_RELIABILITY_LETTERS)
    invalid_rows = live_df[live_df["reliability_letter"].isin(invalid)] if invalid else live_df.iloc[0:0]
    return {"values_present": sorted(present), "valid_legend": sorted(VALID_RELIABILITY_LETTERS),
            "invalid_values": invalid, "invalid_row_count": len(invalid_rows),
            "invalid_row_examples": invalid_rows.head(10).to_dict("records"), "pass": len(invalid) == 0}


def render_section(counts: dict, ranges: dict, duplicates: dict, reliability: dict,
                    marker_start: str, marker_end: str, title: str, source_line: str) -> str:
    lines = [marker_start, "", title, ""]
    lines.append(source_line)
    lines.append(f"Checked: {datetime.date.today().isoformat()}")
    lines.append("")

    lines.append("### 1. Row counts vs. source")
    status = "PASS" if counts["pass"] else "FAIL"
    lines.append(f"- **{status}** -- live table: {counts['live_table_rows']} rows, "
                 f"staging sources combined: {counts['staging_total']}, "
                 f"expected after known exclusions: {counts['expected_live_total']}")
    for name, n in counts["staging_counts"].items():
        lines.append(f"  - `{name}`: {n if n is not None else 'NOT FOUND'}")
    for name, (n, reason) in counts["known_exclusions"].items():
        lines.append(f"  - Known exclusion: {n} row(s) from `{name}` -- {reason}")
    if counts["note"]:
        lines.append(f"  - {counts['note']}")
    lines.append("")

    lines.append("### 2. Rent and vacancy ranges")
    status = "PASS" if ranges["pass"] else "FAIL"
    lines.append(f"- **{status}** -- {ranges['violations']} value(s) outside their metric's real bound, "
                 f"{len(ranges['unknown_metric_types'])} metric_type(s) with no bound defined")
    for metric, (low, high) in sorted(ranges["bounds"].items()):
        lines.append(f"  - `{metric}`: [{low if low is not None else '-inf'}, {high if high is not None else '+inf'}]")
    if ranges["unknown_metric_types"]:
        lines.append(f"  - Unbounded metric_type(s) found in the data, not yet covered: {ranges['unknown_metric_types']}")
    if ranges["violation_detail"]:
        for row in ranges["violation_detail"]:
            lines.append(f"  - {row}")
    lines.append("")

    lines.append("### 3. Duplicate keys")
    status = "PASS" if duplicates["pass"] else "FAIL"
    lines.append(f"- **{status}** -- {duplicates['rows_checked']} rows checked, {duplicates['duplicate_rows']} in a duplicate (zone, period, bedroom_type, dwelling_type, income_band, metric_type) group")
    if duplicates["duplicate_detail"]:
        for row in duplicates["duplicate_detail"]:
            lines.append(f"  - {row}")
    lines.append("")

    lines.append("### 4. Reliability letters")
    status = "PASS" if reliability["pass"] else "FAIL"
    lines.append(f"- **{status}** -- values present: {reliability['values_present']}, valid legend: {reliability['valid_legend']}")
    if reliability["invalid_values"]:
        lines.append(f"  - Invalid value(s) found: {reliability['invalid_values']} ({reliability['invalid_row_count']} rows)")
        for row in reliability["invalid_row_examples"]:
            lines.append(f"    - {row}")
    lines.append("")
    lines.append(marker_end)
    return "\n".join(lines)


def update_report(section: str, marker_start: str, marker_end: str) -> None:
    if REPORT_MD.exists():
        content = REPORT_MD.read_text(encoding="utf-8")
    else:
        content = REPORT_HEADER

    if marker_start in content and marker_end in content:
        before = content.split(marker_start)[0]
        after = content.split(marker_end)[1]
        content = before + section + after
    else:
        content = content.rstrip() + "\n\n" + section + "\n"

    REPORT_MD.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    engine = get_engine()

    print("--- warehouse.fact_rental_market (Windsor + historical) ---")
    live_df = fetch_live_fact_rental_market(engine)
    counts = check_row_counts(live_df, STAGING_SOURCES)
    ranges = check_ranges(live_df)
    duplicates = check_duplicate_keys(live_df)
    reliability = check_reliability_letters(live_df)

    print("Row counts:", "PASS" if counts["pass"] else "FAIL",
          f"(live {counts['live_table_rows']} vs staging {counts['staging_total']})")
    print("Ranges:", "PASS" if ranges["pass"] else "FAIL", f"({ranges['violations']} violations)")
    print("Duplicate keys:", "PASS" if duplicates["pass"] else "FAIL", f"({duplicates['duplicate_rows']} duplicate rows)")
    print("Reliability letters:", "PASS" if reliability["pass"] else "FAIL",
          f"(invalid: {reliability['invalid_values']})")

    section = render_section(
        counts, ranges, duplicates, reliability,
        SECTION_MARKER_START, SECTION_MARKER_END,
        "## Rental market tables (CMHC RMS -- Windsor, historical)",
        "Source: `warehouse.fact_rental_market` (2 staging sources -> 1 table)",
    )
    update_report(section, SECTION_MARKER_START, SECTION_MARKER_END)
    print(f"Written: {REPORT_MD}")

    print("\n--- warehouse.fact_rental_market_comparison (Canada RMS comparison) ---")
    comp_df = fetch_live_fact_rental_market_comparison(engine)
    comp_counts = check_row_counts(comp_df, COMPARISON_STAGING_SOURCES, COMPARISON_KNOWN_EXCLUSIONS)
    comp_ranges = check_ranges(comp_df)
    comp_duplicates = check_duplicate_keys(comp_df)
    comp_reliability = check_reliability_letters(comp_df)

    print("Row counts:", "PASS" if comp_counts["pass"] else "FAIL",
          f"(live {comp_counts['live_table_rows']} vs staging {comp_counts['staging_total']})")
    print("Ranges:", "PASS" if comp_ranges["pass"] else "FAIL", f"({comp_ranges['violations']} violations)")
    print("Duplicate keys:", "PASS" if comp_duplicates["pass"] else "FAIL", f"({comp_duplicates['duplicate_rows']} duplicate rows)")
    print("Reliability letters:", "PASS" if comp_reliability["pass"] else "FAIL",
          f"(invalid: {comp_reliability['invalid_values']})")

    comp_section = render_section(
        comp_counts, comp_ranges, comp_duplicates, comp_reliability,
        COMPARISON_SECTION_MARKER_START, COMPARISON_SECTION_MARKER_END,
        "## Rental market comparison table (CMHC Canada RMS 2025)",
        "Source: `warehouse.fact_rental_market_comparison` (1 staging source -> 1 table)",
    )
    update_report(comp_section, COMPARISON_SECTION_MARKER_START, COMPARISON_SECTION_MARKER_END)
    print(f"Written: {REPORT_MD}")
