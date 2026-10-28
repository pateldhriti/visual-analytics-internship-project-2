"""
Finalize Story 1's dashboard layout: organize the existing charts into
named sections (Gap KPIs, Income-Group Analysis, Household-Type
Analysis, Burden Severity, Census Validation), add 2 new Burden Severity
KPI tiles on warehouse.v_story1_burden_severity, add a Census Validation
markdown note referencing docs/story1_validation.md's already-verified
reconciliation, and resize the income-band/household-type/tenure charts
to full width now that they each have their own section instead of
sharing a row.

Requires warehouse.v_story1_burden_severity already registered as a
Superset dataset (etl/register_superset_datasets.py) and Superset
running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\finalize_story1_layout.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

DASHBOARD_ID = 3
DATASET_SEVERITY = 15  # v_story1_burden_severity

# Existing chart ids on dashboard 3, from Story 1's original build.
EXISTING = {
    "tenure-bar": 2,  # Share of households spending 30%+ on shelter costs, by tenure
    "kpi-renter": 3,  # Renter Burden Rate
    "kpi-owner": 4,  # Owner Burden Rate
    "kpi-total": 5,  # Households Spending 30%+ on Shelter
    "income-band": 6,  # Burden Rate by Income Band
    "household-type": 7,  # Burden Rate by Household Type

}

NEW_CHARTS = {
    "kpi-severity-renter": {
        "slice_name": "Renter Households in Severe Range (30-99%)",
        "description": "Of renter households already spending 30%+ on shelter, the share in the 30%-to-under-100% band -- warehouse.v_story1_burden_severity.",
        "dataset_id": DATASET_SEVERITY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SIMPLE",
                "column": {"column_name": "severe_pct_of_burdened"},
                "aggregate": "MAX",
                "label": "Severe Range Share",
            },
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "subject": "tenure",
                    "operator": "==",
                    "comparator": "Renter",
                    "expressionType": "SIMPLE",
                }
            ],
            "y_axis_format": ".1f",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "of renter burdened households spend 30%-99% of income on shelter",
            "color_scheme": "windsor_housing",
        },
    },
    "kpi-severity-owner": {
        "slice_name": "Owner Households in Severe Range (30-99%)",
        "description": "Of owner households already spending 30%+ on shelter, the share in the 30%-to-under-100% band -- warehouse.v_story1_burden_severity.",
        "dataset_id": DATASET_SEVERITY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SIMPLE",
                "column": {"column_name": "severe_pct_of_burdened"},
                "aggregate": "MAX",
                "label": "Severe Range Share",
            },
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "subject": "tenure",
                    "operator": "==",
                    "comparator": "Owner",
                    "expressionType": "SIMPLE",
                }
            ],
            "y_axis_format": ".1f",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "of owner burdened households spend 30%-99% of income on shelter",
            "color_scheme": "windsor_housing",
        },
    },
}

VALIDATION_MARKDOWN = """**Validated against StatCan's own published figures.** The Renter Burden
Rate (34.8%) and Owner Burden Rate (10.9%) KPIs above were independently
reproduced from two different StatCan products -- the shelter-cost-to-income
ratio table (98-10-0252-01) this dashboard queries, and StatCan's own
pre-computed Census Profile rate characteristics (98-401-X2021002, items
1484/1492) -- and match exactly. Full reconciliation: `docs/story1_validation.md`.
"""


def ensure_chart(session, headers, spec: dict) -> int:
    params_json = json.dumps(spec["params"])
    body = {
        "slice_name": spec["slice_name"],
        "description": spec["description"],
        "viz_type": spec["viz_type"],
        "datasource_id": spec["dataset_id"],
        "datasource_type": "table",
        "params": params_json,
    }
    existing = find_existing(session, headers, "chart", "slice_name", spec["slice_name"])
    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/chart/{existing}", headers=headers, json=body)
        resp.raise_for_status()
        return existing
    resp = session.post(f"{SUPERSET_URL}/api/v1/chart/", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": [dashboard_id]}
    )
    resp.raise_for_status()


def chart_node(node_id: str, parent_id: str, chart_id: int, width: int, height: int = 50) -> dict:
    return {
        "type": "CHART",
        "id": node_id,
        "children": [],
        "parents": ["ROOT_ID", "GRID_ID", parent_id],
        "meta": {"chartId": chart_id, "width": width, "height": height, "uuid": str(uuid.uuid4())},
    }


def header_node(node_id: str, text: str) -> dict:
    return {
        "type": "HEADER",
        "id": node_id,
        "children": [],
        "parents": ["ROOT_ID", "GRID_ID"],
        "meta": {"text": text, "headerSize": "MEDIUM_HEADER", "background": "BACKGROUND_TRANSPARENT"},
    }


def row_node(node_id: str, children: list) -> dict:
    return {
        "type": "ROW",
        "id": node_id,
        "children": children,
        "parents": ["ROOT_ID", "GRID_ID"],
        "meta": {"background": "BACKGROUND_TRANSPARENT"},
    }


def markdown_node(node_id: str, parent_id: str, code: str, width: int = 12, height: int = 30) -> dict:
    return {
        "type": "MARKDOWN",
        "id": node_id,
        "children": [],
        "parents": ["ROOT_ID", "GRID_ID", parent_id],
        "meta": {"width": width, "height": height, "code": code, "uuid": str(uuid.uuid4())},
    }


def build_position_json(chart_ids: dict) -> dict:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [
                "HEADER-gap-kpis",
                "ROW-kpi",
                "ROW-tenure-bar",
                "HEADER-income",
                "ROW-income",
                "HEADER-household",
                "ROW-household",
                "HEADER-severity",
                "ROW-severity",
                "HEADER-validation",
                "ROW-validation",
            ],
            "parents": ["ROOT_ID"],
        },
    }

    position["HEADER-gap-kpis"] = header_node("HEADER-gap-kpis", "Gap KPIs")
    position["ROW-kpi"] = row_node("ROW-kpi", ["CHART-kpi-renter", "CHART-kpi-owner", "CHART-kpi-total"])
    position["CHART-kpi-renter"] = chart_node(
        "CHART-kpi-renter", "ROW-kpi", chart_ids["kpi-renter"], 4
    )
    position["CHART-kpi-owner"] = chart_node("CHART-kpi-owner", "ROW-kpi", chart_ids["kpi-owner"], 4)
    position["CHART-kpi-total"] = chart_node("CHART-kpi-total", "ROW-kpi", chart_ids["kpi-total"], 4)

    position["ROW-tenure-bar"] = row_node("ROW-tenure-bar", ["CHART-tenure-bar"])
    position["CHART-tenure-bar"] = chart_node(
        "CHART-tenure-bar", "ROW-tenure-bar", chart_ids["tenure-bar"], 12, 55
    )

    position["HEADER-income"] = header_node("HEADER-income", "Income-Group Analysis")
    position["ROW-income"] = row_node("ROW-income", ["CHART-income-band"])
    position["CHART-income-band"] = chart_node(
        "CHART-income-band", "ROW-income", chart_ids["income-band"], 12, 55
    )

    position["HEADER-household"] = header_node("HEADER-household", "Household-Type Analysis")
    position["ROW-household"] = row_node("ROW-household", ["CHART-household-type"])
    position["CHART-household-type"] = chart_node(
        "CHART-household-type", "ROW-household", chart_ids["household-type"], 12, 55
    )

    position["HEADER-severity"] = header_node("HEADER-severity", "Burden Severity")
    position["ROW-severity"] = row_node(
        "ROW-severity", ["CHART-severity-renter", "CHART-severity-owner"]
    )
    position["CHART-severity-renter"] = chart_node(
        "CHART-severity-renter", "ROW-severity", chart_ids["kpi-severity-renter"], 6
    )
    position["CHART-severity-owner"] = chart_node(
        "CHART-severity-owner", "ROW-severity", chart_ids["kpi-severity-owner"], 6
    )

    position["HEADER-validation"] = header_node("HEADER-validation", "Census Validation")
    position["ROW-validation"] = row_node("ROW-validation", ["MARKDOWN-validation"])
    position["MARKDOWN-validation"] = markdown_node(
        "MARKDOWN-validation", "ROW-validation", VALIDATION_MARKDOWN
    )

    return position


def verify_native_filter_scope(session, headers, dashboard_id: int, new_chart_ids: set) -> None:
    """The 2 new severity KPIs are, like the Renter/Owner Burden Rate KPIs
    (etl/fix_story1_tenure_filter_scope.py), fixed-per-tenure and must stay
    out of both native filters' chartsInScope -- same conflict would occur
    otherwise (each already has its own hardcoded tenure filter). Nothing
    adds them to chartsInScope, so this only verifies that's still true
    rather than silently assuming it."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", headers=headers)
    resp.raise_for_status()
    metadata = json.loads(resp.json()["result"]["json_metadata"])

    for f in metadata.get("native_filter_configuration", []):
        overlap = set(f["chartsInScope"]) & new_chart_ids
        if overlap:
            raise RuntimeError(f"Filter '{f['name']}' unexpectedly includes new KPI chart(s) {overlap}")
    print("Verified: no native filter includes the new severity KPI tiles.")


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = dict(EXISTING)
    for key, spec in NEW_CHARTS.items():
        chart_id = ensure_chart(session, headers, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")
        link_chart_to_dashboard(session, headers, chart_id, DASHBOARD_ID)

    position_json = build_position_json(chart_ids)
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}",
        headers=headers,
        json={"position_json": json.dumps(position_json)},
    )
    resp.raise_for_status()
    print(f"Dashboard {DASHBOARD_ID} layout updated: 5 sections, {len(chart_ids)} charts.")

    new_ids = {chart_ids[key] for key in NEW_CHARTS}
    verify_native_filter_scope(session, headers, DASHBOARD_ID, new_ids)

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
