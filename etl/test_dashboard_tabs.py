"""Tests for etl/dashboard_tabs.py.

Run: .venv\Scripts\python.exe -m pytest etl\test_dashboard_tabs.py
"""

import pytest

from dashboard_tabs import TABS_ID, add_tabs


def _grid():
    return {
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": ["HEADER-a", "ROW-a", "HEADER-b", "ROW-b"],
                    "parents": ["ROOT_ID"]},
        "HEADER-a": {"type": "HEADER", "id": "HEADER-a", "parents": ["ROOT_ID", "GRID_ID"]},
        "ROW-a": {"type": "ROW", "id": "ROW-a", "children": ["CHART-a"], "parents": ["ROOT_ID", "GRID_ID"]},
        "CHART-a": {"type": "CHART", "id": "CHART-a", "parents": ["ROOT_ID", "GRID_ID", "ROW-a"]},
        "HEADER-b": {"type": "HEADER", "id": "HEADER-b", "parents": ["ROOT_ID", "GRID_ID"]},
        "ROW-b": {"type": "ROW", "id": "ROW-b", "children": ["CHART-b"], "parents": ["ROOT_ID", "GRID_ID"]},
        "CHART-b": {"type": "CHART", "id": "CHART-b", "parents": ["ROOT_ID", "GRID_ID", "ROW-b"]},
    }


def test_sections_move_into_their_tabs_with_full_parent_paths():
    pos = add_tabs(_grid(), [("TAB-1", "One", ["HEADER-a", "ROW-a"]), ("TAB-2", "Two", ["ROW-b"])])
    assert pos["GRID_ID"]["children"] == [TABS_ID]
    assert pos[TABS_ID]["children"] == ["TAB-1", "TAB-2"]
    assert pos["TAB-2"]["meta"]["text"] == "Two"
    assert pos["CHART-a"]["parents"] == ["ROOT_ID", "GRID_ID", TABS_ID, "TAB-1", "ROW-a"]
    assert pos["ROW-b"]["parents"] == ["ROOT_ID", "GRID_ID", TABS_ID, "TAB-2"]
    assert "HEADER-b" not in pos  # unlisted header: the tab title replaces it


def test_a_row_left_out_is_an_error():
    with pytest.raises(ValueError, match="ROW-b"):
        add_tabs(_grid(), [("TAB-1", "One", ["ROW-a"])])


def test_a_section_in_two_tabs_is_an_error():
    with pytest.raises(ValueError, match="two tabs"):
        add_tabs(_grid(), [("TAB-1", "One", ["ROW-a", "ROW-b"]), ("TAB-2", "Two", ["ROW-b"])])
