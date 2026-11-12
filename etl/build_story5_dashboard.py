"""
Build the Story 5 Superset dashboard ("How do affordability, rental
conditions, and supply fit together?"): the combined dashboard. Every
chart reads a view that joins data from two stories (sql/story5_views.sql),
so each answers a question no single story can:

    1. Can Windsor renters afford the rent?      Story 1 incomes x Story 2 rents
       v_story5_rent_affordability
    2. Is Windsor affordable, or only cheap?     Story 1 incomes x Story 4 peer rents
       v_story5_peer_affordability
    3. Did new homes ease the rental market?     Story 3 completions x Story 2 vacancy
       v_story5_supply_vs_rental_market
    4. Is Windsor building as much as its peers? Story 3 starts x Story 4 peer cities
       v_story5_peer_construction
    5. Did building keep up with population?     Story 3 completions x Census population growth
       v_story5_supply_vs_demand                 (all 5 cities, 2016-2021)
    6. Can young renters (students) afford it?   Census renters by age x Story 1 burden x Story 4 cities
       v_story5_renter_burden_by_age
    7. How big is the rental market, and how do  CMHC rental units x Census renter households,
       the five cities compare overall?          then every measure in one table
       v_story5_rental_stock, v_story5_city_profile

Layout: one KPI card per question, then a section per question with its
charts and a note that states the finding in words. Windsor is the blue bar
or line everywhere; comparison cities are grey. A "Years" range filter
narrows the two time-based sections (3 and 4); the KPI cards stay fixed.

Chart-to-chart cross-filtering is off: each chart already compares Windsor
with the other cities or years, so filtering one city out would hide the
comparison. The configuration is still written in the shape Superset's
frontend computes, so an anonymous viewer never triggers a re-save (which
fails with 401 and redirects to the login page).

Charts from the earlier Story 5 dashboard (one snapshot per story, side by
side) are unlinked from the dashboard, not deleted.

Requires the Story 5 views applied (etl/apply_sql_views.py), registered
(etl/register_superset_datasets.py), and Superset running. Re-run
etl/apply_dashboard_theme.py afterwards for the shared dashboard styling.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story5_dashboard.py
"""

import json
import uuid

from dashboard_tabs import add_tabs
from setup_superset_dashboard import SUPERSET_URL, dataset_id, find_existing, get_session
from superset_compat import COLOR_SCHEME, finish_dashboard, gauge, radar, scatter, upgrade_legacy_bars

# Dataset ids, from etl/register_superset_datasets.py's own output.
DATASET_RENT_AFFORDABILITY = dataset_id("v_story5_rent_affordability")
DATASET_PEER_AFFORDABILITY = dataset_id("v_story5_peer_affordability")
DATASET_SUPPLY_MARKET = dataset_id("v_story5_supply_vs_rental_market")
DATASET_PEER_CONSTRUCTION = dataset_id("v_story5_peer_construction")
DATASET_SUPPLY_DEMAND = dataset_id("v_story5_supply_vs_demand")
DATASET_BURDEN_BY_AGE = dataset_id("v_story5_renter_burden_by_age")
DATASET_RENTAL_STOCK = dataset_id("v_story5_rental_stock")
DATASET_CITY_PROFILE = dataset_id("v_story5_city_profile")
DATASET_WINDSOR_VS_PEERS = dataset_id("v_story5_windsor_vs_peers")

# windsor_housing here, Superset's default on the shared server (superset_compat).
DASHBOARD_TITLE = "Story 5: How do affordability, rental conditions, and supply fit together?"

ACCENT = "#2a78d6"  # project blue: Windsor
PEER_GREY = "#aab6c8"  # comparison cities
OTHER_HOMES = "#7fb3a8"  # completions that are not apartments
CITIES = [
    "Windsor CMA",
    "Hamilton CMA",
    "Kitchener-Cambridge-Waterloo CMA",
    "London CMA",
    "St. Catharines-Niagara CMA",
]
PEER_AVERAGE = "Average of the 4 comparison cities"
LABEL_COLORS = {
    **{c: (ACCENT if c == "Windsor CMA" else PEER_GREY) for c in CITIES},
    PEER_AVERAGE: PEER_GREY,
    "Renters who cannot afford it": ACCENT,
    "Apartments": ACCENT,
    "Other homes": OTHER_HOMES,
    "Vacancy rate (October)": ACCENT,
    "Rent increase from the previous October": "#d0703c",
    "Homes needed": "#d0703c",
    "Homes completed": OTHER_HOMES,
    "Renters aged 15-24": "#d0703c",
    "All renters": PEER_GREY,
    "Renters spending 30%+ on shelter": ACCENT,
    # The bubble chart names cities by their short names (SHORT_CITY_SQL), each
    # in its own colour so the bubbles can be told apart; Windsor stays blue.
    "Windsor": ACCENT,
    "Hamilton": "#eb6834",
    "Kitchener-Waterloo": "#1baf7a",
    "London": "#eda100",
    "St. Catharines": "#e87ba4",
}


def eq_filter(column: str, value):
    return {"clause": "WHERE", "subject": column, "operator": "==", "comparator": value, "expressionType": "SIMPLE"}


def sql_filter(sql: str):
    return {"clause": "WHERE", "sqlExpression": sql, "expressionType": "SQL"}


def table_params(columns: list, formats: dict, order_by: str) -> dict:
    """Raw-mode table. Headers come from the dataset columns' verbose
    names (set by set_column_labels below): in raw mode Superset 3.1
    ignores customColumnName."""
    return {
        "query_mode": "raw",
        "all_columns": columns,
        "order_by_cols": [json.dumps([order_by, True])],
        "adhoc_filters": [],
        "row_limit": 10,
        "show_cell_bars": False,
        "include_search": False,
        "column_config": {col: {"d3NumberFormat": fmt} for col, fmt in formats.items()},
    }


# Readable column names for the two datasets shown as tables.
COLUMN_LABELS = {
    DATASET_RENT_AFFORDABILITY: {
        "unit_size": "Unit size",
        "average_rent": "Average rent",
        "income_needed": "Income needed",
        "median_renter_income": "Median renter income",
        "renters_who_cannot_afford": "Renters who earn less",
        "pct_renters_who_cannot_afford": "% of renters",
    },
    DATASET_CITY_PROFILE: {
        "city": "City",
        "average_rent_2br": "2-bed rent",
        "vacancy_rate": "Vacancy %",
        "units_per_100_renter_households": "Rental units per 100 renters",
        "median_renter_income": "Median renter income",
        "rent_pct_of_median_renter_income": "Rent % of income",
        "pct_renters_spending_30pct_plus": "Renters spending 30%+ (%)",
        "pct_young_renters_spending_30pct_plus": "Ages 15-24 spending 30%+ (%)",
        "starts_per_1000_households": "Starts per 1,000 households",
        "pct_needed_homes_built": "Needed homes built (%)",
    },
    DATASET_PEER_AFFORDABILITY: {
        "city": "City",
        "average_rent_2br": "2-bed rent",
        "median_renter_income": "Median renter income",
        "rent_pct_of_median_renter_income": "Rent % of income",
        "pct_renters_who_cannot_afford_2br": "% cannot afford 2-bed",
        "pct_renters_spending_30pct_plus": "% spending 30%+",
        "pct_households_renting": "% of households renting",
    },
}
COLUMN_FIELDS = {"id", "column_name", "verbose_name", "type", "is_dttm", "filterable", "groupby",
                 "expression", "description", "python_date_format", "is_active"}


def set_column_labels(session, headers) -> None:
    for dataset_id, labels in COLUMN_LABELS.items():
        resp = session.get(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers)
        resp.raise_for_status()
        columns = []
        for col in resp.json()["result"]["columns"]:
            col = {k: v for k, v in col.items() if k in COLUMN_FIELDS}
            if col["column_name"] in labels:
                col["verbose_name"] = labels[col["column_name"]]
            columns.append(col)
        session.put(
            f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers, json={"columns": columns}
        ).raise_for_status()


def kpi(slice_name, description, dataset_id, sql, label, number_format, subheader, filters):
    return {
        "slice_name": slice_name,
        "description": description,
        "dataset_id": dataset_id,
        "viz_type": "big_number_total",
        "params": {
            "metric": {"expressionType": "SQL", "sqlExpression": sql, "label": label},
            "adhoc_filters": filters,
            "y_axis_format": number_format,
            "header_font_size": 0.5,
            "subheader_font_size": 0.15,
            "subheader": subheader,
            "color_scheme": COLOR_SCHEME,
        },
    }


# Shorter axis labels so the bars keep their width in the narrower website
# embed; the series (and so colours and tooltips) keep the full names.
SHORT_CITY_SQL = (
    "CASE city WHEN 'Kitchener-Cambridge-Waterloo CMA' THEN 'Kitchener-Waterloo' "
    "WHEN 'St. Catharines-Niagara CMA' THEN 'St. Catharines' "
    "ELSE REPLACE(city, ' CMA', '') END"
)


def city_bar_params(sql: str, label: str, number_format: str, upper=None) -> dict:
    """Horizontal bar, one bar per city. Each city is its own series
    (stacked, so bars keep full width) so Windsor can be blue and the peers
    grey; the x-axis is the same column under another label because
    Superset rejects identical x-axis and series labels."""
    return {
        "x_axis": {"expressionType": "SQL", "sqlExpression": SHORT_CITY_SQL, "label": "City"},
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label}],
        "groupby": ["city"],
        "stack": True,
        "orientation": "horizontal",
        "adhoc_filters": [],
        "row_limit": 20,
        "color_scheme": COLOR_SCHEME,
        "show_value": True,
        "show_legend": False,
        "rich_tooltip": False,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "x_axis_sort": label,
        "x_axis_sort_asc": True,
        "truncateYAxis": upper is not None,
        # A fixed upper bound leaves room for the value labels.
        "y_axis_bounds": [0, upper],
    }


YEAR_AXIS = {"expressionType": "SQL", "sqlExpression": "CAST(period_year AS TEXT)", "label": "Year"}


def year_params(viz: str, metrics: list, number_format: str, groupby=None, stack=False) -> dict:
    """Bar or line over the calendar years in the view, oldest first."""
    params = {
        "x_axis": YEAR_AXIS,
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label} for sql, label in metrics],
        "groupby": groupby or [],
        "adhoc_filters": [],
        "row_limit": 200,
        "color_scheme": COLOR_SCHEME,
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "top",
        "rich_tooltip": True,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "truncateYAxis": False,
        "y_axis_bounds": [0, None],
    }
    if viz == "line":
        params.update({"markerEnabled": True, "markerSize": 6, "seriesType": "line", "connectNulls": False})
    else:
        params.update({"stack": stack, "show_value": False})
    return params


CHARTS = {
    # --- KPI cards: one per combined question, fixed to Windsor ------------
    "kpi-afford": kpi(
        "Story 5: Renters Who Cannot Afford a 2-Bedroom",
        "Share of Windsor renter households whose 2020 income is below 12 x the Oct-25 average "
        "2-bedroom rent / 0.30. Story 1 incomes x Story 2 rents -- warehouse.v_story5_rent_affordability.",
        DATASET_RENT_AFFORDABILITY,
        "MAX(pct_renters_who_cannot_afford) / 100.0",
        "Cannot afford a 2-bedroom",
        ".0%",
        "of Windsor renters cannot afford an average 2-bedroom (30% rule)",
        [eq_filter("unit_size", "2 Bedroom")],
    ),
    "kpi-rent-income": kpi(
        "Story 5: Windsor 2-Bedroom Rent as Share of Renter Income",
        "A year of Windsor's Oct-25 average 2-bedroom apartment rent as a share of the median renter "
        "household income. Story 1 x Story 4 -- warehouse.v_story5_peer_affordability.",
        DATASET_PEER_AFFORDABILITY,
        "MAX(rent_pct_of_median_renter_income) / 100.0",
        "Rent as share of income",
        ".0%",
        "of the median renter's income goes on a 2-bedroom: cheap rent, low incomes",
        [eq_filter("city", "Windsor CMA")],
    ),
    "kpi-completions": kpi(
        "Story 5: Homes Completed in Windsor, 2023 to 2025",
        "Windsor CMA homes completed in 2023, 2024 and 2025, the years rental vacancy rose. "
        "Story 3 x Story 2 -- warehouse.v_story5_supply_vs_rental_market.",
        DATASET_SUPPLY_MARKET,
        "SUM(completions)",
        "Homes completed",
        ",d",
        "homes completed 2023 to 2025, as vacancy rose from 1.8% to 3.6%",
        [sql_filter("period_year BETWEEN 2023 AND 2025")],
    ),
    "kpi-build-rate": kpi(
        "Story 5: Windsor Homes Started per 1,000 Households",
        "Windsor homes started a year per 1,000 households (2021 Census count), averaged over "
        "2016 to the last full year. Story 3 x Story 4 -- warehouse.v_story5_peer_construction.",
        DATASET_PEER_CONSTRUCTION,
        "ROUND(1000.0 * SUM(starts) / MAX(private_households) / COUNT(DISTINCT period_year), 1)",
        "Starts per 1,000 households",
        ",.1f",
        "homes started a year per 1,000 households since 2016: fewest of the 5 cities",
        [eq_filter("city", "Windsor CMA")],
    ),
    # --- 1. Story 1 x Story 2 ------------------------------------------------
    "afford-by-size": {
        "slice_name": "Story 5: Windsor Renters Who Cannot Afford the Average Rent, by Unit Size",
        "description": (
            "Share of Windsor renter households (2021 Census, 2020 incomes) earning less than the income "
            "the Oct-25 average rent needs under the 30% rule, for each unit size (apartments and row "
            "houses). 3-bedroom rent is not published. warehouse.v_story5_rent_affordability."
        ),
        "dataset_id": DATASET_RENT_AFFORDABILITY,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": "unit_size",
            "metrics": [
                {
                    "expressionType": "SQL",
                    "sqlExpression": "MAX(pct_renters_who_cannot_afford) / 100.0",
                    "label": "Renters who cannot afford it",
                }
            ],
            "groupby": [],
            "adhoc_filters": [],
            "row_limit": 10,
            "color_scheme": COLOR_SCHEME,
            "show_value": True,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ".0%",
            "x_axis_title": "",
            "y_axis_title": "",
            "orientation": "horizontal",
            "x_axis_sort": "Renters who cannot afford it",
            "x_axis_sort_asc": True,
            "truncateYAxis": False,
            "y_axis_bounds": [0, 1],
        },
    },
    "afford-table": {
        "slice_name": "Story 5: Income Needed for the Average Windsor Rent",
        "description": (
            "Average rent (Oct-25), the yearly income it needs (rent x 12 / 0.30), the median renter "
            "income (2020) and how many renter households earn less. warehouse.v_story5_rent_affordability."
        ),
        "dataset_id": DATASET_RENT_AFFORDABILITY,
        "viz_type": "table",
        "params": table_params(
            ["unit_size", "average_rent", "income_needed", "median_renter_income",
             "renters_who_cannot_afford", "pct_renters_who_cannot_afford"],
            {
                "average_rent": "$,.0f",
                "income_needed": "$,.0f",
                "median_renter_income": "$,.0f",
                "renters_who_cannot_afford": ",d",
                "pct_renters_who_cannot_afford": ",.1f",
            },
            "unit_size_sort_order",
        ),
    },
    # --- 2. Story 1 x Story 4 ------------------------------------------------
    "peer-rent-income": {
        "slice_name": "Story 5: 2-Bedroom Rent as Share of Median Renter Income, by City",
        "description": (
            "A year of the Oct-25 average 2-bedroom apartment rent as a share of each city's median "
            "renter household income (2020). Above 30% means the typical renter cannot afford the "
            "typical 2-bedroom. warehouse.v_story5_peer_affordability."
        ),
        "dataset_id": DATASET_PEER_AFFORDABILITY,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "MAX(rent_pct_of_median_renter_income) / 100.0", "Rent as share of median renter income", ".0%", upper=0.5
        ),
    },
    "peer-burden": {
        "slice_name": "Story 5: Renters Spending 30%+ of Income on Shelter, by City",
        "description": (
            "Share of tenant households spending 30% or more of income on shelter, 2021 Census, Windsor "
            "and the four comparison cities. warehouse.v_story5_peer_affordability."
        ),
        "dataset_id": DATASET_PEER_AFFORDABILITY,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "MAX(pct_renters_spending_30pct_plus) / 100.0", "Renters spending 30%+ on shelter", ".0%", upper=0.5
        ),
    },
    "windsor-radar": {
        "slice_name": "Story 5: Windsor (Blue) vs the Comparison-City Average (Grey = 100)",
        "description": (
            "Each measure is Windsor's value as a % of the four comparison cities' average (the grey "
            "shape, 100). Windsor is below average on all eight; furthest on homes started per 1,000 "
            "households. warehouse.v_story5_windsor_vs_peers."
        ),
        "dataset_id": DATASET_WINDSOR_VS_PEERS,
        **dict(zip(("viz_type", "params"), radar(
            "group_label",
            [{"expressionType": "SQL", "sqlExpression": f"MAX({col})", "label": label} for col, label in (
                ("rent_index", "2-bed rent"),
                ("income_index", "Renter income"),
                ("rent_share_index", "Rent % of income"),
                ("burden_index", "Renters 30%+"),
                ("vacancy_index", "Vacancy"),
                ("rental_units_index", "Rental units per renter"),
                ("build_rate_index", "Homes started"),
                ("needed_built_index", "Needed homes built"),
            )],
            [], ",d", 120,
        ))),
    },
    "peer-scatter": {
        "slice_name": "Story 5: Rent vs Renter Income by City",
        "description": (
            "Each city's Oct-25 average 2-bedroom apartment rent (up) against its renters' median 2020 "
            "income (across). Windsor is lowest on both. Hover a bubble for the city. "
            "warehouse.v_story5_peer_affordability."
        ),
        "dataset_id": DATASET_PEER_AFFORDABILITY,
        **dict(zip(("viz_type", "params"), scatter(
            "median_renter_income",
            {"expressionType": "SQL", "sqlExpression": "MAX(average_rent_2br)", "label": "2-bedroom rent"},
            "city_short", [], "Median renter household income (2020)", "Average 2-bedroom rent (Oct-25)",
            "$,.0f", "$,.0f", x_bounds=(45000, 62000), y_bounds=(1300, 1950),
        ))),
    },
    # --- 3. Story 3 x Story 2 ------------------------------------------------
    "supply-completions": {
        "slice_name": "Story 5: Homes Completed in Windsor by Year",
        "description": (
            "Homes finished in the Windsor CMA each year, apartments and other homes "
            "(StatCan 34-10-0154-01), for the years the rental survey also covers. "
            "warehouse.v_story5_supply_vs_rental_market."
        ),
        "dataset_id": DATASET_SUPPLY_MARKET,
        "viz_type": "echarts_timeseries_bar",
        "params": year_params(
            "bar",
            [("SUM(apartment_completions)", "Apartments"), ("SUM(completions - apartment_completions)", "Other homes")],
            ",d",
            stack=True,
        ),
    },
    "supply-vacancy": {
        "slice_name": "Story 5: Windsor Rental Vacancy and Rent Increase by Year",
        "description": (
            "October vacancy rate and the rise in average rent from the previous October, Windsor CMA, "
            "apartments and row houses, all unit sizes (CMHC). Read with the completions chart beside it. "
            "warehouse.v_story5_supply_vs_rental_market."
        ),
        "dataset_id": DATASET_SUPPLY_MARKET,
        "viz_type": "echarts_timeseries_line",
        "params": year_params(
            "line",
            [
                ("MAX(vacancy_rate) / 100.0", "Vacancy rate (October)"),
                ("MAX(rent_change_pct) / 100.0", "Rent increase from the previous October"),
            ],
            ".1%",
        ),
    },
    # --- 4. Story 3 x Story 4 ------------------------------------------------
    "peer-build-rate": {
        "slice_name": "Story 5: Homes Started per 1,000 Households, by City",
        "description": (
            "Homes started a year per 1,000 households (2021 Census count), averaged over the selected "
            "years, Windsor and the four comparison cities. warehouse.v_story5_peer_construction."
        ),
        "dataset_id": DATASET_PEER_CONSTRUCTION,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "ROUND(1000.0 * SUM(starts) / MAX(private_households) / COUNT(DISTINCT period_year), 1)",
            "Starts a year per 1,000 households",
            ",.1f",
            upper=30,  # above any city's single-year rate (max 25.6), so every Years range fits
        ),
    },
    "peer-build-trend": {
        "slice_name": "Story 5: Homes Started per 1,000 Households, Windsor vs Comparison Cities",
        "description": (
            "Homes started per 1,000 households each year: Windsor against the average of the four "
            "comparison cities. warehouse.v_story5_peer_construction."
        ),
        "dataset_id": DATASET_PEER_CONSTRUCTION,
        "viz_type": "echarts_timeseries_line",
        "params": year_params(
            "line",
            [("AVG(starts_per_1000_households)", "Starts per 1,000 households")],
            ",.1f",
            groupby=[
                {
                    "expressionType": "SQL",
                    "sqlExpression": f"CASE WHEN is_windsor THEN 'Windsor CMA' ELSE '{PEER_AVERAGE}' END",
                    "label": "Group",
                }
            ],
        ),
    },
    # --- 5. Story 3 x Census population (demand) -------------------------------
    "demand-ratio": {
        "slice_name": "Story 5: Homes Completed per Home Needed for Population Growth, by City",
        "description": (
            "Homes completed 2016-2020 divided by the homes the 2016-2021 population growth needed at "
            "2021 household sizes. 100% means building kept pace; below 100% it fell short. "
            "warehouse.v_story5_supply_vs_demand."
        ),
        "dataset_id": DATASET_SUPPLY_DEMAND,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "MAX(homes_built_per_home_needed)", "Share of needed homes completed", ".0%", upper=1.2
        ),
    },
    "demand-gauge": {
        "slice_name": "Story 5: Share of Needed Homes Windsor Built, 2016 to 2021",
        "description": (
            "Homes Windsor completed in 2016-2020 as a share of the homes its 2016-2021 population growth "
            "needed. The full dial is 100%: building kept pace. warehouse.v_story5_supply_vs_demand."
        ),
        "dataset_id": DATASET_SUPPLY_DEMAND,
        **dict(zip(("viz_type", "params"), gauge(
            {"expressionType": "SQL", "sqlExpression": "MAX(homes_built_per_home_needed)", "label": "Needed homes built"},
            [eq_filter("city", "Windsor CMA")], ".0%", 1,
        ))),
    },
    "demand-needed-built": {
        "slice_name": "Story 5: Homes Needed vs Homes Completed, 2016 to 2021, by City",
        "description": (
            "Homes needed for each city's population growth between the 2016 and 2021 Censuses "
            "(growth / people per household) next to homes completed in 2016-2020 "
            "(StatCan 34-10-0154-01). warehouse.v_story5_supply_vs_demand."
        ),
        "dataset_id": DATASET_SUPPLY_DEMAND,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": {"expressionType": "SQL", "sqlExpression": SHORT_CITY_SQL, "label": "City"},
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "MAX(homes_needed)", "label": "Homes needed"},
                {"expressionType": "SQL", "sqlExpression": "MAX(homes_completed_2016_2020)", "label": "Homes completed"},
            ],
            "groupby": [],
            "orientation": "horizontal",
            "adhoc_filters": [],
            "row_limit": 20,
            "color_scheme": COLOR_SCHEME,
            "show_value": True,
            "show_legend": True,
            "legendType": "scroll",
            "legendOrientation": "top",
            "rich_tooltip": True,
            "y_axis_format": ",d",
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_sort": "Homes needed",
            "x_axis_sort_asc": True,
            "truncateYAxis": False,
            "y_axis_bounds": [0, None],
        },
    },
    # --- 7. Rental market size, and every measure per city --------------------
    "rental-stock": {
        "slice_name": "Story 5: Purpose-Built Rental Units per 100 Renter Households, by City",
        "description": (
            "Purpose-built rental units (apartments and row houses, CMHC Rental Market Survey Table "
            "3.1.3, October 2025) per 100 renter households (2021 Census). The rest of the renters live "
            "in rented houses, condos, basements and other units the survey does not cover. "
            "warehouse.v_story5_rental_stock."
        ),
        "dataset_id": DATASET_RENTAL_STOCK,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "MAX(units_per_100_renter_households)", "Rental units per 100 renter households", ",.0f", upper=80
        ),
    },
    "city-profile": {
        "slice_name": "Story 5: Windsor and Comparison Cities, All Measures",
        "description": (
            "Every Story 5 measure for the five cities in one table: rent and vacancy (Oct-25), rental "
            "units per 100 renter households, renter incomes and burden (2021 Census), construction "
            "(2016-2025) and the share of needed homes built (2016-2021). warehouse.v_story5_city_profile."
        ),
        "dataset_id": DATASET_CITY_PROFILE,
        "viz_type": "table",
        "params": table_params(
            ["city", "average_rent_2br", "vacancy_rate", "units_per_100_renter_households", "median_renter_income",
             "rent_pct_of_median_renter_income", "pct_renters_spending_30pct_plus",
             "pct_young_renters_spending_30pct_plus", "starts_per_1000_households", "pct_needed_homes_built"],
            {
                "average_rent_2br": "$,.0f",
                "vacancy_rate": ",.1f",
                "units_per_100_renter_households": ",.1f",
                "median_renter_income": "$,.0f",
                "rent_pct_of_median_renter_income": ",.1f",
                "pct_renters_spending_30pct_plus": ",.1f",
                "pct_young_renters_spending_30pct_plus": ",.1f",
                "starts_per_1000_households": ",.1f",
                "pct_needed_homes_built": ",.0f",
            },
            "average_rent_2br",
        ),
    },
    # --- 6. Census renters by age x Story 1 x Story 4 ------------------------
    "young-vs-all": {
        "slice_name": "Story 5: Young Renters vs All Renters Spending 30%+ on Shelter, by City",
        "description": (
            "Share of renter households spending 30% or more of income on shelter: households led by "
            "someone aged 15-24 against all renters, 2021 Census (98-10-0241-01). "
            "warehouse.v_story5_renter_burden_by_age."
        ),
        "dataset_id": DATASET_BURDEN_BY_AGE,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": {"expressionType": "SQL", "sqlExpression": SHORT_CITY_SQL, "label": "City"},
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "MAX(pct_30pct_plus) / 100.0", "label": "Renters aged 15-24"},
                {"expressionType": "SQL", "sqlExpression": "MAX(all_renters_pct_30pct_plus) / 100.0", "label": "All renters"},
            ],
            "groupby": [],
            "orientation": "horizontal",
            "adhoc_filters": [eq_filter("age_sort", 15)],
            "row_limit": 20,
            "color_scheme": COLOR_SCHEME,
            "show_value": True,
            "show_legend": True,
            "legendType": "scroll",
            "legendOrientation": "top",
            "rich_tooltip": True,
            "y_axis_format": ".0%",
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_sort": "Renters aged 15-24",
            "x_axis_sort_asc": True,
            "truncateYAxis": True,
            "y_axis_bounds": [0, 0.7],
        },
    },
    "windsor-by-age": {
        "slice_name": "Story 5: Windsor Renters Spending 30%+ on Shelter, by Age",
        "description": (
            "Share of Windsor renter households spending 30% or more of income on shelter, by age of "
            "the person who maintains the household, 2021 Census (98-10-0241-01). "
            "warehouse.v_story5_renter_burden_by_age."
        ),
        "dataset_id": DATASET_BURDEN_BY_AGE,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            "x_axis": {"expressionType": "SQL", "sqlExpression": "REPLACE(age_group, ' years', '')", "label": "Age"},
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "MAX(pct_30pct_plus) / 100.0", "label": "Renters spending 30%+ on shelter"},
            ],
            "groupby": [],
            "adhoc_filters": [eq_filter("city", "Windsor CMA")],
            "orientation": "horizontal",  # every age label fits on the vertical axis
            "row_limit": 20,
            "color_scheme": COLOR_SCHEME,
            "show_value": True,
            "show_legend": False,
            "rich_tooltip": True,
            "y_axis_format": ".0%",
            "x_axis_title": "",
            "y_axis_title": "",
            "x_axis_sort": "Age",
            "x_axis_sort_asc": True,  # with horizontal bars this puts the youngest at the top
            "truncateYAxis": True,
            "y_axis_bounds": [0, 0.6],
        },
    },
}

INTRO_MARKDOWN = """**Every chart on this page joins data from at least two sources.** Each story answers its own
question from one dataset; here the datasets are combined through what they share (the city,
the year, and renters) to answer questions none of them can answer alone. Windsor is blue;
the four comparison cities (London, Hamilton, Kitchener-Cambridge-Waterloo,
St. Catharines-Niagara) are grey. Use **Years** in the filter bar to narrow questions 3 and 4. Each tab answers one question.
"""

NOTES = {
    "afford": """**What it shows.** Under the 30% rule, an average Windsor 2-bedroom ($1,451 a month,
October 2025) needs a household income of about **$58,000**. The median renter household earned
**$48,400**, so about **61% of renter households (27,700)** earn less than that. Even a
1-bedroom is out of reach for about half.

**Why it matters.** Story 2 shows rents; Story 1 shows renter incomes. Only together do they show
how many renters each rent leaves behind.

*Incomes are for 2020 and rents for 2025, so the shares are an upper bound: incomes have risen
since.*
""",
    "radar": """**Windsor at a glance.** Each point is Windsor as a % of the four comparison cities'
average (the grey shape is 100).

- **Cheaper, but poorer:** rent is about 13% below average and renter incomes about 10% below,
  so rent takes nearly the same share of income (96).
- **The outlier is building:** Windsor starts homes at about **half** the comparison cities'
  rate (56) and built 71% as many of the homes its growth needed.
- **Below average on every measure**, including renters spending 30%+ (91) and rental units
  per renter (86).

*Every figure is in the all-measures table (tab 7).*
""",
    "peer": """**What it shows.** Windsor has the **lowest** 2-bedroom rent of the five cities, but its renters
also have the second-lowest incomes. A year of rent takes **36%** of the median renter's income,
the same as Hamilton and close to every other city (36%-39%), and about **6 in 10** renters
cannot afford the average 2-bedroom in every city.

**So Windsor is cheap, but not more affordable.** Its share of renters spending 30%+ on shelter
(34.8%) is still the lowest of the five.

*Scatter chart: across is renter income, up is rent. Windsor sits lowest on both: cheaper
because its renters earn less.*
""",
    "supply": """**What it shows.** Few homes were finished in 2021 and 2022, and vacancy fell to **1.8%** in
2022 while rent jumped **10.9%** in 2021. Completions then rose to **1,967** in 2023 (1,162
apartments) and stayed high; vacancy climbed back to **3.6%** by 2025 and rent growth slowed to
5.9%. Story 2's rising vacancy lines up with Story 3's completion surge.

*Construction and the rental survey are counted differently (all new homes vs. purpose-built
rentals), so this shows timing, not cause.*
""",
    "build": """**What it shows.** Since 2016 Windsor has started **8.4 homes a year per 1,000 households**, the
fewest of the five cities; Kitchener-Cambridge-Waterloo started 19.7, more than twice as many.
In every year except 2024 Windsor built less than even the lowest of the four; its 2024 surge
(13.0) only matched the comparison cities' average that year (13.2), and 2025 fell back to 7.6.

**Why it matters.** Story 3 shows Windsor's building in isolation; against its peers it is
consistently the slowest builder. Tab 5 checks whether that is simply because Windsor grew
more slowly.
""",
    "demand": """**What it shows.** From 2016 to 2021 Windsor gained **23,912 people**, about
**9,500 homes' worth**, but completed only **5,666**: **59%** of the homes needed, the lowest
of the five cities.

**Why it matters.** Windsor grew about as fast as Hamilton and St. Catharines-Niagara, yet
built least for its growth, a shortfall of about 3,900 homes, consistent with the tight
2022 rental market (tab 3).

*Estimates: 2021 household sizes, completions not net of demolitions. The ranking between
cities is the reliable part.*
""",
    "stock": """**What it shows.** Windsor has **19,883** purpose-built rental units (October 2025)
for **45,625** renter households (2021 Census): about **44 units per 100 renters**, the
second-lowest of the five cities (St. Catharines-Niagara 33, London 65). So roughly **half or
more of Windsor's renters** live in rented houses, condos, basements and other units that
CMHC's rental survey does not cover: Story 2's rents and vacancy describe only part of the
market.

**Does a tighter market mean more pressure?** Not across these cities. Vacancy barely differs
(3.6% to 4.1%), and Windsor's market is nearly as tight as Hamilton's yet has the lowest share
of renters spending 30%+. The differences come from incomes, not vacancy (tab 2).

*Units are counted in 2025 and households in 2021, and some units are vacant, so the share
outside purpose-built rentals is an estimate.*
""",
    "young": """**What it shows.** In Windsor, **46.5%** of renter households led by someone aged 15-24
(2,680 households) spend 30% or more of their income on shelter, against **34.8%** of all
renters: the most burdened age group, ahead of renters aged 85 and over (44.9%). Young renters
are worse off than other renters in every city, but Windsor's are the least burdened of the
five (50.6%-55.3% elsewhere), in line with its lower rents.

**The rents they face.** Under the 30% rule an average studio ($948 a month) needs about
**$37,900** a year and a 1-bedroom ($1,193) about **$47,700** (tab 1).

*The Census counts students who head their own rented household. Students in residence, living
with parents, or away during the May 2021 online term are not included. CMHC's core-housing-need
measure leaves out most student households, so it is not used here.*
""",
}

# Top-to-bottom: (kind, id, content). Widths add to 12 per row.
LAYOUT = [
    ("markdown-row", "ROW-intro", [("MARKDOWN-intro", INTRO_MARKDOWN, 12, 14)]),
    ("chart-row", "ROW-kpis", [("kpi-afford", 3, 22), ("kpi-rent-income", 3, 22), ("kpi-completions", 3, 22), ("kpi-build-rate", 3, 22)]),
    ("chart-row", "ROW-radar", [("windsor-radar", 7, 52)], ("MARKDOWN-radar", NOTES["radar"], 5, 52)),
    ("header", "HEADER-afford", "1. Can Windsor renters afford the rent? (Story 1 + Story 2)"),
    ("chart-row", "ROW-afford", [("afford-by-size", 5, 50), ("afford-table", 7, 50)]),
    ("markdown-row", "ROW-afford-note", [("MARKDOWN-afford", NOTES["afford"], 12, 28)]),
    ("header", "HEADER-peer", "2. Is Windsor affordable, or only cheap? (Story 1 + Story 4)"),
    ("chart-row", "ROW-peer", [("peer-rent-income", 6, 45), ("peer-burden", 6, 45)]),
    ("chart-row", "ROW-peer-table", [("peer-scatter", 7, 45)], ("MARKDOWN-peer", NOTES["peer"], 5, 45)),
    ("header", "HEADER-supply", "3. Did new homes ease the rental market? (Story 3 + Story 2)"),
    ("chart-row", "ROW-supply", [("supply-completions", 6, 50), ("supply-vacancy", 6, 50)]),
    ("markdown-row", "ROW-supply-note", [("MARKDOWN-supply", NOTES["supply"], 12, 28)]),
    ("header", "HEADER-build", "4. Is Windsor building as much as its peers? (Story 3 + Story 4)"),
    ("chart-row", "ROW-build", [("peer-build-rate", 6, 50), ("peer-build-trend", 6, 50)]),
    ("markdown-row", "ROW-build-note", [("MARKDOWN-build", NOTES["build"], 12, 28)]),
    ("header", "HEADER-demand", "5. Did building keep up with population growth? (Story 3 + Census population)"),
    ("chart-row", "ROW-demand", [("demand-ratio", 7, 50)], ("MARKDOWN-demand", NOTES["demand"], 5, 50)),
    ("chart-row", "ROW-demand-built", [("demand-gauge", 4, 42), ("demand-needed-built", 8, 42)]),
    ("header", "HEADER-young", "6. Can young renters and students afford to rent? (Census renters by age + Story 1 + Story 4)"),
    ("chart-row", "ROW-young", [("young-vs-all", 12, 42)]),
    ("chart-row", "ROW-young-age", [("windsor-by-age", 12, 40)]),
    ("markdown-row", "ROW-young-note", [("MARKDOWN-young", NOTES["young"], 12, 34)]),
    ("header", "HEADER-stock", "7. How big is the rental market? (Story 2 + Story 4 + Census renters)"),
    ("chart-row", "ROW-stock", [("rental-stock", 6, 58)], ("MARKDOWN-stock", NOTES["stock"], 6, 58)),
    ("chart-row", "ROW-profile", [("city-profile", 12, 44)]),
]

# Card titles shown on this dashboard: the chart names keep their "Story 5:"
# prefix (unique across Superset), which the narrow KPI cards cut off.
TITLE_OVERRIDES = {
    "kpi-afford": "Can't afford a 2-bed",
    "kpi-rent-income": "2-bed rent / renter income",
    "kpi-completions": "Completed 2023-2025",
    "kpi-build-rate": "Yearly build rate",
    "demand-ratio": "Share of needed homes completed, 2016-2021",
}

# Charts the Years filter reaches (the two time-based sections).
YEAR_FILTER_KEYS = ["supply-completions", "supply-vacancy", "peer-build-rate", "peer-build-trend"]
# Charts Superset lets emit cross-filters (ECharts and tables).
INTERACTIVE_KEYS = [k for k, spec in CHARTS.items() if spec["viz_type"] != "big_number_total"]


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


# One screen per tab (etl/dashboard_tabs.py): an overview with the
# all-measures table, then one tab per combined question.
TABS = [
    ("TAB-overview", "Overview", ["ROW-intro", "ROW-kpis", "ROW-radar"]),
    ("TAB-afford", "1. Afford the rent?", ["HEADER-afford", "ROW-afford", "ROW-afford-note"]),
    ("TAB-peer", "2. Cheap or affordable?", ["HEADER-peer", "ROW-peer", "ROW-peer-table"]),
    ("TAB-supply", "3. New homes and rents", ["HEADER-supply", "ROW-supply", "ROW-supply-note"]),
    ("TAB-build", "4. Building vs peers", ["HEADER-build", "ROW-build", "ROW-build-note"]),
    ("TAB-demand", "5. Population growth", ["HEADER-demand", "ROW-demand", "ROW-demand-built"]),
    ("TAB-young", "6. Young renters", ["HEADER-young", "ROW-young", "ROW-young-age", "ROW-young-note"]),
    ("TAB-stock", "7. Rental market size", ["HEADER-stock", "ROW-stock", "ROW-profile"]),
]


def build_position_json(chart_ids: dict) -> dict:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [node_id for _, node_id, *_ in LAYOUT],
            "parents": ["ROOT_ID"],
        },
    }
    for kind, node_id, content, *extra in LAYOUT:
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
        else:  # chart-row, optionally ending with one markdown note
            children = []
            for chart_key, width, height in content:
                chart_node_id = f"CHART-{chart_key}"
                children.append(chart_node_id)
                position[chart_node_id] = {
                    "type": "CHART",
                    "id": chart_node_id,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", node_id],
                    "meta": {
                        "chartId": chart_ids[chart_key],
                        "width": width,
                        "height": height,
                        "uuid": str(uuid.uuid4()),
                        **(
                            {"sliceNameOverride": TITLE_OVERRIDES[chart_key]}
                            if chart_key in TITLE_OVERRIDES
                            else {}
                        ),
                    },
                }
            for md_id, code, width, height in extra:
                children.append(md_id)
                position[md_id] = markdown_node(md_id, node_id, code, width, height)
            position[node_id] = row_node(node_id, children)
    return add_tabs(position, TABS)


def build_native_filters(chart_ids: dict) -> list:
    in_scope = sorted(chart_ids[key] for key in YEAR_FILTER_KEYS)
    excluded = sorted(cid for cid in chart_ids.values() if cid not in in_scope)
    return [
        {
            "id": "NATIVE_FILTER-story5-years",
            "name": "Years",
            "filterType": "filter_range",
            "targets": [{"datasetId": DATASET_PEER_CONSTRUCTION, "column": {"name": "period_year"}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": excluded},
            "type": "NATIVE_FILTER",
            "description": "Narrow the construction and rental-market sections (3 and 4) to a range of years.",
            "chartsInScope": in_scope,
            "tabsInScope": [],
            "controlValues": {"enableEmptyFilter": False},
        }
    ]


def ensure_dashboard(session, headers, position_json: dict, chart_ids: dict) -> int:
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)
    # Merge into the stored metadata (Superset's frontend keeps keys of its
    # own there; dropping them makes it try to re-save on the next load).
    metadata = {}
    if existing:
        current = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers)
        current.raise_for_status()
        metadata = json.loads(current.json()["result"]["json_metadata"] or "{}")
    all_ids = sorted(chart_ids.values())
    no_cross_filter = {"scope": {"rootPath": ["ROOT_ID"], "excluded": all_ids}, "chartsInScope": []}
    metadata.update(
        {
            "native_filter_configuration": build_native_filters(chart_ids),
            "color_scheme": COLOR_SCHEME,
            "label_colors": LABEL_COLORS,
            "chart_configuration": {
                str(chart_ids[key]): {"id": chart_ids[key], "crossFilters": no_cross_filter} for key in INTERACTIVE_KEYS
            },
            "global_chart_configuration": no_cross_filter,
            "cross_filters_enabled": True,
        }
    )
    for key, default in (
        ("shared_label_colors", {}),
        ("timed_refresh_immune_slices", []),
        ("expanded_slices", {}),
        ("refresh_frequency", 0),
    ):
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


def link_chart_to_dashboard(session, headers, chart_id: int, dashboard_id: int) -> None:
    """POST /api/v1/dashboard/ doesn't fill the dashboard_slices join
    table from position_json -- see etl/build_story2_dashboard.py's
    function of the same name for how that was found."""
    resp = session.put(
        f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": [dashboard_id]}
    )
    resp.raise_for_status()


def unlink_stale_charts(session, headers, dashboard_id: int, keep: set) -> list:
    """Detach charts still linked to the dashboard that are no longer in its
    layout (the earlier one-snapshot-per-story charts). They are kept, not
    deleted."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}/charts", headers=headers)
    resp.raise_for_status()
    stale = [c["id"] for c in resp.json()["result"] if c["id"] not in keep]
    for chart_id in stale:
        session.put(
            f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json={"dashboards": []}
        ).raise_for_status()
    return stale


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    set_column_labels(session, headers)
    print("Table column labels set.")

    chart_ids = {}
    for key, spec in CHARTS.items():
        chart_ids[key] = ensure_chart(session, headers, spec)
        print(f"Chart ready: {spec['slice_name']} (id={chart_ids[key]})")

    dashboard_id = ensure_dashboard(session, headers, build_position_json(chart_ids), chart_ids)
    print(f"Dashboard ready: id={dashboard_id}")

    for chart_id in chart_ids.values():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    stale = unlink_stale_charts(session, headers, dashboard_id, set(chart_ids.values()))
    print(f"Linked {len(chart_ids)} charts; unlinked {len(stale)} earlier charts {stale}.")

    print(f"Finished: {finish_dashboard(session, headers, dashboard_id)}")
    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
