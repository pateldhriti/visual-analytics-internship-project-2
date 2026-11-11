"""Tests for etl/extract_peer_cma_context.py, on small made-up files (no raw data needed).

Run: .venv\\Scripts\\python.exe -m pytest etl\\test_peer_cma_context.py
"""

import zipfile

import pytest

import extract_peer_cma_context as ex


def test_cma_code_matches_both_dguid_vintages():
    assert ex.cma_code("2021S0503559") == "559"
    assert ex.cma_code("2011S0503555") == "555"


@pytest.mark.parametrize("dguid", ["2021S0503535", "2021A000235", "2021S0504010", None, ""])
def test_cma_code_ignores_other_places(dguid):
    # Toronto (535), Ontario, Grand Falls-Windsor (a CA, not a CMA), blanks
    assert ex.cma_code(dguid) is None


def test_check_names_every_missing_city_and_source():
    present = [src for src in ex.SOURCES if src != "34-10-0154-01"]
    rows = [ex._row(code, src, "x", None, None, 2021, 1.0) for code in ex.CMAS for src in present]
    with pytest.raises(ValueError, match="34-10-0154-01"):
        ex.check(rows)
    rows += [ex._row(code, "34-10-0154-01", "starts", None, "Total", 2020, 1.0) for code in ex.CMAS]
    ex.check(rows)  # complete: no error


def _starts_zip(tmp_path, months_2025: int):
    header = '"REF_DATE","GEO","DGUID","Housing estimates","Type of unit","VALUE"\n'
    lines = []
    for year, months in ((2024, 12), (2025, months_2025)):
        for m in range(1, months + 1):
            for code in ex.CMAS:
                lines.append(f'"{year}-{m:02d}","x","2011S0503{code}","Housing starts","Total units","10"\n')
                # a unit type and a place the extract must skip
                lines.append(f'"{year}-{m:02d}","x","2011S0503{code}","Housing starts","Row units","99"\n')
            lines.append(f'"{year}-{m:02d}","Toronto","2011S0503535","Housing starts","Total units","500"\n')
    path = tmp_path / "34100154-eng.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("34100154.csv", header + "".join(lines))
    return path


def test_starts_are_summed_by_year_and_partial_years_dropped(tmp_path):
    rows = ex.extract_starts(_starts_zip(tmp_path, months_2025=9))
    assert {r["period_year"] for r in rows} == {2024}  # Jan-Sep 2025 left out
    assert {r["cma_name"] for r in rows} == set(ex.CMAS.values())
    assert all(r["value"] == 120 and r["category"] == "Total" for r in rows)


def test_full_year_is_kept(tmp_path):
    rows = ex.extract_starts(_starts_zip(tmp_path, months_2025=12))
    assert {r["period_year"] for r in rows} == {2024, 2025}


def test_census_profile_rejects_renumbered_characteristic(tmp_path):
    header = "CENSUS_YEAR,DGUID,ALT_GEO_CODE,GEO_LEVEL,GEO_NAME,TNR_SF,TNR_LF,DQF,CHARACTERISTIC_ID,CHARACTERISTIC_NAME,NOTE,C1_COUNT_TOTAL\n"
    good = '2021,"2021S0503559","559","Census metropolitan area","Windsor",0,0,"0",1492,"  % of tenant households spending 30% or more of its income on shelter costs",,34.8\n'
    path = tmp_path / "profile.csv"
    path.write_text(header + good, encoding="latin-1")
    (row,) = ex.extract_census_profile(path)
    assert row["indicator"] == "pct_spending_30pct_plus" and row["value"] == 34.8

    path.write_text(header + good.replace("% of tenant households", "Something else"), encoding="latin-1")
    with pytest.raises(ValueError, match="update PROFILE_ITEMS"):
        ex.extract_census_profile(path)


def test_shelter_cost_keeps_renter_bands_median_and_burden(tmp_path):
    cols = [
        "REF_DATE", "GEO", "DGUID", ex.INCOME_COL, *ex.SHELTER_TOTALS, ex.RATIO_COL, "Coordinate",
        "Tenure (3):Total - Tenure[1]", "Symbol", "Tenure (3):Owner[2]", "Symbol", "Tenure (3):Renter[3]", "Symbol",
    ]
    totals = list(ex.SHELTER_TOTALS.values())

    def line(dguid, band, ratio, renter, household="Total - Household type including census family structure"):
        values = ["2021", "g", dguid, band, household, *totals[1:], ratio, "1", "100", "", "60", "", str(renter), ""]
        return ",".join(f'"{v}"' for v in values)

    total_ratio = "Total - Shelter-cost-to-income ratio"
    body = "\n".join([
        line("2021S0503559", "$40,000 to $49,999", total_ratio, 5000),
        line("2021S0503559", "$40,000 to $49,999", "Spending 30% or more of income on shelter costs", 2000),
        line("2021S0503559", "$40,000 to $49,999", "Spending less than 30% of income on shelter costs", 3000),
        line("2021S0503559", "Median total income of household ($)", total_ratio, 48400),
        line("2021S0503559", "$40,000 to $49,999", total_ratio, 7, household="Census-family households"),
        line("2021S0503535", "$40,000 to $49,999", total_ratio, 99999),
    ])
    path = tmp_path / "shelter.csv"
    path.write_text(",".join(f'"{c}"' for c in cols) + "\n" + body + "\n", encoding="utf-8")
    rows = [r for r in ex.extract_shelter_cost(path) if r["tenure"] == "Renter"]
    got = {(r["indicator"], r["category"]): r["value"] for r in rows}
    assert got == {
        ("households", "$40,000 to $49,999"): 5000,
        ("households_30pct_plus", "$40,000 to $49,999"): 2000,
        ("median_household_income", None): 48400,
    }


def test_housing_indicators_keep_renters_by_age_and_skip_other_breakdowns(tmp_path):
    tenure_total, tenure_renter = ex.INDICATOR_TENURE_COLS
    cols = ["REF_DATE", "GEO", "DGUID", ex.AGE_COL, *ex.INDICATOR_TOTALS, ex.INDICATOR_COL, "Coordinate",
            tenure_total, "Symbol", tenure_renter, "Symbol"]
    totals = list(ex.INDICATOR_TOTALS.values())
    affordability = "Affordability: 30% or more of household income is spent on shelter costs"

    def line(dguid, age, indicator, total, renter, household=totals[0]):
        values = ["2021", "g", dguid, age, household, *totals[1:], indicator, "1", total, "", renter, ""]
        return ",".join(f'"{v}"' for v in values)

    body = "\n".join([
        line("2021S0503559", "15 to 24 years", "Total - Housing indicators", 3000, 2680),
        line("2021S0503559", "15 to 24 years", affordability, 1300, 1246),
        line("2021S0503559", "15 to 24 years", "In core need", 400, 335),
        line("2021S0503559", "15 to 24 years", "Suitability: not suitable", 99, 99),  # not kept
        line("2021S0503559", "15 to 24 years", affordability, 7, 7, household="Census-family households"),
        line("2021S0503535", "15 to 24 years", affordability, 9999, 9999),  # Toronto
    ])
    path = tmp_path / "98100241-eng.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("98100241.csv", ",".join(f'"{c}"' for c in cols) + "\n" + body + "\n")
    rows = ex.extract_housing_indicators_by_age(path)
    got = {(r["indicator"], r["tenure"]): r["value"] for r in rows}
    assert got == {
        ("households", "Total"): 3000, ("households", "Renter"): 2680,
        ("households_30pct_plus", "Total"): 1300, ("households_30pct_plus", "Renter"): 1246,
        ("households_core_need", "Total"): 400, ("households_core_need", "Renter"): 335,
    }
    assert {r["category"] for r in rows} == {"15 to 24 years"}
    assert {r["cma_name"] for r in rows} == {"Windsor CMA"}


def _rms_workbooks(tmp_path, kcw_label="Kitchener - Cambridge - Waterloo CMA"):
    import openpyxl

    for code, slug in ex.RMS_FILES.items():
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Table 3.1.3"
        # CMHC spaces the hyphens ("St. Catharines - Niagara CMA"); the extract normalises them.
        name = kcw_label if code == "541" else ex.CMAS[code].replace("-", " - ")
        ws.append([f"3.1.3 Number of Private Row (Townhouse) and Apartment Units in the Universe - {ex.CMAS[code]}"])
        ws.append(["Zone 1 - Centre", "1", "1", "2", "2", "3", "3", "4", "4", "10", "10"])
        ws.append([name, "100", "110", "1,000", "1,100", "2,000", "2,100", "300", "310", "3,400", "3,620"])
        wb.save(tmp_path / f"{slug}.xlsx")
    return tmp_path


def test_rental_universe_reads_each_cma_total_row(tmp_path):
    rows = ex.extract_rental_universe(_rms_workbooks(tmp_path))
    assert len(rows) == 10  # 5 cities x Oct-24 and Oct-25
    assert {(r["period_year"], r["value"]) for r in rows} == {(2024, 3400.0), (2025, 3620.0)}
    assert {r["cma_name"] for r in rows} == set(ex.CMAS.values())


def test_rental_universe_fails_loudly_when_a_total_row_is_missing(tmp_path):
    with pytest.raises(ValueError, match="Kitchener"):
        ex.extract_rental_universe(_rms_workbooks(tmp_path, kcw_label="Kitchener Region"))


def _table_zip(tmp_path, pid: str, header: str, lines: list[str]):
    path = tmp_path / f"{pid}-eng.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{pid}.csv", "﻿" + header + "".join(lines))
    return path


def test_rent_history_keeps_row_and_apartment_rents_from_2015(tmp_path):
    header = '"REF_DATE","GEO","DGUID","Type of structure","Type of unit","VALUE","STATUS"\n'
    both = "Row and apartment structures of three units and over"
    lines = [
        f'"2015","Windsor, Ontario","2011S0503559","{both}","Two bedroom units","823",""\n',
        f'"2025","Windsor, Ontario","2011S0503559","{both}","Two bedroom units","1451",""\n',
        f'"2025","Windsor, Ontario","2011S0503559","{both}","Bachelor units","",F\n',  # suppressed
        f'"2014","Windsor, Ontario","2011S0503559","{both}","Two bedroom units","799",""\n',  # before 2015
        '"2025","Windsor, Ontario","2011S0503559","Apartment structures of three units and over","Two bedroom units","1454",""\n',
        f'"2025","Toronto, Ontario","2011S0503535","{both}","Two bedroom units","2000",""\n',
    ]
    rows = ex.extract_rent_history(_table_zip(tmp_path, "34100133", header, lines))
    assert [(r["period_year"], r["category"], r["value"]) for r in rows] == [
        (2015, "2 Bedroom", 823.0),
        (2025, "2 Bedroom", 1451.0),
    ]
    assert {r["source_table"] for r in rows} == {"34-10-0133-01"}


def test_vacancy_history_keeps_the_five_cities(tmp_path):
    header = '"REF_DATE","GEO","DGUID","VALUE"\n'
    lines = [f'"2020","x","2011S0503{code}","3.5"\n' for code in ex.CMAS]
    lines.append('"2020","Census metropolitan areas","","3.1"\n')
    rows = ex.extract_vacancy_history(_table_zip(tmp_path, "34100130", header, lines))
    assert {r["cma_name"] for r in rows} == set(ex.CMAS.values())
    assert all(r["indicator"] == "vacancy_rate" and r["value"] == 3.5 for r in rows)


def test_refresh_table_falls_back_to_the_saved_copy(tmp_path, monkeypatch):
    saved = _table_zip(tmp_path, "34100130", '"REF_DATE","GEO","DGUID","VALUE"\n', [])

    def offline(*args, **kwargs):
        raise ex.requests.ConnectionError("offline")

    monkeypatch.setattr(ex.requests, "get", offline)
    assert ex.refresh_table(saved) == saved
    with pytest.raises(ex.requests.ConnectionError):
        ex.refresh_table(tmp_path / "34100133-eng.zip")  # nothing saved yet
