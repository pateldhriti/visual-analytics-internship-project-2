"""
Build the Story 2 Superset dashboard ("What is happening in Windsor's
rental market?"): a 4-tile KPI section (Average Rent, Vacancy, Turnover,
Rental Stock), a zone-level section (rental stock, vacancy, vacancy over
time and a 4-metric snapshot table per zone, alongside rent by zone and
bedroom type), rent and vacancy over the
project's real 6-year span (Oct-20 to Oct-25 -- not 10 years, see
sql/story2_views.sql's own header comment), turnover by bedroom type,
vacancy by dwelling type, with native filters for zone, bedroom type,
and dwelling scope.

No Period filter is included: every chart with multiple real periods
uses period as its own trend axis (filtering to one period would
collapse the trend), and every chart without that is already anchored
to the latest real survey (Oct-25) for good reason, not an oversight --
confirmed by checking each chart's own params, not assumed.

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

Review pass (labels, units and filter defaults):
  - Rents are monthly and cover apartments and row houses ("Combined");
    every rent label and KPI subheader now says so.
  - The zone snapshot table shows readable column names (set as the
    dataset's column labels) and $ / % formats instead of raw names and
    plain numbers.
  - Filter defaults: "Dwelling Scope" starts on Apartment + Combined
    (row-house figures are mostly suppressed by CMHC); "Bedroom Type" no
    longer offers "Total", which every chart in its scope excludes and so
    always returned an empty chart. Every filter has a description, and
    filter ids are fixed so a re-run doesn't reset saved filter state.
  - A "About the Data" note explains reliability letters, suppression and
    what the survey covers.

Requires the 7 Story 2 views already registered as Superset datasets
(etl/register_superset_datasets.py) and Superset running.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\build_story2_dashboard.py
"""

import json
import re
import uuid

from dashboard_tabs import add_tabs
from setup_superset_dashboard import SUPERSET_URL, dataset_id, find_existing, get_session
from superset_compat import COLOR_SCHEME, SHARED, finish_dashboard, heatmap, trendline_kpi, upgrade_legacy_bars

# Dataset ids, from etl/register_superset_datasets.py's own output --
# re-verify with `SELECT id, table_name FROM tables` if this script is
# ever run against a fresh environment where ids may differ.
DATASET_RENT_YOY = dataset_id("v_story2_rent_yoy_change")
DATASET_VACANCY = dataset_id("v_story2_vacancy_trend")
DATASET_TURNOVER = dataset_id("v_story2_turnover_by_bedroom")
DATASET_RENT_ZONE = dataset_id("v_story2_rent_by_zone_bedroom")
# v_dashboard1_rental_yoy -- built for Dashboard 1, reused here rather than
# duplicated: it's the only registered view with a "universe" (rental
# stock) row at all. No Story 2 view carries that column (confirmed
# against sql/story2_views.sql) -- fabricating a new one just to avoid
# reuse would mean a second view computing the same real
# fact_rental_market rows the Dashboard 1 one already does.
DATASET_RENTAL_YOY = dataset_id("v_dashboard1_rental_yoy")
DATASET_ZONE_SNAPSHOT = dataset_id("v_story2_zone_snapshot")
DATASET_ZONE_VACANCY = dataset_id("v_story2_vacancy_by_zone_trend")

# windsor_housing here, Superset's default on the shared server (superset_compat).

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


DATASET_ZONE_EXPLANATION = dataset_id("v_story2_zone_explanation")  # (all unit sizes)

# The explanation panel's dataset: a virtual (SQL) dataset over
# warehouse.v_story2_zone_bedroom_explanation that keeps one unit size --
# the one chosen in the Bedroom Type filter (or clicked in a unit-size
# chart), else 'Total' (all unit sizes) -- so the panel recalculates when
# the filter changes. filter_values() is Superset's Jinja macro for the
# values of an active filter (needs ENABLE_TEMPLATE_PROCESSING, see
# docker/superset_config.py). The chosen value is only compared with a
# fixed list, never pasted into the SQL as typed.
PANEL_DATASET_NAME = "story2_panel_by_unit_size"
PANEL_DATASET_SQL = """{% set allowed = ['Studio', '1 Bedroom', '2 Bedroom', '3 Bedroom +', 'Total'] %}
{% set chosen = filter_values('bedroom_type_label') %}
{% set unit = chosen[0] if chosen and chosen[0] in allowed else 'Total' %}
SELECT *
FROM warehouse.v_story2_zone_bedroom_explanation
WHERE bedroom_type_label = '{{ unit }}'"""

ACCENT = "#2a78d6"  # the project's blue accent (slot 1 of windsor_housing)
# The windsor_housing palette (docker/superset_config.py), as Superset
# stores it in color_scheme_domain.
COLOR_DOMAIN = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ZONES = [
    "Zone 1 - Centre",
    "Zone 2 - East Inner",
    "Zone 3 - East Outer",
    "Zone 4 - West",
    "Zone 5 - Amherstburg",
    "Zone 6 - North Essex County",
    "Zone 7 - South Essex County",
]
ZONE_COLORS = dict(zip(ZONES, COLOR_DOMAIN))


def zone_bar_params(sql: str, label: str, number_format: str) -> dict:
    """Horizontal ECharts bar, one bar per zone, clickable.

    In Superset 3.1 an ECharts bar chart emits a cross-filter for the
    *series* (group-by) value of the clicked bar, not for its x-axis
    category -- clicking a plain one-series bar does nothing (tested). So
    the zone is also the series: each zone is its own series, stacked so
    every bar keeps its full width, and a click emits that zone. Each zone
    also keeps the same colour as its line in the zone trend chart."""
    return {
        # Same column under another label: Superset rejects a query whose
        # x-axis and series have the same label.
        "x_axis": {"expressionType": "SQL", "sqlExpression": "zone_label", "label": "Zone"},
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label}],
        "groupby": ["zone_label"],
        "stack": True,
        "adhoc_filters": [],
        "orientation": "horizontal",
        "row_limit": 50,
        "color_scheme": COLOR_SCHEME,
        "show_value": True,
        "show_legend": False,
        # Item tooltip: each zone is its own series, so the default
        # all-series tooltip listed 7 rows with 6 of them empty.
        "rich_tooltip": False,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "truncateYAxis": False,
        "y_axis_bounds": [None, None],
    }


def echarts_params(
    viz: str,
    x_axis: str,
    sql: str,
    label: str,
    number_format: str,
    groupby: list | None = None,
    filters: list | None = None,
    rotate: int = 0,
) -> dict:
    """ECharts bar/line chart with a category x-axis. With a group-by
    (series) the rows are pivoted on the x-axis, which sorts survey labels
    Oct-20 ... Oct-25 oldest first -- the legacy charts sorted by value."""
    params = {
        "x_axis": x_axis,
        "metrics": [{"expressionType": "SQL", "sqlExpression": sql, "label": label}],
        "groupby": groupby or [],
        "adhoc_filters": filters or [],
        "row_limit": 100,
        "color_scheme": COLOR_SCHEME,
        "show_legend": bool(groupby),
        "legendType": "scroll",
        "legendOrientation": "top",
        "rich_tooltip": True,
        "tooltipSortByMetric": True,
        "y_axis_format": number_format,
        "x_axis_title": "",
        "y_axis_title": "",
        "xAxisLabelRotation": rotate,
        "truncateYAxis": False,
        "y_axis_bounds": [None, None],
    }
    if viz == "line":
        params.update({"markerEnabled": True, "markerSize": 6, "seriesType": "line", "connectNulls": False})
    else:
        params.update({"show_value": False})
    return params


EXPLANATION_COLUMNS = [
    "zone_label", "bedroom_type_label", "unit_label", "average_rent",
    "rent_text", "vacancy_text", "units_text", "turnover_text",
    "cma_rent_text", "cma_vacancy_text", "cma_units_text", "cma_turnover_text",
    "priciest_zone", "priciest_rent_text", "cheapest_zone", "cheapest_rent_text",
    "tightest_zone", "tightest_vacancy_text", "largest_zone", "largest_units_text",
    "rent_vs_text", "vacancy_vs_text", "turnover_vs_text", "units_vs_text", "rank_text",
    "size_rank_text", "rent_bullet", "vacancy_bullet", "stock_bullet", "turnover_bullet",
    "reliability_note", "takeaway", "overview_takeaway",
]

# Rendered by Superset's Handlebars chart from the panel's query result
# ("data" = the rows left after the Zone filter and any cross-filter).
# Four sections: Zone Overview, Key Numbers, What This Means, Key Takeaway.
# 2+ rows: the Windsor-wide version; 1 row: the selected zone against
# Windsor; 0 rows: a message. Every value and sentence is a column of
# warehouse.v_story2_zone_explanation, computed from the survey data.
# Class names are replaced by inline styles below (INLINE_STYLES).
EXPLANATION_TEMPLATE = """{{#if data.[1]}}{{#with data.[0]}}
<div class="xp">
<div class="xp-sec">Zone overview</div>
<div class="xp-name">All 7 zones &middot; Windsor CMA</div>
<div class="xp-cta">&#128070; Click a zone in the table or a chart, or pick one in the Zone filter, to explain it here. Bedroom Type switches the figures to one unit size.</div>
<div class="xp-sec">Key numbers &middot; Oct 2025 &middot; {{unit_label}}</div>
<div class="xp-tiles">
<div class="xp-tile"><span class="xp-l">Average rent</span><span class="xp-v">{{cma_rent_text}}</span><span class="xp-d">per month</span></div>
<div class="xp-tile"><span class="xp-l">Vacancy</span><span class="xp-v">{{cma_vacancy_text}}</span><span class="xp-d">of units vacant</span></div>
<div class="xp-tile"><span class="xp-l">Rental units</span><span class="xp-v">{{cma_units_text}}</span><span class="xp-d">purpose-built</span></div>
<div class="xp-tile"><span class="xp-l">Turnover</span><span class="xp-v">{{cma_turnover_text}}</span><span class="xp-d">changed tenants</span></div>
</div>
<div class="xp-sec">What this means</div>
<div class="xp-li">&bull; Most expensive: <strong>{{priciest_zone}}</strong> ({{priciest_rent_text}})</div>
<div class="xp-li">&bull; Least expensive: <strong>{{cheapest_zone}}</strong> ({{cheapest_rent_text}})</div>
<div class="xp-li">&bull; Tightest market: <strong>{{tightest_zone}}</strong> ({{tightest_vacancy_text}} vacant)</div>
<div class="xp-li">&bull; Most units: <strong>{{largest_zone}}</strong> ({{largest_units_text}})</div>
<div class="xp-sec">Key takeaway</div>
<div class="xp-take">{{overview_takeaway}}</div>
</div>
{{/with}}{{else}}{{#if data.[0]}}{{#with data.[0]}}
<div class="xp">
<div class="xp-sec">Zone overview</div>
<div class="xp-name">{{zone_label}}</div>
<div class="xp-chips"><span class="xp-chip">{{rank_text}}</span><span class="xp-chip">{{units_vs_text}}</span></div>
<div class="xp-sec">Key numbers &middot; Oct 2025 &middot; {{unit_label}}</div>
<div class="xp-tiles">
<div class="xp-tile"><span class="xp-l">Average rent</span><span class="xp-v">{{rent_text}}</span><span class="xp-d">{{rent_vs_text}} ({{cma_rent_text}})</span></div>
<div class="xp-tile"><span class="xp-l">Vacancy</span><span class="xp-v">{{vacancy_text}}</span><span class="xp-d">{{vacancy_vs_text}} ({{cma_vacancy_text}})</span></div>
<div class="xp-tile"><span class="xp-l">Rental units</span><span class="xp-v">{{units_text}}</span><span class="xp-d">{{size_rank_text}}</span></div>
<div class="xp-tile"><span class="xp-l">Turnover</span><span class="xp-v">{{turnover_text}}</span><span class="xp-d">{{turnover_vs_text}} ({{cma_turnover_text}})</span></div>
</div>
<div class="xp-sec">What this means</div>
<div class="xp-li">&bull; {{rent_bullet}}</div>
<div class="xp-li">&bull; {{vacancy_bullet}}</div>
<div class="xp-li">&bull; {{stock_bullet}}</div>
<div class="xp-li">&bull; {{turnover_bullet}}</div>
{{#if reliability_note}}<div class="xp-note">{{reliability_note}}</div>{{/if}}
<div class="xp-sec">Key takeaway</div>
<div class="xp-take">{{takeaway}}</div>
<div class="xp-clear"><a class="xp-reset" href="?standalone=2">&#8634; Reset to all zones</a> or click {{zone_label}} again.</div>
</div>
{{/with}}{{else}}
<div class="xp"><div class="xp-sec">Zone overview</div><div class="xp-name">No data for this selection</div><div class="xp-cta">CMHC publishes no zone figures for the current filters and selection. <a class="xp-reset" href="?standalone=2">&#8634; Reset the dashboard</a></div></div>
{{/if}}{{/if}}"""

# Superset 3.1 sanitizes Handlebars output: it drops <style> tags and, by
# default, every attribute. docker/superset_config.py allows the inline
# `style` attribute only (HTML_SANITIZATION_SCHEMA_EXTENSIONS), so the
# template's class names are turned into inline styles here.
INLINE_STYLES = {
    "xp": "color:#1d2433;font-size:13px;line-height:1.4;padding:0 2px;",
    "xp-sec": (
        f"color:{ACCENT};font-size:11px;font-weight:700;letter-spacing:.07em;"
        "text-transform:uppercase;margin:12px 0 5px;padding-bottom:3px;border-bottom:1px solid #e3e9f2;"
    ),
    "xp-name": "font-size:20px;font-weight:800;line-height:1.2;margin:2px 0 6px;",
    "xp-cta": f"background:#eef5fd;border:1px dashed {ACCENT};border-radius:8px;padding:6px 9px;font-size:12px;color:#1d2433;",
    "xp-chips": "display:flex;flex-wrap:wrap;gap:6px;",
    "xp-chip": f"background:#eef5fd;color:{ACCENT};border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;",
    "xp-tiles": "display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;",
    "xp-tile": f"border:1px solid #e3e9f2;border-left:3px solid {ACCENT};border-radius:8px;padding:5px 9px;background:#fbfcfe;",
    "xp-l": "display:block;color:#5f6b7d;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;",
    "xp-v": "display:block;font-size:18px;font-weight:800;line-height:1.25;",
    "xp-d": "display:block;color:#5f6b7d;font-size:11px;",
    "xp-li": "margin:0 0 3px;",
    "xp-note": "margin:5px 0 0;padding:5px 8px;background:#fff6e0;border-radius:6px;font-size:11.5px;",
    "xp-take": f"background:{ACCENT};color:#ffffff;border-radius:8px;padding:8px 10px;font-weight:600;",
    "xp-clear": "margin-top:8px;color:#5f6b7d;font-size:11.5px;",
    "xp-reset": (
        f"display:inline-block;background:#ffffff;border:1px solid {ACCENT};color:{ACCENT};"
        "border-radius:999px;padding:2px 10px;font-weight:700;text-decoration:none;margin-right:4px;"
    ),
}

EXPLANATION_TEMPLATE = re.sub(
    r'class="([a-z-]+)"', lambda m: f'style="{INLINE_STYLES[m.group(1)]}"', EXPLANATION_TEMPLATE
)

CHART_GUIDE_MARKDOWN = """**How to read this dashboard**

- **Interact:** click a zone in the *Zone Snapshot* table, a zone bar or a zone trend line. The
  other zone charts and the explanation panel switch to that zone. To see every zone again, click
  it a second time or the ✕ next to it under **Cross-filters** in the filter bar. The filters on
  the left (Zone, Bedroom Type, Dwelling Scope) narrow the charts too; **Clear all** resets them.
- **Zone Snapshot** compares the 7 zones on rent, vacancy, size and turnover; the bar inside each
  cell shows how each zone compares with the others.
- **Rental Stock by Zone** shows where the rental housing is. Bigger zones affect the Windsor
  average more.
- **Vacancy Rate by Zone:** a lower rate means a tighter market, where fewer units are free and
  rents tend to rise faster.
- **Average Rent by Zone and Bedroom Type** shows what each unit size costs in each zone.
- **Trend lines** follow each survey from October 2020 to October 2025, oldest first. Hover a
  point for exact values. Clicking a unit-size line or bar filters the other unit-size charts.
- **Turnover** is the share of units whose tenant changed in the past year.
"""


# Each entry: internal key, slice_name, dataset id, viz_type, params.
# KPI tiles are "big_number_total" (same viz_type Story 1's KPI tiles
# use); everything else is "dist_bar".
CHARTS = {
    # Rent and vacancy show October 2025 with every October since 2020 as a
    # trendline underneath. Vacancy has no "% change" line: a percent change
    # of a rate (3.5% to 3.6% = +2.9%) reads as if vacancy rose 2.9 points.
    "kpi-vacancy": {
        "slice_name": "Windsor CMA Vacancy Rate",
        "description": "Share of purpose-built rental units (apartments and row houses) vacant and available, October 2025, with every October since 2020 underneath. CMHC Rental Market Survey -- warehouse.v_story2_vacancy_trend.",
        "dataset_id": DATASET_VACANCY,
        **dict(zip(("viz_type", "params"), trendline_kpi(
            {"expressionType": "SQL", "sqlExpression": "AVG(vacancy_rate_pct) / 100.0", "label": "Vacancy Rate"},
            "period_date", [combined_filter(), bedroom_filter("Total")], ".1%", None, "",
        ))),
    },
    "kpi-rent": {
        "slice_name": "Windsor CMA Average Rent",
        "description": "Average monthly rent across all unit sizes, apartments and row houses (Combined), October 2025, with every October since 2020 underneath and the change since October 2020. CMHC Rental Market Survey -- warehouse.v_story2_rent_yoy_change.",
        "dataset_id": DATASET_RENT_YOY,
        **dict(zip(("viz_type", "params"), trendline_kpi(
            {"expressionType": "SQL", "sqlExpression": "AVG(average_rent)", "label": "Average Rent"},
            "period_date", [bedroom_filter("Total")], "$,.0f", 5, " since Oct-20",
        ))),
    },
    "kpi-turnover": {
        "slice_name": "Windsor CMA Turnover Rate",
        "description": "Share of occupied units whose tenant changed in the past 12 months, apartments and row houses, October 2025. CMHC Rental Market Survey -- warehouse.v_story2_turnover_by_bedroom.",
        "dataset_id": DATASET_TURNOVER,
        "viz_type": "big_number_total",
        "params": {
            "metric": {
                "expressionType": "SQL",
                "sqlExpression": "AVG(turnover_rate_pct) / 100.0",
                "label": "Turnover Rate",
            },
            "adhoc_filters": [combined_filter(), bedroom_filter("Total"), period_filter("Oct-25")],
            "y_axis_format": ".1%",
            "subheader": "Windsor benchmark · all units",
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
            "subheader": "Windsor benchmark · all units",
        },
    },
    "vacancy-dwelling": {
        "slice_name": "Vacancy Rate by Period and Dwelling Type (Oct-20 to Oct-25)",
        "description": (
            "Vacancy rate each October from 2020 to 2025 for apartments, and for apartments and row "
            "houses combined (all unit sizes). The two lines move together, so the Combined figures "
            "used elsewhere are a fair guide -- warehouse.v_story2_vacancy_trend."
        ),
        "dataset_id": DATASET_VACANCY,
        "viz_type": "echarts_timeseries_line",
        "params": echarts_params(
            "line", "period_label", "AVG(vacancy_rate_pct) / 100.0", "Vacancy rate", ".1%",
            groupby=["dwelling_type_label"], filters=[bedroom_filter("Total")],
        ),
    },
    "rent-zone": {
        "slice_name": "Average Rent by Zone and Bedroom Type",
        "description": (
            "Average monthly rent by zone and unit size, October 2025, apartments and row houses. "
            "Compare bars within a zone to see the price step between unit sizes. Missing bars are "
            "values CMHC suppressed. Click a unit size to filter the other unit-size charts -- "
            "warehouse.v_story2_rent_by_zone_bedroom."
        ),
        "dataset_id": DATASET_RENT_ZONE,
        "viz_type": "echarts_timeseries_bar",
        "params": echarts_params(
            "bar", "zone_label", "AVG(average_rent)", "Average monthly rent", "$,.0f",
            groupby=["bedroom_type_label"], filters=[EXCLUDE_TOTAL_BEDROOM], rotate=30,
        ),
    },
    "zone-stock": {
        "slice_name": "Rental Stock by Zone (Oct-25)",
        "description": (
            "Purpose-built rental units in each zone, October 2025, apartments and row houses. "
            "Shows where Windsor's rental housing is. Click a bar to explore that zone. "
            "The 7 zones sum to the Windsor CMA total (19,883) -- warehouse.v_story2_zone_snapshot."
        ),
        "dataset_id": DATASET_ZONE_SNAPSHOT,
        "viz_type": "echarts_timeseries_bar",
        "params": zone_bar_params("SUM(rental_universe)", "Rental units", ",.0f"),
    },
    "zone-vacancy": {
        "slice_name": "Vacancy Rate by Zone (Oct-25)",
        "description": (
            "Share of each zone's rental units that were empty and available, October 2025. "
            "Lower means a tighter market where it is harder to find a unit. Click a bar to "
            "explore that zone -- warehouse.v_story2_zone_snapshot."
        ),
        "dataset_id": DATASET_ZONE_SNAPSHOT,
        "viz_type": "echarts_timeseries_bar",
        "params": zone_bar_params("AVG(vacancy_rate_pct) / 100.0", "Vacancy rate", ".1%"),
    },
    "zone-vacancy-trend": {
        "slice_name": "Vacancy Rate by Zone and Period (Oct-20 to Oct-25)",
        "description": (
            "Vacancy rate in each zone (rows) every October from 2020 to 2025 (columns), apartments "
            "and row houses. Darker cells are looser markets, lighter cells tighter. Zone 7 has no "
            "data before Oct-23 and two Zone 5 values are suppressed by CMHC; blank cells are not "
            "zeros -- warehouse.v_story2_vacancy_by_zone_trend."
        ),
        "dataset_id": DATASET_ZONE_VACANCY,
        # A heatmap instead of seven crossing lines: every zone and year at once.
        **dict(zip(("viz_type", "params"), heatmap(
            "period_label", "zone_label",
            {"expressionType": "SQL", "sqlExpression": "AVG(vacancy_rate_pct) / 100.0", "label": "Vacancy rate"},
            # Suppressed values are left out, not drawn as a (black) cell.
            [{"clause": "WHERE", "expressionType": "SQL", "sqlExpression": "vacancy_rate_pct IS NOT NULL"}],
            ".1%",
        ))),
    },
    "zone-table": {
        "slice_name": "Zone Snapshot: Rent, Vacancy, Stock and Turnover (Oct-25)",
        "description": (
            "One row per zone, October 2025, apartments and row houses. The bars inside each "
            "column compare the zones at a glance. Click a zone name to filter the rest of the "
            "dashboard to it; click it again to clear -- warehouse.v_story2_zone_snapshot."
        ),
        "dataset_id": DATASET_ZONE_SNAPSHOT,
        "viz_type": "table",
        "params": {
            # Aggregate mode (one row per zone): a Table chart emits a
            # cross-filter when a value in a group-by column is clicked.
            "query_mode": "aggregate",
            "groupby": ["zone_label"],
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "MAX(average_rent)", "label": "Average monthly rent"},
                {"expressionType": "SQL", "sqlExpression": "MAX(vacancy_rate_pct) / 100.0", "label": "Vacancy rate"},
                {"expressionType": "SQL", "sqlExpression": "SUM(rental_universe)", "label": "Rental units"},
                {"expressionType": "SQL", "sqlExpression": "MAX(share_of_zone_stock_pct) / 100.0", "label": "Share of Windsor's units"},
                {"expressionType": "SQL", "sqlExpression": "MAX(turnover_rate_pct) / 100.0", "label": "Turnover rate"},
            ],
            "all_columns": [],
            "percent_metrics": [],
            "timeseries_limit_metric": {
                "expressionType": "SQL",
                "sqlExpression": "MAX(average_rent)",
                "label": "Average monthly rent",
            },
            "order_desc": True,
            "row_limit": 10,
            "server_pagination": False,
            "include_search": False,
            "show_cell_bars": True,
            "color_pn": False,
            "allow_rearrange_columns": False,
            "column_config": {
                "Average monthly rent": {"d3NumberFormat": "$,.0f"},
                "Vacancy rate": {"d3NumberFormat": ".1%"},
                "Rental units": {"d3NumberFormat": ",.0f"},
                "Share of Windsor's units": {"d3NumberFormat": ".1%"},
                "Turnover rate": {"d3NumberFormat": ".1%"},
            },
        },
    },
    "zone-explain": {
        "slice_name": "What the Zone Data Says",
        "description": (
            "Explanation panel. With no zone selected it summarizes Windsor; select a zone (click "
            "a zone bar or table row, or use the Zone filter) and it explains that zone against "
            "Windsor CMA. Choosing a Bedroom Type recalculates it for that unit size. Every figure "
            "and sentence is computed in warehouse.v_story2_zone_bedroom_explanation from CMHC's "
            "October 2025 survey."
        ),
        "dataset_id": DATASET_ZONE_EXPLANATION,
        "viz_type": "handlebars",
        "params": {
            "query_mode": "raw",
            "all_columns": EXPLANATION_COLUMNS,
            "order_by_cols": ['["average_rent", false]'],
            "row_limit": 10,
            "server_pagination": False,
            "handlebarsTemplate": EXPLANATION_TEMPLATE,
            "styleTemplate": "",
        },
    },
    "rent-trend": {
        "slice_name": "Average Rent by Period and Bedroom Type (Oct-20 to Oct-25)",
        "description": (
            "Average monthly rent for each unit size every October from 2020 to 2025, apartments and "
            "row houses. Every line rises: rent went up each year. CMHC does not publish 3-bedroom+ "
            "rent for every year -- warehouse.v_story2_rent_yoy_change."
        ),
        "dataset_id": DATASET_RENT_YOY,
        "viz_type": "echarts_timeseries_line",
        "params": echarts_params(
            "line", "period_label", "AVG(average_rent)", "Average monthly rent", "$,.0f",
            groupby=["bedroom_type_label"], filters=[EXCLUDE_TOTAL_BEDROOM],
        ),
    },
    "vacancy-trend": {
        "slice_name": "Vacancy Rate by Period and Bedroom Type (Oct-20 to Oct-25)",
        "description": (
            "Vacancy rate for each unit size every October from 2020 to 2025, apartments and row "
            "houses. All sizes dipped to their lowest around 2022 and recovered by 2025 -- "
            "warehouse.v_story2_vacancy_trend."
        ),
        "dataset_id": DATASET_VACANCY,
        "viz_type": "echarts_timeseries_line",
        "params": echarts_params(
            "line", "period_label", "AVG(vacancy_rate_pct) / 100.0", "Vacancy rate", ".1%",
            groupby=["bedroom_type_label"], filters=[combined_filter(), EXCLUDE_TOTAL_BEDROOM],
        ),
    },
    "turnover": {
        "slice_name": "Turnover Rate by Bedroom Type (Oct-25)",
        "description": (
            "Share of units in each size whose tenant changed in the past year, October 2025. Small "
            "units turn over most; households in 3-bedroom+ units stay longest -- "
            "warehouse.v_story2_turnover_by_bedroom."
        ),
        "dataset_id": DATASET_TURNOVER,
        "viz_type": "echarts_timeseries_bar",
        "params": {
            **echarts_params(
                "bar", "bedroom_type_label", "AVG(turnover_rate_pct) / 100.0", "Turnover rate", ".1%",
                filters=[combined_filter(), EXCLUDE_TOTAL_BEDROOM, period_filter("Oct-25")],
            ),
            "show_value": True,
            # Highest turnover first, instead of alphabetical (Studio last).
            "x_axis_sort": "Turnover rate",
            "x_axis_sort_asc": False,
        },
    },
}

DASHBOARD_TITLE = "Story 2: What is happening in Windsor's rental market?"

# Readable column names for the zone snapshot table, set as the dataset's
# column labels (Superset's table chart shows a column's label as its
# header).
# The explanation panel on the university's shared Superset, where template
# processing (the panel's per-unit-size dataset) and styled HTML (the
# Handlebars layout) are switched off and cannot be turned on by a user: a
# table of the same SQL-computed sentences, one row per zone, all unit sizes.
# It still narrows to the zone picked in the Zone filter or clicked in a
# zone chart.
SIMPLE_PANEL = {
    "slice_name": "What the Zone Data Says",
    "description": (
        "What each zone's figures mean against Windsor CMA, all unit sizes, October 2025. Select a zone "
        "(click a zone bar or table row, or use the Zone filter) to see only that zone. Every sentence "
        "is computed in warehouse.v_story2_zone_explanation from CMHC's survey."
    ),
    "dataset_id": DATASET_ZONE_EXPLANATION,
    "viz_type": "table",
    "params": {
        "query_mode": "raw",
        "all_columns": ["zone_label", "takeaway", "rent_vs_text", "vacancy_vs_text", "reliability_note"],
        "order_by_cols": ['["average_rent", false]'],
        "row_limit": 10,
        "server_pagination": False,
        "include_search": False,
        "show_cell_bars": False,
        "table_timestamp_format": "smart_date",
    },
}

PANEL_LABELS = {
    "takeaway": "What it means",
    "rent_vs_text": "Rent vs Windsor",
    "vacancy_vs_text": "Vacancy vs Windsor",
    "reliability_note": "Note",
}

ZONE_SNAPSHOT_LABELS = {
    "zone_label": "Zone",
    "period_label": "Survey",
    "average_rent": "Average monthly rent",
    "rent_reliability": "Rent reliability",
    "vacancy_rate_pct": "Vacancy rate (%)",
    "vacancy_reliability": "Vacancy reliability",
    "rental_universe": "Rental units",
    "share_of_zone_stock_pct": "Share of Windsor's units (%)",
    "turnover_rate_pct": "Turnover rate (%)",
}

# Compact guide shown under the KPI cards.
HOW_TO_MARKDOWN = """**How to use this dashboard** &nbsp;
**1 · Pick a zone:** click a row in *Zone Snapshot*, a zone bar or a zone trend line, or choose one
in the **Zone** filter. &nbsp; **2 · Read it:** the zone charts and the panel on the right switch
to that zone; **Bedroom Type** switches the panel to one unit size. &nbsp; **3 · Clear it:** click
the zone again, the ✕ beside it under **Cross-filters**, or **↺ Reset** in the panel. &nbsp;
**Note:** the four cards above are fixed Windsor benchmarks and do not change with filters or clicks.
"""

COMMON_LABELS = {
    "zone_label": "Zone",
    "bedroom_type_label": "Bedroom Type",
    "dwelling_type_label": "Dwelling Type",
    "period_label": "Survey",
}

DATA_NOTES_MARKDOWN = """**About the data**

- **Source:** CMHC Rental Market Survey, Windsor CMA, every October from 2020 to 2025.
  CMHC's zone tables cannot be downloaded for earlier years; for **ten years (2015-2025)**
  of Windsor-wide rent and vacancy, see Story 4's **Ten Years** tab.
- **Coverage:** purpose-built rental buildings with 3 or more units. Rented condos,
  basements and houses are not included.
- **"Combined"** means apartments and row houses together. Most charts use it because
  CMHC suppresses most row-house-only figures in Windsor.
- **Rent** is the average monthly rent of all surveyed units, occupied and vacant,
  not the asking rent for a vacant unit.
- **Reliability letters** are CMHC's grades: a excellent, b very good, c good, d fair
  (use with caution).
- **Blank bars** are values CMHC suppressed for reliability or confidentiality, not zeros.
"""

# Top-to-bottom grid entries: a HEADER-* id with its text, or a ROW-* id
# with (chart key, width) pairs -- widths sum to 12 per row, same grid
# convention as Story 1's dashboard.
#
# Every section has a header, matching Dashboards 1, 2 and 4 (this was the
# only dashboard without them). KPI tiles follow Dashboard 1's rental row
# order (Rent, Vacancy, Stock, Turnover) so the same 4 numbers read in the
# same order wherever they appear. The rent and vacancy trend charts are
# full width rather than side by side: each draws 4 bedroom types x 6
# periods = 24 bars, which crowds badly in a half-width cell once the
# dashboard is embedded in the React story page's narrower iframe.
LAYOUT = [
    ("HEADER-kpi", "Windsor CMA Benchmarks (Oct-25): Fixed Totals, All Zones, Apartments + Row Houses"),
    ("ROW-howto", [("md:howto", 12)]),
    ("ROW-kpi", [("kpi-rent", 3), ("kpi-vacancy", 3), ("kpi-stock", 3), ("kpi-turnover", 3)]),
    ("HEADER-zone", "Explore by Zone: Click a Zone to Filter"),
    ("ROW-zone-table", [("zone-table", 7), ("zone-explain", 5)]),
    ("ROW-zone-bars", [("zone-stock", 6), ("zone-vacancy", 6)]),
    ("ROW-zone", [("rent-zone", 12)]),
    ("ROW-zone-trend", [("zone-vacancy-trend", 12)]),
    ("HEADER-trends", "Rent and Vacancy Trends (Oct-20 to Oct-25)"),
    ("ROW-rent-trend", [("rent-trend", 12)]),
    ("ROW-vacancy-trend", [("vacancy-trend", 12)]),
    ("HEADER-turnover", "Turnover and Dwelling Type"),
    ("ROW-turnover", [("turnover", 12)]),
    ("ROW-dwelling", [("vacancy-dwelling", 12)]),
    ("HEADER-notes", "How to Read This Dashboard"),
    ("ROW-notes", [("md:guide", 6), ("md:notes", 6)]),
]

MARKDOWN = {
    "md:notes": (DATA_NOTES_MARKDOWN, 60),
    "md:guide": (CHART_GUIDE_MARKDOWN, 60),
    "md:howto": (HOW_TO_MARKDOWN, 14),
}

# Charts whose datasets have a zone_label column. Cross-filters on a zone
# are applied only to these; the KPI tiles and the bedroom-type and
# dwelling-type charts have no zone column, so a zone cross-filter would
# make their queries fail.
# On the shared Superset the explanation panel is a plain table over the
# all-unit-sizes view (see SIMPLE_PANEL below), which has no unit-size column,
# so it stays out of the Bedroom Type filter and its cross-filters.
PANEL_BY_UNIT_SIZE = [] if SHARED else ["zone-explain"]

ZONE_CHART_KEYS = ["zone-table", "zone-explain", "zone-stock", "zone-vacancy", "rent-zone", "zone-vacancy-trend"]
# Cross-filter groups. A chart's click filters on the column it groups by
# (zone for the zone charts; unit size for the rent/vacancy/turnover by
# bedroom charts), so each group only reaches charts whose dataset has that
# column. Every ECharts/Table chart on the dashboard must appear in exactly
# one group or in NO_CROSS_FILTER_KEYS: Superset's frontend computes a
# configuration for every clickable chart, and any difference from the
# stored one makes it try to save (see build_cross_filter_config).
CROSS_FILTER_GROUPS = {
    "zone": {
        "emitters": ["zone-table", "zone-stock", "zone-vacancy"],  # the heatmap cannot emit
        "receivers": ZONE_CHART_KEYS,
    },
    "bedroom": {
        "emitters": ["rent-zone", "rent-trend", "vacancy-trend", "turnover"],
        "receivers": ["rent-zone", "rent-trend", "vacancy-trend", "turnover", *PANEL_BY_UNIT_SIZE],
    },
}
# Clickable charts whose clicks should filter nothing: the dwelling-type
# chart's column only exists in one other dataset, where it is fixed to
# "Combined", so a dwelling cross-filter could only empty that chart.
NO_CROSS_FILTER_KEYS = ["vacancy-dwelling"]

# Chart heights in Superset grid units (8px each). KPI tiles stay
# compact; the zone table only has 7 rows, so 55 would leave a large
# blank area under it.
KPI_HEIGHT = 32  # room for the trendline under the rent and vacancy tiles
TABLE_HEIGHT = 40
CHART_HEIGHT = 55


def chart_height(key: str) -> int:
    if key.startswith("kpi"):
        return KPI_HEIGHT
    if key in ("zone-table", "zone-explain"):
        # Tall enough for the longest panel content (a zone with a
        # reliability note, measured at 582px) so the panel never scrolls
        # inside its card.
        return 84
    if CHARTS[key]["viz_type"] == "table":
        return TABLE_HEIGHT
    return CHART_HEIGHT


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


# One screen per tab (etl/dashboard_tabs.py). The trend and turnover
# headers are dropped: the tab titles say the same thing.
TABS = [
    ("TAB-overview", "Overview", ["HEADER-kpi", "ROW-howto", "ROW-kpi", "HEADER-notes", "ROW-notes"]),
    ("TAB-zone", "Explore by Zone", ["HEADER-zone", "ROW-zone-table"]),
    ("TAB-zones", "Zones Compared", ["ROW-zone-bars", "ROW-zone-trend"]),
    ("TAB-rent", "Rent", ["ROW-rent-trend", "ROW-zone"]),
    ("TAB-vacancy", "Vacancy", ["ROW-vacancy-trend", "ROW-dwelling"]),
    ("TAB-turnover", "Turnover", ["ROW-turnover"]),
]


def build_position_json(chart_ids: dict) -> dict:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [node_id for node_id, _ in LAYOUT],
            "parents": ["ROOT_ID"],
        },
    }

    for row_id, charts_in_row in LAYOUT:
        if row_id.startswith("HEADER-"):
            position[row_id] = {
                "type": "HEADER",
                "id": row_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {
                    "text": charts_in_row,
                    "headerSize": "MEDIUM_HEADER",
                    "background": "BACKGROUND_TRANSPARENT",
                },
            }
            continue

        chart_node_ids = [
            f"MARKDOWN-{key[3:]}" if key.startswith("md:") else f"CHART-{key}" for key, _ in charts_in_row
        ]
        position[row_id] = {
            "type": "ROW",
            "id": row_id,
            "children": chart_node_ids,
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for (key, width), node_id in zip(charts_in_row, chart_node_ids):
            if key.startswith("md:"):
                code, height = MARKDOWN[key]
                position[node_id] = {
                    "type": "MARKDOWN",
                    "id": node_id,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", row_id],
                    "meta": {"width": width, "height": height, "code": code, "uuid": str(uuid.uuid4())},
                }
                continue
            position[node_id] = {
                "type": "CHART",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "chartId": chart_ids[key],
                    "width": width,
                    # 25, not 50, for KPI tiles -- 50 left a large empty
                    # gap above the number inside every big_number_total
                    # card, confirmed visually, not a guess.
                    "height": chart_height(key),
                    "uuid": str(uuid.uuid4()),
                },
            }

    return add_tabs(position, TABS)


DWELLING_DEFAULT = ["Apartment", "Combined"]


def filter_scope(chart_ids: dict, keys: list) -> tuple[dict, list]:
    """Scope that reaches only the given charts. Superset applies a native
    filter to every chart its scope covers (chartsInScope is derived from
    it), so an empty "excluded" list made the Bedroom Type and Dwelling
    Scope filters reach the KPI cards and empty them ("No data")."""
    in_scope = sorted(chart_ids[key] for key in keys)
    excluded = sorted(cid for cid in chart_ids.values() if cid not in in_scope)
    return {"rootPath": ["ROOT_ID"], "excluded": excluded}, in_scope


def build_native_filters(chart_ids: dict) -> list:
    non_kpi_bedroom_charts = [
        chart_ids["rent-zone"],
        chart_ids["rent-trend"],
        chart_ids["vacancy-trend"],
        chart_ids["turnover"],
    ]
    zone_scope, zone_in = filter_scope(chart_ids, ZONE_CHART_KEYS)
    bedroom_scope, bedroom_in = filter_scope(
        chart_ids, ["rent-zone", "rent-trend", "vacancy-trend", "turnover", *PANEL_BY_UNIT_SIZE]
    )
    dwelling_scope, dwelling_in = filter_scope(chart_ids, ["vacancy-dwelling"])
    return [
        {
            "id": "NATIVE_FILTER-story2-zone",
            "name": "Zone",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_RENT_ZONE, "column": {"name": "zone_label"}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": zone_scope,
            "type": "NATIVE_FILTER",
            "description": "Show only the selected CMHC zones. Leave empty for all 7 zones.",
            "chartsInScope": zone_in,
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
            "id": "NATIVE_FILTER-story2-bedroom",
            # Title Case per docs/filter_standards.md rule 1 (was "Bedroom
            # type", the follow-up that doc flagged for this dashboard).
            "name": "Bedroom Type",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_RENT_YOY, "column": {"name": "bedroom_type_label"}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            # Pre-filter the list of values: every chart in this filter's
            # scope already excludes the "Total" row, so offering it only
            # ever produced empty charts.
            "adhoc_filters": [EXCLUDE_TOTAL_BEDROOM],
            "time_range": "No filter",
            "cascadeParentIds": [],
            "scope": bedroom_scope,
            "type": "NATIVE_FILTER",
            "description": "Show only the selected unit sizes. Leave empty for all.",
            "chartsInScope": bedroom_in,
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
            "id": "NATIVE_FILTER-story2-dwelling",
            "name": "Dwelling Scope",
            "filterType": "filter_select",
            "targets": [{"datasetId": DATASET_VACANCY, "column": {"name": "dwelling_type_label"}}],
            # Starts on Apartment + Combined: CMHC suppresses most Windsor
            # row-house-only figures, so including Row by default added a
            # mostly empty series. Users can still add it.
            "defaultDataMask": {
                "extraFormData": {
                    "filters": [{"col": "dwelling_type_label", "op": "IN", "val": DWELLING_DEFAULT}]
                },
                "filterState": {"value": DWELLING_DEFAULT},
                "ownState": {},
            },
            "cascadeParentIds": [],
            "scope": dwelling_scope,
            "type": "NATIVE_FILTER",
            # Every other chart on this dashboard already hardcodes
            # dwelling_type_label == 'Combined' in its own adhoc_filters
            # (Apartment data is sparse or absent for rent/turnover at
            # this scope -- see sql/story2_views.sql). AND-combining a
            # user-selected 'Apartment' value onto those would be the
            # same zero-rows conflict etl/fix_story1_tenure_filter_scope.py
            # found and fixed for Story 1's KPI tiles, so this filter is
            # scoped ONLY to the one new chart built specifically to vary
            # by dwelling type (both scopes have full real 6-period
            # coverage there -- confirmed directly, not assumed).
            "description": "Apartments, row houses, or both combined. Row-house figures are often suppressed by CMHC.",
            "chartsInScope": dwelling_in,
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


# Keys Superset's dataset PUT accepts for each column.
DATASET_COLUMN_KEYS = (
    "id",
    "column_name",
    "verbose_name",
    "description",
    "expression",
    "filterable",
    "groupby",
    "is_active",
    "is_dttm",
    "python_date_format",
    "type",
    "advanced_data_type",
    "extra",
)


def ensure_panel_dataset(session, headers) -> int:
    """Create or update the panel's virtual dataset; returns its id."""
    existing = find_existing(session, headers, "dataset", "table_name", PANEL_DATASET_NAME)
    if existing:
        resp = session.put(f"{SUPERSET_URL}/api/v1/dataset/{existing}", headers=headers, json={"sql": PANEL_DATASET_SQL})
        resp.raise_for_status()
        dataset_id = existing
    else:
        ref = session.get(f"{SUPERSET_URL}/api/v1/dataset/{DATASET_ZONE_EXPLANATION}", headers=headers)
        ref.raise_for_status()
        database_id = ref.json()["result"]["database"]["id"]
        resp = session.post(
            f"{SUPERSET_URL}/api/v1/dataset/",
            headers=headers,
            json={"database": database_id, "schema": "warehouse", "table_name": PANEL_DATASET_NAME, "sql": PANEL_DATASET_SQL},
        )
        resp.raise_for_status()
        dataset_id = resp.json()["id"]
    session.put(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}/refresh", headers=headers).raise_for_status()
    return dataset_id


def set_column_labels(session, headers, dataset_id: int, labels: dict) -> None:
    """Set readable labels (verbose_name) on a dataset's columns, keeping
    every other column property as it is."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers)
    resp.raise_for_status()
    columns = []
    for col in resp.json()["result"]["columns"]:
        kept = {k: col[k] for k in DATASET_COLUMN_KEYS if k in col}
        if col["column_name"] in labels:
            kept["verbose_name"] = labels[col["column_name"]]
        columns.append(kept)
    resp = session.put(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers, json={"columns": columns})
    resp.raise_for_status()


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


def build_cross_filter_config(chart_ids: dict) -> tuple[dict, dict]:
    """Superset 3.1 dashboard metadata for cross-filtering: each zone chart
    may emit, and its cross-filter reaches only the other zone charts.

    Written in exactly the shape Superset's frontend computes on load
    (chartsInScope sorted by id). If the stored value differs, the frontend
    tries to save its own version with PUT /api/v1/dashboard/<id>; for an
    anonymous (Public role) viewer that PUT returns 401 and Superset sends
    the visitor to the login page -- which would break the public embed on
    the React Story 2 page. Verified by loading the dashboard anonymously
    and checking that no PUT is made."""
    all_ids = list(chart_ids.values())
    zone_ids = sorted(chart_ids[key] for key in ZONE_CHART_KEYS)
    other_ids = [cid for key, cid in chart_ids.items() if key not in ZONE_CHART_KEYS]
    chart_configuration = {}
    for group in CROSS_FILTER_GROUPS.values():
        receiver_ids = sorted(chart_ids[key] for key in group["receivers"])
        for key in group["emitters"]:
            cid = chart_ids[key]
            excluded = [c for c in all_ids if c == cid or c not in receiver_ids]
            chart_configuration[str(cid)] = {
                "id": cid,
                "crossFilters": {
                    "scope": {"rootPath": ["ROOT_ID"], "excluded": excluded},
                    "chartsInScope": [c for c in receiver_ids if c != cid],
                },
            }
    for key in NO_CROSS_FILTER_KEYS:
        cid = chart_ids[key]
        chart_configuration[str(cid)] = {
            "id": cid,
            "crossFilters": {"scope": {"rootPath": ["ROOT_ID"], "excluded": all_ids}, "chartsInScope": []},
        }
    global_chart_configuration = {
        "scope": {"rootPath": ["ROOT_ID"], "excluded": other_ids},
        "chartsInScope": zone_ids,
    }
    return chart_configuration, global_chart_configuration


def ensure_dashboard(session, headers, position_json: dict, native_filters: list, chart_ids: dict) -> int:
    chart_configuration, global_chart_configuration = build_cross_filter_config(chart_ids)
    existing = find_existing(session, headers, "dashboard", "dashboard_title", DASHBOARD_TITLE)

    # Merge into the stored metadata rather than replacing it: Superset's
    # frontend adds keys of its own (cross_filters_enabled,
    # color_scheme_domain, label colours, ...), and dropping them makes it
    # try to re-save on the next load -- the same anonymous-401 problem as
    # above.
    metadata = {}
    if existing:
        resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{existing}", headers=headers)
        resp.raise_for_status()
        metadata = json.loads(resp.json()["result"]["json_metadata"] or "{}")
    metadata.update(
        {
            "native_filter_configuration": native_filters,
            "color_scheme": COLOR_SCHEME,
            "chart_configuration": chart_configuration,
            "global_chart_configuration": global_chart_configuration,
            "cross_filters_enabled": True,
        }
    )
    metadata.setdefault("color_scheme_domain", COLOR_DOMAIN)
    # One fixed palette colour per zone, so each zone has the same colour
    # in the zone bars and the zone trend lines, and no two zones share one
    # (Superset otherwise assigns colours by label and repeated a green).
    metadata["label_colors"] = ZONE_COLORS
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


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    # Pick up columns added to v_story2_zone_explanation (the panel reads them).
    session.put(f"{SUPERSET_URL}/api/v1/dataset/{DATASET_ZONE_EXPLANATION}/refresh", headers=headers).raise_for_status()
    set_column_labels(session, headers, DATASET_ZONE_SNAPSHOT, ZONE_SNAPSHOT_LABELS)
    # Cross-filter tags and tooltips show these labels instead of raw
    # column names such as "zone_label".
    for dataset_id in (DATASET_RENT_ZONE, DATASET_ZONE_VACANCY, DATASET_ZONE_EXPLANATION,
                       DATASET_RENT_YOY, DATASET_VACANCY, DATASET_TURNOVER):
        set_column_labels(session, headers, dataset_id, COMMON_LABELS)
    print("Dataset column labels set.")

    if SHARED:
        CHARTS["zone-explain"] = SIMPLE_PANEL
        set_column_labels(session, headers, DATASET_ZONE_EXPLANATION, {**COMMON_LABELS, **PANEL_LABELS})
        print("Explanation panel: simple table (shared Superset).")
    else:
        panel_dataset_id = ensure_panel_dataset(session, headers)
        CHARTS["zone-explain"]["dataset_id"] = panel_dataset_id
        set_column_labels(session, headers, panel_dataset_id, COMMON_LABELS)
        print(f"Panel dataset ready: {PANEL_DATASET_NAME} (id={panel_dataset_id})")

    chart_ids = {}
    for key, spec in CHARTS.items():
        chart_id = ensure_chart(session, headers, key, spec)
        chart_ids[key] = chart_id
        print(f"Chart ready: {spec['slice_name']} (id={chart_id})")

    position_json = build_position_json(chart_ids)
    native_filters = build_native_filters(chart_ids)
    dashboard_id = ensure_dashboard(session, headers, position_json, native_filters, chart_ids)
    print(f"Dashboard ready: id={dashboard_id}")

    for key, chart_id in chart_ids.items():
        link_chart_to_dashboard(session, headers, chart_id, dashboard_id)
    print(f"Linked all {len(chart_ids)} charts to dashboard {dashboard_id}.")

    print(f"Finished: {finish_dashboard(session, headers, dashboard_id)}")
    print(f"View it at: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
