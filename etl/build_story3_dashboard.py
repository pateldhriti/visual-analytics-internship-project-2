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

from dashboard_tabs import add_tabs
from setup_superset_dashboard import SUPERSET_URL, add_chart_to_dashboard, dataset_id, find_existing, get_session
from superset_compat import COLOR_SCHEME, finish_dashboard, named, prefix_names, upgrade_legacy_bars

# Dataset ids, from etl/register_superset_datasets.py's own output.
DATASET_ANNUAL = dataset_id("v_story3_windsor_supply_annual")
DATASET_PER_1000 = dataset_id("v_story3_windsor_supply_per_1000_households")
DATASET_PERIODS = dataset_id("v_story3_period_comparison")

# windsor_housing here, Superset's default on the shared server (superset_compat).
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
    "period-mix": {
        "slice_name": "What Windsor Starts: Dwelling Mix, 2016-2020 vs 2021-2025",
        "description": (
            "Share of homes started by dwelling type, five years before and from 2020. "
            "warehouse.v_story3_period_comparison."
        ),
        "dataset_id": DATASET_PERIODS,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": "period",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(avg_units_per_year)", "label": "Homes started a year"}],
            "groupby": ["dwelling_type"],
            "adhoc_filters": [eq_filter("activity", "Starts"), EXCLUDE_TOTAL],
            "stack": "Expand",
            "orientation": "horizontal",
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_value": False,  # the labels showed only the 100% totals, cut off at the edge
            "show_legend": True,
            "legendOrientation": "top",
            "rich_tooltip": True,
            "y_axis_format": ".0%",
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_sort_asc": False,
        },
    },
    "period-totals": {
        "slice_name": "Homes a Year: 2016-2020 vs 2021-2025",
        "description": (
            "Average homes started and completed a year in Windsor, all dwelling types, 2016-2020 and "
            "2021-2025. warehouse.v_story3_period_comparison."
        ),
        "dataset_id": DATASET_PERIODS,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": "activity",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(avg_units_per_year)", "label": "Homes a year"}],
            "groupby": ["period"],
            "adhoc_filters": [TOTAL_ONLY],
            "row_limit": 50,
            "color_scheme": COLOR_SCHEME,
            "show_value": True,
            "show_legend": True,
            "legendOrientation": "top",
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_title": "",
            "y_axis_title": "",
            "truncateYAxis": True,
            "y_axis_bounds": [0, 1800],
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

# The legacy dist_bar charts are drawn with the ECharts bar chart (superset_compat).
upgrade_legacy_bars(CHARTS)

# Same order and colours on both period charts: earlier period grey, later blue.
PERIOD_COLORS = {"2016 to 2020": "#aab6c8", "2021 to 2025": "#2a78d6"}

PERIODS_MARKDOWN = (
    """**What changed after 2020.** Windsor started **1,520 homes a year** in 2021-2025, up from
**1,261** in 2016-2020 (+21%), and completed **1,489 a year**, up from **1,133** (+31%).

**What it builds changed more.** Apartments went from **20% of homes started to 54%**, while
single-detached starts fell from **677 a year to 455**. Most new supply is now rental-type
apartments rather than houses, which fits the recovery in rental vacancy from 2024 (Story 4).

*Five full calendar years each; StatCan 34-10-0154-01.*
""",
    34,
)

SOURCE_NOTE_MARKDOWN = """**About this data.** Windsor CMA housing starts, completions and units under
construction come from CMHC's Starts and Completions Survey as published by
Statistics Canada (table 34-10-0154-01, monthly), summed to calendar years.
Units under construction are a count at year end, not a yearly total. The
per-1,000-households rate divides by the 2021 Census count of private
households (165,665) for every year, since no annual household estimate is
available, so read it as a trend against a fixed base. The current year is
partial and is labelled with the months it covers.
"""

DASHBOARD_TITLE = named("Story 3: Is Windsor building enough housing?")
# A fixed URL name: the website, the token API and the embedding script
# use it instead of the dashboard id, which differs on every Superset.
DASHBOARD_SLUG = "windsor-story-3"

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
    ("HEADER-periods", "Before vs From 2020: Five Years Each"),
    ("ROW-periods", [("period-totals", 6), ("period-mix", 6)]),
    ("MARKDOWN-periods", PERIODS_MARKDOWN),
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


# One screen per tab (etl/dashboard_tabs.py).
TABS = [
    ("TAB-glance", "At a Glance", ["HEADER-kpi", "ROW-kpi", "HEADER-dwelling", "ROW-dwelling"]),
    ("TAB-trend", "Ten-Year Trend", ["HEADER-trend", "ROW-trend", "ROW-per-1000"]),
    ("TAB-periods", "Before vs From 2020", ["HEADER-periods", "ROW-periods", "ROW-MARKDOWN-periods"]),
    ("TAB-mix", "Mix and Sources", ["ROW-starts-mix", "ROW-MARKDOWN-source"]),
]


# Shorter titles on the dashboard for the KPI tiles: the Year filter's badge
# takes part of the title bar, which cut the full names off.
TITLE_OVERRIDES = {
    "kpi-starts": "Homes started",
    "kpi-completions": "Homes completed",
    "kpi-under-construction": "Under construction",
    "kpi-per-1000": "Starts per 1,000 households",
}
# Taller than CHART_HEIGHT where a chart is alone in its tab.
HEIGHTS = {"starts-mix": 72}


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
            code, height = content if isinstance(content, tuple) else (content, MARKDOWN_HEIGHT)
            position[node_id] = {
                "type": "MARKDOWN",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {"width": 12, "height": height, "code": code, "uuid": str(uuid.uuid4())},
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
                    "height": HEIGHTS.get(key, KPI_HEIGHT if key.startswith("kpi") else CHART_HEIGHT),
                    "uuid": str(uuid.uuid4()),
                    **({"sliceNameOverride": TITLE_OVERRIDES[key]} if key in TITLE_OVERRIDES else {}),
                },
            }

    return add_tabs(position, TABS)


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
            # Every other chart is excluded explicitly: the ECharts bar charts
            # apply any filter whose scope includes them (the old dist_bar
            # charts ignored it), which cut the ten-year charts to one year.
            "scope": {
                "rootPath": ["ROOT_ID"],
                "excluded": sorted(cid for cid in chart_ids.values() if cid not in year_scoped),
            },
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
    add_chart_to_dashboard(session, headers, chart_id, dashboard_id)


def ensure_dashboard(session, headers, position_json: dict, native_filters: list, chart_ids: dict) -> int:
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    # Merge into the stored metadata and write the cross-filter settings in
    # the shape Superset's frontend computes. Replacing the metadata with
    # only the filters and colours made an anonymous viewer's browser try to
    # save the missing keys on load; the save fails with 401 and Superset
    # then shows its login page instead of the dashboard.
    metadata = {}
    if existing:
        current = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers)
        current.raise_for_status()
        metadata = json.loads(current.json()["result"]["json_metadata"] or "{}")
    all_ids = sorted(chart_ids.values())
    no_cross_filter = {"scope": {"rootPath": ["ROOT_ID"], "excluded": all_ids}, "chartsInScope": []}
    metadata.update(
        {
            "native_filter_configuration": native_filters,
            "color_scheme": COLOR_SCHEME,
            # Every bar chart can emit cross-filters; a click filters nothing.
            # finish_dashboard() sets the scheme's colours.
            "chart_configuration": {
                str(chart_ids[key]): {"id": chart_ids[key], "crossFilters": no_cross_filter}
                for key, spec in CHARTS.items()
                if spec["viz_type"].startswith("echarts")
            },
            "label_colors": PERIOD_COLORS,
            "global_chart_configuration": no_cross_filter,
            "cross_filters_enabled": True,
        }
    )
    for key, default in (
        ("shared_label_colors", {}),
        ("label_colors", {}),
        ("timed_refresh_immune_slices", []),
        ("expanded_slices", {}),
        ("refresh_frequency", 0),
    ):
        metadata.setdefault(key, default)
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": DASHBOARD_SLUG,
        "published": True,
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps(metadata),
    }

    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers, json=body)
        resp.raise_for_status()
        return existing

    resp = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


if __name__ == "__main__":
    prefix_names(CHARTS)
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = {}
    for key, spec in CHARTS.items():
        chart_ids[key] = ensure_chart(session, headers, spec)
        print(f"Chart ready: {spec['slice_name']} (id={chart_ids[key]})")

    dashboard_id = ensure_dashboard(
        session, headers, build_position_json(chart_ids), build_native_filters(chart_ids), chart_ids
    )
    print(f"Dashboard ready: id={dashboard_id}")

    for chart_id in chart_ids.values():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"Finished: {finish_dashboard(session, headers, dashboard_id)}")
    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
