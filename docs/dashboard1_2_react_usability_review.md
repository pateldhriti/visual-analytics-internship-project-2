# Dashboards 1 & 2 -- Usability Review for React Integration

Reviews whether Dashboard 1 (**01 - Windsor Housing Executive Overview**, Superset id 5) and
Dashboard 2 (**Story 1: Who faces the greatest affordability pressure?**, id 3) will work once
embedded in, or linked from, the React frontend. Every figure below was checked against the live
Superset instance (`position_json`, chart params and anonymous `/api/v1/chart/data` requests), not
estimated from the build scripts alone.

## How the frontend embeds a dashboard today

- `web/src/components/SupersetEmbed.jsx` renders a plain iframe of
  `/superset/dashboard/<id>/?standalone=2` as the anonymous Public role (no guest token -- see
  `docs/superset_embedding_research.md`, Option A). `standalone=2` hides Superset's navbar and the
  dashboard title row; the native filter bar stays.
- Only Dashboard 2 is embedded so far (`StoryAffordability.jsx`, `dashboardId={3}`), at the
  component's default `height = 1400` px.
- The iframe sits in `.story-dashboard-band` (max-width 1480px, 24px side padding) to the right of
  the 268px fixed sidebar. On a 1440px-wide laptop that leaves about **1,124px** for the iframe;
  Superset's expanded vertical filter bar takes roughly 260px of that, so the 12-column chart grid
  gets about 860px.

## Findings

| # | Dashboard | Finding | Severity | Status |
|---|---|---|---|---|
| 1 | 2 | Severity-breakdown chart (chart 32) blank for every public visitor | **High** | Fixed |
| 2 | 1 | Rent change in the Oct-24 vs Oct-25 table labelled "units" | Medium | Fixed |
| 3 | 2 | Dashboard is ~2,900px tall inside a 1,400px iframe (nested scroll) | Medium | Recommendation |
| 4 | 1 | KPI tiles beside the tenure bar chart leave ~240px of empty space | Low | Recommendation |
| 5 | 1, 2 | Grid does not reflow below ~860px -- unusable on phones | Medium | Recommendation |
| 6 | 1 | Benchmark table shows raw metric keys (`pct_change_rent`) | Low | Recommendation |
| 7 | 1 vs 3 | Same KPI names show different numbers (Apartment vs Combined scope) | Low | Recommendation |

### 1. Severity-breakdown chart blocked for anonymous viewers (fixed)

Chart 32, "Severity Breakdown of Burdened Households by Tenure", was added to Dashboard 2 after
`docker/superset_config.py`'s `PUBLIC_DATASOURCE_NAMES` list was written, and its dataset
(`v_story1_burden_severity_breakdown`, id 18) was never granted to the Public role. An anonymous
request for that chart's data returned **404** while chart 2 on the same dashboard returned 200 --
so the React Story 1 page has been showing an error tile in place of this chart.

Fix: dataset 18 added to `PUBLIC_DATASOURCE_NAMES` (Superset restart required, since the grant
runs in `FLASK_APP_MUTATOR` at startup). Re-checked after restart: every chart on Dashboards 1, 2
and 3 now returns 200 for an anonymous request.

### 2. Rent change labelled "units" (fixed)

`v_dashboard1_rental_yoy.change_unit` returned `units` for both `universe` (rental stock) and
`average_rent`, so the table read "+65 units" for a $65 rent increase -- easy to misread as 65 new
rental units. `sql/dashboard1_views.sql` now returns `dollars` for `average_rent`.

### 3. Dashboard 2 is about twice as tall as its iframe

Dashboard 2's grid rows add up to 300 grid units (KPI row 25, four chart rows of 55, the severity
KPI row 25 and the validation note 30). At Superset's 8px grid unit that is 2,400px of charts,
plus 5 section headers and row gutters -- roughly **2,900px** in total. The iframe is 1,400px, so a
visitor scrolls the page, then has to scroll *inside* the iframe to reach the severity and
validation sections. Scroll-inside-scroll is easy to miss on a trackpad and the lower half of the
dashboard is likely never seen.

Recommendation: pass an explicit `height` to `SupersetEmbed` for each dashboard (about 3,000 for
Dashboard 2) rather than relying on the 1,400 default. A cross-origin iframe can't report its own
content height back to the page without the Embedded SDK, so this has to be set per dashboard and
updated if the layout changes. Dashboard 1 (215 grid units plus 4 headers) would need about 2,200.
These are computed from `position_json`, so confirm them in a browser before relying on them.

### 4. Empty space beside Dashboard 1's affordability KPIs

`ROW-affordability` puts the tenure bar chart (height 55) next to the Renter and Owner Burden Rate
tiles (height 25 each). Superset sizes a row to its tallest child, so both tiles sit at the top of
a 440px row with about 240px of blank space under them. Stacking the two tiles vertically in a
`COLUMN` container next to the bar chart would fill that space. Not changed here, because it means
restructuring how `build_dashboard1_overview.py` builds that row.

### 5. No layout for narrow screens

Superset 3.1's dashboard grid scales columns proportionally and never stacks them. Below the
frontend's own 860px breakpoint (where the sidebar collapses to a top bar), a 3-wide KPI tile is
under 100px wide on a phone and bar-chart axis labels overlap. Recommendation: below 860px, show
the story page's own KPI cards plus the existing "Open full dashboard" link instead of the iframe,
rather than trying to make the Superset grid responsive.

### 6. Raw metric keys in the CMA benchmark table

The `metric` column of "Windsor vs CMA Benchmark" shows `average_rent`, `pct_change_rent`,
`turnover_rate` and `vacancy_rate` as-is. Fine for the team; unclear for a public visitor. A
`metric_label` column in `v_dashboard1_cma_benchmark` (for example "Average 2-bedroom rent") would
fix it without changing the chart.

### 7. Same KPI name, different number

Dashboard 1's rental tiles are Apartment scope (rent $1,287, vacancy 3.7%), while Dashboard 3's
are Combined scope (rent $1,293, vacancy 3.6%). Both are correct and both chart titles say which
scope they use, but a visitor moving between the two pages will see two different "Windsor average
rent" figures. The React pages should name the scope wherever these numbers are quoted.

## What already works well

- **Titles**: every chart title names its measure and, where relevant, its period (for example
  "Burden Rate by Income Band"). With `standalone=2` hiding the dashboard title, the React page's
  own heading is the only title shown -- no duplicate.
- **Sections**: both dashboards use section headers (Dashboard 1: 4, Dashboard 2: 5) that line up
  with the story page's own structure.
- **Filters**: Dashboard 2's Tenure and Household Type filters are correctly scoped (KPI tiles
  with a hardcoded tenure are excluded, per `docs/filter_standards.md`). Dashboard 1 has no
  filters, by design (see `build_native_filters()` in `etl/build_dashboard1_overview.py`).
- **Percentages**: all rate charts and KPI tiles on both dashboards render with a "%" sign after
  `etl/polish_percentage_kpi_formatting.py`.
- **Tables**: both Dashboard 1 tables are now 40 grid units tall instead of 55, so a 4-row table
  no longer leaves a large blank area underneath (part of the Dashboard 3 cross-dashboard polish
  pass, `docs/dashboards_1_3_polish_review.md`).
