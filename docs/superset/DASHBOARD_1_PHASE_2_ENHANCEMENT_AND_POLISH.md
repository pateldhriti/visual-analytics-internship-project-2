# Dashboard 1 – Phase 2: Enhancement, Interaction and Final Layout Polish

## Project
**Windsor Housing Visual Analytics**  
Dashboard: **01 - Windsor Housing Executive Overview**

## Objective
Phase 2 converted the working Dashboard 1 prototype into a structured Executive Overview suitable for demonstration and final React integration.

## Story Structure

### Housing Affordability
Contains:
- Housing Cost Burden by Tenure
- Renter Housing Cost Burden KPI
- Owner Housing Cost Burden KPI

Purpose: show the renter-owner affordability contrast immediately.

### Windsor Rental Market
Contains:
- Average Rent
- Vacancy Rate
- Rental Stock
- Turnover Rate
- Oct-24 vs Oct-25 comparison table
- Dwelling Scope filter

Purpose: support current-market exploration and period comparison.

### Housing Supply
Contains:
- Housing Supply Snapshot
- YTD Starts vs Completions by Dwelling Type

Purpose: show the August 2026 snapshot and Jan-Aug 2026 YTD construction activity without inventing a historical trend.

### Windsor vs Canadian CMAs
Contains:
- Windsor vs CMA Benchmark table

Purpose: compare Windsor with the validated national CMA benchmark.

## Naming Cleanup
Redundant `Overview -` prefixes were removed where possible.

Examples:
- Average Rent
- Vacancy Rate
- Rental Stock
- Turnover Rate
- Housing Cost Burden by Tenure
- Renter Housing Cost Burden
- Owner Housing Cost Burden

## Number and Unit Formatting
Formatting was reviewed so each metric uses the correct unit:
- rent as currency
- rental stock as units
- vacancy/turnover as rates
- affordability metrics as percentages or clearly labelled percent values

The rental-stock currency formatting issue was corrected.

## Filter Validation
The `Dwelling Scope` filter was tested with:
- `apartment`
- `row_and_apartment`
- `row_townhouse`

It correctly updates only the compatible rental visuals and leaves Affordability, Housing Supply, and CMA Comparison unchanged.

## Rental Period Comparison
The Oct-24 vs Oct-25 table was retained because it adds real analytical comparison beyond KPI cards.

It shows:
- previous value
- latest value
- absolute change
- change unit
- trend/significance information where available

## Layout Improvements
Charts and KPI cards were reorganized by story rather than creation order.

Key decisions:
- KPI cards grouped together
- wide tables given more horizontal space
- charts kept large enough for readable axes, labels, and legends
- section headers separate the four stories
- charts are not intentionally shrunk when doing so causes Superset/ECharts to hide or paginate content

## Final Structure

```text
01 - Windsor Housing Executive Overview

Housing Affordability
- Housing Cost Burden by Tenure
- Renter Burden KPI
- Owner Burden KPI

Windsor Rental Market
- Dwelling Scope Filter
- Average Rent
- Vacancy Rate
- Rental Stock
- Turnover Rate
- Oct-24 vs Oct-25 Comparison

Housing Supply
- August 2026 Supply Snapshot
- Jan-Aug 2026 Starts vs Completions by Dwelling Type

Windsor vs Canadian CMAs
- Windsor vs CMA Benchmark
```

## Phase 2 Outcome
Dashboard 1 is functionally complete:
- analytical content complete
- native rental filter working
- filter scope validated
- comparison components included
- four analytical sections separated
- unit/formatting issues corrected
- titles simplified
- layout reorganized

Any remaining work is limited to final theme consistency across all five dashboards.

## Status
**Dashboard 1: COMPLETE**
