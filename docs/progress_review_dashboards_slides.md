# Progress Review — Dashboards Section

**Presenter:** Pavan Rella
**Covers:** the KPI catalogue and the 4 real story dashboards built on top of it. One slide per `##`
heading below -- paste each section as its own slide. All figures are real, pulled directly from
live Superset and this repo's own docs (`docs/kpi_catalogue.md`), not estimated for this review.

## Slide 1: What's live right now

4 real dashboards, 33 charts total, built on 18 registered Superset datasets:

| Dashboard | Charts | Covers |
|---|---|---|
| Story 1 -- Affordability | 9 | Burden by tenure, income band, household type, severity breakdown |
| Story 2 -- Rental Market | 9 | Rent/vacancy/turnover trends, by zone, bedroom type, dwelling scope |
| 01 - Executive Overview | 11 | Cross-story summary: affordability, rental, supply, CMA benchmark |
| Story 4 -- Comparison | 6 | Windsor vs. 4 real comparator CMAs on vacancy, rent, rent growth |

(A 5th, "Embedding Spike Test Dashboard," is a leftover 1-chart proof-of-concept from the embedding
research spike -- not a real story dashboard, not counted above.)

## Slide 2: The KPI catalogue

`docs/kpi_catalogue.md` documents **19 KPIs** across all 4 stories, each with its real formula, the
exact table/columns it's computed from, and a caveat section for every KPI with a known data gap --
e.g. KPI 1/2's denominator-bug history (`docs/story1_validation.md`), or Story 3's KPIs reporting
Ontario/Canada scope because no Windsor-specific starts/completions figure exists in CMHC's source.

**Known gap, flagged honestly for this review**: the catalogue predates several things now live --
Dashboard 1's Rental Stock/Turnover KPI tiles, Dashboard 2's severity-breakdown chart, and the whole
Story 4 dashboard. It documents the KPI *definitions* correctly, but its own chart inventory is
stale relative to what's actually built. Worth a refresh pass, not urgent -- the formulas it
documents are still the real ones every dashboard uses.

## Slide 3: Story 1 -- Affordability

9 charts: 3 headline KPI tiles (Renter/Owner Burden Rate, Households Spending 30%+), burden by
income band and household type, a severity breakdown (now a real stacked chart, not just 2 separate
numbers -- see `docs/filter_standards.md`'s worked example), and a Census-validation note
cross-checking this project's own numbers against StatCan's independently published rate.

## Slide 4: Story 2 -- Rental Market

9 charts: a 4-tile KPI row (Average Rent, Vacancy, Turnover, Rental Stock), rent by zone and bedroom
type, rent/vacancy trends across the real 6-year span (Oct-20 to Oct-25), turnover by bedroom type,
and a vacancy-by-dwelling-type comparison backing the new Dwelling Scope filter.

## Slide 5: Executive Overview and Story 4

**01 - Executive Overview** (11 charts) pulls one headline view from each story into a single page:
affordability KPIs, rental KPIs, a housing-supply snapshot, and a Windsor-vs-CMA benchmark table --
built by reproducing a teammate's reference dashboard against this project's own real data, catching
2 real discrepancies along the way (an inflated supply figure from double-counted period scopes, and
a "42 CMAs" ranking claim this project's real extraction can't support -- it only covers 5).

**Story 4 -- Comparison** (6 charts) is the newest: 3 Windsor KPI tiles plus bar-chart comparisons
against the 4 real comparator CMAs on vacancy, rent, and the real rent-growth half of the
affordability-gap index. The index itself isn't shown as one number -- the renter-income-growth side
is `NULL` everywhere in this project's data (`docs/affordability_gap_index.md`), so a markdown note
explains the gap instead of a fabricated figure.

## Slide 6: Filter standards, applied

`docs/filter_standards.md` writes down the naming/placement/default/scope rules this project had
already converged on through 3 separate real bug fixes, and fixes the one naming inconsistency
Story 1 actually had ("Household type" -> "Household Type"). The core rule, worth saying out loud in
this review: **never scope a filter to a chart that already hardcodes the same column** -- the exact
bug class that silently zeroed out KPI tiles twice before it was written down as a standard.

## Slide 7: Next steps

- Refresh `docs/kpi_catalogue.md`'s chart inventory to match what's actually live (flagged above,
  not urgent).
- Apply `docs/filter_standards.md`'s naming fix to Dashboard 3's "Bedroom type" filter (left as a
  follow-up, out of this task's scope).
- Re-verify `docs/superset_hosting_tuning.md`'s settings against a real hosted instance once Render
  setup happens (~Week 9) -- today's work is dev-environment tuning that will carry over, not a
  report that a hosted VM has been tested.
