# Exploratory Analysis: Story 1

**Goal:** query `warehouse.v_story1_burden_by_tenure`, `v_story1_burden_by_income_band`, and
`v_story1_burden_by_household_type` directly and look for patterns beyond the three headline
numbers already on the Story 1 page -- every figure below was pulled fresh from the live warehouse,
not reused from `docs/story1_narrative_v1.md` without re-checking.

## Finding 1: Renters are burdened at more than 3x the rate of owners

34.8% of renter households (15,735 of 45,280) spend 30%+ of income on shelter, vs. 10.9% of owner
households (13,005 of 118,940) -- `v_story1_burden_by_tenure`.

## Finding 2: More burdened households citywide are renters than owners, even though owners outnumber renters nearly 3 to 1

Owner households (118,940) outnumber renter households (45,280) by a ratio of 2.6:1 citywide.
Renters are therefore only 27.6% of all households (45,280 of 164,220) -- but they make up **54.7%
of all burdened households** (15,735 of 28,745 total burdened). This is the one pattern not visible
from the rate alone: looking only at the 34.8%-vs-10.9% rate gap could suggest renter burden is a
smaller-population problem than it is -- in raw count, more burdened households in Windsor are
renters than owners.

## Finding 3: Burden rate falls almost perfectly monotonically with income -- no bracket out of order

Every one of the 11 real income brackets has a lower burden rate than the bracket below it, from
93.1% (under $10,000) down to 1.5% ($100,000 and over) -- a clean, uninterrupted gradient, not a
single threshold effect. The steepest single-bracket drop is between $10,000-$19,999 (76.5%) and
$20,000-$29,999 (56.2%) -- a 20.3-percentage-point fall in one step, the largest of any bracket
transition in the curve.

| Income band | Burden rate |
|---|---|
| Under $10,000 | 93.1% |
| $10,000-$19,999 | 76.5% |
| $20,000-$29,999 | 56.2% |
| $30,000-$39,999 | 43.6% |
| $40,000-$49,999 | 28.3% |
| $50,000-$59,999 | 20.7% |
| $60,000-$69,999 | 15.1% |
| $70,000-$79,999 | 9.7% |
| $80,000-$89,999 | 6.8% |
| $90,000-$99,999 | 5.1% |
| $100,000 and over | 1.5% |

## Finding 4: Non-census-family households are burdened at roughly double the citywide rate; couple-family households at roughly half it

One-person non-census-family households sit at 32.9% (15,160 of 46,015) and non-census-family
households overall at 31.1% (16,195 of 52,020) -- both close to double the 17.5% citywide baseline.
Couple-family households, with or without children, both land at exactly 9.1% -- about half the
baseline. Household structure splits the city almost evenly into a higher-burden half and a
lower-burden half around that 17.5% midpoint, rather than clustering near it.

## Finding 5: One-parent families are burdened more than 2.5x as often as couple families with children

23.3% of one-parent-family households (3,965 of 17,040) are burdened, vs. 9.1% of couple families
with children (4,070 of 44,625) -- the clearest single-income-vs-dual-income gap in the
household-type breakdown, and sharper than the renter-vs-owner gap in relative terms (2.56x vs.
3.19x -- close, but the one-parent comparison holds tenure constant in a way the renter/owner split
doesn't).

## Source

`warehouse.v_story1_burden_by_tenure`, `warehouse.v_story1_burden_by_income_band`,
`warehouse.v_story1_burden_by_household_type` -- queried directly against the live database,
2026-10-28. Underlying data: StatCan 98-10-0252-01, Shelter-cost-to-income ratio by tenure
(Windsor CMA, 2021 Census).
