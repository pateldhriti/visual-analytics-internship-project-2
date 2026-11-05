-- SQL views for Story 1 ("Who faces the greatest housing affordability
-- pressure?"): shelter-cost burden rate by tenure, income band, and
-- household type -- each with the burdened-household count, the total
-- household count, and the resulting percentage, not just a bare ratio.
-- Built on warehouse.fact_shelter_cost, using the exact baseline filter and
-- formulas already verified in docs/story1_questions_and_measures.md (Q1,
-- Q2, Q4) -- these views don't invent new logic, they give that
-- already-checked logic a stable name Superset can query directly instead
-- of re-deriving the same ad-hoc SQL in every chart.
--
-- Every view shares the same baseline slice: housing_suitability and
-- dwelling_condition restricted to their 'Total' rows, statistic restricted
-- to 'Number of private households' (not a confidence-interval bound).
-- Skipping this filter makes every (income, household, tenure, ratio)
-- combination appear 27x instead of once -- see docs/shelter_cost_audit.md.
--
-- total_households is the sum of the 'Spending less than 30%' and
-- 'Spending 30% or more' rows -- deliberately NOT the raw 'Total -
-- Shelter-cost-to-income ratio' row, which also includes 'Not applicable'
-- households (zero/negative income or an agricultural-operation dwelling --
-- see 98100252_MetaData.csv note 9). Those households have no computable
-- ratio at all, so StatCan's own published rate excludes them from its
-- denominator too. Confirmed by reproducing StatCan's own Census Profile
-- figures exactly (docs/story1_validation.md): using the raw Total as the
-- denominator gives Owner 10.9% / Renter 34.5%; excluding 'Not applicable'
-- gives Owner 10.9% / Renter 34.8% -- an exact match to the published
-- Census Profile characteristics 1484/1492, not just closer.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- v_story1_burden_by_tenure
-- One row per tenure (Owner, Renter): Q1.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story1_burden_by_tenure AS
SELECT
    t.tenure_name AS tenure,
    SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
             THEN f.value ELSE 0 END) AS burdened_households,
    SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                     'Spending 30% or more of income on shelter costs')
             THEN f.value ELSE 0 END) AS total_households,
    ROUND(
        100.0 * SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                          THEN f.value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                          'Spending 30% or more of income on shelter costs')
                          THEN f.value ELSE 0 END), 0),
        1
    ) AS burden_rate_pct
FROM warehouse.fact_shelter_cost f
JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
WHERE f.housing_suitability = 'Total - Housing suitability'
  AND f.dwelling_condition = 'Total - Dwelling condition'
  AND f.statistic = 'Number of private households'
  AND ib.scheme = 'statcan_bracket' AND ib.band_label = 'Total - Total income of household'
  AND f.household_type_key = 1  -- 'Total - Household type including census family structure'
  AND t.tenure_name <> 'Total'
GROUP BY t.tenure_name;

-- ============================================================
-- v_story1_burden_by_income_band
-- One row per real income bracket (excludes the Total row and the 2
-- non-count statistics rows -- Median/Average $ -- per
-- docs/story1_questions_and_measures.md rule 2): Q2.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story1_burden_by_income_band AS
SELECT
    ib.band_label AS income_band,
    ib.member_id AS income_band_sort_order,
    SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
             THEN f.value ELSE 0 END) AS burdened_households,
    SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                     'Spending 30% or more of income on shelter costs')
             THEN f.value ELSE 0 END) AS total_households,
    ROUND(
        100.0 * SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                          THEN f.value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                          'Spending 30% or more of income on shelter costs')
                          THEN f.value ELSE 0 END), 0),
        1
    ) AS burden_rate_pct
FROM warehouse.fact_shelter_cost f
JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
WHERE f.housing_suitability = 'Total - Housing suitability'
  AND f.dwelling_condition = 'Total - Dwelling condition'
  AND f.statistic = 'Number of private households'
  AND f.household_type_key = 1
  AND t.tenure_name = 'Total'
  AND ib.scheme = 'statcan_bracket'
  AND ib.member_id BETWEEN 2 AND 12  -- excludes member 1 (Total) and 13/14 (Median/Average $, not counts)
GROUP BY ib.band_label, ib.member_id;

-- ============================================================
-- v_story1_burden_by_household_type
-- One row per household type, grouped by household_type_key (StatCan's own
-- member_id), not the text label alone -- 2 label pairs collide
-- ("Without children" / "With children" appear under 2 different parent
-- branches each) -- see docs/shelter_cost_audit.md. Q4.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story1_burden_by_household_type AS
SELECT
    ht.household_type_key,
    ht.household_type_label AS household_type,
    ht.parent_member_id,
    SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
             THEN f.value ELSE 0 END) AS burdened_households,
    SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                     'Spending 30% or more of income on shelter costs')
             THEN f.value ELSE 0 END) AS total_households,
    ROUND(
        100.0 * SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                          THEN f.value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN f.shelter_cost_ratio IN ('Spending less than 30% of income on shelter costs',
                          'Spending 30% or more of income on shelter costs')
                          THEN f.value ELSE 0 END), 0),
        1
    ) AS burden_rate_pct
FROM warehouse.fact_shelter_cost f
JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
JOIN warehouse.dim_household_type ht ON ht.household_type_key = f.household_type_key
WHERE f.housing_suitability = 'Total - Housing suitability'
  AND f.dwelling_condition = 'Total - Dwelling condition'
  AND f.statistic = 'Number of private households'
  AND ib.scheme = 'statcan_bracket' AND ib.band_label = 'Total - Total income of household'
  AND t.tenure_name = 'Total'
GROUP BY ht.household_type_key, ht.household_type_label, ht.parent_member_id;

-- ============================================================
-- v_story1_burden_severity
-- One row per tenure (Owner, Renter): of the households already spending
-- 30%+ of income on shelter, how many are in the "30% to less than 100%"
-- band, and how many spend 100% or more.
--
-- StatCan's table publishes "30% to less than 100%" as a sub-category of
-- "Spending 30% or more" (member 4 has parent member 3 in
-- data/raw/shelter_cost/98100252_MetaData.csv) and has no separate
-- "100% or more" row. Because the parent is the sum of its parts, the
-- remainder (30%+ minus 30%-to-under-100%) is the households spending 100%
-- or more of income on shelter. It is derived, not published, and StatCan
-- rounds every count to a multiple of 5, so treat it as approximate.
--
-- Column names are kept from the first version of this view (severe_* and
-- unaccounted_*) so existing Superset charts keep working:
--   severe_30_to_99 / severe_pct_of_burdened   -> the 30%-to-under-100% band
--   unaccounted_households / _pct_of_burdened  -> the derived 100%-or-more group
-- "Severe" is not an official StatCan term; chart labels use the band names.
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story1_burden_severity AS
SELECT
    t.tenure_name AS tenure,
    SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
             THEN f.value ELSE 0 END) AS total_burdened,
    SUM(CASE WHEN f.shelter_cost_ratio = '30% to less than 100%'
             THEN f.value ELSE 0 END) AS severe_30_to_99,
    ROUND(
        100.0 * SUM(CASE WHEN f.shelter_cost_ratio = '30% to less than 100%' THEN f.value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                          THEN f.value ELSE 0 END), 0),
        1
    ) AS severe_pct_of_burdened,
    SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
             THEN f.value ELSE 0 END)
        - SUM(CASE WHEN f.shelter_cost_ratio = '30% to less than 100%' THEN f.value ELSE 0 END)
        AS unaccounted_households,
    ROUND(
        100.0 * (
            SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                     THEN f.value ELSE 0 END)
            - SUM(CASE WHEN f.shelter_cost_ratio = '30% to less than 100%' THEN f.value ELSE 0 END)
        ) / NULLIF(SUM(CASE WHEN f.shelter_cost_ratio = 'Spending 30% or more of income on shelter costs'
                          THEN f.value ELSE 0 END), 0),
        1
    ) AS unaccounted_pct_of_burdened
FROM warehouse.fact_shelter_cost f
JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
WHERE f.housing_suitability = 'Total - Housing suitability'
  AND f.dwelling_condition = 'Total - Dwelling condition'
  AND f.statistic = 'Number of private households'
  AND ib.scheme = 'statcan_bracket' AND ib.band_label = 'Total - Total income of household'
  AND f.household_type_key = 1
  AND t.tenure_name <> 'Total'
GROUP BY t.tenure_name;

-- ============================================================
-- v_story1_burden_severity_breakdown
-- Long-format reshape of v_story1_burden_severity, built for a stacked
-- chart: one row per (tenure, category), category being either
-- "30% to under 100%" or "100% or more" -- the same 2 percentages
-- v_story1_burden_severity reports as separate columns, reshaped so a
-- single stacked bar per tenure shows both segments (each tenure sums to
-- 100%).
-- ============================================================
CREATE OR REPLACE VIEW warehouse.v_story1_burden_severity_breakdown AS
SELECT tenure, '30% to under 100%' AS category, severe_pct_of_burdened AS pct_of_burdened
FROM warehouse.v_story1_burden_severity
UNION ALL
SELECT tenure, '100% or more' AS category, unaccounted_pct_of_burdened AS pct_of_burdened
FROM warehouse.v_story1_burden_severity;
