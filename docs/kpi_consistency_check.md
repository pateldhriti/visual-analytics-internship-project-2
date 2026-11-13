# KPI Consistency Check

**Date:** 6 November 2026
**Question:** does each KPI show the same number everywhere it appears, on the six Superset dashboards and the React site?

**Method:** every big-number card on every dashboard was read in a browser as an anonymous visitor (the values a visitor actually sees), and every KPI on the React pages was compared against the warehouse view behind it.

## Rule

A KPI with the same name must show the same number. Where two figures legitimately differ because they measure different things, the label must say which is which:

- **Windsor's own figures** (Story 2, Dashboard 1, Home): purpose-built **apartments and row houses**, all unit sizes, Windsor CMA.
- **Comparison with other cities** (Story 4, and Story 5's city comparison): **apartments only**, because CMHC publishes the city comparison for apartments only; rent is for **2-bedroom** units, the size CMHC compares cities on.

## Findings and fixes

| KPI | Where | Before | After | Fix |
|---|---|---|---|---|
| Windsor average rent | Story 2 card | $1,293 (apartments + row houses) | $1,293 | — (reference) |
| | Executive Overview card | **$1,287** (apartments only) | **$1,293** | `v_dashboard1_rental_yoy` now uses apartments + row houses for all four metrics; card renamed from "(Apartment)" |
| Windsor vacancy rate | Story 2 card | 3.6% | 3.6% | — (reference) |
| | Executive Overview card | **3.7%** (apartments only) | **3.6%** | same view fix |
| | Story 4 card | 3.7% (apartments only) | 3.7% | kept: city comparison is apartments only; caption now says "apartments only" |
| Rental stock / turnover | Story 2, Executive Overview | 19,883 / 11.9% | 19,883 / 11.9% | — (already consistent) |
| 2-bedroom rent | Story 4 card, Story 5 | $1,454 (apartments) | $1,454 | caption now says "2-bedroom apartments" |
| | Home page card | $1,451 (apartments + row houses), caption "Windsor CMA" | $1,451 | caption now says "apartments + row houses" |
| Housing starts | Story 3 dashboard | 1,262 (Windsor, 2025) | 1,262 | — (reference) |
| | Story 3 React page cards | **17,786 / 14,083 / 162,138 (Ontario, Q2 2026)** | **1,262 / 1,671 / 1,635 (Windsor, 2025)** | page cards now match the Windsor dashboard embedded below them |
| | Home page card and supply panel | **17,786 (Ontario)**, caption "no Windsor-specific figure yet" | **1,262 (Windsor, 2025)** | the Windsor figure exists (StatCan 34-10-0154-01) |
| Burden rates | Story 1, Executive Overview, Story 1 page, Home | 34.8% / 10.9% | 34.8% / 10.9% | — (same chart objects) |

## Other defects found during the check

- **Missing captions:** the Executive Overview and Story 4 cards set `subtitle`, which Superset 3.1's big-number chart ignores (it reads `subheader`), so they showed no scope or date. Fixed in `etl/build_dashboard1_overview.py` and `etl/build_story4_dashboard.py`.
- **Metadata overwrite:** both builders replaced the dashboard's stored metadata on every run. With clickable (ECharts/table) charts that makes Superset's frontend try to re-save, which fails for anonymous viewers and sends them to the login page. Both now merge into the stored metadata, as `build_story2_dashboard.py` already does.

## How to re-check

Open each dashboard at `http://localhost:8088/superset/dashboard/<id>/?standalone=2` (5, 3, 4, 7, 6, 8) and compare the cards with this table, or query the views named in the cards' descriptions.

## Re-check, 13 November 2026

Since the first check, several KPI cards were added: trendline tiles on the Overview, Story 2 and Story 4, Story 3's yearly cards, Story 5's overview cards, and the ten-year rents. Every big-number card on every tab of the six dashboards was read again as an anonymous visitor (30 cards), and the React pages were compared with `web/src/data/figures.json`, which the pages now read their figures from.

| KPI | Where | Shows | Verdict |
|---|---|---|---|
| Renter / owner burden rate | Overview, Story 1 | 34.8% / 10.9% | Consistent (same chart objects) |
| Households spending 30%+ | Story 1 | 28,740 | Consistent: the sum of owners and renters, labelled so; the overall count is 28,745 (StatCan rounding, explained on the page) |
| Windsor average rent, vacancy, stock, turnover | Overview, Story 2 | $1,293, 3.6%, 19,883, 11.9% (rent +35.7% since Oct-20 on both) | Consistent |
| Windsor 2-bedroom rent | Story 4 card | $1,454 (2-bedroom apartments, Oct-25) | Consistent with Story 5's city comparison and the Story 4 page |
| Windsor 2-bedroom rent, 2015 to 2025 | Story 4 card, Story 4 page, Story 1 and 5 pages | **$1,451** (apartments **and row houses**) | **Fixed.** Shown beside the $1,454 card with no scope, it read as a different number for the same thing. The card's caption now says "since 2015 · apartments + row houses", and so do the Story 4 page's card and unit-scope label |
| Windsor apartment vacancy | Story 4 | 3.7% (apartments only) | Consistent; differs from Story 2's 3.6% by scope, as labelled |
| Homes started / completed / under construction | Story 3, Story 3 page | 1,262 / 1,671 / 1,635 (2025) | Consistent |
| Starts per 1,000 households | Story 3 (7.6, selected year 2025), Story 5 (8.4, yearly average since 2016) | — | Consistent: different measures, each labelled with its period |
| Renters who cannot afford a 2-bedroom, rent share of income, homes completed 2023-2025 | Story 5, Story 1 and 5 pages | 61%, 36%, 5,247 | Consistent |

The Methodology page's note on apartments and row houses now also covers Story 4's ten-year figures.
