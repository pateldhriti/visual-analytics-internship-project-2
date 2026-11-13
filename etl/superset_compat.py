"""
Keep the dashboard builders working on two Superset installations:

    local   this project's Superset 3.1 (docker/superset_config.py), where we
            add our own colour scheme (windsor_housing), template processing
            and styled HTML for Story 2's explanation panel
    shared  the university's Superset (apss.cs.uwindsor.ca, 6.x), where we
            are ordinary users and none of those settings can be changed

Choose with the SUPERSET_TARGET environment variable (default: local).

What this module provides:

    from_dist_bar(params)   the legacy NVD3 bar chart ("dist_bar") was removed
                            after Superset 3; every builder now describes its
                            bars in the old shape and draws them with the ECharts
                            bar chart, which both versions have
    finish_dashboard(...)   run after a dashboard is built: gives every series
                            an explicit colour from the project palette (so the
                            charts look the same without our colour scheme) and
                            fills in any missing cross-filter settings (so a
                            viewer's browser never has to save them)
"""

import json
import os

from setup_superset_dashboard import SUPERSET_URL

SUPERSET_TARGET = os.getenv("SUPERSET_TARGET", "local").strip().lower()
if SUPERSET_TARGET not in ("local", "shared"):
    raise ValueError(f"SUPERSET_TARGET must be 'local' or 'shared', not {SUPERSET_TARGET!r}")
SHARED = SUPERSET_TARGET == "shared"

# The windsor_housing palette (docker/superset_config.py), in slot order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
COLOR_SCHEME = "supersetColors" if SHARED else "windsor_housing"

# On the shared server every chart and dashboard name starts with this, so a
# builder (which finds charts and dashboards by name) can only ever match our
# own; dashboards still show the plain chart titles (finish_dashboard()).
NAME_PREFIX = "Windsor Housing | " if SHARED else ""


def named(name: str) -> str:
    """A chart or dashboard name with the shared-server prefix (no change locally)."""
    return name if name.startswith(NAME_PREFIX) else NAME_PREFIX + name


def match_bar_order(charts: dict) -> dict:
    """Superset 6 draws a horizontal bar chart's categories bottom-up where
    3.1 draws them top-down, so on the shared server every horizontal bar
    chart's sort is reversed: the bars then read in the same order as
    locally (Zone 1 at the top; largest first where sorted by value)."""
    if not SHARED:
        return charts
    for spec in charts.values():
        params = spec.get("params", {})
        if spec.get("viz_type") != "echarts_timeseries_bar" or params.get("orientation") != "horizontal":
            continue
        x = params["x_axis"]
        x_label = x["label"] if isinstance(x, dict) else x
        if params.get("x_axis_sort"):
            params["x_axis_sort_asc"] = not params.get("x_axis_sort_asc", True)
        else:  # unsorted: 3.1 shows the categories in ascending order, top-down
            params["x_axis_sort"] = x_label
            params["x_axis_sort_asc"] = False
        if params.get("groupby"):
            # With series (each zone or city is its own series, for
            # cross-filtering and the Windsor colour) Superset 6 reads
            # x_axis_sort as a sort type: by name, or by the bar's total.
            params["x_axis_sort"] = "name" if params["x_axis_sort"] == x_label else "sum"
        if params.get("stack") is True:  # Superset 6 stacks only on "Stack"
            params["stack"] = "Stack"
    return charts


def prefix_names(charts: dict) -> dict:
    """Apply named() to every chart spec's slice_name (and legacy_names), in place."""
    for spec in charts.values():
        spec["slice_name"] = named(spec["slice_name"])
        if "legacy_names" in spec:
            spec["legacy_names"] = [named(n) for n in spec["legacy_names"]]
    return charts

# Series that appear on several dashboards keep one colour everywhere.
PROJECT_LABEL_COLORS = {
    "Starts": PALETTE[0],
    "Starts per 1,000 Households": PALETTE[0],
    "Completions": PALETTE[1],
    "Completions per 1,000 Households": PALETTE[1],
    "Under Construction": PALETTE[2],
    "Owner": PALETTE[0],
    "Renter": PALETTE[1],
}

NO_SERIES_VIZ = {"big_number_total", "big_number", "table", "handlebars", "markdown"}


def from_dist_bar(params: dict, **overrides) -> dict:
    """An ECharts bar chart's params from a dist_bar's: x axis = the first
    groupby, one series per `columns` value (or per metric), same filters,
    stacking, sorting, labels and number format. `overrides` set ECharts
    options directly (e.g. orientation="horizontal" for long labels)."""
    x = params["groupby"][0]
    series = list(params.get("columns") or [])
    metric_labels = [m["label"] if isinstance(m, dict) else m for m in params["metrics"]]
    out = {
        "x_axis": x,
        "metrics": params["metrics"],
        "groupby": series,
        "adhoc_filters": params.get("adhoc_filters", []),
        "row_limit": params.get("row_limit", 100),
        "color_scheme": COLOR_SCHEME,
        "show_legend": params.get("show_legend", True),
        "legendOrientation": "top",
        "rich_tooltip": params.get("rich_tooltip", True),
        "show_value": params.get("show_bar_value", False),
        "y_axis_format": params.get("y_axis_format", "SMART_NUMBER"),
        "x_axis_title": params.get("x_axis_label", ""),
        "x_axis_title_margin": 30 if params.get("x_axis_label") else 15,
        "y_axis_title": params.get("y_axis_label", ""),
        "y_axis_title_margin": 50 if params.get("y_axis_label") else 15,
        "y_axis_title_position": "Left",
        "truncateYAxis": False,
        "y_axis_bounds": [None, None],
    }
    if params.get("bar_stacked") or params.get("stack"):
        out["stack"] = "Stack"
    if params.get("order_desc") and not series:
        out["x_axis_sort"], out["x_axis_sort_asc"] = metric_labels[0], False
    elif params.get("order_bars"):
        out["x_axis_sort"], out["x_axis_sort_asc"] = x, True
    if overrides.get("orientation") == "horizontal":
        # The category axis is now on the left beside long labels, so it
        # loses its title; the value axis title moves below the ticks.
        out.update({"x_axis_title": "", "x_axis_title_margin": 15, "y_axis_title_margin": 30})
    out.update(overrides)
    return out


def upgrade_legacy_bars(charts: dict, overrides: dict | None = None) -> dict:
    """Convert every dist_bar spec in a builder's CHARTS dict in place;
    `overrides` maps a chart key to extra ECharts options."""
    for key, spec in charts.items():
        if spec.get("viz_type") == "dist_bar":
            spec["viz_type"] = "echarts_timeseries_bar"
            spec["params"] = from_dist_bar(spec["params"], **(overrides or {}).get(key, {}))
    return charts


def assign_colors(series: list[str], label_colors: dict) -> dict:
    """Colours for series that have none yet: the first palette colour not
    already used in this chart, so every chart starts with the project blue
    and no two series in a chart share a colour. Existing entries are kept,
    so a city or zone has the same colour on every chart."""
    used = {label_colors[s] for s in series if s in label_colors}
    added = {}
    for s in series:
        if s in label_colors or s in added:
            continue
        free = [c for c in PALETTE if c not in used] or PALETTE
        added[s] = free[0]
        used.add(free[0])
    return added


def chart_series(session, headers, chart: dict) -> list[str]:
    """The series a chart draws: the values of its groupby column (read
    through Superset), or its metric labels when it has no groupby."""
    form = chart["form_data"]
    groupby = form.get("groupby") or form.get("columns") or []
    physical = [g for g in groupby if isinstance(g, str)]
    if physical:
        dataset_id = int(str(form["datasource"]).split("__")[0])
        resp = session.get(
            f"{SUPERSET_URL}/api/v1/datasource/table/{dataset_id}/column/{physical[0]}/values/", headers=headers
        )
        resp.raise_for_status()
        return sorted(str(v) for v in resp.json()["result"] if v is not None)
    if groupby:  # a SQL-expression series (e.g. Windsor vs the average): builders colour these
        return []
    metrics = form.get("metrics") or ([form["metric"]] if form.get("metric") else [])
    return [m["label"] if isinstance(m, dict) else m for m in metrics]


def finish_dashboard(session, headers, dashboard_id: int, drop_title_prefix: str = "") -> dict:
    """Fill in what a dashboard's builder did not set, without changing what
    it did: a colour for every series, a cross-filter entry for every ECharts
    chart, and the colour scheme for this Superset. On the dashboard, chart
    titles lose the shared-server name prefix and `drop_title_prefix` (e.g.
    "Story 5: ", which every Story 5 chart name starts with). Returns what
    was added."""
    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", headers=headers)
    resp.raise_for_status()
    metadata = json.loads(resp.json()["result"]["json_metadata"] or "{}")
    charts = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}/charts", headers=headers)
    charts.raise_for_status()
    charts = sorted(charts.json()["result"], key=lambda c: c["id"])
    chart_ids = [c["id"] for c in charts]

    label_colors = {**(metadata.get("label_colors") or {}), **PROJECT_LABEL_COLORS}
    new_colors = {}
    for chart in charts:
        if chart["form_data"].get("viz_type") in NO_SERIES_VIZ:
            continue
        added = assign_colors(chart_series(session, headers, chart), {**label_colors, **new_colors})
        new_colors.update(added)

    config = dict(metadata.get("chart_configuration") or {})
    no_cross_filter = {"scope": {"rootPath": ["ROOT_ID"], "excluded": chart_ids}, "chartsInScope": []}
    new_config = {
        str(c["id"]): {"id": c["id"], "crossFilters": no_cross_filter}
        for c in charts
        if str(c["form_data"].get("viz_type", "")).startswith("echarts") and str(c["id"]) not in config
    }

    metadata["label_colors"] = {**label_colors, **new_colors}
    metadata["chart_configuration"] = {**config, **new_config}
    metadata.setdefault("global_chart_configuration", no_cross_filter)
    metadata["cross_filters_enabled"] = True
    metadata["color_scheme"] = COLOR_SCHEME
    if SHARED:
        # The shared Superset computes these itself (and from 4.x keeps
        # shared_label_colors as a list, not the dict 3.1 uses).
        metadata.pop("color_scheme_domain", None)
    else:
        metadata["color_scheme_domain"] = PALETTE
        metadata.setdefault("shared_label_colors", {})
    for key, default in (("timed_refresh_immune_slices", []), ("expanded_slices", {}), ("refresh_frequency", 0)):
        metadata.setdefault(key, default)
    body = {"json_metadata": json.dumps(metadata)}
    if NAME_PREFIX or drop_title_prefix:
        # Show the plain chart titles on the dashboard, not the prefixed names.
        position = json.loads(resp.json()["result"]["position_json"] or "{}")
        names = {c["id"]: c["slice_name"] for c in charts}
        for node in position.values():
            if isinstance(node, dict) and node.get("type") == "CHART" and not node["meta"].get("sliceNameOverride"):
                name = names.get(node["meta"].get("chartId"), "")
                shown = name[len(NAME_PREFIX):] if NAME_PREFIX and name.startswith(NAME_PREFIX) else name
                if drop_title_prefix and shown.startswith(drop_title_prefix):
                    shown = shown[len(drop_title_prefix):]
                if shown != name:
                    node["meta"]["sliceNameOverride"] = shown
        body["position_json"] = json.dumps(position)
    session.put(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", headers=headers, json=body).raise_for_status()
    return {"colors_added": new_colors, "cross_filter_entries_added": sorted(int(k) for k in new_config)}


# --- richer chart types -------------------------------------------------------
# Built-in on both installations; where a type was replaced between versions
# (the heatmap), the one this Superset has is chosen.


def trendline_kpi(metric: dict, time_column: str, filters: list, number_format: str,
                  compare_lag: int, compare_suffix: str, subheader: str = "") -> tuple[str, dict]:
    """Big Number with Trendline: the latest value, its change over
    `compare_lag` periods, and the line of every period underneath. Both
    the newer (x_axis) and older (granularity_sqla) time settings are given,
    so either version reads the one it uses."""
    return "big_number", {
        "metric": metric,
        "adhoc_filters": filters,
        "x_axis": time_column,
        "granularity_sqla": time_column,
        "time_grain_sqla": "P1Y",
        "time_range": "No filter",
        "compare_lag": compare_lag,
        "compare_suffix": compare_suffix,
        "show_trend_line": True,
        "start_y_axis_at_zero": False,
        "rolling_type": "None",
        "y_axis_format": number_format,
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
        "subheader": subheader,
        "color_picker": {"r": 42, "g": 120, "b": 214, "a": 1},  # project blue, PALETTE[0]
    }


def heatmap(x: str, y: str, metric: dict, filters: list, number_format: str) -> tuple[str, dict]:
    """A grid of `metric` by `x` (columns) and `y` (rows), one sequential
    blue scale, each cell labelled with its value."""
    common = {
        "metric": metric,
        "adhoc_filters": filters,
        "row_limit": 1000,
        "linear_color_scheme": "superset_seq_1",  # one blue scale, in both versions
        "normalize_across": "heatmap",
        "show_legend": False,  # every cell prints its value
        "show_values": True,
        "y_axis_format": number_format,
        "sort_x_axis": "alpha_asc",
        "sort_y_axis": "alpha_asc",
        "xscale_interval": -1,
        "yscale_interval": -1,
    }
    if SHARED:  # heatmap_v2 (ECharts), Superset 4.1 and later; a wider left margin for long row labels
        return "heatmap_v2", {**common, "x_axis": x, "groupby": [y], "show_percentage": False,
                              "value_bounds": [None, None], "left_margin": 170}
    return "heatmap", {**common, "all_columns_x": x, "all_columns_y": y, "show_perc": False,
                       "canvas_image_rendering": "pixelated", "left_margin": "auto", "bottom_margin": "auto"}


def scatter(x_column: str, y: dict, series: str, filters: list, x_label: str, y_label: str,
            x_format: str, y_format: str, x_bounds=(None, None), y_bounds=(None, None)) -> tuple[str, dict]:
    """One point per `series` value: `y` against the numeric column
    `x_column`, all points the same size (ECharts scatter, in both
    versions). Used instead of the bubble chart, which scales sizes from
    the smallest value to the largest and so shrinks the smallest to a dot."""
    return "echarts_timeseries_scatter", {
        "x_axis": x_column,
        "metrics": [y],
        "groupby": [series],
        "adhoc_filters": filters,
        "row_limit": 100,
        "markerSize": 16,
        "color_scheme": COLOR_SCHEME,
        "show_legend": True,
        "legendOrientation": "top",
        "rich_tooltip": False,
        "x_axis_title": x_label,
        "x_axis_title_margin": 30,
        "y_axis_title": y_label,
        "y_axis_title_margin": 50,
        "y_axis_title_position": "Left",
        "x_axis_time_format": "smart_date",
        "xAxisFormat": x_format,
        "y_axis_format": y_format,
        "truncateXAxis": True,
        "xAxisBounds": list(x_bounds),
        "truncateYAxis": True,
        "y_axis_bounds": list(y_bounds),
    }


def gauge(metric: dict, filters: list, number_format: str, max_value: float) -> tuple[str, dict]:
    """ECharts gauge (gauge_chart, in both versions): one value against a
    full scale from 0 to `max_value`."""
    return "gauge_chart", {
        "metric": metric,
        "adhoc_filters": filters,
        "groupby": [],
        "row_limit": 10,
        "min_val": 0,
        "max_val": max_value,
        "start_angle": 225,
        "end_angle": -45,
        "font_size": 18,
        "number_format": number_format,
        "show_pointer": True,
        "animation": True,
        "show_axis_line_ticks": False,
        "show_split_line": False,
        "split_number": 5,
        "show_progress": True,
        "overlap": True,
        "round_cap": True,
        "color_scheme": COLOR_SCHEME,
    }


def radar(group_column: str, metrics: list[dict], filters: list, number_format: str,
          axis_max: float) -> tuple[str, dict]:
    """ECharts radar (in both versions): one shape per `group_column` value,
    one axis per metric, every axis on the same 0..`axis_max` scale. No
    legend: Superset's radar leaves no room for one, so it covers the top or
    bottom axis label; name the shapes and their colours in the chart title."""
    return "radar", {
        "groupby": [group_column],
        "metrics": metrics,
        "adhoc_filters": filters,
        "row_limit": 10,
        "column_config": {m["label"]: {"radarMetricMaxValue": axis_max} for m in metrics},
        "is_circle_shape": False,
        "show_labels": False,
        "show_legend": False,
        "number_format": number_format,
        "color_scheme": COLOR_SCHEME,
    }
