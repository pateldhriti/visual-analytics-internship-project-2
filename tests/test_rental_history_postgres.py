"""
Tests for the additive history extension in PostgreSQL
(sql/migrations/001_..., sql/analysis/05_..., etl/load_rental_history_to_postgres.py,
etl/validate_rental_history_postgres.py).

Static tests read the SQL files. Live tests query the running Docker PostgreSQL
and are skipped if it is unreachable or the history table is not loaded. They
never reload or commit: the tamper test runs inside a transaction that is
always rolled back.

    .venv\\Scripts\\python.exe -m pytest tests\\test_rental_history_postgres.py -v
"""

import psycopg2
import pytest

import load_rental_history_to_postgres as hload
import validate_rental_history_postgres as vhp
from load_cleaned_to_postgres import LoadError, connect


def code(path) -> str:
    return "\n".join(line.split("--")[0] for line in path.read_text(encoding="utf-8").splitlines()).upper()


class TestMigrationIsAdditive:
    def test_migration_never_drops_or_alters(self):
        sql = code(hload.MIGRATION_SQL)
        assert "DROP " not in sql and "ALTER " not in sql and "TRUNCATE" not in sql
        assert "CREATE TABLE IF NOT EXISTS CLEAN.RENTAL_MARKET_WINDSOR_HISTORY" in sql

    def test_history_views_are_create_or_replace_only(self):
        sql = code(hload.VIEWS_SQL)
        assert "DROP " not in sql and "CREATE SCHEMA" not in sql
        assert sql.count("CREATE OR REPLACE VIEW") == len(hload.HISTORY_VIEWS)
        assert sql.count("CREATE VIEW") == 0


@pytest.fixture(scope="module")
def conn():
    try:
        connection = connect()
    except (LoadError, psycopg2.OperationalError) as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('clean.rental_market_windsor_history') IS NOT NULL")
        loaded = cur.fetchone()[0]
    connection.rollback()
    if not loaded:
        connection.close()
        pytest.skip("history table not loaded (run etl/load_rental_history_to_postgres.py)")
    yield connection
    connection.rollback()
    connection.close()


class TestLiveHistory:
    def test_every_validation_check_passes(self, conn):
        checks, bench = vhp.run_checks(conn)
        failed = [f"[{c.area}] {c.name} -- {c.detail}" for c in checks if not c.passed]
        assert not failed, "\n".join(failed)
        assert str(bench[(2019, "average_rent")]) == "949.0" and str(bench[(2025, "average_rent")]) == "1454.0"

    def test_primary_index_blocks_a_second_primary_row(self, conn):
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute("UPDATE clean.rental_market_windsor_history SET is_primary_series = true "
                            "WHERE year = 2022 AND geography_basis = 'pre_2021_census'")
        conn.rollback()

    def test_validator_detects_tampering_and_nothing_is_committed(self, conn):
        with conn.cursor() as cur:
            cur.execute("UPDATE clean.rental_market_windsor_history SET value = value + 1 "
                        "WHERE year = 2021 AND metric = 'average_rent'")
            cur.execute("DELETE FROM clean.rental_market_windsor_history "
                        "WHERE year = 2022 AND geography_basis = 'pre_2021_census' AND metric = 'vacancy_rate'")
        checks, _ = vhp.run_checks(conn)  # sees uncommitted changes, then rolls back
        failed = {c.name for c in checks if not c.passed}
        assert "every staging row reconciles cell by cell (incl. lineage columns)" in failed
        assert "2022 keeps both geography bases; 2021_census row is primary" in failed
        assert "row count = staging row count (32)" in failed
        assert all(c.passed for c in vhp.run_checks(conn)[0])  # rolled back: intact
