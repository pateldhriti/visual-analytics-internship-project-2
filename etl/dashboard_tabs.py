"""
Split a dashboard's single long grid into tabs, so each tab fits one screen
without scrolling (supervisor feedback, Nov 2026: "a dashboard is something
you don't want to scroll").

Every dashboard builder still lays its sections out top to bottom as before;
add_tabs() then moves each top-level section (a header or a row) into the
tab it is listed under and fixes every component's `parents` path, which is
what Superset uses to know where a chart sits. The dashboard keeps its id,
so the website's embeds and links do not change.

    position = add_tabs(position, [
        ("TAB-overview", "Overview", ["HEADER-kpi", "ROW-kpi"]),
        ("TAB-trends", "Trends", ["ROW-trend"]),
    ])

A header that is not listed is removed (the tab title replaces it); any
other section left out is an error, so a chart cannot silently disappear.
"""

TABS_ID = "TABS-main"


def add_tabs(position: dict, tabs: list[tuple[str, str, list[str]]], tabs_id: str = TABS_ID) -> dict:
    grid = position["GRID_ID"]
    top_level = list(grid["children"])
    tab_of = {}
    for tab_id, _, members in tabs:
        for member in members:
            if member not in top_level:
                raise ValueError(f"{member} is not a top-level section of this dashboard")
            if member in tab_of:
                raise ValueError(f"{member} is listed in two tabs")
            tab_of[member] = tab_id

    missing = [m for m in top_level if m not in tab_of and position[m]["type"] != "HEADER"]
    if missing:
        raise ValueError(f"Not placed in any tab: {missing}")
    for header in (m for m in top_level if m not in tab_of):
        del position[header]

    for node_id, node in position.items():
        parents = node.get("parents") if isinstance(node, dict) else None
        if not parents or parents[:2] != ["ROOT_ID", "GRID_ID"]:
            continue
        top = parents[2] if len(parents) > 2 else node_id
        node["parents"] = ["ROOT_ID", "GRID_ID", tabs_id, tab_of[top], *parents[2:]]

    for tab_id, title, members in tabs:
        position[tab_id] = {
            "type": "TAB",
            "id": tab_id,
            "children": list(members),
            "parents": ["ROOT_ID", "GRID_ID", tabs_id],
            "meta": {"text": title, "defaultText": "Tab title", "placeholder": "Tab title"},
        }
    position[tabs_id] = {
        "type": "TABS",
        "id": tabs_id,
        "children": [tab_id for tab_id, _, _ in tabs],
        "parents": ["ROOT_ID", "GRID_ID"],
        "meta": {},
    }
    grid["children"] = [tabs_id]
    return position
