# Final Report — Limitations and Future Work (draft)

**Windsor Housing Visual Analytics** · COMP-8977 Internship/Project-2, Fall 2026
**Draft:** 19 November 2026, for the final report (follows the results and evaluation sections). Places that need a citation or a result still to come are marked **[TODO]**.

---

## Limitations

The findings are descriptive and rest on official statistics; their limits come mainly from what those statistics measure, when, and at what geography. Each limit below is also stated where it matters on the dashboards or the website.

### Data coverage

1. **One Census, and 2020 incomes.** Every affordability measure (Story 1, and Story 5's income side) comes from the 2021 Census, whose incomes are for 2020. That was a pandemic year in which government benefits raised many low incomes, so the share of renters spending 30% or more on shelter may be lower than in a typical year. **[TODO: cite Statistics Canada's note on pandemic benefits and 2021 housing indicators.]** The next comparable figures are the 2026 Census, published from 2027.
2. **No yearly income data at the city level.** Rents and vacancy are surveyed every October, but renter incomes only every five years. The project therefore cannot measure whether rents rose faster than incomes year by year. The affordability-gap index was designed but left empty (`docs/affordability_gap_index.md`), and the "Windsor 2030" projection has to assume income growth (2%, 3% or 4% a year) instead of measuring it.
3. **Only purpose-built rentals.** CMHC's Rental Market Survey covers buildings with three or more rental units. Rented condominiums, basement apartments and rented houses (the secondary market) are not included, although many Windsor renters live in them. Rents and vacancy in the dashboards describe the purpose-built market, not every renter's situation; the Census side (Story 1) does cover all renter households.
4. **Two scopes in CMHC's tables.** CMHC publishes Windsor's figures for apartments only and for apartments and row houses together, but its city comparisons for apartments only. The two differ slightly (October 2025 vacancy 3.7% against 3.6%). Each chart states its scope, but a reader comparing two charts must notice it.
5. **Suppressed and low-reliability estimates.** CMHC suppresses estimates too unreliable to publish (shown as gaps, for example 3-bedroom vacancy) and grades the rest from "a" (excellent) to "d" (use with caution). Zone- and unit-size breakdowns are the most affected; the zone panel says when a figure is rated "d".
6. **Random rounding.** Statistics Canada rounds every Census count to a multiple of 5, so parts do not always add to totals; for small groups (such as owners with incomes under $10,000) this moves a rate by a point or more.

### Comparability over time and place

7. **Boundary change in 2022.** CMHC adopted the 2021 Census CMA boundaries from its 2022 survey and split Windsor's zones differently; it revised the previous year's figures (Windsor's October 2022 2-bedroom rent: $1,197 first published, $1,174 revised). The project uses the revised figures, but comparisons across 2021-2022, and the 2021 rental-units-per-renter ratio, should be read with caution.
8. **No income below the CMA.** The Census table used for Story 1 has no zone-level breakdown, so affordability cannot be shown by rental zone; the zone tabs show rents and vacancy only, not who can afford them.
9. **Estimated housing need.** "Homes needed for population growth" divides population growth by 2021 household size, and completions are not net of demolitions or conversions. The ranking of the five cities is more reliable than the exact share (Windsor: 59%).
10. **Choice of comparison cities.** Four Ontario CMAs of similar size were chosen (`docs/comparator_cmas_justification.md`), with Toronto added for one comparison. Other choices could change Windsor's rank on some measures.

### Process and system

11. **Five files downloaded by hand.** The Census Profile refuses scripted downloads, CMHC renames its quarterly workbook, and CMHC's Housing Market Information Portal has no download link a script can use. These files go stale until someone saves a new copy; the Story 3 build warns when the intended-market files are behind the monthly data (`etl/README.md`).
12. **Dashboards behind a university login, opened rather than embedded.** The university's Superset blocks embedding in other sites and requires a UWindsor login, so the website links to each dashboard instead of showing it on the page, and visitors outside the university can read the website but not explore the dashboards. **[TODO: update if the admin enables embedding or public access.]**
13. **Two Superset versions.** Development uses Superset 3.1 and production Superset 6. One set of builder scripts produces both, but small differences remain (for example how a series order is computed), which each change must be checked against.
14. **One production server, maintained by students.** The website and backups run on one university virtual machine; the database and Superset are the university's. There is no failover, and monitoring alerts go to a log file unless a webhook is configured.
15. **Small user test.** The evaluation rests on six think-aloud sessions with testers recruited by the team. **[TODO: replace with the results and their limits once the sessions are done.]**

---

## Future work

### More and newer data

- **The 2026 Census** (from 2027): rerun Story 1 and Story 5's income side with 2025 incomes, and measure the change since 2021, which the current data cannot show. The pipeline already handles a new Census year; the table identifiers and the schema-guard snapshot need updating.
- **Yearly incomes from tax data.** Statistics Canada's tax-filer family income tables give yearly incomes by CMA. Adding them would let the affordability-gap index (rent growth against income growth) be computed every year instead of assumed.
- **The secondary rental market.** CMHC's secondary rental market estimates, where published for Windsor, or asking-rent data from listing reports, would cover renters outside purpose-built buildings. Asking rents would also show what a new tenant pays today, which Story 2 currently approximates with the rent of vacant units.
- **Neighbourhood detail.** Census-tract or zone-level shelter-cost data (a custom tabulation from Statistics Canada) would allow an affordability map of Windsor.
- **Automatic CMHC downloads.** If CMHC offers its portal data through an API or stable file links, the five manual files could be downloaded by the weekly refresh like the rest.

### Analysis

- **An interactive scenario tool.** Let the reader choose rent and income growth for "Windsor 2030" instead of three fixed scenarios, with the range shown honestly.
- **Uncertainty on the dashboards.** Show CMHC's reliability grades on charts (for example lighter bars for "c" and "d"), not only in the zone panel.
- **More comparison cities.** The extracts already read every Canadian CMA; any city could become a comparison with a configuration change.

### Platform

- **Public, embedded dashboards.** With the university's agreement, enable embedding on apss and public read-only access, so the website shows each dashboard on its page (the code already supports it: rebuild without `VITE_EMBED_MODE=link`).
- **Alerting and failover.** Connect the uptime and refresh alerts to a Teams channel; document a recovery procedure for whva using the tested backup restore.
- **Accessibility and language.** A full WCAG 2.1 AA audit of the website and dashboards, and a French version, as expected of public information in Canada.
- **A template for other cities.** The pipeline, views and builders are parameterized by CMA code in most places; packaging them so another city can be analysed with a configuration file would turn the project into a reusable tool.
