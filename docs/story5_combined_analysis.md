# Story 5: Combined Analysis

**Question:** How do affordability, rental conditions, and supply fit together?
**Dashboard:** Superset dashboard 8, embedded on the React Story 5 page.
**Status:** replaces the earlier Story 5, which put one conclusion from each story side by side without joining any data (decision D20, superseded by D32).

## Why this story exists

Stories 1 to 4 each answer a question from one dataset. The supervisor's feedback was that they read as four separate projects. Story 5 joins the datasets, so each result needs data from **two** stories and could not come from either one alone.

The datasets share three keys:

| Key | Shared by |
|---|---|
| **Renter** (tenure) | Story 1 shelter-cost table, Story 2 rental survey |
| **City** (CMA) | Story 1 Census tables, Story 3 construction, Story 4 comparison cities |
| **Year** | Story 2 rental survey (October), Story 3 construction (calendar year) |

## Data added

Stories 1 and 3 used only Windsor's rows. The same StatCan files also cover the four comparison cities Story 4 uses (London, Hamilton, Kitchener-Cambridge-Waterloo, St. Catharines-Niagara), so questions 1–5 needed no new download. Question 6 (young renters) adds one new Census table, 98-10-0241-01, and question 7 adds CMHC's rental workbooks for the four comparison cities (Windsor's was already loaded).

`etl/extract_peer_cma_context.py` takes the five cities' rows from:

| File | What is kept |
|---|---|
| 98-10-0252-01 (shelter cost by income and tenure, 2021 Census) | renter households by $10,000 income band, median renter household income, renters spending 30%+ |
| 98-401-X2021002 (Census Profile 2021) | population in 2016 and 2021, private households and the people in them, renter households, % of tenants spending 30%+, median household income, median rent paid |
| 34-10-0154-01 (monthly starts and completions) | yearly starts and completions, all homes and apartments, full years 2016 to 2025 |
| 98-10-0241-01 (housing indicators by age of primary household maintainer, 2021 Census; **new**, downloaded on first run) | households and households spending 30%+ on shelter, by age group, for renters and all households |
| CMHC Rental Market Survey, October 2025, one workbook per city (**new** for the 4 comparison cities, downloaded on first run) | Table 3.1.3: purpose-built rental units (apartments and row houses, all unit sizes), October 2024 and 2025 |

Cities are matched by the CMA code at the end of each DGUID (559 = Windsor), because each file spells city names differently. The rows load into `warehouse.fact_peer_cma_context` (780 rows), which has one row per city, source, indicator and breakdown. Windsor's rows match Stories 1 and 3 exactly; for example, 34.8% of tenants spending 30%+, and 1,262 starts and 1,671 completions in 2025.

## The combined views (`sql/story5_views.sql`)

| View | Joins | Key |
|---|---|---|
| `v_story5_rent_affordability` | Story 1 renter incomes x Story 2 average rents | Windsor renters |
| `v_story5_peer_affordability` | Story 1 incomes and burden (all 5 cities) x Story 4 2-bedroom rents | City |
| `v_story5_supply_vs_rental_market` | Story 3 completions x Story 2 vacancy and rent | Year (2020-2025) |
| `v_story5_peer_construction` | Story 3 construction (all 5 cities) x Census households | City and year |
| `v_story5_supply_vs_demand` | Story 3 completions (all 5 cities) x Census population growth 2016-2021 | City |
| `v_story5_renter_burden_by_age` | Census renters by age (98-10-0241-01) x Story 1's burden measure x Story 4 cities | City and age group |
| `v_story5_rental_stock` | CMHC purpose-built rental units (all 5 cities) x Census renter households | City |
| `v_story5_city_profile` | Every measure above plus Story 4's vacancy, one row per city | City |

**Can-afford rule.** A rent is affordable to a household whose income is at least rent x 12 / 0.30, the standard 30% rule.

**Counting renters below an income.** Incomes are published in $10,000 bands. Every band entirely below the income needed is counted in full. For the one band containing it, households are assumed to be spread evenly across the band (linear interpolation).

## Findings

### 1. Can Windsor renters afford the rent? (Story 1 + Story 2)

| Unit size | Average rent (Oct-25) | Income needed | Renters who earn less |
|---|---|---|---|
| Studio | $948 | $37,920 | 36.8% |
| 1 bedroom | $1,193 | $47,720 | 49.1% |
| 2 bedroom | $1,451 | $58,040 | 60.7% (27,664 households) |
| All unit sizes | $1,293 | $51,720 | 53.8% |

The median renter household earned $48,400, so about **61% of Windsor renters cannot afford an average 2-bedroom**, and about half cannot afford a 1-bedroom. (Rents are for apartments and row houses. CMHC does not publish 3-bedroom rent for Windsor.)

### 2. Is Windsor affordable, or only cheap? (Story 1 + Story 4)

| City | 2-bed rent | Median renter income | Rent % of income | Cannot afford 2-bed | Tenants spending 30%+ |
|---|---|---|---|---|---|
| Windsor | $1,454 | $48,400 | 36.0% | 60.8% | 34.8% |
| St. Catharines-Niagara | $1,527 | $48,000 | 38.2% | 63.2% | 39.5% |
| London | $1,651 | $51,200 | 38.7% | 64.9% | 38.4% |
| Hamilton | $1,656 | $55,200 | 36.0% | 59.9% | 39.0% |
| Kitchener-Cambridge-Waterloo | $1,832 | $60,000 | 36.6% | 61.9% | 36.9% |

Windsor has the lowest rent, but its renters have the second-lowest incomes. Rent takes 36% of the median renter's income, the same as Hamilton and close to every other city, and about 6 in 10 renters cannot afford a 2-bedroom in each city. **Windsor is cheap, not more affordable.** Its share of tenants spending 30%+ on shelter is still the lowest of the five.

### 3. Did new homes ease the rental market? (Story 3 + Story 2)

| Year | Completions (apartments) | Vacancy (Oct) | Rent increase |
|---|---|---|---|
| 2020 | 1,391 (436) | 3.5% | |
| 2021 | 1,069 (229) | 3.4% | 10.9% |
| 2022 | 1,131 (288) | 1.8% | 2.5% |
| 2023 | 1,967 (1,162) | 2.1% | 4.3% |
| 2024 | 1,609 (939) | 3.2% | 8.1% |
| 2025 | 1,671 (1,095) | 3.6% | 5.9% |

- **2021–2022:** few homes were finished, and vacancy fell to its low of 1.8%.
- **From 2023:** completions surged, led by apartments. Vacancy rose back to 3.6% by 2025, and rent growth slowed from 8.1% in 2024 to 5.9%.

The timing is consistent with new homes loosening the market. It does not prove cause (see limitations).

### 4. Is Windsor building as much as its peers? (Story 3 + Story 4)

Average homes started a year per 1,000 households, 2016 to 2025:

| City | Starts a year per 1,000 households |
|---|---|
| Windsor | 8.4 |
| Hamilton | 10.9 |
| St. Catharines-Niagara | 13.4 |
| London | 16.1 |
| Kitchener-Cambridge-Waterloo | 19.7 |

- In every year except 2024, Windsor built less than even the lowest of the four comparison cities.
- In 2024 it reached 13.0, matching their average that year (13.2).
- In 2025 it fell back to 7.6.

### 5. Did building keep up with population growth? (Story 3 + Census population)

Homes needed = population growth between the 2016 and 2021 Censuses / people per private household (2021). Homes built = completions in calendar 2016-2020, the five full years closest to the Census interval (May 2016 to May 2021).

| City | Population growth | People per household | Homes needed | Homes completed 2016-2020 | Built per home needed |
|---|---|---|---|---|---|
| Windsor | 23,912 (6.0%) | 2.51 | 9,534 | 5,666 | **0.59** |
| London | 49,482 (10.0%) | 2.41 | 20,525 | 14,753 | 0.72 |
| Hamilton | 37,639 (5.0%) | 2.52 | 14,958 | 12,599 | 0.84 |
| St. Catharines-Niagara | 27,530 (6.8%) | 2.37 | 11,596 | 9,846 | 0.85 |
| Kitchener-Cambridge-Waterloo | 51,953 (9.9%) | 2.59 | 20,034 | 18,255 | 0.91 |

Every city built fewer homes than its population growth needed, but **Windsor fell furthest short: 0.59 homes per home needed, a gap of about 3,900 homes**. Windsor grew about as fast as Hamilton and St. Catharines-Niagara, so its slow building (section 4) is not explained by slow growth. The shortfall is consistent with vacancy falling to 1.8% in 2022 (section 3).

### 6. Can young renters and students afford to rent? (Census renters by age + Story 1 + Story 4)

Renter households by the age of the person who maintains them, and the share spending 30% or more of income on shelter (Story 1's measure), 2021 Census:

| City | Renters aged 15–24 | Of them, spending 30%+ | All renters spending 30%+ | Gap (points) |
|---|---|---|---|---|
| Windsor | 2,680 | **46.5%** | 34.8% | +11.7 |
| St. Catharines-Niagara | 2,835 | 50.6% | 39.5% | +11.1 |
| Kitchener-Cambridge-Waterloo | 6,775 | 54.7% | 36.9% | +17.8 |
| London | 6,690 | 54.8% | 38.4% | +16.4 |
| Hamilton | 4,605 | 55.3% | 39.0% | +16.3 |

In Windsor, renters aged 15–24 are the **most burdened age group**: 46.5% spend 30%+ on shelter, against 29.4% at 35–44 and 44.9% at 85 and over (a U-shape across ages). Young renters are worse off than other renters in every city, but Windsor's are the least burdened of the five, in line with its lower rents.

The rents they face (section 1): an average studio ($948 a month) needs about $37,900 a year under the 30% rule, and a 1-bedroom ($1,193) about $47,700.

**What this does and does not cover.** The Census counts students who head their own rented household (including shared houses). It leaves out students in residence or living with their parents, and the May 2021 Census fell in an online term, when many students were away. CMHC's core-housing-need measure is in the same table but is not used: it leaves out non-family households with a maintainer aged 15–29 attending school, so it understates need among students.

### 7. How big is the rental market, and how do the cities compare overall? (CMHC rental units + Census renters, then every measure)

Purpose-built rental units (apartments and row houses, October 2025) against renter households (2021 Census):

| City | Rental units | Renter households | Units per 100 renters |
|---|---|---|---|
| St. Catharines-Niagara | 17,078 | 51,210 | 33.3 |
| **Windsor** | **19,883** | **45,625** | **43.6** |
| Hamilton | 47,799 | 96,600 | 49.5 |
| Kitchener-Cambridge-Waterloo | 42,911 | 77,470 | 55.4 |
| London | 53,617 | 83,170 | 64.5 |

Windsor has about **44 purpose-built rental units for every 100 renter households**, the second-lowest of the five. So roughly **half or more of Windsor's renters** live in rented houses, condos, basements and other units that CMHC's rental survey does not cover. Story 2's rents and vacancy rates describe only that purpose-built part of the market.

**Does a tighter market mean more pressure?** Not across these cities. October 2025 vacancy barely differs (3.6% to 4.1%), and Windsor's market is nearly as tight as Hamilton's (3.7% against 3.6%) yet has the lowest share of renters spending 30%+ (34.8% against 39.0%). The differences between cities come from incomes (section 2), not from vacancy. With five cities this is an observation, not a tested relationship.

The dashboard ends with one table that puts every measure for the five cities side by side: rent, vacancy, rental units per 100 renters, median renter income, rent as a share of income, renters and young renters spending 30%+, starts per 1,000 households, and the share of needed homes built.

### Together

- **Renters:** Windsor's low rents reflect low renter incomes, so most renters still cannot afford an average 2-bedroom.
- **Recent completions:** the 2023–2025 surge coincided with a looser market.
- **Building:** Windsor builds more slowly than any comparison city and, from 2016 to 2021, finished only 0.59 homes for every home its population growth needed. New supply is unlikely to keep easing rents without more construction.
- **Young renters:** nearly half of renter households aged 15–24 spend 30% or more on shelter, the highest of any age group, although less than in the comparison cities.
- **Rental market:** purpose-built rentals house at most about half of Windsor's renters, so the rest of the market is outside CMHC's survey.

## Dashboard

| Part | What it shows |
|---|---|
| KPI cards | 61% (cannot afford a 2-bed), 36% (rent share of income), 5,247 (homes completed 2023–2025), 8.4 (starts per 1,000 households) |
| Section 1 | Bar chart by unit size, plus a table of rent, income needed and renters below |
| Section 2 | Two city bar charts (rent share of income; tenants spending 30%+), plus a comparison table |
| Section 3 | Completions by year (apartments and other homes), with vacancy and rent increase by year |
| Section 4 | Starts per 1,000 households by city, plus Windsor against the comparison-city average by year |
| Section 5 | Homes completed per home needed by city, plus homes needed against homes completed |
| Section 6 | Young renters against all renters spending 30%+, by city, plus Windsor renters by age |
| Section 7 | Rental units per 100 renter households by city, plus one table with every measure for the five cities |
| Interaction | A **Years** range filter narrows sections 3 and 4; the KPI cards stay fixed |

Windsor is blue and the comparison cities grey throughout. Each section ends with a note stating the finding in words.

## Limitations

- **Income year:** incomes are for 2020 (2021 Census) and rents for 2025. Incomes have risen since, so the shares who cannot afford a rent are an upper bound.
- **Income bands:** households are assumed evenly spread within the $10,000 band that contains the income needed.
- **What each count covers:** completions include condos and homes for sale, while vacancy covers purpose-built rentals only. Section 3 therefore shows timing, not cause.
- **Rent type:** the city comparison uses apartment rents only, the only comparison CMHC publishes. Windsor's own figures include row houses ($1,451 against $1,454 for a 2-bedroom).
- **Household counts:** "per 1,000 households" uses the 2021 household count for every year.
- **Rental stock:** section 7 compares units counted in 2025 with households counted in 2021, and some units are vacant, so the share of renters outside purpose-built rentals is an estimate.
- **Young renters:** section 6 counts only students who head their own rented household; see the note in section 6.
- **Homes needed:** section 5 applies 2021 household sizes to the whole 2016-2021 growth. Completions are not net of demolitions, and calendar 2016-2020 only approximates the May-to-May Census interval. The ratios are estimates; the ranking between cities is the reliable part.

## Reproducing

```
.venv\Scripts\python.exe etl\extract_peer_cma_context.py
.venv\Scripts\python.exe etl\refresh_all.py          # loads fact_peer_cma_context, applies story5_views.sql
.venv\Scripts\python.exe etl\build_story5_dashboard.py
.venv\Scripts\python.exe etl\apply_dashboard_theme.py
```

The figures in the dashboard notes and on the React page are written out by hand. Re-check them against the views after a data refresh.
