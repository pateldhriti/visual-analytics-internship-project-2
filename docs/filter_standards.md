# Filter and Cross-Filter Standards

Shared rules for every native filter this project adds to a Superset dashboard, written down after
repeatedly finding (and fixing) the same 2 classes of real bug across Dashboards 1-4: a scope
conflict that silently zeroes out a chart, and inconsistent naming between dashboards. Applied to
Story 1's dashboard (id=3) below as the worked example.

## 1. Naming: Title Case, a short noun phrase

Every filter name is Title Case -- every word capitalized, not just the first. This project's
filters before this pass:

| Dashboard | Filter name (before) | Title Case? |
|---|---|---|
| Story 1 | Tenure | yes |
| Story 1 | Household type | **no** |
| Story 2/3 | Zone | yes |
| Story 2/3 | Bedroom type | **no** |
| Story 2/3 | Dwelling Scope | yes |

2 of 5 existing filters weren't Title Case -- a real, if minor, inconsistency, not a hypothetical
one. Story 1's "Household type" is corrected to "Household Type" here as the worked example (see
`etl/apply_filter_standards_story1.py`). Dashboard 3's "Bedroom type" is flagged as the same issue
but left as a follow-up -- this task's scope is Story 1 specifically, not a rename sweep across
every dashboard.

## 2. Placement: broadest dimension first, then category filters

Filters are ordered left-to-right from broadest/most-structural to narrowest:

1. A geographic dimension, if the dashboard has one (Zone on Dashboard 3/4).
2. The dashboard's most fundamental segment (Tenure on Story 1 -- the story's own headline split).
3. Narrower category filters (Household Type, Bedroom Type, Dwelling Scope).

This isn't a new rule invented for this doc -- it's the order every dashboard already used; writing
it down makes it a standard to follow deliberately on the next dashboard, not an accident of build
order.

## 3. Defaults: empty (show all) unless that would silently blend an aggregate

A multi-select filter defaults to no selection (show every value) *unless* leaving it empty would
let Superset AND an aggregate metric across values that can't be meaningfully combined -- e.g.
averaging a vacancy rate across both "Apartment" and "Combined" dwelling scope would produce a
blended number that isn't a real measurement of either. In that case, the filter is either:

- scoped only to a chart built specifically so every value is safe to show (Dashboard 3's "Dwelling
  Scope" filter -- see `etl/build_story2_dashboard.py`), or
- given an explicit non-empty default matching the dashboard's existing behavior, if removing a
  chart's hardcoded value entirely isn't being done.

No filter in this project currently needs the second form -- every one so far was handled by the
first, which is the lower-risk option and the one to prefer going forward.

## 4. Scope: never include a chart that already hardcodes the same column

**The real, recurring bug.** Superset ANDs a native filter's selection onto every in-scope chart's
own `adhoc_filters`. If a chart already hardcodes `tenure == 'Renter'` and a user-facing Tenure
filter is also scoped to that chart, picking "Owner" ANDs an impossible condition onto it and the
chart goes blank -- not an edge case, a guaranteed zero-rows result for most filter selections.

This has been found and fixed as a real bug 3 times in this project, not reasoned about in the
abstract:

- `etl/fix_story1_tenure_filter_scope.py` -- Renter/Owner Burden Rate KPI tiles (chart ids 3, 4)
  were in scope for Tenure/Household-type despite each hardcoding its own tenure value.
- `etl/build_story2_dashboard.py`'s Dwelling Scope filter -- scoped only to the one chart built
  without a hardcoded `dwelling_type_label`, since every other Dashboard 3 chart already hardcodes
  it (Apartment data is sparse/absent for rent and turnover at that scope).
- `etl/finalize_story1_layout.py`'s severity-breakdown chart -- the opposite case: tenure is that
  chart's *groupby*, not a hardcoded filter, so it was deliberately *added* to the Tenure filter's
  scope rather than excluded, since there the filter is meaningful and safe.

**The rule, stated once instead of re-derived each time:** before adding a chart to any filter's
`chartsInScope`, check that chart's own `adhoc_filters` for the exact column the filter targets. If
it's there as a hardcoded value, exclude the chart. If the column appears only as the chart's
`groupby`/`columns` dimension (not a fixed WHERE value), including it is correct and useful.

## Applied to Story 1 (worked example)

`etl/apply_filter_standards_story1.py` renames Story 1's "Household type" filter to "Household
Type" -- the only standards violation Story 1 actually had (its placement already puts Tenure
first, and its scope already correctly excludes the hardcoded-tenure KPI tiles per
`etl/fix_story1_tenure_filter_scope.py`). Idempotent: re-running it when the name is already correct
is a no-op.
