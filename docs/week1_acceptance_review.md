# Week 1 Acceptance Review (Oct 8–14)

Checked against the repository's actual commit history and merged PRs as of this review — not against task-list intentions. Every commit author checked: only `pateldhriti` has any commits in this repository; no commits from Romit1605, charmip134, or rellap766 exist yet.

## Dhritiben

| Ticket | Acceptance criteria | Status | Notes |
|---|---|---|---|
| Profile the shelter-cost table | Notebook covering 4 dimensions; sub-totals vs. totals checked across 2,389 rows; suppressed cells counted; 1-page audit note | **Accepted** | All criteria met (PR #4). One correction to the ticket itself: the real Windsor extract is 30,240 rows, not 2,389 — investigated and explained in `docs/shelter_cost_audit.md` (full dimensional cross-product), not forced to match the wrong assumption. |
| Shared StatsCan profiling module | Reusable functions: encoding, symbol detection, nulls/ranges; tested on 2 files; module + usage example saved in GitHub | **Accepted** | PR #6 (module) + PR #7 (usage example, added after the review caught it was missing from the first pass). All sub-criteria verified. |
| Prototype wide-to-long reshape | Script producing one row per income × household × tenure × cost band; expected combinations defined; actual vs expected compared; reshape preserves original data | **Accepted — one open item** | PR #8. Verified: 3,360 actual = 3,360 expected rows; 3 preservation checks + round-trip spot check all pass. **Open item:** the source table has 3 more dimensions (suitability, dwelling condition, statistics) not named in the ticket; the script filters to a single baseline slice before reshaping, a scope decision flagged twice to the ticket owner but not yet explicitly confirmed. Low risk — if the assumption is wrong, only this script and the Story 1 doc (which builds on its output) would need revisiting. |
| Compare free hosting options | Oracle Cloud Free, Render, Railway, university server compared on RAM/storage/sleep/cost; Week 2 recommendation | **Accepted** | PR #9. University server removed from the comparison (confirmed by team: not available/not in use) rather than left as an unresearched gap. Oracle Cloud Always Free recommended as primary target for the Week 2 test. |
| Story 1 questions and measures | 4–6 questions mapped to exact columns and formulas | **Accepted** | PR #10. 5 questions, each with real computed numbers (not placeholders) verified against `windsor_shelter_cost_long.csv`. Depends on the reshape task's open item above — if that scope assumption changes, these numbers would need recomputing. |
| Week 1 acceptance review | This ticket | **Accepted** | Satisfied by this document. |

**Dhritiben: 6/6 tickets complete, 5 merged to `main`, 1 open confirmation item (reshape scope).**

## Romit, Pavan, Charmiben

| Member | Tickets | Status |
|---|---|---|
| Romit | Repository and dev environment; Profile CMHC Windsor RMS 2025 workbook; Raw staging load; Conceptual ER model | **Not started** — no commits found under Romit1605 or elsewhere in the repo |
| Pavan | Docker setup for PostgreSQL + Superset; Census Profile extraction script; Choose comparator CMAs; End-to-end test chart; Data dictionary (census/comparison) | **Not started** — no commits found under rellap766 or elsewhere in the repo |
| Charmiben | React project scaffold; Layout and navigation shell; Profile CMHC starts/completions workbook; Website wireframes; Data dictionary (supply tables) | **Not started** — no commits found under charmip134 or elsewhere in the repo |

**14 of 20 Week 1 tickets across the team have not been started.** Note: Romit's "Repository and dev environment" ticket overlaps with work already done on `main` (Python 3.12 venv, Jupyter, folder structure, `docker-compose.yml` for PostgreSQL) — his ticket should be scoped as *extending* that existing setup (branch protection, pre-commit hooks, onboarding the other 3 laptops), not rebuilding it from scratch.

## Returned

None. Every ticket that has actual work behind it meets its acceptance criteria; nothing merged needs to be redone.

## Before the Oct 14 review

1. Confirm the reshape task's scope assumption (flagged above).
2. Romit, Pavan, and Charmiben's 14 tickets need to actually start — at current state, 70% of the team's Week 1 scope has no commits.
