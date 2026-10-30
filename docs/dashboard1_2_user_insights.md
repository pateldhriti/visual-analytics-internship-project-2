# Dashboards 1 & 2 -- User-Facing Insights

Short, plain-language readings of each major section of Dashboard 1 (**01 - Windsor Housing
Executive Overview**) and Dashboard 2 (**Story 1: Who faces the greatest affordability
pressure?**), written to be reused on the React story pages and in the user guide. Each section
has:

- **What it shows**: one sentence on what the chart measures.
- **What it tells us**: the reading, using the real figures on the dashboard.
- **Questions to explore**: prompts that point a reader at the filters or the next section.

All figures are from the live warehouse views behind each chart (queried directly, not copied
from older docs). Affordability figures are from the 2021 Census; rental figures are CMHC's
October 2025 survey unless stated.

---

## Dashboard 2 -- Story 1: Affordability

### Gap KPIs

**What it shows:** the share of renter and owner households spending 30% or more of their income
on shelter (the standard "unaffordable" line), and how many Windsor households that is in total.

**What it tells us:** **34.8%** of renter households are over the line, against **10.9%** of
owners -- renters are about three times as likely to be cost-burdened. In total **28,740**
households in the Windsor CMA spend 30%+ of income on shelter.

**Questions to explore:**
- Renters are only about 28% of Windsor's households (45,280 of 164,220), but how much of the
  burdened total do they make up? (About 55%: 15,735 of 28,740.)
- Is the renter-owner gap driven by income, household type, or both? (See the next two sections.)

### Burden Rate by Income Band

**What it shows:** the share of households over the 30% line in each household-income bracket.

**What it tells us:** burden falls steeply as income rises. Below $10,000 almost every household
is burdened (**93.1%**). It is still more than half at $20,000-$29,999 (**56.2%**) and drops under
30% only in the $40,000-$49,999 band (**28.3%**). At $100,000 and over it is **1.5%**. In
Windsor, affordability pressure is mostly a low-income problem rather than a market-wide one.

**Questions to explore:**
- Use the Tenure filter: at the same income, are renters more burdened than owners?
- Roughly where is the income threshold below which a typical Windsor rent stops being affordable?

### Burden Rate by Household Type

**What it shows:** the share of households over the 30% line for each household type in the
Census family-structure breakdown.

**What it tells us:** people living alone are the most exposed: **32.9%** of one-person households
are burdened, and at **15,160** households they are more than half of everyone who is burdened.
One-parent families come next at **23.3%**. Couples, with or without children, sit around **9%**.
The common thread is a single income paying for a whole home.

**Questions to explore:**
- With the Tenure filter set to Renter, how much higher do one-person and one-parent households
  go?
- Which household types should Story 2's rental-market figures (bachelor and 1-bedroom rents) be
  read against?

### Burden Severity

**What it shows:** of the households already over the 30% line, how many fall in the 30-99%
range StatCan publishes, and how many are not covered by any published sub-category.

**What it tells us:** about **91%** of burdened households are in the 30-99% range (renters
90.7%, owners 91.8%). The remaining **9.3%** of burdened renters and **8.2%** of burdened owners
aren't covered by any published StatCan sub-category. The dashboard shows that gap as
"Unaccounted" rather than assuming it is the 100%+ group.

**Questions to explore:**
- What would it take to find out how many of the "Unaccounted" households spend 100% or more of
  their income on shelter? (See `docs/shelter_cost_audit.md`.)

### Census Validation

**What it shows:** a note confirming the dashboard's two headline rates match StatCan's own
published figures.

**What it tells us:** the 34.8% and 10.9% rates were reproduced from two separate StatCan
products and match exactly, so readers can trust them as official figures, not project
estimates.

---

## Dashboard 1 -- Executive Overview

### Housing Affordability

**What it shows:** the renter vs. owner burden comparison from Story 1, as a single summary.

**What it tells us:** same reading as Story 1 -- **34.8%** of renters vs. **10.9%** of owners
spend 30%+ of income on shelter. Use this as the entry point and send readers to the Story 1 page
for the income and household breakdowns.

### Windsor Rental Market

**What it shows:** four headline rental figures for the latest survey, and how each moved since
October 2024.

**What it tells us:** the market loosened slightly over the year while rents kept climbing:

| Figure (scope) | Oct-24 | Oct-25 | Change |
|---|---|---|---|
| Average rent (apartments) | $1,222 | $1,287 | +$65 (+5.3%) |
| Vacancy rate (apartments) | 3.3% | 3.7% | +0.4 points |
| Rental stock (all purpose-built) | 19,292 | 19,883 | +591 units |
| Turnover rate (all purpose-built) | 11.5% | 11.9% | +0.4 points |

More vacant units and 591 new rental units haven't stopped rents rising. The extra supply is
easing availability, but not price yet.

**Questions to explore:**
- Is the rent increase the same for every unit size? (Story 2's bedroom-type charts.)
- Where in the CMA was the new stock added? (Story 2's zone-level section.)

*Note:* rent and vacancy here are apartment-only; Story 2's tiles cover all purpose-built rentals
(Combined), so its figures differ slightly ($1,293, 3.6%). Both are correct for their scope.

### Housing Supply

**What it shows:** housing starts, completions and units under construction -- for **Ontario as
a whole**, because CMHC's source table has no Windsor-level breakdown.

**What it tells us:** in the second quarter of 2026 Ontario started **17,786** homes, completed
**14,083**, and had **162,138** under construction. Apartments dominate: **12,547** of the
quarter's starts (about 71%) and **134,228** of the units under construction. From January to
June, starts (**31,779**) ran ahead of completions (**27,476**), so the pipeline is still
growing.

**Questions to explore:**
- How much of this provincial pipeline is in Windsor-Essex? (Not answerable from this source --
  see the Methodology page's limitations.)

### Windsor vs Canadian CMAs

**What it shows:** Windsor's value on four rental measures against the median of four similar
Ontario CMAs (London, Kitchener-Cambridge-Waterloo, Hamilton, St. Catharines-Niagara), with
Windsor's rank out of the five.

**What it tells us:** Windsor is the **least expensive** of the five for a 2-bedroom apartment
(**$1,454**, about $200 below the comparator median of $1,653.50). Its rents are rising at about
the same pace as the others (**3.6%** vs. a 3.7% median), so the price advantage is holding but
not widening. Vacancy (3.7% vs. 4.0%) and turnover (12.2% vs. 14.1%) are both a little below the
median: Windsor renters move less often than renters in the comparison cities.

**Questions to explore:**
- Lower rents but lower turnover: are tenants staying put because moving would mean paying a
  higher new-lease rent? (Story 4 explores the comparison in full.)

*Note:* the benchmark uses 2-bedroom apartment rent, so its $1,454 is higher than the all-sizes
average rent in the Rental Market section.
