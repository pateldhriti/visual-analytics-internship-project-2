# Dashboard 2 – Housing Affordability: Current Implementation Progress

## Project
**Windsor Housing Visual Analytics**  
Dashboard: **02 - Housing Affordability**

## Status
**In Progress – analytical components are largely built; final layout, filter verification, and polish remain.**

Central question:

> Who faces the greatest housing affordability pressure in Windsor?

## Income Group Analysis
Dataset:
`analysis.story1_affordability_by_income_group`

Chart:
**Burden by Income Group and Tenure**

Configuration:
- Chart type: Grouped Bar Chart
- X-axis: `income_group`
- Metric: `MAX(burden_30_plus_pct)`
- Series: `tenure`

Income bands were reordered into a meaningful progression rather than alphabetical order.

The chart supports interactive tenure analysis and shows how burden changes as income changes.

## Tenure Filter
Native filter:
`Tenure`

Values:
- Owner
- Renter
- Total - Tenure

The filter supports multi-select and has been tested with single and multiple tenure selections.

## Household Type Analysis
Dataset:
`analysis.story1_affordability_by_household_type`

Chart:
**Burden by Household Type and Tenure**

Configuration:
- X-axis: `household_type`
- Metric: `MAX(burden_30_plus_pct)`
- Series: `tenure`
- Hierarchy filter: `hierarchy_level = 1`

This prevents parent and child household categories from being mixed.

Top-level comparison:
- Census-family households
- Non-census-family household

## Burden Severity
Dataset:
`analysis.story1_burden_severity_by_tenure`

Chart:
**Burden Severity by Tenure**

Visualization:
- 100% stacked bar
- horizontal orientation

Severity categories:
- Spending less than 30%
- 30% to less than 100%
- 100% or more

Validated renter composition is approximately:
- 65.25% spending less than 30%
- 31.52% spending 30% to less than 100%
- 3.24% spending 100% or more

## Renter–Owner Gap KPIs
Dataset:
`analysis.story1_tenure_burden_gap`

Created two Big Number cards:

### Renter–Owner Burden Gap
**23.8 percentage points**

### Renter / Owner Burden Ratio
**3.18x**

These KPIs are intentionally independent of the Tenure filter because the view is a pre-calculated renter-versus-owner comparison.

## Calculated vs Census Published
Dataset:
`analysis.story1_burden_vs_census_published`

Validation table columns:
- `tenure`
- `calculated_burden_30_plus_pct_1dp`
- `census_published_pct`
- `difference_pct_points_1dp`

Validated results:

| Tenure | Calculated | Census Published | Difference |
|---|---:|---:|---:|
| Renter | 34.8 | 34.8 | 0.0 |
| Total - Tenure | 17.5 | 17.5 | 0.0 |
| Owner | 10.9 | 10.9 | 0.0 |

Purpose: demonstrate that the project calculation reproduces the published Statistics Canada rates.

## Analytical Questions Covered
Dashboard 2 currently answers:
1. How does burden vary by income group?
2. How does renter burden differ from owner burden?
3. Which top-level household type experiences greater burden?
4. How severe is housing-cost pressure?
5. How large is the renter-owner gap?
6. How many times higher is renter burden?
7. Do calculated results reproduce published Census values?

## Planned Final Layout

```text
02 - Housing Affordability
[ Tenure Filter ]

Affordability Gap: Renters vs Owners
[ Gap KPI ] [ Ratio KPI ]

Who Faces the Greatest Housing Cost Burden?
[ Full-width Burden by Income Group ]

[ Household Type Comparison ] [ Burden Severity ]

Data Validation
[ Calculated vs Census Published ]
```

## Remaining Work
- finalize chart sizing and spacing
- shorten redundant chart titles
- verify Tenure filter scope
- improve percentage/unit formatting where practical
- add section headers
- complete filter/functionality testing
- apply project-wide visual consistency

## Current Status Summary
Completed:
- income-group analysis
- tenure filter
- household-type analysis
- burden-severity analysis
- renter-owner gap KPI
- renter-owner ratio KPI
- Census validation table

Remaining:
- layout
- usability polish
- final filter/scoping verification
- final visual consistency review

**Dashboard 2 is in the polishing/testing stage.**
