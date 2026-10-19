"""
Validate the `analysis` views in the LIVE PostgreSQL database and write
docs/SQL_ANALYSIS_VALIDATION.md, whose first line is exactly
"SQL ANALYTICS STATUS: PASS" or "SQL ANALYTICS STATUS: FAIL".

    .venv\\Scripts\\python.exe etl\\validate_analysis_views.py

Exit code 0 = PASS, 1 = FAIL. Read-only (SELECT only).

Traceability checks do not trust the views: they re-read clean.* with plain
SELECTs and recompute the same numbers in Python (Decimal arithmetic), then
compare row by row. Source safety re-runs the PostgreSQL load validation
(clean.* still equals data/staging/ cell by cell) and the raw-file manifest.
"""

from __future__ import annotations

import datetime
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import psycopg2

import validate_postgres_load as vpl
from cleaning_common import PROJECT_ROOT, STAGING_DIR, verify_raw_manifest
from load_cleaned_to_postgres import LoadError, connect

REPORT_PATH = PROJECT_ROOT / "docs" / "SQL_ANALYSIS_VALIDATION.md"
SCHEMA = "analysis"

EXPECTED_VIEWS = {
    "story1_shelter_cost_burden", "story1_affordability_by_tenure", "story1_tenure_burden_gap",
    "story1_affordability_by_income_group", "story1_affordability_by_household_type",
    "story1_burden_severity_by_tenure", "story1_burden_vs_census_published",
    "story2_survey_periods", "story2_period_change", "story2_same_sample_rent_change", "story2_latest_cma_kpis",
    "story2_rent_by_bedroom", "story2_vacancy_by_bedroom", "story2_turnover_by_bedroom", "story2_rental_universe",
    "story2_zone_comparison", "story2_vacant_vs_occupied_rent", "story2_new_rental_stock",
    "story2_income_quintile_rental_stock",
    "story3_supply_totals", "story3_supply_by_dwelling_type", "story3_starts_by_dwelling_type",
    "story3_completions_by_dwelling_type", "story3_under_construction_by_dwelling_type",
    "story3_ytd_starts_completions",
    "story4_cma_metric_ranking", "story4_cma_vacancy_comparison", "story4_cma_rent_2br_comparison",
    "story4_cma_turnover_comparison", "story4_cma_rent_growth_comparison", "story4_windsor_position",
}
# analytical key per view: must be unique
VIEW_KEYS = {
    "story1_shelter_cost_burden": ["income_group_member_id", "household_type_member_id", "tenure_member_id"],
    "story1_affordability_by_tenure": ["tenure"],
    "story1_affordability_by_income_group": ["income_group_order", "tenure"],
    "story1_affordability_by_household_type": ["household_type_member_id", "tenure"],
    "story1_burden_severity_by_tenure": ["tenure", "severity_category"],
    "story1_burden_vs_census_published": ["tenure"],
    "story2_period_change": ["source_table", "zone", "bedroom_type", "metric"],
    "story2_same_sample_rent_change": ["source_table", "zone", "bedroom_type", "change_period_label"],
    "story2_latest_cma_kpis": ["dwelling_scope", "metric"],
    "story2_rent_by_bedroom": ["dwelling_scope", "bedroom_type"],
    "story2_vacancy_by_bedroom": ["dwelling_scope", "bedroom_type"],
    "story2_turnover_by_bedroom": ["dwelling_scope", "bedroom_type"],
    "story2_rental_universe": ["dwelling_scope", "zone", "bedroom_type"],
    "story2_zone_comparison": ["dwelling_scope", "zone"],
    "story2_vacant_vs_occupied_rent": ["dwelling_scope", "zone", "bedroom_type"],
    "story2_new_rental_stock": ["zone", "bedroom_type"],
    "story2_income_quintile_rental_stock": ["zone", "bedroom_type", "income_quintile"],
    "story3_supply_totals": ["source_table", "activity"],
    "story3_supply_by_dwelling_type": ["source_table", "activity", "dwelling_type"],
    "story3_ytd_starts_completions": ["dwelling_type"],
    "story4_cma_metric_ranking": ["centre", "metric"],
    "story4_windsor_position": ["metric"],
}
SCOPES = {"apartment", "row_townhouse", "row_and_apartment"}
RMS_PERIODS = {"Oct-24", "Oct-25", "Oct-23 to Oct-24", "Oct-24 to Oct-25"}
SUPPLY_PERIODS = {"August 2026", "January to August 2026"}
TOTAL_INCOME = "Total - Total income of household"
TOTAL_HOUSEHOLD = "Total - Household type including census family structure"
BURDEN = "Spending 30% or more of income on shelter costs"
ROUNDING_STEP = 5  # StatCan random rounding of counts


@dataclass
class Check:
    area: str
    name: str
    passed: bool
    detail: str


def fetch(cur, sql: str, params=()) -> list[dict]:
    cur.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def scalar(cur, sql: str, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def r4(x: Decimal | None) -> Decimal | None:
    return None if x is None else x.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def r1(x: Decimal | None) -> Decimal | None:
    return None if x is None else x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def pct(num, den) -> Decimal | None:
    if num is None or den is None or den == 0:
        return None
    return r4(Decimal(100) * Decimal(num) / Decimal(den))


def compare(expected: dict, actual: dict, fields: list[str]) -> tuple[int, list[str]]:
    """expected/actual: key -> row dict. Returns (mismatch count, examples)."""
    mismatches, examples = 0, []
    for key in set(expected) | set(actual):
        e, a = expected.get(key), actual.get(key)
        if e is None or a is None:
            mismatches += 1
            examples.append(f"{key}: {'missing from view' if a is None else 'not expected'}")
            continue
        for f in fields:
            if e[f] != a[f]:
                mismatches += 1
                examples.append(f"{key} {f}: expected {e[f]!r}, view {a[f]!r}")
    return mismatches, examples[:5]


def check_compare(area, name, expected, actual, fields) -> Check:
    n, ex = compare(expected, actual, fields)
    return Check(area, name, n == 0, f"{len(expected)} rows recomputed from clean.*, {n} mismatches"
                 + (": " + "; ".join(ex) if ex else ""))


# ---------------------------------------------------------------------------
# Schema and source safety
# ---------------------------------------------------------------------------

def schema_checks(cur) -> list[Check]:
    checks = []
    exists = scalar(cur, "SELECT count(*) FROM pg_namespace WHERE nspname = %s", (SCHEMA,))
    checks.append(Check("schema", "analysis schema exists", exists == 1, f"{exists} schema"))
    views = {r["table_name"] for r in fetch(cur, "SELECT table_name FROM information_schema.views WHERE table_schema = %s",
                                            (SCHEMA,))}
    missing, extra = EXPECTED_VIEWS - views, views - EXPECTED_VIEWS
    checks.append(Check("schema", f"exactly the {len(EXPECTED_VIEWS)} expected views exist", not missing and not extra,
                        f"{len(views)} views" + (f"; missing {sorted(missing)}" if missing else "")
                        + (f"; unexpected {sorted(extra)}" if extra else "")))
    others = fetch(cur, """SELECT c.relname, c.relkind::text AS kind FROM pg_class c
                           JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s AND c.relkind <> 'v'""",
                   (SCHEMA,))
    checks.append(Check("schema", "no tables / materialized views / other relations in analysis", not others,
                        ", ".join(f"{o['relname']} ({o['kind']})" for o in others) or "views only"))
    refs = fetch(cur, """SELECT DISTINCT table_schema FROM information_schema.view_table_usage
                         WHERE view_schema = %s""", (SCHEMA,))
    schemas = sorted(r["table_schema"] for r in refs)
    checks.append(Check("schema", "views read only clean.* (and other analysis views)",
                        set(schemas) <= {"clean", SCHEMA} and "clean" in schemas, f"referenced schemas: {schemas}"))
    no_comment = [r["relname"] for r in fetch(cur, """
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind = 'v' AND obj_description(c.oid, 'pg_class') IS NULL""", (SCHEMA,))]
    checks.append(Check("schema", "every view has a grain/purpose comment", not no_comment,
                        ", ".join(no_comment) or "all commented"))
    if not missing:
        for view, keys in VIEW_KEYS.items():
            dupes = scalar(cur, f"SELECT count(*) FROM (SELECT 1 FROM {SCHEMA}.{view} GROUP BY {', '.join(keys)} "
                                "HAVING count(*) > 1) d")
            checks.append(Check("schema", f"{view}: no duplicate analytical keys ({', '.join(keys)})", dupes == 0,
                                f"{dupes} duplicated keys"))
    return checks


def source_safety_checks(conn, cur) -> list[Check]:
    checks = []
    counts = {t: scalar(cur, f"SELECT count(*) FROM clean.{t}") for t in vpl.EXPECTED_ROWS}
    bad = {t: n for t, n in counts.items() if n != vpl.EXPECTED_ROWS[t]}
    checks.append(Check("source safety", "clean.* row counts unchanged", not bad,
                        ", ".join(f"{t} {n:,}" for t, n in counts.items())))
    load_checks = vpl.run_checks(conn)  # read-only; rolls back its own transaction
    failed = [f"{c.table}: {c.name}" for c in load_checks if not c.passed]
    checks.append(Check("source safety", "clean.* still equals data/staging/ cell by cell (PostgreSQL load checks)",
                        not failed, f"{len(load_checks) - len(failed)}/{len(load_checks)} load checks passed"
                        + (f"; failed: {failed[:5]}" if failed else "")))
    problems = verify_raw_manifest()
    checks.append(Check("source safety", "data/raw/ files match etl/raw_manifest.json (SHA-256)", not problems,
                        "; ".join(problems) or "all raw files unchanged"))
    return checks


# ---------------------------------------------------------------------------
# Story 1
# ---------------------------------------------------------------------------

def expected_story1_burden(cur) -> dict:
    """Recompute analysis.story1_shelter_cost_burden from clean.shelter_cost rows in Python."""
    cells = defaultdict(dict)
    labels = {}
    for r in fetch(cur, """SELECT income_group_member_id, income_group, household_type_member_id, tenure_member_id,
                                  shelter_cost_ratio, value
                           FROM clean.shelter_cost
                           WHERE measure_kind = 'household_count' AND value_status = 'published'"""):
        key = (r["income_group_member_id"], r["household_type_member_id"], r["tenure_member_id"])
        cells[key][r["shelter_cost_ratio"]] = r["value"]
        labels[key] = r["income_group"]
    expected = {}
    for key, c in cells.items():
        total = c.get("Total - Shelter-cost-to-income ratio")
        burden = c.get(BURDEN)
        if "Not applicable" in c:
            basis, na = "published", c["Not applicable"]
        elif labels[key] not in (TOTAL_INCOME, "Under $10,000"):
            basis, na = "zero_by_definition", Decimal(0)
        else:
            basis, na = "missing", None
        applicable = None if total is None or na is None else total - na
        rate = pct(burden, applicable)
        if rate is not None and burden > applicable:  # rounding artefact: never published as > 100%
            rate = None
        expected[key] = {"applicable_households": applicable, "burden_30_plus_households": burden,
                         "not_applicable_basis": basis, "burden_30_plus_pct": rate}
    return expected


def story1_checks(cur) -> list[Check]:
    a = "story 1"
    checks = []
    tenure = {r["tenure"]: r for r in fetch(cur, f"SELECT * FROM {SCHEMA}.story1_affordability_by_tenure")}
    for t, num, rate in [("Owner", 13_005, Decimal("10.9")), ("Renter", 15_735, Decimal("34.8"))]:
        row = tenure.get(t, {})
        checks.append(Check(a, f"{t} 30%+ numerator = {num:,}", row.get("numerator_burden_30_plus_households") == num,
                            f"{row.get('numerator_burden_30_plus_households')}"))
        checks.append(Check(a, f"{t} burden rounds to {rate}%", r1(row.get("burden_30_plus_pct")) == rate,
                            f"{row.get('burden_30_plus_pct')}% = {row.get('numerator_burden_30_plus_households')} / "
                            f"{row.get('denominator_applicable_households')}"))
    dens = [r["denominator_applicable_households"] for r in tenure.values()]
    checks.append(Check(a, "tenure denominators > 0", len(dens) == 3 and all(d and d > 0 for d in dens), f"{dens}"))

    census = fetch(cur, f"SELECT tenure, difference_pct_points_1dp FROM {SCHEMA}.story1_burden_vs_census_published")
    checks.append(Check(a, "calculated burden equals Census Profile published rate (1 dp)",
                        len(census) == 3 and all(r["difference_pct_points_1dp"] == 0 for r in census),
                        ", ".join(f"{r['tenure']}: diff {r['difference_pct_points_1dp']}" for r in census)))

    expected = expected_story1_burden(cur)
    actual = {(r["income_group_member_id"], r["household_type_member_id"], r["tenure_member_id"]): r
              for r in fetch(cur, f"SELECT * FROM {SCHEMA}.story1_shelter_cost_burden")}
    checks.append(check_compare(a, "story1_shelter_cost_burden equals independent recomputation", expected, actual,
                                ["applicable_households", "burden_30_plus_households", "not_applicable_basis",
                                 "burden_30_plus_pct"]))
    bad = [k for k, r in actual.items() if (r["burden_30_plus_pct"] is None) != (r["rate_null_reason"] is not None)]
    reasons = defaultdict(int)
    for r in actual.values():
        reasons[r["rate_null_reason"] or "rate calculated"] += 1
    checks.append(Check(a, "every NULL rate has a reason, every rate has none", not bad,
                        f"{len(bad)} inconsistent rows; " + ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items()))))
    bad = [k for k, r in actual.items() if r["burden_30_plus_pct"] is not None
           and not (r["applicable_households"] > 0 and 0 <= r["burden_30_plus_pct"] <= 100)]
    checks.append(Check(a, "all rates have denominator > 0 and lie within 0-100", not bad, f"{len(bad)} bad rows"))
    zero_def = {r["income_group"] for r in actual.values() if r["not_applicable_basis"] == "zero_by_definition"}
    checks.append(Check(a, "'zero_by_definition' only used for income bands of $10,000 and over",
                        not zero_def & {TOTAL_INCOME, "Under $10,000"} and len(zero_def) == 10,
                        f"{len(zero_def)} bands: {sorted(zero_def)[:3]}..."))

    bands = fetch(cur, f"SELECT * FROM {SCHEMA}.story1_affordability_by_income_group")
    checks.append(Check(a, "income-group view has 11 bands x 3 tenures, no Total / dollar rows",
                        len(bands) == 33 and not {b["income_group"] for b in bands} & {TOTAL_INCOME}
                        and not any("($)" in b["income_group"] for b in bands), f"{len(bands)} rows"))
    for t in ["Owner", "Renter", "Total - Tenure"]:
        parts = sum(b["numerator_burden_30_plus_households"] for b in bands if b["tenure"] == t)
        total = tenure[t]["numerator_burden_30_plus_households"]
        tol = ROUNDING_STEP * 11
        checks.append(Check(a, f"{t}: income bands' 30%+ counts sum to the tenure total (no double counting)",
                            abs(parts - total) <= tol, f"bands {parts} vs total {total} (rounding tolerance {tol})"))

    hh = fetch(cur, f"SELECT * FROM {SCHEMA}.story1_affordability_by_household_type")
    by = {(r["household_type_member_id"], r["tenure"]): r for r in hh}
    bad = []
    for (member, t), r in by.items():
        children = [c for c in hh if c["parent_member_id"] == member and c["tenure"] == t]
        if children:
            total = sum(c["total_households"] for c in children)
            if abs(total - r["total_households"]) > ROUNDING_STEP * len(children):
                bad.append(f"{member}/{t}: children {total} vs {r['total_households']}")
    checks.append(Check(a, "household-type hierarchy: children sum to parent (within StatCan rounding)",
                        not bad and len(hh) == 48, f"{len(hh)} rows; " + ("; ".join(bad[:5]) or "all parents reconcile")))

    sev = fetch(cur, f"SELECT * FROM {SCHEMA}.story1_burden_severity_by_tenure")
    bad = []
    for t in tenure:
        rows_t = {s["severity_category"]: s for s in sev if s["tenure"] == t}
        derived = tenure_row = None
        derived = rows_t.get("100% or more", {}).get("households")
        base = fetch(cur, f"""SELECT burden_30_plus_households - burden_30_to_under_100_households AS d
                              FROM {SCHEMA}.story1_shelter_cost_burden
                              WHERE is_income_total AND is_household_type_total AND tenure = %s""", (t,))
        if len(rows_t) != 3 or derived != base[0]["d"]:
            bad.append(t)
    checks.append(Check(a, "severity categories present and 100%+ = 30%+ minus 30-<100%", not bad and len(sev) == 9,
                        f"{len(sev)} rows" + (f"; bad: {bad}" if bad else "")))
    return checks


# ---------------------------------------------------------------------------
# Story 2
# ---------------------------------------------------------------------------

STORY2_VIEWS = ["story2_period_change", "story2_same_sample_rent_change", "story2_latest_cma_kpis",
                "story2_rent_by_bedroom", "story2_vacancy_by_bedroom", "story2_turnover_by_bedroom",
                "story2_rental_universe", "story2_zone_comparison", "story2_vacant_vs_occupied_rent",
                "story2_new_rental_stock", "story2_income_quintile_rental_stock"]


def story2_checks(cur) -> list[Check]:
    a = "story 2"
    checks = []
    for view in STORY2_VIEWS:
        geos = sorted(r["geography"] for r in fetch(cur, f"SELECT DISTINCT geography FROM {SCHEMA}.{view}"))
        scopes = {r["dwelling_scope"] for r in fetch(cur, f"SELECT DISTINCT dwelling_scope FROM {SCHEMA}.{view}")}
        checks.append(Check(a, f"{view}: Windsor CMA only, dwelling_scope kept and valid",
                            geos == ["Windsor CMA"] and scopes <= SCOPES and None not in scopes,
                            f"geography {geos}; scopes {sorted(s for s in scopes if s)}"))

    periods = {r["period_label"] for r in fetch(cur, f"SELECT period_label FROM {SCHEMA}.story2_survey_periods")}
    latest = fetch(cur, f"SELECT period_kind, period_label FROM {SCHEMA}.story2_survey_periods WHERE is_latest")
    checks.append(Check(a, "only the real periods exist (Oct-24, Oct-25 and the two rent-change periods)",
                        periods == RMS_PERIODS, f"{sorted(periods)}; latest: {[(r['period_kind'], r['period_label']) for r in latest]}"))
    pc = fetch(cur, f"SELECT * FROM {SCHEMA}.story2_period_change")
    labels = {(r["previous_period_label"], r["latest_period_label"]) for r in pc}
    checks.append(Check(a, "period_change compares Oct-24 with Oct-25 only", labels == {("Oct-24", "Oct-25")},
                        f"{labels}"))
    checks.append(Check(a, "period_change covers 3 scopes x 9 zones x 5 bedrooms x 4 metrics",
                        len(pc) == 540 and {r["dwelling_scope"] for r in pc} == SCOPES, f"{len(pc)} rows"))

    # Independent recomputation of period_change from clean.rental_market_windsor
    cells = {}
    for r in fetch(cur, "SELECT source_table, zone, bedroom_type, metric, period_label, value, value_status "
                        "FROM clean.rental_market_windsor WHERE period_label IN ('Oct-24', 'Oct-25')"):
        cells[(r["source_table"], r["zone"], r["bedroom_type"], r["metric"], r["period_label"])] = r
    expected = {}
    for (table, zone, bed, metric, period), r in cells.items():
        prev = cells.get((table, zone, bed, metric, "Oct-24"))
        if period != "Oct-25" or prev is None:
            continue
        change = r["value"] - prev["value"] if r["value"] is not None and prev["value"] is not None else None
        unit_pct = None
        if change is not None and metric in ("average_rent", "rental_universe"):
            unit_pct = pct(change, prev["value"])
        expected[(table, zone, bed, metric)] = {"latest_value": r["value"], "previous_value": prev["value"],
                                                "change_value": change, "change_pct": unit_pct}
    actual = {(r["source_table"], r["zone"], r["bedroom_type"], r["metric"]): r for r in pc}
    checks.append(check_compare(a, "story2_period_change equals independent recomputation", expected, actual,
                                ["latest_value", "previous_value", "change_value", "change_pct"]))

    leaked = [r for r in pc if r["change_value"] is not None
              and (r["latest_value_status"] != "published" or r["previous_value_status"] != "published")]
    checks.append(Check(a, "suppressed / unpublished values never enter a change calculation", not leaked,
                        f"{sum(1 for r in pc if not r['is_comparable'])} non-comparable rows, all with NULL change; "
                        f"{len(leaked)} leaks"))
    leaks = scalar(cur, f"""SELECT count(*) FROM {SCHEMA}.story2_vacant_vs_occupied_rent
                            WHERE vacant_minus_occupied_dollars IS NOT NULL
                              AND (vacant_units_rent_status <> 'published' OR occupied_units_rent_status <> 'published')""")
    leaks += scalar(cur, f"""SELECT count(*) FROM {SCHEMA}.story2_income_quintile_rental_stock
                             WHERE share_of_universe_pct IS NOT NULL
                               AND (universe_status <> 'published' OR total_universe_units IS NULL)""")
    leaks += scalar(cur, f"""SELECT count(*) FROM {SCHEMA}.story2_same_sample_rent_change
                             WHERE (rent_change_pct IS NULL) <> (value_status <> 'published')""")
    checks.append(Check(a, "suppressed values excluded from differences, shares and rent-change figures", leaks == 0,
                        f"{leaks} leaks"))

    rents = fetch(cur, f"""
        SELECT 'rent_by_bedroom' v, latest_average_rent x FROM {SCHEMA}.story2_rent_by_bedroom
        UNION ALL SELECT 'rent_by_bedroom', previous_average_rent FROM {SCHEMA}.story2_rent_by_bedroom
        UNION ALL SELECT 'zone_comparison', average_rent FROM {SCHEMA}.story2_zone_comparison
        UNION ALL SELECT 'vacant', vacant_units_average_rent FROM {SCHEMA}.story2_vacant_vs_occupied_rent
        UNION ALL SELECT 'occupied', occupied_units_average_rent FROM {SCHEMA}.story2_vacant_vs_occupied_rent
        UNION ALL SELECT 'new_stock', new_stock_average_rent FROM {SCHEMA}.story2_new_rental_stock""")
    published = [r["x"] for r in rents if r["x"] is not None]
    checks.append(Check(a, "published rents > 0 in every rent view", published and all(x > 0 for x in published),
                        f"{len(published)} published rents, min {min(published) if published else None}"))
    rates = fetch(cur, f"""
        SELECT latest_vacancy_rate_pct x FROM {SCHEMA}.story2_vacancy_by_bedroom
        UNION ALL SELECT previous_vacancy_rate_pct FROM {SCHEMA}.story2_vacancy_by_bedroom
        UNION ALL SELECT latest_turnover_rate_pct FROM {SCHEMA}.story2_turnover_by_bedroom
        UNION ALL SELECT previous_turnover_rate_pct FROM {SCHEMA}.story2_turnover_by_bedroom
        UNION ALL SELECT vacancy_rate_pct FROM {SCHEMA}.story2_zone_comparison
        UNION ALL SELECT turnover_rate_pct FROM {SCHEMA}.story2_zone_comparison
        UNION ALL SELECT vacancy_rate_pct FROM {SCHEMA}.story2_income_quintile_rental_stock
        UNION ALL SELECT share_of_universe_pct FROM {SCHEMA}.story2_income_quintile_rental_stock
        UNION ALL SELECT share_of_zone_universe_pct FROM {SCHEMA}.story2_rental_universe
        UNION ALL SELECT new_stock_vacancy_rate_pct FROM {SCHEMA}.story2_new_rental_stock""")
    vals = [r["x"] for r in rates if r["x"] is not None]
    checks.append(Check(a, "rates and shares within 0-100", all(0 <= x <= 100 for x in vals),
                        f"{len(vals)} values, range {min(vals)}–{max(vals)}"))
    changes = [r["rent_change_pct"] for r in fetch(cur, f"SELECT rent_change_pct FROM {SCHEMA}.story2_same_sample_rent_change")
               if r["rent_change_pct"] is not None]
    checks.append(Check(a, "same-sample rent changes within -100 to 100", all(-100 <= x <= 100 for x in changes),
                        f"{len(changes)} values"))

    kpis = fetch(cur, f"SELECT * FROM {SCHEMA}.story2_latest_cma_kpis")
    clean_kpi = {(r["dwelling_scope"], r["metric"]): r["value"] for r in fetch(cur, """
        SELECT dwelling_scope, metric, value FROM clean.rental_market_windsor
        WHERE zone = 'Windsor CMA' AND bedroom_type = 'Total' AND period_label = 'Oct-25'
          AND metric IN ('vacancy_rate', 'turnover_rate', 'average_rent', 'rental_universe')""")}
    bad = [k for k in clean_kpi if {(r["dwelling_scope"], r["metric"]): r["latest_value"] for r in kpis}.get(k) != clean_kpi[k]]
    checks.append(Check(a, "latest CMA KPIs equal clean.rental_market_windsor (Windsor CMA, Total, Oct-25)",
                        len(kpis) == 12 and not bad, f"{len(kpis)} KPI rows; mismatches {bad}"))

    q = fetch(cur, f"SELECT * FROM {SCHEMA}.story2_income_quintile_rental_stock")
    totals = {(r["zone"], r["bedroom_type"]): r["universe_units"] for r in q if r["income_quintile"] == "Total"}
    bad = [r for r in q if r["income_quintile"] != "Total"
           and r["share_of_universe_pct"] != pct(r["universe_units"], totals.get((r["zone"], r["bedroom_type"])))]
    checks.append(Check(a, "income-quintile shares recompute from clean values", not bad and len(q) == 315,
                        f"{len(q)} rows, {len(bad)} mismatches"))
    return checks


# ---------------------------------------------------------------------------
# Story 3
# ---------------------------------------------------------------------------

STORY3_VIEWS = ["story3_supply_totals", "story3_supply_by_dwelling_type", "story3_starts_by_dwelling_type",
                "story3_completions_by_dwelling_type", "story3_under_construction_by_dwelling_type",
                "story3_ytd_starts_completions"]


def story3_checks(cur) -> list[Check]:
    a = "story 3"
    checks = []
    for view in STORY3_VIEWS:
        geos = sorted(r["geography"] for r in fetch(cur, f"SELECT DISTINCT geography FROM {SCHEMA}.{view}"))
        periods = {r["period_label"] for r in fetch(cur, f"SELECT DISTINCT period_label FROM {SCHEMA}.{view}")}
        checks.append(Check(a, f"{view}: Windsor CMA only, August 2026 / Jan-Aug 2026 periods only",
                            geos == ["Windsor CMA"] and periods <= SUPPLY_PERIODS and periods,
                            f"geography {geos}; periods {sorted(periods)}"))

    clean_rows = fetch(cur, "SELECT source_table, activity, dwelling_type, units FROM clean.starts_completions_windsor")
    sums, totals = defaultdict(int), {}
    for r in clean_rows:
        if r["dwelling_type"] == "Total":
            totals[(r["source_table"], r["activity"])] = r["units"]
        else:
            sums[(r["source_table"], r["activity"])] += r["units"]
    view_totals = {(r["source_table"], r["activity"]): r for r in fetch(cur, f"SELECT * FROM {SCHEMA}.story3_supply_totals")}
    bad = [k for k in totals if sums[k] != totals[k] or view_totals.get(k, {}).get("component_sum_units") != sums[k]
           or view_totals[k]["published_total_units"] != totals[k] or not view_totals[k]["total_reconciles"]]
    checks.append(Check(a, "components reconcile with published Total (recomputed from clean.*)",
                        not bad and len(view_totals) == 5,
                        "; ".join(f"{k[1]} {k[0]}: {sums[k]} = {totals[k]}" for k in sorted(totals)) or "none"))

    comp = fetch(cur, f"SELECT * FROM {SCHEMA}.story3_supply_by_dwelling_type")
    checks.append(Check(a, "Total row never counted as a component", len(comp) == 20
                        and "Total" not in {r["dwelling_type"] for r in comp}, f"{len(comp)} component rows"))
    neg = [r for r in comp if r["units"] is None or r["units"] < 0]
    checks.append(Check(a, "no negative or missing units", not neg, f"{len(neg)} bad rows"))
    expected = {(r["source_table"], r["activity"], r["dwelling_type"]): {"share_of_total_pct": pct(r["units"], sums[(r["source_table"], r["activity"])])}
                for r in clean_rows if r["dwelling_type"] != "Total"}
    actual = {(r["source_table"], r["activity"], r["dwelling_type"]): r for r in comp}
    checks.append(check_compare(a, "dwelling-type shares equal independent recomputation", expected, actual,
                                ["share_of_total_pct"]))
    share_sums = defaultdict(Decimal)
    for r in comp:
        key = (r["source_table"], r["activity"])
        # a NULL share (components not reconciling) poisons the group's sum
        share_sums[key] = None if share_sums[key] is None or r["share_of_total_pct"] is None \
            else share_sums[key] + r["share_of_total_pct"]
    checks.append(Check(a, "shares sum to 100% per activity and period",
                        all(s is not None and abs(s - 100) <= Decimal("0.001") for s in share_sums.values()),
                        ", ".join(f"{k[1]} {k[0]}: {s}" for k, s in sorted(share_sums.items()))))
    views = {"story3_starts_by_dwelling_type": ("Starts", "August 2026"),
             "story3_completions_by_dwelling_type": ("Completions", "August 2026"),
             "story3_under_construction_by_dwelling_type": ("Under Construction", "August 2026")}
    for view, (activity, period) in views.items():
        got = {(r["activity"], r["period_label"]) for r in fetch(cur, f"SELECT activity, period_label FROM {SCHEMA}.{view}")}
        n = scalar(cur, f"SELECT count(*) FROM {SCHEMA}.{view}")
        checks.append(Check(a, f"{view}: {activity}, {period}, 4 dwelling types", got == {(activity, period)} and n == 4,
                            f"{n} rows, {got}"))
    ytd = fetch(cur, f"SELECT * FROM {SCHEMA}.story3_ytd_starts_completions")
    checks.append(Check(a, "YTD view: 4 dwelling types, starts 594 / completions 881 in total",
                        len(ytd) == 4 and sum(r["ytd_starts_units"] for r in ytd) == totals[("Table A6_1", "Starts")]
                        and sum(r["ytd_completions_units"] for r in ytd) == totals[("Table A6_1", "Completions")],
                        f"starts {sum(r['ytd_starts_units'] for r in ytd)}, completions "
                        f"{sum(r['ytd_completions_units'] for r in ytd)}"))
    return checks


# ---------------------------------------------------------------------------
# Story 4
# ---------------------------------------------------------------------------

def story4_checks(cur) -> list[Check]:
    a = "story 4"
    checks = []
    ranking = fetch(cur, f"SELECT * FROM {SCHEMA}.story4_cma_metric_ranking")
    centres = {r["centre"] for r in ranking}
    clean_centres = {r["centre"] for r in fetch(cur, "SELECT DISTINCT centre FROM clean.rental_market_canada")}
    checks.append(Check(a, "all 42 CMAs of the source represented for each of 4 metrics",
                        centres == clean_centres and len(centres) == 42 and len(ranking) == 168
                        and {r["cmas_in_source"] for r in ranking} == {42}, f"{len(centres)} CMAs, {len(ranking)} rows"))
    bad = [c for c in centres if "CMA" not in c.split() or c.startswith("Canada") or "10,000+" in c or c.endswith(" CA")]
    checks.append(Check(a, "no province / CA / national rows", not bad, ", ".join(bad) or "CMA rows only"))
    scopes = {r["dwelling_scope"] for r in ranking}
    checks.append(Check(a, "apartment scope only", scopes == {"apartment"}, f"{scopes}"))
    for view, metric in [("story4_cma_vacancy_comparison", "vacancy_rate"),
                         ("story4_cma_rent_2br_comparison", "average_rent_2br"),
                         ("story4_cma_turnover_comparison", "turnover_rate"),
                         ("story4_cma_rent_growth_comparison", "rent_pct_change_2br")]:
        rows_v = fetch(cur, f"SELECT centre, metric FROM {SCHEMA}.{view}")
        checks.append(Check(a, f"{view}: 42 CMAs incl. Windsor CMA, metric {metric} only",
                            len(rows_v) == 42 and "Windsor CMA" in {r["centre"] for r in rows_v}
                            and {r["metric"] for r in rows_v} == {metric}, f"{len(rows_v)} rows"))

    # Independent ranks from clean.rental_market_canada (latest period per metric)
    latest_period = {"vacancy_rate": "Oct-25", "turnover_rate": "Oct-25", "average_rent_2br": "Oct-25",
                     "rent_pct_change_2br": "Oct-24 to Oct-25"}
    src = fetch(cur, "SELECT centre, metric, period_label, value FROM clean.rental_market_canada")
    expected = {}
    for metric, period in latest_period.items():
        vals = {r["centre"]: r["value"] for r in src if r["metric"] == metric and r["period_label"] == period}
        published = [v for v in vals.values() if v is not None]
        for centre, v in vals.items():
            rank = None if v is None else 1 + sum(1 for x in published if x > v)
            expected[(centre, metric)] = {"value": v, "period_label": period, "rank_highest_first": rank,
                                          "cmas_ranked": len(published)}
    actual = {(r["centre"], r["metric"]): r for r in ranking}
    checks.append(check_compare(a, "values and ranks equal independent recomputation from clean.rental_market_canada",
                                expected, actual, ["value", "period_label", "rank_highest_first", "cmas_ranked"]))

    position = {r["metric"]: r for r in fetch(cur, f"SELECT * FROM {SCHEMA}.story4_windsor_position")}
    bad = []
    for metric, period in latest_period.items():
        published = [r["value"] for r in src if r["metric"] == metric and r["period_label"] == period and r["value"] is not None]
        p = position.get(metric)
        w = expected[("Windsor CMA", metric)]
        if (p is None or p["windsor_value"] != w["value"] or p["windsor_rank_highest_first"] != w["rank_highest_first"]
                or p["cma_median_value"] != Decimal(str(statistics.median(published)))
                or p["cma_min_value"] != min(published) or p["cma_max_value"] != max(published)):
            bad.append(metric)
    checks.append(Check(a, "Windsor position (value, rank, median, min, max) reconciles", not bad and len(position) == 4,
                        ", ".join(f"{m}: rank {position[m]['windsor_rank_highest_first']}/{position[m]['cmas_ranked']}"
                                  for m in sorted(position)) + (f"; bad {bad}" if bad else "")))

    # Scope consistency: the national table's Windsor row is the apartment scope of Windsor's own RMS.
    pairs = [("vacancy_rate", "Table 1.1.1", "Total"), ("turnover_rate", "Table 1.1.6", "Total"),
             ("average_rent_2br", "Table 1.1.2", "2 Bedroom"), ("rent_pct_change_2br", "Table 1.1.5", "2 Bedroom")]
    bad = []
    for metric, table, bed in pairs:
        nat = {r["period_label"]: r["value"] for r in src if r["centre"] == "Windsor CMA" and r["metric"] == metric}
        loc = {r["period_label"]: r["value"] for r in fetch(cur, """
            SELECT period_label, value FROM clean.rental_market_windsor
            WHERE source_table = %s AND zone = 'Windsor CMA' AND bedroom_type = %s""", (table, bed))}
        if nat != loc:
            bad.append(f"{metric}: national {nat} vs {table} {loc}")
    checks.append(Check(a, "national-table Windsor row equals Windsor RMS apartment tables (same scope)", not bad,
                        "; ".join(bad) or "vacancy, turnover, 2BR rent and 2BR rent change match for all periods"))
    return checks


# ---------------------------------------------------------------------------

def run_checks(conn) -> list[Check]:
    with conn.cursor() as cur:
        checks = schema_checks(cur)
        if not all(c.passed for c in checks[:2]):
            conn.rollback()
            return checks
        checks += story1_checks(cur)
        checks += story2_checks(cur)
        checks += story3_checks(cur)
        checks += story4_checks(cur)
        # last: the PostgreSQL load validation ends the session's transaction
        checks += source_safety_checks(conn, cur)
    conn.rollback()  # read-only session
    return checks


def render(checks: list[Check], database: str) -> str:
    failed = [c for c in checks if not c.passed]
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"SQL ANALYTICS STATUS: {'FAIL' if failed else 'PASS'}",
        "",
        "# SQL Analysis Validation",
        "",
        f"Generated by `etl/validate_analysis_views.py` on {now}, querying the live database `{database}`.",
        f"**{len(checks) - len(failed)} of {len(checks)} checks passed.**",
        "",
        "Traceability checks recompute results in Python from plain `SELECT`s on `clean.*` and compare them with "
        "the views row by row. See [SQL_ANALYSIS_REPORT.md](SQL_ANALYSIS_REPORT.md) for the views and values.",
        "",
    ]
    if failed:
        lines += ["## Failed checks", "", "| Area | Check | Detail |", "|---|---|---|"]
        lines += [f"| {c.area} | {c.name} | {c.detail} |" for c in failed] + [""]
    lines += ["## All checks", "", "| Area | Check | Result | Detail |", "|---|---|---|---|"]
    for c in checks:
        lines.append(f"| {c.area} | {c.name} | {'PASS' if c.passed else '**FAIL**'} | {c.detail.replace('|', chr(92) + '|')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        REPORT_PATH.write_text(f"SQL ANALYTICS STATUS: FAIL\n\nCould not connect to PostgreSQL: {exc}\n", encoding="utf-8")
        print(f"SQL ANALYTICS STATUS: FAIL (cannot connect: {exc})")
        return 1
    try:
        checks = run_checks(conn)
        database = conn.get_dsn_parameters()["dbname"]
    finally:
        conn.close()
    REPORT_PATH.write_text(render(checks, database), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    for c in failed:
        print(f"FAIL  [{c.area}] {c.name} -- {c.detail}")
    print(f"SQL ANALYTICS STATUS: {'FAIL' if failed else 'PASS'} ({len(checks) - len(failed)}/{len(checks)} checks passed)")
    print(f"Report written: {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
