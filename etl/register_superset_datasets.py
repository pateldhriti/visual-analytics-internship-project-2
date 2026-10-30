"""
Register every SQL view across all 4 stories (sql/story1_views.sql
through sql/story4_views.sql) as a Superset dataset, each with saved
metrics -- so chart-builders pick a named metric from a dropdown instead
of retyping ad-hoc SQL per chart, which is how
etl/setup_superset_dashboard.py's single chart currently works.

Reuses the Database connection and auth helpers from
etl/setup_superset_dashboard.py rather than duplicating them -- same
Postgres instance, just a different schema (warehouse, not public) and
multiple datasets instead of one.

The "one shared colour palette" half of this task is NOT done here: a
Superset custom color scheme is registered via EXTRA_CATEGORICAL_COLOR_
SCHEMES in docker/superset_config.py (a container-level setting, not
reachable through the REST API), requiring a Superset container restart
to take effect. See that file for the actual palette definition --
market -> hex, using the dataviz skill's validated CVD-safe categorical
slots (references/palette.md), same source as the existing Owner/Renter
chart's colors.

Requires Superset running and a .env file with SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD/POSTGRES_* (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\register_superset_datasets.py
"""

from setup_superset_dashboard import SUPERSET_URL, ensure_database, find_existing, get_session

SCHEMA = "warehouse"

# view name -> list of saved metrics (metric_name, expression, verbose_name)
# Only metrics over real, non-NULL columns are defined -- a saved metric
# over a column that's NULL for every row would silently show as 0 or
# blank in a chart, indistinguishable from "the real value happens to be
# zero" -- worse than no metric at all. This rule is applied per view
# below, e.g. v_story4_affordability_gap's renter_income_growth_pct /
# affordability_gap_index (see docs/affordability_gap_index.md) and
# v_story3_supply_per_1000_households' households_total /
# supply_per_1000_households (see sql/story3_views.sql) -- both all-NULL
# by design, so neither gets a metric.
VIEWS = {
    "v_story1_burden_by_tenure": [
        {
            "metric_name": "avg_burden_rate",
            "expression": "AVG(burden_rate_pct)",
            "verbose_name": "Average Shelter-Cost Burden Rate (%)",
            "metric_type": "avg",
            "description": "Share of households spending 30%+ of income on shelter, averaged across whatever rows are in scope (e.g. filtered to one tenure).",
        },
    ],
    "v_story1_burden_by_income_band": [
        {
            "metric_name": "avg_burden_rate",
            "expression": "AVG(burden_rate_pct)",
            "verbose_name": "Average Shelter-Cost Burden Rate (%)",
            "metric_type": "avg",
            "description": "Share of households spending 30%+ of income on shelter, averaged across whatever rows are in scope (e.g. filtered to one income band).",
        },
    ],
    "v_story1_burden_by_household_type": [
        {
            "metric_name": "avg_burden_rate",
            "expression": "AVG(burden_rate_pct)",
            "verbose_name": "Average Shelter-Cost Burden Rate (%)",
            "metric_type": "avg",
            "description": "Share of households spending 30%+ of income on shelter, averaged across whatever rows are in scope (e.g. filtered to one household type).",
        },
    ],
    "v_story1_burden_severity": [
        {
            "metric_name": "avg_severe_pct",
            "expression": "AVG(severe_pct_of_burdened)",
            "verbose_name": "Share of Burdened Households in the 30-99% Band (%)",
            "metric_type": "avg",
            "description": "Of households already spending 30%+ on shelter, the share in the 30%-to-under-100% band StatCan's table directly publishes. No metric defined on unaccounted_households/unaccounted_pct_of_burdened -- see this view's own comment in sql/story1_views.sql for why that gap is reported, not assumed.",
        },
    ],
    "v_story1_burden_severity_breakdown": [
        {
            "metric_name": "avg_pct_of_burdened",
            "expression": "AVG(pct_of_burdened)",
            "verbose_name": "Average Share of Burdened Households (%)",
            "metric_type": "avg",
            "description": "Share of each tenure's burdened households in a given severity category (Severe 30-99%, or Unaccounted), averaged across whatever rows are in scope.",
        },
    ],
    "v_story2_rent_yoy_change": [
        {
            "metric_name": "avg_rent",
            "expression": "AVG(average_rent)",
            "verbose_name": "Average Rent ($)",
            "metric_type": "avg",
            "description": "Average rent, Windsor CMA Combined scope, averaged across whatever rows are in scope.",
        },
        {
            "metric_name": "avg_yoy_change_pct",
            "expression": "AVG(yoy_change_pct)",
            "verbose_name": "Average YoY Rent Change (%)",
            "metric_type": "avg",
            "description": "Year-over-year rent change. NULL for each bedroom type's first real period (Oct-20, no prior year in this dataset) -- AVG() excludes those NULLs rather than treating them as 0.",
        },
    ],
    "v_story2_rent_growth": [
        {
            "metric_name": "avg_growth_pct",
            "expression": "AVG(growth_pct)",
            "verbose_name": "Average Rent Growth, Real Span (%)",
            "metric_type": "avg",
            "description": "Total rent growth over this project's real data span (5 years, Oct-20 to Oct-25 -- see each row's own data_note). NULL for 3 Bedroom+ (a real gap in the Oct-25 data), excluded by AVG() rather than treated as 0.",
        },
    ],
    "v_story2_vacancy_trend": [
        {
            "metric_name": "avg_vacancy_rate",
            "expression": "AVG(vacancy_rate_pct)",
            "verbose_name": "Average Vacancy Rate (%)",
            "metric_type": "avg",
            "description": "Vacancy rate, Windsor CMA, averaged across whatever rows are in scope (e.g. filtered to one bedroom/dwelling type).",
        },
    ],
    "v_story2_turnover_by_bedroom": [
        {
            "metric_name": "avg_turnover_rate",
            "expression": "AVG(turnover_rate_pct)",
            "verbose_name": "Average Turnover Rate (%)",
            "metric_type": "avg",
            "description": "Turnover rate, Windsor CMA, averaged across whatever rows are in scope (e.g. filtered to one bedroom/dwelling type).",
        },
    ],
    "v_story2_rent_by_zone_bedroom": [
        {
            "metric_name": "avg_rent",
            "expression": "AVG(average_rent)",
            "verbose_name": "Average Rent ($)",
            "metric_type": "avg",
            "description": "Average rent, Oct-25, by Windsor's 7 real zones and bedroom type -- excludes the Windsor CMA and Windsor City rollup rows. Some zone/bedroom-type cells are NULL (suppressed by CMHC for sample size), excluded by AVG() rather than treated as 0.",
        },
    ],
    "v_story2_zone_snapshot": [
        {
            "metric_name": "avg_vacancy_rate",
            "expression": "AVG(vacancy_rate_pct)",
            "verbose_name": "Average Vacancy Rate (%)",
            "metric_type": "avg",
            "description": "Oct-25 vacancy rate by Windsor zone, Combined dwelling types, Total bedroom type.",
        },
        {
            "metric_name": "total_rental_universe",
            "expression": "SUM(rental_universe)",
            "verbose_name": "Rental Stock (Units)",
            "metric_type": "sum",
            "description": "Oct-25 rental universe (surveyed rental units) by zone. Summing all 7 zones gives the Windsor CMA total (19,883) -- the rollup rows are excluded from this view, so nothing is double-counted.",
        },
        {
            "metric_name": "avg_rent",
            "expression": "AVG(average_rent)",
            "verbose_name": "Average Rent ($)",
            "metric_type": "avg",
            "description": "Oct-25 average rent by zone, all bedroom types blended (CMHC's Total row).",
        },
    ],
    "v_story2_vacancy_by_zone_trend": [
        {
            "metric_name": "avg_vacancy_rate",
            "expression": "AVG(vacancy_rate_pct)",
            "verbose_name": "Average Vacancy Rate (%)",
            "metric_type": "avg",
            "description": "Vacancy rate by Windsor zone and period, Oct-20 to Oct-25. Zone 7 starts at Oct-23 and Zone 5 has 2 suppressed (NULL) periods -- AVG() excludes those rather than treating them as 0.",
        },
    ],
    "v_story3_starts_completions_by_dwelling_type": [
        {
            "metric_name": "total_units",
            "expression": "SUM(units)",
            "verbose_name": "Total Units",
            "metric_type": "sum",
            "description": "Housing units (starts/completions/under construction), Ontario/Canada -- no Windsor-specific figure exists in this source. Summed across whatever rows are in scope.",
        },
    ],
    "v_story3_supply_per_1000_households": [
        {
            "metric_name": "total_starts",
            "expression": "SUM(starts_total)",
            "verbose_name": "Total Starts",
            "metric_type": "sum",
            "description": "Housing starts, Ontario/Canada. No metric defined on households_total or supply_per_1000_households -- both are NULL for every row (see this view's own data_note in sql/story3_views.sql): no households figure exists at this geography.",
        },
    ],
    "v_story3_windsor_supply_annual": [
        {
            "metric_name": "total_units",
            "expression": "SUM(units)",
            "verbose_name": "Total Units",
            "metric_type": "sum",
            "description": "Windsor CMA starts/completions (year's monthly sum) or units under construction (year-end stock). Only sum within one activity -- adding Starts to Under Construction mixes a flow with a stock.",
        },
    ],
    "v_story3_windsor_supply_per_1000_households": [
        {
            "metric_name": "avg_starts_per_1000",
            "expression": "AVG(starts_per_1000_households)",
            "verbose_name": "Starts per 1,000 Households",
            "metric_type": "avg",
            "description": "Windsor CMA housing starts per 1,000 private households, full years only, against the 2021 Census household count.",
        },
        {
            "metric_name": "avg_completions_per_1000",
            "expression": "AVG(completions_per_1000_households)",
            "verbose_name": "Completions per 1,000 Households",
            "metric_type": "avg",
            "description": "Windsor CMA housing completions per 1,000 private households, full years only, against the 2021 Census household count.",
        },
    ],
    "v_story4_vacancy_comparison": [
        {
            "metric_name": "avg_vacancy_rate",
            "expression": "AVG(vacancy_rate_pct)",
            "verbose_name": "Average Vacancy Rate (%)",
            "metric_type": "avg",
            "description": "Apartment vacancy rate, Total bedroom type, averaged across whatever rows are in scope (e.g. filtered to one period).",
        },
    ],
    "v_story4_rent_comparison": [
        {
            "metric_name": "avg_rent_2br",
            "expression": "AVG(average_rent_2br)",
            "verbose_name": "Average 2BR Rent ($)",
            "metric_type": "avg",
            "description": "Average 2-bedroom apartment rent, averaged across whatever rows are in scope.",
        },
    ],
    "v_story4_affordability_gap": [
        {
            "metric_name": "avg_rent_growth",
            "expression": "AVG(rent_growth_pct)",
            "verbose_name": "Average Rent Growth (%)",
            "metric_type": "avg",
            "description": "Oct-24-to-25 rent growth (CMHC's matched-sample figure), averaged across whatever rows are in scope. The income-growth and index columns have no saved metric: both are NULL for every row -- see docs/affordability_gap_index.md.",
        },
    ],
    "v_dashboard1_rental_yoy": [
        {
            "metric_name": "avg_change_value",
            "expression": "AVG(change_value)",
            "verbose_name": "Average Change",
            "metric_type": "avg",
            "description": "Oct-24-to-Oct-25 change, averaged across whatever rows are in scope (mixed units across metrics -- see change_unit).",
        },
    ],
    "v_dashboard1_cma_benchmark": [
        {
            "metric_name": "avg_windsor_minus_median",
            "expression": "AVG(windsor_minus_median)",
            "verbose_name": "Average Windsor vs. Comparator-Median Gap",
            "metric_type": "avg",
            "description": "Windsor's value minus the 4-comparator median, averaged across whatever rows are in scope.",
        },
    ],
}


def ensure_dataset(session, headers, database_id: int, table_name: str) -> int:
    existing = find_existing(session, headers, "dataset", "table_name", table_name)
    if existing:
        return existing

    resp = session.post(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        json={"database": database_id, "table_name": table_name, "schema": SCHEMA},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def set_metrics(session, headers, dataset_id: int, metrics: list[dict]) -> None:
    """Create-or-update each metric by name. Superset's dataset PUT treats
    a metric object without an "id" as a brand-new metric -- re-running
    this with the same metric_name but no id fails with 422 "One or more
    metrics already exist" instead of updating it in place. Fetching the
    dataset's current metrics first and attaching each existing metric's
    real id (by matching metric_name) is what makes this safe to re-run."""
    existing_resp = session.get(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers)
    existing_resp.raise_for_status()
    existing_by_name = {m["metric_name"]: m["id"] for m in existing_resp.json()["result"]["metrics"]}

    merged_metrics = []
    for metric in metrics:
        merged = dict(metric)
        if metric["metric_name"] in existing_by_name:
            merged["id"] = existing_by_name[metric["metric_name"]]
        merged_metrics.append(merged)

    resp = session.put(
        f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}",
        headers=headers,
        json={"metrics": merged_metrics},
    )
    resp.raise_for_status()


if __name__ == "__main__":
    session, headers = get_session()
    print("Logged in to Superset.")

    database_id = ensure_database(session, headers)
    print(f"Database connection ready: id={database_id}")

    for view_name, metrics in VIEWS.items():
        dataset_id = ensure_dataset(session, headers, database_id, view_name)
        set_metrics(session, headers, dataset_id, metrics)
        metric_names = ", ".join(m["metric_name"] for m in metrics)
        print(f"Dataset ready: {view_name} (id={dataset_id}), metrics: {metric_names}")
