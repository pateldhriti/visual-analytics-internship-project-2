# Shelter-Cost Dataset Audit — Windsor CMA

**Source:** Statistics Canada table 98-10-0252-01, "Shelter-cost-to-income ratio by tenure" (2021 Census). Confirmed via `data/raw/shelter_cost/98100252_MetaData.csv` (Product Id `98100252`).
**Geographic scope:** Windsor (CMA), Ont. only — DGUID `2021S0503559`, extracted from a national bulk CSV covering 166 geographies.
**Extraction:** `etl/extract_windsor_shelter_cost.py`, chunked read (150k rows/chunk, `utf-8-sig`, all columns as `str` to preserve published values exactly) of the 1.28 GB / 5,019,840-row source. Source file verified unmodified after extraction (same size/timestamp).
**Output:** `data/staging/windsor_shelter_cost.csv` — **30,240 rows**, 16 columns.

## Dimension mappings (four assigned dimensions)

| Dimension | Column | Categories |
|---|---|---|
| Household total income groups | `Household total income groups (14)` | 14: Total + 11 income brackets + **Median ($)** + **Average ($)** (the latter two are dollar statistics, not counts) |
| Household type incl. census family structure | `Household type including census family structure (16)` | 16 real categories, but only **14 distinct text labels** — see label collision below |
| Tenure | `Tenure (3):Total - Tenure[1]` / `Owner[2]` / `Renter[3]` (+ paired `Symbol`/`Symbol.1`/`Symbol.2`) | Pivoted into **3 columns**, not rows |
| Shelter-cost-to-income ratio | `Shelter-cost-to-income ratio (5)` | 5: Total, <30%, ≥30%, "30% to <100%" (child of ≥30%), Not applicable |

**Household-type label collision:** two household-type member IDs (5 and 10, and similarly another pair) render as the identical text "Without children" / "With children" under different family-structure branches. Confirmed via the `Coordinate` column, which encodes true StatCan member IDs. Grouping by the text column alone silently merges these into 2 categories instead of 16 — `Coordinate` must be used to disambiguate.

## Additional dimensions in the source (not assigned, but affect row count)

- **Housing suitability (3)** and **Dwelling condition (3)** — each Total + 2 detail categories.
- **Statistics (3C)** — point estimate ("Number of private households") plus 95% CI lower/upper bounds; only the point estimate should be used for counts.

## Row-count discrepancy (Phase 4): 2,389 (proposal) vs 30,240 (verified)

**Explained and confirmed against the actual data:** 30,240 = 14 (income) × 16 (household type, by real member ID) × 3 (suitability) × 3 (dwelling condition) × 3 (statistics) × 5 (ratio) — the full cross-product, with tenure pivoted into columns. Verified via `Coordinate` member-ID segments, not metadata counts alone, after a naive text-label check first (wrongly) produced 26,460 due to the label collision above. The proposal's 2,389 figure was most likely generated from StatCan's web interface with a narrower dimension selection (e.g., point-estimate statistic only, Total-only suitability/dwelling condition); the original selection was not available to confirm, so this remains a well-supported inference, not a certainty.

## Data-quality findings

- **Row counts:** 5,019,840 source rows (166 geographies) → 30,240 Windsor rows, confirmed independently by the extraction script's own tally.
- **Missing/blank values:** none found in the checked columns of the extract.
- **Special symbols** (per metadata's Symbol Legend — `x`=suppressed, `...`=not applicable, etc.): present only in the `Symbol`/`Symbol.1`/`Symbol.2` columns (210–396 non-null observation gaps per tenure column, all symbol-flagged, mostly `...` and `x`); never treated as zero.
- **Duplicates:** 0, keyed correctly by `Coordinate` (30,240 unique values for 30,240 rows). A first attempt using a text-label composite key falsely flagged 7,560 "duplicates" — an artifact of the household-type label collision, not real duplicate data.
- **Total/subtotal reconciliation (Tenure):** Owner + Renter vs Total-Tenure, restricted to the point-estimate statistic and excluding the Median/Average income rows (dollar values, not counts — their inclusion in a first pass produced mismatches up to 410,000, which is a methodological artifact, not a data error). Of 8,640 valid household-count rows, 6,123 reconcile exactly; the remaining 2,517 differ by a small amount (5–35, concentrated at 5), consistent with StatCan's random-rounding disclosure control for small census counts.
- **Total/subtotal reconciliation (Ratio):** for the Windsor-wide baseline (all totals), `<30% + ≥30% + Not applicable` = `Total` exactly (164,730). However, `"30% to less than 100%"` (26,210) does **not** equal its stated parent `≥30%` (28,745) — a gap of 2,535 with no published sibling category to account for it.

## Remaining uncertainties

1. The exact StatCan web-table selection behind the proposal's 2,389-row estimate is unconfirmed.
2. The relationship between `"30% to less than 100%"` and its parent `≥30%` category is incompletely documented in the metadata — unresolved.

## Reproducibility

- Script: `etl/extract_windsor_shelter_cost.py`
- Notebook: `notebooks/01_shelter_cost_exploration.ipynb` (all figures above generated live from the extract; re-run to verify)
