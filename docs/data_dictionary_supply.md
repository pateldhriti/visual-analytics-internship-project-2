# Data Dictionary — Supply Tables

Every column kept by `etl/extract_cmhc_starts_completions.py`, the CMHC starts/completions extraction. Source workbook profiled in `docs/cmhc_starts_completions_audit.md`.

**Pipeline stage this covers:** `data/raw/cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx` → `data/staging/ontario_canada_starts_completions.csv` (6 columns, melted from Tables C1 and C2's wide layout).

**Status note:** there is currently no `warehouse.fact_starts_completions` table on `main` to extend this dictionary into — one existed briefly earlier in this project's history but was removed along with other work during a history rewrite. The 6 columns below are what's real right now: the staging CSV's own columns. If/when a warehouse table is rebuilt for this source, this dictionary should be extended to cover its resolved dimension keys too, not just replaced.

| Column | Meaning | Unit | Source |
|---|---|---|---|
| `period_type` | Which of the workbook's two period framings this row is: `quarter` (a single current-quarter snapshot, Table C1) or `ytd` (year-to-date cumulative, Table C2). Not a real calendar period itself — see `period_label` for that. | categorical: `quarter` \| `ytd` | Derived — assigned by the extraction script per source sheet, not a column in the raw workbook. |
| `period_label` | The actual period this row covers, in CMHC's own wording. | text, e.g. `"Second Quarter 2026"`, `"January to June 2026"` | Table C1/C2 title cell (row 3 of each sheet). |
| `activity` | Which construction-activity stage this row measures. | categorical: `Starts` \| `Completions` \| `Under Construction` | Table C1/C2, "Activity" column (column A). Note: the `ytd` period only has `Starts` and `Completions` rows — `Under Construction` is a stock metric that doesn't accumulate year-to-date, so CMHC's own Table C2 has no row for it (not a gap in this extraction). |
| `province` | Geography the row covers. | categorical: `Ontario` \| `Canada` | Table C1/C2, "Province" column (column B). This workbook has no CMA-level rows at all — see the audit note for why Windsor can't appear here. |
| `dwelling_type` | Structural dwelling-type category. | categorical: `Singles` \| `Semis` \| `Row` \| `Apartment and Other` \| `Total` | Table C1/C2's 5 dwelling-type columns, melted from wide to long (one output row per dwelling type per source row). `Total` is CMHC's own published aggregate row, kept explicitly rather than dropped or recomputed. |
| `units` | The actual count: number of dwelling units for this (period × activity × province × dwelling_type) combination. | count (whole dwelling units) | Table C1/C2's numeric cells under each dwelling-type column. |

## What's deliberately not kept

- **Reliability/quality markers** — this workbook's Coverage and Geography / Concepts and Definitions sheets don't publish a reliability letter per cell (unlike the CMHC Rental Market Survey tables), so there's nothing to carry through here.
- **Tables C3/C4 (Intended Market: Homeownership/Rental/Condo/Co-op)** — profiled in the audit note, but not yet part of this extraction's scope. A different classification axis from dwelling type; would need its own columns if added later, not folded into `dwelling_type`.
- **Any geography besides Ontario and Canada** — the workbook only publishes those two; there's nothing else to keep.
