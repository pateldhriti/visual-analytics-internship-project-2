"""
The figures quoted in the website's story pages and home page (KPI tiles,
narratives, "how this connects" notes), computed from the same warehouse
views as the dashboards. etl/export_site_highlights.py writes them to
web/src/data/figures.json and the pages read them from there, so a data
refresh updates every number on the site.

The pages' sentences also make comparisons ("the most in ten years",
"vacancy dipped, then recovered") that new data could make untrue. So the
file records which data the text was written for (TEXT_WRITTEN_FOR) next
to the latest data in the warehouse; when they differ, the export warns
and test_site_highlights.py fails until someone has re-read the text and
updated TEXT_WRITTEN_FOR.
"""

from sqlalchemy import text

# The data the page text was last reviewed against. Update both after
# re-reading the story pages against a newer survey or construction year.
TEXT_WRITTEN_FOR = {"rent_survey_year": 2025, "construction_year": 2025}


def _num(value):
    if value is None:
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def _rows(conn, sql: str, **params) -> list[dict]:
    return [{k: (v if isinstance(v, (str, bool)) else _num(v)) for k, v in r._mapping.items()}
            for r in conn.execute(text(sql), params)]


def _one(conn, sql: str, **params) -> dict:
    (row,) = _rows(conn, sql, **params)
    return row


def _scalar(conn, sql: str, **params):
    return next(iter(_one(conn, sql, **params).values()))


def _pct(part, whole, digits=0):
    return round(100.0 * part / whole, digits) if whole else None


def story1(conn) -> dict:
    total = _one(conn, """SELECT burdened_households AS burdened, total_households AS households, burden_rate_pct AS pct
                          FROM warehouse.v_story1_burden_by_household_type WHERE household_type_key = 1""")
    tenure = {r["tenure"]: r for r in _rows(conn, "SELECT * FROM warehouse.v_story1_burden_by_tenure")}
    bands = _rows(conn, """SELECT income_band, income_band_sort_order AS sort, burdened_households AS burdened,
                                  total_households AS households, burden_rate_pct AS pct
                           FROM warehouse.v_story1_burden_by_income_band ORDER BY income_band_sort_order""")
    under40 = [b for b in bands if b["sort"] <= 5]  # under $10,000 to $30,000-$39,999
    below_avg = next(b for b in bands if b["pct"] < total["pct"])
    types = {r["household_type_key"]: r for r in _rows(
        conn, "SELECT household_type_key, burdened_households, burden_rate_pct FROM warehouse.v_story1_burden_by_household_type")}
    severity = _one(conn, "SELECT SUM(unaccounted_households) AS n FROM warehouse.v_story1_burden_severity")
    tenure_burdened = tenure["Renter"]["burdened_households"] + tenure["Owner"]["burdened_households"]
    tenure_households = tenure["Renter"]["total_households"] + tenure["Owner"]["total_households"]
    return {
        "burdenPct": total["pct"], "burdened": total["burdened"], "households": total["households"],
        "burdenedByTenure": tenure_burdened,
        "renterPct": tenure["Renter"]["burden_rate_pct"], "ownerPct": tenure["Owner"]["burden_rate_pct"],
        "renterTimesOwner": round(tenure["Renter"]["burden_rate_pct"] / tenure["Owner"]["burden_rate_pct"]),
        "renterShareOfHouseholds": _pct(tenure["Renter"]["total_households"], tenure_households),
        "renterShareOfBurdened": _pct(tenure["Renter"]["burdened_households"], tenure_burdened),
        "lowestBandPct": bands[0]["pct"], "highestBandPct": bands[-1]["pct"],
        "under40ShareOfHouseholds": _pct(sum(b["households"] for b in under40), sum(b["households"] for b in bands)),
        "under40ShareOfBurdened": _pct(sum(b["burdened"] for b in under40), sum(b["burdened"] for b in bands)),
        # "$60,000 to $69,999" -> 60000: the first band burdened below the overall rate
        "belowAverageFromIncome": int(below_avg["income_band"].split(" ")[0].strip("$").replace(",", "")),
        "onePersonPct": types[15]["burden_rate_pct"],
        "onePersonShareOfBurdened": _pct(types[15]["burdened_households"], total["burdened"]),
        "oneParentPct": types[7]["burden_rate_pct"],
        "couplePct": types[4]["burden_rate_pct"],
        "hundredPlus": severity["n"],
    }


def story2(conn) -> dict:
    rent = _rows(conn, """SELECT period_year AS year, average_rent AS rent, yoy_change_pct AS change
                          FROM warehouse.v_story2_rent_yoy_change WHERE bedroom_type_label = 'Total' ORDER BY period_year""")
    two = _rows(conn, """SELECT period_year AS year, average_rent AS rent FROM warehouse.v_story2_rent_yoy_change
                         WHERE bedroom_type_label = '2 Bedroom' ORDER BY period_year""")
    vac = _rows(conn, """SELECT period_year AS year, vacancy_rate_pct AS v FROM warehouse.v_story2_vacancy_trend
                         WHERE dwelling_type_label = 'Combined' AND bedroom_type_label = 'Total' ORDER BY period_year""")
    low = min(vac, key=lambda r: r["v"])
    latest_label = _scalar(conn, "SELECT MAX(period_label) FROM warehouse.v_story2_zone_snapshot")
    zones = _rows(conn, """SELECT zone_label AS zone, average_rent AS rent, vacancy_rate_pct AS vacancy,
                                  share_of_zone_stock_pct AS share, rental_universe AS units
                           FROM warehouse.v_story2_zone_snapshot WHERE period_label = :p ORDER BY zone_label""", p=latest_label)
    city = [z for z in zones if z["zone"][:6] in ("Zone 1", "Zone 2", "Zone 3", "Zone 4")]
    county = [z for z in zones if z not in city]
    cheapest = min(zones, key=lambda z: z["rent"])
    priciest = max(zones, key=lambda z: z["rent"])
    turnover = {r["b"]: r["t"] for r in _rows(conn, """
        SELECT bedroom_type_label AS b, turnover_rate_pct AS t FROM warehouse.v_story2_turnover_by_bedroom
        WHERE dwelling_type_label = 'Combined' AND period_year = (SELECT MAX(period_year) FROM warehouse.v_story2_turnover_by_bedroom)""")}
    units = _scalar(conn, """SELECT value FROM warehouse.v_dashboard1_rental_trend
                             WHERE metric = 'universe' ORDER BY period_year DESC LIMIT 1""")
    return {
        "firstYear": rent[0]["year"], "latestYear": rent[-1]["year"], "units": units,
        "rentFirst": rent[0]["rent"], "rentLatest": rent[-1]["rent"],
        "rentChangePct": round(100 * (rent[-1]["rent"] / rent[0]["rent"] - 1), 1),
        "rentGrowthPrev": rent[-2]["change"], "rentGrowthLatest": rent[-1]["change"], "prevYear": rent[-2]["year"],
        "twoBedFirst": two[0]["rent"], "twoBedLatest": two[-1]["rent"],
        "twoBedRise": two[-1]["rent"] - two[0]["rent"],
        "twoBedRisePct": round(100 * (two[-1]["rent"] / two[0]["rent"] - 1), 1),
        "vacancyFirst": vac[0]["v"], "vacancyLow": low["v"], "vacancyLowYear": low["year"], "vacancyLatest": vac[-1]["v"],
        "cityZoneShare": round(sum(z["share"] for z in city)),
        "cheapestZone": cheapest["zone"].split(" - ")[-1], "cheapestRent": cheapest["rent"],
        "cheapestVacancy": cheapest["vacancy"],
        "priciestZone": priciest["zone"].split(" - ")[-1], "priciestRent": priciest["rent"],
        "zoneRentGap": priciest["rent"] - cheapest["rent"],
        "countyVacancyMin": min(z["vacancy"] for z in county), "countyVacancyMax": max(z["vacancy"] for z in county),
        "turnover": turnover["Total"], "turnoverOneIn": round(100 / turnover["Total"]),
        "turnoverStudio": turnover["Studio"], "turnoverThreeBed": turnover["3 Bedroom +"],
    }


def story3(conn) -> dict:
    annual = _rows(conn, """SELECT period_year AS year, activity, dwelling_type, units
                            FROM warehouse.v_story3_windsor_supply_annual WHERE NOT is_partial_year""")

    def u(year, activity, dwelling="Total"):
        return next((r["units"] for r in annual if r["year"] == year and r["activity"] == activity
                     and r["dwelling_type"] == dwelling), None)

    years = sorted({r["year"] for r in annual})
    first, latest = years[0], years[-1]
    starts = {y: u(y, "Starts") for y in years}
    peak = max(starts, key=starts.get)
    per1000 = {r["year"]: r["p"] for r in _rows(
        conn, "SELECT period_year AS year, starts_per_1000_households AS p FROM warehouse.v_story3_windsor_supply_per_1000_households")}
    early = [starts[y] for y in years if y < peak]
    return {
        "firstYear": first, "latestYear": latest, "peakYear": peak,
        "startsEarlyAvg": round(sum(early) / len(early), -2), "earlyLastYear": peak - 1,
        "startsPeak": starts[peak], "startsPeakPer1000": per1000.get(peak),
        "startsLatest": starts[latest], "startsFirst": starts[first],
        "startsDropPct": round(100 * (1 - starts[latest] / starts[latest - 1])) if latest - 1 in starts else None,
        "aptShareFirst": _pct(u(first, "Starts", "Apartment and Other"), starts[first]),
        "aptShareLatest": _pct(u(latest, "Starts", "Apartment and Other"), starts[latest]),
        "aptStartsLatest": u(latest, "Starts", "Apartment and Other"),
        "singlesFirst": u(first, "Starts", "Singles"), "singlesLatest": u(latest, "Starts", "Singles"),
        "completions2023": u(2023, "Completions"), "starts2023": u(2023, "Starts"),
        "completionsLatest": u(latest, "Completions"),
        "underConstructionLatest": u(latest, "Under Construction"),
        "completionsLast3": sum(u(y, "Completions") for y in years[-3:]), "last3From": years[-3],
    }


def story4(conn) -> dict:
    rents = _rows(conn, """SELECT market, average_rent_2br AS rent FROM warehouse.v_story4_rent_comparison
                           WHERE period_label = (SELECT MAX(period_label) FROM warehouse.v_story4_rent_comparison)
                           ORDER BY average_rent_2br""")
    prior = _rows(conn, """SELECT market, average_rent_2br AS rent FROM warehouse.v_story4_rent_comparison
                           WHERE period_label = (SELECT MIN(period_label) FROM warehouse.v_story4_rent_comparison)
                           ORDER BY average_rent_2br""")
    vac = _rows(conn, """SELECT market, vacancy_rate_pct AS v FROM warehouse.v_story4_vacancy_comparison
                         WHERE period_label = (SELECT MAX(period_label) FROM warehouse.v_story4_vacancy_comparison)
                         ORDER BY vacancy_rate_pct""")
    growth = _rows(conn, "SELECT market, rent_growth_pct AS g FROM warehouse.v_story4_affordability_gap ORDER BY rent_growth_pct")
    bench = {r["metric"]: r for r in _rows(conn, """SELECT * FROM warehouse.v_dashboard1_cma_benchmark
                                                    WHERE period_label = (SELECT MAX(period_label) FROM warehouse.v_dashboard1_cma_benchmark)""")}
    w = next(r for r in rents if r["market"] == "Windsor CMA")
    hist = _rows(conn, "SELECT * FROM warehouse.v_story4_period_comparison")
    hw = next(h for h in hist if h["is_windsor"])
    wh = _rows(conn, "SELECT period_year AS year, rent_change_pct AS c, vacancy_rate AS v FROM warehouse.v_story4_rent_history WHERE is_windsor ORDER BY period_year")
    jumps = [{"year": r["year"], "pct": r["c"]} for r in wh if r["c"] is not None and r["c"] >= 9]
    fastest_other = max((h for h in hist if not h["is_windsor"]), key=lambda h: h["rent_change_2015_2025"])
    speedups = {h["city_short"]: h["avg_rent_growth_2020_2025"] - h["avg_rent_growth_2015_2020"] for h in hist}

    def short(m):
        return m.replace(" CMA", "")

    return {
        "ranking": [{"market": r["market"], "rent": r["rent"], "isWindsor": r["market"] == "Windsor CMA"} for r in rents],
        "windsorRent": w["rent"], "windsorRank": [r["market"] for r in rents].index("Windsor CMA") + 1,
        "nextCheapest": short(rents[1]["market"]), "nextCheapestGap": rents[1]["rent"] - w["rent"],
        "priciest": short(rents[-1]["market"]), "priciestGap": rents[-1]["rent"] - w["rent"],
        "belowPeerMedian": -bench["average_rent"]["windsor_minus_median"],
        "windsorCheapestLastYear": prior[0]["market"] == "Windsor CMA",
        "windsorVacancy": next(r["v"] for r in vac if r["market"] == "Windsor CMA"),
        "vacancyRanking": [{"market": short(r["market"]), "vacancy": r["v"]} for r in vac],
        "windsorVacancyRankLowest": [r["market"] for r in vac].index("Windsor CMA") + 1,
        "tightest": short(vac[0]["market"]), "tightestVacancy": vac[0]["v"],
        "windsorRentGrowth": next(r["g"] for r in growth if r["market"] == "Windsor CMA"),
        "windsorRentGrowthRank": len(growth) - [r["market"] for r in growth].index("Windsor CMA"),
        "slowestGrowth": short(growth[0]["market"]), "slowestGrowthPct": growth[0]["g"],
        "fastestGrowth": short(growth[-1]["market"]), "fastestGrowthPct": growth[-1]["g"],
        "windsorTurnover": bench["turnover_rate"]["windsor_value"], "peerTurnoverMedian": bench["turnover_rate"]["cma_median_value"],
        "rent2015": hw["rent_2015"], "rent2025": hw["rent_2025"], "rentChangeDecade": hw["rent_change_2015_2025"],
        "fastestDecade": fastest_other["city_short"], "fastestDecadePct": fastest_other["rent_change_2015_2025"],
        "growthBefore": hw["avg_rent_growth_2015_2020"], "growthAfter": hw["avg_rent_growth_2020_2025"],
        "biggestSpeedup": max(speedups, key=speedups.get) == "Windsor",
        "shareOfPeers2015": hw["windsor_pct_of_peer_rent_2015"], "shareOfPeers2025": hw["windsor_pct_of_peer_rent_2025"],
        "jumps": jumps,
        "vacancyLow": min(r["v"] for r in wh if r["year"] >= 2020),
        "vacancyLowYear": min((r for r in wh if r["year"] >= 2020), key=lambda r: r["v"])["year"],
        "vacancyLatest": wh[-1]["v"],
    }


def story5(conn) -> dict:
    aff = {r["unit_size"]: r for r in _rows(conn, "SELECT * FROM warehouse.v_story5_rent_affordability")}
    prof = _rows(conn, "SELECT * FROM warehouse.v_story5_city_profile")
    w = next(p for p in prof if p["is_windsor"])
    others = [p for p in prof if not p["is_windsor"]]
    demand = _rows(conn, "SELECT * FROM warehouse.v_story5_supply_vs_demand")
    wd = next(d for d in demand if d["is_windsor"])
    age = _rows(conn, "SELECT * FROM warehouse.v_story5_renter_burden_by_age WHERE age_sort = 15")
    wa = next(a for a in age if a["is_windsor"])
    by_build = sorted(prof, key=lambda p: p["starts_per_1000_households"])
    by_units = sorted(prof, key=lambda p: p["units_per_100_renter_households"])
    same_share = [p["city"].replace(" CMA", "") for p in others
                  if round(p["rent_pct_of_median_renter_income"]) == round(w["rent_pct_of_median_renter_income"])]
    return {
        "cannotAffordPct": round(aff["2 Bedroom"]["pct_renters_who_cannot_afford"]),
        "cannotAfford": round(aff["2 Bedroom"]["renters_who_cannot_afford"], -2),
        "oneBedCannotAffordPct": aff["1 Bedroom"]["pct_renters_who_cannot_afford"],
        "rent2Bed": aff["2 Bedroom"]["average_rent"], "incomeNeeded": round(aff["2 Bedroom"]["income_needed"], -3),
        "medianIncome": aff["2 Bedroom"]["median_renter_income"],
        "affordableRent": round(aff["2 Bedroom"]["median_renter_income"] * 0.30 / 12),
        "studioIncomeNeeded": round(aff["Studio"]["income_needed"], -2),
        "rentShare": round(w["rent_pct_of_median_renter_income"]),
        "rentShareMin": round(min(p["rent_pct_of_median_renter_income"] for p in prof)),
        "rentShareMax": round(max(p["rent_pct_of_median_renter_income"] for p in prof)),
        "sameShareAs": same_share,
        "burdenPct": w["pct_renters_spending_30pct_plus"],
        "burdenLowest": w["pct_renters_spending_30pct_plus"] == min(p["pct_renters_spending_30pct_plus"] for p in prof),
        "startsPer1000": w["starts_per_1000_households"],
        "startsPer1000Rank": [p["city"] for p in by_build].index(w["city"]) + 1,
        "topBuilder": by_build[-1]["city"].replace(" CMA", ""), "topBuilderPer1000": by_build[-1]["starts_per_1000_households"],
        "populationGrowth": wd["population_growth"], "homesNeeded": round(wd["homes_needed"], -2),
        "homesCompleted": wd["homes_completed_2016_2020"], "builtPerNeeded": wd["homes_built_per_home_needed"],
        "builtPerNeededMin": min(d["homes_built_per_home_needed"] for d in demand if not d["is_windsor"]),
        "builtPerNeededMax": max(d["homes_built_per_home_needed"] for d in demand if not d["is_windsor"]),
        "unitsPer100": round(w["units_per_100_renter_households"]),
        "unitsPer100Rank": [p["city"] for p in by_units].index(w["city"]) + 1,
        "vacancyMin": min(p["vacancy_rate"] for p in prof), "vacancyMax": max(p["vacancy_rate"] for p in prof),
        "youngPct": wa["pct_30pct_plus"], "allRentersPct": wa["all_renters_pct_30pct_plus"],
        "youngOthersMin": min(a["pct_30pct_plus"] for a in age if not a["is_windsor"]),
        "youngOthersMax": max(a["pct_30pct_plus"] for a in age if not a["is_windsor"]),
    }


def build_figures(conn) -> dict:
    s2, s3 = story2(conn), story3(conn)
    return {
        "textWrittenFor": TEXT_WRITTEN_FOR,
        "latestData": {"rent_survey_year": s2["latestYear"], "construction_year": s3["latestYear"]},
        "s1": story1(conn), "s2": s2, "s3": s3, "s4": story4(conn), "s5": story5(conn),
    }


def stale_text(figures: dict) -> list[str]:
    """Which parts of the page text were written for older data than the
    warehouse now has (an empty list when the text is current)."""
    return [k for k, v in figures["latestData"].items() if v != figures["textWrittenFor"].get(k)]
