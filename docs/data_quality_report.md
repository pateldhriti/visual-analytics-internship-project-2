# Data Quality Report

Shared validation report for this project's source tables. Each section
documents real, computed checks against real data -- not assumptions.
Run the corresponding `etl/validate_*.py` script to reproduce a section;
re-running overwrites that section in place, leaving the others untouched.

<!-- BEGIN: supply tables -->

## Supply tables (CMHC starts/completions)

Source: `data/staging/ontario_canada_starts_completions.csv` -> `warehouse.fact_starts_completions`
Checked: 2026-10-15

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
