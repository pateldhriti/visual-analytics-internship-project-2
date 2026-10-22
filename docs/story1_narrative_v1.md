# Story 1 — "Who faces the greatest housing affordability pressure?" (Chart List & Narrative v1)

**Status:** first draft. Builds directly on `docs/story1_narrative_outline.md` (the original chart
plan) and `docs/story1_validation.md` (the figures below are the *corrected* ones — the
denominator bug that validation found and fixed changes two of the four findings' numbers, and one
of them materially: the income-bracket ranking itself flips). Grounded entirely in
`warehouse.fact_shelter_cost` via `sql/story1_views.sql`, StatCan 98-10-0252-01, Windsor CMA, 2021
Census.

## Chart list (updated from the outline — same 4 charts, corrected figures)

| # | Chart | Source view | What it shows now |
|---|---|---|---|
| 1 | Owner vs. renter burden | `v_story1_burden_by_tenure` | Owner 10.9%, Renter **34.8%** (was 34.5% before the fix — now an exact match to StatCan's own published rate) |
| 2 | Burden by household type | `v_story1_burden_by_household_type` | Top 3 unchanged in rank, each up ~0.1-0.2 points: 32.9% / 31.1% / 23.3%, baseline 17.5% |
| 3 | Burden by income bracket | `v_story1_burden_by_income_band` | **Ranking changed, not just the numbers**: Under $10,000 is now first at **93.1%** (was reported second, at 73.6%), ahead of $10,000-$19,999 at 76.5% |
| 4 | Severity within the 30%+ group | (Story 1 Q3, not yet a named view) | Unchanged: 91.2% in the 30-<100% band, 8.8% (2,535 households) unaccounted for |

## Draft text

In Windsor, renters hit the 30%-of-income shelter-cost line far more often than owners do — **34.8%
of renter households** spend 30% or more of their income on shelter, compared with **10.9% of owner
households**. That's not a small gap: a renter household is more than three times as likely to be
cost-burdened as an owner household in the same city. This figure is also one this project has
independently reproduced from two different Statistics Canada products and confirmed matches
exactly (`docs/story1_validation.md`) — not an estimate, a verified number.

Splitting owners and renters further by household type sharpens the picture without changing its
shape. Non-census-family one-person households carry the heaviest burden at 32.9%, followed closely
by non-census-family households overall at 31.1% and one-parent families at 23.3% — all well above
Windsor's citywide baseline of 17.5%. The households most exposed to housing-cost pressure, in other
words, tend to be the ones without a second income or a shared-earner structure to fall back on.

Income tells a sharper version of the same story — sharper than this project originally reported.
Households earning under $10,000 a year are burdened at **93.1%**, not the 73.6% first calculated:
that correction came from excluding households with no computable shelter-cost ratio at all (zero or
negative income, or an agricultural-operation dwelling) from the denominator, the same adjustment
StatCan's own published rate already makes. Once that's done, the lowest income bracket isn't a
close second to $10,000-$19,999 (76.5%) — it's clearly the most burdened group in Windsor by a wide
margin. Burden still falls sharply as income rises from there, as expected, but the real headline is
how extreme the bottom bracket is once the number is measured correctly.

Within the group spending 30% or more, most of the burden is severe rather than borderline: 91.2% of
burdened households (26,210 of 28,745) are in the 30%-to-under-100% range, not just barely over the
line. The remaining 2,535 households (8.8%) aren't accounted for by any sub-category StatCan
publishes for this table — flagged honestly here as an open data-quality question
(`docs/shelter_cost_audit.md`), not folded into the 30-<100% figure or assumed to be 100%+ spenders
without a source for that label.

## Open items for v2

- **Chart order worth revisiting.** The outline put household type (chart 2) before income bracket
  (chart 3) when both findings were similarly sized. Now that income bracket's corrected figure
  (93.1%) is the single most dramatic number in the whole story — more dramatic than the
  owner/renter headline itself — it may read better leading with income rather than following
  household type. Flagging as an open question, not changing the order unilaterally here.
- **Bridging sentence between findings 2 and 3** (household type vs. income) is still needed in the
  final prose, per the outline's own open question — this draft states both findings but doesn't yet
  explicitly connect them (e.g. whether low-income and non-family-household status overlap in this
  data, which isn't something these two univariate breakdowns can answer on their own).
- **No chart exists yet in Superset for any of these 4 findings** — this is text and SQL views only;
  building the actual charts and embedding them in `web/src/pages/StoryAffordability.jsx` is
  separate, not-yet-done work.
