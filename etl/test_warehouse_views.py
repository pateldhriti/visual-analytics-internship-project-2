r"""Data tests for the warehouse: the SQL views and the fact-table loads.

These run against the loaded database (the one in .env), so they check the
real numbers, not a fixture: every view in sql/*.sql runs, the views the
dashboards rely on have no duplicate rows, shares add to 100%, parts add up
to their totals, a figure shown in several stories has the same value in
each, Story 1 matches Statistics Canada's published rates, values are in a
plausible range, and each fact table holds every row of its staging file.

Where no database is reachable (e.g. GitHub Actions, which has no warehouse)
every test is skipped, not failed. Run them after a refresh:

    .venv\Scripts\python.exe -m pytest etl\test_warehouse_views.py -v
"""

import re
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
STAGING = PROJECT_ROOT / "data" / "staging"


@pytest.fixture(scope="module")
def db():
    """A connection to the warehouse, or skip every test when there is none."""
    try:
        from sqlalchemy import text

        from apply_sql_views import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM warehouse.dim_period LIMIT 1"))
    except Exception as exc:  # no .env, no server, or not loaded yet
        pytest.skip(f"no loaded warehouse to test against ({type(exc).__name__})")

    def query(sql: str, **params):
        with engine.connect() as conn:
            return [dict(r) for r in conn.execute(text(sql), params).mappings()]

    return query


def one(db, sql: str):
    """The single value a query returns."""
    rows = db(sql)
    assert len(rows) == 1, f"expected one row from: {sql}"
    return next(iter(rows[0].values()))


# --- every view ----------------------------------------------------------------

VIEW_NAMES = sorted({m for f in SQL_DIR.glob("*views*.sql")
                     for m in re.findall(r"CREATE (?:OR REPLACE )?VIEW warehouse\.(\w+)", f.read_text(encoding="utf-8"))})


def test_the_view_files_define_the_views():
    assert len(VIEW_NAMES) >= 50


@pytest.mark.parametrize("view", VIEW_NAMES)
def test_every_view_exists_and_runs(db, view):
    db(f"SELECT * FROM warehouse.{view} LIMIT 1")


# --- no duplicate rows ---------------------------------------------------------

UNIQUE_KEYS = {
    "v_story1_burden_by_tenure": ["tenure"],
    "v_story1_burden_by_income_tenure": ["income_band", "tenure"],
    "v_story1_burden_distribution": ["tenure", "category"],
    "v_story2_zone_snapshot": ["zone_label"],
    "v_story2_turnover_change": ["unit_size"],
    "v_story2_stock_by_unit_size": ["unit_size"],
    "v_story2_rent_vacant_occupied": ["unit_size"],
    "v_story2_bedroom_oct": ["unit_size", "period_label"],
    "v_story2_market_history": ["period_year"],
    "v_story3_pipeline": ["stage", "dwelling_type"],
    "v_story3_intended_market": ["period_label", "activity", "intended_market"],
    "v_story3_windsor_supply_annual": ["year_label", "activity", "dwelling_type"],
    "v_story4_cma_canada": ["cma_code"],
    "v_story4_city_history": ["city", "period_year"],
    "v_story4_rental_supply_2021": ["cma_code"],
    "v_story5_city_profile": ["city"],
    "v_dashboard1_rental_yoy": ["metric", "dwelling_type_label"],
}


@pytest.mark.parametrize("view, key", UNIQUE_KEYS.items())
def test_no_duplicate_rows(db, view, key):
    cols = ", ".join(key)
    dupes = db(f"SELECT {cols}, count(*) AS n FROM warehouse.{view} GROUP BY {cols} HAVING count(*) > 1")
    assert dupes == [], f"{view} repeats {dupes[:3]}"


# --- shares and parts ------------------------------------------------------------

@pytest.mark.parametrize("view, share, group", [
    ("v_story2_stock_by_unit_size", "pct_of_units", None),
    ("v_story3_pipeline", "pct_of_stage", "stage"),
    ("v_story3_intended_market", "share_pct", "period_label, activity"),
    ("v_story1_burden_distribution", "pct_of_households", "tenure"),
])
def test_shares_add_to_100(db, view, share, group):
    by = f" GROUP BY {group}" if group else ""
    for row in db(f"SELECT SUM({share}) AS total FROM warehouse.{view}{by}"):
        assert abs(float(row["total"]) - 100) <= 0.3  # rounding of each share


def test_zones_add_up_to_windsor(db):
    zones = one(db, "SELECT SUM(rental_universe) FROM warehouse.v_story2_zone_snapshot")
    sizes = one(db, "SELECT SUM(units) FROM warehouse.v_story2_stock_by_unit_size")
    assert zones == sizes  # both apartments, October 2025


def test_this_year_so_far_agrees_across_story3(db):
    latest = db("SELECT ytd_starts, ytd_completions, ytd_label FROM warehouse.v_story3_latest_month")[0]
    pipe = {r["stage"]: r["units"] for r in db(
        "SELECT stage, SUM(units) AS units FROM warehouse.v_story3_pipeline GROUP BY stage")}
    assert pipe["Starts so far"] == latest["ytd_starts"]
    assert pipe["Completions so far"] == latest["ytd_completions"]
    market = {r["activity"]: (r["period_label"], r["total_units"]) for r in db(
        "SELECT DISTINCT activity, period_label, total_units FROM warehouse.v_story3_intended_market WHERE is_ytd")}
    for activity, ytd in (("Starts", latest["ytd_starts"]), ("Completions", latest["ytd_completions"])):
        period, total = market[activity]
        if period == latest["ytd_label"]:  # the hand-downloaded exports can lag a month (etl/README.md)
            assert total == ytd


# --- the same figure in every story ---------------------------------------------

def test_renter_burden_is_the_same_in_every_story(db):
    values = {
        "story1": one(db, "SELECT burden_rate_pct FROM warehouse.v_story1_burden_by_tenure WHERE tenure = 'Renter'"),
        "story4 tile": one(db, "SELECT renter_burden_pct FROM warehouse.v_story4_windsor_2021"),
        "story4 scatter": one(db, "SELECT renter_burden_pct FROM warehouse.v_story4_cma_canada WHERE is_windsor"),
        "story5": one(db, "SELECT pct_renters_spending_30pct_plus FROM warehouse.v_story5_city_profile WHERE is_windsor"),
    }
    assert len({round(float(v), 1) for v in values.values()}) == 1, values


def test_latest_apartment_rent_and_vacancy_are_the_same_in_every_story(db):
    year = one(db, "SELECT MAX(period_year) FROM warehouse.v_story2_market_history")
    label = f"Oct-{str(year)[2:]}"
    rents = {
        "story2 trend": one(db, f"SELECT rent_2br_apartments FROM warehouse.v_story2_market_history WHERE period_year = {year}"),
        "story2 prices": one(db, "SELECT average_rent FROM warehouse.v_story2_bedroom_oct "
                                 f"WHERE unit_size = '2 Bedroom' AND period_label = '{label}'"),
        "story4 bars": one(db, "SELECT average_rent_2br FROM warehouse.v_story4_rent_comparison "
                               f"WHERE market = 'Windsor CMA' AND period_label = '{label}'"),
        "story4 lines": one(db, "SELECT rent_2br_apartments FROM warehouse.v_story4_city_history "
                                f"WHERE city = 'Windsor' AND period_year = {year}"),
        "story5": one(db, "SELECT average_rent_2br FROM warehouse.v_story5_city_profile WHERE is_windsor"),
    }
    assert len({float(v) for v in rents.values()}) == 1, rents
    vacancy = {
        "story2 trend": one(db, f"SELECT vacancy_rate_pct FROM warehouse.v_story2_market_history WHERE period_year = {year}"),
        "story4 bars": one(db, "SELECT vacancy_rate_pct FROM warehouse.v_story4_vacancy_comparison "
                               f"WHERE market = 'Windsor CMA' AND period_label = '{label}'"),
        "story4 lines": one(db, "SELECT vacancy_rate_pct FROM warehouse.v_story4_city_history "
                                f"WHERE city = 'Windsor' AND period_year = {year}"),
        "story5": one(db, "SELECT vacancy_rate FROM warehouse.v_story5_city_profile WHERE is_windsor"),
    }
    assert len({float(v) for v in vacancy.values()}) == 1, vacancy


def test_full_year_starts_are_the_same_in_story3_and_story5(db):
    story5 = {r["period_year"]: r["starts"] for r in db(
        "SELECT period_year, starts FROM warehouse.v_story5_supply_vs_rental_market")}
    story3 = {r["period_year"]: r["units"] for r in db(
        "SELECT period_year, units FROM warehouse.v_story3_windsor_supply_annual "
        "WHERE activity = 'Starts' AND dwelling_type = 'Total' AND NOT is_partial_year")}
    for year, starts in story5.items():
        if year in story3:
            assert float(starts) == float(story3[year]), year


# --- validated against published figures, and plausible ranges --------------------

def test_story1_matches_statistics_canadas_published_rates(db):
    for row in db("SELECT tenure, difference_pts FROM warehouse.v_story1_validation"):
        assert abs(float(row["difference_pts"])) <= 0.1, row


@pytest.mark.parametrize("view, column, low, high", [
    ("v_story2_zone_snapshot", "vacancy_rate_pct", 0, 20),
    ("v_story2_zone_snapshot", "average_rent", 300, 5000),
    ("v_story4_city_history", "vacancy_rate_pct", 0, 20),
    ("v_story4_cma_canada", "renter_burden_pct", 0, 100),
    ("v_story1_burden_by_income_tenure", "burden_rate_pct", 0, 100),
    ("v_story5_city_profile", "pct_renters_spending_30pct_plus", 0, 100),
])
def test_values_are_in_a_plausible_range(db, view, column, low, high):
    lo, hi = db(f"SELECT MIN({column}) AS lo, MAX({column}) AS hi FROM warehouse.{view}")[0].values()
    assert lo is not None and low <= float(lo) and float(hi) <= high, (lo, hi)


# --- the loads ---------------------------------------------------------------------

@pytest.mark.parametrize("table, staging_files", [
    ("fact_cma_canada", ["cma_canada.csv"]),
    ("fact_windsor_intended_market", ["windsor_intended_market.csv"]),
    ("fact_rental_market", ["windsor_rental_market.csv", "windsor_rental_market_historical.csv"]),
])
def test_each_fact_table_holds_every_row_of_its_staging_files(db, table, staging_files):
    paths = [STAGING / f for f in staging_files]
    if not all(p.exists() for p in paths):
        pytest.skip("staging files not built on this machine")
    expected = sum(len(pd.read_csv(p)) for p in paths)
    assert one(db, f"SELECT count(*) FROM warehouse.{table}") == expected


def test_every_fact_row_found_its_dimensions(db):
    # A label the loader could not match to a dimension would be a NULL key.
    missing = one(db, """SELECT count(*) FROM warehouse.fact_rental_market
                         WHERE zone_key IS NULL OR period_key IS NULL OR bedroom_type_key IS NULL
                            OR dwelling_type_key IS NULL OR tenure_key IS NULL""")
    assert missing == 0
