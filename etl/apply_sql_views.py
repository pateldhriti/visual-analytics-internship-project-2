"""
Apply every story's SQL view file (sql/story1_views.sql through
story4_views.sql) against the warehouse schema.

Fills a real gap etl/README.md's own "Views and Superset" section
flagged honestly: "there's no dedicated apply script yet -- run each
file through any Postgres client." Every view is CREATE OR REPLACE, so
this is naturally idempotent -- safe to run as many times as needed,
same as every other step in the load pipeline.

Requires a running Postgres instance (see docker/docker-compose.yml)
with the warehouse schema already created (etl/create_warehouse_schema.py)
and a .env file with POSTGRES_HOST/PORT/DB/USER/PASSWORD
(see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\apply_sql_views.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
VIEW_FILES = [
    SQL_DIR / "story1_views.sql",
    SQL_DIR / "story2_views.sql",
    SQL_DIR / "story3_views.sql",
    SQL_DIR / "story4_views.sql",
    SQL_DIR / "dashboard1_views.sql",
]


def get_engine():
    load_dotenv(PROJECT_ROOT / ".env")
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    db = os.environ["POSTGRES_DB"]
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def apply_file(engine, sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL view file not found: {sql_path}")
    sql = sql_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))


def run() -> list[str]:
    engine = get_engine()
    applied = []
    for sql_path in VIEW_FILES:
        apply_file(engine, sql_path)
        applied.append(sql_path.name)
    return applied


if __name__ == "__main__":
    applied = run()
    print(f"Applied {len(applied)} view files:")
    for name in applied:
        print(f"  {name}")
