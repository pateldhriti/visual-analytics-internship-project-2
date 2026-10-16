# Choosing Comparator CMAs — Justification

**Task:** pick 4–5 Ontario CMAs comparable to Windsor by size and market; confirm each has the same RMS 2025 tables; short justification.

**Chosen (4):** London CMA, Kitchener-Cambridge-Waterloo CMA, Hamilton CMA, St. Catharines-Niagara CMA.

An earlier version of this project's comparator set (`etl/extract_rms_canada_comparison.py`) used London, Kitchener-Cambridge-Waterloo, and Toronto. That set was built without checking either criterion this task actually asks for — size comparability wasn't verified against real population figures, and table availability was assumed rather than confirmed. This note redoes the selection against both, replacing it with the result.

## Step 1 — Size: real 2021 Census population, not estimated

Every Ontario CMA's population, queried directly from the Census Profile data already in this project (`data/raw/statcan/98-401-X2021002_English_CSV_data.csv`, characteristic 1, "Population, 2021") — the authoritative source, not a third-party estimate:

| CMA | Population | vs. Windsor (422,630) |
|---|---|---|
| **Windsor** | **422,630** | — |
| St. Catharines-Niagara | 433,604 | +2.6% |
| Oshawa | 415,311 | −1.7% |
| London | 543,551 | +28.6% |
| Kitchener-Cambridge-Waterloo | 575,847 | +36.3% |
| Guelph | 165,588 | −60.8% |
| Kingston | 172,546 | −59.2% |
| Greater Sudbury | 170,605 | −59.6% |
| Barrie | 212,856 | −49.6% |
| Hamilton | 785,184 | +85.8% |
| Brantford | 144,162 | −65.9% |
| Peterborough | 128,624 | −69.6% |
| Thunder Bay | 123,258 | −70.8% |
| Belleville-Quinte West | 111,184 | −73.7% |
| Ottawa-Gatineau | 1,488,307 | +252.2% |
| Toronto | 6,202,225 | +1,368.0% |

The field splits cleanly into three tiers: four CMAs within roughly ±36% of Windsor (St. Catharines-Niagara, Oshawa, London, Kitchener-Cambridge-Waterloo), a cluster of much smaller CMAs at 40–74% below Windsor's size, and two CMAs (Ottawa-Gatineau, Toronto) that are multiples larger. Toronto in particular is 14.7x Windsor's population — not a size peer by any reasonable reading, regardless of anything else about it.

## Step 2 — Table availability: confirmed against CMHC's own major-centres list, not assumed

The task asks to "confirm each has the same RMS 2025 tables" — i.e., does CMHC actually publish a full, multi-sheet Rental Market Report workbook for each candidate, the same kind Windsor has (29 sheets, per `docs/cmhc_rms_sheet_catalogue.md`), not just a single summary row in the national comparison table.

Checked against CMHC's own "Rental Market Reports — Major Centres" page. Ontario CMAs confirmed on that list: **Greater Toronto Area, Hamilton, Kitchener-Cambridge-Waterloo, London, Ottawa, St. Catharines-Niagara, Windsor**.

This immediately rules out **Oshawa** as a comparator, despite it being the single closest population match (−1.7%): Oshawa is not on CMHC's major-centres list, so there is no confirmed full RMS 2025 workbook for it — only the quarterly starts/completions table and some StatCan asking-rent figures include it, which is a different, thinner data product than what Windsor has. Picking it would have failed this task's own second criterion.

It also rules out every CMA in the "40–74% smaller" tier (Guelph, Kingston, Greater Sudbury, Barrie, Brantford, Peterborough, Thunder Bay, Belleville-Quinte West) on both criteria at once — none of them are size-comparable, and none are confirmed on the major-centres list either.

## Result: 4, not 5

Intersecting both criteria leaves exactly four CMAs: **London, Kitchener-Cambridge-Waterloo, Hamilton, St. Catharines-Niagara**. All four are real Ontario CMAs, all four are within a defensible size range of Windsor (closest: St. Catharines-Niagara at +2.6%; furthest: Hamilton at +85.8%, included because it's still an order of magnitude closer to Windsor than Toronto or Ottawa, and it's confirmed on the major-centres list), and all four are confirmed to have the same kind of full RMS 2025 workbook treatment Windsor does.

A genuine 5th candidate that passes both criteria does not exist in this dataset — the only other major-centres-confirmed Ontario CMAs are Toronto and Ottawa, and both fail size comparability outright (+1,368% and +252% respectively). Forcing a 5th pick would mean violating one of the two criteria the task itself sets. Four real, double-confirmed comparators is the honest result, not a shortfall.

## What changed in the codebase

- `etl/extract_rms_canada_comparison.py`: `CENTRES` updated to the 4 confirmed comparators (Toronto removed, Hamilton and St. Catharines-Niagara added). Re-run and verified: 40/40 expected rows extracted, 0 suppressed/null values, Hamilton and St. Catharines-Niagara figures spot-checked against the raw workbook cells directly.
- `sql/warehouse_seed_dimensions.sql`: `dim_zone`'s `comparator_cma` rows updated to match.
- Full pipeline re-verified end-to-end from a clean schema: `fact_rental_market` loads with 0 unmatched dimension keys across all 5 CMAs (Windsor + 4 comparators).
