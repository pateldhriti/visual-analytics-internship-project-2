# Code Review: Data-Quality Checks (Romit's "Rebaseline and validate data cleaning pipeline" PR)

**Scope:** [PR #49](https://github.com/pateldhriti/visual-analytics-internship-project-2/pull/49),
`rebaseline-data-pipeline`, open since 2026-10-19, not yet merged. Reviewed by checking out the
branch in an isolated `git worktree` (never touching the primary working copy or the live
`warehouse` schema) and actually running its cleaners against this project's real raw files, not
just reading the code.

## What this PR actually is

Not an incremental fix — a **full parallel rewrite** of the entire raw-to-database pipeline:
5 new cleaner scripts (`etl/clean_*.py`), a new Postgres schema (`sql/clean_schema.sql`, schema
name `clean`), new SQL analysis views (`sql/analysis/`), a new pytest suite (`tests/`), and new
validation reports (`docs/DATA_CLEANING_REPORT.md` etc.). 6,210 additions, **0 deletions** — the
existing `etl/extract_*.py` / `reshape_*.py` scripts are untouched; copies are additionally placed
under `legacy/` as a second reference, not moved.

## Verified by actually running it, not just reading it

Copied this project's real `data/raw/` files into the isolated worktree and ran 3 of the 5 cleaners
directly:

| Cleaner | Result | Cross-check against known-good values |
|---|---|---|
| `clean_census_profile` | 514 rows (420,960 raw → 2,631 Windsor rows → 514 after topic-scope filtering) | Population, 2021 = **422,630** — exact match |
| `clean_windsor_rental_market` | 2,385 rows across 20 of 28 real sheets | Vacancy (Combined, Oct-25) = **3.6%**, 2BR rent = **$1,451** — exact match to the currently-verified figures |
| `clean_canada_rental_market` | 336 rows, all 42 real CMAs kept (no comparator pre-selection) | 42 CMA rows correctly separated from 13 non-CMA aggregate rows |

Also ran the PR's own test suite (`pytest tests/test_cleaning.py`): **28 of 38 tests pass** standalone;
the other 10 correctly fail with a clear `FileNotFoundError`, not a code bug — see below.

**The code that was testable works, and matches already-verified figures exactly.** This isn't a
rough draft; the raw-file integrity verification (SHA-256 manifest checked before *and* after
cleaning, so the pipeline can prove it never touched `data/raw/`), the explicit `value_status`/
`value_flag` columns for every suppression/not-applicable/revised marker, and the "stop on an
unrecognized marker" design are all genuinely careful engineering.

## Blocker 1: depends on 2 raw files this project doesn't have

`etl/cleaning_common.py`'s `RAW_FILES` expects:
- `statcan/9810025201_databaseLoadingData (1).csv` (765 KB) — a **pre-filtered, Windsor-only**
  StatCan export, not the 1.28 GB national bulk file (`shelter_cost/98100252.csv`) the current
  pipeline downloads and filters itself.
- `cmhc/provincial-starts-completions-dwelling-type-08-26-en.xlsx` — an **August 2026** edition
  with apparent **CMA-level Windsor rows** (`DATASET_NOTES`: "Only the `Windsor` row of Tables
  A4_1, A5_1 and A6_1"), not the June-2026 Ontario/Canada-only quarterly file this project
  currently has.

Neither file exists in `data/raw/`. This is exactly why 10 of the PR's own 38 tests fail locally —
not a bug, a missing-input problem. **Worth flagging as potentially valuable, not just a blocker:**
if that second file is real and obtainable, it would resolve the exact gap
`docs/story3_narrative_v1.md` and `docs/starts_history_profile.md` both independently flagged —
no Windsor-specific starts/completions figure exists anywhere else in this project. Finding and
downloading both files is a prerequisite before this PR can be fully evaluated, let alone merged.

## Blocker 2: abandons the team's reviewed star-schema design, undiscussed

`sql/clean_schema.sql` creates a separate `clean` schema — flat tables, **no foreign keys, no
conformed dimensions** ("the tables are not linked by foreign keys: their geographies and periods
differ," per its own header comment). This is a deliberate, complete departure from
`docs/conceptual_er_model.md`'s star schema (8 shared dimensions + one fact table per source), which
that doc states was "reviewed with Pavan" — i.e. an actual team design decision, not something to
reverse unilaterally in a PR. **Not a correctness problem** (a flat schema can be perfectly valid),
but a real architecture decision this project already made once, being silently proposed again
without a corresponding discussion in the PR itself.

## Blocker 3: 3+ days stale relative to everything built on main since

This branch is based on main as of 2026-10-19. Everything since then is entirely absent from it:
the shared ETL framework (`etl/etl_framework.py`), the warehouse's keys/constraints/indexes and ER
diagram, the Story 1 SQL views (including the validation fix that corrected a real bug in the
burden-rate denominator), the GitHub Actions CI workflow, the KPI catalogue, the embedding spike.
Merging this now would not be a clean fast-forward or even a simple rebase — it would need a real,
careful reconciliation against roughly a week of independently-verified work.

## Blocker 4: filename collision, self-acknowledged but not resolved

The PR's own generated report (`docs/DATA_CLEANING_REPORT.md`) states: *"`extract_windsor_census_
profile.py` writes to the same file name as this pipeline's census output, so do not run it."*
That's a real landmine left in place, not fixed -- anyone who doesn't happen to read that one line
in a generated report could silently overwrite one pipeline's output with the other's.

## Recommendation: do not merge as-is

Everything that was testable works correctly and matches already-verified figures exactly -- this
is real, careful engineering, not a rough draft to dismiss. But it's a full architectural
alternative to the current pipeline, not an incremental patch, and merging it today would mean:
missing 2 of 5 raw inputs, silently reversing a reviewed team design decision, reconciling a week of
drift, and leaving a known output-filename collision live. None of that is a quick fix inside this
review -- it needs the missing files sourced, an explicit team decision on the schema question
(keep both, migrate, or drop one), and a real rebase before it's mergeable.
