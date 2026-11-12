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
from setup_superset_dashboard import SUPERSET_URL, dataset_id, find_existing, get_session
from superset_compat import COLOR_SCHEME, finish_dashboard, upgrade_legacy_bars

DASHBOARD_ID = 3
DATASET_SEVERITY = dataset_id("v_story1_burden_severity")
DATASET_SEVERITY_BREAKDOWN = dataset_id("v_story1_burden_severity_breakdown")
# windsor_housing here, Superset's default on the shared server (superset_compat).

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

EXISTING_CHART_UPDATES = {
    2: {
        "description": "Share of owner and renter households spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census.",
    },
    3: {
        "description": "Share of renter households spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
    },
    4: {
        "description": "Share of owner households spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
    },
    5: {
        "description": "Number of Windsor households (owners and renters) spending 30% or more of income on shelter. StatCan 98-10-0252-01, 2021 Census -- warehouse.v_story1_burden_by_tenure.",
    },
    6: {
        "description": "Share of households in each 2020 income band spending 30% or more of income on shelter. Households with no computable ratio are excluded. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_income_band.",
        "viz_type": "echarts_timeseries_bar",
        "params": INCOME_BAND_BARS,
    },
    7: {
        "description": "Share of households of each type spending 30% or more of income on shelter. StatCan 98-10-0252-01, Windsor CMA, 2021 Census -- warehouse.v_story1_burden_by_household_type.",
        "viz_type": "echarts_timeseries_bar",
        "params": HOUSEHOLD_TYPE_BARS,
    },
}


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


def verify_native_filter_scope(
    session, headers, dashboard_id: int, excluded_chart_ids: set, tenure_scoped_chart_id: int
) -> None:
    """The 2 severity KPIs are, like the Renter/Owner Burden Rate KPIs
    (etl/fix_story1_tenure_filter_scope.py), fixed-per-tenure and must stay
    out of both native filters' chartsInScope -- same conflict would occur
    otherwise (each already has its own hardcoded tenure filter). Nothing
    adds them to chartsInScope, so this only verifies that's still true
    rather than silently assuming it.

    The new severity-breakdown chart is different: tenure is its groupby,
    not a hardcoded filter, so including it in the Tenure filter's scope
    is correct and useful (picking "Owner" narrows the stacked bar to just
    Owner, same mechanism the Zone/Bedroom-type filters already use
    elsewhere). Its dataset has no household_type column at all, though,
    so it must be added to Tenure only -- added here directly rather than
    left to be missed, since nothing else would add it."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", headers=headers)
    resp.raise_for_status()
    metadata = json.loads(resp.json()["result"]["json_metadata"])

    changed = False
    for f in metadata.get("native_filter_configuration", []):
        overlap = set(f["chartsInScope"]) & excluded_chart_ids
        if overlap:
            raise RuntimeError(f"Filter '{f['name']}' unexpectedly includes KPI chart(s) {overlap}")

        if f["name"] == "Tenure" and tenure_scoped_chart_id not in f["chartsInScope"]:
            f["chartsInScope"] = sorted(set(f["chartsInScope"]) | {tenure_scoped_chart_id})
            changed = True

    if changed:
        resp = session.put(
            f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}",
            headers=headers,
            json={"json_metadata": json.dumps(metadata)},
        )
        resp.raise_for_status()
        print(f"Tenure filter now also scoped to chart {tenure_scoped_chart_id} (severity breakdown).")

    print("Verified: no native filter includes the fixed-per-tenure KPI tiles.")


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = dict(EXISTING)
    for chart_id, update in EXISTING_CHART_UPDATES.items():
        update_existing_chart(session, headers, chart_id, update)
        print(f"Chart {chart_id}: labels and description updated.")
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
    print(f"Finished: {finish_dashboard(session, headers, DASHBOARD_ID)}")

    excluded_ids = {chart_ids["kpi-severity-renter"], chart_ids["kpi-severity-owner"]}
    verify_native_filter_scope(
        session, headers, DASHBOARD_ID, excluded_ids, chart_ids["severity-breakdown"]
    )

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{DASHBOARD_ID}/")
