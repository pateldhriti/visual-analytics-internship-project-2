"""
Build the Story 5 Superset dashboard ("How do affordability, rental
conditions, and supply fit together?"): one headline conclusion from each
of Stories 1-4, each as a single chart with its key insight beside it,
plus a short combined reading at the top.

    Story 1  Burdened households by tenure        pie   (v_story1_burden_by_tenure)
    Story 2  Rental stock by zone                 pie   (v_story2_zone_snapshot)
    Story 3  2025 housing starts by dwelling type pie   (v_story3_windsor_supply_annual)
    Story 4  2-bedroom rent, Windsor vs peers     bar   (v_story4_rent_comparison)

Stories 1-3 are pies because each conclusion is a share of a whole (the
slices add up to all burdened households, all rental units, all 2025
starts). Story 4's conclusion is a ranking -- Windsor has the lowest rent
of 5 cities -- which isn't parts of a whole, so it stays a bar chart; a
pie of 5 rents would show each city's "share" of a sum that means nothing.

No new SQL: every chart reads a view another story dashboard already
uses, so the figures here can't drift from the dashboards they summarise.
The charts are new chart objects, though, not the story dashboards' own,
so restyling one (as a pie) doesn't change the story dashboard it came from.

The React Story 5 page shows static images of these four charts
(etl/render_story5_snapshots.py) with the same key insights.

Requires the 4 datasets registered (etl/register_superset_datasets.py)
and Superset running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story5_dashboard.py
"""

import json
import uuid

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

# Dataset ids, from etl/register_superset_datasets.py's own output.
DATASET_BURDEN_BY_TENURE = 5  # v_story1_burden_by_tenure
DATASET_ZONE_SNAPSHOT = 19  # v_story2_zone_snapshot
DATASET_SUPPLY_ANNUAL = 21  # v_story3_windsor_supply_annual
DATASET_RENT_COMPARISON = 3  # v_story4_rent_comparison

COLOR_SCHEME = "windsor_housing"  # validated CVD-safe palette, docker/superset_config.py


def eq_filter(column: str, value):
    return {"clause": "WHERE", "subject": column, "operator": "==", "comparator": value, "expressionType": "SIMPLE"}


def pie_params(groupby: str, metric_sql: str, metric_label: str, filters: list) -> dict:
    return {
        "groupby": [groupby],
        "metric": {"expressionType": "SQL", "sqlExpression": metric_sql, "label": metric_label},
        "adhoc_filters": filters,
        "row_limit": 20,
        "sort_by_metric": True,
        "color_scheme": COLOR_SCHEME,
        "show_labels": True,
        "labels_outside": True,
        "label_type": "key_percent",
        "show_labels_threshold": 2,
        "number_format": ",d",
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "bottom",
        "outerRadius": 70,
        "innerRadius": 35,
    }


CHARTS = {
    "s1-tenure": {
        "slice_name": "Story 5: Burdened Households by Tenure",
        "description": (
            "Households spending 30%+ of income on shelter, Windsor CMA, 2021 Census -- "
            "warehouse.v_story1_burden_by_tenure."
        ),
        "dataset_id": DATASET_BURDEN_BY_TENURE,
        "viz_type": "pie",
        "params": pie_params("tenure", "SUM(burdened_households)", "Burdened Households", []),
    },
    "s2-zone-stock": {
        "slice_name": "Story 5: Rental Stock by Zone (Oct-25)",
        "description": (
            "Purpose-built rental units by Windsor zone, Combined dwelling types -- "
            "warehouse.v_story2_zone_snapshot. The 7 zones sum to the CMA total (19,883)."
        ),
        "dataset_id": DATASET_ZONE_SNAPSHOT,
        "viz_type": "pie",
        "params": pie_params("zone_label", "SUM(rental_universe)", "Rental Units", []),
    },
    "s3-starts-mix": {
        "slice_name": "Story 5: 2025 Housing Starts by Dwelling Type",
        "description": "Windsor CMA housing starts in 2025 -- warehouse.v_story3_windsor_supply_annual.",
        "dataset_id": DATASET_SUPPLY_ANNUAL,
        "viz_type": "pie",
        "params": pie_params(
            "dwelling_type",
            "SUM(units)",
            "Units Started",
            [
                eq_filter("activity", "Starts"),
                eq_filter("period_year", 2025),
                {
                    "clause": "WHERE",
                    "subject": "dwelling_type",
                    "operator": "!=",
                    "comparator": "Total",
                    "expressionType": "SIMPLE",
                },
            ],
        ),
    },
    "s4-rent": {
        "slice_name": "Story 5: 2-Bedroom Rent, Windsor vs Peer Cities (Oct-25)",
        "description": "Average 2-bedroom apartment rent, Oct-25 -- warehouse.v_story4_rent_comparison.",
        "dataset_id": DATASET_RENT_COMPARISON,
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["market"],
            "metrics": [{"expressionType": "SQL", "sqlExpression": "AVG(average_rent_2br)", "label": "Average 2-Bedroom Rent"}],
            "adhoc_filters": [eq_filter("period_label", "Oct-25")],
            "order_desc": False,
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_legend": False,
            "show_bar_value": True,
            "rich_tooltip": True,
            "y_axis_format": "$,.0f",
            "x_axis_label": "Market",
            "y_axis_label": "Average 2-Bedroom Rent ($)",
        },
    },
}

SUMMARY_MARKDOWN = """**How the four stories fit together**

- **Renters carry most of the burden, even in the cheapest market.** Renters are 28% of
  Windsor's households but 55% of those spending 30%+ of income on shelter, while Windsor has
  the lowest 2-bedroom rent of the five comparison cities. Cheap next to its peers is not the
  same as affordable to the people renting (Stories 1 and 4).
- **Most rentals are in the city.** The four Windsor city zones hold 82% of the rental stock;
  the county zones are small and dearer (Story 2).
- **New supply has turned to apartments, but there is less of it.** Apartments were 60% of
  2025 starts, up from 6% in 2016, yet total starts fell 41% from 2024 (Story 3).
"""

INSIGHTS = {
    "s1": """**Story 1 -- Who carries the burden**

Of the **28,740** Windsor households spending 30% or more of income on shelter, **15,735
(55%)** rent and 13,005 (45%) own.

Renters are only **28%** of all households (45,280 of 164,220), so they are about twice as
likely to be cost-burdened as their numbers alone would suggest.
""",
    "s2": """**Story 2 -- Where the rentals are**

Windsor's **19,883** purpose-built rental units are concentrated in the city: Zones 1-4 hold
**16,226 (82%)**, with Zone 1 - Centre alone at 5,509 (28%).

The county zones are small: Amherstburg has 597 units (3%) and the highest average rent of any
zone ($1,955 vs. $1,155 in Zone 1).
""",
    "s3": """**Story 3 -- What is being built**

Of **1,262** homes started in 2025, **752 (60%)** were apartments, 331 (26%) single-detached,
90 (7%) semi-detached and 89 (7%) row houses.

In 2016 apartments were just 6% of starts. The mix has moved toward the housing renters use,
though "Apartment and Other" also includes condominium apartments, not only rentals.
""",
    "s4": """**Story 4 -- How Windsor compares**

Windsor's average 2-bedroom rent (**$1,454**, Oct-25) is the lowest of the five comparison
cities: $73 below St. Catharines-Niagara, about $200 below London and Hamilton, and **$378
below Kitchener-Cambridge-Waterloo**.

This is a ranking, not parts of a whole, so it is shown as bars rather than a pie.
""",
}

DASHBOARD_TITLE = "Story 5: How do affordability, rental conditions, and supply fit together?"

# Top-to-bottom: (kind, id, content). Rows pair a chart (width 7) with its
# insight note (width 5).
LAYOUT = [
    ("header", "HEADER-summary", "Key Conclusions Across Stories 1-4"),
    ("markdown-row", "ROW-summary", [("MARKDOWN-summary", SUMMARY_MARKDOWN, 12, 30)]),
    ("header", "HEADER-s1", "Story 1: Affordability"),
    ("chart-row", "ROW-s1", [("s1-tenure", "MARKDOWN-s1", INSIGHTS["s1"])]),
    ("header", "HEADER-s2", "Story 2: Rental Market"),
    ("chart-row", "ROW-s2", [("s2-zone-stock", "MARKDOWN-s2", INSIGHTS["s2"])]),
    ("header", "HEADER-s3", "Story 3: Housing Supply"),
    ("chart-row", "ROW-s3", [("s3-starts-mix", "MARKDOWN-s3", INSIGHTS["s3"])]),
    ("header", "HEADER-s4", "Story 4: Comparison"),
    ("chart-row", "ROW-s4", [("s4-rent", "MARKDOWN-s4", INSIGHTS["s4"])]),
]

CHART_WIDTH = 7
NOTE_WIDTH = 5
ROW_HEIGHT = 55


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


def markdown_node(node_id: str, row_id: str, code: str, width: int, height: int) -> dict:
    return {
        "type": "MARKDOWN",
        "id": node_id,
        "children": [],
        "parents": ["ROOT_ID", "GRID_ID", row_id],
        "meta": {"width": width, "height": height, "code": code, "uuid": str(uuid.uuid4())},
    }


def row_node(row_id: str, children: list) -> dict:
    return {
        "type": "ROW",
        "id": row_id,
        "children": children,
        "parents": ["ROOT_ID", "GRID_ID"],
        "meta": {"background": "BACKGROUND_TRANSPARENT"},
    }


def build_position_json(chart_ids: dict) -> dict:
    grid_children = [node_id for _, node_id, _ in LAYOUT]
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": grid_children, "parents": ["ROOT_ID"]},
    }

    for kind, node_id, content in LAYOUT:
        if kind == "header":
            position[node_id] = {
                "type": "HEADER",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"text": content, "headerSize": "MEDIUM_HEADER", "background": "BACKGROUND_TRANSPARENT"},
            }
        elif kind == "markdown-row":
            position[node_id] = row_node(node_id, [md_id for md_id, *_ in content])
            for md_id, code, width, height in content:
                position[md_id] = markdown_node(md_id, node_id, code, width, height)
        else:  # chart-row: one chart and its insight note
            ((chart_key, md_id, code),) = content
            chart_node_id = f"CHART-{chart_key}"
            position[node_id] = row_node(node_id, [chart_node_id, md_id])
            position[chart_node_id] = {
                "type": "CHART",
                "id": chart_node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", node_id],
                "meta": {
                    "chartId": chart_ids[chart_key],
                    "width": CHART_WIDTH,
                    "height": ROW_HEIGHT,
                    "uuid": str(uuid.uuid4()),
                },
            }
            position[md_id] = markdown_node(md_id, node_id, code, NOTE_WIDTH, ROW_HEIGHT)

    return position


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    """POST /api/v1/dashboard/ doesn't fill the dashboard_slices join
    table from position_json -- see etl/build_story2_dashboard.py's
    function of the same name for how that was found."""
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": [dashboard_id]}
    )
    resp.raise_for_status()


def ensure_dashboard(session, headers, position_json: dict) -> int:
    body = {
        "dashboard_title": DASHBOARD_TITLE,
        "published": True,
        "position_json": json.dumps(position_json),
        # No native filters: each chart is one fixed headline conclusion
        # from its own story; the story dashboards carry the filters.
        "json_metadata": json.dumps({"native_filter_configuration": [], "color_scheme": COLOR_SCHEME}),
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

    dashboard_id = ensure_dashboard(session, headers, build_position_json(chart_ids))
    print(f"Dashboard ready: id={dashboard_id}")

    for chart_id in chart_ids.values():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
