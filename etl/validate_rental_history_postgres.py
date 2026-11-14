"""
Validate the additive history extension in the LIVE PostgreSQL database
(clean.rental_market_windsor_history + the Story 2 historical views) and write
docs/HISTORICAL_RENTAL_POSTGRES_VALIDATION.md, whose first line is exactly
"HISTORICAL RENTAL POSTGRESQL STATUS: PASS" or "... FAIL".

    .venv\\Scripts\\python.exe etl\\validate_rental_history_postgres.py

Exit code 0 = PASS, 1 = FAIL. Read-only (SELECT only).
Benchmarks are recomputed in Python from the staging CSV, not from the views.
"Nothing existing changed" compares the five original clean tables and the 31
original analysis views with etl/postgres_pre_history_baseline.json (taken
before the first history load), and re-runs the existing PostgreSQL load and
analysis validators.
"""

from __future__ import annotations

import datetime
import json
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import psycopg2

import validate_analysis_views as vav
import validate_postgres_load as vpl
from clean_windsor_rental_history import OUTPUT_NAME
from cleaning_common import PROJECT_ROOT, STAGING_DIR
from load_cleaned_to_postgres import LoadError, connect, read_staging
from load_rental_history_to_postgres import BASELINE_PATH, HISTORY_VIEWS, TABLE, fingerprint

REPORT_PATH = PROJECT_ROOT / "docs" / "HISTORICAL_RENTAL_POSTGRES_VALIDATION.md"
YEARS = list(range(2019, 2026))
METRICS = ["average_rent", "vacancy_rate", "rental_universe", "turnover_rate"]
INTEGER_COLS = {"year", "source_edition_year"}
NUMERIC_COLS = {"value"}
BOOLEAN_COLS = {"is_primary_series"}
SERIES_VIEWS = {"average_rent": ("story2_historical_rent", "average_rent_2br"),
                "vacancy_rate": ("story2_historical_vacancy", "vacancy_rate_pct"),
                "turnover_rate": ("story2_historical_turnover", "turnover_rate_pct")}


@dataclass
class Check:
    area: str
    name: str
    passed: bool
    detail: str


def fetch(cur, sql, params=()) -> list[dict]:
    cur.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def dec(text: str) -> Decimal | None:
    return None if text == "" else Decimal(text)


def r4(x: Decimal | None) -> Decimal | None:
    return None if x is None else x.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def cell_equal(text: str, value, column: str) -> bool:
    if text == "":
        return value is None
    if value is None:
        return False
    if column in BOOLEAN_COLS:
        return {"True": True, "False": False}[text] is value
    if column in INTEGER_COLS or column in NUMERIC_COLS:
        return Decimal(text) == Decimal(value)
    return text == value


def table_checks(cur, csv: pd.DataFrame) -> list[Check]:
    a = "table"
    checks = []
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'clean' "
                "AND table_name = %s ORDER BY ordinal_position", (TABLE,))
    types = dict(cur.fetchall())
    checks.append(Check(a, f"clean.{TABLE} exists", bool(types), f"{len(types)} columns"))
    if not types:
        return checks
    checks.append(Check(a, "columns match staging CSV header (names and order)", list(types) == list(csv.columns),
                        f"{list(types)}" if list(types) != list(csv.columns) else "identical"))
    want = {c: ("integer" if c in INTEGER_COLS else "numeric" if c in NUMERIC_COLS else
                "boolean" if c in BOOLEAN_COLS else "text") for c in csv.columns}
    bad = {c: t for c, t in types.items() if want.get(c) != t}
    checks.append(Check(a, "types: year/edition integer, value numeric, is_primary_series boolean, rest text", not bad,
                        f"{bad}" if bad else "all as expected"))

    rows = fetch(cur, f"SELECT * FROM clean.{TABLE}")
    checks.append(Check(a, "row count = staging row count (32)", len(rows) == len(csv) == 32,
                        f"table {len(rows)}, CSV {len(csv)}"))
    db = {(r["year"], r["metric"], r["geography_basis"]): r for r in rows}
    mismatches, examples = 0, []
    for rec in csv.to_dict("records"):
        key = (int(rec["year"]), rec["metric"], rec["geography_basis"])
        row = db.pop(key, None)
        if row is None:
            mismatches += 1
            examples.append(f"{key} missing")
            continue
        for col, text in rec.items():
            if not cell_equal(text, row[col], col):
                mismatches += 1
                examples.append(f"{key} {col}: CSV {text!r} vs table {row[col]!r}")
    mismatches += len(db)
    checks.append(Check(a, "every staging row reconciles cell by cell (incl. lineage columns)", mismatches == 0,
                        f"{len(csv)} rows × {csv.shape[1]} columns compared, {mismatches} mismatches"
                        + (": " + "; ".join(examples[:5]) if examples else "")))

    primary = fetch(cur, f"SELECT year, metric, count(*) n FROM clean.{TABLE} WHERE is_primary_series GROUP BY 1, 2")
    ok = len(primary) == len(YEARS) * len(METRICS) and all(p["n"] == 1 for p in primary)
    checks.append(Check(a, "exactly one primary-series row per metric per year (28)", ok, f"{len(primary)} year × metric pairs"))
    bridge = fetch(cur, f"""SELECT metric, array_agg(geography_basis ORDER BY geography_basis) b,
                                   bool_and(is_primary_series = (geography_basis = '2021_census')) p
                            FROM clean.{TABLE} WHERE year = 2022 GROUP BY metric""")
    ok = len(bridge) == 4 and all(r["b"] == ["2021_census", "pre_2021_census"] and r["p"] for r in bridge)
    checks.append(Check(a, "2022 keeps both geography bases; 2021_census row is primary", ok,
                        f"{len(bridge)} metrics with both 2022 rows"))
    sup = fetch(cur, f"""SELECT count(*) FILTER (WHERE value IS NULL) nulls,
                                count(*) FILTER (WHERE value_status = 'suppressed') suppressed,
                                count(*) FILTER (WHERE (value IS NULL) <> (value_status <> 'published')) bad,
                                count(*) FILTER (WHERE value = 0 AND raw_value = '**') zero_from_suppressed
                         FROM clean.{TABLE}""")[0]
    csv_nulls = int((csv["value"] == "").sum())
    checks.append(Check(a, "NULL/suppression preserved (NULL ⇔ suppressed, never 0; NULL count = CSV)",
                        sup["bad"] == 0 and sup["zero_from_suppressed"] == 0 and sup["nulls"] == csv_nulls,
                        f"{sup['nulls']} NULL values (CSV {csv_nulls}), {sup['suppressed']} suppressed"))
    lineage = fetch(cur, f"""SELECT count(*) FILTER (WHERE source_workbook IS NULL OR source_table IS NULL
                                    OR source_cell IS NULL OR split_part(source_cell, '!', 1) <> source_table) bad,
                                    count(DISTINCT source_workbook || source_cell) cells
                             FROM clean.{TABLE}""")[0]
    checks.append(Check(a, "source lineage complete and unique", lineage["bad"] == 0 and lineage["cells"] == 32,
                        f"{lineage['cells']} distinct source cells"))
    existing = fetch(cur, f"""SELECT h.year, h.metric, h.value hv, e.value ev, h.reliability_code hr, e.reliability_code er
                              FROM clean.{TABLE} h JOIN clean.rental_market_windsor e
                                ON e.source_table = h.source_table AND e.zone = 'Windsor CMA'
                               AND e.bedroom_type = h.bedroom_type AND e.metric = h.metric
                               AND e.period_label = h.period_label
                              WHERE h.year IN (2024, 2025)""")
    ok = len(existing) == 8 and all(r["hv"] == r["ev"] and r["hr"] == r["er"] for r in existing)
    checks.append(Check(a, "2024-2025 equal the existing clean.rental_market_windsor (value, reliability)", ok,
                        f"{len(existing)} rows compared in PostgreSQL"))
    return checks


def view_checks(cur, csv: pd.DataFrame) -> tuple[list[Check], dict]:
    a = "views"
    checks = []
    present = {r["table_name"] for r in fetch(cur, "SELECT table_name FROM information_schema.views "
                                                   "WHERE table_schema = 'analysis'")}
    missing = set(HISTORY_VIEWS) - present
    checks.append(Check(a, f"the {len(HISTORY_VIEWS)} history views exist", not missing,
                        f"missing {sorted(missing)}" if missing else ", ".join(HISTORY_VIEWS)))
    if missing:
        return checks, {}
    refs = {r["table_name"] for r in fetch(cur, """SELECT DISTINCT table_schema || '.' || table_name AS table_name
                                                  FROM information_schema.view_table_usage
                                                  WHERE view_schema = 'analysis' AND view_name = ANY(%s)""",
                                           (HISTORY_VIEWS,))}
    checks.append(Check(a, f"history views read only clean.{TABLE}", refs == {f"clean.{TABLE}"}, f"{sorted(refs)}"))

    primary = {(int(r["year"]), r["metric"]): r for r in csv.to_dict("records") if r["is_primary_series"] == "True"}
    bench = {}
    for metric, (view, col) in SERIES_VIEWS.items():
        rows = {r["year"]: r for r in fetch(cur, f"SELECT * FROM analysis.{view}")}
        problems = []
        if sorted(rows) != YEARS:
            problems.append(f"years {sorted(rows)}")
        for y in YEARS:
            exp = primary[(y, metric)]
            got = rows.get(y)
            if got is None:
                continue
            bench[(y, metric)] = got[col]
            if got[col] != dec(exp["value"]) or got["geography_basis"] != exp["geography_basis"] \
                    or got["source_cell"] != exp["source_cell"] or got["value_status"] != exp["value_status"]:
                problems.append(f"{y}: view {got[col]} vs CSV {exp['value']}")
            prev = primary.get((y - 1, metric))
            same = prev is not None and prev["geography_basis"] == exp["geography_basis"]
            change_col = "change_dollars" if metric == "average_rent" else "change_pct_points"
            want = (dec(exp["value"]) - dec(prev["value"])) if same and exp["value"] and prev["value"] else None
            if got[change_col] != want or (prev is not None and got["comparable_with_previous_year"] != same):
                problems.append(f"{y} change: view {got[change_col]} vs expected {want}")
            if metric == "average_rent":
                want_pct = r4(Decimal(100) * want / dec(prev["value"])) if want is not None else None
                if got["change_pct"] != want_pct:
                    problems.append(f"{y} change_pct: view {got['change_pct']} vs {want_pct}")
        checks.append(Check(a, f"{view}: every year 2019-2025 benchmarked against staging (value, basis, lineage, change)",
                            not problems, "; ".join(problems[:5]) or "7 years match"))
        cross = [y for y in YEARS if rows.get(y) and rows[y]["comparable_with_previous_year"] is False]
        checks.append(Check(a, f"{view}: change across the 2022 geography break is NULL and flagged",
                            cross == [2022] and rows[2022][change_col] is None, f"non-comparable years: {cross}"))

    uni = fetch(cur, "SELECT * FROM analysis.story2_historical_rental_universe")
    csv_uni = {(int(r["year"]), r["geography_basis"]): r for r in csv.to_dict("records") if r["metric"] == "rental_universe"}
    problems = []
    for r in uni:
        exp = csv_uni.get((r["year"], r["geography_basis"]))
        prev = csv_uni.get((r["year"] - 1, r["geography_basis"]))
        want = dec(exp["value"]) - dec(prev["value"]) if exp and prev else None
        if exp is None or r["rental_universe_units"] != dec(exp["value"]) or r["change_units_same_boundary"] != want:
            problems.append(f"{r['year']} {r['geography_basis']}")
    both_2022 = sorted(r["geography_basis"] for r in uni if r["year"] == 2022)
    checks.append(Check(a, "rental universe: all 8 rows, both 2022 boundaries, changes only within a boundary",
                        len(uni) == 8 and both_2022 == ["2021_census", "pre_2021_census"] and not problems,
                        f"{len(uni)} rows; 2022 bases {both_2022}" + (f"; bad {problems}" if problems else "")))

    summary = {(r["metric"], r["era"]): r for r in fetch(cur, "SELECT * FROM analysis.story2_historical_period_summary")}
    problems = []
    for metric in SERIES_VIEWS:
        for era, years in (("2019-2021", range(2019, 2022)), ("2022-2025", range(2022, 2026))):
            vals = [dec(primary[(y, metric)]["value"]) for y in years]
            pub = [v for v in vals if v is not None]
            s = summary.get((metric, era))
            want = {"published_years": len(pub), "mean_of_annual_values": r4(sum(pub) / len(pub)),
                    "min_value": min(pub), "max_value": max(pub), "first_year_value": vals[0], "last_year_value": vals[-1]}
            if s is None or any(s[k] != v for k, v in want.items()):
                problems.append(f"{metric} {era}")
    checks.append(Check(a, "period summary (mean/min/max/first/last per era) recomputes from staging; no universe",
                        not problems and len(summary) == 6 and not any(m == "rental_universe" for m, _ in summary),
                        f"{len(summary)} rows" + (f"; bad {problems}" if problems else "")))
    return checks, bench


def unchanged_checks(conn, cur) -> list[Check]:
    a = "existing objects"
    checks = []
    if not BASELINE_PATH.exists():
        return [Check(a, "pre-migration baseline exists", False, f"missing {BASELINE_PATH}")]
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    now = fingerprint(cur)
    changed = [t for t, meta in baseline["clean_tables"].items() if now["clean_tables"].get(t) != meta]
    checks.append(Check(a, "5 original clean tables unchanged (columns, constraints, indexes, row count, content hash)",
                        not changed, "; ".join(changed) or ", ".join(f"{t} {m['rows']:,}"
                                                                     for t, m in now["clean_tables"].items())))
    base_views, now_views = baseline["analysis_views"], now["analysis_views"]
    changed = [v for v in base_views if now_views.get(v) != base_views[v]]
    added = sorted(set(now_views) - set(base_views))
    checks.append(Check(a, f"{len(base_views)} original analysis views present with identical definitions",
                        not changed and not added and len(base_views) == 31,
                        f"changed/missing: {changed}; unexpected: {added}" if changed or added else "31 definitions identical"))
    conn.rollback()
    pg = vpl.run_checks(conn)
    failed = [f"{c.table}: {c.name}" for c in pg if not c.passed]
    checks.append(Check(a, "existing PostgreSQL load validation still passes", not failed,
                        f"{len(pg) - len(failed)}/{len(pg)} passed" + (f"; {failed[:5]}" if failed else "")))
    an = vav.run_checks(conn)
    failed = [f"[{c.area}] {c.name}" for c in an if not c.passed]
    checks.append(Check(a, "existing analysis validation still passes (now incl. history views)", not failed,
                        f"{len(an) - len(failed)}/{len(an)} passed" + (f"; {failed[:5]}" if failed else "")))
    return checks


def run_checks(conn, staging_dir: Path = STAGING_DIR) -> tuple[list[Check], dict]:
    csv = read_staging(staging_dir / OUTPUT_NAME)
    with conn.cursor() as cur:
        checks = table_checks(cur, csv)
        vchecks, bench = view_checks(cur, csv)
        checks += vchecks
        checks += unchanged_checks(conn, cur)
    conn.rollback()
    return checks, bench


def render(checks: list[Check], bench: dict, database: str) -> str:
    failed = [c for c in checks if not c.passed]
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [f"HISTORICAL RENTAL POSTGRESQL STATUS: {'FAIL' if failed else 'PASS'}", "",
             "# Historical Rental — PostgreSQL Validation", "",
             f"Generated by `etl/validate_rental_history_postgres.py` on {now}, querying the live database `{database}`.",
             f"**{len(checks) - len(failed)} of {len(checks)} checks passed.**", "",
             "## Benchmark values (primary series, from the analysis views)", "",
             "| Year | 2-bedroom rent ($) | Vacancy (%) | Turnover (%) | Geography basis |", "|---|---|---|---|---|"]
    for y in YEARS:
        basis = "2021 census" if y >= 2022 else "pre-2021 census"
        lines.append(f"| {y} | {bench.get((y, 'average_rent'))} | {bench.get((y, 'vacancy_rate'))} | "
                     f"{bench.get((y, 'turnover_rate'))} | {basis} |")
    lines.append("")
    if failed:
        lines += ["## Failed checks", "", "| Area | Check | Detail |", "|---|---|---|"]
        lines += [f"| {c.area} | {c.name} | {c.detail} |" for c in failed] + [""]
    lines += ["## All checks", "", "| Area | Check | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {c.area} | {c.name} | {'PASS' if c.passed else '**FAIL**'} | {c.detail.replace('|', chr(92) + '|')} |"
              for c in checks]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        REPORT_PATH.write_text(f"HISTORICAL RENTAL POSTGRESQL STATUS: FAIL\n\nCannot connect: {exc}\n", encoding="utf-8")
        print(f"HISTORICAL RENTAL POSTGRESQL STATUS: FAIL (cannot connect: {exc})")
        return 1
    try:
        checks, bench = run_checks(conn)
        database = conn.get_dsn_parameters()["dbname"]
    finally:
        conn.close()
    REPORT_PATH.write_text(render(checks, bench, database), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    for c in failed:
        print(f"FAIL  [{c.area}] {c.name} -- {c.detail}")
    print(f"HISTORICAL RENTAL POSTGRESQL STATUS: {'FAIL' if failed else 'PASS'} "
          f"({len(checks) - len(failed)}/{len(checks)} checks passed)")
    print(f"Report written: {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
