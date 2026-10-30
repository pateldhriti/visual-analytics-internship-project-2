# Exploratory Analysis: Story 3

**Goal:** query Story 3's Windsor supply views directly
(`warehouse.v_story3_windsor_supply_annual`, `v_story3_windsor_supply_per_1000_households`, and the
monthly `fact_windsor_starts_completions` they're built on) and look for patterns beyond the
headline starts/completions totals on the Story 3 dashboard. Every figure below was pulled fresh
from the live warehouse.

Scope: Windsor CMA, January 2016 to September 2026 -- StatCan table 34-10-0154-01 (CMHC's Starts
and Completions Survey at CMA level; see `etl/extract_windsor_starts_completions.py`). "Starts" and
"completions" are calendar-year sums; "under construction" is a point-in-time count, not a sum.

## Finding 1: Windsor switched from building mostly houses to mostly apartments in under a decade

In 2016, single-detached houses were **63.5%** of Windsor's housing starts and apartments only
**5.9%**. By 2024 that had flipped: apartments were **63.9%** of starts and singles **22.5%**. The
swing happened in two steps: a jump in 2019 (apartments 11.8% to 35.2%), then a steady climb from
2021 to 2024. Singles started fell from 804 units in 2016 to 331 in 2025 (**-59%**), while
apartment starts rose from 75 to 752 (10x).

| Year | Apartment share of starts | Single-detached share of starts |
|---|---|---|
| 2016 | 5.9% | 63.5% |
| 2018 | 11.8% | 61.2% |
| 2019 | 35.2% | 43.9% |
| 2021 | 41.8% | 36.2% |
| 2023 | 53.6% | 25.0% |
| 2024 | 63.9% | 22.5% |
| 2025 | 59.6% | 26.2% |

## Finding 2: 2024 was the decade's biggest building year -- and 2025 gave almost all of it back

Windsor started **2,157** homes in 2024: **13.0 per 1,000 households**, the highest of any year since
2016 and well above the decade average of **8.4 per 1,000** (13,905 starts over 2016-2025). Most of
the jump was apartments (1,379 of the 2,157). In 2025 starts fell **41%** to 1,262 (**7.6 per
1,000**), back below the decade average. The 2024 figure reads as a one-year surge, not a new,
higher level of building.

| Year | Starts | Starts per 1,000 households |
|---|---|---|
| 2022 | 1,515 | 9.1 |
| 2023 | 1,208 | 7.3 |
| 2024 | 2,157 | 13.0 |
| 2025 | 1,262 | 7.6 |
| 2016-2025 average | 1,391 | 8.4 |

*Per-1,000 rates use the 2021 Census household count (165,665) for every year -- the only household
figure this project has -- so they show the trend against a fixed base.*

## Finding 3: Since 2023 Windsor has finished more homes than it started, and the pipeline is shrinking

From 2019 to 2022, Windsor started more homes than it finished every year, and the number of units
under construction more than tripled, from 620 at the end of 2018 to **1,997** at the end of 2022.
Since then the balance has reversed: over 2023-2025 Windsor completed **5,247** homes and started
**4,627**. Completions beat starts in 2023 and 2025; only the 2024 surge (Finding 2) went the other
way. Units under construction stood at **1,303** in September 2026, the lowest September count
since 2020. Homes are being finished faster than new ones are begun, so the completions now arriving
are drawing down earlier starts rather than being replaced.

| Year | Starts | Completions | Under construction (year end) |
|---|---|---|---|
| 2019 | 1,345 | 858 | 1,108 |
| 2022 | 1,515 | 1,131 | 1,997 |
| 2023 | 1,208 | 1,967 | 1,394 |
| 2024 | 2,157 | 1,609 | 1,968 |
| 2025 | 1,262 | 1,671 | 1,635 |
| 2026 (Jan-Sep) | 690 | 1,029 | 1,303 (Sep) |

## Finding 4: 2026 is on track to be one of the slowest years for new starts since 2016

From January to September 2026 Windsor started **690** homes. That ties 2018 as the lowest
January-to-September total of the 11 years in this data, and is 60% below the same months of 2024
(1,729). The apartment share of starts also fell back to **40.1%**, from 59.6% in 2025, so the drop
is mostly in apartments: 277 apartment starts so far in 2026, against 752 in all of 2025.

| Year | Starts, January-September |
|---|---|
| 2018 | 690 |
| 2022 | 1,279 |
| 2024 | 1,729 |
| 2025 | 871 |
| 2026 | 690 |

## Finding 5: Windsor builds a smaller share of apartments than Ontario as a whole

In the same quarter (April-June 2026) and from the same CMHC survey, apartments were **55.5%** of
Windsor's starts (218 of 393) against **70.5%** for Ontario (12,547 of 17,786 --
`v_story3_starts_completions_by_dwelling_type`). Windsor's mix leans more toward ground-oriented
housing: singles were 28.5% of its starts that quarter (112 of 393), against 15.1% province-wide
(2,693 of 17,786). Windsor accounted for **2.2%** of Ontario's starts that quarter.

| April-June 2026 starts | Windsor CMA | Ontario |
|---|---|---|
| Total | 393 | 17,786 |
| Apartment and Other | 218 (55.5%) | 12,547 (70.5%) |
| Singles | 112 (28.5%) | 2,693 (15.1%) |
| Semis | 50 (12.7%) | 284 (1.6%) |
| Row | 13 (3.3%) | 2,262 (12.7%) |

## What these suggest for the Story 3 page

- Finding 1 is the clearest headline: the *kind* of housing Windsor builds has changed more than
  the *amount*.
- Findings 2-4 together answer "is Windsor building enough?" with a caution: the 2024 peak hasn't
  lasted, and both new starts and the pipeline are now below their recent levels.
- Finding 5 gives the Windsor-vs-Ontario comparison the current page can't make, since its
  narrative covers Ontario only.

## Source

`warehouse.v_story3_windsor_supply_annual`, `v_story3_windsor_supply_per_1000_households`,
`fact_windsor_starts_completions` and `v_story3_starts_completions_by_dwelling_type` -- queried
directly against the live database, 2026-10-30. Underlying data: CMHC Starts and Completions
Survey via Statistics Canada table 34-10-0154-01 (Windsor CMA, monthly), and CMHC's Quarterly
Starts, Completions and Units Under Construction table (Ontario, Second Quarter 2026).
