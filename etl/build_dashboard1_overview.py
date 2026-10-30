"""
Build "01 - Windsor Housing Executive Overview": a combined dashboard
across Stories 1-4, built to match the shape of a dashboard a teammate
built directly in a separate Superset environment, reproduced here
against this project's own real data (not copied from an environment
this project has no access to).

4 sections:
    - Housing Affordability: reuses Story 1's existing charts directly
      (same Superset chart objects, added to this dashboard too -- no
      duplication).
    - Windsor Rental Market: 4 new KPI tiles + a Oct-24-vs-Oct-25 table,
      on warehouse.v_dashboard1_rental_yoy.
    - Housing Supply: 2 new charts on the already-existing
      warehouse.v_story3_starts_completions_by_dwelling_type (Ontario/
      Canada scope -- no Windsor-specific figure exists in CMHC's source
      table, labeled as such rather than implied to be Windsor-specific).
    - Windsor vs Canadian CMAs: a benchmark table on the new
      warehouse.v_dashboard1_cma_benchmark -- Windsor vs. the median of
      this project's real 4 comparator CMAs (5 total), not a national
      ranking (see sql/dashboard1_views.sql's own comment on why a
      wider ranking isn't reproducible from this project's real data).

Requires warehouse.v_dashboard1_rental_yoy and v_dashboard1_cma_benchmark
already registered as Superset datasets (etl/register_superset_datasets.py)
and Superset running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_dashboard1_overview.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

DATASET_RENTAL_YOY = 16  # v_dashboard1_rental_yoy
DATASET_CMA_BENCHMARK = 17  # v_dashboard1_cma_benchmark
DATASET_SUPPLY = 12  # v_story3_starts_completions_by_dwelling_type

DASHBOARD_TITLE = "01 - Windsor Housing Executive Overview"

# Story 1's existing chart ids (dashboard 3), reused here directly.
AFFORDABILITY_CHART_IDS = {"tenure-bar": 2, "kpi-renter": 3, "kpi-owner": 4}

COLOR_SCHEME = "windsor_housing"


def metric_filter(value: str, col: str = "metric"):
    return {"clause": "WHERE", "subject": col, "operator": "==", "comparator": value, "expressionType": "SIMPLE"}


def province_filter(value: str = "Ontario"):
    return {
        "clause": "WHERE",
        "subject": "province",
        "operator": "==",
        "comparator": value,
        "expressionType": "SIMPLE",
    }


NEW_CHARTS = {
    "kpi-rent": {
        "slice_name": "Windsor Average Rent (Apartment)",
        "description": "Oct-25, apartment scope -- warehouse.v_dashboard1_rental_yoy.",
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SIMPLE",
                "column": {"column_name": "latest_value"},
                "aggregate": "MAX",
                "label": "Average Rent",
            },
            "adhoc_filters": [metric_filter("average_rent")],
            "y_axis_format": "$,.0f",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-vacancy": {
        "slice_name": "Windsor Vacancy Rate (Apartment)",
        "description": "Oct-25, apartment scope -- warehouse.v_dashboard1_rental_yoy.",
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(latest_value) / 100.0",
                "label": "Vacancy Rate",
            },
            "adhoc_filters": [metric_filter("vacancy_rate")],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-stock": {
        "slice_name": "Windsor Rental Stock (Combined)",
        "description": "Oct-25, Combined dwelling scope (not Apartment -- rental-stock universe isn't published at Apartment scope in this project's data) -- warehouse.v_dashboard1_rental_yoy.",
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SIMPLE",
                "column": {"column_name": "latest_value"},
                "aggregate": "MAX",
                "label": "Rental Stock",
            },
            "adhoc_filters": [metric_filter("universe")],
            "y_axis_format": ",d",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25, Combined scope",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-turnover": {
        "slice_name": "Windsor Turnover Rate (Combined)",
        "description": "Oct-25, Combined dwelling scope -- warehouse.v_dashboard1_rental_yoy.",
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(latest_value) / 100.0",
                "label": "Turnover Rate",
            },
            "adhoc_filters": [metric_filter("turnover_rate")],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "Latest CMHC survey -- Oct-25, Combined scope",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "rental-yoy-table": {
        "slice_name": "Rental Market Oct-24 vs Oct-25",
        "description": "All 4 metrics, Windsor CMA -- warehouse.v_dashboard1_rental_yoy.",
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "table",
        "params": {
            "query_mode": "raw",
            "columns": [
                "metric",
                "dwelling_type_label",
                "previous_period_label",
                "previous_value",
                "latest_period_label",
                "latest_value",
                "change_value",
                "change_unit",
            ],
            "row_limit": 10,
            "server_pagination": False,
        },
    },
    "supply-snapshot": {
        "slice_name": "Housing Supply Snapshot",
        "description": "Ontario, Second Quarter 2026 (the 'Total' dwelling-type row, not summed from the per-dwelling-type rows -- this source has both, and they're not interchangeable: it also separately publishes a January-to-June-2026 YTD period, which would silently double stack if not filtered out) -- no Windsor-specific starts/completions figure exists in CMHC's source table -- warehouse.v_story3_starts_completions_by_dwelling_type.",
        "dataset_id": DATASET_SUPPLY,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["activity"],
            "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "units"}, "aggregate": "SUM", "label": "Units"}],
            "adhoc_filters": [
                province_filter("Ontario"),
                {
                    "clause": "WHERE",
                    "subject": "period_label",
                    "operator": "==",
                    "comparator": "Second Quarter 2026",
                    "expressionType": "SIMPLE",
                },
                {
                    "clause": "WHERE",
                    "subject": "dwelling_type",
                    "operator": "==",
                    "comparator": "Total",
                    "expressionType": "SIMPLE",
                },
            ],
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_label": "Activity",
            "y_axis_label": "Units (Ontario, Second Quarter 2026)",
        },
    },
    "supply-by-dwelling-type": {
        "slice_name": "YTD Starts vs Completions by Dwelling Type",
        "description": "Ontario, January to June 2026 (YTD) -- excludes the pre-computed 'Total' dwelling-type row, which would otherwise double the real total alongside the 4 individual categories -- warehouse.v_story3_starts_completions_by_dwelling_type.",
        "dataset_id": DATASET_SUPPLY,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["dwelling_type"],
            "columns": ["activity"],
            "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "units"}, "aggregate": "SUM", "label": "Units"}],
            "adhoc_filters": [
                province_filter("Ontario"),
                {
                    "clause": "WHERE",
                    "subject": "period_label",
                    "operator": "==",
                    "comparator": "January to June 2026",
                    "expressionType": "SIMPLE",
                },
                {
                    "clause": "WHERE",
                    "subject": "dwelling_type",
                    "operator": "!=",
                    "comparator": "Total",
                    "expressionType": "SIMPLE",
                },
                {
                    "clause": "WHERE",
                    "subject": "activity",
                    "operator": "IN",
                    "comparator": ["Starts", "Completions"],
                    "expressionType": "SIMPLE",
                },
            ],
            "row_limit": 20,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_label": "Dwelling type",
            "y_axis_label": "Units (Ontario, YTD)",
        },
    },
    "cma-benchmark-table": {
        "slice_name": "Windsor vs CMA Benchmark",
        "description": "Windsor vs. the median of this project's real 4 comparator CMAs (5 total, not a national ranking) -- warehouse.v_dashboard1_cma_benchmark.",
        "dataset_id": DATASET_CMA_BENCHMARK,
        "viz_type": "table",
        "params": {
            "query_mode": "raw",
            "columns": [
                "metric",
                "period_label",
                "windsor_value",
                "cma_median_value",
                "windsor_minus_median",
                "windsor_rank_highest_first",
                "cmas_ranked",
            ],
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "subject": "period_label",
                    "operator": "==",
                    "comparator": "Oct-25",
                    "expressionType": "SIMPLE",
                }
            ],
            "row_limit": 10,
            "server_pagination": False,
        },
    },
}


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
    # Fetch the chart's current dashboards first -- PUT replaces the list,
    # so a chart already on another dashboard (e.g. Story 1's charts,
    # already on dashboard 3) must keep that membership, not lose it.
    resp = session.get(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers)
    resp.raise_for_status()
    current = [d["id"] for d in resp.json()["result"].get("dashboards", [])]
    if dashboard_id not in current:
        current.append(dashboard_id)
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": current}
    )
    resp.raise_for_status()


# Both tables on this dashboard have 4 rows -- at 55 (the bar-chart
# height) each left a large blank area under its last row. 40 matches the
# zone snapshot table on Dashboard 3 (etl/build_story2_dashboard.py).
TABLE_HEIGHT = 40


def chart_node(node_id: str, parent_id: str, chart_id: int, width: int, height: int = 25) -> dict:
    # Default height, used only by big_number_total KPI tiles (every bar
    # chart below passes its own height=55, tables TABLE_HEIGHT) -- was
    # 50, which left a large empty gap above the number inside every KPI
    # card, confirmed visually, not a guess.
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


def build_position_json(chart_ids: dict) -> dict:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [
                "HEADER-affordability",
                "ROW-affordability",
                "HEADER-rental",
                "ROW-rental-kpi",
                "ROW-rental-table",
                "HEADER-supply",
                "ROW-supply",
                "HEADER-cma",
                "ROW-cma",
            ],
            "parents": ["ROOT_ID"],
        },
    }

    position["HEADER-affordability"] = header_node("HEADER-affordability", "Housing Affordability")
    position["ROW-affordability"] = row_node(
        "ROW-affordability", ["CHART-tenure-bar", "CHART-kpi-renter-a", "CHART-kpi-owner-a"]
    )
    position["CHART-tenure-bar"] = chart_node(
        "CHART-tenure-bar", "ROW-affordability", chart_ids["tenure-bar"], 6, 55
    )
    position["CHART-kpi-renter-a"] = chart_node(
        "CHART-kpi-renter-a", "ROW-affordability", chart_ids["kpi-renter"], 3
    )
    position["CHART-kpi-owner-a"] = chart_node(
        "CHART-kpi-owner-a", "ROW-affordability", chart_ids["kpi-owner"], 3
    )

    position["HEADER-rental"] = header_node("HEADER-rental", "Windsor Rental Market")
    position["ROW-rental-kpi"] = row_node(
        "ROW-rental-kpi",
        ["CHART-kpi-rent", "CHART-kpi-vacancy", "CHART-kpi-stock", "CHART-kpi-turnover"],
    )
    position["CHART-kpi-rent"] = chart_node("CHART-kpi-rent", "ROW-rental-kpi", chart_ids["kpi-rent"], 3)
    position["CHART-kpi-vacancy"] = chart_node(
        "CHART-kpi-vacancy", "ROW-rental-kpi", chart_ids["kpi-vacancy"], 3
    )
    position["CHART-kpi-stock"] = chart_node(
        "CHART-kpi-stock", "ROW-rental-kpi", chart_ids["kpi-stock"], 3
    )
    position["CHART-kpi-turnover"] = chart_node(
        "CHART-kpi-turnover", "ROW-rental-kpi", chart_ids["kpi-turnover"], 3
    )
    position["ROW-rental-table"] = row_node("ROW-rental-table", ["CHART-rental-yoy-table"])
    position["CHART-rental-yoy-table"] = chart_node(
        "CHART-rental-yoy-table", "ROW-rental-table", chart_ids["rental-yoy-table"], 12, TABLE_HEIGHT
    )

    position["HEADER-supply"] = header_node("HEADER-supply", "Housing Supply")
    position["ROW-supply"] = row_node(
        "ROW-supply", ["CHART-supply-snapshot", "CHART-supply-by-dwelling-type"]
    )
    position["CHART-supply-snapshot"] = chart_node(
        "CHART-supply-snapshot", "ROW-supply", chart_ids["supply-snapshot"], 6, 55
    )
    position["CHART-supply-by-dwelling-type"] = chart_node(
        "CHART-supply-by-dwelling-type", "ROW-supply", chart_ids["supply-by-dwelling-type"], 6, 55
    )

    position["HEADER-cma"] = header_node("HEADER-cma", "Windsor vs Canadian CMAs")
    position["ROW-cma"] = row_node("ROW-cma", ["CHART-cma-benchmark-table"])
    position["CHART-cma-benchmark-table"] = chart_node(
        "CHART-cma-benchmark-table", "ROW-cma", chart_ids["cma-benchmark-table"], 12, TABLE_HEIGHT
    )

    return position


def build_native_filters() -> list:
    """No native filters yet -- every section here spans a different
    dataset shape (tenure, bedroom type, dwelling type, CMA), so a single
    cross-cutting filter would either no-op on most charts or need per-
    section scoping with no clear shared dimension. Left for a follow-up
    once there's a real cross-section filter to add, not stubbed in."""
    return []


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = dict(AFFORDABILITY_CHART_IDS)
    for key, spec in NEW_CHARTS.items():
        chart_id = ensure_chart(session, headers, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")

    position_json = build_position_json(chart_ids)
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "published": True,
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps(
            {"native_filter_configuration": build_native_filters(), "color_scheme": COLOR_SCHEME}
        ),
    }
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers, json=body)
        dashboard_id = existing
    else:
        resp = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", headers=headers, json=body)
        dashboard_id = resp.json()["id"] if resp.status_code < 400 else None
    resp.raise_for_status()
    if dashboard_id is None:
        dashboard_id = resp.json()["id"]
    print(f"Dashboard ready: id={dashboard_id}")

    for key, chart_id in chart_ids.items():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
