-- Story 5: combined views. Each view joins data from two stories, so it
-- produces a figure neither story has on its own:
--
--   v_story5_rent_affordability      Story 1 renter incomes  x Story 2 rents
--   v_story5_peer_affordability      Story 1 incomes/burden  x Story 4 peer rents
--   v_story5_supply_vs_rental_market Story 3 construction    x Story 2 vacancy and rent
--   v_story5_peer_construction       Story 3 construction    x Story 4 peer cities
--
-- "Can afford" uses the standard 30% rule: a rent is affordable to a
-- household whose yearly income is at least rent x 12 / 0.30.
--
-- Incomes come in $10,000 bands. The share of renters below an income is
-- counted band by band; for the one band the income falls inside, the
-- households are assumed to be spread evenly across it (linear
-- interpolation). Incomes are for 2020 (2021 Census) and rents for October
-- 2025, so the shares are an upper-bound reading: incomes have grown since.
--
-- Peer-city incomes, households and construction come from
-- warehouse.fact_peer_cma_context (etl/extract_peer_cma_context.py).


-- ---------------------------------------------------------------------------
-- v_story5_income_bands
-- Lower and upper bounds of the 11 StatCan household income bands, for the
-- interpolation above. The top band has no upper bound.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_income_bands AS
SELECT
    ib.band_label,
    ib.member_id,
    (ib.member_id - 2) * 10000 AS band_lower,
    CASE WHEN ib.member_id = 12 THEN NULL ELSE (ib.member_id - 1) * 10000 END AS band_upper
FROM warehouse.dim_income_band ib
WHERE ib.scheme = 'statcan_bracket'
  AND ib.member_id BETWEEN 2 AND 12;


-- ---------------------------------------------------------------------------
-- v_story5_rent_affordability (Story 1 x Story 2)
-- Windsor CMA, October 2025 average rent by unit size (apartments and row
-- houses, CMHC) against 2021 Census renter household incomes. One row per
-- unit size with a published rent.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_rent_affordability AS
WITH rent AS (
    SELECT
        b.bedroom_type_label AS unit_size,
        b.bedroom_type_key AS unit_size_sort_order,
        f.value AS average_rent
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE f.metric_type = 'average_rent'
      AND z.zone_label = 'Windsor CMA'
      AND p.period_label = 'Oct-25'
      AND d.dwelling_type_label = 'Combined'
      AND f.value IS NOT NULL
),
renters AS (
    SELECT bands.band_lower, bands.band_upper, f.value AS households
    FROM warehouse.fact_shelter_cost f
    JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
    JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
    JOIN warehouse.v_story5_income_bands bands ON bands.member_id = ib.member_id
    WHERE t.tenure_name = 'Renter'
      AND ib.scheme = 'statcan_bracket'
      AND f.household_type_key = 1
      AND f.statistic = 'Number of private households'
      AND f.shelter_cost_ratio = 'Total - Shelter-cost-to-income ratio'
      AND f.housing_suitability = 'Total - Housing suitability'
      AND f.dwelling_condition = 'Total - Dwelling condition'
),
median_income AS (
    SELECT f.value AS median_renter_income
    FROM warehouse.fact_shelter_cost f
    JOIN warehouse.dim_tenure t ON t.tenure_key = f.tenure_key
    JOIN warehouse.dim_income_band ib ON ib.income_band_key = f.income_band_key
    WHERE t.tenure_name = 'Renter'
      AND ib.band_label = 'Median total income of household ($)'
      AND f.household_type_key = 1
      AND f.statistic = 'Number of private households'
      AND f.shelter_cost_ratio = 'Total - Shelter-cost-to-income ratio'
      AND f.housing_suitability = 'Total - Housing suitability'
      AND f.dwelling_condition = 'Total - Dwelling condition'
)
SELECT
    CASE WHEN r.unit_size = 'Total' THEN 'All unit sizes' ELSE r.unit_size END AS unit_size,
    r.unit_size_sort_order,
    r.average_rent,
    ROUND(r.average_rent * 12 / 0.30) AS income_needed,
    m.median_renter_income,
    ROUND(100.0 * r.average_rent * 12 / m.median_renter_income, 1) AS rent_pct_of_median_renter_income,
    SUM(h.households) AS renter_households,
    ROUND(SUM(h.households * CASE
        WHEN h.band_upper IS NOT NULL AND h.band_upper <= r.average_rent * 12 / 0.30 THEN 1
        WHEN h.band_lower >= r.average_rent * 12 / 0.30 THEN 0
        ELSE (r.average_rent * 12 / 0.30 - h.band_lower) / (h.band_upper - h.band_lower)
    END)) AS renters_who_cannot_afford,
    ROUND(100.0 * SUM(h.households * CASE
        WHEN h.band_upper IS NOT NULL AND h.band_upper <= r.average_rent * 12 / 0.30 THEN 1
        WHEN h.band_lower >= r.average_rent * 12 / 0.30 THEN 0
        ELSE (r.average_rent * 12 / 0.30 - h.band_lower) / (h.band_upper - h.band_lower)
    END) / SUM(h.households), 1) AS pct_renters_who_cannot_afford
FROM rent r
CROSS JOIN renters h
CROSS JOIN median_income m
GROUP BY r.unit_size, r.unit_size_sort_order, r.average_rent, m.median_renter_income;


-- ---------------------------------------------------------------------------
-- v_story5_peer_affordability (Story 1 x Story 4)
-- For Windsor and the four comparison cities: October 2025 average
-- 2-bedroom apartment rent (Story 4) against each city's own renter
-- incomes and shelter-cost burden (2021 Census, the source Story 1 uses
-- for Windsor). Answers "is Windsor affordable, or only cheap?".
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_peer_affordability AS
WITH rent AS (
    SELECT market AS city, average_rent_2br
    FROM warehouse.v_story4_rent_comparison
    WHERE period_label = 'Oct-25'
),
ctx AS (
    SELECT cma_name, source_table, indicator, tenure, category, value
    FROM warehouse.fact_peer_cma_context
    WHERE period_year = 2021
),
bands AS (
    SELECT c.cma_name, b.band_lower, b.band_upper, c.value AS households
    FROM ctx c
    JOIN warehouse.v_story5_income_bands b ON b.band_label = c.category
    WHERE c.indicator = 'households' AND c.tenure = 'Renter'
),
city AS (
    -- Median renter income from 98-10-0252-01 (the Census Profile has no
    -- renter-only median); the rest from the Census Profile.
    SELECT
        cma_name,
        MAX(value) FILTER (WHERE source_table = '98-10-0252-01'
                             AND indicator = 'median_household_income'
                             AND tenure = 'Renter') AS median_renter_income,
        MAX(value) FILTER (WHERE indicator = 'pct_spending_30pct_plus') AS pct_renters_spending_30pct_plus,
        MAX(value) FILTER (WHERE indicator = 'renter_households') AS renter_households,
        MAX(value) FILTER (WHERE indicator = 'private_households') AS private_households
    FROM ctx
    GROUP BY cma_name
)
SELECT
    r.city,
    (r.city = 'Windsor CMA') AS is_windsor,
    r.average_rent_2br,
    ROUND(r.average_rent_2br * 12 / 0.30) AS income_needed_2br,
    c.median_renter_income,
    ROUND(100.0 * r.average_rent_2br * 12 / c.median_renter_income, 1) AS rent_pct_of_median_renter_income,
    ROUND(100.0 * SUM(b.households * CASE
        WHEN b.band_upper IS NOT NULL AND b.band_upper <= r.average_rent_2br * 12 / 0.30 THEN 1
        WHEN b.band_lower >= r.average_rent_2br * 12 / 0.30 THEN 0
        ELSE (r.average_rent_2br * 12 / 0.30 - b.band_lower) / (b.band_upper - b.band_lower)
    END) / SUM(b.households), 1) AS pct_renters_who_cannot_afford_2br,
    c.pct_renters_spending_30pct_plus,
    c.renter_households,
    ROUND(100.0 * c.renter_households / c.private_households, 1) AS pct_households_renting
FROM rent r
JOIN city c ON c.cma_name = r.city
JOIN bands b ON b.cma_name = r.city
GROUP BY r.city, r.average_rent_2br, c.median_renter_income, c.pct_renters_spending_30pct_plus,
         c.renter_households, c.private_households;


-- ---------------------------------------------------------------------------
-- v_story5_supply_vs_rental_market (Story 3 x Story 2)
-- Windsor CMA, one row per year with both sources (2020-2025): homes
-- started and completed (all types and apartments, StatCan monthly counts
-- summed by calendar year) next to the October rental survey's vacancy
-- rate, average rent and rental-unit count (apartments and row houses).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_supply_vs_rental_market AS
WITH supply AS (
    SELECT
        period_year,
        SUM(units) FILTER (WHERE activity = 'Starts' AND dwelling_type = 'Total') AS starts,
        SUM(units) FILTER (WHERE activity = 'Starts' AND dwelling_type = 'Apartment and Other') AS apartment_starts,
        SUM(units) FILTER (WHERE activity = 'Completions' AND dwelling_type = 'Total') AS completions,
        SUM(units) FILTER (WHERE activity = 'Completions' AND dwelling_type = 'Apartment and Other') AS apartment_completions,
        COUNT(DISTINCT period_month) AS months
    FROM warehouse.fact_windsor_starts_completions
    GROUP BY period_year
),
market AS (
    SELECT
        2000 + RIGHT(p.period_label, 2)::int AS period_year,
        MAX(f.value) FILTER (WHERE f.metric_type = 'vacancy_rate') AS vacancy_rate,
        MAX(f.value) FILTER (WHERE f.metric_type = 'average_rent') AS average_rent,
        MAX(f.value) FILTER (WHERE f.metric_type = 'universe') AS rental_units
    FROM warehouse.fact_rental_market f
    JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
    JOIN warehouse.dim_period p ON p.period_key = f.period_key
    JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
    JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
    WHERE z.zone_label = 'Windsor CMA'
      AND b.bedroom_type_label = 'Total'
      AND d.dwelling_type_label = 'Combined'
      AND p.period_label LIKE 'Oct-%'
    GROUP BY p.period_label
)
SELECT
    s.period_year,
    MAKE_DATE(s.period_year, 1, 1) AS year_start,
    s.starts,
    s.apartment_starts,
    s.completions,
    s.apartment_completions,
    m.vacancy_rate,
    m.average_rent,
    m.rental_units,
    m.vacancy_rate - LAG(m.vacancy_rate) OVER (ORDER BY s.period_year) AS vacancy_change_pts,
    ROUND(100.0 * (m.average_rent / LAG(m.average_rent) OVER (ORDER BY s.period_year) - 1), 1) AS rent_change_pct
FROM supply s
JOIN market m ON m.period_year = s.period_year
WHERE s.months = 12;


-- ---------------------------------------------------------------------------
-- v_story5_peer_construction (Story 3 x Story 4)
-- Windsor and the four comparison cities, 2016 to the last full year:
-- homes started and completed per 1,000 households (2021 Census household
-- count for every year, as in Story 3), and the apartment share of starts.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_peer_construction AS
WITH households AS (
    SELECT cma_name, value AS private_households
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '98-401-X2021002' AND indicator = 'private_households'
),
yearly AS (
    SELECT
        cma_name,
        period_year,
        MAX(value) FILTER (WHERE indicator = 'starts' AND category = 'Total') AS starts,
        MAX(value) FILTER (WHERE indicator = 'starts' AND category = 'Apartment and Other') AS apartment_starts,
        MAX(value) FILTER (WHERE indicator = 'completions' AND category = 'Total') AS completions
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '34-10-0154-01'
    GROUP BY cma_name, period_year
)
SELECT
    y.cma_name AS city,
    (y.cma_name = 'Windsor CMA') AS is_windsor,
    y.period_year,
    MAKE_DATE(y.period_year, 1, 1) AS year_start,
    y.starts,
    y.apartment_starts,
    y.completions,
    h.private_households,
    ROUND(1000.0 * y.starts / h.private_households, 1) AS starts_per_1000_households,
    ROUND(1000.0 * y.completions / h.private_households, 1) AS completions_per_1000_households,
    ROUND(100.0 * y.apartment_starts / NULLIF(y.starts, 0), 1) AS apartment_share_of_starts
FROM yearly y
JOIN households h ON h.cma_name = y.cma_name;
