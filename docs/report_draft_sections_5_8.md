# Final Report — Draft of Sections 5-8

**Windsor Housing Visual Analytics** · COMP-8977 Internship/Project-2, Fall 2026
**Status:** first merged draft, 19 November 2026. Follows sections 1-4 (`docs/report_draft_sections_1_4.md`): 5 Analysis and findings, 6 Implementation, 7 Testing and evaluation, 8 Conclusion. Limitations and future work are a separate section (`docs/report_limitations_future_work.md`). **[TODO]** marks results still to come (user testing, the runs on the university servers).

---

## 5. Analysis and findings

The full findings, with the 14 figures exported from the dashboards, are in `docs/report_findings.md`; this section summarises them. All rates are from official statistics: the 2021 Census (incomes for 2020), CMHC's October Rental Market Survey (to 2025) and CMHC's starts and completions (to September 2026).

| Story | Finding | Key evidence |
|---|---|---|
| 1. Who faces the greatest pressure? | Renters, and low-income renters most | 34.8% of renter households spend 30%+ of income on shelter, against 10.9% of owners (3.18 times); 89% of renters with incomes under $10,000; 3.2% of renters spend all their income or more |
| 2. The rental market | Easier to find, not cheaper | Apartment vacancy 1.8% (2022) to 3.7% (2025); 2-bedroom apartment rent $949 (2019) to $1,454 (+53%); units the lowest-income renters can afford are 2.3% vacant |
| 3. Building enough? | A 2024 peak, now slowing | Starts 2,157 (2024) to 1,262 (2025); January-September 2026 starts 21% behind 2025; rental completions high (590 this year) but rental starts low (277) |
| 4. Compared with similar cities | Cheapest, but catching up fastest | Lowest 2-bedroom rent of five Ontario cities ($1,454) but the fastest rise since 2019 (53%; Toronto 31%) |
| 5. Combined Analysis | Cheaper, not more affordable | 61% of renters cannot afford the average 2-bedroom; rent takes 36% of the median renter's income, like the other cities; Windsor built 59% of the homes its 2016-2021 growth needed, the least of the five; 52% priced out of a 2-bedroom now, 63% by 2030 in the central scenario |

**The combined picture.** Each story alone gives a partial answer: renters are under pressure (1), the market is loosening (2), construction is slowing (3), Windsor is cheap (4). Joined (5), they show why the pressure persists: Windsor's lower rents are matched by lower renter incomes, rents have outpaced any plausible income growth since 2019, and the supply that would ease it was not built at the pace of population growth and is now falling again. The most affected are renters with low incomes, living alone, and the units they can afford are the scarcest.

---

## 6. Implementation

### 6.1 Overview

The system was built from 7 October 2026 by four people, in weekly sprints, with every change on its own branch, reviewed through a pull request (about 145 by 19 November) and tested automatically before reaching `main`. Its architecture is described in section 4 and in `docs/architecture.md`; this section covers what was built and the main implementation choices.

| Component | Size | Notes |
|---|---|---|
| Data pipeline (`etl/`) | 27 source files; one extract per source; warehouse load; refresh orchestration | Every source checked by the schema guard before loading; the weekly refresh downloads what changes |
| Warehouse (`sql/`) | 8 dimensions, 9 fact tables, 59 views | Every measure defined once, in a view |
| Dashboards | 6 dashboards, 38 tabs | Built entirely by script (`etl/build_*_dashboard.py`), never by hand |
| Website (`web/`) | React (Vite): home page, five story pages, methodology and sources | Its numbers are exported from the same views as the dashboards |
| Deployment (`deploy/`) | University PostgreSQL, Superset 6 (apss), our server whva | HTTPS, firewall, daily backups, uptime monitoring |

### 6.2 Implementation choices

- **Dashboards as code.** Superset dashboards are usually built by clicking. Here every chart, tab, filter, colour and note is created by a Python script through Superset's API. This made the dashboards reproducible on a fresh Superset, reviewable in pull requests, and portable between Superset 3.1 (development) and 6 (the university's server), with one compatibility module for the differences (`etl/superset_compat.py`). It also made the notes under each chart compute their numbers from the warehouse at build time, so they cannot drift from the charts.
- **One definition per measure.** Rates, shares and comparisons are SQL views; the dashboards query them and the website's figures are exported from them. A change to a measure is made once and appears everywhere, and the cross-story consistency tests (section 7) check that it does.
- **Long-format staging.** Every extract writes the same shape (one row per place, category, period and measure), which made adding sources (for example, every Canadian city, or CMHC's intended-market tables late in the project) a matter of one extract, one loader function and one view.
- **Data quality before loading.** The schema guard compares each file's columns, sheets and header rows with a saved snapshot and stops the whole run on any change; each extract then checks its own output (required cities present, parts adding up to totals). A failed refresh changes nothing and raises an alert.
- **Deploying to university services.** The original plan was a commercial host (Render). The project moved to the University of Windsor's PostgreSQL, Superset and a virtual machine, which cost nothing and kept the data on campus, but brought constraints: laptops cannot reach the database (the data is loaded from whva as one transactional package), and the shared Superset blocks embedding, so the website currently links to the dashboards instead of embedding them (decisions D46, D51).

### 6.3 Changes driven by feedback

The supervisor's reviews shaped the final system (decision log, D32-D59):

| Feedback | Change |
|---|---|
| The four stories read as separate projects | Story 5, Combined Analysis: joined views answering questions no single story can |
| Dashboards too dense; a dashboard should not need scrolling | Every dashboard split into tabs that each fit one screen |
| Compare before and after the pandemic | Ten years of rent and vacancy for five cities; 2016-2020 against 2021-2025 for construction |
| Make the key findings more striking than bar charts | The website draws its own charts for the main findings, with Superset for exploring |
| Match the team's reference dashboards | New tabs, colours and formats; apartment-only figures where the reference used them; scope stated on every chart |

---

## 7. Testing and evaluation

### 7.1 Automated tests

| Kind | Count | What they check | Where they run |
|---|---|---|---|
| Unit tests | 127 | Each extract's parsing of a small in-memory copy of its source layout (CMHC workbooks, StatCan tables, portal exports); the schema guard; the refresh's failure handling; the dashboard tab helper; the website export; the Superset compatibility layer; the token API's request checks | every merge to `main` (GitHub Actions) |
| Data tests | 97 | Against the loaded warehouse: all 59 views run; no duplicate rows in 17 key views; shares add to 100%; zones and unit sizes add to the Windsor total; the same figure (renter burden, rent, vacancy, starts) is equal in every story that shows it; Story 1 matches Statistics Canada's published rates; values in plausible ranges; every staging row loaded | after each refresh, where a warehouse is available (`etl/test_warehouse_views.py`) |
| Web checks | lint and production build | code style and that the site builds | every merge |

All 224 pass (19 November 2026).

### 7.2 Data validation

- **Against published figures:** our computed renter and owner burden (34.8%, 10.9%) equal the Census Profile's own (difference 0.0 points), shown on Story 1's Data Validation tab.
- **Against the team's reference dashboards:** every figure of Stories 1-4 was compared with the reference screenshots (for example Story 4's rental-supply table, the Jan-Sep 2026 tiles 690 / 1,029 / 1,303, and the 2019-2025 rents); all match after the switch to CMHC's revised and apartment-only tables.
- **Cross-story consistency:** checked by the data tests above.

### 7.3 Dashboard and system checks

- **Layout and filters:** an automated browser check opened every tab of the six dashboards (local and on the university's Superset), recorded errors, empty charts, overlapping cards and page height, and tried every filter on every tab. It found and led to fixes for a filter that emptied a tile (Story 3, Year = 2026), hidden axis labels and tabs taller than one screen; all 38 tabs now load without errors and fit one screen at 1440 x 1000.
- **Backup restore:** a backup taken by the daily job restored into an empty database in 2 seconds, with all 17 tables matching and all 59 views running (rehearsed locally). **[TODO: result on whva with the nightly backup.]**
- **Load:** **[TODO: results of `deploy/load_test.py` against the public site.]**
- **Uptime:** **[TODO: availability over the monitoring period, from `uptime_check.sh --report`.]**
- **Refresh:** **[TODO: the recorded end-to-end refresh with StatCan's October 2026 data.]**

### 7.4 User testing

**[TODO: six think-aloud sessions (`docs/user_testing_plan.md`): participants, task success, how many testers stated each story's main finding (goal G1: 4 of 5), the issues found and what was changed.]**

### 7.5 Evaluation against the goals

| Goal (design document) | Result |
|---|---|
| G1 A visitor can follow each story to its conclusion | **[TODO: user testing]** |
| G2 At least two combined questions use two or more datasets | Met: Story 5 answers eight combined questions from joined views |
| G3 Every number traceable to its source | Met: every chart names its source table; data tests and the schema guard run on each refresh |
| G4 Pages fast enough | **[TODO: load test and page timings on whva]** |
| G5 Refresh is repeatable | Met: one command (`etl/scheduled_refresh.py`) downloads, checks and reloads; weekly schedule |
| G6 Free to run | Met: university services, $0 |
| G7 Works on desktop and mobile | Partly: the website works at phone width; the dashboards keep a desktop layout inside a scrolling frame (decision D31) |

---

## 8. Conclusion

The project set out to make housing affordability in Windsor understandable from official data, and to show how affordability, the rental market and new supply fit together. It delivered a public website and six interactive dashboards on the University of Windsor's servers, backed by a tested pipeline that loads 27 government files into one warehouse and refreshes itself weekly.

The analysis gives a clear answer. Windsor is the cheapest of the five Ontario cities compared, but not more affordable for the people who rent there: renter incomes are correspondingly lower, rents have risen faster than in any of the comparison cities since 2019, and construction did not keep pace with population growth. Six in ten renter households cannot afford the average 2-bedroom today, and on current trends the share grows. The pressure falls hardest on renters with low incomes and on people living alone.

Technically, the main lessons were to define every measure once and build everything else from it; to treat dashboards as code, which made them reproducible across two Superset versions and reviewable like any other change; and to check data before loading it, since the most likely failure of a public-data pipeline is a source changing its format. Working within university infrastructure traded convenience (embedding, direct database access) for zero cost and local control.

**[TODO: one paragraph on what user testing showed and the team's reflection, then a closing sentence on the most valuable next step (see Future work: yearly income data and the 2026 Census).]**
