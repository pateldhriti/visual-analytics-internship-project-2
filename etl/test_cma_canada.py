"""Tests for etl/extract_cma_canada.py (no database needed).

Run: .venv\Scripts\python.exe -m pytest etl\test_cma_canada.py
"""

import pytest

import extract_cma_canada as ex

CITIES = ["559", "555", "537", "539", "541", "535"]  # Windsor, the four comparison cities, Toronto
OTHERS = [str(i) for i in range(100, 130)]


def test_only_whole_cmas_get_a_code():
    assert ex._code("2021S0503559") == "559"  # Census, Windsor CMA
    assert ex._code("2011S0503559") == "559"  # CMHC tables, same CMA
    assert ex._code("2021S0504010") is None  # a census agglomeration
    assert ex._code("2021S050535505") is None  # part of a CMA (Ottawa - Gatineau, Ontario part)


def test_names_match_across_census_and_cmhc():
    assert ex._key("Kitchener - Cambridge - Waterloo") == ex._key("Kitchener-Cambridge-Waterloo CMA")


def _rows(codes, indicators=("vacancy_rate", "rental_universe", "renter_households")):
    return [{"cma_code": c, "cma_name": c, "indicator": i, "period_year": 2021, "value": 1.0}
            for c in codes for i in indicators]


def test_check_needs_windsor_the_comparison_cities_and_toronto():
    ex.check(_rows(CITIES + OTHERS))
    with pytest.raises(ValueError, match="Windsor"):
        ex.check(_rows(CITIES[1:] + OTHERS))
    with pytest.raises(ValueError, match="Toronto"):
        ex.check(_rows(CITIES[:-1] + OTHERS))


def test_check_needs_rental_universe_and_renter_households():
    with pytest.raises(ValueError, match="rental universe"):
        ex.check(_rows(CITIES, ("vacancy_rate",)) + _rows(OTHERS))


def test_check_needs_most_cmas():
    with pytest.raises(ValueError, match="Only 6 CMAs"):
        ex.check(_rows(CITIES))
