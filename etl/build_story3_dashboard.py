"""
Build the Story 3 Superset dashboard ("Is Windsor building enough
housing?"): Windsor CMA housing starts vs completions by dwelling type,
supply per 1,000 households, and a ten-year trend, with a Year filter.

Built on the two Windsor views in sql/story3_views.sql
(v_story3_windsor_supply_annual, v_story3_windsor_supply_per_1000_households),
which come from StatCan table 34-10-0154-01 via
etl/extract_windsor_starts_completions.py -- Windsor-specific and monthly
from January 2016. The older Ontario/Canada views stay on Dashboard 1.

Year filter: single-select on year_label, defaulting to 2025 (the latest
full year) and required, never empty -- per docs/filter_standards.md rule
3, an empty selection would SUM every year into one meaningless total on
the KPI tiles and the dwelling-type chart. It is scoped only to those
charts: the trend charts use year as their own x-axis, so filtering them
to one year would collapse the trend (rule 4's reasoning, applied to
groupby rather than a hardcoded value).

Same viz types as the other story dashboards: "big_number_total" for KPI
tiles, "dist_bar" for bars (see etl/build_story2_dashboard.py's docstring
for why dist_bar), plus one markdown note on sources and caveats.

Requires both views registered as Superset datasets
(etl/register_superset_datasets.py) and Superset running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story3_dashboard.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

# Dataset ids, from etl/register_superset_datasets.py's own output.
DATASET_ANNUAL = 21  # v_story3_windsor_supply_annual
DATASET_PER_1000 = 22  # v_story3_windsor_supply_per_1000_households

COLOR_SCHEME = "windsor_housing"  # validated CVD-safe palette, docker/superset_config.py
DEFAULT_YEAR = "2025"


def eq_filter(column: str, value):
    return {
        "clause": "WHERE",
        "subject": column,
        "operator": "==",
        "comparator": value,
        "expressionType": "SIMPLE",
    }


def in_filter(column: str, values: list):
    return {
        "clause": "WHERE",
        "subject": column,
        "operator": "IN",
        "comparator": values,
        "expressionType": "SIMPLE",
    }


TOTAL_ONLY = eq_filter("dwelling_type", "Total")
EXCLUDE_TOTAL = {
    "clause": "WHERE",
    "subject": "dwelling_type",
    "operator": "!=",
    "comparator": "Total",
    "expressionType": "SIMPLE",
}
FLOWS = in_filter("activity", ["Starts", "Completions"])
FULL_YEARS = {"clause": "WHERE", "expressionType": "SQL", "sqlExpression": "NOT is_partial_year"}

UNITS = {"expressionType": "SQL", "sqlExpression": "SUM(units)", "label": "Units"}


def kpi(slice_name: str, description: str, activity: str, subheader: str) -> dict:
    return {
        "slice_name": slice_name,
        "description": description,
        "dataset_id": DATASET_ANNUAL,
        "viz_type": "big_number_total",
        "params": {
            "metric": {**UNITS, "label": activity},
            "adhoc_filters": [eq_filter("activity", activity), TOTAL_ONLY],
            "y_axis_format": ",d",
            "subheader": subheader,
        },
    }


CHARTS = {
    "kpi-starts": kpi(
        "Windsor Housing Starts",
        "Total units started in the selected year, Windsor CMA -- warehouse.v_story3_windsor_supply_annual.",
        "Starts",
        "units started in the selected year, Windsor CMA",
    ),
    "kpi-completions": kpi(
        "Windsor Housing Completions",
        "Total units completed in the selected year, Windsor CMA -- warehouse.v_story3_windsor_supply_annual.",
        "Completions",
        "units completed in the selected year, Windsor CMA",
    ),
    "kpi-under-construction": kpi(
        "Windsor Units Under Construction",
        "Units under construction at the end of the selected year (or its latest month) -- a stock, "
        "not a yearly sum -- warehouse.v_story3_windsor_supply_annual.",
        "Under Construction",
        "units under construction at year end",
    ),
    "kpi-per-1000": {
        "slice_name": "Windsor Starts per 1,000 Households",
        "description": (
            "Housing starts per 1,000 private households (2021 Census base, 165,665), full years only -- "
            "warehouse.v_story3_windsor_supply_per_1000_households. Blank for a partial year."
        ),
        "dataset_id": DATASET_PER_1000,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "AVG(starts_per_1000_households)",
                "label": "Starts per 1,000 Households",
            },
            "adhoc_filters": [],
            "y_axis_format": ".1f",
            "subheader": "starts per 1,000 households (2021 Census base), full years only",
        },
    },
    "by-dwelling": {
        "slice_name": "Starts vs Completions by Dwelling Type (Selected Year)",
        "description": "Windsor CMA, the year chosen in the Year filter -- warehouse.v_story3_windsor_supply_annual.",
        "dataset_id": DATASET_ANNUAL,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["dwelling_type"],
            "columns": ["activity"],
            "metrics": [UNITS],
            "adhoc_filters": [FLOWS, EXCLUDE_TOTAL],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_label": "Dwelling Type",
            "y_axis_label": "Units",
        },
    },
    "trend": {
        "slice_name": "Starts vs Completions by Year (2016-2025)",
        "description": "Windsor CMA, all dwelling types, full years only -- warehouse.v_story3_windsor_supply_annual.",
        "dataset_id": DATASET_ANNUAL,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["year_label"],
            "columns": ["activity"],
            "metrics": [UNITS],
            "adhoc_filters": [FLOWS, TOTAL_ONLY, FULL_YEARS],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_label": "Year",
            "y_axis_label": "Units",
        },
    },
    "per-1000": {
        "slice_name": "Starts and Completions per 1,000 Households by Year",
        "description": (
            "Windsor CMA, full years, against the 2021 Census private-household count -- "
            "warehouse.v_story3_windsor_supply_per_1000_households."
        ),
        "dataset_id": DATASET_PER_1000,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["year_label"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(starts_per_1000_households)",
                    "label": "Starts per 1,000 Households",
                },
                {
                    "expressionType": "SQL",
                    "sqlExpression": "AVG(completions_per_1000_households)",
                    "label": "Completions per 1,000 Households",
                },
            ],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ".1f",
            "x_axis_label": "Year",
            "y_axis_label": "Units per 1,000 Households",
        },
    },
    "starts-mix": {
        "slice_name": "Housing Starts by Dwelling Type and Year (2016-2025)",
        "description": "Windsor CMA, full years, stacked by dwelling type -- warehouse.v_story3_windsor_supply_annual.",
        "dataset_id": DATASET_ANNUAL,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["year_label"],
            "columns": ["dwelling_type"],
            "metrics": [UNITS],
            "adhoc_filters": [eq_filter("activity", "Starts"), EXCLUDE_TOTAL, FULL_YEARS],
            "row_limit": 100,
            "color_scheme": COLOR_SCHEME,
            "bar_stacked": True,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_label": "Year",
            "y_axis_label": "Units Started",
        },
    },
}

SOURCE_NOTE_MARKDOWN = """**About this data.** Windsor CMA housing starts, completions and units under
construction come from CMHC's Starts and Completions Survey as published by
Statistics Canada (table 34-10-0154-01, monthly), summed to calendar years.
Units under construction are a count at year end, not a yearly total. The
per-1,000-households rate divides by the 2021 Census count of private
households (165,665) for every year, since no annual household estimate is
available, so read it as a trend against a fixed base. The current year is
partial and is labelled with the months it covers.
"""

DASHBOARD_TITLE = "Story 3: Is Windsor building enough housing?"

# Top-to-bottom grid entries: a HEADER-* id with its text, a MARKDOWN-* id
# with its code, or a ROW-* id with (chart key, width) pairs -- widths sum
# to 12 per row.
LAYOUT = [
    ("HEADER-kpi", "Windsor Supply at a Glance (Selected Year)"),
    (
        "ROW-kpi",
        [("kpi-starts", 3), ("kpi-completions", 3), ("kpi-under-construction", 3), ("kpi-per-1000", 3)],
    ),
    ("HEADER-dwelling", "Starts vs Completions by Dwelling Type"),
    ("ROW-dwelling", [("by-dwelling", 12)]),
    ("HEADER-trend", "Ten-Year Trend (2016-2025)"),
    ("ROW-trend", [("trend", 12)]),
    ("ROW-per-1000", [("per-1000", 12)]),
    ("ROW-starts-mix", [("starts-mix", 12)]),
    ("MARKDOWN-source", SOURCE_NOTE_MARKDOWN),
]

KPI_HEIGHT = 25
CHART_HEIGHT = 55
MARKDOWN_HEIGHT = 25


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


def build_position_json(chart_ids: dict) -> dict:
    grid_children = []
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": grid_children, "parents": ["ROOT_ID"]},
    }

    for node_id, content in LAYOUT:
        if node_id.startswith("HEADER-"):
            grid_children.append(node_id)
            position[node_id] = {
                "type": "HEADER",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"text": content, "headerSize": "MEDIUM_HEADER", "background": "BACKGROUND_TRANSPARENT"},
            }
            continue

        if node_id.startswith("MARKDOWN-"):
            # A markdown component has to sit inside a row, like a chart.
            row_id = f"ROW-{node_id}"
            grid_children.append(row_id)
            position[row_id] = {
                "type": "ROW",
                "id": row_id,
                "children": [node_id],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            position[node_id] = {
                "type": "MARKDOWN",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {"width": 12, "height": MARKDOWN_HEIGHT, "code": content, "uuid": str(uuid.uuid4())},
            }
            continue

        grid_children.append(node_id)
        chart_node_ids = [f"CHART-{key}" for key, _ in content]
        position[node_id] = {
            "type": "ROW",
            "id": node_id,
            "children": chart_node_ids,
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for (key, width), chart_node_id in zip(content, chart_node_ids):
            position[chart_node_id] = {
                "type": "CHART",
                "id": chart_node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", node_id],
                "meta": {
                    "chartId": chart_ids[key],
                    "width": width,
                    "height": KPI_HEIGHT if key.startswith("kpi") else CHART_HEIGHT,
                    "uuid": str(uuid.uuid4()),
                },
            }

    return position


def build_native_filters(chart_ids: dict) -> list:
    year_scoped = [
        chart_ids["kpi-starts"],
        chart_ids["kpi-completions"],
        chart_ids["kpi-under-construction"],
        chart_ids["kpi-per-1000"],
        chart_ids["by-dwelling"],
    ]
    return [
        {
            "id": f"NATIVE_FILTER-{uuid.uuid4().hex[:8]}",
            "name": "Year",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_ANNUAL, "column": {"name": "year_label"}}],
            "defaultDataMask": {
                "extraFormData": {"filters": [{"col": "year_label", "op": "IN", "val": [DEFAULT_YEAR]}]},
                "filterState": {"value": [DEFAULT_YEAR], "label": DEFAULT_YEAR},
                "ownState": {},
            },
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "type": "NATIVE_FILTER",
            "description": "Year shown on the KPI tiles and the dwelling-type chart.",
            "chartsInScope": year_scoped,
            "tabsInScope": [],
            "controlValues": {
                # Required and single-select: an empty or multi-year
                # selection would sum several years into one KPI value.
                "enableEmptyFilter": True,
                "defaultToFirstItem": False,
                "multiSelect": False,
                "searchAllOptions": False,
                "inverseSelection": False,
                "sortAscending": False,
            },
        },
    ]


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    """POST /api/v1/dashboard/ doesn't fill the dashboard_slices join
    table from position_json -- see etl/build_story2_dashboard.py's
    function of the same name for how that was found."""
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
            {"native_filter_configuration": native_filters, "color_scheme": COLOR_SCHEME}
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
        chart_ids[key] = ensure_chart(session, headers, spec)
        print(f"Chart ready: {spec['slice_name']} (id={chart_ids[key]})")

    dashboard_id = ensure_dashboard(
        session, headers, build_position_json(chart_ids), build_native_filters(chart_ids)
    )
    print(f"Dashboard ready: id={dashboard_id}")

    for chart_id in chart_ids.values():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
