# Dashboard 1 – Phase 1: Superset Setup and Baseline Executive Overview

## Project
**Windsor Housing Visual Analytics**  
Dashboard: **01 - Windsor Housing Executive Overview**  
Platform: **Apache Superset + PostgreSQL**

## Objective
This phase connected Apache Superset to the validated PostgreSQL analytical layer and created the first working Executive Overview covering the four approved stories: Housing Affordability, Windsor Rental Market, Housing Supply, and Windsor vs Canadian CMA Comparison.

## Superset Environment Setup
Apache Superset was run through the existing Docker environment with PostgreSQL and Redis.

```powershell
cd docker
docker compose --env-file ../.env up -d
```

Superset was accessed at `http://localhost:8088`.

Database connection:
- Database: `housing_windsor`
- Host inside Docker: `postgres`
- Port: `5432`
- Schema used for analytics: `analysis`

The connection was verified through Superset SQL Lab.

## SQL Analytics Verification
Selected analytical views were queried before dashboard creation.

```sql
SELECT *
FROM analysis.story1_affordability_by_tenure;
```

```sql
SELECT *
FROM analysis.story4_windsor_position;
```

Returned values matched the previously validated SQL analytics results.

## Superset Datasets Registered
The Executive Overview used:
- `analysis.story1_affordability_by_tenure`
- `analysis.story2_latest_cma_kpis`
- `analysis.story3_supply_totals`
- `analysis.story3_ytd_starts_completions`
- `analysis.story4_windsor_position`

CSV files were not uploaded directly into Superset; validated PostgreSQL analytical views were used as datasets.

## Housing Affordability
Created **Housing Cost Burden by Tenure**:
- Chart type: Bar Chart
- Dimension: `tenure`
- Metric: `MAX(burden_30_plus_pct)`
- Main comparison: Owner vs Renter
- Orientation: Horizontal

Validated values:
- Owner: about **10.9%**
- Renter: about **34.8%**

Supporting KPI cards:
- Renter Housing Cost Burden: **34.8**
- Owner Housing Cost Burden: **10.9**

## Rental Market KPIs
Using `analysis.story2_latest_cma_kpis`, created:
- Average Rent
- Vacancy Rate
- Rental Stock
- Turnover Rate

Apartment values used:
- Average rent: **$1,287**
- Vacancy: **3.7%**
- Rental stock: **19,042 units**
- Turnover: **12.2%**

Also created **Rental Market Oct-24 vs Oct-25** table containing previous value, latest value, change, change unit, and CMHC trend/significance information where available.

## Dwelling Scope Filter
Created native filter: **Dwelling Scope**

Values:
- `apartment`
- `row_and_apartment`
- `row_townhouse`

Scoped only to:
- Average Rent
- Vacancy Rate
- Rental Stock
- Turnover Rate
- Rental Market Oct-24 vs Oct-25

Affordability, Housing Supply, and CMA Comparison were intentionally excluded.

## Housing Supply
Created **Housing Supply Snapshot** from `analysis.story3_supply_totals` using `MAX(published_total_units)`.

Created **YTD Starts vs Completions by Dwelling Type** from `analysis.story3_ytd_starts_completions`.

Dwelling types:
- Singles
- Semis
- Row
- Apt. and Other

Validated YTD totals:
- Starts: **594**
- Completions: **881**

## CMA Benchmark
Using `analysis.story4_windsor_position`, created a benchmark table showing:
- metric
- period
- Windsor value
- CMA median
- Windsor minus median
- Windsor rank
- CMAs ranked

Metrics include two-bedroom rent, rent growth, turnover, and vacancy.

## Phase 1 Outcome
Phase 1 produced a complete working analytical baseline:
- PostgreSQL connected to Superset
- SQL views registered as datasets
- affordability comparison created
- rental KPIs created
- native Dwelling Scope filter added
- rental period comparison added
- supply visuals added
- CMA benchmark added

The dashboard was functionally complete but still needed layout restructuring, naming cleanup, formatting, and final usability improvements.

## Next Phase
Phase 2 focuses on:
- layout restructuring
- section headers
- title cleanup
- chart/table resizing
- unit formatting
- filter-scope verification
- presentation polish
