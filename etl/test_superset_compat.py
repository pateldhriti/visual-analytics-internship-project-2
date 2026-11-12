"""Tests for etl/superset_compat.py (no Superset needed).

Run: .venv\Scripts\python.exe -m pytest etl\test_superset_compat.py
"""

import importlib

import pytest

import superset_compat as compat


def test_dist_bar_becomes_an_echarts_bar_with_the_same_query():
    old = {
        "groupby": ["year_label"], "columns": ["activity"],
        "metrics": [{"label": "Units", "expressionType": "SQL", "sqlExpression": "SUM(units)"}],
        "adhoc_filters": [{"subject": "x"}], "bar_stacked": True, "y_axis_format": ",d",
        "x_axis_label": "Year", "row_limit": 50,
    }
    new = compat.from_dist_bar(old)
    assert new["x_axis"] == "year_label" and new["groupby"] == ["activity"]
    assert new["metrics"] == old["metrics"] and new["adhoc_filters"] == old["adhoc_filters"]
    assert new["stack"] == "Stack" and new["y_axis_format"] == ",d" and new["x_axis_title"] == "Year"


def test_ordered_single_series_bars_sort_by_value_and_horizontal_drops_the_category_title():
    old = {"groupby": ["band"], "metrics": [{"label": "Rate"}], "order_desc": True, "x_axis_label": "Band"}
    assert compat.from_dist_bar(old)["x_axis_sort"] == "Rate"
    horizontal = compat.from_dist_bar(old, orientation="horizontal")
    assert horizontal["x_axis_title"] == "" and horizontal["x_axis_sort_asc"] is False


def test_upgrade_legacy_bars_leaves_other_charts_alone():
    charts = {"a": {"viz_type": "dist_bar", "params": {"groupby": ["x"], "metrics": ["m"]}},
              "b": {"viz_type": "table", "params": {"keep": 1}}}
    compat.upgrade_legacy_bars(charts)
    assert charts["a"]["viz_type"] == "echarts_timeseries_bar"
    assert charts["b"] == {"viz_type": "table", "params": {"keep": 1}}


def test_colours_keep_existing_entries_and_never_repeat_within_a_chart():
    existing = {"Windsor": compat.PALETTE[0]}
    added = compat.assign_colors(["Windsor", "London", "Hamilton"], existing)
    assert "Windsor" not in added
    assert compat.PALETTE[0] not in added.values()
    assert len(set(added.values())) == 2


def test_names_are_unchanged_locally(monkeypatch):
    assert compat.named("Story 1: x") == "Story 1: x"


def test_names_are_prefixed_once_on_the_shared_server(monkeypatch):
    monkeypatch.setenv("SUPERSET_TARGET", "shared")
    shared = importlib.reload(compat)
    try:
        assert shared.named("Story 1: x") == "Windsor Housing | Story 1: x"
        assert shared.named(shared.named("Story 1: x")) == "Windsor Housing | Story 1: x"
        charts = shared.prefix_names({"a": {"slice_name": "Chart", "legacy_names": ["Old"]}})
        assert charts["a"] == {"slice_name": "Windsor Housing | Chart", "legacy_names": ["Windsor Housing | Old"]}
        assert shared.heatmap("x", "y", {}, [], ".1f")[0] == "heatmap_v2"
    finally:
        monkeypatch.setenv("SUPERSET_TARGET", "local")
        importlib.reload(compat)


def test_an_unknown_target_is_rejected(monkeypatch):
    monkeypatch.setenv("SUPERSET_TARGET", "staging")
    with pytest.raises(ValueError, match="local' or 'shared"):
        importlib.reload(compat)
    monkeypatch.setenv("SUPERSET_TARGET", "local")
    importlib.reload(compat)
