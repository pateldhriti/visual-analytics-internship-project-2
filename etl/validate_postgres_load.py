"""
Validate the `clean` schema in the LIVE PostgreSQL database against the five
staging CSVs, and write docs/POSTGRES_VALIDATION.md, whose first line is
exactly "POSTGRESQL LOAD STATUS: PASS" or "POSTGRESQL LOAD STATUS: FAIL".

    .venv\\Scripts\\python.exe etl\\validate_postgres_load.py

Exit code 0 = PASS, 1 = FAIL. Read-only: it only runs SELECT queries.
Reconciliation compares every cell of every table with its staging CSV.
"""

from __future__ import annotations

import datetime
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pandas as pd
import psycopg2

from cleaning_common import OUTPUT_FILES, PROJECT_ROOT, STAGING_DIR
from load_cleaned_to_postgres import SCHEMA, TABLES, LoadError, connect, read_staging
from validate_cleaned_data import EXPECTED, NATURAL_KEYS

REPORT_PATH = PROJECT_ROOT / "docs" / "POSTGRES_VALIDATION.md"

EXPECTED_ROWS = {
    "census_profile": 514,
    "shelter_cost": 2389,
    "rental_market_windsor": 2385,
    "starts_completions_windsor": 25,
    "rental_market_canada": 336,
}
# Columns that must be numeric in PostgreSQL; every other column must be text.
NUMERIC_COLUMNS = {
    "census_profile": ["census_year", "alt_geo_code", "tnr_sf", "tnr_lf", "data_quality_flag", "characteristic_id",
                       "characteristic_indent_level", "characteristic_note", "count_total", "count_men",
                       "count_women", "rate_total", "rate_men", "rate_women"],
    "shelter_cost": ["ref_year", "income_group_member_id", "household_type_member_id",
                     "housing_suitability_member_id", "dwelling_condition_member_id", "statistic_member_id",
                     "shelter_cost_ratio_member_id", "tenure_member_id", "value"],
    "rental_market_windsor": ["value"],
    "starts_completions_windsor": ["units"],
    "rental_market_canada": ["value"],
}
NUMERIC_TYPES = {"integer", "bigint", "smallint", "numeric"}
TEXT_TYPES = {"text", "character varying"}
PRIMARY_KEYS = {
    "census_profile": ["characteristic_id"],
    "shelter_cost": ["coordinate"],
    "rental_market_windsor": ["source_cell"],
    "starts_completions_windsor": ["source_cell"],
    "rental_market_canada": ["source_cell"],
}
WINDSOR_TABLES = ["census_profile", "shelter_cost", "rental_market_windsor", "starts_completions_windsor"]
# (value column, status column, statuses that carry a number)
VALUE_STATUS = {
    "census_profile": [(c, f"{c}_status", ("published", "use_with_caution", "revised"))
                       for c in ["count_total", "count_men", "count_women", "rate_total", "rate_men", "rate_women"]],
    "shelter_cost": [("value", "value_status", ("published", "use_with_caution", "revised"))],
    "rental_market_windsor": [("value", "value_status", ("published",))],
    "starts_completions_windsor": [("units", "value_flag", ("published", "nil_or_zero"))],
    "rental_market_canada": [("value", "value_status", ("published",))],
}


@dataclass
class Check:
    table: str
    name: str
    passed: bool
    detail: str


def scalar(cur, sql: str, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def table_types(cur, table: str) -> dict[str, str]:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position", (SCHEMA, table))
    return dict(cur.fetchall())


def cells_equal(csv_text: str, db_value, data_type: str) -> bool:
    if csv_text == "":
        return db_value is None
    if db_value is None:
        return False
    if data_type in NUMERIC_TYPES:
        return Decimal(csv_text) == Decimal(db_value)
    return csv_text == db_value


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def structure_checks(cur, csvs: dict[str, pd.DataFrame]) -> list[Check]:
    checks = []
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (SCHEMA,))
    present = {r[0] for r in cur.fetchall()}
    expected = set(TABLES.values())
    checks.append(Check(SCHEMA, "exactly the 5 expected base tables exist", present == expected,
                        f"present: {sorted(present)}" + (f"; missing: {sorted(expected - present)}" if expected - present else "")
                        + (f"; unexpected: {sorted(present - expected)}" if present - expected else "")))
    cur.execute("SELECT count(*) FROM information_schema.views WHERE table_schema = %s", (SCHEMA,))
    views = cur.fetchone()[0]
    checks.append(Check(SCHEMA, "no views in the schema (no analytical views yet)", views == 0, f"{views} views"))

    for key, table in TABLES.items():
        if table not in present:
            continue
        types = table_types(cur, table)
        csv_cols = list(csvs[key].columns)
        checks.append(Check(table, "columns match staging CSV header (names and order)", list(types) == csv_cols,
                            f"{len(types)} columns" if list(types) == csv_cols
                            else f"table: {list(types)} vs CSV: {csv_cols}"))
        bad_numeric = [f"{c}={types.get(c)}" for c in NUMERIC_COLUMNS[table] if types.get(c) not in NUMERIC_TYPES]
        checks.append(Check(table, "numeric columns are integer/numeric", not bad_numeric,
                            ", ".join(bad_numeric) or ", ".join(f"{c} ({types[c]})" for c in NUMERIC_COLUMNS[table])))
        bad_text = [f"{c}={t}" for c, t in types.items() if c not in NUMERIC_COLUMNS[table] and t not in TEXT_TYPES]
        checks.append(Check(table, "all other columns are text", not bad_text,
                            ", ".join(bad_text) or f"{len(types) - len(NUMERIC_COLUMNS[table])} text columns"))

        rows = scalar(cur, f"SELECT count(*) FROM {SCHEMA}.{table}")
        checks.append(Check(table, f"row count = {EXPECTED_ROWS[table]:,}", rows == EXPECTED_ROWS[table],
                            f"{rows:,} rows"))
        checks.append(Check(table, "row count = staging CSV row count", rows == len(csvs[key]),
                            f"table {rows:,}, CSV {len(csvs[key]):,}"))
    return checks


def quality_checks(cur, csvs: dict[str, pd.DataFrame]) -> list[Check]:
    checks = []
    for key, table in TABLES.items():
        keys = NATURAL_KEYS[key]
        dupes = scalar(cur, f"SELECT count(*) FROM (SELECT 1 FROM {SCHEMA}.{table} GROUP BY {', '.join(keys)} "
                            "HAVING count(*) > 1) d")
        checks.append(Check(table, f"no duplicate natural keys ({', '.join(keys)})", dupes == 0,
                            f"{dupes} duplicated keys"))

        csv = csvs[key]
        expected_nulls = {c: int((csv[c] == "").sum()) for c in csv.columns}
        select = ", ".join(f"count(*) - count({c})" for c in csv.columns)
        cur.execute(f"SELECT {select} FROM {SCHEMA}.{table}")
        actual_nulls = dict(zip(csv.columns, cur.fetchone()))
        diff = [f"{c}: table {actual_nulls[c]} vs CSV {n}" for c, n in expected_nulls.items() if actual_nulls[c] != n]
        nonzero = {c: n for c, n in actual_nulls.items() if n}
        checks.append(Check(table, "NULL count per column = empty fields in staging CSV", not diff,
                            "; ".join(diff) or (", ".join(f"{c} {n}" for c, n in nonzero.items()) or "no NULLs")))

        bad = 0
        for value_col, status_col, numbered in VALUE_STATUS[table]:
            bad += scalar(cur, f"SELECT count(*) FROM {SCHEMA}.{table} "
                               f"WHERE ({value_col} IS NULL) <> ({status_col} <> ALL(%s))", (list(numbered),))
        checks.append(Check(table, "NULL value <=> non-published status", bad == 0, f"{bad} inconsistent cells"))

    for table in WINDSOR_TABLES:
        cur.execute(f"SELECT DISTINCT geography FROM {SCHEMA}.{table}")
        geos = sorted(r[0] for r in cur.fetchall())
        checks.append(Check(table, "Windsor CMA only", geos == ["Windsor CMA"], f"geography values: {geos}"))
    for table in ["census_profile", "shelter_cost"]:
        cur.execute(f"SELECT DISTINCT dguid FROM {SCHEMA}.{table}")
        dguids = sorted(r[0] for r in cur.fetchall())
        checks.append(Check(table, "DGUID is Windsor CMA (2021S0503559)", dguids == ["2021S0503559"], f"{dguids}"))

    t = "rental_market_canada"
    windsor = scalar(cur, f"SELECT count(*) FROM {SCHEMA}.{t} WHERE centre = 'Windsor CMA'")
    checks.append(Check(t, "Windsor CMA present", windsor > 0, f"{windsor} Windsor CMA rows"))
    non_cma = scalar(cur, f"SELECT count(*) FROM {SCHEMA}.{t} WHERE centre !~ '\\mCMA\\M' OR geography_level <> 'cma'")
    centres = scalar(cur, f"SELECT count(DISTINCT centre) FROM {SCHEMA}.{t}")
    csv_centres = csvs["canada_rental_market"]["centre"].nunique()
    checks.append(Check(t, "CMA rows only", non_cma == 0 and centres == csv_centres,
                        f"{non_cma} non-CMA rows; {centres} centres (CSV {csv_centres})"))

    for table in ["rental_market_windsor", "rental_market_canada"]:
        cur.execute(f"SELECT count(*), count(*) FILTER (WHERE value IS NULL OR value <= 0) FROM {SCHEMA}.{table} "
                    "WHERE unit = 'dollars' AND value_status = 'published'")
        n, bad = cur.fetchone()
        checks.append(Check(table, "published rents > 0", bad == 0 and n > 0, f"{n} published rents, {bad} not > 0"))
        cur.execute(f"""SELECT count(*),
                               count(*) FILTER (WHERE metric LIKE '%pct_change' AND value NOT BETWEEN -100 AND 100),
                               count(*) FILTER (WHERE metric NOT LIKE '%pct_change' AND value NOT BETWEEN 0 AND 100)
                        FROM {SCHEMA}.{table} WHERE unit = 'percent' AND value IS NOT NULL""")
        n, bad_change, bad_rate = cur.fetchone()
        checks.append(Check(table, "rates within 0-100, % changes within -100 to 100", bad_change + bad_rate == 0,
                            f"{n} percent values; {bad_rate} rates and {bad_change} changes out of range"))
    t = "starts_completions_windsor"
    cur.execute(f"SELECT count(*), count(*) FILTER (WHERE units < 0) FROM {SCHEMA}.{t}")
    n, bad = cur.fetchone()
    checks.append(Check(t, "units >= 0", bad == 0, f"{n} rows, {bad} negative"))
    return checks


def reconciliation_checks(cur, csvs: dict[str, pd.DataFrame]) -> list[Check]:
    checks = []
    for key, table in TABLES.items():
        csv = csvs[key]
        types = table_types(cur, table)
        pk = PRIMARY_KEYS[table]
        cur.execute(f"SELECT {', '.join(csv.columns)} FROM {SCHEMA}.{table}")
        db = {tuple(str(r[csv.columns.get_loc(c)]) for c in pk): r for r in cur.fetchall()}
        mismatches, examples = 0, []
        for record in csv.itertuples(index=False):
            k = tuple(str(Decimal(record[csv.columns.get_loc(c)])) if types[c] in NUMERIC_TYPES
                      else record[csv.columns.get_loc(c)] for c in pk)
            row = db.pop(k, None)
            if row is None:
                mismatches += 1
                examples.append(f"{k} missing from table")
                continue
            for col, text, value in zip(csv.columns, record, row):
                if not cells_equal(text, value, types[col]):
                    mismatches += 1
                    if len(examples) < 5:
                        examples.append(f"{k} {col}: CSV {text!r} vs table {value!r}")
        mismatches += len(db)
        examples += [f"{k} not in CSV" for k in list(db)[:5]]
        cells = csv.shape[0] * csv.shape[1]
        checks.append(Check(table, "every cell equals staging CSV", mismatches == 0,
                            f"{cells:,} cells compared, {mismatches} mismatches" + (f": {'; '.join(examples[:5])}" if examples else "")))

    pop = scalar(cur, f"SELECT count_total FROM {SCHEMA}.census_profile WHERE characteristic_id = 1")
    checks.append(Check("census_profile", f"population 2021 = {EXPECTED['census_population_2021']:,}",
                        pop == EXPECTED["census_population_2021"], f"{pop}"))
    for tenure, expected in [("Owner", EXPECTED["shelter_owner_30_plus"]), ("Renter", EXPECTED["shelter_renter_30_plus"])]:
        cur.execute(f"""SELECT value FROM {SCHEMA}.shelter_cost
                        WHERE income_group = 'Total - Total income of household'
                          AND household_type = 'Total - Household type including census family structure'
                          AND shelter_cost_ratio = %s
                          AND tenure = %s""", ("Spending 30% or more of income on shelter costs", tenure))
        values = [r[0] for r in cur.fetchall()]
        checks.append(Check("shelter_cost", f"{tenure} 30%+ = {expected:,}", values == [expected], f"{values}"))

    cur.execute(f"""SELECT source_table, activity,
                           sum(units) FILTER (WHERE dwelling_type <> 'Total'),
                           sum(units) FILTER (WHERE dwelling_type = 'Total'),
                           count(*) FILTER (WHERE dwelling_type <> 'Total')
                    FROM {SCHEMA}.starts_completions_windsor GROUP BY 1, 2 ORDER BY 1, 2""")
    for source_table, activity, parts, total, n_parts in cur.fetchall():
        checks.append(Check("starts_completions_windsor", f"{source_table} {activity}: components sum to Total",
                            parts == total and n_parts == 4, f"{n_parts} components sum {parts}, Total {total}"))
    return checks


def run_checks(conn, staging_dir: Path = STAGING_DIR) -> list[Check]:
    csvs = {key: read_staging(staging_dir / OUTPUT_FILES[key]) for key in TABLES}
    with conn.cursor() as cur:
        checks = structure_checks(cur, csvs)
        if not all(c.passed for c in checks if c.name == "exactly the 5 expected base tables exist"):
            return checks
        checks += quality_checks(cur, csvs)
        checks += reconciliation_checks(cur, csvs)
    conn.rollback()  # read-only session; end the implicit transaction
    return checks


def render(checks: list[Check], database: str) -> str:
    failed = [c for c in checks if not c.passed]
    status = "FAIL" if failed else "PASS"
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"POSTGRESQL LOAD STATUS: {status}",
        "",
        "# PostgreSQL Load Validation",
        "",
        f"Generated by `etl/validate_postgres_load.py` on {now}, querying the live database `{database}`, "
        f"schema `{SCHEMA}`.",
        f"**{len(checks) - len(failed)} of {len(checks)} checks passed.**",
        "",
    ]
    if failed:
        lines += ["## Failed checks", "", "| Table | Check | Detail |", "|---|---|---|"]
        lines += [f"| `{c.table}` | {c.name} | {c.detail} |" for c in failed]
        lines.append("")
    lines += ["## All checks", "", "| Table | Check | Result | Detail |", "|---|---|---|---|"]
    for c in checks:
        detail = c.detail.replace("|", "\\|")
        lines.append(f"| `{c.table}` | {c.name} | {'PASS' if c.passed else '**FAIL**'} | {detail} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        conn = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        REPORT_PATH.write_text(f"POSTGRESQL LOAD STATUS: FAIL\n\nCould not connect to PostgreSQL: {exc}\n",
                               encoding="utf-8")
        print(f"POSTGRESQL LOAD STATUS: FAIL (cannot connect: {exc})")
        return 1
    try:
        checks = run_checks(conn)
        database = conn.get_dsn_parameters()["dbname"]
    finally:
        conn.close()
    REPORT_PATH.write_text(render(checks, database), encoding="utf-8")
    failed = [c for c in checks if not c.passed]
    for c in failed:
        print(f"FAIL  {c.table}: {c.name} -- {c.detail}")
    print(f"POSTGRESQL LOAD STATUS: {'FAIL' if failed else 'PASS'} ({len(checks) - len(failed)}/{len(checks)} checks passed)")
    print(f"Report written: {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
