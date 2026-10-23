# Weekly Supervisor Status Note

**To:** Dr. Andreas Maniatis (Supervisor)
**From:** Pavan Rella (this week's rotation)
**Date:** October 23, 2026
**Re:** COMP-8977 "Visual Analytics of Housing Affordability... in Windsor" — Week 4 status

**Scope note:** same method as last week's note (`docs/sprint1_status_note.md`) — this reviews each
member's actual committed GitHub output since then (October 16-23), not meeting time, Jira activity,
or research that never became a committed artifact.

## Overall status: core analytics layer complete across all 4 stories

Since last week's note, the project moved from "Story 4 only" to a full, working analytics layer:
SQL views now exist for all 4 stories (13 views total), all are registered as Superset datasets with
saved metrics, the historical rental-market data now spans 6 real years (Oct-20 to Oct-25) instead of
just the current survey, the Story-1 affordability bug found last week stayed fixed and verified, and
the web app went through two full redesigns (light theme, then an interactive dashboard-style hero)
on top of the existing React/Vite scaffold. CI (pre-commit, ETL tests, web lint+build) has been
required on every merge to `main` since last week and caught nothing broken this week.

## This week's real output, by person

**Romit Patel** — Automated data-quality checks for the rental-market table (row counts, rent/vacancy
ranges, duplicate keys, reliability letters; found and fixed a real bug along the way — 43 rows had a
stray space instead of a valid reliability letter, traced to the raw workbook). Extended the
historical RMS extraction to 6 real years. Wrote SQL views for Story 2 (rent YoY change, rent growth,
vacancy trend, turnover by bedroom) and the ETL README (how to run, add a dataset, read the
load-audit table). Also opened a full pipeline rebaseline (`PR #49`) that didn't make it in — real,
working code, but reviewed and correctly held back: it depends on 2 raw files this project doesn't
have, and it quietly abandons the team's reviewed star-schema design without discussion.

**Pavan Rella** — Census Profile ETL, Superset public-role configuration, KPI catalogue (19 KPIs
across all 4 stories), a PostgreSQL schema code review, and the affordability-gap index method note
(rent growth vs. renter income growth, tested on real data, with an honest limit: renter income
growth isn't computable from any source this project has extracted yet). This week: Story 4 SQL
views registered as Superset datasets, extended to cover all 13 views across every story (previously
only Story 4's 3 were registered), and a real auth bug found and fixed in the Superset registration
script itself (see below).

**Charmiben Patel** — Starts/completions ETL (long format, through the shared framework), the
story-page template and methodology page, and an embedding spike with Pavan (Superset Embedded SDK +
guest token). The spike confirms the mechanism works end-to-end but hits a real, predicted blocker:
this project has no backend server to mint guest tokens from safely, so public dashboard embedding
isn't live yet. Also profiled 2015-2025 starts history and documented honestly that CMHC's source
only supports back to a more limited real range, not the full 10 years originally scoped.

**Dhritiben Patel (PM)** — Story 1 SQL views, the Story 1 chart list and narrative v1, GitHub Actions
CI + the hosting decision (Render, deferred near Week 9), plus two full homepage redesigns (light
theme, then an interactive data-dashboard hero with real stat panels and a 3D skyline visual) on top
of the existing React scaffold — all real figures, nothing fabricated. Also reviewed Romit's PR #49
in an isolated worktree before it was held back (see above).

## A process issue found and fixed today

Registering all 13 SQL views as Superset datasets exposed a real auth bug: the script's JWT-only
login never populated Flask-Login's session state, so every dataset it created became invisible to
its own later reads (404 on GET, absent from the list) even though the row, columns, and permissions
all existed correctly — confirmed by inspecting Superset's metadata database directly, not just
re-reading the code. Fixed by switching to the classic session-cookie login; re-verified end-to-end
against a freshly restarted Superset container, all 13 datasets and their saved metrics now genuinely
visible and queryable. Same spirit as last week's PR #44 recovery: found by actually testing against
live state, not assumed to work because the code looked right.

## Known real gaps (flagged honestly, not fabricated or hidden)

- **Story 3 (supply):** Ontario/Canada-only data — no Windsor-specific starts/completions figure
  exists in CMHC's source table, so `v_story3_supply_per_1000_households` reports starts honestly
  with the households-per-1,000 columns left `NULL` rather than computing a number from mismatched
  geographies.
- **Affordability-gap index:** rent-growth side is real and tested across Windsor + all 4 comparator
  CMAs; the renter-income-growth side is `NULL` everywhere — no source extracted so far contains that
  time series.
- **Public dashboard embedding:** blocked on a backend token-minting server that doesn't exist yet
  (see Charmiben's spike above).
- **Historical rental data:** 5 real years of growth data (Oct-20 to Oct-25), not 10 — flagged
  explicitly in `docs/affordability_gap_index.md` rather than assumed to be a full decade.

## Next steps

- Decide whether to resource a backend token-minting endpoint to unblock public embedding, or defer
  it past the current scope.
- Revisit PR #49's useful pieces (its 3 working cleaners) without its unresolved blockers, if the
  team still wants that rewrite's approach.
- Continue toward the Week 4-5 analytics/dashboard milestones now that all 4 stories have a working
  SQL + Superset layer to build real charts on.

---

*This note was drafted from the team's actual GitHub history for the week, the same way as last
week's. Delivery to the supervisor (email/LMS/whatever channel the team uses) is outside this
repository and is the PM's/this week's rotation's own responsibility to send.*
