"""Tests for etl/export_site_highlights.py's check (no database needed).

Run: .venv\Scripts\python.exe -m pytest etl\test_site_highlights.py
"""

import copy
import json
from pathlib import Path

import pytest

from export_site_highlights import OUTPUT, check

CITIES = ["Windsor", "London", "Hamilton", "St. Catharines", "Kitchener-Waterloo"]


def _data():
    return {
        "cities": [{"city": c} for c in CITIES],
        "supply": [{"city": c} for c in CITIES],
        "rentHistory": {"years": [2015, 2016], "series": [{"city": c, "rent": [900, 950]} for c in CITIES]},
        "startsMix": [{"type": t} for t in ("Total", "Singles", "Semis", "Row", "Apartment and Other")],
    }


def test_complete_data_passes():
    check(_data())


def test_a_missing_city_fails():
    data = _data()
    data["supply"].pop()
    with pytest.raises(ValueError, match="four comparison cities"):
        check(data)


def test_a_missing_dwelling_type_fails():
    data = _data()
    data["startsMix"].pop()
    with pytest.raises(ValueError, match="dwelling types"):
        check(data)


def test_a_missing_year_fails():
    data = copy.deepcopy(_data())
    data["rentHistory"]["series"][2]["rent"][1] = None
    with pytest.raises(ValueError, match="Hamilton"):
        check(data)


def test_the_committed_file_passes_the_same_check():
    check(json.loads(Path(OUTPUT).read_text(encoding="utf-8")))
