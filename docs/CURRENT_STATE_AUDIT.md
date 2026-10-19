# Current State Audit

**Audit date:** 2026-10-18 (Sunday of **Week 2**, Oct 15–21, in the 8-Week Project Plan)
**Commit audited:** `f1ff774` on `main`, the same as `origin/main`
**Machine:** Romit's Windows 11 laptop, running the project's local Docker stack

## How this audit was done

Every statement below comes from one of these sources:

- reading the file itself
- a live query against the running PostgreSQL or Superset containers
- a read-only Python probe of the files in `data/raw/`
- running the test suite

A file existing was never treated as proof that it works. Nothing in the repository, the database or Superset was changed. The only output is this document.

What was *not* run, and why:

- **React lint and build were not run.** `web/node_modules` is not installed, and installing it would change the working tree.
- **The ETL scripts were not executed.** They write to `data/staging/` and the database. Whether they *could* run was checked by comparing each script's input paths against the files actually on disk.
- **`pre-commit run` was not run.** Its hooks rewrite files.

---

## Working and verified

| Item | Evidence |
|---|---|
| Docker stack is up | `windsor_housing_postgres` (healthy), `windsor_housing_superset` (healthy) and `windsor_housing_redis` have been running for about 26 hours. Superset `/health` returns `HTTP 200 OK`. |
| Superset metadata database is initialised | `superset_meta` has 55 tables, an `admin` user created 2026-10-17 16:11 UTC, and the 5 default roles (Admin, Public, Alpha, Gamma, sql_lab). |
| Shelter-cost unit tests | `pytest etl/test_affordability_etl.py`: **14 passed, 1 skipped** in 6.3 s. See [Test results](#test-results). |
| `etl/statcan_profiling.py` | Pure functions: encoding, symbol legend, chunked column profiling. Its logic is exercised indirectly through `reshape_shelter_cost_long.py`, which the tests import. |
| Shelter-cost reshape logic (`reshape_long`, `verify_preserves_original`) | Covered by passing tests: symbols become NULL, each symbol maps to a flag, unknown symbols raise an error, each wide row becomes exactly 3 long rows, and the round trip has no mismatches. |
| Story 1 headline figures exist in the raw data on disk | The read-only probe of `data/raw/9810025201_databaseLoadingData (1).csv` reproduces every count in `docs/story1_questions_and_measures.md`: Owner 30%+ = **13,005** / 119,125; Renter 30%+ = **15,735** / 45,605; Total = 164,730; 30–<100% = 26,210; ≥30% = 28,745; Not applicable = 510. |
| Census Profile raw data | The zip holds 420,960 rows, 2,631 of them for Windsor CMA (DGUID `2021S0503559`). Population **422,630** and 165,665 households match the plan's check value and the docs. Characteristic 1492 (tenants spending 30%+) = **34.8%** and characteristic 1484 (owners) = **10.9%**, matching the plan's Week 3 validation targets. |
| CMHC Windsor RMS 2025 workbook | 29 sheets. All 9 sheets that `etl/extract_windsor_rms.py` needs are present. |
| CMHC Canada RMS 2025 workbook | `Table 1.0` contains all 5 centres `extract_rms_canada_comparison.py` needs: Windsor, London, Kitchener-Cambridge-Waterloo, Hamilton and St. Catharines-Niagara. |
| Python environment | `.venv` runs Python 3.12.0 and has everything in `requirements.txt` plus `requests` 2.34.2. |
| React routing | `web/src/App.jsx` defines the plan's 6 routes. `Header.jsx` has a responsive menu toggle with `aria-expanded` and `aria-controls`. `index.css` has a `@media (max-width: 680px)` breakpoint. |
| Pre-commit configuration | `.pre-commit-config.yaml` sets up trailing-whitespace, end-of-file, check-yaml, merge-conflict, case-conflict and a 5 MB large-file block. |
| Raw and staging data are kept out of git | `.gitignore` lines 228–231 exclude `data/raw/*` and `data/staging/*` but keep the `.gitkeep` files. |

---

## Implemented but incomplete

These items have real code or documents, but cannot currently be reproduced on this machine, or do less than the plan or their own documentation says.

### ETL scripts: what each one actually does, and whether it can run here

| Script | What it actually does | Can it run on this machine? |
|---|---|---|
| `extract_windsor_shelter_cost.py` | Streams `data/raw/shelter_cost/98100252.csv` (the 1.28 GB national file, wide format with tenure as columns) and keeps the Windsor rows. | **No.** That file and folder don't exist. The local shelter-cost file is a different product (see [Data problems](#data-problems--blockers)). |
| `reshape_shelter_cost_long.py` | Turns the wide staging CSV into long format (30,240 rows → 90,720), renames columns to snake_case, adds `data_quality_flag` and runs its preservation checks. | **No.** Its input staging CSV doesn't exist, and the local raw file is already long-format with different column names. |
| `load_windsor_shelter_cost_to_postgres.py` | Loads the wide staging CSV into `public.windsor_shelter_cost`. | **No.** Input is missing. |
| `load_windsor_shelter_cost_long_to_postgres.py` | Loads the long staging CSV into `public.windsor_shelter_cost_long`. | **No.** Input is missing. |
| `run_affordability_etl.py` | Runs extract → reshape → `TRUNCATE` → `load_shelter_cost_facts()` with logging. | **No.** Needs the missing raw file and an existing `warehouse` schema. |
| `extract_windsor_census_profile.py` | Streams `data/raw/statcan/98-401-X2021002_English_CSV_data.csv` (cp1252 encoding) and keeps 60 curated Windsor characteristics. | **No, as configured.** The CSV is still inside `98-401-X2021002_eng_CSV.zip` and there is no `statcan/` folder. The data itself is fine. |
| `reshape_census_profile_long.py` | Turns 60 wide rows into 360 long rows (measure type × sex). | Only after the extract above has run. |
| `extract_windsor_rms.py` | Parses 9 sheets into `windsor_rental_market.csv`, documented as 1,395 rows. | **No, as configured.** It expects `data/raw/cmhc/rmr-windsor-2025-en.xlsx`, but the file sits directly in `data/raw/`. |
| `extract_rms_canada_comparison.py` | Parses `Table 1.0` for 5 centres: 40 rows expected. | **No, as configured.** Same `cmhc/` subfolder problem. |
| `extract_cmhc_starts_completions.py` | Reads Tables C1 and C2 of `quarterly-starts-completions-under-construction-06-26-en.xlsx`, keeps Ontario and Canada, and turns 5 dwelling-type columns into rows. | **No.** That workbook isn't on disk. The local starts workbook is a different publication with no C1/C2 sheets. |
| `validate_supply_data.py` | Checks counts, ranges, component-sum reconciliation and periods, and **rewrites** a section of `docs/data_quality_report.md`. | **No.** Input is missing. |
| `load_raw_files_to_postgres.py` | Recursively loads every CSV and xlsx under `data/raw/` into the `raw` schema as-is, using COPY fast-path or a lenient fallback. | **Yes, probably.** It walks the folder recursively, so the flat layout is fine. It would *not* load the zipped census CSV. Not executed. |
| `create_warehouse_schema.py` | `DROP SCHEMA warehouse CASCADE`, then runs `warehouse_schema.sql` and the seed SQL. | **Yes.** Only needs the database. Not executed. |
| `load_warehouse_facts.py` | Truncates and loads the 4 fact tables from 5 staging CSVs, joining dimension keys. | **No.** None of the 5 staging CSVs exist. |
| `setup_superset_dashboard.py` | Creates the "Windsor Housing Data" database connection, a dataset on `public.windsor_shelter_cost_long`, and one `dist_bar` chart, using the REST API. | Would create the connection, but the dataset step needs `public.windsor_shelter_cost_long`, which doesn't exist. |
| `register_superset_datasets.py` | Registers 3 Story 4 views as datasets with one saved metric each. | Needs the `warehouse` views, which don't exist. |
| `example_statcan_profiling.py` | A demo that profiles `data/staging/windsor_shelter_cost.csv`. | **No.** Input is missing. |

**Bottom line:** 0 of the 13 data-producing ETL steps can run as configured with the raw files on this machine. Only the schema-creation and raw-landing scripts could run.

### Other partial items

- **The warehouse was never loaded on this machine.** `docs/sprint1_status_note.md` says there is "a populated PostgreSQL warehouse (4 fact tables, 0 unmatched dimension keys)". That may be true on another laptop, but there is no load-audit table, database dump or CI run that proves it. It can't be rebuilt here without the missing raw files.
- **Shelter-cost ETL (plan Week 2) is only partly done.**
  - Done: symbols set to NULL, flag column added, fact load, row-count logging.
  - Not done: "standard category labels". Category values are still StatCan's raw text, such as `"Total - Household type including census family structure"`.
  - Not done: the "real raw file" test is skipped.
- **Story 3 views (`sql/story3_views.sql`) are thin.**
  - `v_story3_starts_completions_by_dwelling_type` simply passes the fact table through. It covers Ontario and Canada only, for a single quarter plus year-to-date, not "per year".
  - `v_story3_supply_per_1000_households` returns hard-coded `NULL`s for `households_total` and `supply_per_1000_households`.
- **Story 4 views (`sql/story4_views.sql`)**: `v_story4_affordability_gap` returns `NULL` for `renter_income_growth_pct` and `affordability_gap_index`. The index is defined, but not computed.
- **Superset Story 4 datasets and theme.**
  - The script exists, but the saved metrics cover only 3 views with 1 metric each.
  - The palette is defined in `docker/superset_config.py`.
  - None of it is registered in the running Superset (see [Current Superset state](#current-superset-state)).
- **PostgreSQL schema (plan Week 2).**
  - Done: DDL with primary keys, foreign keys and unique constraints.
  - Not done: there is **no `CREATE INDEX`** anywhere in `sql/`, although the plan asks for indexes.
  - Not done: the "ER diagram exported for the report". There is only a Mermaid block in `docs/conceptual_er_model.md`, and that diagram leaves out `fact_starts_completions`.
- **ER model review (plan Week 1).** `docs/conceptual_er_model.md` itself says: "**Not yet reviewed with Pavan**".
- **Docker setup (plan Week 1).**
  - Done: the compose file, the admin init script and persistent volumes.
  - Not evidenced: the "tested on Windows and Mac" check and a "written setup guide". There is only a README section, and the README says Docker is "set up separately by the team".
- **Repo and dev environment (plan Week 1).** Branch protection only blocks deleting `main`, per `docs/onboarding_checklist.md`. Team rule 3 ("nothing merged without one review") is not enforced by GitHub.
- **React home and data-sources pages (plan Week 3) were built and then lost from `main`.**
  - The work exists in git history: commits `beac7b3`, `13d32af`, `77cade9`, `342d9a4` and `5cda460` (PRs #30, #34, #35).
  - At `5cda460` the tree contains `pages/Sources.jsx`, `components/StoryCard.jsx`, `KpiStrip.jsx`, `ThemeToggle.jsx`, `ScrollProgress.jsx` and `hooks/useSpotlight.js`.
  - Recovery merge `ae32639` ("Merge pull request #35 (recovery)") did not bring them back. The current `main` has none of those files, and `Home.jsx` is a 13-line placeholder.
  - This matches the status note's own wording that "the non-web pieces are back on `main`".
- **Unit tests check less than the plan asks.** The plan says "totals matching the raw file", but the only test that touches real data is skipped.
- **`requirements.txt` is missing a dependency.** `setup_superset_dashboard.py` and `register_superset_datasets.py` both import `requests`, which isn't listed. It is only in `.venv` as a side effect of Jupyter.
- **Hosting test (plan Week 2):** the status note calls it "in progress". No artifact exists in the repo.

---

## Planned but not started

Plan items due by the end of Week 2 (Oct 21) or earlier, with no artifact anywhere in the repository, git history, database or Superset:

| Plan item | Owner | Due |
|---|---|---|
| **Shared ETL framework**: a config file per dataset, a loader that validates the schema and stops on unexpected columns, logging, and a load-audit table (file, rows, time, status) | Romit | Week 2 |
| Code review of the affordability ETL (no review artifact visible locally) | Romit | Week 2 |
| Superset configuration: Public role and a test of anonymous viewing (`superset_config.py` has no `PUBLIC_ROLE_LIKE`) | Pavan | Week 2 |
| Embedding research (Embedded SDK vs public dashboards) | Pavan | Week 2 |
| KPI catalogue (15–20 KPIs) | Pavan | Week 2 |
| Code review of the PostgreSQL schema | Pavan | Week 2 |
| Story-page template (reusable story component) and a real methodology page | Charmiben | Week 2 |
| Embedding spike (`@superset-ui/embedded-sdk` is not in `web/package.json`) | Charmiben | Week 2 |
| Profile the 2015–2025 starts history and build a dwelling-type mapping table | Charmiben | Week 2 |
| Hosting go/no-go note | Dhritiben | Week 2 |

Week 3 items (Oct 22–28) not started:

- SQL views for Story 1
- GitHub Actions CI (there is no `.github/` folder) and the hosting decision
- Validating Story 1 against published figures
- **Historical RMS 2015–2024 ETL** (Romit)
- **Automated data-quality checks for the RMS tables** (Romit)
- **SQL views for Story 2** (Romit)
- **ETL README** (Romit)
- Story 1 chart list and narrative v1

Done early, ahead of Week 3: Story 3 views, Story 4 views, comparator ETL, affordability-gap index note, Superset dataset script, supply data-quality checks, Story 3 narrative v1, peer test. Some of these are only partly done (see above).

**Story 2 (Romit's end-to-end story)** has no SQL views, no Superset dashboard, no narrative, no findings and no historical data yet. Its only parts are the RMS 2025 extraction and the fact-table design.

---

## Data problems / blockers

1. **The raw files on disk don't match what the ETL expects.** Every ETL script and every doc assumes a `data/raw/{cmhc,statcan,shelter_cost}/` layout. On this machine `data/raw/` is flat:

   | ETL / docs expect | On disk |
   |---|---|
   | `shelter_cost/98100252.csv` (1.28 GB, 5,019,840 rows, wide) and `98100252_MetaData.csv` | `9810025201_databaseLoadingData (1).csv`: 748 KB, **2,389 rows**, long format |
   | `statcan/98-401-X2021002_English_CSV_data.csv` | `98-401-X2021002_eng_CSV.zip` (not extracted) |
   | `cmhc/rmr-windsor-2025-en.xlsx`, `cmhc/rmr-canada-2025-en.xlsx` | Same files, in the wrong folder |
   | `cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx` (Q2 2026, Canada and provinces) | `provincial-starts-completions-dwelling-type-08-26-en.xlsx`: a **different publication** (Housing Information Monthly, August 2026) |

   There is no manifest of source URLs, file names or checksums, so nobody can tell which files a teammate's database was built from.

2. **The local shelter-cost file is a different extract from the one the ETL was built for.**
   - It has a single `Tenure (3)` column plus `VALUE`, `STATUS` and `SYMBOL` columns, and the `SYMBOL` column is completely empty. Suppression markers live in `STATUS`: 40 `x`, 42 `...`.
   - The ETL expects `Tenure (3):Total - Tenure[1]`, `Symbol` and `Coordinate` columns.
   - It contains only the Total housing-suitability, Total dwelling-condition and point-estimate slices.
   - On the upside, its 2,389 rows match the plan's "2,389 rows" exactly. That confirms the explanation `docs/shelter_cost_audit.md` gave as an unconfirmed inference: it is a narrower web-table selection.
   - This file is enough to answer every Story 1 question, but the current reshape code can't read it.

3. **Story 1 doesn't reproduce the published figures with the current formula.** The plan's Week 3 targets are **34.8%** of tenants and **10.9%** of owners at 30%+, and the Census Profile on disk has exactly those values.
   - Q1 in `docs/story1_questions_and_measures.md` divides by the ratio total *including* "Not applicable" households, which gives **34.5%** for renters (15,735 / 45,605).
   - Leaving "Not applicable" out of the denominator gives **34.75% → 34.8%** for renters (15,735 / 45,280) and **10.93% → 10.9%** for owners (13,005 / 118,940).
   - The team needs to decide which denominator to use before dashboards are built. The Story 1 outline currently states 34.5%.

4. **Windsor starts and completions data *does* exist locally, which contradicts the docs.**
   - The August 2026 workbook has Windsor CMA rows in `Table A4_1` (starts and completions by dwelling type, CMAs), `Table A5_1` (under construction) and `Table A6_1` (cumulative year-to-date).
   - `docs/cmhc_starts_completions_audit.md`, `docs/data_dictionary_supply.md`, `docs/story3_narrative_v1.md` and `sql/story3_views.sql` all say no Windsor figure exists. That was true of the Q2 workbook they audited, but not of the file now on disk.
   - It is still one month plus year-to-date, not the plan's 2015–2025 series.

5. **No historical RMS workbooks.** The plan's Story 2 (2015–2025 trends) needs 10 years of Windsor workbooks. Only the 2025 edition is on disk, which covers Oct-24 and Oct-25 only.

6. **The affordability-gap index can't be computed.** There is no renter-income growth series (see `docs/affordability_gap_index.md`).

7. **Supply per 1,000 households.** This is currently blocked by a geography mismatch, but it becomes computable once the Windsor rows from point 4 are extracted. A year mismatch remains: 2021 Census households against 2026 starts, which the plan's risk table already says must be labelled on every chart.

8. **Owner and renter counts differ between sources.** The Census Profile has Owner = 120,050 and Renter = 45,625, while the shelter-cost table has 119,125 and 45,605. These are different survey universes, not an error. The planned "KPI consistency check" must label which source each figure comes from.

---

## Documentation inconsistencies

| Doc / file | What it says | What is actually the case |
|---|---|---|
| `docs/data_architecture.md` | Three schemas exist (`public`, `raw`, `warehouse`); warehouse fact tables are "not actually loaded"; Superset queries `public`. | This contradicts `conceptual_er_model.md` and `sprint1_status_note.md`, which both say the fact tables are loaded. On this machine **none of the three schemas has any tables**. |
| `docs/data_dictionary_supply.md` | "There is currently no `warehouse.fact_starts_completions` table on `main`." | `sql/warehouse_schema.sql`, `load_starts_completions_facts()` and both Story 3 views all define or use it. |
| `docs/conceptual_er_model.md` | Starts/completions is "not profiled yet" and "has no fact table yet". The diagram shows 3 fact tables. | The schema has 4 fact tables, and the starts source has been profiled. |
| `etl/load_warehouse_facts.py` (docstring) | The comparison set is "London, Kitchener-Cambridge-Waterloo, Toronto"; "32 rows extracted, 28 loaded". | The code uses Hamilton and St. Catharines-Niagara instead of Toronto, giving 40 rows extracted. By the function's own filter, that means 36 loaded. |
| `docs/affordability_gap_index.md` | The rent-growth table and ranking include **Toronto CMA**. | Toronto was removed from the comparator set (`comparator_cmas_justification.md`), and Hamilton and St. Catharines-Niagara have no rows in it. |
| `docker/superset_config.py` (comment) | The palette assigns "Toronto CMA = slot 4". | Toronto is no longer a comparator, and there are now 5 markets, not 4. |
| `docs/cmhc_starts_completions_audit.md`, `data_dictionary_supply.md`, `story3_narrative_v1.md`, `sql/story3_views.sql` | No Windsor starts or completions data exists. | The local workbook has Windsor CMA tables (Data problem 4). The file they describe is not on disk. |
| `docs/story3_narrative_v1.md` | "Row housing came next at 2,262 (13%), then singles at 2,693 (15%)". | By its own numbers, singles (2,693) rank above row housing (2,262). |
| `docs/story1_questions_and_measures.md` (dependency note) | The long table is "not yet loaded into the database". | This conflicts with `story1_narrative_outline.md`, which says that dependency is now resolved. |
| `docs/story1_*` vs the 8-Week Plan | Renter burden is 34.5%. | The plan's validation target is 34.8% (Data problem 3). |
| `docs/sprint1_status_note.md` | "We're at the end of Week 3." | By the 8-Week Plan, Oct 16 is **Week 2** (Oct 15–21). The note uses the proposal's week numbering. |
| `docs/sprint1_status_note.md` | "A data dictionary exists for all 4 sources." | Only 2 data dictionaries exist (`data_dictionary_census_comparison.md`, `data_dictionary_supply.md`). The shelter-cost audit and the RMS sheet catalogue are audits, not column dictionaries, so shelter cost and the Windsor RMS have none. |
| `docs/sprint1_status_note.md` | The warehouse is populated and Story 4 datasets are registered in Superset. | Neither can be reproduced on this machine, and the repo has nothing that proves either. |
| `docs/shelter_cost_audit.md` | The 2,389-row figure is "a well-supported inference, not a certainty". | It can now be confirmed: the local file has exactly 2,389 rows from a narrower selection. |
| All ETL docstrings and audits | Paths under `data/raw/cmhc/`, `data/raw/statcan/`, `data/raw/shelter_cost/`. | `data/raw/` is flat on this machine (Data problem 1). |
| `README.md` | "Copy `.env.example` to `.env`". | `.env.example` is **deleted in the working tree** (uncommitted, `git status: D .env.example`). It still exists at `HEAD`. |
| `README.md` "Running the full stack" | Steps 3–4 only cover the two `public`-schema shelter-cost loaders and the first chart. | The warehouse pipeline (`create_warehouse_schema.py`, the extract scripts, `load_warehouse_facts.py`, `run_affordability_etl.py`, the view SQL, `register_superset_datasets.py`) and its run order are not documented anywhere a new user would find them. |
| `web/src/pages/Methodology.jsx` | Says "Every figure on this site traces back to an official ... download". | The page has no source links and is marked "scaffold placeholder only". |

---

## Current Superset state

Checked live against `superset_meta` and the running container on 2026-10-18.

| Object | Count | Detail |
|---|---|---|
| Database connections (`dbs`) | **0** | "Windsor Housing Data" has not been created. |
| Datasets (`tables`) | **0** | |
| Charts (`slices`) | **0** | The "end-to-end test chart" (plan Week 1) is not present here. |
| Dashboards | **0** | |
| Users | 1 | `admin`, created 2026-10-17 16:11:17 UTC |
| Roles | 5 | Admin, Public, Alpha, Gamma, sql_lab (Superset defaults). The Public role has not been configured. |

Configuration (`docker/superset_config.py`):

- The Redis cache is set up and the custom `windsor_housing` 8-colour palette is defined.
- There is **no** `PUBLIC_ROLE_LIKE`, no `FEATURE_FLAGS` such as `EMBEDDED_SUPERSET`, no guest-token setting, and no CORS or Talisman setting. Anonymous viewing and embedding are both unconfigured.
- Image is `apache/superset:3.1.0`.

---

## Current React state

Stack: Vite 5, React 18.3, React Router 6, with ESLint 9 and Prettier configured.

**Not verified:** `node_modules` is absent, so `npm run lint` and `npm run build` were not run. No build output (`dist/`) exists.

| Route | File | State |
|---|---|---|
| `/` | `Home.jsx` (13 lines) | **Placeholder.** A title and one paragraph. The plan's "intro and 4 story cards" are missing (they were built, then lost; see above). |
| `/stories/affordability` | `StoryAffordability.jsx` | **Placeholder.** Title, 2 questions, "scaffold placeholder only". |
| `/stories/rental-market` | `StoryRentalMarket.jsx` | **Placeholder.** Same pattern. |
| `/stories/housing-supply` | `StoryHousingSupply.jsx` | **Placeholder.** Same pattern. |
| `/stories/comparison` | `StoryComparison.jsx` | **Placeholder.** Same pattern. |
| `/methodology` | `Methodology.jsx` | **Placeholder.** A stack list, no source links, "scaffold placeholder only". |
| (sources page) | none on `main` | **Missing.** `pages/Sources.jsx` exists only in history (`5cda460`). |

Shared components on `main`: `Header`, `Footer` and `PageContainer`. There is no reusable story-page component, no dashboard slot, no embedding code and no data fetching. **No page is complete.**

---

## Current PostgreSQL state

Checked live in the `windsor_housing_postgres` container. The container and the `docker_pgdata` volume were both **created 2026-10-17 16:10 UTC**, so this is a fresh instance.

| Database | Schemas (non-system) | Tables | Views |
|---|---|---|---|
| `housing_windsor` (the project database) | `public` only | **0** | **0** |
| `superset_meta` | `public` | 55 (Superset internals) | none |
| `postgres` | `public` | 0 | none |

- There is **no `raw` schema, no `warehouse` schema** and no `public.windsor_shelter_cost` or `public.windsor_shelter_cost_long`.
- **None of the 4 warehouse fact tables exist**, so none are populated.
- **None of the 5 analytical views exist** (`v_story3_*` ×2, `v_story4_*` ×3).

Row counts that the docs claim but that could not be verified here:

| Table | Claimed rows |
|---|---|
| `fact_shelter_cost` | 90,720 |
| `fact_census_profile` | 360 |
| `fact_rental_market` | 1,395 Windsor rows plus a comparison count that is inconsistent between docs (28 vs 36) |
| `fact_starts_completions` | 50 |
| `public.windsor_shelter_cost` | 30,240 |
| `public.windsor_shelter_cost_long` | 90,720 |
| `raw` schema | 31 tables |

**SQL analytical views as defined in `sql/`** (none of them exist in the live database):

- `v_story3_starts_completions_by_dwelling_type`: passes the fact table through. Ontario and Canada only.
- `v_story3_supply_per_1000_households`: starts with hard-coded NULL households and rate, plus a `data_note`.
- `v_story4_vacancy_comparison`: apartment vacancy, Total bedroom type, Windsor plus comparators.
- `v_story4_rent_comparison`: apartment 2-bedroom average rent, Windsor plus comparators.
- `v_story4_affordability_gap`: Oct-25 rent growth; income growth and index are NULL.
- There are **no Story 1 or Story 2 views.**

---

## Test results

Command run:

```
.venv\Scripts\python.exe -m pytest etl\test_affordability_etl.py -v -p no:cacheprovider
```

Result: **14 passed, 1 skipped, 0 failed** (6.33 s, Python 3.12.0, pytest 9.1.1).

| Class | Tests | Result |
|---|---|---|
| `TestSymbolHandling` | 11 (including 6 parametrised symbol→flag cases) | all passed |
| `TestRowCounts` | 2 | all passed |
| `TestTotalsMatchRawFile::test_reshape_preserves_wide_totals_on_a_fixture` | 1 | passed |
| `TestTotalsMatchRawFile::test_known_total_matches_the_real_raw_file` | 1 | **skipped**: `requires data/staging/windsor_shelter_cost.csv` |

Coverage gaps:

- This is the **only test file in the repo**. There are no tests for the census, RMS, comparator or starts extractors, the fact loaders, the SQL views, or the Superset scripts.
- No React tests.
- No CI (no `.github/workflows/`).
- The single real-data test can't run on this machine because of Data problem 2.

Notebooks:

- `00_environment_check.ipynb`: 1 code cell, executed, no errors stored.
- `01_shelter_cost_exploration.ipynb`: 18/18 code cells executed, no errors stored. It reads `../data/staging/windsor_shelter_cost.csv`, which doesn't exist here, so it was not re-run.

---

## Recommended next tasks

These are not implemented. They are ordered by what unblocks the most work. Items marked **(Romit)** are Romit's in the 8-Week Plan.

1. **Fix the raw-data inventory first** — **(Romit: shared ETL framework, data quality)**
   - Agree as a team on the exact raw files and folder layout.
   - Either get the files the ETL was written for (the full `98100252.csv` with its metadata, and the Q2 2026 quarterly starts workbook) or change the extractors to read the files actually on disk.
   - Add a committed `data/raw/MANIFEST` recording source URL, release date, file name and SHA-256 for each file, so every laptop builds from identical inputs.
2. **Build the shared ETL framework and one-command refresh** — **(Romit, Week 2 + Week 4)**
   - A config per dataset holding path, expected columns and target table.
   - Schema validation that stops on unexpected columns. This would have caught Data problems 1–2 straight away.
   - A `warehouse.load_audit` table recording file, rows, time and status.
   - One command that rebuilds `raw` → staging → `warehouse` → views in order and can safely run twice.
3. **Rebuild the database from scratch on this machine and record the real row counts** in the load-audit table. Compare them with the documented figures: 90,720 / 360 / 1,395 + (28 or 36) / 50.
4. **Re-register Superset** by running `setup_superset_dashboard.py` and `register_superset_datasets.py`. Then do the plan's Public role and anonymous-viewing test **(Pavan)**.
5. **Decide the Story 1 denominator** (Data problem 3) and write the Story 1 SQL views and published-figure validation **(Dhritiben, Week 3)**.
6. **Start Story 2** — **(Romit, Week 3)**
   - Download the historical Windsor RMS workbooks for 2015–2024 and check zone and table changes. The plan's fallback is to keep 5 years if harmonising takes more than 9 hours.
   - Then write the Story 2 views (rent year-over-year, 10-year growth, vacancy trend, turnover by bedroom type) and the RMS data-quality checks.
7. **Recover the lost React work** (home, sources, design system, components) from `5cda460` through a reviewed PR, and decide whether it replaces the current shell **(Charmiben)**.
8. **Extract Windsor starts and completions** from `Table A4_1`, `A5_1` and `A6_1` of the local workbook. Collect historical editions so Story 3 can be Windsor-specific and supply per 1,000 households can be computed **(Charmiben)**.
9. **Fix the documentation drift** listed above, especially `data_architecture.md`, `data_dictionary_supply.md`, `conceptual_er_model.md`, the `load_warehouse_facts.py` docstring, the Toronto references, and the README's full-pipeline run order. Write the **ETL README** **(Romit, Week 3)**.
10. **Small repo fixes:**
    - Restore `.env.example` (`git restore .env.example`).
    - Add `requests` to `requirements.txt`.
    - Add indexes on the fact-table foreign keys, as the plan asks **(Romit)**.
11. **Add GitHub Actions CI** running pytest and `npm run lint`, and make it a required check on `main` **(Dhritiben, Week 3)**. Add tests for the other extractors and the views **(Pavan, Week 7)**.
12. **Remaining Week 2 items:** the KPI catalogue, embedding research and spike, story-page template, hosting go/no-go note, and the ER-model review with Pavan.
