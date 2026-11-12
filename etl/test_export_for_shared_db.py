"""Tests for etl/export_for_shared_db.py (no database needed).

Run: .venv\Scripts\python.exe -m pytest etl\test_export_for_shared_db.py
"""

import pytest

import export_for_shared_db as ex


def test_the_story1_table_moves_into_warehouse():
    sql = "CREATE TABLE public.windsor_shelter_cost_long (a int);\nCOPY public.windsor_shelter_cost_long (a) FROM stdin;\n"
    moved = ex.move_to_warehouse(sql)
    assert "public." not in moved
    assert moved.count("warehouse.windsor_shelter_cost_long") == 2


def test_a_dump_without_the_table_is_rejected():
    with pytest.raises(ValueError):
        ex.move_to_warehouse("CREATE TABLE public.something_else (a int);")


def test_the_package_replaces_only_our_schema_and_lets_superset_read_it(monkeypatch):
    monkeypatch.setattr(ex, "pg_dump", lambda *args: "-- dump\nCREATE TABLE public.windsor_shelter_cost_long (a int);\n")
    sql = ex.build()
    assert sql.index("DROP SCHEMA IF EXISTS warehouse CASCADE") < sql.index("-- dump")
    assert "DROP SCHEMA" not in sql.replace("DROP SCHEMA IF EXISTS warehouse CASCADE", "")
    assert sql.rstrip().endswith("GRANT SELECT ON ALL TABLES IN SCHEMA warehouse TO PUBLIC;")
