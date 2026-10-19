"""
Tests for the staging -> PostgreSQL load (etl/load_cleaned_to_postgres.py,
etl/validate_postgres_load.py, sql/clean_schema.sql).

Unit tests need no database. Live tests query the running Docker PostgreSQL
(.env) and are skipped if it is unreachable or the `clean` schema has not been
loaded. They never reload or commit: the tamper test changes rows inside a
transaction that is always rolled back.

    .venv\\Scripts\\python.exe -m pytest tests\\test_postgres_load.py -v
"""

import re

import pandas as pd
import psycopg2
import pytest

import load_cleaned_to_postgres as loader
import validate_postgres_load as vpl
from cleaning_common import OUTPUT_FILES


# ---------------------------------------------------------------------------
# Unit tests: conversion and header checks
# ---------------------------------------------------------------------------

class TestConvertCell:
    def test_empty_is_null(self):
        assert loader.convert_cell("", "numeric", "x") is None
        assert loader.convert_cell("", "text", "x") is None

    def test_integer_written_as_float_is_accepted(self):
        assert loader.convert_cell("83.0", "integer", "x") == "83"
        assert loader.convert_cell("2021", "integer", "x") == "2021"

    def test_fractional_value_rejected_for_integer_column(self):
        with pytest.raises(loader.LoadError, match="not a whole number"):
            loader.convert_cell("1.5", "integer", "x")

    def test_numeric_text_kept_exactly(self):
        assert loader.convert_cell("4.3", "numeric", "x") == "4.3"
        assert loader.convert_cell("-36000.0", "numeric", "x") == "-36000.0"

    def test_non_number_rejected_for_numeric_column(self):
        with pytest.raises(loader.LoadError, match="not a number"):
            loader.convert_cell("**", "numeric", "x")


class TestHeaderCheck:
    COLUMNS = {"id": "integer", "label": "text", "value": "numeric"}

    def test_missing_column_fails_clearly(self):
        df = pd.DataFrame({"id": ["1"], "label": ["a"]})
        with pytest.raises(loader.LoadError, match=r"Missing from CSV: \['value'\]"):
            loader.prepare_rows(df, self.COLUMNS, "demo.csv")

    def test_unexpected_column_fails_clearly(self):
        df = pd.DataFrame({"id": ["1"], "label": ["a"], "value": ["2"], "extra": ["z"]})
        with pytest.raises(loader.LoadError, match=r"Not in table: \['extra'\]"):
            loader.prepare_rows(df, self.COLUMNS, "demo.csv")

    def test_rows_follow_table_column_order(self):
        df = pd.DataFrame({"value": ["", "2.5"], "label": ["a", "b"], "id": ["1.0", "2"]})
        assert loader.prepare_rows(df, self.COLUMNS, "demo.csv") == [["1", "a", None], ["2", "b", "2.5"]]


def schema_columns() -> dict[str, list[str]]:
    """Column names per table, parsed from sql/clean_schema.sql."""
    sql = loader.SCHEMA_SQL.read_text(encoding="utf-8")
    tables = {}
    for name, body in re.findall(r"CREATE TABLE clean\.(\w+) \((.*?)\n\);", sql, flags=re.S):
        tables[name] = re.findall(r"^\s{4}(\w+)\s+(?:INTEGER|NUMERIC|TEXT)\b", body, flags=re.M)
    return tables


class TestSchemaFile:
    def test_defines_exactly_the_five_tables(self):
        assert set(schema_columns()) == set(loader.TABLES.values())

    def test_columns_match_pipeline_output_headers(self, cleaned_dir):
        tables = schema_columns()
        for key, table in loader.TABLES.items():
            header = list(pd.read_csv(cleaned_dir / OUTPUT_FILES[key], nrows=0).columns)
            assert tables[table] == header, table

    def test_no_views_and_no_cascade(self):
        sql = loader.SCHEMA_SQL.read_text(encoding="utf-8")
        code = "\n".join(line.split("--")[0] for line in sql.splitlines())
        assert "CREATE VIEW" not in code.upper() and "CASCADE" not in code.upper()


# ---------------------------------------------------------------------------
# Live database tests (read-only)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conn():
    try:
        connection = loader.connect()
    except (loader.LoadError, psycopg2.OperationalError) as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'clean'")
        loaded = cur.fetchone()[0]
    connection.rollback()
    if not loaded:
        connection.close()
        pytest.skip("schema 'clean' not loaded (run etl/load_cleaned_to_postgres.py)")
    yield connection
    connection.rollback()
    connection.close()


class TestLiveDatabase:
    def test_every_validation_check_passes(self, conn):
        checks = vpl.run_checks(conn)
        failed = [f"{c.table}: {c.name} -- {c.detail}" for c in checks if not c.passed]
        assert not failed, "\n".join(failed)

    def test_validator_detects_tampering_and_nothing_is_committed(self, conn):
        with conn.cursor() as cur:
            cur.execute("UPDATE clean.rental_market_windsor SET value = value + 1 "
                        "WHERE source_cell = (SELECT min(source_cell) FROM clean.rental_market_windsor "
                        "WHERE value_status = 'published' AND unit = 'dollars')")
            cur.execute("UPDATE clean.shelter_cost SET value = value + 1 WHERE tenure = 'Owner' "
                        "AND income_group = 'Total - Total income of household' "
                        "AND household_type = 'Total - Household type including census family structure' "
                        "AND shelter_cost_ratio = %s", ("Spending 30% or more of income on shelter costs",))
            cur.execute("DELETE FROM clean.starts_completions_windsor "
                        "WHERE source_table = 'Table A4_1' AND activity = 'Starts' AND dwelling_type = 'Singles'")
        checks = vpl.run_checks(conn)  # sees the uncommitted changes, then rolls them back
        failed = {(c.table, c.name) for c in checks if not c.passed}
        assert ("rental_market_windsor", "every cell equals staging CSV") in failed
        assert ("shelter_cost", "Owner 30%+ = 13,005") in failed
        assert ("starts_completions_windsor", "row count = 25") in failed
        assert ("starts_completions_windsor", "Table A4_1 Starts: components sum to Total") in failed
        # rolled back: the live data is intact
        assert all(c.passed for c in vpl.run_checks(conn))
