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


def finish_dashboard(session, headers, dashboard_id: int) -> dict:
    """Fill in what a dashboard's builder did not set, without changing what
    it did: a colour for every series, a cross-filter entry for every ECharts
    chart, and the colour scheme for this Superset. Returns what was added."""
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
    session.put(
        f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}",
        headers=headers,
        json={"json_metadata": json.dumps(metadata)},
    ).raise_for_status()
    return {"colors_added": new_colors, "cross_filter_entries_added": sorted(int(k) for k in new_config)}
