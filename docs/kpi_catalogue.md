# KPI Catalogue

19 KPIs across the project's 4 stories. Every formula and figure below is verified against the live
`warehouse` schema (queried directly, not estimated) or an existing project doc, not invented for
this catalogue. Two KPIs are deliberately included as **not computable with real data right now**
(`NULL`, not a fabricated placeholder) -- see Story 3 KPI 15 and Story 4 KPI 19 -- because an honest
gap is more useful to the team than a chart that looks real but measures nothing real.

---

## Story 1 -- Affordability (`warehouse.fact_shelter_cost`)

### 1. Shelter-cost burden rate by tenure
- **Definition:** share of households spending 30%+ of income on shelter costs, split Owner vs Renter.
- **Formula:** `value[ratio='Spending 30% or more...'] / value[ratio='Total - Shelter-cost-to-income ratio'] * 100`, per `tenure`.
- **Source table:** `fact_shelter_cost`
- **Unit:** %
- **Verified:** Owner 10.9% (13,005/118,940), Renter 34.8% (15,735/45,280) -- denominator excludes "Not applicable" households (zero/negative income or an agricultural-operation dwelling), matching StatCan's own published rate exactly (see `docs/story1_validation.md`). An earlier version of this line used the raw, unfiltered Total as the denominator and read Renter 34.5% (15,735/45,605) -- wrong, corrected here.
- **Caveat:** must filter to the baseline slice (`housing_suitability`/`dwelling_condition` = Total, `statistic` = "Number of private households") first -- skipping it makes each combination appear 27x, not once.

### 2. Burden rate by income bracket
- **Definition:** same burden share as KPI 1, broken out by household income bracket instead of tenure.
- **Formula:** same as KPI 1, grouped by `income_group`, `tenure = 'Total'`.
- **Source table:** `fact_shelter_cost`
- **Unit:** %
- **Verified (top 3):** Under $10,000: 93.1%; $10,000-$19,999: 76.5%; $20,000-$29,999: 56.2%.
- **Caveat:** `income_group` has 2 non-count rows (Median/Average $ statistics) -- exclude both or the ranking breaks. Also exclude "Not applicable" households from the denominator (same fix as KPI 1) -- an earlier version of this line used the unfiltered denominator and read Under $10,000: 73.6%, ranked *second* behind $10,000-$19,999's 76.4% -- wrong on both the value and the ranking. Corrected: Under $10,000 is clearly the most burdened bracket, not a close second.

### 3. Severity within the burdened group
- **Definition:** of households already spending 30%+, how much is in the most extreme published sub-band.
- **Formula:** `value[ratio='30% to less than 100%'] / value[ratio='Spending 30% or more...']`
- **Source table:** `fact_shelter_cost`
- **Unit:** % (and a residual household count)
- **Verified:** 26,210 of 28,745 (91.2%) in the 30-<100% band; 2,535 households (8.8%) unaccounted for.
- **Caveat:** the 8.8% residual isn't explained by any published StatCan sub-category -- don't assume it means "100%+ spenders" without a source for that label (see `docs/shelter_cost_audit.md`).

### 4. Burden rate by household type
- **Definition:** same burden share as KPI 1, broken out by household type.
- **Formula:** same as KPI 1, grouped by `(household_type, household_type_member_id)`, `tenure = 'Total'`.
- **Source table:** `fact_shelter_cost`
- **Unit:** %
- **Verified (top 3):** non-census-family one-person households 32.9%; non-census-family households overall 31.1%; one-parent families (no additional persons) 23.3% -- all above the Windsor-wide baseline of 17.5%. (An earlier version of this line used the unfiltered "Not applicable"-inclusive denominator -- same fix as KPI 1 -- and read 32.7%/30.9%/23.2%/17.4%; corrected here.)
- **Caveat:** `household_type` has 16 real categories but only 14 distinct text labels (2 label collisions) -- group by `household_type_member_id`, never the text label alone.

### 5. Households outside the ratio calculation
- **Definition:** share of households the shelter-cost-to-income ratio simply doesn't apply to.
- **Formula:** `value[ratio='Not applicable'] / value[ratio='Total']  * 100`
- **Source table:** `fact_shelter_cost`
- **Unit:** %
- **Verified:** 510 / 164,730 = 0.31%.
- **Caveat:** covers households on an agricultural operation or with zero/negative income -- small enough in Windsor to mention in passing, not a standalone headline KPI.

---

## Story 2 -- Rental Market (`warehouse.fact_rental_market`, Windsor CMA, Combined dwelling type)

### 6. Apartment+Row vacancy rate
- **Definition:** share of purpose-built rental units vacant, Windsor CMA, all dwelling types combined.
- **Formula:** `value WHERE metric_type='vacancy_rate' AND dwelling_type='Combined' AND bedroom_type='Total'`
- **Source table:** `fact_rental_market`
- **Unit:** %
- **Verified:** 3.6% (Oct-25, reliability letter `b` = Very Good).
- **Caveat:** this is the Combined (apartment + row) figure -- Table 1.0's Apartment-only national comparison table reports 3.7% for the same period (see Story 4 KPI 16). Different dwelling-type scope, not a data error.

### 7. Average 2-bedroom rent
- **Definition:** average monthly rent for a 2-bedroom unit, Windsor CMA, Combined dwelling types.
- **Formula:** `value WHERE metric_type='average_rent' AND dwelling_type='Combined' AND bedroom_type='2 Bedroom'`
- **Source table:** `fact_rental_market`
- **Unit:** $ CAD / month
- **Verified:** $1,451 (Oct-25, reliability letter `a` = Excellent).
- **Caveat:** reliability letter should be checked per cell on any new period/zone pulled in later -- `a` here isn't guaranteed for every combination.

### 8. Rental universe (stock size)
- **Definition:** total count of purpose-built rental units in the surveyed stock.
- **Formula:** `value WHERE metric_type='universe' AND dwelling_type='Combined' AND bedroom_type='Total'`
- **Source table:** `fact_rental_market`
- **Unit:** unit count
- **Verified:** 19,883 units (Oct-25).
- **Caveat:** universe/stock-count tables carry no reliability letter at all in this source (raw counts, not survey-estimated rates) -- a `NULL` reliability letter here is structural, not a missing-data gap.

### 9. Turnover rate
- **Definition:** share of occupied units that changed tenants over the past year.
- **Formula:** `value WHERE metric_type='turnover_rate' AND dwelling_type='Combined' AND bedroom_type='Total'`
- **Source table:** `fact_rental_market`
- **Unit:** %
- **Verified:** 11.9% (Oct-25, reliability letter `a`).
- **Caveat:** only extracted at the zone/Windsor-CMA level for Combined dwelling type -- the year-of-construction and structure-size turnover cuts (Tables 1.2.3/1.3.4) aren't extracted (see `docs/cmhc_rms_sheet_catalogue.md`).

### 10. Rent premium: vacant vs. occupied units
- **Definition:** gap between what's being asked for currently-vacant units and what occupied tenants are actually paying -- a market-tightness signal.
- **Formula:** `value[metric='rent_vacant_units'] - value[metric='rent_occupied_units']`
- **Source table:** `fact_rental_market` (Table 3.1.9)
- **Unit:** $ CAD / month
- **Verified:** $1,419 (vacant) vs $1,288 (occupied) = $131 premium, Windsor CMA, Oct-25, Combined, Total bedroom.
- **Caveat:** Table 3.1.9 also publishes a statistical-significance flag for this gap -- check it before treating the $ difference as a real signal rather than sampling noise.

---

## Story 3 -- Housing Supply (`warehouse.fact_starts_completions`)

### 11. Housing starts
- **Definition:** new housing units that began construction in the period.
- **Formula:** `units WHERE activity='Starts' AND dwelling_type='Total'`
- **Source table:** `fact_starts_completions`
- **Unit:** unit count
- **Verified:** 17,786 (Ontario, Second Quarter 2026).
- **Caveat:** **Ontario/Canada only** -- no Windsor-specific starts figure exists anywhere in this project's data yet (see `docs/story3_narrative_v1.md`'s "Data gaps" section).

### 12. Completions-to-starts ratio
- **Definition:** how completions in the period compare to starts in the same period.
- **Formula:** `units[activity='Completions', dwelling_type='Total'] / units[activity='Starts', dwelling_type='Total']`
- **Source table:** `fact_starts_completions`
- **Unit:** ratio (unitless)
- **Verified:** 14,083 / 17,786 = 0.79 (Ontario, Second Quarter 2026).
- **Caveat:** completions lag starts by a construction project's length -- a quarter with more starts than completions reflects a filling pipeline, not necessarily a slowdown. Don't over-interpret one quarter as a trend.

### 13. Construction pipeline backlog
- **Definition:** units currently under construction, expressed as a multiple of the quarter's own completions -- how much is "in the pipe" relative to current throughput.
- **Formula:** `units[activity='Under Construction', dwelling_type='Total'] / units[activity='Completions', dwelling_type='Total']`
- **Source table:** `fact_starts_completions`
- **Unit:** multiple of quarterly completions
- **Verified:** 162,138 / 14,083 = 11.5x (Ontario, Second Quarter 2026).
- **Caveat:** only one quarter of data exists -- this is a snapshot ratio, not a trend; "is the backlog growing" can't be answered until more quarters are extracted.

### 14. Apartment share of new starts
- **Definition:** what fraction of new housing starts are apartments vs. other dwelling types.
- **Formula:** `units[activity='Starts', dwelling_type='Apartment and Other'] / units[activity='Starts', dwelling_type='Total']`
- **Source table:** `fact_starts_completions`
- **Unit:** %
- **Verified:** 12,547 / 17,786 = 70.6% (Ontario, Second Quarter 2026).
- **Caveat:** same Ontario/Canada-only geography limit as KPI 11 -- can't say what Windsor's own dwelling-type mix looks like from this source.

### 15. Supply per 1,000 households -- NOT COMPUTABLE
- **Definition:** new housing starts relative to existing household count, the standard way to judge if supply is keeping pace.
- **Formula:** `starts / (households_total / 1000)` -- **left `NULL`, not computed.**
- **Source table:** `warehouse.v_story3_supply_per_1000_households` (view; joins `fact_starts_completions` and `fact_census_profile`)
- **Unit:** units per 1,000 households
- **Caveat (why `NULL`, not estimated):** the only households count in this project (`fact_census_profile`, characteristic 50: 165,665 households) is **Windsor-CMA-specific**, while `fact_starts_completions` is **Ontario/Canada-only** -- no shared geography exists to divide one into the other. Dividing them anyway would produce a number that looks like a real supply rate but measures nothing real. Closing this gap needs a CMA-level CMHC starts table (see `sql/story3_views.sql`'s own comment).

---

## Story 4 -- Comparison (`warehouse.fact_rental_market`, comparator CMA rows, Apartment scope)

Windsor CMA + 4 comparator CMAs (London, Kitchener-Cambridge-Waterloo, Hamilton, St. Catharines-Niagara -- selection justified in `docs/comparator_cmas_justification.md`). All 5 markets reported at the same scope here -- Apartment only, Oct-25 -- for an apples-to-apples comparison (Table 1.0's national scope, not Windsor's richer Combined data).

### 16. Vacancy rate vs. comparator CMAs
- **Definition:** Windsor's apartment vacancy rate against 4 size-comparable Ontario CMAs.
- **Formula:** `value WHERE metric_type='vacancy_rate' AND dwelling_type='Apartment' AND bedroom_type='Total'`, grouped by market.
- **Source table:** `fact_rental_market`
- **Unit:** %
- **Verified (Oct-25):** Windsor 3.7%, Hamilton 3.6%, St. Catharines-Niagara 3.9%, London 4.0%, Kitchener-Cambridge-Waterloo 4.1% -- Windsor has the 2nd-tightest market of the 5.
- **Caveat:** this is the Apartment-only scope (Table 1.0) -- Windsor's own Combined-dwelling-type figure is 3.6% (KPI 6), a different, non-comparable scope, not a contradiction.

### 17. Average 2BR rent vs. comparator CMAs
- **Definition:** Windsor's average 2-bedroom apartment rent against the same 4 CMAs.
- **Formula:** `value WHERE metric_type='average_rent' AND dwelling_type='Apartment' AND bedroom_type='2 Bedroom'`, grouped by market.
- **Source table:** `fact_rental_market`
- **Unit:** $ CAD / month
- **Verified (Oct-25):** Windsor $1,454 (cheapest of the 5), St. Catharines-Niagara $1,527, London $1,651, Hamilton $1,656, Kitchener-Cambridge-Waterloo $1,832 (most expensive).
- **Caveat:** same Apartment-only scope note as KPI 16 -- don't mix with Windsor's Combined-dwelling-type rent figures from Story 2.

### 18. Year-over-year rent growth vs. comparator CMAs
- **Definition:** Oct-24-to-25 rent growth, Windsor vs. the 4 comparators.
- **Formula:** `value WHERE metric_type='pct_change_rent' AND dwelling_type='Apartment' AND bedroom_type='2 Bedroom' AND period_label='Oct-25'`, grouped by market.
- **Source table:** `fact_rental_market`
- **Unit:** %
- **Verified:** Windsor 3.6%, Hamilton 1.6%, Kitchener-Cambridge-Waterloo 3.3%, London 4.1%, St. Catharines-Niagara 5.5% -- Windsor sits mid-pack.
- **Caveat:** this is CMHC's own matched-sample rent-growth figure (existing-tenant, turnover-adjusted) -- don't recompute it as a simple `(rent_2025 - rent_2024) / rent_2024` from KPI 17's two periods, it won't match exactly.

### 19. Affordability-gap index -- NOT COMPUTABLE
- **Definition:** whether rent is growing faster than renter income, by market -- the intended headline comparison metric.
- **Formula:** `rent_growth_pct - renter_income_growth_pct` -- **`renter_income_growth_pct` and the resulting index are left `NULL`, not estimated.**
- **Source table:** `warehouse.v_story4_affordability_gap` (view; `fact_rental_market`)
- **Unit:** percentage-point gap
- **Caveat (why `NULL`, not estimated):** no source extracted so far contains a renter/household income **time series** to compute a real growth rate from -- `fact_census_profile`'s income figures are a single 2021 snapshot, not year-over-year. A placeholder number would look like real data in a chart with no way for a viewer to tell the difference -- see `docs/affordability_gap_index.md`'s full "Limits" section for what source would close this gap.

---

## Cross-cutting notes

- Every KPI above is grounded in a real, currently-loaded row in `warehouse` -- none are projected, estimated, or interpolated, except the two explicitly marked `NULL`.
- `sql/story3_views.sql` and `sql/story4_views.sql` define the SQL views referenced above, but **are not yet applied to every environment** -- confirmed while building this catalogue: querying `warehouse.v_story4_vacancy_comparison` directly against this machine's database returned "relation does not exist." KPIs 16-19 above were verified by querying `fact_rental_market` directly with the same filters the views apply, not through the views themselves. Running `sql/story3_views.sql` and `sql/story4_views.sql` against a given environment is a prerequisite before building Superset charts on top of those view names specifically.
