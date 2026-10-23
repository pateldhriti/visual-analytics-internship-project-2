# Affordability-Gap Index — Method Note

## Definition

**Affordability-Gap Index (AGI)** = Rent Growth Rate − Renter Income Growth Rate, over the same period.

- **AGI > 0**: rents are growing faster than renter incomes — the affordability gap is widening.
- **AGI ≈ 0**: rents and renter incomes are growing at roughly the same pace — the gap is stable.
- **AGI < 0**: renter incomes are growing faster than rents — the gap is narrowing.

This is a simple spread, not a ratio or index number normalized to a base period (e.g. 100). A spread was chosen over a ratio because it reads directly in percentage points — "rents outpaced renter income growth by 2.1 points" — without requiring a base-year choice, and because CMHC's own rent-growth figures (below) are already percentages, not re-based index values.

## Rent Growth component — real, computed from this project's data

Rent growth uses CMHC's own "Percentage Change of Average Rent, Two Bedroom, From Fixed Sample (Existing Structures Only)" figure (Table 1.0 of the national RMS workbook, `etl/extract_rms_canada_comparison.py`), Oct-24 → Oct-25. This is CMHC's matched-sample methodology — it holds the building sample fixed year over year, so it isolates actual rent growth from composition effects (new, typically pricier, construction entering the average). A naive `(rent_2025 - rent_2024) / rent_2024` on the raw average-rent figures would NOT isolate the same thing and would read differently — this note uses CMHC's own matched-sample number, not a recomputed one.

**Real values, Oct-24 → Oct-25** (from `data/staging/rms_canada_comparison.csv`, refreshed against the final comparator CMA list -- see `docs/comparator_cmas_justification.md`; this table originally listed Toronto, which was dropped from the comparator set the day after this note was first written):

| Market | Rent Growth |
|---|---|
| Hamilton CMA | 1.6% |
| Kitchener-Cambridge-Waterloo CMA | 3.3% |
| Windsor CMA | 3.6% |
| London CMA | 4.1% |
| St. Catharines-Niagara CMA | 5.5% |

Windsor's own RMS workbook (the Combined/Row+Apartment scope, not just apartments) does **not** have a rent-growth figure loaded in this project — Tables 1.1.5/2.1.5/3.1.5 (the percentage-change-of-rent sheets) were deliberately excluded from `etl/extract_windsor_rms.py`'s scope (see `docs/cmhc_rms_sheet_catalogue.md`'s recommendation). The 3.6% above is Windsor's apartment-only figure from the national comparison table, used here because it's the only rent-growth number currently extracted for Windsor on a basis comparable to the 4 comparator CMAs (also apartment-only, from the same table). If Windsor's Combined-scope rent growth is needed later, it requires extracting Table 3.1.5, which is a small follow-on to the existing RMS extraction pattern.

## Renter Income Growth component — NOT available from current project data

**This is the real limit on testing this index right now.** No source this project has extracted contains a renter-income time series:

- The Census Profile (`fact_census_profile`, StatCan 98-401-X2021002) has exactly one reference year of household income (2020, as reported in the 2021 Census) — a single point, not two points to compute growth from. It also isn't renter-specific; it's household income regardless of tenure.
- CMHC's Table 3.1.8 (loaded into `fact_rental_market` as `quintile_universe`/`quintile_vacancy_rate`) uses renter-household income quintile *thresholds*, not a growth series. Its own footnote says those thresholds are "derived from Census 2021 and increased according to provincial median weekly wage growth over the corresponding period" — which tells us CMHC itself proxies renter income growth with **provincial median weekly wage growth**, but that wage-growth series itself was never extracted into this project; only the already-escalated dollar thresholds are in the data.
- The shelter-cost table (`fact_shelter_cost`, StatCan 98-10-0252-01) is also single-year (2021 Census), with income *brackets* (counts of households per bracket), not a time series either.

**What would close this gap**: StatCan's median employment/total income tables are published annually (e.g., table 11-10-0239-01, Economic characteristics, by tenure) and would give an actual renter-income growth rate comparable in cadence to CMHC's annual RMS rent figures. Alternatively, Ontario's provincial median weekly wage growth (the series CMHC's own methodology references) could serve as the proxy CMHC itself uses, applied uniformly across markets — a coarser but immediately obtainable substitute, at the cost of losing any real cross-market variation in income growth (every market would get the same income-growth number, so AGI differences between markets would come entirely from the rent side).

## What "testing the index" actually produced

Because the income-growth component isn't available, the index **cannot be computed as a single number yet** for Windsor or any comparator. What can be reported honestly:

- Real, verified rent-growth ranking: Hamilton (1.6%) < Kitchener-Cambridge-Waterloo (3.3%) < Windsor (3.6%) < London (4.1%) < St. Catharines-Niagara (5.5%).
- If renter income growth turns out to be roughly uniform across these markets (plausible if using a shared provincial-wage-growth proxy, since Windsor and all 4 comparators are Ontario CMAs), then the *relative ranking* of the AGI across markets would mirror the rent-growth ranking above — St. Catharines-Niagara would show the widest gap, Hamilton the narrowest. This is a reasonable directional read, not a computed index value.
- No absolute AGI value (e.g. "Windsor's gap is +1.8 points") can be stated as real data — anything of that form in this project before now would be fabricated, not measured.

## Recommendation

1. Treat this method note as the index definition, not a finished computation.
2. Next real step: extract a renter/household income growth series (StatCan table 11-10-0239-01 or similar) at a cadence comparable to the RMS data, following the same extract → reshape → load pattern as the other sources in this project.
3. Once that exists, AGI becomes a one-line calculation (`rent_growth - income_growth`) per market per period, addable to `fact_rental_market` or a derived view rather than a new fact table.
