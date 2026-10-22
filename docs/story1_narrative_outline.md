# Story 1 — Narrative Outline

**Headline question (proposal):** "Who faces the greatest housing affordability pressure?"

**Status:** superseded by `docs/story1_narrative_v1.md` (first prose draft, with corrected figures
from `docs/story1_validation.md`'s denominator-bug fix — Q1's renter figure and Q2's entire ranking
changed). This outline is kept for the original chart-order reasoning, but the specific numbers
below are stale; see the v1 doc for current ones.

**Data dependency now resolved:** `docs/story1_questions_and_measures.md`'s dependency note flagged
that these formulas were only verified against the local staging CSV, not yet loaded into the
database. That's resolved — `etl/run_affordability_etl.py` now loads this table straight into
`warehouse.fact_shelter_cost`, so every finding below can be built as a real Superset chart against
the warehouse, not just computed by hand.

## Page flow

Following the generic story-page layout already in `docs/wireframes.html` (Screen 2):

1. **Label + title** — "Story 1" / "Who faces the greatest housing affordability pressure?"
2. **Guiding questions** (from `web/src/pages/StoryAffordability.jsx`'s current placeholder,
   kept as-is): "How does shelter-cost burden vary by income group and household type?" / "How
   different is the burden for renters and owners?"
3. **Embedded Superset dashboard** — 4 charts, in the order listed below.
4. **Narrative text** (2-3 paragraphs) — written to walk through the 4 charts in the same order,
   each paragraph naming the real figures the chart shows.
5. **Data source note** — `warehouse.fact_shelter_cost`, StatCan 98-10-0252-01, 2021 Census;
   link to `docs/shelter_cost_audit.md` and `docs/peer_test_affordability_etl.md`.

## Findings to test (4, in display order)

All 4 are already verified in `docs/story1_questions_and_measures.md` — this picks which of its
5 questions become the story's featured findings, and in what order, rather than re-deriving them.

1. **Owner vs. renter burden (Q1).** Renters are burdened more than 3x as often as owners —
   34.5% (15,735 / 45,605) vs. 10.9% (13,005 / 119,125). This is the story's headline contrast and
   opens the page: tenure is the first and starkest split in "who."
2. **Burden by household type (Q4).** Non-census-family one-person households face the highest
   burden (32.7%), followed by non-census-family households overall (30.9%) and one-parent
   families (23.2%) — all well above the Windsor-wide baseline of 17.4%. Narrows "who" from tenure
   to household composition.
3. **Burden by income bracket (Q2).** Burden drops sharply as income rises: $10,000-$19,999 at
   76.4%, under $10,000 at 73.6%, $20,000-$29,999 at 56.2%. Narrows "who" a third way, and sets up
   the steepness of the income gradient as its own point.
4. **Severity within the burdened group (Q3).** Of the 28,745 households spending 30%+ on shelter
   costs, 26,210 (91.2%) are in the 30-<100% band; the remaining 2,535 (8.8%) aren't accounted for
   by any published sub-category. Closes the page on "how bad," with the residual flagged
   honestly as an open data-quality question (per `docs/shelter_cost_audit.md`), not assumed away.

**Left out deliberately:** Q5 (households outside the ratio calculation entirely, 0.31%) — the
source doc itself already notes this is "small enough in Windsor to mention but not a major story
element on its own." Worth one line in the narrative text or a data-source footnote, not its own
chart.

## Chart order

| # | Finding | Chart type | Why |
|---|---|---|---|
| 1 | Owner vs. renter burden | 2-bar comparison (or 2 KPI tiles + 1 small bar) | Only 2 categories — a KPI-style contrast reads faster than a full bar chart for a 2-way split, and sets the page's opening number immediately. |
| 2 | Burden by household type | Horizontal bar, sorted descending | Household-type labels are long (`docs/shelter_cost_audit.md`'s label-collision categories) and there are several of them — horizontal bars keep labels readable without truncation. |
| 3 | Burden by income bracket | Vertical bar, ordered by income bracket (not sorted by value) | Income brackets have a natural order (low to high); keeping that order on the x-axis is what makes "burden drops as income rises" visually obvious, which a value-sorted bar would obscure. |
| 4 | Severity within the 30%+ group | Stacked bar or donut: 30-<100% segment vs. unaccounted residual | A part-of-a-whole breakdown, not a ranking — and the residual segment should be visually distinct (e.g. hatched or muted) to signal "unaccounted for," not just another category. |

## Open question for the narrative draft

Charts 2 and 3 both answer "which sub-group is worst off," just sliced differently (household type
vs. income). The prose draft needs one explicit sentence bridging them — e.g. that low-income and
non-family-household status overlap partially but aren't the same lens — rather than presenting
back-to-back rankings with no connecting logic between them.
