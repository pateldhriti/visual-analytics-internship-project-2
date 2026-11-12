r"""
Export the figures behind the home page's "story in four charts" from the
warehouse views to web/src/data/highlights.json, so the website's own charts
show the same numbers as the Superset dashboards instead of hand-typed ones.

    1. renters who cannot afford an average 2-bedroom (v_story5_rent_affordability)
    2. 2-bedroom rent vs median renter income, five cities (v_story5_peer_affordability)
    3. 2-bedroom rent every October 2015-2025, five cities (v_story4_rent_history)
    4. homes built vs homes needed, 2016-2021, five cities (v_story5_supply_vs_demand)
    5. what Windsor starts, by dwelling type, 2016-2020 vs 2021-2025 (v_story3_period_comparison;
       shown on the Story 3 page)

It also writes web/src/data/figures.json: every figure the story pages and
home page quote (etl/site_figures.py), and warns when the page text was
written for older data than the warehouse now has.

Run after a data refresh, then rebuild the website:
    .venv\Scripts\python.exe etl\export_site_highlights.py
"""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine
from site_figures import build_figures, stale_text

OUTPUT = Path(__file__).resolve().parents[1] / "web" / "src" / "data" / "highlights.json"
FIGURES_OUTPUT = OUTPUT.with_name("figures.json")

SHORT_CITY = """CASE city WHEN 'Kitchener-Cambridge-Waterloo CMA' THEN 'Kitchener-Waterloo'
    WHEN 'St. Catharines-Niagara CMA' THEN 'St. Catharines' ELSE REPLACE(city, ' CMA', '') END"""


def number(value):
    """Postgres NUMERIC arrives as Decimal; JSON needs int or float."""
    if value is None:
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def rows(conn, sql: str) -> list[dict]:
    return [
        {k: (v if isinstance(v, (str, bool)) else number(v)) for k, v in r._mapping.items()}
        for r in conn.execute(text(sql))
    ]


def build(conn) -> dict:
    (afford,) = rows(conn, """
        SELECT pct_renters_who_cannot_afford AS pct, renters_who_cannot_afford AS cannot,
               renter_households AS renters, average_rent AS rent, income_needed,
               median_renter_income AS median_income
        FROM warehouse.v_story5_rent_affordability WHERE unit_size = '2 Bedroom'""")
    cities = rows(conn, f"""
        SELECT {SHORT_CITY} AS city, is_windsor, average_rent_2br AS rent,
               median_renter_income AS income, rent_pct_of_median_renter_income AS rent_pct
        FROM warehouse.v_story5_peer_affordability ORDER BY average_rent_2br""")
    history = rows(conn, """
        SELECT city_short AS city, is_windsor, period_year AS year, average_rent_2br AS rent, vacancy_rate
        FROM warehouse.v_story4_rent_history ORDER BY is_windsor DESC, city_short, period_year""")
    supply = rows(conn, f"""
        SELECT {SHORT_CITY} AS city, is_windsor, homes_needed AS needed,
               homes_completed_2016_2020 AS built, homes_built_per_home_needed AS ratio
        FROM warehouse.v_story5_supply_vs_demand ORDER BY homes_built_per_home_needed""")

    mix = rows(conn, """
        SELECT dwelling_type, period, avg_units_per_year AS per_year, pct_of_total AS share
        FROM warehouse.v_story3_period_comparison WHERE activity = 'Starts'
        ORDER BY dwelling_type, period""")

    years = sorted({r["year"] for r in history})
    series = []
    for city in dict.fromkeys(r["city"] for r in history):
        by_year = {r["year"]: r for r in history if r["city"] == city}
        series.append({
            "city": city,
            "isWindsor": by_year[years[0]]["is_windsor"],
            "rent": [by_year.get(y, {}).get("rent") for y in years],
            "vacancy": [by_year.get(y, {}).get("vacancy_rate") for y in years],
        })

    return {
        "generated": date.today().isoformat(),
        "affordability": {
            "pct": afford["pct"], "cannot": afford["cannot"], "renters": afford["renters"],
            "rent": afford["rent"], "incomeNeeded": afford["income_needed"],
            "medianIncome": afford["median_income"],
        },
        "cities": [
            {"city": c["city"], "isWindsor": c["is_windsor"], "rent": c["rent"], "income": c["income"],
             "rentPct": c["rent_pct"]}
            for c in cities
        ],
        "rentHistory": {"years": years, "series": series},
        "supply": [
            {"city": s["city"], "isWindsor": s["is_windsor"], "needed": s["needed"], "built": s["built"],
             "ratio": s["ratio"]}
            for s in supply
        ],
        "startsMix": [
            {
                "type": t,
                "before": next(m for m in mix if m["dwelling_type"] == t and m["period"] == "2016 to 2020"),
                "after": next(m for m in mix if m["dwelling_type"] == t and m["period"] == "2021 to 2025"),
            }
            for t in dict.fromkeys(m["dwelling_type"] for m in mix)
        ],
    }


def check(data: dict) -> None:
    """Fail loudly rather than publish a chart with a city or year missing."""
    if len(data["cities"]) != 5 or len(data["supply"]) != 5 or len(data["rentHistory"]["series"]) != 5:
        raise ValueError("Expected Windsor and the four comparison cities in every chart")
    if {m["type"] for m in data["startsMix"]} != {"Total", "Singles", "Semis", "Row", "Apartment and Other"}:
        raise ValueError("Expected the total and the four dwelling types for both periods")
    for s in data["rentHistory"]["series"]:
        if any(v is None for v in s["rent"]):
            raise ValueError(f"{s['city']}: a year has no 2-bedroom rent")


def main() -> None:
    with get_engine().connect() as conn:
        data = build(conn)
        figures = build_figures(conn)
    check(data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    FIGURES_OUTPUT.write_text(json.dumps(figures, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {FIGURES_OUTPUT}")
    for part in stale_text(figures):
        print(f"WARNING: the story pages were written for {part} {figures['textWrittenFor'][part]}, "
              f"the data now has {figures['latestData'][part]}. The numbers update by themselves, but re-read "
              f"the pages' wording (e.g. 'the most in ten years'), then update TEXT_WRITTEN_FOR in "
              f"etl/site_figures.py.")


if __name__ == "__main__":
    main()
