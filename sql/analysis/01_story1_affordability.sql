-- =============================================================================
-- STORY 1 -- HOUSING AFFORDABILITY (Windsor CMA, Census 2021)
-- Source: clean.shelter_cost (StatCan 98-10-0252-01); clean.census_profile for
-- the published cross-check only.
--
-- Shelter-cost-to-income ratio categories in the source (inspected):
--   'Total - Shelter-cost-to-income ratio'                 = all households
--   'Spending less than 30% of income on shelter costs'    (applicable)
--   'Spending 30% or more of income on shelter costs'      (applicable; the burden numerator)
--   '30% to less than 100%'                                (subset of 30%+)
--   'Not applicable'                                       (household income <= 0)
--
-- Burden rate (standard 30%+ measure):
--   households spending 30% or more
--   / households to which the ratio is applicable
--     = 'Total' - 'Not applicable'
-- This matches the Census Profile's own base (characteristic 1465, "households
-- with household total income greater than zero").
--
-- Missing 'Not applicable' rows (agreed rule): the extract has no 'Not
-- applicable' row for any income band of $10,000 and over. 'Not applicable'
-- means household income <= 0, so those bands cannot contain such households:
-- the count is taken as 0 *by definition* and flagged
-- (not_applicable_basis = 'zero_by_definition'). Anywhere else a missing row
-- leaves the denominator and rate NULL (not_applicable_basis = 'missing',
-- rate_null_reason says why). No other missing value is filled.
--
-- Only household counts are used (measure_kind = 'household_count'); the
-- Median/Average income rows are dollars, not households. The extract only
-- holds the Total housing-suitability / Total dwelling-condition slice.
-- StatCan randomly rounds counts to multiples of 5, so components can differ
-- from published totals by a few households.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- analysis.story1_shelter_cost_burden
-- Grain: one row per income group x household type x tenure (member ids from
-- the source COORDINATE). The base of every other Story 1 view.
-- Includes Total rows -- never sum this view across a dimension without
-- filtering to one level (see is_*_total flags).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_shelter_cost_burden AS
WITH pivot AS (
    SELECT
        geography,
        ref_year,
        income_group_member_id,
        max(income_group)   AS income_group,
        household_type_member_id,
        max(household_type) AS household_type,
        tenure_member_id,
        max(tenure)         AS tenure,
        max(value) FILTER (WHERE shelter_cost_ratio = 'Total - Shelter-cost-to-income ratio')              AS total_households,
        max(value) FILTER (WHERE shelter_cost_ratio = 'Spending less than 30% of income on shelter costs') AS below_30_households,
        max(value) FILTER (WHERE shelter_cost_ratio = 'Spending 30% or more of income on shelter costs')   AS burden_30_plus_households,
        max(value) FILTER (WHERE shelter_cost_ratio = '30% to less than 100%')                             AS burden_30_to_under_100_households,
        max(value) FILTER (WHERE shelter_cost_ratio = 'Not applicable')                                    AS not_applicable_households_published,
        max(coordinate) FILTER (WHERE shelter_cost_ratio = 'Total - Shelter-cost-to-income ratio')            AS total_coordinate,
        max(coordinate) FILTER (WHERE shelter_cost_ratio = 'Spending 30% or more of income on shelter costs') AS burden_30_plus_coordinate,
        max(coordinate) FILTER (WHERE shelter_cost_ratio = 'Not applicable')                                  AS not_applicable_coordinate
    FROM clean.shelter_cost
    WHERE measure_kind = 'household_count'
      AND value_status = 'published'
    GROUP BY geography, ref_year, income_group_member_id, household_type_member_id, tenure_member_id
),
basis AS (
    SELECT
        p.*,
        CASE
            WHEN not_applicable_households_published IS NOT NULL THEN 'published'
            WHEN income_group NOT IN ('Total - Total income of household', 'Under $10,000') THEN 'zero_by_definition'
            ELSE 'missing'
        END AS not_applicable_basis
    FROM pivot p
),
measures AS (
    SELECT
        b.*,
        CASE not_applicable_basis
            WHEN 'published' THEN not_applicable_households_published
            WHEN 'zero_by_definition' THEN 0
        END AS not_applicable_households
    FROM basis b
)
SELECT
    geography,
    ref_year,
    income_group_member_id,
    income_group,
    income_group = 'Total - Total income of household'                        AS is_income_total,
    household_type_member_id,
    household_type,
    household_type = 'Total - Household type including census family structure' AS is_household_type_total,
    tenure_member_id,
    tenure,
    tenure = 'Total - Tenure'                                                 AS is_tenure_total,
    total_households,
    not_applicable_households,
    not_applicable_basis,
    total_households - not_applicable_households                             AS applicable_households,
    below_30_households,
    burden_30_plus_households,
    burden_30_to_under_100_households,
    -- derived: '30% or more' minus '30% to less than 100%' = 100% or more
    burden_30_plus_households - burden_30_to_under_100_households            AS burden_100_plus_households_derived,
    -- NULL (never capped) when random rounding makes the 30%+ count exceed the
    -- applicable households -- only happens in a few very small cells.
    CASE WHEN burden_30_plus_households <= total_households - not_applicable_households
         THEN round(100.0 * burden_30_plus_households
                    / NULLIF(total_households - not_applicable_households, 0), 4)
    END                                                                       AS burden_30_plus_pct,
    CASE
        WHEN total_households IS NULL THEN 'total_row_missing'
        WHEN burden_30_plus_households IS NULL THEN 'burden_30_plus_row_missing'
        WHEN not_applicable_basis = 'missing' THEN 'not_applicable_row_missing'
        WHEN total_households - not_applicable_households <= 0 THEN 'no_applicable_households'
        WHEN burden_30_plus_households > total_households - not_applicable_households
             THEN 'numerator_exceeds_denominator_rounding'
    END                                                                       AS rate_null_reason,
    -- audit: applicable households vs the sum of the two applicable categories
    -- (differs only by StatCan random rounding when both are published)
    (total_households - not_applicable_households)
        - (below_30_households + burden_30_plus_households)                  AS applicable_minus_category_sum,
    total_coordinate,
    burden_30_plus_coordinate,
    not_applicable_coordinate
FROM measures;

COMMENT ON VIEW analysis.story1_shelter_cost_burden IS
    'Grain: income group x household type x tenure. 30%+ shelter-cost burden with numerator, denominator and source coordinates. Includes Total rows.';


-- -----------------------------------------------------------------------------
-- analysis.story1_affordability_by_tenure
-- Question: how different is shelter-cost burden for renters and owners?
-- Grain: one row per tenure (Total, Owner, Renter); all incomes, all household types.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_affordability_by_tenure AS
SELECT
    geography,
    ref_year,
    tenure_member_id,
    tenure,
    burden_30_plus_households AS numerator_burden_30_plus_households,
    applicable_households     AS denominator_applicable_households,
    total_households,
    not_applicable_households,
    not_applicable_basis,
    burden_30_plus_pct,
    rate_null_reason,
    burden_30_plus_coordinate,
    total_coordinate,
    not_applicable_coordinate
FROM analysis.story1_shelter_cost_burden
WHERE is_income_total
  AND is_household_type_total;

COMMENT ON VIEW analysis.story1_affordability_by_tenure IS
    'Grain: tenure. 30%+ burden for Owner, Renter and all households (numerator / applicable-household denominator).';


-- -----------------------------------------------------------------------------
-- analysis.story1_tenure_burden_gap
-- Question: how large is the renter-owner difference?
-- Grain: one row. Gap in percentage points and renter/owner ratio, with both
-- numerators and denominators.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_tenure_burden_gap AS
SELECT
    o.geography,
    o.ref_year,
    o.numerator_burden_30_plus_households AS owner_burden_30_plus_households,
    o.denominator_applicable_households   AS owner_applicable_households,
    o.burden_30_plus_pct                  AS owner_burden_30_plus_pct,
    r.numerator_burden_30_plus_households AS renter_burden_30_plus_households,
    r.denominator_applicable_households   AS renter_applicable_households,
    r.burden_30_plus_pct                  AS renter_burden_30_plus_pct,
    round(r.burden_30_plus_pct - o.burden_30_plus_pct, 4)                 AS renter_minus_owner_pct_points,
    round(r.burden_30_plus_pct / NULLIF(o.burden_30_plus_pct, 0), 4)      AS renter_to_owner_rate_ratio
FROM analysis.story1_affordability_by_tenure o
JOIN analysis.story1_affordability_by_tenure r
  ON r.geography = o.geography AND r.ref_year = o.ref_year
WHERE o.tenure = 'Owner'
  AND r.tenure = 'Renter';

COMMENT ON VIEW analysis.story1_tenure_burden_gap IS
    'Grain: one row. Renter minus owner 30%+ burden (percentage points) and renter/owner ratio.';


-- -----------------------------------------------------------------------------
-- analysis.story1_affordability_by_income_group
-- Question: how does shelter-cost burden vary by income group?
-- Grain: one row per income band x tenure; all household types. The 11 bands
-- (Under $10,000 ... $100,000 and over) partition households, so the Total
-- income row and the Median/Average income rows are excluded.
-- share_of_burdened_households_pct = the band's share of all 30%+ households of
-- the same tenure.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_affordability_by_income_group AS
SELECT
    b.geography,
    b.ref_year,
    b.income_group_member_id AS income_group_order,
    b.income_group,
    b.tenure_member_id,
    b.tenure,
    b.burden_30_plus_households AS numerator_burden_30_plus_households,
    b.applicable_households     AS denominator_applicable_households,
    b.total_households,
    b.not_applicable_households,
    b.not_applicable_basis,
    b.burden_30_plus_pct,
    b.rate_null_reason,
    t.burden_30_plus_households AS tenure_total_burden_30_plus_households,
    round(100.0 * b.burden_30_plus_households / NULLIF(t.burden_30_plus_households, 0), 4)
                                AS share_of_burdened_households_pct,
    b.burden_30_plus_coordinate
FROM analysis.story1_shelter_cost_burden b
JOIN analysis.story1_shelter_cost_burden t
  ON t.tenure_member_id = b.tenure_member_id
 AND t.is_income_total
 AND t.is_household_type_total
WHERE b.is_household_type_total
  AND NOT b.is_income_total;

COMMENT ON VIEW analysis.story1_affordability_by_income_group IS
    'Grain: income band x tenure (household type = Total). 30%+ burden per band and the band''s share of burdened households.';


-- -----------------------------------------------------------------------------
-- analysis.story1_affordability_by_household_type
-- Question: how does shelter-cost burden vary by household type?
-- Grain: one row per household type member x tenure; all incomes.
-- The 16 members form a hierarchy (StatCan's census family structure; parent
-- and level below follow the source's member order and labels, and are checked
-- by etl/validate_analysis_views.py: children sum to parents within rounding).
-- Two labels repeat ('Without children' / 'With children'), so use
-- household_type_member_id or household_type_path, and never sum rows across
-- different hierarchy levels.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_affordability_by_household_type AS
WITH hierarchy (member_id, parent_member_id, hierarchy_level, is_leaf) AS (
    VALUES
        (1, NULL, 0, false),   -- Total - Household type including census family structure
        (2, 1,    1, false),   -- Census-family households
        (3, 2,    2, false),   -- One-census-family households without additional person
        (4, 3,    3, false),   -- One couple census family without other persons in the household
        (5, 4,    4, true),    -- Without children
        (6, 4,    4, true),    -- With children
        (7, 3,    3, true),    -- ... without additional persons: one-parent family
        (8, 2,    2, false),   -- One-census-family households with additional persons
        (9, 8,    3, false),   -- One couple census family with other persons in the household
        (10, 9,   4, true),    -- Without children
        (11, 9,   4, true),    -- With children
        (12, 8,   3, true),    -- ... with additional persons: one-parent family
        (13, 2,   2, true),    -- Multiple-census-family household
        (14, 1,   1, false),   -- Non-census-family household
        (15, 14,  2, true),    -- ... one-person household
        (16, 14,  2, true)     -- ... two-or-more-person non-census-family household
)
SELECT
    b.geography,
    b.ref_year,
    b.household_type_member_id,
    b.household_type,
    h.hierarchy_level,
    h.parent_member_id,
    parent.household_type AS parent_household_type,
    CASE WHEN parent.household_type IS NULL THEN b.household_type
         ELSE parent.household_type || ' > ' || b.household_type END AS household_type_path,
    h.is_leaf,
    b.tenure_member_id,
    b.tenure,
    b.burden_30_plus_households AS numerator_burden_30_plus_households,
    b.applicable_households     AS denominator_applicable_households,
    b.total_households,
    b.not_applicable_households,
    b.not_applicable_basis,
    b.burden_30_plus_pct,
    b.rate_null_reason,
    b.burden_30_plus_coordinate
FROM analysis.story1_shelter_cost_burden b
JOIN hierarchy h ON h.member_id = b.household_type_member_id
LEFT JOIN (SELECT DISTINCT household_type_member_id, household_type
           FROM clean.shelter_cost) parent
       ON parent.household_type_member_id = h.parent_member_id
WHERE b.is_income_total;

COMMENT ON VIEW analysis.story1_affordability_by_household_type IS
    'Grain: household type member x tenure (income = Total). 30%+ burden with hierarchy level/parent; do not sum across levels.';


-- -----------------------------------------------------------------------------
-- analysis.story1_burden_severity_by_tenure
-- Question: how severe is the burden (under 30%, 30% to under 100%, 100%+)?
-- Grain: one row per tenure x severity category; all incomes and household
-- types. '100% or more' is derived (30%+ minus 30%-to-under-100%) and labelled
-- as such. Shares use the applicable-household denominator; because of
-- StatCan rounding the three shares can sum to slightly more or less than 100.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_burden_severity_by_tenure AS
SELECT
    t.geography,
    t.ref_year,
    t.tenure_member_id,
    t.tenure,
    c.severity_order,
    c.severity_category,
    c.category_source,
    c.households,
    t.applicable_households AS denominator_applicable_households,
    round(100.0 * c.households / NULLIF(t.applicable_households, 0), 4) AS share_of_applicable_households_pct
FROM analysis.story1_shelter_cost_burden t
CROSS JOIN LATERAL (
    VALUES
        (1, 'Spending less than 30%', 'published', t.below_30_households),
        (2, '30% to less than 100%',  'published', t.burden_30_to_under_100_households),
        (3, '100% or more',           'derived: 30% or more minus 30% to less than 100%', t.burden_100_plus_households_derived)
) AS c (severity_order, severity_category, category_source, households)
WHERE t.is_income_total
  AND t.is_household_type_total;

COMMENT ON VIEW analysis.story1_burden_severity_by_tenure IS
    'Grain: tenure x severity category. Households under 30%, 30-<100% and 100%+ (derived) as shares of applicable households.';


-- -----------------------------------------------------------------------------
-- analysis.story1_burden_vs_census_published
-- Question: does the calculated burden reproduce StatCan's own published rate?
-- Grain: one row per tenure. Same geography (Windsor CMA), same year (2021),
-- same concept: the Census Profile publishes these exact rates as
-- characteristics 1484 (owners), 1492 (tenants) and 1467 (all households, as a
-- rate of characteristic 1465). Join is on an explicit characteristic id, not
-- on label similarity.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story1_burden_vs_census_published AS
WITH census_map (tenure, characteristic_id) AS (
    VALUES ('Owner', 1484), ('Renter', 1492), ('Total - Tenure', 1467)
)
SELECT
    t.geography,
    t.ref_year,
    t.tenure,
    t.numerator_burden_30_plus_households,
    t.denominator_applicable_households,
    t.burden_30_plus_pct                                AS calculated_burden_30_plus_pct,
    round(t.burden_30_plus_pct, 1)                      AS calculated_burden_30_plus_pct_1dp,
    c.characteristic_id                                 AS census_characteristic_id,
    c.characteristic_name                               AS census_characteristic_name,
    c.rate_total                                        AS census_published_pct,
    c.rate_total_status                                 AS census_published_status,
    round(t.burden_30_plus_pct, 1) - c.rate_total       AS difference_pct_points_1dp
FROM analysis.story1_affordability_by_tenure t
JOIN census_map m ON m.tenure = t.tenure
JOIN clean.census_profile c
  ON c.characteristic_id = m.characteristic_id
 AND c.geography = t.geography
 AND c.census_year = t.ref_year;

COMMENT ON VIEW analysis.story1_burden_vs_census_published IS
    'Grain: tenure. Calculated 30%+ burden next to the Census Profile''s published rate for the same geography and year.';
