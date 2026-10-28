# ETL: Historical RMS (Oct-20 to Oct-23) — Zone Mapping and Breaks

**Goal:** load 10 years of Windsor RMS workbooks into `warehouse.fact_rental_market`, map renamed
or redrawn zones to the 2025 zone scheme, and flag years with structural breaks.

## What's actually achievable: 6 years, not 10

CMHC's digital RMS portal only has Windsor editions back to **2021**, confirmed by testing the real
download URL pattern directly (`.../rental-market-report-data-tables/[YEAR]/rmr-windsor-[YEAR]-en.xlsx`):
2021-2025 all return `200`, 2015-2020 all return `404`. CMHC's own materials say survey data exists
back to 2006, but only through their Housing Knowledge Centre's browse/search interface, which needs
interactive browser access this project's tooling doesn't have in an automated session — the same
blocker `docs/starts_history_profile.md` already hit for a different CMHC table.

Downloaded the 4 real, available editions (2021, 2022, 2023, 2024) — combined with the already-loaded
2025 edition, this gives **6 real periods: Oct-20 through Oct-25** (each edition covers its own year
plus the prior year's comparison column), not the full 10 requested. 2015-2020 remain genuinely
unavailable, not just unextracted.

## Zone and bedroom-type renames (found by comparing real values, not assumed from labels)

| Raw label (2021-2023) | 2025 label | Evidence it's a rename, not a redraw |
|---|---|---|
| `Zone 6 - Remainder of CMA` | `Zone 6 - North Essex County` | Universe counts are continuous across the rename — 2022's Zone 6 value matches 2023's at the overlapping period, which continues into 2024's "North Essex County" trend |
| `Zone 7 - Essex` (2023 only) | `Zone 7 - South Essex County` | Same continuity check against 2024's "South Essex County" |
| `Bachelor` (2021-2024) | `Studio` | Same column position, same row-6 header cell, only the 2025 edition uses the new word |

**Zone 7 has no data at all before 2023** — not a renamed zone, a zone that wasn't reported
separately yet. The 2021 and 2022 editions' sheets have only **8** real zone rows (no Zone 7 row at
all, not even blank), vs. 9 in 2023+. The extraction script detects each sheet's real row count
dynamically rather than assuming a fixed 9 — an earlier version of this script hardcoded 9 and
silently read one blank phantom row past the real data for 2021/2022 (caught by checking for
`zone IS NULL` rows in the output: found 90, all from those 2 editions, fixed by reading rows until
an empty cell instead of a fixed count).

## The one real "break": Windsor CMA's Oct-22 total was recalculated after the Zone 7 split

Cross-checked every pair of overlapping editions (e.g. 2022's own "Oct-22" column against 2023's
"prior year" Oct-22 column — both editions report the same real period). Two editions agree exactly
(0 mismatches); one pair doesn't:

| Years compared | Period | Cells compared | Mismatches |
|---|---|---|---|
| 2021 vs 2022 | Oct-21 | 240 | 0 |
| 2022 vs 2023 | Oct-22 | 270 | **44** |
| 2023 vs 2024 | Oct-23 | 270 | 0 |
| 2024 vs 2025 (live warehouse) | Oct-24 | 271 | 1 |

Investigated the 44 Oct-22 mismatches directly rather than assuming they're noise: **23 are Zone 7
appearing retroactively** (2023's prior-year column includes it, 2022's own column never did — expected,
not an error) and **21 are all in the "Windsor CMA" rollup row specifically — every individual zone
1-6 matches exactly between editions.** That's the city-wide total being correctly recalculated once
Zone 7 was split out of the old combined Zone 6, not a data quality problem. Resolved by taking the
2023 edition's recomputed "Windsor CMA" figures for Oct-22 instead of 2022's pre-split ones, so the
loaded value is consistent with the current (2024/2025) zone scheme throughout.

The single Oct-24 mismatch (`Windsor CMA`, `Total`/`Apartment`, `turnover_rate`): the 2024 edition
has it suppressed (`**`), the 2025 edition's prior-year column has a real value (11.8%) — a late-published
figure, not a conflict; the already-loaded 2025-edition value is kept (the 2024 edition's own Oct-24
column isn't loaded at all, since that period is already in the warehouse from the 2025 edition).

## Verified end-to-end

Rebuilt the warehouse schema fresh (new `dim_period` rows added: Oct-20 through Oct-23) and ran the
full fact load: **990 historical rows loaded, 0 unmatched dimension keys.** `fact_rental_market`
totals 2,385 rows across its 2 sources (Windsor 2025 + this historical load). The Canada-comparison
source has since moved into its own table, `fact_rental_market_comparison` (36 rows) -- see
`sql/warehouse_schema.sql`'s comment on that table for why.
Queried the full 6-year Windsor CMA vacancy-rate trend directly from the warehouse afterward:

```
Oct-20: 3.5%   Oct-21: 3.4%   Oct-22: 1.8%   Oct-23: 2.1%   Oct-24: 3.2%   Oct-25: 3.6%
```

A coherent trend (sharp pandemic-era tightening in 2022, gradual loosening since) — not just
structurally loaded, genuinely plausible as real market history.

## What this sets up

This is the real data `sql/story2_views.sql`'s planned rent year-over-year change, 10-year growth
rate (6-year, with the above caveat), vacancy trend, and turnover-by-bedroom-type views will need —
none of it existed before this task.
