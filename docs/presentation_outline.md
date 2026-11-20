# Final presentation: outline and speaker notes

The deck has 17 slides and runs about 15 minutes plus questions, with the live demo in the middle (about 4 minutes). Every number on the slides comes from [report_findings.md](report_findings.md); charts are the exported figures in [figures/](figures/). The demo path and fallback are in [demo_script.md](demo_script.md).

| Section | Slides | Time |
|---|---|---|
| Introduction | 1-3 | 2 min |
| Method | 4 | 1 min |
| Findings | 5-10 | 5 min |
| Product (demo, quality, deployment) | 11-13 | 5 min |
| Close | 14-17 | 2 min + questions |

Suggested speakers: Dhritiben (1-5), Romit (4, 6, 13), Pavan (7-10, 12), Charmiben (11, 14-17). Adjust as the team prefers.

## Slides

### 1. Windsor Housing Visual Analytics (cover)
Introduce the team and the project in one sentence: a public tool that explains housing affordability in Windsor from official open data, and shows how affordability, the rental market and new supply fit together.

### 2. Affordability in Windsor can't be read from one number
Affordability depends on three things that come from different sources: incomes (Census, every five years), rents (CMHC, every October) and construction (CMHC, every month). Nobody had put them side by side for Windsor in a form the public can use.

### 3. Each story answers one question
Stories 1 to 4 were first built separately, one dataset each. The supervisor pointed out they read as four projects, so Story 5, the Combined Analysis, joins their data: for example renter incomes against rents, or construction against population growth.

### 4. From 27 government files to one source of truth
The pipeline: download, check each file's structure, extract and reshape, load a star-schema warehouse, then build the dashboards and the website from the same views. Three choices made it reliable: one definition per measure, dashboards built by script rather than by clicking, and a guard that stops any load when a source changes format.

### 5. Story 1: Renters, especially low-income renters, face the most pressure
- **Figure:** fig01.
- **Notes:**
  - A third of renter households spend 30% or more of income on shelter, three times the owner rate.
  - Burden falls steeply with income: 89% of renters under $10,000, under 2% from $100,000.
  - We validated our calculation against Statistics Canada's own published rates: 34.8% and 10.9%, a difference of zero.

### 6. Story 2: Easier to find an apartment, but not cheaper
- **Figures:** fig03 (vacancy) and fig04 (2-bedroom rent).
- **Notes:**
  - Vacancy hit a very tight 1.8% in 2022 and recovered to 3.7%, but rent kept rising every year: 53% since 2019, from $949 to $1,454.
  - New tenants pay about $200 more than sitting ones for a 2-bedroom.
  - The units the lowest-income fifth of renters can afford are the scarcest, at 2.3% vacant.

### 7. Story 3: Construction peaked in 2024 and is slowing
- **Figures:** fig07 (starts and completions) and fig09 (2026 by intended market).
- **Notes:**
  - Starts surged to 2,157 in 2024 and fell back to 1,262 in 2025; January to September 2026 is 21% behind the same months of 2025.
  - The 590 rental homes completed this year were started two to three years ago.
  - Only 277 rental homes have started this year, so rental supply will thin out.

### 8. Story 4: Still the cheapest, but rents are catching up fastest
- **Figure:** fig10 (rent indexed to 2019).
- **Notes:**
  - Windsor's 2-bedroom rent, $1,454, is the lowest of the five Ontario cities.
  - Its rent has risen 53% since 2019, more than London, Kitchener-Waterloo, Hamilton or Toronto (31%).
  - Vacancy moved the same way everywhere: lowest in 2021 to 2023, higher again by 2025.

### 9. Story 5: Windsor is cheaper, not more affordable
- **Slide type:** a statement slide with no chart.
- **Notes:**
  - Joining Census renter incomes with CMHC rents (apartments and row houses) shows the average 2-bedroom, $1,451, needs about $58,000 a year. 61% of Windsor renter households earn less.
  - A 2-bedroom takes 36% of the median renter's income ($48,400), the same share as Hamilton. Lower rents are matched by lower incomes.

### 10. Story 5: Not enough was built, and the pressure is growing
- **Figures:** fig13 (homes needed against homes completed) and fig14 (2030 scenarios).
- **Notes:**
  - Windsor completed 5,666 of the roughly 9,534 homes its 2016-2021 population growth needed: 59%, the lowest of the five cities.
  - If rents keep their 2020-2025 pace while incomes grow 3% a year, the share of renters priced out of a 2-bedroom rises from 52% to 63% by 2030.
  - The share rises in all six scenarios we tried, to between 51% and 68%. Say clearly that these are scenarios, not forecasts.

### 11. Live demo
Switch to the browser:
1. Open the home page.
2. Open a story page.
3. Change a filter so everyone sees the charts update.
4. Finish on Combined Analysis.

If the network or the university login fails, play the backup recording (3 min 35 s).

### 12. How we know it works
- 224 automated tests run on every pull request.
- A schema guard checks all 27 source files before loading.
- The nightly backup restored in full (18 tables, 59 views).
- Median page time stayed under 0.1 s with up to 10 visitors at once.
- The live site has 0 automated accessibility violations.
- All 38 dashboard tabs fit on one screen. See [load_test_results.md](load_test_results.md) and [accessibility_mobile_check.md](accessibility_mobile_check.md).

### 13. Running on the university's servers
- The warehouse is on the department's PostgreSQL server.
- The dashboards are on the shared Superset 6 server.
- The website runs on our own server behind nginx with HTTPS.
- A nightly backup and an uptime check every five minutes keep it running.
- The site links to the dashboards rather than embedding them because the shared server requires a university login.

### 14. Three lessons
1. **One definition per measure.** Early on, two dashboards disagreed about the same year's rent.
2. **Dashboards as code.** Moving to the university server was a rebuild, not a redo.
3. **Check data before loading.** CMHC and Statistics Canada change file layouts and revise earlier years.

### 15. What the data cannot tell us yet
- **Limitations:**
  - Incomes are from 2020 while rents run to 2025, so today's gap is probably wider.
  - The rents cover purpose-built rentals only.
  - Some CMHC files must be downloaded by hand.
  - The dashboards need a login, so the site links to them.
- **Future work:**
  - 2026 Census incomes.
  - Yearly tax-filer incomes.
  - Public, embeddable dashboards.
- **Detail:** [report_limitations_future_work.md](report_limitations_future_work.md).

### 16. Who built what
- **Dhritiben Patel:** Story 1 and operations.
- **Romit Patel:** the data pipeline.
- **Pavan Rella:** dashboards and testing.
- **Charmiben Patel:** the website, accessibility and this presentation.

### 17. Thank you
Thank the audience and the supervisor, then take questions. Keep the live site open in case a question needs a chart.

## Likely questions

- **Why are incomes from 2020?** The 2021 Census reports 2020 incomes. They are the latest renter household incomes we can match to shelter costs. The 2026 Census will update them.
- **Why only purpose-built rentals?** That is what the CMHC Rental Market Survey covers. Condo and secondary rentals are surveyed separately and less consistently across cities.
- **Why these comparison cities?** See [comparator_cmas_justification.md](comparator_cmas_justification.md).
- **How would the data be refreshed?** The pipeline is re-run, which repeats the checks and rebuilds the views. See [live_refresh_demo.md](live_refresh_demo.md).
