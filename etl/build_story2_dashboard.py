"""
Build the Story 2 Superset dashboard ("What is happening in Windsor's
rental market?"): a 4-tile KPI section (Average Rent, Vacancy, Turnover,
Rental Stock), rent by bedroom type and zone, rent and vacancy over the
project's real 6-year span (Oct-20 to Oct-25 -- not 10 years, see
sql/story2_views.sql's own header comment), turnover by bedroom type,
with native filters for zone and bedroom type.

Reuses the auth/session helpers from etl/setup_superset_dashboard.py
(same classic form-login session-cookie approach that fixed the
JWT-only-login visibility bug -- see that file's get_session()
docstring). The 4 KPI tiles use viz_type "big_number_total" (the trend
and breakdown charts stay "dist_bar", the one chart type already proven
to render correctly end-to-end in this Superset build -- period_label
(Oct-20..Oct-25) is a text column, not a real DATE type, so a proper
time-series viz_type isn't reliably available without first adding a
computed date column; dist_bar with period as the x-axis category sorts
correctly anyway since "Oct-20" < "Oct-21" < ... < "Oct-25" in plain
string order). The 2 non-KPI-tile charts' row below is unaffected.

The 4 KPI tiles are deliberately excluded from both native filters'
chartsInScope, same as Story 1's KPI tiles -- each tile already hardcodes
its own bedroom-type/period scope, and AND-combining that with a
user-selected filter value can silently return zero rows (confirmed
directly as a real bug on Story 1's tiles, see
docs/story1_exploratory_findings.md history in git log for
fix_story1_tenure_filter_scope.py). Rental Stock's dataset
(v_dashboard1_rental_yoy) doesn't even have a bedroom_type_label column,
so including it in the Bedroom-type filter's scope would error outright.

Requires the 5 Story 2 views already registered as Superset datasets
(etl/register_superset_datasets.py) and Superset running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story2_dashboard.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

# Dataset ids, from etl/register_superset_datasets.py's own output --
# re-verify with `SELECT id, table_name FROM tables` if this script is
# ever run against a fresh environment where ids may differ.
DATASET_RENT_YOY = 9  # v_story2_rent_yoy_change
DATASET_VACANCY = 6  # v_story2_vacancy_trend
DATASET_TURNOVER = 11  # v_story2_turnover_by_bedroom
DATASET_RENT_ZONE = 14  # v_story2_rent_by_zone_bedroom
# v_dashboard1_rental_yoy -- built for Dashboard 1, reused here rather than
# duplicated: it's the only registered view with a "universe" (rental
# stock) row at all. No Story 2 view carries that column (confirmed
# against sql/story2_views.sql) -- fabricating a new one just to avoid
# reuse would mean a second view computing the same real
# fact_rental_market rows the Dashboard 1 one already does.
DATASET_RENTAL_YOY = 16  # v_dashboard1_rental_yoy

COLOR_SCHEME = "windsor_housing"  # validated CVD-safe palette, docker/superset_config.py

EXCLUDE_TOTAL_BEDROOM = {
    "clause": "WHERE",
    "subject": "bedroom_type_label",
    "operator": "!=",
    "comparator": "Total",
    "expressionType": "SIMPLE",
}


def combined_filter(dwelling_type_col="dwelling_type_label"):
    return {
        "clause": "WHERE",
        "subject": dwelling_type_col,
        "operator": "==",
        "comparator": "Combined",
        "expressionType": "SIMPLE",
    }


def period_filter(period="Oct-25"):
    return {
        "clause": "WHERE",
        "subject": "period_label",
        "operator": "==",
        "comparator": period,
        "expressionType": "SIMPLE",
    }


def bedroom_filter(bedroom="Total"):
    return {
        "clause": "WHERE",
        "subject": "bedroom_type_label",
        "operator": "==",
        "comparator": bedroom,
        "expressionType": "SIMPLE",
    }


# Each entry: internal key, slice_name, dataset id, viz_type, params.
# KPI tiles are "big_number_total" (same viz_type Story 1's KPI tiles
# use); everything else is "dist_bar".
CHARTS = {
    "kpi-vacancy": {
        "slice_name": "Windsor CMA Vacancy Rate",
        "description": "Combined dwelling types, Total bedroom type, Oct-25 -- warehouse.v_story2_vacancy_trend.",
        "dataset_id": DATASET_VACANCY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "AVG(vacancy_rate_pct)",
                "label": "Vacancy Rate",
            },
            "adhoc_filters": [combined_filter(), bedroom_filter("Total"), period_filter("Oct-25")],
            "y_axis_format": ".1f",
            "subheader": "October 2025, Combined dwelling types",
        },
    },
    "kpi-rent": {
        "slice_name": "Windsor CMA Average Rent",
        "description": "All bedroom types blended, Oct-25 -- warehouse.v_story2_rent_yoy_change.",
        "dataset_id": DATASET_RENT_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "AVG(average_rent)",
                "label": "Average Rent",
            },
            "adhoc_filters": [bedroom_filter("Total"), period_filter("Oct-25")],
            "y_axis_format": "$,.0f",
            "subheader": "October 2025, all bedroom types",
        },
    },
    "kpi-turnover": {
        "slice_name": "Windsor CMA Turnover Rate",
        "description": "Combined dwelling types, Total bedroom type, Oct-25 -- warehouse.v_story2_turnover_by_bedroom.",
        "dataset_id": DATASET_TURNOVER,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "AVG(turnover_rate_pct)",
                "label": "Turnover Rate",
            },
            "adhoc_filters": [combined_filter(), bedroom_filter("Total"), period_filter("Oct-25")],
            "y_axis_format": ".1f",
            "subheader": "October 2025, Combined dwelling types",
        },
    },
    "kpi-stock": {
        "slice_name": "Windsor CMA Rental Stock",
        "description": (
            "Combined dwelling types, Oct-25 rental universe (total surveyed rental units) -- "
            "warehouse.v_dashboard1_rental_yoy."
        ),
        "dataset_id": DATASET_RENTAL_YOY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(latest_value)",
                "label": "Rental Stock",
            },
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "subject": "metric",
                    "operator": "==",
                    "comparator": "universe",
                    "expressionType": "SIMPLE",
                },
                combined_filter("dwelling_type_label"),
            ],
            "y_axis_format": ",.0f",
            "subheader": "October 2025, Combined dwelling types, total rental universe",
        },
    },
    "rent-zone": {
        "slice_name": "Average Rent by Zone and Bedroom Type",
        "description": "Oct-25, excludes the Windsor CMA/Windsor City rollup rows and the Total bedroom-type row -- warehouse.v_story2_rent_by_zone_bedroom.",
        "dataset_id": DATASET_RENT_ZONE,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["zone_label"],
            "columns": ["bedroom_type_label"],
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "AVG(average_rent)", "label": "Average Rent"}
            ],
            "adhoc_filters": [EXCLUDE_TOTAL_BEDROOM],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": "$,.0f",
            "x_axis_label": "Zone",
            "y_axis_label": "Average Rent ($)",
        },
    },
    "rent-trend": {
        "slice_name": "Average Rent by Period and Bedroom Type (Oct-20 to Oct-25)",
        "description": "Real 6-year span this project has data for -- warehouse.v_story2_rent_yoy_change. Excludes the Total bedroom-type row.",
        "dataset_id": DATASET_RENT_YOY,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["period_label"],
            "columns": ["bedroom_type_label"],
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "AVG(average_rent)", "label": "Average Rent"}
            ],
            "adhoc_filters": [EXCLUDE_TOTAL_BEDROOM],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": "$,.0f",
            "x_axis_label": "Period",
            "y_axis_label": "Average Rent ($)",
        },
    },
    "vacancy-trend": {
        "slice_name": "Vacancy Rate by Period and Bedroom Type (Oct-20 to Oct-25)",
        "description": "Combined dwelling types, real 6-year span -- warehouse.v_story2_vacancy_trend. Excludes the Total bedroom-type row.",
        "dataset_id": DATASET_VACANCY,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["period_label"],
            "columns": ["bedroom_type_label"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(vacancy_rate_pct)",
                    "label": "Vacancy Rate",
                }
            ],
            "adhoc_filters": [combined_filter(), EXCLUDE_TOTAL_BEDROOM],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ".1f",
            "x_axis_label": "Period",
            "y_axis_label": "Vacancy Rate (%)",
        },
    },
    "turnover": {
        "slice_name": "Turnover Rate by Bedroom Type (Oct-25)",
        "description": "Combined dwelling types -- warehouse.v_story2_turnover_by_bedroom. Excludes the Total bedroom-type row.",
        "dataset_id": DATASET_TURNOVER,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["bedroom_type_label"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(turnover_rate_pct)",
                    "label": "Turnover Rate",
                }
            ],
            "adhoc_filters": [combined_filter(), EXCLUDE_TOTAL_BEDROOM, period_filter("Oct-25")],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ".1f",
            "x_axis_label": "Bedroom Type",
            "y_axis_label": "Turnover Rate (%)",
        },
    },
}

DASHBOARD_TITLE = "Story 2: What is happening in Windsor's rental market?"

# width units sum to 12 per row, same grid convention as Story 1's dashboard.
LAYOUT = [
    ("ROW-kpi", [("kpi-vacancy", 3), ("kpi-rent", 3), ("kpi-turnover", 3), ("kpi-stock", 3)]),
    ("ROW-zone", [("rent-zone", 12)]),
    ("ROW-trends", [("rent-trend", 6), ("vacancy-trend", 6)]),
    ("ROW-turnover", [("turnover", 12)]),
]


def ensure_chart(session, headers, key: str, spec: dict) -> int:
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


def build_position_json(chart_ids: dict) -> dict:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [row_id for row_id, _ in LAYOUT],
            "parents": ["ROOT_ID"],
        },
    }

    for row_id, charts_in_row in LAYOUT:
        chart_node_ids = [f"CHART-{key}" for key, _ in charts_in_row]
        position[row_id] = {
            "type": "ROW",
            "id": row_id,
            "children": chart_node_ids,
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for (key, width), node_id in zip(charts_in_row, chart_node_ids):
            position[node_id] = {
                "type": "CHART",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "chartId": chart_ids[key],
                    "width": width,
                    "height": 50 if key.startswith("kpi") else 55,
                    "uuid": str(uuid.uuid4()),
                },
            }

    return position


def build_native_filters(chart_ids: dict) -> list:
    non_kpi_bedroom_charts = [
        chart_ids["rent-zone"],
        chart_ids["rent-trend"],
        chart_ids["vacancy-trend"],
        chart_ids["turnover"],
    ]
    return [
        {
            "id": f"NATIVE_FILTER-{uuid.uuid4().hex[:8]}",
            "name": "Zone",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_RENT_ZONE, "column": {"name": "zone_label"}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "type": "NATIVE_FILTER",
            "description": "",
            "chartsInScope": [chart_ids["rent-zone"]],
            "tabsInScope": [],
            "controlValues": {
                "enableEmptyFilter": False,
                "defaultToFirstItem": False,
                "multiSelect": True,
                "searchAllOptions": False,
                "inverseSelection": False,
            },
        },
        {
            "id": f"NATIVE_FILTER-{uuid.uuid4().hex[:8]}",
            "name": "Bedroom type",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_RENT_YOY, "column": {"name": "bedroom_type_label"}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "type": "NATIVE_FILTER",
            "description": "",
            "chartsInScope": non_kpi_bedroom_charts,
            "tabsInScope": [],
            "controlValues": {
                "enableEmptyFilter": False,
                "defaultToFirstItem": False,
                "multiSelect": True,
                "searchAllOptions": False,
                "inverseSelection": False,
            },
        },
    ]


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    """Creating a dashboard via POST /api/v1/dashboard/ does NOT populate
    the dashboard_slices join table from position_json's chartId
    references, even though position_json alone determines each chart's
    on-screen position -- confirmed directly against the live metadata
    database (a dashboard built this way had 0 dashboard_slices rows
    despite its charts rendering fine individually and its layout
    correctly referencing their ids). PUT /api/v1/chart/{id} with a
    "dashboards" field is the real, documented way to create that
    relational link; without it, the dashboard is empty."""
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": [dashboard_id]}
    )
    resp.raise_for_status()


def ensure_dashboard(session, headers, position_json: dict, native_filters: list) -> int:
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "published": True,
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps(
            {
                "native_filter_configuration": native_filters,
                "color_scheme": COLOR_SCHEME,
            }
        ),
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
        chart_id = ensure_chart(session, headers, key, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")

    position_json = build_position_json(chart_ids)
    native_filters = build_native_filters(chart_ids)
    dashboard_id = ensure_dashboard(session, headers, position_json, native_filters)
    print(f"Dashboard ready: id={dashboard_id}")

    for key, chart_id in chart_ids.items():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
