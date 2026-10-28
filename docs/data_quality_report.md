# Data Quality Report

Shared validation report for this project's source tables. Each section
documents real, computed checks against real data -- not assumptions.
Run the corresponding `etl/validate_*.py` script to reproduce a section;
re-running overwrites that section in place, leaving the others untouched.

<!-- BEGIN: supply tables -->

## Supply tables (CMHC starts/completions)

Source: `data/staging/ontario_canada_starts_completions.csv` -> `warehouse.fact_starts_completions`
Checked: 2026-10-22

### 1. Counts
- Total rows: **50**
- Provinces: Canada, Ontario
- Periods (2): January to June 2026, Second Quarter 2026
- Activities: Completions, Starts, Under Construction
- Dwelling types: Apartment and Other, Row, Semis, Singles, Total
- Activities per (province, period): quarter periods have 3 (Starts, Completions, Under Construction); the YTD period has only 2 (no Under Construction -- a stock metric that doesn't accumulate YTD, a real structural difference, not a missing-data gap).

### 2. Ranges
- **PASS** -- units range [284, 410323]
- Negative rows: 0, null rows: 0, absurd (>10,000,000) rows: 0

### 3. Reconciliation (dwelling-type components sum to Total)
- **PASS** -- 10 groups checked, 0 mismatches

### 4. Missing months/periods
- **NOT a time series** -- 2 period(s) present: January to June 2026, Second Quarter 2026
- This is a single-quarter snapshot (Second Quarter 2026) plus its own YTD figure (January to June 2026), not a multi-period time series. CMHC publishes this table quarterly going back many years -- every prior quarter is 'missing' from this project's data, not just a few scattered gaps. A real time series requires extracting additional historical editions, which hasn't been done yet.

<!-- END: supply tables -->

<!-- BEGIN: rental market tables -->

## Rental market tables (CMHC RMS -- Windsor, historical)

Source: `warehouse.fact_rental_market` (2 staging sources -> 1 table)
Checked: 2026-10-28

### 1. Row counts vs. source
- **PASS** -- live table: 2385 rows, staging sources combined: 2385, expected after known exclusions: 2385
  - `windsor_rental_market.csv`: 1395
  - `windsor_rental_market_historical.csv`: 990

### 2. Rent and vacancy ranges
- **PASS** -- 0 value(s) outside their metric's real bound, 0 metric_type(s) with no bound defined
  - `average_rent`: [50, 10000]
  - `new_stock_average_rent`: [50, 10000]
  - `new_stock_universe`: [0, +inf]
  - `new_stock_vacancy_rate`: [0, 100]
  - `pct_change_rent`: [-100, 100]
  - `quintile_universe`: [0, +inf]
  - `quintile_vacancy_rate`: [0, 100]
  - `rent_occupied_units`: [50, 10000]
  - `rent_vacant_units`: [50, 10000]
  - `turnover_rate`: [0, 100]
  - `universe`: [0, +inf]
  - `vacancy_rate`: [0, 100]

### 3. Duplicate keys
- **PASS** -- 2385 rows checked, 0 in a duplicate (zone, period, bedroom_type, dwelling_type, income_band, metric_type) group

### 4. Reliability letters
- **PASS** -- values present: ['a', 'b', 'c', 'd'], valid legend: ['a', 'b', 'c', 'd']

<!-- END: rental market tables -->

<!-- BEGIN: rental market comparison table -->

## Rental market comparison table (CMHC Canada RMS 2025)

Source: `warehouse.fact_rental_market_comparison` (1 staging source -> 1 table)
Checked: 2026-10-28

### 1. Row counts vs. source
- **PASS** -- live table: 36 rows, staging sources combined: 40, expected after known exclusions: 36
  - `rms_canada_comparison.csv`: 40
  - Known exclusion: 4 row(s) from `rms_canada_comparison.csv` -- Windsor's vacancy_rate/average_rent rows, excluded at load time as duplicates of the Windsor-specific workbook

### 2. Rent and vacancy ranges
- **PASS** -- 0 value(s) outside their metric's real bound, 0 metric_type(s) with no bound defined
  - `average_rent`: [50, 10000]
  - `new_stock_average_rent`: [50, 10000]
  - `new_stock_universe`: [0, +inf]
  - `new_stock_vacancy_rate`: [0, 100]
  - `pct_change_rent`: [-100, 100]
  - `quintile_universe`: [0, +inf]
  - `quintile_vacancy_rate`: [0, 100]
  - `rent_occupied_units`: [50, 10000]
  - `rent_vacant_units`: [50, 10000]
  - `turnover_rate`: [0, 100]
  - `universe`: [0, +inf]
  - `vacancy_rate`: [0, 100]

### 3. Duplicate keys
- **PASS** -- 36 rows checked, 0 in a duplicate (zone, period, bedroom_type, dwelling_type, income_band, metric_type) group

### 4. Reliability letters
- **PASS** -- values present: ['a', 'b', 'c', 'd'], valid legend: ['a', 'b', 'c', 'd']

<!-- END: rental market comparison table -->
