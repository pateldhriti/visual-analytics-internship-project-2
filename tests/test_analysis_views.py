"""
Tests for the analytical views (sql/analysis/, etl/build_analysis_views.py,
etl/validate_analysis_views.py).

Static tests read the SQL files only. Live tests query the running Docker
PostgreSQL (.env) and are skipped if it is unreachable or the `analysis`
schema has not been built. They never rebuild or commit: the tamper test
changes clean.* inside a transaction that is always rolled back.

    .venv\\Scripts\\python.exe -m pytest tests\\test_analysis_views.py -v
"""

import re

import psycopg2
import pytest

import build_analysis_views as build
import validate_analysis_views as vav
from load_cleaned_to_postgres import LoadError, connect


def sql_code(path) -> str:
    """SQL text without -- comments and with string literals blanked."""
    code = "\n".join(line.split("--")[0] for line in path.read_text(encoding="utf-8").splitlines())
    return re.sub(r"'(?:[^']|'')*'", "''", code)


ALL_SQL = {p.name: sql_code(p) for p in build.sql_files()}


# ---------------------------------------------------------------------------
# Static checks on sql/analysis/
# ---------------------------------------------------------------------------

class TestSqlFiles:
    def test_files_run_in_story_order(self):
        assert list(ALL_SQL) == ["00_analysis_schema.sql", "01_story1_affordability.sql",
                                 "02_story2_rental_market.sql", "03_story3_housing_supply.sql",
                                 "04_story4_cma_comparison.sql"]

    def test_declared_views_match_validator_list(self):
        declared = set()
        for code in ALL_SQL.values():
            declared |= set(re.findall(r"CREATE VIEW analysis\.(\w+)", code))
        assert declared == vav.EXPECTED_VIEWS

    def test_every_view_has_a_comment(self):
        for name, code in ALL_SQL.items():
            views = set(re.findall(r"CREATE VIEW analysis\.(\w+)", code))
            commented = set(re.findall(r"COMMENT ON VIEW analysis\.(\w+)", code))
            assert views == commented, name

    def test_only_plain_views_no_tables(self):
        for name, code in ALL_SQL.items():
            upper = code.upper()
            assert "CREATE TABLE" not in upper and "MATERIALIZED" not in upper, name
            assert "INSERT " not in upper and "UPDATE " not in upper and "DELETE " not in upper, name

    def test_reads_only_clean_and_analysis(self):
        for name, code in ALL_SQL.items():
            schemas = set(re.findall(r"(?<!DISTINCT )\b(?:FROM|JOIN)\s+(\w+)\.", code, flags=re.I))
            assert schemas <= {"clean", "analysis"}, (name, schemas)
            assert "warehouse" not in code.lower(), name

    def test_every_division_is_protected_with_nullif(self):
        for name, code in ALL_SQL.items():
            unprotected = re.findall(r"/\s*(?!NULLIF\()\S+", code)
            assert not unprotected, (name, unprotected)

    def test_null_is_never_replaced_with_zero(self):
        for name, code in ALL_SQL.items():
            assert "COALESCE" not in code.upper(), name


# ---------------------------------------------------------------------------
# Live database tests (read-only)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conn():
    try:
        connection = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.views WHERE table_schema = 'analysis'")
        built = cur.fetchone()[0]
    connection.rollback()
    if not built:
        connection.close()
        pytest.skip("schema 'analysis' not built (run etl/build_analysis_views.py)")
    yield connection
    connection.rollback()
    connection.close()


class TestLiveAnalysis:
    def test_every_validation_check_passes(self, conn):
        checks = vav.run_checks(conn)
        failed = [f"[{c.area}] {c.name} -- {c.detail}" for c in checks if not c.passed]
        assert not failed, "\n".join(failed)

    def test_burden_rates_from_view(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT tenure, round(burden_30_plus_pct, 1) FROM analysis.story1_affordability_by_tenure")
            rates = dict(cur.fetchall())
        conn.rollback()
        assert str(rates["Owner"]) == "10.9" and str(rates["Renter"]) == "34.8"

    def test_validator_detects_tampered_source_and_nothing_is_committed(self, conn):
        with conn.cursor() as cur:
            cur.execute("UPDATE clean.shelter_cost SET value = value + 100 WHERE tenure = 'Renter' "
                        "AND income_group = 'Total - Total income of household' "
                        "AND household_type = 'Total - Household type including census family structure' "
                        "AND shelter_cost_ratio = %s", ("Spending 30% or more of income on shelter costs",))
            cur.execute("UPDATE clean.starts_completions_windsor SET units = units + 1 "
                        "WHERE source_table = 'Table A4_1' AND activity = 'Starts' AND dwelling_type = 'Row'")
        checks = vav.run_checks(conn)  # sees the uncommitted changes, then rolls them back
        failed = {c.name for c in checks if not c.passed}
        assert "Renter 30%+ numerator = 15,735" in failed
        assert "calculated burden equals Census Profile published rate (1 dp)" in failed
        assert "components reconcile with published Total (recomputed from clean.*)" in failed
        assert "clean.* still equals data/staging/ cell by cell (PostgreSQL load checks)" in failed
        assert all(c.passed for c in vav.run_checks(conn))  # rolled back: live data intact

    def test_non_view_object_in_analysis_blocks_rebuild(self, conn):
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE analysis.should_not_exist (x int)")
            assert build.non_view_objects(cur) == ["should_not_exist (r)"]
        conn.rollback()
        with conn.cursor() as cur:
            assert build.non_view_objects(cur) == []
        conn.rollback()
