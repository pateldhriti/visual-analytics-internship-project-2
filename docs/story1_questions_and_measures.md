# Story 1 — Questions and Measures

**Story 1 (proposal):** "Who faces the greatest housing affordability pressure?"

**Data source:** `data/staging/windsor_shelter_cost_long.csv` (produced by `etl/reshape_shelter_cost_long.py`), columns: `income_group`, `household_type`, `household_type_member_id`, `housing_suitability`, `dwelling_condition`, `statistic`, `shelter_cost_ratio`, `tenure`, `value`, `symbol`. This file keeps **all 7 dimensions** (not just the 4 named in Story 1) — housing suitability, dwelling condition, and statistic are preserved as columns rather than pre-filtered out, so every question below must explicitly restrict to the baseline slice itself.

**Three rules every formula below follows** (all documented pitfalls from the audit, and all re-confirmed while computing these examples):
1. Every question filters to `housing_suitability = "Total - Housing suitability"`, `dwelling_condition = "Total - Dwelling condition"`, and `statistic = "Number of private households"` — the straightforward household count, not a suitability/condition breakdown or a confidence-interval bound. Skipping this filter means each `(income, household, tenure, ratio)` combination appears 27 times instead of once, which breaks any formula that expects a single value per combination.
2. `income_group` includes two non-count rows — `"Median total income of household ($)"` and `"Average total income of household ($)"` — which are dollar statistics, not household counts. Excluded from every question that ranks or sums across income brackets.
3. `household_type` has 16 real categories but only 14 distinct text labels (two label-collision pairs). Any question that groups by household type uses `household_type_member_id` alongside the text label, not the text label alone.

---

### Q1. How does the affordability burden differ between owners and renters?

- **Columns:** `tenure`, `shelter_cost_ratio`, `value`
- **Filter:** baseline slice (rule 1) + `income_group = "Total - Total income of household"`, `household_type = "Total - Household type including census family structure"`
- **Formula:** `value[ratio="Spending 30% or more..."] / value[ratio="Total - Shelter-cost-to-income ratio"] * 100`, computed separately per `tenure`
- **Verified result:** Owner 10.9% (13,005 / 119,125) vs. Renter 34.5% (15,735 / 45,605) — renters are burdened more than 3x as often as owners.

### Q2. Which household income bracket faces the greatest burden?

- **Columns:** `income_group`, `shelter_cost_ratio`, `value`
- **Filter:** baseline slice (rule 1) + `household_type = "Total - ..."`, `tenure = "Total"`, **excluding** the Median/Average income rows
- **Formula:** per `income_group`, same % formula as Q1, ranked descending
- **Verified result (top 3):** $10,000–$19,999: 76.4%; Under $10,000: 73.6%; $20,000–$29,999: 56.2% — burden drops sharply as income rises, as expected, but worth showing because it quantifies exactly how sharply.

### Q3. Within the "spending 30%+" group, how much is in the most extreme range, and what's left over?

- **Columns:** `shelter_cost_ratio`, `value`
- **Filter:** baseline slice (rule 1) + `income_group`, `household_type` = Total, `tenure = "Total"`
- **Formula:** compare `value[ratio="30% to less than 100%"]` to `value[ratio="Spending 30% or more..."]`
- **Verified result:** 26,210 of 28,745 (91.2%) are in the 30–<100% band; a residual of 2,535 households (8.8%) is **not accounted for by any published sub-category** — flagged as an open data-quality question in `docs/shelter_cost_audit.md`, not assumed to be 100%+ spenders without a source for that label.

### Q4. Which household type faces the greatest burden?

- **Columns:** `household_type`, `household_type_member_id`, `shelter_cost_ratio`, `value`
- **Filter:** baseline slice (rule 1) + `income_group = "Total - ..."`, `tenure = "Total"`
- **Formula:** per `(household_type, household_type_member_id)`, same % formula as Q1, ranked descending
- **Verified result (top 3):** Non-census-family one-person households: 32.7%; non-census-family households overall: 30.9%; one-parent families (no additional persons): 23.2% — all well above the Windsor-wide baseline of 17.4%.

### Q5. How many households fall outside the ratio calculation entirely?

- **Columns:** `shelter_cost_ratio`, `value`
- **Filter:** baseline slice (rule 1) + `income_group`, `household_type` = Total, `tenure = "Total"`
- **Formula:** `value[ratio="Not applicable"] / value[ratio="Total"] * 100`
- **Verified result:** 510 / 164,730 = 0.31%. Per the source metadata, this category covers households on an agricultural operation or with zero/negative income — small enough in Windsor to mention but not a major story element on its own.

---

## Dependency note

These formulas are verified against `data/staging/windsor_shelter_cost_long.csv` directly (local file, not yet in Postgres). Before Superset can build these into dashboard charts, this long-format table needs to be loaded into the database — it currently only has the wide-format `windsor_shelter_cost` table (see earlier project discussion). That load step is Romit/Pavan's territory (ER model, Docker/Superset setup), not part of this task.
