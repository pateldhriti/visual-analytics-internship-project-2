"""Tests for etl/extract_peer_cma_context.py, on small made-up files (no raw data needed).

Run: .venv\\Scripts\\python.exe -m pytest etl\\test_peer_cma_context.py
"""

import io
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
    rows = [ex._row(code, src, "x", None, None, 2021, 1.0) for code in ex.CMAS for src in ("98-10-0252-01", "98-401-X2021002")]
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
