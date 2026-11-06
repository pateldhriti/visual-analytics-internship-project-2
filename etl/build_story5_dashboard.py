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

from setup_superset_dashboard import SUPERSET_URL, find_existing, get_session

# Dataset ids, from etl/register_superset_datasets.py's own output.
DATASET_RENT_AFFORDABILITY = 25  # v_story5_rent_affordability
DATASET_PEER_AFFORDABILITY = 26  # v_story5_peer_affordability
DATASET_SUPPLY_MARKET = 27  # v_story5_supply_vs_rental_market
DATASET_PEER_CONSTRUCTION = 28  # v_story5_peer_construction
DATASET_SUPPLY_DEMAND = 29  # v_story5_supply_vs_demand

COLOR_SCHEME = "windsor_housing"  # validated CVD-safe palette, docker/superset_config.py
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
    "Homes needed for population growth": "#d0703c",
    "Homes completed": OTHER_HOMES,
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


def city_bar_params(sql: str, label: str, number_format: str, upper=None) -> dict:
    """Horizontal bar, one bar per city. Each city is its own series
    (stacked, so bars keep full width) so Windsor can be blue and the peers
    grey; the x-axis is the same column under another label because
    Superset rejects identical x-axis and series labels."""
    return {
        "x_axis": {"expressionType": "SQL", "sqlExpression": "city", "label": "City"},
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
            "MAX(pct_renters_spending_30pct_plus) / 100.0", "Renters spending 30%+ on shelter", ".1%", upper=0.5
        ),
    },
    "peer-table": {
        "slice_name": "Story 5: Rent and Renter Income, Windsor and Comparison Cities",
        "description": (
            "Each city's Oct-25 average 2-bedroom apartment rent (CMHC) next to its renters' 2020 "
            "incomes and shelter-cost burden (2021 Census). warehouse.v_story5_peer_affordability."
        ),
        "dataset_id": DATASET_PEER_AFFORDABILITY,
        "viz_type": "table",
        "params": table_params(
            ["city", "average_rent_2br", "median_renter_income", "rent_pct_of_median_renter_income",
             "pct_renters_who_cannot_afford_2br", "pct_renters_spending_30pct_plus", "pct_households_renting"],
            {
                "average_rent_2br": "$,.0f",
                "median_renter_income": "$,.0f",
                "rent_pct_of_median_renter_income": ",.1f",
                "pct_renters_who_cannot_afford_2br": ",.1f",
                "pct_renters_spending_30pct_plus": ",.1f",
                "pct_households_renting": ",.1f",
            },
            "average_rent_2br",
        ),
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
            "2021 household sizes. 1.0 means building kept pace; below 1.0 it fell short. "
            "warehouse.v_story5_supply_vs_demand."
        ),
        "dataset_id": DATASET_SUPPLY_DEMAND,
        "viz_type": "echarts_timeseries_bar",
        "params": city_bar_params(
            "MAX(homes_built_per_home_needed)", "Homes completed per home needed", ",.2f", upper=1.2
        ),
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
            "x_axis": "city",
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "MAX(homes_needed)", "label": "Homes needed for population growth"},
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
            "x_axis_sort": "Homes needed for population growth",
            "x_axis_sort_asc": True,
            "truncateYAxis": False,
            "y_axis_bounds": [0, None],
        },
    },
}

INTRO_MARKDOWN = """**Every chart on this page joins two of the four stories.** Each story answers its own
question from one dataset; here the datasets are combined through what they share (the city,
the year, and renters) to answer questions none of them can answer alone. Windsor is blue;
the four comparison cities (London, Hamilton, Kitchener-Cambridge-Waterloo,
St. Catharines-Niagara) are grey. Use **Years** in the filter bar to narrow sections 3 and 4.
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
    "peer": """**What it shows.** Windsor has the **lowest** 2-bedroom rent of the five cities, but its renters
also have the second-lowest incomes. A year of rent takes **36%** of the median renter's income,
the same as Hamilton and close to every other city (36%-39%), and about **6 in 10** renters
cannot afford the average 2-bedroom in every city.

**So Windsor is cheap, but not more affordable.** Its share of renters spending 30%+ on shelter
(34.8%) is still the lowest of the five.
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
consistently the slowest builder. Section 5 checks whether that is simply because Windsor grew
more slowly.
""",
    "demand": """**What it shows.** Between the 2016 and 2021 Censuses Windsor gained **23,912 people (6.0%)**.
At 2.51 people per household that is about **9,500 homes needed**, but only **5,666** were
completed in 2016-2020: **0.59 homes for every home needed**, the lowest of the five cities
(London 0.72, Hamilton 0.84, St. Catharines-Niagara 0.85, Kitchener-Cambridge-Waterloo 0.91).

**Why it matters.** Windsor grew about as fast as Hamilton (5.0%) and St. Catharines-Niagara
(6.8%) yet built the least for its growth, a shortfall of roughly 3,900 homes. That is
consistent with the tight 2022 rental market in section 3: supply did not keep up with demand.

*Completions are not net of demolitions, and 2021 household sizes are applied to the whole
period, so the ratios are estimates; the ranking between cities is the robust part.*
""",
}

# Top-to-bottom: (kind, id, content). Widths add to 12 per row.
LAYOUT = [
    ("markdown-row", "ROW-intro", [("MARKDOWN-intro", INTRO_MARKDOWN, 12, 14)]),
    ("chart-row", "ROW-kpis", [("kpi-afford", 3, 22), ("kpi-rent-income", 3, 22), ("kpi-completions", 3, 22), ("kpi-build-rate", 3, 22)]),
    ("header", "HEADER-afford", "1. Can Windsor renters afford the rent? (Story 1 + Story 2)"),
    ("chart-row", "ROW-afford", [("afford-by-size", 5, 50), ("afford-table", 7, 50)]),
    ("markdown-row", "ROW-afford-note", [("MARKDOWN-afford", NOTES["afford"], 12, 22)]),
    ("header", "HEADER-peer", "2. Is Windsor affordable, or only cheap? (Story 1 + Story 4)"),
    ("chart-row", "ROW-peer", [("peer-rent-income", 6, 45), ("peer-burden", 6, 45)]),
    ("chart-row", "ROW-peer-table", [("peer-table", 7, 45)], ("MARKDOWN-peer", NOTES["peer"], 5, 45)),
    ("header", "HEADER-supply", "3. Did new homes ease the rental market? (Story 3 + Story 2)"),
    ("chart-row", "ROW-supply", [("supply-completions", 6, 50), ("supply-vacancy", 6, 50)]),
    ("markdown-row", "ROW-supply-note", [("MARKDOWN-supply", NOTES["supply"], 12, 19)]),
    ("header", "HEADER-build", "4. Is Windsor building as much as its peers? (Story 3 + Story 4)"),
    ("chart-row", "ROW-build", [("peer-build-rate", 6, 50), ("peer-build-trend", 6, 50)]),
    ("markdown-row", "ROW-build-note", [("MARKDOWN-build", NOTES["build"], 12, 19)]),
    ("header", "HEADER-demand", "5. Did building keep up with population growth? (Story 3 + Census population)"),
    ("chart-row", "ROW-demand", [("demand-ratio", 6, 50), ("demand-needed-built", 6, 50)]),
    ("markdown-row", "ROW-demand-note", [("MARKDOWN-demand", NOTES["demand"], 12, 24)]),
]

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
                    },
                }
            for md_id, code, width, height in extra:
                children.append(md_id)
                position[md_id] = markdown_node(md_id, node_id, code, width, height)
            position[node_id] = row_node(node_id, children)
    return position


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

    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
