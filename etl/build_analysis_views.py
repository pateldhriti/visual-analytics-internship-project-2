"""
Build the `analysis` schema (analytical views over clean.*) from sql/analysis/.

    .venv\\Scripts\\python.exe etl\\build_analysis_views.py

Runs every sql/analysis/*.sql file in file-name order (00_, 01_, ...) inside
ONE transaction: an SQL error rolls everything back, names the failing file,
and leaves the database as it was. 00_analysis_schema.sql drops and recreates
the schema, so re-running is safe and never leaves stale views.

Refuses to run if the `analysis` schema holds anything other than views (it
must never contain tables), or if POSTGRES_DB is the Superset metadata
database. Never writes to clean.* -- the views only read it.

Afterwards writes docs/SQL_ANALYSIS_REPORT.md from live query results.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import psycopg2

from cleaning_common import PROJECT_ROOT
from load_cleaned_to_postgres import LoadError, connect

SQL_DIR = PROJECT_ROOT / "sql" / "analysis"
REPORT_PATH = PROJECT_ROOT / "docs" / "SQL_ANALYSIS_REPORT.md"
SCHEMA = "analysis"


class BuildError(RuntimeError):
    pass


def sql_files(sql_dir: Path = SQL_DIR) -> list[Path]:
    files = sorted(sql_dir.glob("*.sql"))
    if not files or files[0].name != "00_analysis_schema.sql":
        raise BuildError(f"{sql_dir} must contain 00_analysis_schema.sql as its first file")
    return files


def non_view_objects(cur) -> list[str]:
    """Anything in the analysis schema that is not a plain view (tables, matviews, sequences...)."""
    cur.execute("""
        SELECT c.relname || ' (' || c.relkind::text || ')'
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind <> 'v'
        ORDER BY 1""", (SCHEMA,))
    return [r[0] for r in cur.fetchall()]


def build(conn, sql_dir: Path = SQL_DIR) -> list[str]:
    files = sql_files(sql_dir)
    with conn:  # one transaction: commit on success, roll back on any error
        with conn.cursor() as cur:
            blocking = non_view_objects(cur)
            if blocking:
                raise BuildError(f"schema '{SCHEMA}' contains non-view objects, refusing to drop it: {blocking}")
            for path in files:
                try:
                    cur.execute(path.read_text(encoding="utf-8"))
                except psycopg2.Error as exc:
                    raise BuildError(f"{path.relative_to(PROJECT_ROOT).as_posix()}: {exc.pgerror or exc}") from exc
                print(f"executed {path.relative_to(PROJECT_ROOT).as_posix()} - build_analysis_views.py:67")
            cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = %s ORDER BY 1", (SCHEMA,))
            views = [r[0] for r in cur.fetchall()]
            blocking = non_view_objects(cur)
            if blocking:
                raise BuildError(f"sql/analysis created non-view objects: {blocking}")
    return views


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def rows(cur, sql: str) -> list[tuple]:
    cur.execute(sql)
    return cur.fetchall()


def table(header: list[str], data: list[tuple]) -> list[str]:
    def fmt(v):
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "yes" if v else "no"
        return f"{v:,}" if isinstance(v, int) else str(v)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(fmt(v).replace("|", "\\|") for v in r) + " |" for r in data]
    return lines


KEY_VALUE_QUERIES = [
    ("Story 1 — 30%+ shelter-cost burden by tenure",
     ["Tenure", "30%+ households", "Applicable households", "Burden %", "Census published %"],
     """SELECT t.tenure, t.numerator_burden_30_plus_households::int, t.denominator_applicable_households::int,
               t.burden_30_plus_pct, c.census_published_pct
        FROM analysis.story1_affordability_by_tenure t
        JOIN analysis.story1_burden_vs_census_published c USING (tenure) ORDER BY t.tenure_member_id"""),
    ("Story 1 — renter vs owner gap",
     ["Owner %", "Renter %", "Gap (pct points)", "Renter / owner ratio"],
     """SELECT owner_burden_30_plus_pct, renter_burden_30_plus_pct, renter_minus_owner_pct_points,
               renter_to_owner_rate_ratio FROM analysis.story1_tenure_burden_gap"""),
    ("Story 1 — burden severity (all tenures)",
     ["Tenure", "Category", "Source", "Households", "Share of applicable %"],
     """SELECT tenure, severity_category, category_source, households::int, share_of_applicable_households_pct
        FROM analysis.story1_burden_severity_by_tenure ORDER BY tenure_member_id, severity_order"""),
    ("Story 1 — burden by income band (renters)",
     ["Income band", "30%+ households", "Applicable", "Burden %", "Not-applicable basis"],
     """SELECT income_group, numerator_burden_30_plus_households::int, denominator_applicable_households::int,
               burden_30_plus_pct, not_applicable_basis
        FROM analysis.story1_affordability_by_income_group WHERE tenure = 'Renter' ORDER BY income_group_order"""),
    ("Story 2 — latest Windsor CMA rental KPIs (bedroom Total)",
     ["Scope", "Metric", "Oct-24", "Oct-25", "Change", "Change unit", "CMHC trend", "Reliability (Oct-25)"],
     """SELECT dwelling_scope, metric, previous_value, latest_value, change_value, change_unit, yoy_trend,
               latest_reliability_code
        FROM analysis.story2_latest_cma_kpis ORDER BY dwelling_scope, metric"""),
    ("Story 2 — CMHC same-sample rent change, Windsor CMA (bedroom Total)",
     ["Scope", "Period", "% change", "Status", "Reliability"],
     """SELECT dwelling_scope, change_period_label, rent_change_pct, value_status, reliability_code
        FROM analysis.story2_same_sample_rent_change WHERE zone = 'Windsor CMA' AND bedroom_type = 'Total'
        ORDER BY dwelling_scope, change_period_label"""),
    ("Story 3 — Windsor CMA housing supply by dwelling type",
     ["Activity", "Period", "Singles", "Semis", "Row", "Apt. and other", "Published Total", "Components reconcile"],
     """SELECT activity, period_label,
               max(units) FILTER (WHERE dwelling_type = 'Singles'), max(units) FILTER (WHERE dwelling_type = 'Semis'),
               max(units) FILTER (WHERE dwelling_type = 'Row'), max(units) FILTER (WHERE dwelling_type = 'Apt. and Other'),
               max(published_total_units), bool_and(total_reconciles)
        FROM analysis.story3_supply_by_dwelling_type GROUP BY activity, period_label, period_type
        ORDER BY period_type, activity"""),
    ("Story 4 — Windsor CMA position among CMAs (apartment, latest period)",
     ["Metric", "Period", "Windsor", "Rank (1 = highest)", "CMAs ranked", "CMA median", "Min", "Max"],
     """SELECT metric, period_label, windsor_value, windsor_rank_highest_first, cmas_ranked, cma_median_value,
               cma_min_value, cma_max_value FROM analysis.story4_windsor_position ORDER BY metric"""),
]

LIMITATIONS = [
    "Story 1 is a single Census year (2021). The source extract only holds the Total housing-suitability / "
    "Total dwelling-condition slice, and 971 of the 3,360 possible combinations are absent; absent rows are not "
    "created. StatCan rounds counts to multiples of 5, so components can differ slightly from totals.",
    "Story 1: for income bands of $10,000 and over, the missing 'Not applicable' count is taken as 0 by "
    "definition (Not applicable = household income ≤ 0) and flagged `zero_by_definition`. Elsewhere a missing "
    "'Not applicable' row gives a NULL rate (`rate_null_reason`), e.g. owner/renter rows of household types "
    "7–13.",
    "Story 1: in 4 very small 'Under $10,000' cells, random rounding makes the 30%+ count exceed the applicable "
    "households; the rate is left NULL (`numerator_exceeds_denominator_rounding`), never capped, with numerator "
    "and denominator still shown.",
    "Story 1: '100% or more' is derived (30%+ minus 30% to <100%), not a published category.",
    "Story 2 covers only the two survey periods in the workbook (Oct-24, Oct-25) and the two CMHC rent-change "
    "periods. Many cells are suppressed by CMHC (`**`), especially for row/townhouse and small zones; those stay "
    "NULL and are excluded from every calculation, so some comparisons are unavailable.",
    "Story 2: `change_value` for average rent compares two published averages from different samples; CMHC's "
    "same-sample rent change (`story2_same_sample_rent_change`) is the like-for-like measure.",
    "Story 3 is one monthly edition (August 2026, plus January–August 2026 year to date and under-construction "
    "stock at month end). No trend, no annualisation, no Ontario/Canada values.",
    "Story 4 is apartment-only (CMHC Table 1.0) and compares Windsor only with the national table's own Windsor "
    "row, never with Windsor `row_and_apartment` figures. Ottawa-Gatineau appears as two parts (Ont. / Qué.), "
    "each ranked as listed in the source. Rent growth has suppressed / not-significant values (NULL) for some "
    "CMAs, so fewer CMAs are ranked for that metric. No comparator subset is selected.",
    "No affordability-gap index is computed: renter-income growth data is not in the validated sources.",
    "Views are descriptive. They do not support causal conclusions.",
]


def render_report(conn, views: list[str]) -> str:
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    with conn.cursor() as cur:
        meta = rows(cur, f"""
            SELECT c.relname, obj_description(c.oid, 'pg_class'),
                   (SELECT count(*) FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped)
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = '{SCHEMA}' AND c.relkind = 'v' ORDER BY c.relname""")
        counts = {name: rows(cur, f"SELECT count(*) FROM {SCHEMA}.{name}")[0][0] for name, _, _ in meta}
        lines = [
            "# SQL Analysis Report",
            "",
            f"Generated by `etl/build_analysis_views.py` on {now} from `sql/analysis/`, against the live "
            f"database `{conn.get_dsn_parameters()['dbname']}`.",
            "Validation results are in [SQL_ANALYSIS_VALIDATION.md](SQL_ANALYSIS_VALIDATION.md).",
            "",
            "Every view reads only `clean.*`. The old `sql/warehouse_*.sql` and `sql/story*_views.sql` were not used. "
            "Plain views only: no tables, no materialized views, no Superset objects.",
            "",
            "## Views",
            "",
        ]
        lines += table(["View", "Rows", "Columns", "Grain and purpose"],
                       [(f"`{SCHEMA}.{name}`", counts[name], ncols, comment or "") for name, comment, ncols in meta])
        lines += ["", "## Important calculated values", ""]
        for title, header, sql in KEY_VALUE_QUERIES:
            lines += [f"### {title}", ""] + table(header, rows(cur, sql)) + [""]
    conn.rollback()
    lines += ["## Limitations", ""] + [f"- {item}" for item in LIMITATIONS]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        print(f"Cannot connect to PostgreSQL: {exc} - build_analysis_views.py:205")
        return 1
    try:
        print(f"Building schema '{SCHEMA}' from {SQL_DIR.relative_to(PROJECT_ROOT).as_posix()}/ - build_analysis_views.py:208")
        views = build(conn)
        print(f"Committed: {len(views)} views in '{SCHEMA}' - build_analysis_views.py:210")
        for name in views:
            print(f"{SCHEMA}.{name} - build_analysis_views.py:212")
        REPORT_PATH.write_text(render_report(conn, views), encoding="utf-8")
        print(f"Report written: {REPORT_PATH} - build_analysis_views.py:214")
    except (BuildError, psycopg2.Error) as exc:
        print(f"BUILD FAILED (rolled back, database unchanged): {exc} - build_analysis_views.py:216")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
