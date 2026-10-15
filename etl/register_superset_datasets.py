"""
Register every Story 4 SQL view (sql/story4_views.sql) as a Superset
dataset, each with saved metrics -- so chart-builders pick a named metric
from a dropdown instead of retyping ad-hoc SQL per chart, which is how
etl/setup_superset_dashboard.py's single chart currently works.

Reuses the Database connection and auth helpers from
etl/setup_superset_dashboard.py rather than duplicating them -- same
Postgres instance, just a different schema (warehouse, not public) and
multiple datasets instead of one.

The "one shared colour palette" half of this task is NOT done here: a
Superset custom color scheme is registered via EXTRA_CATEGORICAL_COLOR_
SCHEMES in docker/superset_config.py (a container-level setting, not
reachable through the REST API), requiring a Superset container restart
to take effect. See that file for the actual palette definition --
market -> hex, using the dataviz skill's validated CVD-safe categorical
slots (references/palette.md), same source as the existing Owner/Renter
chart's colors.

Requires Superset running and a .env file with SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD/POSTGRES_* (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\register_superset_datasets.py
"""

from setup_superset_dashboard import SUPERSET_URL, ensure_database, find_existing, get_session

SCHEMA = "warehouse"

# view name -> list of saved metrics (metric_name, expression, verbose_name)
# Only metrics over real, non-NULL columns are defined -- NOT
# renter_income_growth_pct or affordability_gap_index on
# v_story4_affordability_gap, since both are NULL for every row right now
# (see docs/affordability_gap_index.md). A saved metric over an all-NULL
# column would silently show as 0 or blank in a chart, indistinguishable
# from "the real value happens to be zero" -- worse than no metric at all.
VIEWS = {
    "v_story4_vacancy_comparison": [
        {
            "metric_name": "avg_vacancy_rate",
            "expression": "AVG(vacancy_rate_pct)",
            "verbose_name": "Average Vacancy Rate (%)",
            "metric_type": "avg",
            "description": "Apartment vacancy rate, Total bedroom type, averaged across whatever rows are in scope (e.g. filtered to one period).",
        },
    ],
    "v_story4_rent_comparison": [
        {
            "metric_name": "avg_rent_2br",
            "expression": "AVG(average_rent_2br)",
            "verbose_name": "Average 2BR Rent ($)",
            "metric_type": "avg",
            "description": "Average 2-bedroom apartment rent, averaged across whatever rows are in scope.",
        },
    ],
    "v_story4_affordability_gap": [
        {
            "metric_name": "avg_rent_growth",
            "expression": "AVG(rent_growth_pct)",
            "verbose_name": "Average Rent Growth (%)",
            "metric_type": "avg",
            "description": "Oct-24-to-25 rent growth (CMHC's matched-sample figure), averaged across whatever rows are in scope. The income-growth and index columns have no saved metric: both are NULL for every row -- see docs/affordability_gap_index.md.",
        },
    ],
}


def ensure_dataset(session, headers, database_id: int, table_name: str) -> int:
    existing = find_existing(session, headers, "dataset", "table_name", table_name)
    if existing:
        return existing

    resp = session.post(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        json={"database": database_id, "table_name": table_name, "schema": SCHEMA},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def set_metrics(session, headers, dataset_id: int, metrics: list[dict]) -> None:
    """Create-or-update each metric by name. Superset's dataset PUT treats
    a metric object without an "id" as a brand-new metric -- re-running
    this with the same metric_name but no id fails with 422 "One or more
    metrics already exist" instead of updating it in place. Fetching the
    dataset's current metrics first and attaching each existing metric's
    real id (by matching metric_name) is what makes this safe to re-run."""
    existing_resp = session.get(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers)
    existing_resp.raise_for_status()
    existing_by_name = {m["metric_name"]: m["id"] for m in existing_resp.json()["result"]["metrics"]}

    merged_metrics = []
    for metric in metrics:
        merged = dict(metric)
        if metric["metric_name"] in existing_by_name:
            merged["id"] = existing_by_name[metric["metric_name"]]
        merged_metrics.append(merged)

    resp = session.put(
        f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}",
        headers=headers,
        json={"metrics": merged_metrics},
    )
    resp.raise_for_status()


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    database_id = ensure_database(session, headers)
    print(f"Database connection ready: id={database_id}")

    for view_name, metrics in VIEWS.items():
        dataset_id = ensure_dataset(session, headers, database_id, view_name)
        set_metrics(session, headers, dataset_id, metrics)
        metric_names = ", ".join(m["metric_name"] for m in metrics)
        print(f"Dataset ready: {view_name} (id={dataset_id}), metrics: {metric_names}")
