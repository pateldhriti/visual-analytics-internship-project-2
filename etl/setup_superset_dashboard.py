"""
Connect Superset to the Postgres housing data and create one chart,
proving the Docker + Postgres + Superset stack works end-to-end.

Creates (if not already present):
- A database connection to the housing_windsor database (table
  windsor_shelter_cost_long)
- A dataset on windsor_shelter_cost_long
- One bar chart: households spending 30%+ of income on shelter costs,
  by tenure (Owner vs Renter) -- answers Story 1 Q1
  (see docs/story1_questions_and_measures.md)

Requires Superset running (docker compose up superset) and a .env file with
SUPERSET_ADMIN_USER/SUPERSET_ADMIN_PASSWORD/POSTGRES_* (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\setup_superset_dashboard.py
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPERSET_URL = "http://localhost:8088"

DATABASE_NAME = "Windsor Housing Data"
DATASET_TABLE = "windsor_shelter_cost_long"
CHART_NAME = "Households spending 30%+ on shelter costs, by tenure"

# Baseline filters -- see docs/shelter_cost_audit.md and
# docs/story1_questions_and_measures.md for why each is needed.
BASELINE_ADHOC_FILTERS = [
    {"clause": "WHERE", "subject": "housing_suitability", "operator": "==",
     "comparator": "Total - Housing suitability", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "dwelling_condition", "operator": "==",
     "comparator": "Total - Dwelling condition", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "statistic", "operator": "==",
     "comparator": "Number of private households", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "income_group", "operator": "==",
     "comparator": "Total - Total income of household", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "household_type", "operator": "==",
     "comparator": "Total - Household type including census family structure", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "shelter_cost_ratio", "operator": "==",
     "comparator": "Spending 30% or more of income on shelter costs", "expressionType": "SIMPLE"},
    {"clause": "WHERE", "subject": "tenure", "operator": "!=",
     "comparator": "Total", "expressionType": "SIMPLE"},
]


def get_session() -> tuple[requests.Session, dict]:
    load_dotenv(PROJECT_ROOT / ".env")
    session = requests.Session()

    login_resp = session.post(
        f"{SUPERSET_URL}/api/v1/security/login",
        json={
            "username": os.environ["SUPERSET_ADMIN_USER"],
            "password": os.environ["SUPERSET_ADMIN_PASSWORD"],
            "provider": "db",
            "refresh": True,
        },
    )
    login_resp.raise_for_status()
    access_token = login_resp.json()["access_token"]

    csrf_resp = session.get(
        f"{SUPERSET_URL}/api/v1/security/csrf_token/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    csrf_resp.raise_for_status()
    csrf_token = csrf_resp.json()["result"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-CSRFToken": csrf_token,
        "Referer": SUPERSET_URL,
    }
    return session, headers


def find_existing(session, headers, endpoint: str, name_field: str, name_value: str):
    resp = session.get(f"{SUPERSET_URL}/api/v1/{endpoint}/", headers=headers)
    resp.raise_for_status()
    for item in resp.json()["result"]:
        if item.get(name_field) == name_value:
            return item["id"]
    return None


def ensure_database(session, headers) -> int:
    existing = find_existing(session, headers, "database", "database_name", DATABASE_NAME)
    if existing:
        return existing

    uri = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@postgres:5432/{os.environ['POSTGRES_DB']}"
    )
    resp = session.post(
        f"{SUPERSET_URL}/api/v1/database/",
        headers=headers,
        json={"database_name": DATABASE_NAME, "sqlalchemy_uri": uri},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_dataset(session, headers, database_id: int) -> int:
    existing = find_existing(session, headers, "dataset", "table_name", DATASET_TABLE)
    if existing:
        return existing

    resp = session.post(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        json={"database": database_id, "table_name": DATASET_TABLE, "schema": "public"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_chart(session, headers, dataset_id: int) -> int:
    existing = find_existing(session, headers, "chart", "slice_name", CHART_NAME)
    if existing:
        return existing

    params = {
        "datasource": f"{dataset_id}__table",
        "viz_type": "dist_bar",
        "groupby": ["tenure"],
        "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(value)", "label": "Households"}],
        "adhoc_filters": BASELINE_ADHOC_FILTERS,
        "row_limit": 10,
    }
    resp = session.post(
        f"{SUPERSET_URL}/api/v1/chart/",
        headers=headers,
        json={
            "slice_name": CHART_NAME,
            "viz_type": "dist_bar",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": str(params).replace("'", '"'),
        },
    )
    resp.raise_for_status()
    return resp.json()["id"]


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    database_id = ensure_database(session, headers)
    print(f"Database connection ready: id={database_id}")

    dataset_id = ensure_dataset(session, headers, database_id)
    print(f"Dataset ready: id={dataset_id}")

    chart_id = ensure_chart(session, headers, dataset_id)
    print(f"Chart ready: id={chart_id}")
    print(f"View it at: {SUPERSET_URL}/explore/?slice_id={chart_id}")
