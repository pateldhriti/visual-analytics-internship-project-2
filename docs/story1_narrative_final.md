# Story 1: Who Faces the Greatest Housing Affordability Pressure? (Final Narrative)

**Status:** final text for the React Story 1 page and the final report. Replaces the working draft in `docs/story1_narrative_v1.md`.
**Source:** Statistics Canada, Table 98-10-0252-01, Shelter-cost-to-income ratio by tenure, Windsor CMA, 2021 Census (2020 incomes). Figures come from the `warehouse.v_story1_*` views and match the Story 1 Superset dashboard (slug `windsor-story-1`, locally and on the university's Superset).

---

## Introduction

A household is considered cost-burdened when it spends 30% or more of its income on shelter: rent or mortgage payments, utilities and property tax. In the Windsor census metropolitan area, 28,745 of 164,220 households, or **17.5%**, were over that line in the 2021 Census. That average hides large differences. This story asks which households carry the burden, looking at tenure, income and household type in turn.

## Renters carry most of the burden

Tenure is the clearest dividing line. **34.8%** of renter households (15,735 of 45,280) spend 30% or more of their income on shelter, against **10.9%** of owner households (13,005 of 118,940). A renter household is about three times as likely to be cost-burdened as an owner household.

Renters are only 28% of Windsor's households, but they make up **55%** of the households over the 30% line. The two figures above were checked against a second StatCan product, the Census Profile's own published rates for Windsor, and match exactly.

## Income is the strongest driver

Burden falls steadily as income rises. Almost every household with an income under $10,000 is over the line (**93.1%**, 1,810 of 1,945). The rate is 76.5% for incomes of $10,000 to $19,999, 56.2% for $20,000 to $29,999 and 43.6% for $30,000 to $39,999. It drops below the Windsor average of 17.5% only once income passes about $60,000, and is just 1.5% for households earning $100,000 or more.

Put another way, households earning under $40,000 are **18%** of all Windsor households but **60%** of the cost-burdened ones (17,185 of 28,745). Affordability pressure in Windsor is mainly an income problem: housing costs that are manageable on a middle income are out of reach on a low one.

## Households with one income are most exposed

Household type points the same way. People living alone have the highest burden rate, **32.9%** (15,160 of 46,015), and because there are so many of them they account for more than half of all burdened households. One-parent families come next at **23.3%** (3,965 of 17,040). Couples, with or without children, are at about **9%**.

The pattern is consistent: households that rely on a single income have less room to absorb shelter costs than households with two earners.

## How far over the line?

Most burdened households spend between 30% and 100% of their income on shelter: 90.7% of burdened renters and 91.8% of burdened owners. The rest, about **2,535 households**, report shelter costs equal to or greater than their whole income. StatCan does not publish this group as its own row; it is the difference between the "30% or more" total and the "30% to less than 100%" band. These are often households with very low reported income in 2020, for example people living on savings or student loans, which the Census does not count as income. The figure should be read with that in mind.

## What this means

In Windsor, affordability pressure is concentrated among **renters, low-income households and people living alone**, and these groups overlap heavily. The other stories build on this: Story 2 asks what renters actually pay, Story 3 whether new supply suits them, Story 4 whether Windsor's lower rents relieve the pressure, and Story 5 combines them: an average 2-bedroom rent is out of reach for about 61% of renter households.

## Limitations

- This is one snapshot from the 2021 Census, so it cannot show whether burden is rising or falling.
- Incomes are from 2020, when temporary pandemic benefits raised many low incomes, so burden for that year may be lower than usual.
- StatCan rounds counts to multiples of 5, so totals can differ slightly (28,740 by tenure vs 28,745 overall).
- Households with zero or negative income have no shelter-cost ratio and are excluded from every rate.
