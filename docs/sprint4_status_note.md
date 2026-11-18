# Weekly Supervisor Status Note

**To:** Dr. Andreas Maniatis (Supervisor)
**From:** Charmiben Patel (this week's rotation)
**Date:** November 18, 2026
**Re:** COMP-8977 "Visual Analytics of Housing Affordability... in Windsor": Weeks 7–8 status

**Scope note:** this note uses the same method as the previous ones (`docs/sprint1_status_note.md` to `docs/sprint3_status_note.md`). It reviews each member's committed GitHub output since the last note (November 5 to 18), not meeting time or work that has not been committed. 30 pull requests were merged in this period (#107 to #136).

## Overall status: running on the university's servers; supervisor feedback applied

The project now runs on the University of Windsor's services:

- the data is in the `whva` PostgreSQL database;
- the six dashboards are on the university's Superset (https://apss.cs.uwindsor.ca);
- the website is at https://whva.cs.uwindsor.ca, served over HTTPS.

Both are reachable on the UWindsor network or through the VPN. Teammates have opened the website and the dashboards with their own UWindsor logins. Our data is also backed up every night. Story 5 now answers combined questions that join the datasets, and the changes asked for at the last supervisor meeting are in place (table below).

## This period's output, by person

**Romit Patel:**
- Finished the Story 2 page, narrative and dashboard review, and the weekly scheduled refresh with a schema guard.
- Built an interactive Story 2 dashboard with a zone explanation panel, and a light theme for all dashboards.
- For Story 5, added rental market size (rental units per 100 renter households) and a comparison of all measures by city.
- Added the "before vs from 2020" comparison to Story 3, made Story 4's vacancy chart clearer, and put key-finding charts on every story page.
- Extended the schema guard to every source file the refresh reads (18, up from 10). It found that the ten-year tables were downloaded after the check, and fixed it.

**Pavan Rella:**
- Refined Story 4 and its page, checked that every KPI shows the same number across dashboards, tuned Superset performance (indexes, a 24-hour chart cache), and wrote the methodology page.
- Added ten years of rent and vacancy (2015–2025) for all five cities to Story 4, with a 2015–2020 vs 2020–2025 comparison.
- This week: repeated the KPI and speed checks on all dashboards. Story 4's ten-year rent is now labelled "apartments + row houses" beside the apartments-only figure, and the Story 5 radar's query went from 63 ms to about 7 ms.

**Charmiben Patel:**
- Embedded all dashboards securely with guest tokens, built the Story 3 page, and made mobile and accessibility fixes.
- Linked Stories 1–4 to the combined analysis, and wrote version 2 of the design document.
- Split every dashboard into tabs that each fit one screen.
- Re-checked accessibility and phone layout after the site gained its own charts: 0 WCAG 2.1 AA violations on all 8 pages, and all 13 site charts have a text label and a data table.
- Published the website on whva, with a link mode that opens each dashboard on apss until the university's Superset allows embedding, and added a "Meet the team" section to the Home page.

**Dhritiben Patel (PM):**
- Built the Story 5 combined dashboard joining the four stories' data, including homes built against population growth and the student question, and updated the star schema in the design document.
- Added "The story in four charts" to the Home page.
- Made the dashboard builders work on the university's Superset 6.
- Added richer chart types: trendline KPIs, zone heatmaps, a city scatter, a gauge and a radar.
- Made every figure on the website come from the data, not typed by hand.
- Moved the data and dashboards to the university's database and Superset.
- Prepared the university servers: daily backups, HTTPS settings, the token-service setup and firewall rules. Also updated the data dictionary and the Story 1 narrative.

## Supervisor feedback and how the team responded

| Feedback | Response |
|---|---|
| Two years of rent says little; compare the five years before the pandemic with the five from it | Story 4 shows rent and vacancy every October 2015–2025 for all five cities, comparing 2015–2020 with 2020–2025. Story 3 compares 2016–2020 with 2021–2025 |
| The dashboards are too dense; a dashboard should not need scrolling | Every dashboard is split into tabs that each fit one screen |
| Pick the strongest findings and make them more impressive than bar charts; give the site its own look | The Home page opens with four key findings drawn by the site itself (waffle, rent vs income, ten-year line, homes built), and each story page has its own key-finding charts |
| Fewer plain bar charts | Trendline KPIs, heatmaps, a scatter, a gauge and a radar, each chosen for what its data shows |
| Where is the teamwork? | Story 5 answers combined questions that join two or more stories' data, each owned by members from different stories |

## Known gaps (stated plainly)

- **Embedding on the university's Superset:** apss does not yet let other sites embed its dashboards, so the website on whva opens each dashboard on apss (UWindsor login) instead of showing it inside the page. The required settings have been requested from the server admin; locally, embedding works.
- **Access:** the university's website and Superset are reachable only on the UWindsor network or through the VPN, not from the public internet.
- **Two manual downloads:** the Census Profile and CMHC's quarterly starts workbook refuse automated downloads and are saved by hand; the other sources download automatically.
- **Year mismatch:** combined questions compare 2020 incomes (2021 Census) with 2025 rents; each such figure states this and is presented as an upper bound.
- **Affordability-gap index:** there is still no year-by-year renter income source, so only the rent-growth side is computed.

## Next steps (November 18–25)

- If the admin enables embedding, install the guest-token service on whva so the dashboards appear inside the website, as they do locally.
- Record the university setup on the project wiki space the admin offered.
- Prepare the demo: a walkthrough script and a backup recording.
- Each member confirms their role and bio in the website's team section.

---

*Drafted from the team's GitHub history for the period, the same way as the previous notes. Sending it to the supervisor (email or the team's usual channel) is done outside this repository by this week's rotation.*
