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
from datetime import datetime
import uuid

from dashboard_tabs import add_tabs
from setup_superset_dashboard import SUPERSET_URL, add_chart_to_dashboard, dataset_id, find_existing, get_session
from superset_compat import (PROJECT_LABEL_COLORS, COLOR_SCHEME, finish_dashboard, match_bar_order, named, prefix_names,
                             upgrade_legacy_bars)

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
            "subheader": "starts per 1,000 households (2021 Census base); a partial year counts its months so far",
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
            "adhoc_filters": [FULL_YEARS],  # the view now also has the partial year, for the KPI tile
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



# --- Tabs "This Year So Far" and "This Year's Mix" --------------------------
# January to the latest month StatCan has published, against the same months
# of earlier years. The period labels and the notes' figures are read from
# the warehouse when the dashboard is built, so a rebuild after a data
# refresh keeps them current.
DATASET_LATEST = dataset_id("v_story3_latest_month")
DATASET_YTD = dataset_id("v_story3_ytd_by_year")
DATASET_SHORTFALL = dataset_id("v_story3_ytd_shortfall")
DATASET_PIPELINE = dataset_id("v_story3_pipeline")
DATASET_MARKET = dataset_id("v_story3_intended_market")


def _ytd_facts() -> dict:
    from sqlalchemy import text

    from apply_sql_views import get_engine

    with get_engine().connect() as conn:
        latest = dict(conn.execute(text("SELECT * FROM warehouse.v_story3_latest_month")).mappings().one())
        behind = {(r["comparison_year"], r["activity"]): r["shortfall_pct"] for r in conn.execute(
            text("SELECT * FROM warehouse.v_story3_ytd_shortfall")).mappings()}
        apt = {r["stage"]: r["pct_of_stage"] for r in conn.execute(text(
            "SELECT stage, pct_of_stage FROM warehouse.v_story3_pipeline "
            "WHERE dwelling_type = 'Apartment and Other'")).mappings()}
        market = {(r["period_label"], r["activity"], r["intended_market"]): r for r in conn.execute(
            text("SELECT * FROM warehouse.v_story3_intended_market")).mappings()}
    return {"latest": latest, "behind": behind, "apt": apt, "market": market}


YTD = _ytd_facts()
YTD_LABEL = YTD["latest"]["ytd_label"]  # e.g. "Jan-Sep 2026"
MONTH_LABEL = YTD["latest"]["month_label"]  # e.g. "Sep 2026"
MONTH_FULL = datetime.strptime(MONTH_LABEL, "%b %Y").strftime("%B %Y")  # e.g. "September 2026"
LATEST_YEAR = YTD["latest"]["year"]


def ytd_tile(slice_name: str, sql: str, label: str, subheader: str) -> dict:
    return {
        "slice_name": slice_name,
        "description": (
            f"Windsor CMA, {YTD_LABEL} (StatCan 34-10-0154-01, monthly) -- warehouse.v_story3_latest_month."
        ),
        "dataset_id": DATASET_LATEST,
        "viz_type": "big_number_total",
        "params": {
            "metric": {"expressionType": "SQL", "sqlExpression": sql, "label": label},
            "adhoc_filters": [],
            "y_axis_format": ",d",
            "subheader": subheader,
            "subtitle": subheader,
        },
    }


def grouped_bars(x_axis, groupby: str, sql: str, label: str, number_format: str, filters=None,
                 y_bounds=(0, None), rotate: int = 0) -> dict:
    return {
        "x_axis": x_axis,
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label}],
        "groupby": [groupby],
        "adhoc_filters": filters or [],
        "row_limit": 100,
        "color_scheme": COLOR_SCHEME,
        "show_legend": True,
        "legendOrientation": "top",
        "rich_tooltip": True,
        "show_value": True,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "xAxisLabelRotation": rotate,
        "truncateYAxis": True,
        "y_axis_bounds": list(y_bounds),
        # Series in name order (Superset otherwise puts the largest first). Charts
        # flip the direction with "sort_series_ascending" where the reference
        # dashboard needs it; zero-width-space prefixes do not affect series order
        # on Superset 6.
        "sort_series_type": "name",
        "sort_series_ascending": True,
    }


YEAR_TEXT = {"expressionType": "SQL", "sqlExpression": "CAST(comparison_year AS TEXT)", "label": "Year"}
DWELLING_SHORT = {"expressionType": "SQL", "label": "Dwelling type",
                  "sqlExpression": "CASE dwelling_type WHEN 'Apartment and Other' THEN 'Apartments' "
                                   "ELSE dwelling_type END"}
# Stages in pipeline order (started, completed, under construction): the
# invisible zero-width spaces in front make them sort that way (here the
# reference dashboard's order: under construction, completions, starts).
STAGE_AXIS = {"expressionType": "SQL", "label": "Stage",
              "sqlExpression": "REPEAT(CHR(8203), 4 - stage_sort_order) || CASE stage "
                               "WHEN 'Starts so far' THEN 'YTD Starts' WHEN 'Completions so far' "
                               "THEN 'YTD Completions' ELSE 'Under Construction' END"}
# The pipeline chart's series, named as on the reference dashboard. Sorted
# by name, Z to A, they read starts, completions, then units under
# construction ("Jan-Sep Starts" > "Jan-Sep Completions" > "End-Sep ...").
# Zero-width-space prefixes would not do: Superset 6 sorts series names
# ignoring them, so on apss the order came out reversed.
_STAGE_NAMES = {"Starts so far": f"{YTD_LABEL[:7]} Starts", "Completions so far": f"{YTD_LABEL[:7]} Completions",
                "Under construction": f"End-{MONTH_LABEL[:3]} Under Construction"}
PIPELINE_SERIES = {"expressionType": "SQL", "label": "Stage",
                   "sqlExpression": "CASE stage "
                                    + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in _STAGE_NAMES.items())
                                    + " END"}
# SQL-expression series get no colour from finish_dashboard: name them here.
PROJECT_LABEL_COLORS.update({name: PROJECT_LABEL_COLORS[stage] for stage, name in _STAGE_NAMES.items()})
PROJECT_LABEL_COLORS.update({"Homeowner": "#1FA8C9", "Rental": "#5AC189", "Condo": "#FF7F44"})


def AXIS_TITLES(x: str, y: str) -> dict:  # noqa: N802 -- reads like a constant at the call sites
    return {"x_axis_title": x, "y_axis_title": y, "x_axis_title_margin": 30, "y_axis_title_margin": 40,
            "y_axis_title_position": "Left"}


YTD_CHARTS = {
    "ytd-starts": ytd_tile(f"Windsor Housing Starts, {YTD_LABEL}", "MAX(ytd_starts)", "Starts",
                           "New housing units started"),
    "ytd-completions": ytd_tile(f"Windsor Housing Completions, {YTD_LABEL}", "MAX(ytd_completions)",
                                "Completions", "New housing units completed"),
    "ytd-under-construction": ytd_tile(f"Windsor Units Under Construction, {MONTH_LABEL}",
                                       "MAX(under_construction)", "Under construction",
                                       "Published end-of-month stock"),
    "month-starts": ytd_tile(f"Windsor Housing Starts, {MONTH_LABEL}", "MAX(month_starts)", "Starts",
                             "Monthly housing starts"),
    "month-completions": ytd_tile(f"Windsor Housing Completions, {MONTH_LABEL}", "MAX(month_completions)",
                                  "Completions", "Monthly housing completions"),
    "ytd-shortfall": {
        "slice_name": f"How Far Behind Is {YTD_LABEL}?",
        "description": (
            f"How far Windsor's starts and completions in {YTD_LABEL} are below the same months of each "
            "of the three previous years (positive = behind) -- warehouse.v_story3_ytd_shortfall."
        ),
        "dataset_id": DATASET_SHORTFALL,
        "viz_type": "echarts_timeseries_bar",
        "params": {**grouped_bars(YEAR_TEXT, "activity", "MAX(shortfall_pct)", "Behind by (%)", ",.1f"),
                   **AXIS_TITLES("Comparison year", f"{LATEST_YEAR} shortfall (%)"),
                   "sort_series_ascending": False},  # starts first, as on the reference
    },
    "ytd-pipeline": {
        "slice_name": f"Construction Pipeline by Dwelling Type, {YTD_LABEL}",
        "description": (
            f"Units started and completed in {YTD_LABEL}, and under construction at the end of "
            f"{MONTH_LABEL}, by dwelling type, Windsor CMA -- warehouse.v_story3_pipeline."
        ),
        "dataset_id": DATASET_PIPELINE,
        "viz_type": "echarts_timeseries_bar",
        "params": {**grouped_bars("dwelling_type", PIPELINE_SERIES, "SUM(units)", "Housing units", ",d", rotate=30),
                   **AXIS_TITLES("Dwelling type", "Housing units"),
                   "sort_series_ascending": False},  # Z to A: starts, completions, under construction
    },
    "ytd-mix": {
        "slice_name": f"Dwelling-Type Mix Across the {LATEST_YEAR} Pipeline",
        "description": (
            f"Each stage's units by dwelling type, as a share of that stage: starts and completions in "
            f"{YTD_LABEL}, and units under construction at the end of {MONTH_LABEL} -- "
            "warehouse.v_story3_pipeline."
        ),
        "dataset_id": DATASET_PIPELINE,
        "viz_type": "echarts_timeseries_bar",
        "params": {**grouped_bars(STAGE_AXIS, "dwelling_type", "MAX(pct_of_stage)", "Share of the stage (%)",
                                  ",.1f", y_bounds=(0, 80), rotate=20),  # tilted so all three stages show
                   **AXIS_TITLES("Construction stage", "Share of housing units (%)")},
    },
    "ytd-multi-unit": {
        "slice_name": f"Multi-Unit Share of Housing Activity, {YTD_LABEL[:7]} {2021}-{LATEST_YEAR}",
        "description": (
            "Share of the starts and completions in the same months of each year that are anything but "
            "single-detached houses (semis, row houses, apartments). Windsor's CMHC geography changed "
            "in January 2023 -- warehouse.v_story3_ytd_by_year."
        ),
        "dataset_id": DATASET_YTD,
        "viz_type": "echarts_timeseries_line",
        "params": {
            **grouped_bars({"expressionType": "SQL", "sqlExpression": "CAST(period_year AS TEXT)", "label": "Year"},
                           "activity", "MAX(multi_unit_share_pct)", "Multi-unit share (%)", ",.1f",
                           filters=[eq_filter("dwelling_type", "Total")], y_bounds=(0, 100)),
            **AXIS_TITLES("Year", "Multi-unit share (%)"),
            "sort_series_ascending": False,  # starts first, as on the reference
            "seriesType": "line",
            "markerEnabled": True,
            "markerSize": 6,
        },
    },
}
YTD_CHARTS["ytd-full-year"] = {
    "slice_name": f"Full-Year Housing Starts vs Completions, {LATEST_YEAR - 5}-{LATEST_YEAR - 1}",
    "description": (
        "Windsor CMA housing starts and completions in each of the last five full years, all "
        "dwelling types -- warehouse.v_story3_windsor_supply_annual."
    ),
    "dataset_id": DATASET_ANNUAL,
    "viz_type": "echarts_timeseries_bar",
    "params": {
        **grouped_bars("year_label", "activity", "SUM(units)", "Housing units", ",d",
                       filters=[FLOWS, TOTAL_ONLY, FULL_YEARS,
                                {"clause": "WHERE", "expressionType": "SQL",
                                 "sqlExpression": f"year_label >= '{LATEST_YEAR - 5}'"}]),
        **AXIS_TITLES("Year", "Housing units"),
        "sort_series_ascending": False,  # starts first, as on the reference
    },
}
CHARTS.update(YTD_CHARTS)

# --- Tab "Pipeline and Intended Market" -------------------------------------
# This year's starts and completions so far by the market they are built for
# (CMHC Housing Market Information Portal), as on the reference dashboard:
# the markets across, in the portal's order, starts and completions as bars.
_M = YTD["market"]
MARKET_YTD = next(p for (p, _a, _m), r in _M.items() if r["is_ytd"])  # e.g. "Jan-Sep 2026"
MARKET_AXIS = {"expressionType": "SQL", "label": "Intended market",
               "sqlExpression": "REPEAT(CHR(8203), market_sort_order) || market_label"}
MARKET_CHARTS = {
    "market-units": {
        "slice_name": f"Intended Market of {MARKET_YTD} Housing Supply",
        "description": (
            f"Windsor CMA housing starts and completions in {MARKET_YTD} by the market they are built "
            "for: homeownership (freehold houses), rental, co-op and condominium (CMHC Starts and "
            "Completions Survey, Housing Market Information Portal) -- warehouse.v_story3_intended_market."
        ),
        "dataset_id": DATASET_MARKET,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            **grouped_bars(MARKET_AXIS, "activity", "SUM(units)", "Housing units", ",d", rotate=30,
                           filters=[{"clause": "WHERE", "expressionType": "SQL", "sqlExpression": "is_ytd"}]),
            **AXIS_TITLES("Intended market", f"{MARKET_YTD[:7]} housing units"),
            "sort_series_ascending": False,  # starts first, as on the reference
        },
    },
}
CHARTS.update(MARKET_CHARTS)


def _units(activity: str, market: str) -> float:
    return _M[(MARKET_YTD, activity, market)]["units"]


def _share(activity: str, market: str) -> float:
    return _M[(MARKET_YTD, activity, market)]["share_pct"]


MARKET_NOTE = (
    f"**Pipeline.** {YTD['latest']['under_construction']:,} units were under construction at the end of "
    f"{MONTH_LABEL[:3]}, down from {YTD['latest']['under_construction_previous_month']:,} a month earlier. "
    f"**Intended market.** From January to {MONTH_LABEL}, **{_units('Completions', 'Rental'):,.0f} rental "
    f"homes** were completed (**{_share('Completions', 'Rental'):.0f}%** of completions) but only "
    f"{_units('Starts', 'Rental'):,.0f} started; **{_units('Starts', 'Homeowner'):,.0f}** of the "
    f"{_units('Starts', 'Homeowner') + _units('Starts', 'Rental'):,.0f} starts are for homeownership. "
    f"{_units('Completions', 'Condo'):,.0f} condos were completed and none started. *CMHC reports \"-\" as nil; "
    "co-op and not-available markets recorded no starts or completions. Source: CMHC Starts and "
    "Completions Survey (Housing Market Information Portal), Windsor CMA.*\n"
)

_L, _B = YTD["latest"], YTD["behind"]
_prev = LATEST_YEAR - 1
YTD_NOTE = (
    f"**What it shows.** From January to {MONTH_LABEL}, Windsor started **{_L['ytd_starts']:,}** homes and "
    f"completed **{_L['ytd_completions']:,}**; **{_L['under_construction']:,}** were under construction at the "
    f"end of {MONTH_LABEL[:3]}, down from {_L['under_construction_previous_month']:,} a month earlier. "
    f"Starts are **{_B[(_prev, 'Starts')]:.0f}% behind** the same months of {_prev} and "
    f"{_B[(_prev - 1, 'Starts')]:.0f}% behind {_prev - 1}, when the 2024 surge began; completions are "
    f"{_B[(_prev, 'Completions')]:.0f}% behind {_prev}.\n"
)
MIX_NOTE = (
    f"**What it shows.** Apartments are **{YTD['apt']['Under construction']:.0f}%** of what is under "
    f"construction and **{YTD['apt']['Completions so far']:.0f}%** of this year's completions, but only "
    f"**{YTD['apt']['Starts so far']:.0f}%** of this year's starts: the apartment wave of 2023-2025 is "
    "being finished, and fewer new ones are starting. *CMHC adopted 2021 Census geography for Windsor in "
    "January 2023, so compare 2021-2022 with 2023 onward with caution; CMHC reports \"-\" as nil.*\n"
)


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
    ("HEADER-ytd", f"{YTD_LABEL} So Far: Windsor's Housing Activity This Year"),
    ("ROW-ytd-kpi", [("ytd-starts", 2), ("ytd-completions", 3), ("ytd-under-construction", 3),
                     ("month-starts", 2), ("month-completions", 2)]),
    ("ROW-ytd", [("ytd-full-year", 6), ("ytd-shortfall", 6)]),
    ("MARKDOWN-ytd", (YTD_NOTE, 14)),
    ("HEADER-ytd-mix", f"Housing Mix: What Is Being Started, Built and Finished in {LATEST_YEAR}"),
    ("ROW-ytd-mix", [("ytd-mix", 6), ("ytd-multi-unit", 6)]),
    ("MARKDOWN-ytd-mix", (MIX_NOTE, 16)),
    ("HEADER-market", "Current Pipeline and Intended Market"),
    ("ROW-market", [("ytd-pipeline", 6), ("market-units", 6)]),
    ("MARKDOWN-market", (MARKET_NOTE, 16)),
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
    ("TAB-ytd", "This Year So Far", ["HEADER-ytd", "ROW-ytd-kpi", "ROW-ytd", "ROW-MARKDOWN-ytd"]),
    ("TAB-ytd-mix", "This Year's Mix", ["HEADER-ytd-mix", "ROW-ytd-mix", "ROW-MARKDOWN-ytd-mix"]),
    ("TAB-market", "Pipeline and Intended Market", ["HEADER-market", "ROW-market", "ROW-MARKDOWN-market"]),
]


# Shorter titles on the dashboard for the KPI tiles: the Year filter's badge
# takes part of the title bar, which cut the full names off.
TITLE_OVERRIDES = {
    "kpi-starts": "Homes started",
    "kpi-completions": "Homes completed",
    "kpi-under-construction": "Under construction",
    "kpi-per-1000": "Starts per 1,000 households",
    "ytd-starts": f"{YTD_LABEL} Housing Starts",
    "ytd-completions": f"{YTD_LABEL} Housing Completions",
    "ytd-under-construction": f"Under Construction, {MONTH_LABEL}",
    "month-starts": f"{MONTH_FULL} Starts",
    "month-completions": f"{MONTH_FULL} Completions",
}
# Taller than CHART_HEIGHT where a chart is alone in its tab.
HEIGHTS = {"trend": 50, "per-1000": 50, "starts-mix": 72, "ytd-starts": 26, "ytd-completions": 26, "ytd-under-construction": 26,
           "month-starts": 26, "month-completions": 26, "ytd-shortfall": 50,
           "ytd-mix": 62, "ytd-multi-unit": 62, "market-units": 62, "ytd-full-year": 50,
           "ytd-pipeline": 62}


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
    match_bar_order(prefix_names(CHARTS))
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
