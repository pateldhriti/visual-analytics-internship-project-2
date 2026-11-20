r"""Tests for etl/extract_windsor_intended_market.py (no database needed).

Run: .venv\Scripts\python.exe -m pytest etl\test_windsor_intended_market.py
"""

import pytest

import extract_windsor_intended_market as ex

ANNUAL = [
    "Windsor - Historical Starts by Intended Market  ",
    "2023 to 2025 Dwelling Types - All",
    ",Unknown,Homeowner,Rental,Condo,Co-Op,All,",
    '2024,0,753,590,814,0,"2,157",',
    '2025,0,493,489,280,-,"1,262",',
    "",
    "Source,CMHC Starts and Completions Survey",
]
YTD = [
    "Windsor - Completions by Intended Market by Zone",
    "January - September 2026 Dwelling Types - All",
    ",Homeowner,Rental,Condo,Co-Op,All,",
    "Centre,9,21,0,0,30,",
    'Windsor,314,590,125,0,"1,029",',
    "",
    "Notes",
]


def _get(rows, period, market):
    return next(r["units"] for r in rows if r["period_label"] == period and r["intended_market"] == market)


def test_parse_reads_each_year_and_market():
    rows = ex.parse(ANNUAL)
    assert _get(rows, "2024", "Condo") == 814
    assert _get(rows, "2025", "All") == 1262  # thousands separator removed
    assert _get(rows, "2025", "Co-Op") == 0  # CMHC's "-" is nil
    assert {r["activity"] for r in rows} == {"Starts"} and not any(r["is_ytd"] for r in rows)
    ex.check(rows)


def test_parse_keeps_only_the_windsor_row_of_a_zone_export():
    rows = ex.parse(YTD)
    assert {r["period_label"] for r in rows} == {"Jan-Sep 2026"}
    assert {r["activity"] for r in rows} == {"Completions"} and all(r["is_ytd"] for r in rows)
    assert _get(rows, "Jan-Sep 2026", "Rental") == 590  # not the Centre zone's 21
    ex.check(rows)


def test_check_needs_markets_that_add_up():
    rows = ex.parse(ANNUAL)
    with pytest.raises(ValueError, match="add to"):
        ex.check([dict(r, units=1) if r["intended_market"] == "Rental" else r for r in rows])
    with pytest.raises(ValueError, match="no Rental"):
        ex.check([r for r in rows if r["intended_market"] != "Rental"])
    with pytest.raises(ValueError, match="layout"):
        ex.check(ex.parse(ANNUAL[:3]))
