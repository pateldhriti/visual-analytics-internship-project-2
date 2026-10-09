# CMHC Windsor RMS 2025 — Sheet Catalogue

**Source file:** `data/raw/cmhc_rms/rmr-windsor-2025-en.xlsx` — CMHC Rental Market Survey, Windsor CMA, 2025 edition (data as of October 2025, compared to October 2024).
**29 sheets total**: 1 Table of Contents + 28 data tables, confirmed by reading the workbook directly (not assumed from the filename or any external description).

## Common layout template

Every data sheet (with the exceptions noted below) follows the same shape:

- **Title** in row 3 (or row 2 for a few tables — see exceptions), e.g. `"1.1.1 Private Apartment Vacancy Rates (%), by Zone and Bedroom Type - Windsor CMA"`.
- **Bedroom-type group header** one row above the column headers: `Studio | 1 Bedroom | 2 Bedroom | 3 Bedroom + | Total`, each spanning several sub-columns.
- **Column headers**: the row-dimension label in column A (`Zone`, `Year of Construction`, `Size`, or `Rent Quartiles` depending on the table) + `Oct-24` / `Oct-25` under each bedroom-type group.
- **Data cells**: most tables pair every numeric value with a **reliability letter** in the next cell (see legend below) — e.g. `4.8`, `d`. A suppressed cell shows `**` instead of a value, with no letter.
- **Footer legend**: geographic-definition note, Quality Indicators legend, Other Indicators legend, source line, copyright — present on every sheet, verified identical wording throughout.

### Reliability / quality markers (confirmed from the workbook's own legend, not guessed)

| Marker | Meaning |
|---|---|
| `a` | Excellent |
| `b` | Very Good |
| `c` | Good |
| `d` | Poor (use with caution) |
| `**` | Data suppressed (sample too small / confidentiality) |
| `↑` | Year-over-year change is a statistically significant **increase** |
| `↓` | Year-over-year change is a statistically significant **decrease** |
| `–` (en dash) | Sample doesn't allow interpreting the year-over-year change as significant |
| `++` | (Percentage-change-of-rent tables only) change in rent is not statistically significant |

**Universe (unit count) tables carry no reliability letters or suppression at all** — verified across every zone row in Table 1.1.3, not just a sample: raw counts are always plain numbers. This is a real structural difference from the rate/rent tables, not an inconsistency to flag as an error.

### Zones (7 + 2 aggregate rows, same set in every zone-based table)

Zone 1 - Centre, Zone 2 - East Inner, Zone 3 - East Outer, Zone 4 - West, **Windsor City (Zones 1-4)** [subtotal], Zone 5 - Amherstburg, Zone 6 - North Essex County, Zone 7 - South Essex County, **Windsor CMA** [grand total].

### Bedroom types

Studio, 1 Bedroom, 2 Bedroom, 3 Bedroom+, Total.

### Units by metric

Vacancy Rate / Turnover Rate / Percentage Change of Rent: **%**. Average Rent: **$**. Universe: **unit count** (integer).

### Dwelling-type sections

- **1.x** = Private Apartment only
- **2.x** = Private Row (Townhouse) only — heavily suppressed in Windsor (row housing is a small share of the rental stock; many zone × bedroom-type cells are `**`)
- **3.x** = Private Row (Townhouse) **and** Apartment combined — the full private rental market

## Full sheet catalogue

| Sheet | Row dimension | Column dimension | Special notes |
|---|---|---|---|
| Table 1.1.1 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Vacancy %, reliability letters + YoY trend |
| Table 1.1.2 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Average Rent $, reliability letters |
| Table 1.1.3 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Universe count — no reliability letters |
| Table 1.1.5 | Zone (9) | Bedroom type × Oct-23→24/Oct-24→25 | % change of rent; uses `++` not `–` for non-significant |
| Table 1.1.6 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Turnover %, reliability letters + YoY trend |
| Table 1.1.9 | Zone (9) | Bedroom type × Vacant/Occupied/Y-N | Rent of vacant vs occupied units + significance test; different column shape |
| Table 1.2.1 | Year of Construction (6) + Total | Bedroom type × Oct-24/Oct-25 | Windsor CMA only, no zone breakdown |
| Table 1.2.2 | Year of Construction (6) + Total | Bedroom type × Oct-24/Oct-25 | Average Rent $, Windsor CMA only |
| Table 1.2.3 | Year of Construction (6) + Total | Bedroom type × Oct-24/Oct-25 | Turnover %, Windsor CMA only |
| Table 1.3.1 | Structure Size (5) + Total | Bedroom type × Oct-24/Oct-25 | Vacancy %, Windsor CMA only |
| Table 1.3.2 | Structure Size (5) + Total | Bedroom type × Oct-24/Oct-25 | Average Rent $, Windsor CMA only |
| Table 1.3.3 | Zone (9) | **Structure Size** × Oct-24/Oct-25 | Dimensions flipped vs 1.3.1 — size is the column, zone is the row |
| Table 1.3.4 | Structure Size (5) + Total | Bedroom type × Oct-24/Oct-25 | Turnover %, Windsor CMA only |
| Table 1.4 | Rent Quartile (Q1-Q4) | Bedroom type × Oct-24/Oct-25 | Vacancy %, Windsor CMA only — affordability-adjacent |
| Table 2.1.1 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Row/Townhouse only — heavily suppressed |
| Table 2.1.2 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Row/Townhouse only — heavily suppressed |
| Table 2.1.3 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Row/Townhouse universe counts; many true zeros (small but real stock), not suppressed |
| Table 2.1.5 | Zone (9) | Bedroom type × Oct-23→24/Oct-24→25 | Row/Townhouse % rent change — almost entirely suppressed in the sample checked |
| Table 2.1.6 | Zone (9) | Bedroom type × Oct-24/Oct-25 | Row/Townhouse turnover — heavily suppressed |
| Table 2.1.9 | Zone (9) | Bedroom type × Vacant/Occupied/Y-N | Row/Townhouse — heavily suppressed |
| **Table 3.1.1** | Zone (9) | Bedroom type × Oct-24/Oct-25 | **Combined** vacancy % — full market |
| **Table 3.1.2** | Zone (9) | Bedroom type × Oct-24/Oct-25 | **Combined** average rent $ — full market |
| **Table 3.1.3** | Zone (9) | Bedroom type × Oct-24/Oct-25 | **Combined** universe counts — full market, no reliability letters |
| Table 3.1.5 | Zone (9) | Bedroom type × Oct-23→24/Oct-24→25 | Combined % rent change |
| **Table 3.1.6** | Zone (9) | Bedroom type × Oct-24/Oct-25 | **Combined** turnover % — full market |
| **Table 3.1.7** | Zone (9) | Bedroom type × Universe/Vacancy/Rent | **New rental stock only** (completed July 2022–June 2025), single period, no reliability letters visible in the data checked |
| **Table 3.1.8** | Zone × Income Quintile (81 rows) | Bedroom type × Universe/Vacancy | **Most complex sheet** — links renter household income quintile and the rent level "affordable" at 30% of that income to actual vacancy; direct bridge to Story 1 (shelter-cost burden) |
| **Table 3.1.9** | Zone (9) | Bedroom type × Vacant/Occupied/Y-N | **Combined** rent of vacant vs occupied + significance test |

## Recommended 8–10 sheets for this project's stories

The proposal's Story 2 ("What is happening in Windsor's rental market?") asks about rent, vacancy, rental stock and turnover by unit type and zone — and the combined Row+Apartment (3.1.x) tables are the right primary source for that, not the apartment-only or row-only sections, since they represent the actual full private rental market rather than an artificial split. Recommendation:

**Core Story 2 metrics (by Zone, combined dwelling types):**
1. **Table 3.1.1** — Vacancy Rates
2. **Table 3.1.2** — Average Rents
3. **Table 3.1.3** — Rental Universe (stock size)
4. **Table 3.1.6** — Turnover Rates
5. **Table 3.1.9** — Vacant vs Occupied Rents (market tightness signal)

**Bridges to other stories:**
6. **Table 3.1.8** — Income Quintile vs Affordable Rent vs Vacancy — the strongest direct link to Story 1's affordability work; worth prioritizing despite its complexity
7. **Table 3.1.7** — Profile of New Rental Stock — bridges to Story 3 (housing supply)

**Apartment-specific granularity** (apartments are the dominant, less-suppressed segment — row-housing tables are frequently `**` in this workbook):
8. **Table 1.1.1** — Apartment Vacancy (comparison cut)
9. **Table 1.1.2** — Apartment Average Rents (comparison cut)

**Optional 10th:**
10. **Table 1.4** — Vacancy by Rent Quartile — simpler affordability-adjacent complement to 3.1.8

**Excluded, with reason:** Section 2.x (row/townhouse-only — already represented in the 3.1.x combined tables, and too suppressed to stand alone); Year-of-Construction and Structure-Size cuts (1.2.x, 1.3.x — not asked for by the current story questions, available later if a supply-vintage story is added); the percentage-change-of-rent tables (1.1.5/2.1.5/3.1.5 — secondary/derived metric, not part of the core 4 asks).

## Open items / not yet done

- This catalogue documents structure, not values — no data has been extracted or loaded yet. That's a separate ETL task once the 8-10 sheet selection is confirmed.
- Table 3.1.8's 81-row zone × quintile structure will need its own parsing logic distinct from the other tables' simpler zone-only rows.
