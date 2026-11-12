"""
Finalize Story 1's dashboard layout: organize the existing charts into
named sections (Key Figures, Burden by Household Income, Burden by
Household Type, How Far Over the 30% Line, Validation and Data Notes),
add 2 KPI tiles and a stacked bar on warehouse.v_story1_burden_severity
(and _breakdown), add a validation and data-notes markdown block, and
resize the income-band/household-type/tenure charts to full width.

Review pass (supervisor comments):
  - Plain-language section headers instead of internal names ("Gap KPIs").
  - Metric labels say what the number is ("Share spending 30%+ on
    shelter"), not "Burden Rate (%)" on an axis already shown in percent.
  - The 30%-to-under-100% band is no longer called "severe": it starts
    just above the 30% line. The remainder of the 30%+ group is labelled
    as households spending 100% or more of income on shelter (derived;
    see sql/story1_views.sql).
  - Every chart has a description saying what it measures and its source.
  - A data note explains suppressed values and StatCan's rounding.

Renamed charts are found by their previous name (legacy_names), so a
re-run updates them in place instead of creating duplicates.

Requires warehouse.v_story1_burden_severity already registered as a
Superset dataset (etl/register_superset_datasets.py) and Superset
running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\finalize_story1_layout.py
"""

import json
import uuid

from dashboard_tabs import add_tabs
from setup_superset_dashboard import CHART_NAME as TENURE_BAR_NAME
from setup_superset_dashboard import SUPERSET_URL, dataset_id, find_existing, get_session
from superset_compat import COLOR_SCHEME, finish_dashboard, named, prefix_names, upgrade_legacy_bars

DASHBOARD_TITLE = named("Story 1: Who faces the greatest affordability pressure?")
# A fixed URL name: the website, the token API and the embedding script use it
# instead of the dashboard id, which differs on every Superset.
DASHBOARD_SLUG = "windsor-story-1"
DATASET_TENURE = dataset_id("v_story1_burden_by_tenure")
DATASET_INCOME_BAND = dataset_id("v_story1_burden_by_income_band")
DATASET_HOUSEHOLD_TYPE = dataset_id("v_story1_burden_by_household_type")
DATASET_SEVERITY = dataset_id("v_story1_burden_severity")
DATASET_SEVERITY_BREAKDOWN = dataset_id("v_story1_burden_severity_breakdown")
# windsor_housing here, Superset's default on the shared server (superset_compat).

NEW_CHARTS = {
    "kpi-severity-renter": {
        "slice_name": "Burdened Renters Spending 30% to Under 100%",
        "legacy_names": ["Renter Households in Severe Range (30-99%)"],
        "description": "Of renter households already spending 30%+ of income on shelter, the share spending 30% to under 100%. The rest spend 100% or more. StatCan 98-10-0252-01, 2021 Census -- warehouse.v_story1_burden_severity.",
        "dataset_id": DATASET_SEVERITY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(severe_pct_of_burdened) / 100.0",
                "label": "Share spending 30% to under 100%",
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
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "of burdened renters spend 30% to under 100% of income on shelter",
            "color_scheme": "windsor_housing",
        },
    },
    "kpi-severity-owner": {
        "slice_name": "Burdened Owners Spending 30% to Under 100%",
        "legacy_names": ["Owner Households in Severe Range (30-99%)"],
        "description": "Of owner households already spending 30%+ of income on shelter, the share spending 30% to under 100%. The rest spend 100% or more. StatCan 98-10-0252-01, 2021 Census -- warehouse.v_story1_burden_severity.",
        "dataset_id": DATASET_SEVERITY,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(severe_pct_of_burdened) / 100.0",
                "label": "Share spending 30% to under 100%",
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
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subtitle": "of burdened owners spend 30% to under 100% of income on shelter",
            "color_scheme": "windsor_housing",
        },
    },
    "severity-breakdown": {
        "slice_name": "How Far Over the 30% Line? Burdened Households by Tenure",
        "legacy_names": ["Severity Breakdown of Burdened Households by Tenure"],
        "description": (
            "Each tenure's burdened households split into those spending 30% to under 100% of "
            "income on shelter and those spending 100% or more (derived: 30%+ minus the "
            "30%-to-under-100% band). Each bar sums to 100%. StatCan 98-10-0252-01, 2021 Census -- "
            "warehouse.v_story1_burden_severity_breakdown."
        ),
        "dataset_id": DATASET_SEVERITY_BREAKDOWN,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["tenure"],
            "columns": ["category"],
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "MAX(pct_of_burdened) / 100.0",
                    "label": "Share of Burdened Households",
                }
            ],
            "adhoc_filters": [],
            "row_limit": 10,
            "stack": True,
            "color_scheme": COLOR_SCHEME,
            "show_legend": True,
            "rich_tooltip": True,
            "y_axis_format": ".1%",
            "x_axis_label": "Tenure",
            "y_axis_label": "Share of Burdened Households",
        },
    },
}

# The legacy dist_bar charts are drawn with the ECharts bar chart (superset_compat).
upgrade_legacy_bars(NEW_CHARTS)

VALIDATION_MARKDOWN = """**Validated against StatCan's own published figures.** The renter (34.8%)
and owner (10.9%) burden rates above were reproduced from two StatCan
products -- the shelter-cost-to-income ratio table (98-10-0252-01) this
dashboard queries, and the Census Profile's own rates (98-401-X2021002,
items 1484/1492) -- and match exactly. Reconciliation: `docs/story1_validation.md`.

**Data notes**

- **Suppressed values:** StatCan suppresses (symbol "x") 40 cells in
  Windsor's table. All 40 are the median or average *income* of
  "Not applicable" households (zero or negative income). None of the
  household counts on this dashboard is suppressed.
- **Not applicable households** (zero or negative income, or living on a
  farm they operate) have no shelter-cost ratio and are left out of every
  burden-rate denominator, as StatCan does.
- **Rounding:** StatCan rounds every count to a multiple of 5, so totals
  can differ slightly (28,740 burdened by tenure vs 28,745 in the total row).
- **100% or more** is derived (30%+ minus the 30%-to-under-100% band);
  StatCan does not publish it as its own row.
- **Year:** 2021 Census, income from 2020. One snapshot, not a trend.
"""

# Review pass on the original Story 1 charts (built before this script):
# plain metric labels and a description on every chart. Applied as a merge
# into each chart's existing params, so nothing else about the chart changes.
# Charts 6 and 7 were first built in the Superset UI as dist_bar charts; their
# settings are kept here so they can be rebuilt as ECharts bars (and on
# another Superset). Burden falls as income rises, so sorting by the rate
# keeps the income bands in order.
INCOME_BAND_BARS = upgrade_legacy_bars({"c": {"viz_type": "dist_bar", "params": {
    "groupby": [
        "income_band"
    ],
    "metrics": [
        {
            "expressionType": "SQL",
            "label": "Share spending 30%+ on shelter",
            "sqlExpression": "MAX(burden_rate_pct) / 100.0"
        }
    ],
    "adhoc_filters": [],
    "order_desc": True,
    "row_limit": 15,
    "y_axis_format": ".1%",
    "show_legend": False,
    "x_axis_label": "Household income (2020)",
    "y_axis_label": "Share spending 30%+ on shelter"
}}}, {"c": {"xAxisLabelRotation": 45, "x_axis_title": ""}})["c"]["params"]
HOUSEHOLD_TYPE_BARS = upgrade_legacy_bars(
    {"c": {"viz_type": "dist_bar", "params": {
        "groupby": [
            "household_type"
        ],
        "metrics": [
            {
                "expressionType": "SQL",
                "label": "Share spending 30%+ on shelter",
                "sqlExpression": "MAX(burden_rate_pct) / 100.0"
            }
        ],
        "adhoc_filters": [
            {
                "clause": "WHERE",
                "subject": "household_type_key",
                "operator": "!=",
                "comparator": "1",
                "expressionType": "SIMPLE"
            }
        ],
        "order_desc": True,
        "row_limit": 20,
        "y_axis_format": ".1%",
        "show_legend": False,
        "x_axis_label": "Household type",
        "y_axis_label": "Share spending 30%+ on shelter"
    }}},
    {"c": {"orientation": "horizontal"}},
)["c"]["params"]

# The tenure KPIs and the income-band and household-type charts were first
# built in the Superset UI; they are defined here so the dashboard can be
# rebuilt on any Superset (the university's shared one included). The tenure
# bar (chart 2) is built by etl/setup_superset_dashboard.py.
BASE_CHARTS = {
    "kpi-renter": {
        "slice_name": "Renter Burden Rate",
        "description": "Share of renter households spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
        "dataset_id": DATASET_TENURE,
        "viz_type": "big_number_total",
        "params": {
            "metric": {"expressionType": "SQL", "sqlExpression": "MAX(burden_rate_pct) / 100.0", "label": "Renter Burden Rate"},
            "adhoc_filters": [{"clause": "WHERE", "subject": "tenure", "operator": "==", "comparator": "Renter", "expressionType": "SIMPLE"}],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            # "subtitle" in Superset 4 and later, "subheader" before.
            "subtitle": "of renter households spend 30%+ of income on shelter",
            "subheader": "of renter households spend 30%+ of income on shelter",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-owner": {
        "slice_name": "Owner Burden Rate",
        "description": "Share of owner households spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
        "dataset_id": DATASET_TENURE,
        "viz_type": "big_number_total",
        "params": {
            "metric": {"expressionType": "SQL", "sqlExpression": "MAX(burden_rate_pct) / 100.0", "label": "Owner Burden Rate"},
            "adhoc_filters": [{"clause": "WHERE", "subject": "tenure", "operator": "==", "comparator": "Owner", "expressionType": "SIMPLE"}],
            "y_axis_format": ".1%",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            # "subtitle" in Superset 4 and later, "subheader" before.
            "subtitle": "of owner households spend 30%+ of income on shelter",
            "subheader": "of owner households spend 30%+ of income on shelter",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-total": {
        "slice_name": "Households Spending 30%+ on Shelter",
        "description": "Number of Windsor households (owners and renters) spending 30% or more of income on shelter. StatCan 98-10-0252-01, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
        "dataset_id": DATASET_TENURE,
        "viz_type": "big_number_total",
        "params": {
            "metric": {"expressionType": "SIMPLE", "column": {"column_name": "burdened_households"}, "aggregate": "SUM", "label": "Burdened Households"},
            "adhoc_filters": [],
            "y_axis_format": ",d",
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            # "subtitle" in Superset 4 and later, "subheader" before.
            "subtitle": "Windsor households, owners + renters combined",
            "subheader": "Windsor households, owners + renters combined",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "income-band": {
        "slice_name": "Burden Rate by Income Band",
        "description": "Share of households in each 2020 income band spending 30% or more of income on shelter. Households with no computable ratio are excluded. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_income_band.",
        "dataset_id": DATASET_INCOME_BAND,
        "viz_type": "echarts_timeseries_bar",
        "params": INCOME_BAND_BARS,
    },
    "household-type": {
        "slice_name": "Burden Rate by Household Type",
        "description": "Share of households of each type spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_household_type.",
        "dataset_id": DATASET_HOUSEHOLD_TYPE,
        "viz_type": "echarts_timeseries_bar",
        "params": HOUSEHOLD_TYPE_BARS,
    },
}

TENURE_BAR_DESCRIPTION = (
    "Share of owner and renter households spending 30% or more of income on shelter. "
    "StatCan 98-10-0252-01, Windsor CMA, 2021 Census."
)


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
    for old_name in spec.get("legacy_names", []):
        if existing:
            break
        existing = find_existing(session, headers, "chart", "slice_name", old_name)
    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/chart/{existing}", headers=headers, json=body)
        resp.raise_for_status()
        return existing
    resp = session.post(f"{SUPERSET_URL}/api/v1/chart/", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


def update_existing_chart(session, headers, chart_id: int, update: dict) -> None:
    """Merge a description and selected params into an existing chart,
    leaving the rest of its params as they are. With a new viz_type the
    params are replaced instead (another chart type's keys would linger)."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers)
    resp.raise_for_status()
    params = json.loads(resp.json()["result"]["params"] or "{}")
    if "viz_type" in update:
        params = {"viz_type": update["viz_type"], **update["params"], "color_scheme": COLOR_SCHEME}
    else:
        params.update(update.get("params", {}))
    body = {"params": json.dumps(params)}
    if "viz_type" in update:
        body["viz_type"] = update["viz_type"]
    if "description" in update:
        body["description"] = update["description"]
    resp = session.put(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json=body)
    resp.raise_for_status()


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": [dashboard_id]}
    )
    resp.raise_for_status()


def chart_node(node_id: str, parent_id: str, chart_id: int, width: int, height: int = 25) -> dict:
    # Default height (not used by any chart that passes its own, e.g. the
    # width=12 bar/table rows below) -- 25 is for big_number_total KPI
    # tiles specifically. Was 50: that left a large empty gap above the
    # number inside every KPI card, confirmed visually, not a guess.
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


# One screen per tab (etl/dashboard_tabs.py).
TABS = [
    ("TAB-tenure", "Renters vs Owners", ["HEADER-gap-kpis", "ROW-kpi", "ROW-tenure-bar"]),
    ("TAB-income", "By Income", ["HEADER-income", "ROW-income"]),
    ("TAB-household", "By Household Type", ["HEADER-household", "ROW-household"]),
    ("TAB-severity", "How Far Over 30%", ["HEADER-severity", "ROW-severity", "ROW-severity-breakdown"]),
    ("TAB-notes", "Data Notes", ["HEADER-validation", "ROW-validation"]),
]


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
                "ROW-severity-breakdown",
                "HEADER-validation",
                "ROW-validation",
            ],
            "parents": ["ROOT_ID"],
        },
    }

    position["HEADER-gap-kpis"] = header_node("HEADER-gap-kpis", "Key Figures: Renters vs Owners")
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

    position["HEADER-income"] = header_node("HEADER-income", "Burden by Household Income")
    position["ROW-income"] = row_node("ROW-income", ["CHART-income-band"])
    position["CHART-income-band"] = chart_node(
        "CHART-income-band", "ROW-income", chart_ids["income-band"], 12, 55
    )

    position["HEADER-household"] = header_node("HEADER-household", "Burden by Household Type")
    position["ROW-household"] = row_node("ROW-household", ["CHART-household-type"])
    position["CHART-household-type"] = chart_node(
        "CHART-household-type", "ROW-household", chart_ids["household-type"], 12, 55
    )

    position["HEADER-severity"] = header_node("HEADER-severity", "How Far Over the 30% Line?")
    position["ROW-severity"] = row_node(
        "ROW-severity", ["CHART-severity-renter", "CHART-severity-owner"]
    )
    position["CHART-severity-renter"] = chart_node(
        "CHART-severity-renter", "ROW-severity", chart_ids["kpi-severity-renter"], 6
    )
    position["CHART-severity-owner"] = chart_node(
        "CHART-severity-owner", "ROW-severity", chart_ids["kpi-severity-owner"], 6
    )

    position["ROW-severity-breakdown"] = row_node(
        "ROW-severity-breakdown", ["CHART-severity-breakdown"]
    )
    position["CHART-severity-breakdown"] = chart_node(
        "CHART-severity-breakdown", "ROW-severity-breakdown", chart_ids["severity-breakdown"], 12, 55
    )

    position["HEADER-validation"] = header_node("HEADER-validation", "Validation and Data Notes")
    position["ROW-validation"] = row_node("ROW-validation", ["MARKDOWN-validation"])
    position["MARKDOWN-validation"] = markdown_node(
        "MARKDOWN-validation", "ROW-validation", VALIDATION_MARKDOWN, height=60
    )

    return add_tabs(position, TABS)


# Each filter reaches only the charts whose data has its column and whose own
# filters do not fix it: the Renter/Owner tiles and the severity tiles are
# fixed to one tenure, and the tenure bar is fixed to all household types.
# Every other chart is excluded explicitly, since Superset applies a filter to
# every chart its scope does not exclude.
FILTERS = [
    ("NATIVE_FILTER-story1-tenure", "Tenure", "DATASET_TENURE", "tenure",
     ["tenure-bar", "kpi-total", "severity-breakdown"]),
    ("NATIVE_FILTER-story1-household", "Household Type", "DATASET_HOUSEHOLD_TYPE", "household_type",
     ["household-type"]),
]


def build_native_filters(chart_ids: dict) -> list:
    filters = []
    for filter_id, name, dataset_var, column, keys in FILTERS:
        in_scope = sorted(chart_ids[k] for k in keys)
        filters.append({
            "id": filter_id,
            "name": name,
            "filterType": "filter_select",
            "targets": [{"datasetId": globals()[dataset_var], "column": {"name": column}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"],
                      "excluded": sorted(c for c in chart_ids.values() if c not in in_scope)},
            "type": "NATIVE_FILTER",
            "description": "",
            "chartsInScope": in_scope,
            "tabsInScope": [],
            "controlValues": {"enableEmptyFilter": False, "defaultToFirstItem": False, "multiSelect": True,
                              "searchAllOptions": False, "inverseSelection": False},
        })
    return filters


def ensure_dashboard(session, headers, position_json: dict, chart_ids: dict) -> int:
    """Create the dashboard if this Superset does not have it yet, else
    update it; keeps whatever else is stored in its metadata."""
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    metadata = {}
    if existing:
        current = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers)
        current.raise_for_status()
        metadata = json.loads(current.json()["result"]["json_metadata"] or "{}")
    metadata["native_filter_configuration"] = build_native_filters(chart_ids)
    metadata["color_scheme"] = COLOR_SCHEME
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": DASHBOARD_SLUG,
        "published": True,
        "position_json": json.dumps(position_json),
        "json_metadata": json.dumps(metadata),
    }
    if existing:
        session.put(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers, json=body).raise_for_status()
        return existing
    resp = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")
    charts = prefix_names({**BASE_CHARTS, **NEW_CHARTS})

    chart_ids = {}
    tenure_bar = find_existing(session, headers, "chart", "slice_name", named(TENURE_BAR_NAME))
    if not tenure_bar:
        raise LookupError("The tenure bar chart is missing; run etl/setup_superset_dashboard.py first")
    update_existing_chart(session, headers, tenure_bar, {"description": TENURE_BAR_DESCRIPTION})
    chart_ids["tenure-bar"] = tenure_bar
    for key, spec in charts.items():
        chart_ids[key] = ensure_chart(session, headers, spec)
        print(f"Chart ready: {spec['slice_name']} (id={chart_ids[key]})")

    dashboard_id = ensure_dashboard(session, headers, build_position_json(chart_ids), chart_ids)
    for chart_id in chart_ids.values():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Dashboard ready: id={dashboard_id}, {len(chart_ids)} charts, 5 tabs.")
    print(f"Finished: {finish_dashboard(session, headers, dashboard_id)}")
    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{DASHBOARD_SLUG}/")
