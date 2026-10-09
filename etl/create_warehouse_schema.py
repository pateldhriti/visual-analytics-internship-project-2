"""
Create and seed the conceptual warehouse schema (sql/warehouse_schema.sql,
sql/warehouse_seed_dimensions.sql) in Postgres, and verify it.

Safe to re-run: drops the warehouse schema first if it exists.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\create_warehouse_schema.py
"""

from pathlib import Path

from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = PROJECT_ROOT / "sql" / "warehouse_schema.sql"
SEED_SQL = PROJECT_ROOT / "sql" / "warehouse_seed_dimensions.sql"


def run_sql_file(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.execute(text(sql))


if __name__ == "__main__":
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS warehouse CASCADE"))
        run_sql_file(conn, SCHEMA_SQL)
        run_sql_file(conn, SEED_SQL)
    print("Schema created and seeded.")

    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'warehouse' ORDER BY table_name"
        )).fetchall()
        print(f"\n{len(tables)} tables in schema 'warehouse':")
        for (table_name,) in tables:
            count = conn.execute(text(f'SELECT COUNT(*) FROM warehouse."{table_name}"')).scalar()
            print(f"  {table_name}: {count} rows")
