# Validate Story 1 Against Published Figures

**Goal:** reproduce StatCan's own published Windsor CMA figures (34.8% of tenants, 10.9% of owners
spending 30%+ of income on shelter costs, cited in the project proposal's Motivation section) from
the database, and log any differences.

## Result: found a real, material difference — traced to its exact root cause, not just rounding

The proposal's cited figures come from a **different StatCan product** than the one this project's
Story 1 formulas were built on: `fact_census_profile` (98-401-X2021002, Census Profile) publishes
these as direct, pre-computed rate characteristics (**1484**: "% of owner households spending 30%+",
**1492**: "% of tenant households spending 30%+"), separate from `fact_shelter_cost`
(98-10-0252-01, shelter-cost-to-income ratio by tenure) — the raw-count table every Story 1 formula
in `docs/story1_questions_and_measures.md` and `sql/story1_views.sql` was built on.

**Pulled StatCan's own published rate directly** (`fact_census_profile`, characteristics 1484/1492):

| | Published (Census Profile) |
|---|---|
| Owner | **10.9%** |
| Renter/Tenant | **34.8%** |

**Reproduced from `fact_shelter_cost` using the formula this project had been using** (burdened ÷
raw `Total - Shelter-cost-to-income ratio`):

| | Reproduced (old formula) | Matches published? |
|---|---|---|
| Owner | 10.9% (13,005 / 119,125) | Yes |
| Renter | **34.5%** (15,735 / 45,605) | **No — 0.3 points off** |

Owner matched; Renter didn't. Not close enough to dismiss as display rounding (the raw values are
exact integers, not independently-rounded floats), so this needed a real explanation, not a shrug.

## Root cause: "Not applicable" households were being counted in the denominator

`fact_shelter_cost` publishes a `'Not applicable'` row within `shelter_cost_ratio` for every
(income × household × tenure) combination: households on an agricultural operation, or with
zero/negative total income (per `98100252_MetaData.csv` note 9) — households a shelter-cost-to-income
ratio **cannot be computed for at all**, not households whose ratio happens to be unknown.

The old formula's denominator (`'Total - Shelter-cost-to-income ratio'`) includes those households
anyway. StatCan's own published rate (1484/1492) correctly excludes them. Checked the actual counts:

| | Total | Not applicable | Total − Not applicable |
|---|---|---|---|
| Owner | 119,125 | 185 | 118,940 |
| Renter | 45,605 | 325 | 45,280 |

Recomputing with the corrected denominator:

| | Burdened ÷ (Total − Not applicable) | vs. published |
|---|---|---|
| Owner | 13,005 / 118,940 = **10.9%** | exact match |
| Renter | 15,735 / 45,280 = **34.8%** | **exact match** |

Owner's gap was invisible before only because 185 households is too small a share of 119,125 to
shift the rounded 1-decimal percentage — the bug was there for Owner too, just not visible until
checked against a case (Renter, and especially the income-band breakdown below) where the "Not
applicable" share is proportionally larger.

## A second, bigger finding: the income-band ranking itself changes

Applying the same fix to `v_story1_burden_by_income_band` doesn't just nudge numbers — it **changes
which bracket is most burdened**:

| Income bracket | Old (wrong) denominator | Corrected denominator |
|---|---|---|
| Under $10,000 | 73.6% | **93.1%** |
| $10,000-$19,999 | 76.4% (previously ranked #1) | 76.5% |

"Under $10,000" was previously *reported as second place* (`docs/story1_questions_and_measures.md`
Q2) behind "$10,000-$19,999." With the corrected denominator, it's not close — **93.1% vs 76.5%**.
This makes sense once traced to its cause: very-low-income households are disproportionately the
ones with zero/negative income, so they're disproportionately represented in the "Not applicable"
group the old formula was diluting this bracket's denominator with. Once excluded, the households
*actually* in the Under-$10,000 bracket with a computable ratio turn out to be overwhelmingly
burdened — a materially different, and more accurate, finding than the original Q2 answer.

Household-type breakdown changes were smaller (non-census-family one-person: 32.7% → 32.9%;
baseline: 17.4% → 17.5%) — that dimension doesn't concentrate "Not applicable" households as sharply
as the lowest income bracket does.

## What was fixed

- **`sql/story1_views.sql`**: all 3 views' `total_households`/`burden_rate_pct` now sum
  `'Spending less than 30%'` + `'Spending 30% or more'` instead of the raw `'Total'` row. Re-applied
  to the live warehouse and re-verified: `v_story1_burden_by_tenure` now returns exactly
  **Owner 10.9%, Renter 34.8%** -- confirmed against StatCan's own published rate, not just against
  this project's own earlier (wrong) numbers.
- **`docs/story1_questions_and_measures.md`**: Q1 and Q2's "Verified result" lines corrected to
  match -- Q2 in particular now reports Under-$10,000 as the most-burdened bracket, not second.

## What still needs a follow-up (flagged, not fixed here)

- **`docs/kpi_catalogue.md`** (KPI 1 and KPI 2, authored separately) cites the old 34.5% figure and
  the old income-band ranking -- needs the same correction, out of scope for this validation task
  to edit directly.
- **`docs/story1_narrative_outline.md`**'s finding #3 (burden by income bracket) cites the old
  ranking and should be revisited once the actual prose narrative gets written, so the headline
  number matches what's now verified against StatCan's own published figures.
