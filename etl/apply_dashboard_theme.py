"""
Apply the project's dashboard theme to every Superset dashboard.

A light, lively theme: a soft blue-grey page, white rounded cards that fade
in on load and lift with a blue ring on hover, KPI tiles that each carry
their own colour bar and tint on hover, section titles with a blue accent
bar, clickable table rows that highlight in blue, and the table's in-cell
bars drawn in the project blue (#2a78d6) instead of grey.

Only the dashboard area is styled. Superset's own navigation, title bar
and filter bar are left as Superset draws them, so they stay readable in
both the public (embedded) view and the logged-in view. An earlier dark
version of this theme recoloured those parts and made the logged-in title
bar and KPI titles unreadable; it was replaced by this one.

Uses Superset's per-dashboard custom CSS (the dashboard's "css" field, the
same as Edit dashboard > Edit CSS), so nothing in Superset itself is
changed and the theme is removed by clearing that field. Safe to re-run;
the dashboard builder scripts do not send "css", so rebuilds keep it.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\apply_dashboard_theme.py
    .venv\\Scripts\\python.exe etl\\apply_dashboard_theme.py --remove
"""

import sys

from setup_superset_dashboard import SUPERSET_URL, get_session

# Executive Overview, Stories 1-5.
DASHBOARD_IDS = [5, 3, 4, 7, 6, 8]

ACCENT = "#2a78d6"
INK = "#1d2433"
MUTED = "#5f6b7d"
# KPI tile colour bars, in the order tiles sit in a row (windsor_housing palette).
KPI_COLOURS = ["#2a78d6", "#1baf7a", "#eb6834", "#4a3aa7"]

KPI_BARS = "\n".join(
    f""".grid-row > .dragdroppable-column:nth-child({i}) .dashboard-component-chart-holder:has(.big_number_total) {{
  --kpi: {colour};
}}"""
    for i, colour in enumerate(KPI_COLOURS, start=1)
)

THEME_CSS = f"""
/* Windsor Housing dashboard theme (etl/apply_dashboard_theme.py) */

/* Page: a soft blue-grey background so the white cards stand out */
.dashboard-content, .grid-container {{
  background: linear-gradient(180deg, #eef3fa 0%, #f6f8fc 60%, #ffffff 100%);
}}

/* Section titles: an accent bar and a short underline */
.dashboard-component-header .editable-title {{
  border-left: 4px solid {ACCENT};
  padding-left: 12px;
  font-weight: 700;
  color: {INK};
}}

/* Cards: rounded, fade in on load, lift with a blue ring on hover */
@keyframes windsor-card-in {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: none; }}
}}
.dashboard-component-chart-holder {{
  border-radius: 14px !important;
  border: 1px solid #e3e9f2;
  box-shadow: 0 2px 10px rgba(29, 36, 51, .06);
  animation: windsor-card-in .5s ease both;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}}
.dashboard-component-chart-holder:hover {{
  transform: translateY(-4px);
  border-color: {ACCENT};
  box-shadow: 0 14px 30px rgba(42, 120, 214, .18);
}}
.dashboard-component-chart-holder .header-title {{ transition: color .2s ease; }}
.dashboard-component-chart-holder:hover .header-title {{ color: {ACCENT}; }}

/* KPI tiles: a colour bar on top, a light tint and a bigger number on hover */
{KPI_BARS}
.dashboard-component-chart-holder:has(.big_number_total) {{
  border-top: 5px solid var(--kpi, {ACCENT}) !important;
  background: #ffffff;
}}
.dashboard-component-chart-holder:has(.big_number_total):hover {{
  background: linear-gradient(180deg, #ffffff 0%, #f3f8ff 100%);
  border-color: var(--kpi, {ACCENT});
}}
.dashboard-component-chart-holder:has(.big_number_total) .header-title .editable-title {{
  color: {MUTED};
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
}}
.big_number_total .header-line {{
  color: {INK} !important;
  transition: transform .2s ease, color .2s ease;
  transform-origin: left center;
}}
.dashboard-component-chart-holder:has(.big_number_total):hover .header-line {{
  transform: scale(1.05);
  color: var(--kpi, {ACCENT}) !important;
}}
.big_number_total .subheader-line {{ color: {MUTED} !important; }}

/* Tables: tinted header, blue in-cell bars, highlighted clickable rows */
.dashboard-component-chart-holder table thead th {{
  background: #f1f6fd !important;
  color: {INK};
  border-bottom: 2px solid {ACCENT} !important;
}}
.dashboard-component-chart-holder .cell-bar.positive {{
  background-color: rgba(42, 120, 214, .16) !important;
}}
.dashboard-component-chart-holder table tbody tr {{ transition: background-color .15s ease; }}
.dashboard-component-chart-holder table tbody tr:hover td {{
  background-color: #e6f0fc !important;
  cursor: pointer;
}}

/* The zone a user clicked (Superset marks it as the active cross-filter):
   a stronger blue with a left bar, so it stays visible when not hovered */
.dashboard-component-chart-holder table tbody td.dt-is-active-filter {{
  background-color: #cfe2fa !important;
  color: {INK};
  font-weight: 700;
  box-shadow: inset 4px 0 0 {ACCENT};
}}

/* Markdown cards (guides, data notes) */
.dashboard-markdown {{ border-radius: 14px; }}

@media (prefers-reduced-motion: reduce) {{
  .dashboard-component-chart-holder {{ animation: none; transition: none; }}
  .dashboard-component-chart-holder:hover,
  .dashboard-component-chart-holder:hover .header-line {{ transform: none; }}
}}
"""


def main(remove: bool) -> None:
    session, headers = get_session()
    css = "" if remove else THEME_CSS
    for dashboard_id in DASHBOARD_IDS:
        resp = session.put(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", headers=headers, json={"css": css})
        resp.raise_for_status()
        print(f"Dashboard {dashboard_id}: theme {'removed' if remove else 'applied'}.")


if __name__ == "__main__":
    main(remove="--remove" in sys.argv)
