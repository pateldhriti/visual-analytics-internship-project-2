# Dashboards 1-3 -- Cross-Dashboard Polish & Responsive Review

Side-by-side review of Dashboard 1 (**01 - Windsor Housing Executive Overview**, Superset id 5),
Dashboard 2 (**Story 1**, id 3) and Dashboard 3 (**Story 2: What is happening in Windsor's rental
market?**, id 4) for consistent structure, readable widths, legend behaviour and readiness for
React embedding. Each check below was made against the live dashboards' `position_json` and chart
params, not the build scripts alone. Fixes were applied through the idempotent builders
(`etl/build_story2_dashboard.py`, `etl/build_dashboard1_overview.py`), so re-running them keeps
these changes.

## Summary

| Check | Dashboard 1 | Dashboard 2 | Dashboard 3 (before) | Dashboard 3 (after) |
|---|---|---|---|---|
| Section headers | 4 | 5 | **none** | 4 |
| Rates shown with "%" | yes | yes | **4 charts bare** (e.g. "4.6") | yes |
| Filter names in Title Case | no filters | yes | **"Bedroom type"** | "Bedroom Type" |
| Rental KPI order | Rent, Vacancy, Stock, Turnover | -- | **Vacancy, Rent, Turnover, Stock** | Rent, Vacancy, Stock, Turnover |
| Dense charts in half-width cells | no | no | **2** (24 bars each) | none |
| Table height fits its rows | **no** (55 for 4 rows) | no tables | -- | yes (40 for 7 rows) |
| Legend only on multi-series charts | yes | yes | yes | yes |
| Every chart loads for anonymous viewers | yes | **no** (chart 32, now fixed) | yes | yes |

## Fixed in this pass

**Dashboard 3 had no section headers.** It was the only one of the four story/overview dashboards
without them, so its 13 charts read as one long list. It now has 4: "Windsor CMA at a Glance
(Oct-25)", "Zone-Level Rental Market", "Rent and Vacancy Trends (Oct-20 to Oct-25)" and "Turnover
and Dwelling Type".

**Rates without a "%" sign.** The Vacancy and Turnover KPI tiles (charts 8, 26), "Vacancy Rate by
Period and Bedroom Type" (12) and "Turnover Rate by Bedroom Type" (13) used `y_axis_format: ".1f"`
on columns already stored as percentages, so they rendered "3.6" and "11.9" -- the same issue
`etl/polish_percentage_kpi_formatting.py` fixed on Dashboards 1 and 2. They now divide by 100 and
use `.1%`, like every other rate on the three dashboards. Verified: the tiles now return 0.036 and
0.119, rendered as 3.6% and 11.9%.

**"Bedroom type" filter renamed to "Bedroom Type"** -- the follow-up `docs/filter_standards.md`
left open for this dashboard.

**KPI order matches Dashboard 1.** Dashboard 3's tiles now run Rent, Vacancy, Stock, Turnover, the
same order as Dashboard 1's "Windsor Rental Market" row, so the four headline rental numbers read
in the same order on both pages.

**Trend charts moved to full width.** "Average Rent by Period and Bedroom Type" and "Vacancy Rate by
Period and Bedroom Type" each draw 4 bedroom types x 6 periods = 24 bars and sat side by side at
width 6. In the React iframe (about 860px of chart grid on a 1440px screen once Superset's filter
bar is open) that is roughly 430px per chart -- under 15px per bar. Each now has its own
full-width row.

**Zone axis labels angled.** Zone names run up to 27 characters ("Zone 6 - North Essex County").
The three zone-axis bar charts now use `x_ticks_layout: "45°"` with an automatic bottom margin, so
labels don't overlap in half-width cells.

**Dashboard 1 tables shortened.** "Rental Market Oct-24 vs Oct-25" and "Windsor vs CMA Benchmark"
each have 4 rows but were 55 grid units (440px) tall, the bar-chart height, leaving a large blank
area under the last row. Both are now 40, matching Dashboard 3's zone snapshot table.

## Checked and already consistent

- **Legends**: shown on every multi-series chart (series = bedroom type, dwelling type, tenure or
  zone) and hidden on every single-series one -- no single-series chart carries a one-item legend.
- **Colour**: all three dashboards use the `windsor_housing` scheme, so a series keeps its colour
  across charts. Dashboard 3's zone trend chart uses 7 of the palette's 8 slots, so all 7 zones get
  distinct colours without cycling.
- **KPI tile height**: 25 grid units on all three dashboards.
- **Full-width rows for single charts**: every row with one chart uses width 12.

## Left as follow-ups

- **KPI subtitles differ in wording**: Dashboard 1 uses "Latest CMHC survey -- Oct-25", Dashboard
  3 uses "October 2025, Combined dwelling types". Both are accurate. Pick one style when the KPI
  catalogue (`docs/kpi_catalogue.md`) gets its planned refresh.
- **Dashboard titles follow two patterns**: "01 - Windsor Housing Executive Overview" versus
  "Story N: <question>". Only visible inside Superset (the React embed hides the title row), so
  low priority.
- **Dashboard 1's affordability row**: two KPI tiles beside a taller bar chart leave empty space
  under the tiles. Fixing it means stacking the tiles in a `COLUMN` container -- a layout change to
  `build_dashboard1_overview.py` beyond a polish pass.
- **Narrow screens**: Superset's grid never stacks columns. Below about 860px every dashboard
  becomes hard to read whatever its layout, so the React side needs to handle small screens
  differently (for example the story page's own KPI cards plus an "Open full dashboard" link).
