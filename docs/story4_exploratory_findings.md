# Exploratory Analysis: Story 4

**Goal:** query `warehouse.v_story4_vacancy_comparison`, `v_story4_rent_comparison`, and
`v_story4_affordability_gap` directly and look for patterns in how Windsor compares to its 4 real
comparator CMAs (Hamilton, Kitchener-Cambridge-Waterloo, London, St. Catharines-Niagara -- see
`docs/comparator_cmas_justification.md`) -- every figure below was pulled fresh from the live
warehouse, after fixing a real bug where Windsor's own row was missing from 2 of these 3 views (see
`sql/story4_views.sql`'s own header comment for the fix).

## Finding 1: Windsor has the lowest 2-bedroom apartment rent of all 5 markets

Windsor's Oct-25 average 2-bedroom rent is **$1,454** -- the cheapest of all 5 markets, **$73 below**
the next-cheapest, St. Catharines-Niagara ($1,527) -- `v_story4_rent_comparison`.

| Market | 2BR rent (Oct-25) |
|---|---|
| Windsor CMA | $1,454 |
| St. Catharines-Niagara CMA | $1,527 |
| London CMA | $1,651 |
| Hamilton CMA | $1,656 |
| Kitchener-Cambridge-Waterloo CMA | $1,832 |

## Finding 2: Despite the lowest rent, Windsor's vacancy rate is the second-tightest of the 5

Being the cheapest market doesn't mean Windsor has the most available supply. Its Oct-25 vacancy
rate is **3.7%**, just 0.1 points above Hamilton's 3.6% (the single tightest market) --
`v_story4_vacancy_comparison`. Affordability and market tightness aren't trading off against each
other here -- Windsor is simultaneously the cheapest and one of the two tightest markets.

| Market | Vacancy rate (Oct-25) |
|---|---|
| Hamilton CMA | 3.6% |
| Windsor CMA | 3.7% |
| St. Catharines-Niagara CMA | 3.9% |
| London CMA | 4.0% |
| Kitchener-Cambridge-Waterloo CMA | 4.1% |

## Finding 3: Windsor's rent growth sits almost exactly mid-pack

Windsor's Oct-24-to-Oct-25 rent growth is **3.6%** -- 3rd of 5, sandwiched between
Kitchener-Cambridge-Waterloo (3.3%) and London (4.1%) -- `v_story4_affordability_gap`. Not the
fastest- or slowest-growing market, despite being the cheapest and one of the tightest.

## Finding 4: St. Catharines-Niagara's rent is growing more than 3x as fast as Hamilton's

St. Catharines-Niagara has by far the fastest rent growth of the 5 markets at **5.5%** -- more than
**3x** Hamilton's 1.6%, the slowest -- a **3.9-percentage-point spread** across just 5 similarly
sized Ontario CMAs, not a tight cluster.

| Market | Rent growth (Oct-24 to Oct-25) |
|---|---|
| Hamilton CMA | 1.6% |
| Kitchener-Cambridge-Waterloo CMA | 3.3% |
| Windsor CMA | 3.6% |
| London CMA | 4.1% |
| St. Catharines-Niagara CMA | 5.5% |

## Finding 5: Hamilton is the one market where tight vacancy does NOT line up with fast rent growth

Hamilton has the single tightest vacancy rate (3.6%) of all 5 markets, but also the single slowest
rent growth (1.6%) -- the opposite of what tight-market logic would predict (low vacancy usually
drives faster rent growth, as it roughly does for St. Catharines-Niagara: 3rd-lowest vacancy at
3.9%, highest rent growth at 5.5%). Hamilton is the one real exception to that pattern in this
5-market set.

## Source

`warehouse.v_story4_vacancy_comparison`, `v_story4_rent_comparison`, `v_story4_affordability_gap` --
queried directly against the live database, 2026-10-29, after fixing a real bug where Windsor's own
row was missing from the first two views (Windsor's vacancy_rate/average_rent were excluded from
`fact_rental_market_comparison` at load time to avoid duplicating `fact_rental_market`, but neither
view was pulling Windsor's values back in from there -- see `sql/story4_views.sql`). Underlying data:
CMHC Rental Market Survey, national comparison table (apartment scope, Oct-24/Oct-25).
