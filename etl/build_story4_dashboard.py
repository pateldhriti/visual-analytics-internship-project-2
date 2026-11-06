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

ACCENT = "#2a78d6"  # project blue
PEER_GREY = "#aab6c8"
MARKETS = [
    "Windsor CMA",
    "Hamilton CMA",
    "Kitchener-Cambridge-Waterloo CMA",
    "London CMA",
    "St. Catharines-Niagara CMA",
]
# Windsor in the project blue, the four peers in one grey, on every chart.
MARKET_COLORS = {m: (ACCENT if m == "Windsor CMA" else PEER_GREY) for m in MARKETS}


def market_bar_params(sql: str, label: str, number_format: str, filters: list) -> dict:
    """Horizontal ECharts bar, one bar per city. Each city is its own
    series (stacked, so bars keep full width) so Windsor can be coloured
    differently from the peers; the x-axis is the same column under another
    label because Superset rejects identical x-axis and series labels."""
    return {
        "x_axis": {"expressionType": "SQL", "sqlExpression": "market", "label": "City"},
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label}],
        "groupby": ["market"],
        "stack": True,
        "orientation": "horizontal",
        "adhoc_filters": filters,
        "row_limit": 20,
        "color_scheme": COLOR_SCHEME,
        "show_value": True,
        "show_legend": False,
        "rich_tooltip": False,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "truncateYAxis": False,
        "y_axis_bounds": [None, None],
    }


CHARTS = {
    "kpi-vacancy": {
        "slice_name": "Windsor Apartment Vacancy Rate",
        "description": "Windsor's apartment vacancy rate, all unit sizes, Oct-25. Apartments only because CMHC publishes the city comparison for apartments only (Story 2's 3.6% includes row houses). warehouse.v_story4_vacancy_comparison.",
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
            "subheader": "apartments only · all unit sizes · Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-rent": {
        "slice_name": "Windsor 2-Bedroom Apartment Rent",
        "description": "Windsor's average 2-bedroom apartment rent, Oct-25 -- the unit size CMHC uses to compare cities. warehouse.v_story4_rent_comparison.",
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
            "subheader": "2-bedroom apartments · per month · Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "kpi-rent-growth": {
        "slice_name": "Windsor Rent Growth (Oct-24 to Oct-25)",
        "description": "How much 2-bedroom apartment rent rose from Oct-24 to Oct-25 in the same buildings (CMHC's fixed sample), so new, pricier buildings do not inflate it. warehouse.v_story4_affordability_gap.",
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
            "subheader": "2-bedroom apartments · same units, Oct-24 to Oct-25",
            "color_scheme": COLOR_SCHEME,
        },
    },
    "vacancy-by-market": {
        "slice_name": "Apartment Vacancy Rate by Market (Oct-25)",
        "description": (
            "Share of apartments empty and available, Oct-25, Windsor (blue) and four similar Ontario "
            "cities (grey). Lower means a tighter market where it is harder to find an apartment. "
            "warehouse.v_story4_vacancy_comparison."
        ),
        "dataset_id": DATASET_VACANCY,
        "viz_type": "echarts_timeseries_bar",
        "params": market_bar_params("AVG(vacancy_rate_pct) / 100.0", "Vacancy rate", ".1%", [period_filter()]),
    },
    "rent-by-market": {
        "slice_name": "2-Bedroom Apartment Rent by Market (Oct-25)",
        "description": (
            "Average monthly rent for a 2-bedroom apartment, Oct-25, Windsor (blue) and four similar "
            "Ontario cities (grey). warehouse.v_story4_rent_comparison."
        ),
        "dataset_id": DATASET_RENT,
        "viz_type": "echarts_timeseries_bar",
        "params": market_bar_params("AVG(average_rent_2br)", "Average 2-bedroom rent", "$,.0f", [period_filter()]),
    },
    "rent-growth-by-market": {
        "slice_name": "Rent Growth by Market (Oct-24 to Oct-25)",
        "description": (
            "How much 2-bedroom apartment rent rose from Oct-24 to Oct-25 in the same buildings, "
            "Windsor (blue) and four similar Ontario cities (grey). This is the rent side of the "
            "affordability-gap index; the income side is not available (see the note below). "
            "warehouse.v_story4_affordability_gap."
        ),
        "dataset_id": DATASET_AFFORDABILITY_GAP,
        "viz_type": "echarts_timeseries_bar",
        "params": market_bar_params("AVG(rent_growth_pct) / 100.0", "Rent growth", ".1%", []),
    },
}

AFFORDABILITY_GAP_MARKDOWN = """**How to read this dashboard.** Windsor is the blue bar in every chart; the grey bars
are four Ontario cities of similar size (London, Kitchener-Cambridge-Waterloo, Hamilton,
St. Catharines-Niagara). All figures are for **apartments only**, October 2025, because CMHC
publishes the city comparison for apartments only. That is why Windsor's vacancy and rent here
can differ slightly from Story 2's figures, which also count row houses.

**Why there is no single affordability-gap number.** The gap is rent growth minus the growth of
renters' incomes. Rent growth is shown above. None of the data sources used in this project
reports renters' income year by year, so the income side cannot be measured yet, and the
project does not estimate it.
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


def chart_node(node_id: str, parent_id: str, chart_id: int, width: int, height: int = 25) -> dict:
    # Default height, used only by the 3 KPI tiles (every bar chart below
    # passes its own height=55) -- was 50, which left a large empty gap
    # above the number inside every KPI card, confirmed visually.
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

    position["HEADER-kpis"] = header_node("HEADER-kpis", "Windsor at a Glance: Apartments, October 2025")
    position["ROW-kpi"] = row_node(
        "ROW-kpi", ["CHART-kpi-vacancy", "CHART-kpi-rent", "CHART-kpi-rent-growth"]
    )
    position["CHART-kpi-vacancy"] = chart_node("CHART-kpi-vacancy", "ROW-kpi", chart_ids["kpi-vacancy"], 4)
    position["CHART-kpi-rent"] = chart_node("CHART-kpi-rent", "ROW-kpi", chart_ids["kpi-rent"], 4)
    position["CHART-kpi-rent-growth"] = chart_node(
        "CHART-kpi-rent-growth", "ROW-kpi", chart_ids["kpi-rent-growth"], 4
    )

    position["HEADER-vacancy"] = header_node("HEADER-vacancy", "Vacancy: How Easy Is It to Find an Apartment?")
    position["ROW-vacancy"] = row_node("ROW-vacancy", ["CHART-vacancy-by-market"])
    position["CHART-vacancy-by-market"] = chart_node(
        "CHART-vacancy-by-market", "ROW-vacancy", chart_ids["vacancy-by-market"], 12, 40
    )

    position["HEADER-rent"] = header_node("HEADER-rent", "Rent: What a 2-Bedroom Apartment Costs")
    position["ROW-rent"] = row_node("ROW-rent", ["CHART-rent-by-market"])
    position["CHART-rent-by-market"] = chart_node(
        "CHART-rent-by-market", "ROW-rent", chart_ids["rent-by-market"], 12, 40
    )

    position["HEADER-rent-growth"] = header_node("HEADER-rent-growth", "Rent Growth: How Fast Rents Rose (Oct-24 to Oct-25)")
    position["ROW-rent-growth"] = row_node("ROW-rent-growth", ["CHART-rent-growth-by-market"])
    position["CHART-rent-growth-by-market"] = chart_node(
        "CHART-rent-growth-by-market", "ROW-rent-growth", chart_ids["rent-growth-by-market"], 12, 40
    )

    position["ROW-note"] = row_node("ROW-note", ["MARKDOWN-affordability-gap"])
    position["MARKDOWN-affordability-gap"] = markdown_node(
        "MARKDOWN-affordability-gap", "ROW-note", AFFORDABILITY_GAP_MARKDOWN, height=26
    )

    return position


INTERACTIVE_KEYS = ["vacancy-by-market", "rent-by-market", "rent-growth-by-market"]


def ensure_dashboard(session, headers, position_json: dict, chart_ids: dict) -> int:
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    # Merge into the stored metadata (Superset's frontend keeps its own keys
    # there). The three ECharts charts can emit cross-filters; here a click
    # filters nothing -- every chart shows one city's figure against the
    # others, and the KPI cards are fixed to Windsor -- and the
    # configuration is written explicitly in the shape the frontend
    # computes, so it never tries to re-save it (an anonymous viewer's save
    # fails with 401 and Superset then shows the login page).
    metadata = {}
    if existing:
        current = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers)
        current.raise_for_status()
        metadata = json.loads(current.json()["result"]["json_metadata"] or "{}")
    all_ids = sorted(chart_ids.values())
    metadata.update(
        {
            "color_scheme": COLOR_SCHEME,
            "label_colors": MARKET_COLORS,
            "chart_configuration": {
                str(chart_ids[key]): {
                    "id": chart_ids[key],
                    "crossFilters": {"scope": {"rootPath": ["ROOT_ID"], "excluded": all_ids}, "chartsInScope": []},
                }
                for key in INTERACTIVE_KEYS
            },
            "global_chart_configuration": {
                "scope": {"rootPath": ["ROOT_ID"], "excluded": all_ids},
                "chartsInScope": [],
            },
            "cross_filters_enabled": True,
        }
    )
    for key, default in (("shared_label_colors", {}), ("timed_refresh_immune_slices", []),
                         ("expanded_slices", {}), ("refresh_frequency", 0)):
        metadata.setdefault(key, default)
    body = {
        "dashboard_title": DASHBOARD_TITLE,
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
    session, headers = get_session()
    print("Logged in to Superset.")

    chart_ids = {}
    for key, spec in CHARTS.items():
        chart_id = ensure_chart(session, headers, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")

    position_json = build_position_json(chart_ids)
    dashboard_id = ensure_dashboard(session, headers, position_json, chart_ids)
    print(f"Dashboard ready: id={dashboard_id}")

    for key, chart_id in chart_ids.items():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
