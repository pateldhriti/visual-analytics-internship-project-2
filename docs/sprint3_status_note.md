# Weekly Supervisor Status Note

**To:** Dr. Andreas Maniatis (Supervisor)
**From:** Romit Patel (this week's rotation)
**Date:** November 5, 2026
**Re:** COMP-8977 "Visual Analytics of Housing Affordability... in Windsor" — Weeks 5–6 status

**Scope note:** same method as the previous notes (`docs/sprint1_status_note.md`, `docs/sprint2_status_note.md`): this reviews each member's committed GitHub output since the last note (October 24 to November 5), not meeting time or work that has not been committed. 22 pull requests were merged in this period (#82 to #106 except #83–85).

## Overall status: functional prototype complete; next phase is integrating the stories

All five stories now have a Superset dashboard, and the React website presents them with narrative, KPIs and embedded or linked dashboards. The project is presented as a functional prototype at the November 5 interim demo. Following the supervisor meeting, the main work for the next sprint is to make the stories connect through questions that join datasets, rather than presenting five separate pieces.

## This period's output, by person

**Romit Patel** — One-command refresh of the load pipeline (`etl/refresh_all.py`), the Story 2 rental-market dashboard with turnover and rental-stock tiles, Story 1's final dashboard layout and a fix for its filters conflicting with the KPI tiles, Story 2 exploratory findings and the pipeline progress-review slides. This week: a **weekly scheduled refresh with a schema guard** that stops and raises an alert if any source file's columns change (it catches a real case: CMHC renamed "Bachelor" to "Studio" between its 2024 and 2025 Windsor workbooks); a review pass on the Story 2 dashboard (monthly-rent labels, readable table columns, filter defaults, a data note); the final Story 2 narrative; and the Story 2 React page with its live dashboard embedded.

**Pavan Rella** — Story 4 comparison dashboard (including a fix for a missing Windsor row), filter and cross-filter standards for every dashboard, Superset reliability tuning for hosting, formatting polish on Dashboards 1 and 2, the Dwelling Scope filter on the rental dashboard, corrected KPI-catalogue figures, and the dashboards progress-review slides.

**Charmiben Patel** — Dashboard 1 (Executive Overview), the zone-level section of the rental dashboard, a usability review and user-facing insights for Dashboards 1–2, cross-dashboard polish for embedded widths, the Story 3 housing-supply dashboard on Windsor's own monthly data (StatCan 34-10-0154-01), Story 3 exploratory findings, and the **guest-token backend** that lets the Story 1 page embed its dashboard securely with the Superset Embedded SDK (the blocker reported in the last note is resolved).

**Dhritiben Patel (PM)** — Two front-end redesigns (sidebar, KPI tiles and embedded dashboards, then the current theme), the Story 5 conclusions dashboard and page, the Story 1 exploratory findings, splitting the CMHC comparison data into its own fact table, and public access for the Story 4 datasets. This week: the final Story 1 narrative and React page, a review pass on the Story 1 dashboard (it now labels the 30%-to-under-100% band correctly and identifies the "100% or more" group), production hardening (HTTPS, secrets, daily tested backups, firewall rules), an updated data dictionary covering every table and view, and a decision log of 23 project decisions. Also drafted the design document requested at the supervisor meeting.

## Supervisor feedback and how the team is responding

| Feedback | Response |
|---|---|
| The four stories each use their own file; where is the teamwork? | The datasets share keys (tenure, income, Windsor CMA, year). The next sprint builds combined questions on them, each owned by two members from different stories — for example, comparing renter incomes (Story 1) with rents by unit size (Story 2). |
| Design before implementing | Design document drafted (version 1); the current build is treated as the functional prototype. |
| Do not decide chart types (pie or bar) in advance | Chart types for the combined questions will be chosen once their data is built. |
| Take initiative on blockers | Following up with IT support on server access rights for deployment is an immediate action item for the PM, on the existing email thread. |

## Known gaps (stated plainly)

- **Integration:** Story 5 currently places one conclusion from each story side by side; no chart yet joins two datasets.
- **Deployment:** nothing is hosted yet. The production configuration (HTTPS, backups, firewall) is ready in the repository and is scheduled for November 19–26.
- **Year mismatch:** income is from the 2021 Census (2020 incomes) and rents from 2025; combined questions must adjust for or clearly label this.
- **Affordability-gap index:** still has no renter income growth source; only the rent-growth side is computed.
- **Local stability:** Docker Desktop on the development laptop restarted several times under heavy database load; services recovered automatically and no data was lost, but heavy queries are avoided on that machine.

## Next steps (November 5–12)

- Research and agree the combined questions and confirm whether a fifth dataset is needed (for example income by age for a student question).
- Build the first joined SQL view (renter income compared with rent by unit size) and check it against the numbers in the design document.
- Register the weekly scheduled refresh on the machine that hosts the database and set the alert webhook.
- Finalize the design document with the supervisor's comments.

---

*Drafted from the team's GitHub history for the period, the same way as the previous notes. Sending it to the supervisor (email or the team's usual channel) is done outside this repository by this week's rotation.*
