# Exploratory Analysis: Story 2

**Goal:** query `warehouse.v_story2_rent_yoy_change`, `v_story2_vacancy_trend`,
`v_story2_turnover_by_bedroom`, `v_story2_rent_growth`, and `v_story2_rent_by_zone_bedroom` directly
and look for patterns beyond the headline rent/vacancy numbers already on the Story 2 page -- every
figure below was pulled fresh from the live warehouse.

## Finding 1: Vacancy didn't just rise -- it round-tripped through a 6-year low before recovering

Windsor CMA vacancy (Combined, Total bedroom) fell from 3.5% (Oct-20) to a low of **1.8% in Oct-22**,
then climbed back up to 3.6% by Oct-25 -- `v_story2_vacancy_trend`. The 6-year span isn't a simple
up or down trend; it's a tight-market dip in the middle, not visible from comparing only the first
and last years.

| Period | Vacancy rate |
|---|---|
| Oct-20 | 3.5% |
| Oct-21 | 3.4% |
| Oct-22 | 1.8% |
| Oct-23 | 2.1% |
| Oct-24 | 3.2% |
| Oct-25 | 3.6% |

## Finding 2: 2-Bedroom units had the largest real rent increase of any size, in both dollars and percent

Over the project's real 5-year span (Oct-20 to Oct-25), 2-Bedroom rent rose from $1,038 to $1,451 --
a **$413 (39.8%)** increase, the largest of the 4 bedroom types this project has a full span for --
`v_story2_rent_growth`. Studio (+35.8%, +$250) and 1-Bedroom (+32.9%, +$295) grew nearly as fast in
percentage terms but by smaller dollar amounts.

## Finding 3: 3 Bedroom+ is the one segment where rent fell, not rose -- and it's also the least reliable series

Every bedroom type in this dataset rose every single year except one: 3 Bedroom+ rent **fell two years
running** -- -9.6% in Oct-23 ($1,476 to $1,334) and -6.1% in Oct-24 ($1,334 to $1,253) --
`v_story2_rent_yoy_change`. CMHC doesn't publish an Oct-25 figure for this segment at all (`NULL`),
and its own reliability letter starts at `'d'` (the lowest confidence grade) in Oct-20 before
improving to `'a'` by Oct-24 -- so this is also the one trend in the whole dataset built on the
shakiest underlying sample, flagged as such rather than treated with the same confidence as the
other 4 bedroom types.

## Finding 4: Studios turn over almost 3x as often as 3 Bedroom+ units

As of Oct-25, Studio turnover (15.0%) is the highest of any bedroom type and 3 Bedroom+ (5.3%) the
lowest -- a **2.8x spread** -- `v_story2_turnover_by_bedroom`. Total turnover across all bedroom
types sits at 11.9%, between the two extremes but closer to the smaller-unit end.

| Bedroom type | Turnover rate (Oct-25) |
|---|---|
| Studio | 15.0% |
| 1 Bedroom | 13.4% |
| Total | 11.9% |
| 2 Bedroom | 10.7% |
| 3 Bedroom + | 5.3% |

## Finding 5: Amherstburg is Windsor's priciest zone by a wide margin -- $800 above the cheapest

Of Windsor's 7 real internal zones, Zone 5 - Amherstburg has the highest Oct-25 average rent at
**$1,955** (Total bedroom), while Zone 1 - Centre is the cheapest at $1,155 -- a **$800 (69%) gap**
between the two -- `v_story2_rent_by_zone_bedroom`. The next-highest zone, Zone 6 - North Essex
County ($1,682), is itself $273 below Amherstburg, so this isn't a close cluster at the top -- one
zone is genuinely out ahead of the rest.

| Zone | Average rent (Oct-25, Total) |
|---|---|
| Zone 5 - Amherstburg | $1,955 |
| Zone 6 - North Essex County | $1,682 |
| Zone 7 - South Essex County | $1,347 |
| Zone 3 - East Outer | $1,336 |
| Zone 2 - East Inner | $1,245 |
| Zone 4 - West | $1,230 |
| Zone 1 - Centre | $1,155 |

## Source

`warehouse.v_story2_rent_yoy_change`, `v_story2_vacancy_trend`, `v_story2_turnover_by_bedroom`,
`v_story2_rent_growth`, `v_story2_rent_by_zone_bedroom` -- queried directly against the live
database, 2026-10-29. Underlying data: CMHC Rental Market Survey, Windsor CMA (Oct-20 through Oct-25
editions -- see `docs/rms_historical_extraction.md`).
