# Sprint 1 Acceptance Review and Status Note

**To:** Dr. Andreas Maniatis (Supervisor)
**From:** Dhritiben Patel, Project Manager
**Date:** October 16, 2026
**Re:** COMP-8977 "Visual Analytics of Housing Affordability... in Windsor" — Sprint 1 status

**Scope note:** no standalone Jira-based definition of done exists outside this repository, so this
review checks each member's actual GitHub output against the proposal's own Week 1-3 deliverables
and per-person responsibility table (Sections 5.2-5.3). Jira activity, meeting time, and research
that didn't produce a committed artifact aren't visible to this review and aren't counted against
anyone below.

## Overall status: ahead of schedule in aggregate, uneven by person

We're at the end of Week 3 (data-understanding phase). Against that phase alone, we're done: every
core source is downloaded, profiled, and audited, and a data dictionary exists for all 4 sources
(`docs/shelter_cost_audit.md`, `docs/cmhc_rms_sheet_catalogue.md`, `docs/cmhc_starts_completions_audit.md`,
`docs/data_dictionary_supply.md`, `docs/data_dictionary_census_comparison.md`). In practice the team
has already delivered substantial pieces of Weeks 4-8 too: a populated PostgreSQL warehouse (4 fact
tables, 0 unmatched dimension keys), Superset installed with Story 4 datasets registered, SQL views
for Stories 3 and 4, and a React site scaffold with navigation and wireframes v1.

That aggregate pace masks uneven individual tracking against assigned roles:

| Member | Assigned Week 1-3 role | What's actually committed under their name |
|---|---|---|
| Dhritiben Patel | Narrative flow, proposal writing | Proposal doc, `docs/story1_questions_and_measures.md`, `docs/story1_narrative_outline.md`, plus most of Weeks 4-5's dev-environment/Postgres setup and (this week) the production affordability ETL, its unit tests, and 2 data dictionaries |
| Romit Patel | Validate/profile all files, document data quality (Weeks 2-3) | Raw-staging loader + 2 real robustness fixes (encoding detection, unreadable-file handling), the conceptual ER model, and one workbook profile (CMHC RMS). The other 3 sources' audits were authored by teammates, not Romit, despite being his assigned Week-3 deliverable |
| Pavan Rella | Review Superset, map questions to measures (Weeks 1-3) | Far exceeds Week 3 scope: fact-table population for all 4 sources, 9 CMHC sheet extractions, comparator-CMA selection, Story 4 SQL views and Superset datasets — effectively Weeks 4-8 work already done |
| Charmiben Patel | Repo structure, hosting comparison (Week 3) | React scaffold, layout/nav shell, wireframes v1, a peer-test of the affordability ETL, Story 3 SQL views and narrative draft. Her own assigned Week-3 deliverable (hosting comparison) was written by Dhritiben, not Charmiben |

None of this is a quality problem — everything reviewed checks out (see below) — but role boundaries
have drifted from the proposal's plan, and Romit's own committed output is the thinnest relative to
his "Data Engineering Lead" title. Worth a quick team check-in, not an escalation.

## A process issue found and fixed today

`main` was found to be silently missing 7 merged PRs' worth of work (Story 3 views, supply
data-quality checks, a Story 3 narrative draft, and Charmiben's peer-test report on the
affordability ETL) — GitHub showed them merged, but the commits weren't reachable from `main`,
most likely from an unrecorded rewind rather than a tracked force-push. Recovered today (PR #44);
the non-web pieces are back on `main`, verified against a fresh schema rebuild. Flagging this so
the team tightens the branch/merge discipline already documented in `docs/onboarding_checklist.md`
going forward — this kind of silent loss is exactly what branch protection doesn't catch.

## Today's completed items (Dhritiben's Sprint 1 list)

1. **Affordability ETL, production** — `etl/run_affordability_etl.py`, single job, logs row counts,
   fixes both bugs Charmiben's peer test found, adds a standardized `data_quality_flag` column.
   Verified end-to-end against a rebuilt warehouse.
2. **Unit tests for the affordability ETL** — 15 pytest cases, symbol handling / row counts /
   totals-vs-raw-file, no database required.
3. **Story 1 narrative outline** — page flow, 4 of 5 verified findings selected, chart order and
   rationale.
4. **This status note.**

**In progress:** hosting test on a free VM (Oracle Cloud Always Free) — provisioning is in
progress; Docker install, sample-data load, memory/page-load measurement, and the go/no-go note
will follow once the VM is up.

## Next steps

- Quick sync with Romit on Week 3-4 data-quality ownership so his committed output matches his role
  going forward.
- Close out the hosting VM test this week.
- Begin Week 4's ETL/schema work in earnest now that Week 3's audit deliverables are complete.
