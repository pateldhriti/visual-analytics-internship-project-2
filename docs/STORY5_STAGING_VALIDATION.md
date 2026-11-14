STORY5 STAGING STATUS: PASS

# Story 5 staging validation

Generated 2026-11-13 23:10 by `etl/validate_story5_staging.py` (43/43 checks passed).
Design: `docs/STORY5_CROSS_DATASET_AUDIT.md` (decision D1: Census 2021 + CMHC October 2021).

| Area | Check | Result | Detail |
|---|---|---|---|
| raw | raw files unchanged vs etl/raw_manifest.json (incl. Census ZIP, CMHC Canada 2025) | PASS |  |
| raw | raw files unchanged vs etl/raw_history_manifest.json | PASS | 7 files; changed=[] |
| raw | raw files unchanged vs etl/raw_canada_history_manifest.json | PASS | 6 files; changed=[] |
| files | 3 Story 5 staging files and the geography map exist | PASS | missing=[] |
| geography | map: cmhc_centre_name unique, required columns present | PASS | 43 map rows |
| geography | every source CMA label maps exactly once (none unmapped, none extra) | PASS | 43 source labels; unmapped=[] extra=[] |
| geography | deterministic rules only: exact-after-suffix or the 8 audited explicit lookups; DGUID/name/level match Census | PASS | bad=[]; explicit=8 |
| geography | boundary_changed_flag only on 'Belleville CMA' | PASS | ['Belleville CMA'] |
| geography | focus_peer flags exactly Windsor, London, Hamilton, Kitchener-Cambridge-Waterloo, Toronto | PASS | ['Hamilton', 'Kitchener-Cambridge-Waterloo', 'London', 'Toronto', 'Windsor'] |
| geography | no duplicate DGUID within any year/basis (history) or in the universe | PASS |  |
| geography | 36 safely matched CMA-level geographies for 2021 (CMHC Table 1.0 ∩ Table 5.0 ∩ Census) | PASS | T1.0 2021=36, matched=36 |
| geography | 42 CMA-level geographies on the 2021-census basis for 2022 (revised) and 2023-2025 | PASS | {2022: 42, 2023: 42, 2024: 42, 2025: 42} |
| geography | all 5 focus peers present every year 2019-2025, in the Census profile and the 2021 universe | PASS | missing=[] |
| history | years exactly 2019-2025 | PASS | [2019, 2020, 2021, 2022, 2023, 2024, 2025] |
| history | metrics exactly the 4 audited metrics | PASS | ['average_rent_2br', 'fixed_sample_rent_change_2br', 'turnover_rate', 'vacancy_rate'] |
| history | row count = 1,248 (36x4x3 + 36x4 + 42x4x4) | PASS | 1248 |
| history | geography basis by year (2019-21 pre_2021_census, 2023-25 2021_census) | PASS |  |
| history | 2022 keeps both bases: pre_2021 (edition 2022, current, not primary) and 2021_census (edition 2023, previous, primary) | PASS | pre=36 CMAs, revised=42 CMAs |
| history | exactly one primary row per CMA x year x metric | PASS | 1104 primary keys / 1104 keys |
| history | '**' -> NULL+suppressed, '++' -> NULL+change_not_significant; NULL iff not published; never zero-filled | PASS | {'published': 1213, 'suppressed': 27, 'change_not_significant': 8} |
| history | reliability codes in {a,b,c,d}; every published value carries one | PASS | {'a': 820, 'b': 211, 'c': 135, 'd': 47, nan: 35} |
| history | trend flags only on vacancy/turnover current-column rows, valid values | PASS | 535 trend values |
| history | source lineage complete and unique (workbook + cell) | PASS |  |
| history | ranges: rates 0-100, rents > 0, fixed-sample change -100..100 | PASS |  |
| history | every row re-read independently from its source cell (label, period header, value, marker, reliability, trend) | PASS | 1248 rows re-read; mismatches=[] |
| history | Windsor vacancy/2BR rent/turnover reconcile with validated windsor_rental_market_history.csv (value, basis, primary flag) | PASS | 24 comparisons; diffs=[] |
| history | 2025 rows reconcile with existing verified canada_rental_market_comparison.csv (Oct-25) | PASS | 168 comparisons; diffs=[] |
| statcan | characteristic IDs exactly the approved allowlist (19) | PASS | [] |
| statcan | geography grain: all 43 CMA-level geographies (41 CMA + 2 parts), nothing else | PASS | 43 geographies, 817 rows |
| statcan | no duplicate cma_dguid x characteristic_id | PASS |  |
| statcan | NULL iff status withholds the value (no zero-filling) | PASS | count {'published': 817}; rate {'published': 731, 'not_applicable': 86} |
| statcan | key fields published for every CMHC-matched geography (1414, 1416, 1490-1495, 243) | PASS | 42 geographies; unpublished=0 |
| statcan | every row reconciles cell by cell with the Census Profile ZIP | PASS | 817 rows; mismatches=[] |
| statcan | Windsor benchmarks: renters 45,625; renter share 27.5; tenant 30%+ 34.8; core need 20.3; median rented shelter cost 980 | PASS | 1416.count_total=45625, 1416.rate_total=27.5, 1492.count_total=34.8, 1493.count_total=20.3, 1494.count_total=980 |
| statcan | no renter-income field present or derived (income measures only all-tenure 243/244/252; no extra columns) | PASS |  |
| universe | 2021 only, edition 2021 Table 5.0 only (no 2020, no trend) | PASS |  |
| universe | coverage = the 36 CMA-level geographies of CMHC 2021 Table 1.0 | PASS | 36 rows |
| universe | Windsor Oct-2021 universe = 16,314 | PASS | [16314] |
| universe | scope/basis/warning columns fixed: row_and_apartment_3plus_private, pre_2021_census, severity 'material' | PASS |  |
| universe | every value re-read independently from Table 5.0 column 'Universe' (positive integers) | PASS | mismatches=[] |
| regression | existing verified staging outputs byte-identical to pre-Story-5 baseline | PASS | 6 files; changed=[] |
| regression | existing cleaning validation still passes | PASS | 63/63 |
| regression | existing Windsor history validation still passes | PASS | 21/21 |

## Benchmark values

Primary series, CMHC Table 1.0 (2BR rent $ / vacancy % / turnover %):

| CMA | 2019 | 2021 | 2025 |
|---|---|---|---|
| Windsor | 949 / 2.9 / 17.4 | 1,154 / 3.5 / 16.8 | 1,454 / 3.7 / 12.2 |
| London | 1,107 / 1.8 / 19.3 | 1,275 / 1.9 / 19.1 | 1,651 / 4.0 / 15.1 |
| Hamilton | 1,219 / 3.9 / 14.0 | 1,362 / 2.8 / 14.9 | 1,656 / 3.6 / 13.1 |
| Kitchener-Cambridge-Waterloo | 1,231 / 2.1 / 14.2 | 1,356 / 2.0 / 16.9 | 1,832 / 4.1 / 16.1 |
| Toronto | 1,562 / 1.5 / 9.5 | 1,679 / 4.6 / 14.4 | 2,046 / 3.0 / 8.7 |

Census 2021 (renters / renter share % / tenant 30%+ % / core need % / median rented shelter cost $) and CMHC Oct-2021 row+apartment universe:

| CMA | Renters | Share | 30%+ | Core need | Median shelter cost | Universe 2021 |
|---|---|---|---|---|---|---|
| Windsor | 45,625 | 27.5 | 34.8 | 20.3 | 980 | 16,314 |
| London | 83,170 | 37.4 | 38.4 | 21.4 | 1,110 | 51,431 |
| Hamilton | 96,600 | 31.4 | 39.0 | 26.1 | 1,210 | 47,666 |
| Kitchener-Cambridge-Waterloo | 77,470 | 35.4 | 36.9 | 19.0 | 1,300 | 39,539 |
| Toronto | 789,545 | 34.9 | 40.5 | 28.7 | 1,540 | 327,970 |

## Caveats carried forward (audit D2/D3)

- CMHC 2019-2021 and the 2022 `pre_2021_census` rows use 2016-census CMA boundaries; Census 2021 and CMHC 2022 (revised)-2025 use 2021-census boundaries. Do not draw a continuous line across 2021->2022 except on `is_primary_series = true`, flagged as a basis change.
- `canada_cma_rental_universe.csv` is Oct-2021 row + apartment on 2016-census boundaries and carries `boundary_mismatch_severity = 'material'` and `count_ratio_warning`. No ratio is computed at staging.
- `Belleville CMA` (2019-2022) and `Belleville - Quinte West CMA` (2023+) share DGUID 2021S0503522; the old name is flagged `boundary_changed_flag = true`.
- Ottawa - Gatineau is represented only by its two CMA parts; the whole-CMA Census row has no CMHC match.
- The Census Profile has no renter-income field; none is derived.
