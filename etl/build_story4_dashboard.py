"""
Build the Story 4 Superset dashboard ("How does Windsor compare to
similar markets?"): Windsor vs. the 4 real comparator CMAs (Hamilton,
Kitchener-Cambridge-Waterloo, London, St. Catharines-Niagara -- see
docs/comparator_cmas_justification.md) on apartment vacancy, 2-bedroom
rent, and the real rent-growth side of the affordability-gap index
(docs/affordability_gap_index.md).

The affordability-gap index itself (rent growth minus renter income
growth) is NOT shown as a single computed number -- the renter-income
side is NULL everywhere in this project's data (no source extracted
contains that time series, see the method note). Showing only the real
rent-growth component, with an honest markdown note on why the full
index isn't computable yet, is the choice made here -- a fabricated
index number would look like real data with no way for a viewer to
tell the difference.

Requires warehouse.v_story4_vacancy_comparison, v_story4_rent_comparison,
and v_story4_affordability_gap already registered as Superset datasets
(etl/register_superset_datasets.py) and Superset running. Also requires
sql/story4_views.sql's Windsor-row fix (this same change) already
applied -- without it, Windsor's own KPI tiles below would return no
rows.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story4_dashboard.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

DATASET_VACANCY = 2  # v_story4_vacancy_comparison
DATASET_RENT = 3  # v_story4_rent_comparison
DATASET_AFFORDABILITY_GAP = 4  # v_story4_affordability_gap

COLOR_SCHEME = "windsor_housing"
DASHBOARD_TITLE = "Story 4: How does Windsor compare to similar markets?"


def market_filter(market: str = "Windsor CMA"):
    return {
        "clause": "WHERE",
        "subject": "market",
        "operator": "==",
        "comparator": market,
        "expressionType": "SIMPLE",
    }


def period_filter(period: str = "Oct-25"):
    return {
        "clause": "WHERE",
        "subject": "period_label",
        "operator": "==",
        "comparator": period,
        "expressionType": "SIMPLE",
    }


CHARTS = {
    "kpi-vacancy": {
        "slice_name": "Windsor Apartment Vacancy Rate",
        "description": "Oct-25, apartment scope, Total bedroom type -- warehouse.v_story4_vacancy_comparison.",
        "dataset_id": DATASET_VACANCY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(vacancy_rate_pct) / 100.0",
                "label": "Vacancy Rate",
            },
            "adhoc_filters": [market_filter(), period_filter()],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-rent": {
        "slice_name": "Windsor 2-Bedroom Apartment Rent",
        "description": "Oct-25, apartment scope -- warehouse.v_story4_rent_comparison.",
        "dataset_id": DATASET_RENT,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SIMPLE",
                "column": {"column_name": "average_rent_2br"},
                "aggregate": "MAX",
                "label": "Average Rent",
            },
            "adhoc_filters": [market_filter(), period_filter()],
            "y_axis_format": "$,.0f",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-rent-growth": {
        "slice_name": "Windsor Rent Growth (Oct-24 to Oct-25)",
        "description": "CMHC matched-sample rent growth -- warehouse.v_story4_affordability_gap.",
        "dataset_id": DATASET_AFFORDABILITY_GAP,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(rent_growth_pct) / 100.0",
                "label": "Rent Growth",
            },
            "adhoc_filters": [market_filter()],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Oct-24 to Oct-25, matched sample",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "vacancy-by-market": {
        "slice_name": "Apartment Vacancy Rate by Market (Oct-25)",
        "description": "Windsor vs. the 4 real comparator CMAs -- warehouse.v_story4_vacancy_comparison.",
        "dataset_id": DATASET_VACANCY,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["market"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(vacancy_rate_pct) / 100.0",
                    "label": "Vacancy Rate",
                }
            ],
            "adhoc_filters": [period_filter()],
            "order_desc": True,
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ".1%",
            "x_axis_label": "Market",
            "y_axis_label": "Vacancy Rate (%)",
        },
    },
    "rent-by-market": {
        "slice_name": "2-Bedroom Apartment Rent by Market (Oct-25)",
        "description": "Windsor vs. the 4 real comparator CMAs -- warehouse.v_story4_rent_comparison.",
        "dataset_id": DATASET_RENT,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["market"],
            "metrics": [
                {
                    "expressionType": "SIMPLE",
                    "column": {"column_name": "average_rent_2br"},
                    "aggregate": "AVG",
                    "label": "Average Rent",
                }
            ],
            "adhoc_filters": [period_filter()],
            "order_desc": True,
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": "$,.0f",
            "x_axis_label": "Market",
            "y_axis_label": "Average Rent ($)",
        },
    },
    "rent-growth-by-market": {
        "slice_name": "Rent Growth by Market (Oct-24 to Oct-25)",
        "description": (
            "Real rent-growth component of the affordability-gap index -- "
            "warehouse.v_story4_affordability_gap. The index itself (rent growth minus renter "
            "income growth) can't be shown -- income growth isn't available, see the markdown "
            "note below."
        ),
        "dataset_id": DATASET_AFFORDABILITY_GAP,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["market"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(rent_growth_pct) / 100.0",
                    "label": "Rent Growth",
                }
            ],
            "adhoc_filters": [],
            "order_desc": True,
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ".1%",
            "x_axis_label": "Market",
            "y_axis_label": "Rent Growth, Oct-24 to Oct-25 (%)",
        },
    },
}

AFFORDABILITY_GAP_MARKDOWN = """**Why no single affordability-gap number is shown.** The
Affordability-Gap Index (AGI) is defined as rent growth minus renter income
growth over the same period. The rent-growth side above is real, CMHC
matched-sample data. The renter-income-growth side is `NULL` for every
market -- no source this project has extracted contains a renter/household
income time series to compute it from (confirmed directly, not assumed).
A fabricated number here would look like real data with no way for a
viewer to tell the difference. Full method note, what would close the
gap, and the directional read if income growth turns out to be roughly
uniform across these Ontario CMAs: `docs/affordability_gap_index.md`.
"""


def ensure_chart(session, headers, spec: dict) -> int:
    body = {
        "slice_name": spec["slice_name"],
        "description": spec["description"],
        "viz_type": spec["viz_type"],
        "datasource_id": spec["dataset_id"],
        "datasource_type": "table",
        "params": json.dumps(spec["params"]),
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
                "HEADER-kpis",
                "ROW-kpi",
                "HEADER-vacancy",
                "ROW-vacancy",
                "HEADER-rent",
                "ROW-rent",
                "HEADER-rent-growth",
                "ROW-rent-growth",
                "ROW-note",
            ],
            "parents": ["ROOT_ID"],
        },
    }

    position["HEADER-kpis"] = header_node("HEADER-kpis", "Windsor at a Glance")
    position["ROW-kpi"] = row_node(
        "ROW-kpi", ["CHART-kpi-vacancy", "CHART-kpi-rent", "CHART-kpi-rent-growth"]
    )
    position["CHART-kpi-vacancy"] = chart_node("CHART-kpi-vacancy", "ROW-kpi", chart_ids["kpi-vacancy"], 4)
    position["CHART-kpi-rent"] = chart_node("CHART-kpi-rent", "ROW-kpi", chart_ids["kpi-rent"], 4)
    position["CHART-kpi-rent-growth"] = chart_node(
        "CHART-kpi-rent-growth", "ROW-kpi", chart_ids["kpi-rent-growth"], 4
    )

    position["HEADER-vacancy"] = header_node("HEADER-vacancy", "Vacancy Rate Comparison")
    position["ROW-vacancy"] = row_node("ROW-vacancy", ["CHART-vacancy-by-market"])
    position["CHART-vacancy-by-market"] = chart_node(
        "CHART-vacancy-by-market", "ROW-vacancy", chart_ids["vacancy-by-market"], 12, 55
    )

    position["HEADER-rent"] = header_node("HEADER-rent", "Rent Comparison")
    position["ROW-rent"] = row_node("ROW-rent", ["CHART-rent-by-market"])
    position["CHART-rent-by-market"] = chart_node(
        "CHART-rent-by-market", "ROW-rent", chart_ids["rent-by-market"], 12, 55
    )

    position["HEADER-rent-growth"] = header_node("HEADER-rent-growth", "Affordability-Gap Index")
    position["ROW-rent-growth"] = row_node("ROW-rent-growth", ["CHART-rent-growth-by-market"])
    position["CHART-rent-growth-by-market"] = chart_node(
        "CHART-rent-growth-by-market", "ROW-rent-growth", chart_ids["rent-growth-by-market"], 12, 55
    )

    position["ROW-note"] = row_node("ROW-note", ["MARKDOWN-affordability-gap"])
    position["MARKDOWN-affordability-gap"] = markdown_node(
        "MARKDOWN-affordability-gap", "ROW-note", AFFORDABILITY_GAP_MARKDOWN
    )

    return position


def ensure_dashboard(session, headers, position_json: dict) -> int:
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "published": True,
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps({"color_scheme": COLOR_SCHEME}),
    }
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers, json=body)
        resp.raise_for_status()
        return existing
    resp = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = {}
    for key, spec in CHARTS.items():
        chart_id = ensure_chart(session, headers, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")

    position_json = build_position_json(chart_ids)
    dashboard_id = ensure_dashboard(session, headers, position_json)
    print(f"Dashboard ready: id={dashboard_id}")

    for key, chart_id in chart_ids.items():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
