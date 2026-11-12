-- Story 5: combined views. Each view joins data from two stories, so it
-- produces a figure neither story has on its own:
--
--   v_story5_rent_affordability      Story 1 renter incomes  x Story 2 rents
--   v_story5_peer_affordability      Story 1 incomes/burden  x Story 4 peer rents
--   v_story5_supply_vs_rental_market Story 3 construction    x Story 2 vacancy and rent
--   v_story5_peer_construction       Story 3 construction    x Story 4 peer cities
--   v_story5_supply_vs_demand        Story 3 completions     x Census population growth
--   v_story5_renter_burden_by_age    Census renters by age   x Story 1 burden x Story 4 cities
--   v_story5_rental_stock            CMHC rental units       x Census renter households
--   v_story5_city_profile            every measure above, one row per city
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
    ROUND(100.0 * c.renter_households / c.private_households, 1) AS pct_households_renting,
    -- Short name for chart labels and colours (the Story 5 bubble chart).
    CASE r.city WHEN 'Kitchener-Cambridge-Waterloo CMA' THEN 'Kitchener-Waterloo'
                WHEN 'St. Catharines-Niagara CMA' THEN 'St. Catharines'
                ELSE REPLACE(r.city, ' CMA', '') END AS city_short
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


-- ---------------------------------------------------------------------------
-- v_story5_supply_vs_demand (Story 3 x Census population, all 5 cities)
-- Did building keep up with population growth between the 2016 and 2021
-- Censuses? Homes needed = population growth / average household size
-- (people in private households / private households, 2021). Homes built =
-- completions in calendar 2016-2020, the five full years closest to the
-- Census interval (May 2016 to May 2021). A ratio below 1 means fewer homes
-- were finished than the added population would occupy at 2021 household
-- sizes.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_supply_vs_demand AS
WITH census AS (
    SELECT
        cma_name,
        MAX(value) FILTER (WHERE indicator = 'population_2016') AS population_2016,
        MAX(value) FILTER (WHERE indicator = 'population_2021') AS population_2021,
        MAX(value) FILTER (WHERE indicator = 'private_households') AS private_households,
        MAX(value) FILTER (WHERE indicator = 'persons_in_private_households') AS persons_in_private_households
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '98-401-X2021002'
    GROUP BY cma_name
),
built AS (
    SELECT
        cma_name,
        SUM(value) FILTER (WHERE indicator = 'completions') AS homes_completed_2016_2020,
        SUM(value) FILTER (WHERE indicator = 'starts') AS homes_started_2016_2020,
        COUNT(DISTINCT period_year) AS years
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '34-10-0154-01'
      AND category = 'Total'
      AND period_year BETWEEN 2016 AND 2020
    GROUP BY cma_name
)
SELECT
    c.cma_name AS city,
    (c.cma_name = 'Windsor CMA') AS is_windsor,
    c.population_2016,
    c.population_2021,
    c.population_2021 - c.population_2016 AS population_growth,
    ROUND(100.0 * (c.population_2021 / c.population_2016 - 1), 1) AS population_growth_pct,
    ROUND(c.persons_in_private_households / c.private_households, 2) AS persons_per_household,
    ROUND((c.population_2021 - c.population_2016) * c.private_households / c.persons_in_private_households)
        AS homes_needed,
    b.homes_completed_2016_2020,
    b.homes_started_2016_2020,
    ROUND(b.homes_completed_2016_2020
          / ((c.population_2021 - c.population_2016) * c.private_households / c.persons_in_private_households), 2)
        AS homes_built_per_home_needed,
    ROUND(100.0 * b.homes_completed_2016_2020 / (c.population_2021 - c.population_2016), 1)
        AS homes_built_per_100_new_residents
FROM census c
JOIN built b ON b.cma_name = c.cma_name
WHERE b.years = 5;


-- ---------------------------------------------------------------------------
-- v_story5_renter_burden_by_age (new Census table x Story 1 x Story 4)
-- Can young renters, including most students who rent, afford their
-- housing? For Windsor and the four comparison cities: renter households
-- by age of the primary household maintainer (98-10-0241-01, 2021 Census),
-- the share spending 30% or more of income on shelter, and the same share
-- for all renters (Story 1's measure) to compare against. One row per
-- city x age group.
--
-- Core housing need is in the source but not used here: CMHC's definition
-- leaves out non-family households with a maintainer aged 15-29 attending
-- school, so it understates need among students.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_renter_burden_by_age AS
WITH renters AS (
    SELECT
        cma_name,
        category AS age_group,
        MAX(value) FILTER (WHERE indicator = 'households') AS renter_households,
        MAX(value) FILTER (WHERE indicator = 'households_30pct_plus') AS renters_30pct_plus
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '98-10-0241-01'
      AND tenure = 'Renter'
    GROUP BY cma_name, category
),
all_renters AS (
    SELECT cma_name, ROUND(100.0 * renters_30pct_plus / renter_households, 1) AS all_renters_pct_30pct_plus
    FROM renters
    WHERE age_group = 'Total - Age of primary household maintainer'
)
SELECT
    r.cma_name AS city,
    (r.cma_name = 'Windsor CMA') AS is_windsor,
    r.age_group,
    LEFT(r.age_group, 2)::int AS age_sort,
    r.renter_households,
    r.renters_30pct_plus,
    ROUND(100.0 * r.renters_30pct_plus / r.renter_households, 1) AS pct_30pct_plus,
    a.all_renters_pct_30pct_plus,
    ROUND(100.0 * r.renters_30pct_plus / r.renter_households, 1) - a.all_renters_pct_30pct_plus
        AS pct_points_above_all_renters
FROM renters r
JOIN all_renters a ON a.cma_name = r.cma_name
WHERE r.age_group <> 'Total - Age of primary household maintainer';


-- ---------------------------------------------------------------------------
-- v_story5_rental_stock (Story 2 / Story 4 rental universe x Census renters)
-- How large is each city's purpose-built rental market compared with the
-- number of renter households? Purpose-built rental units (apartments and
-- row houses, CMHC Rental Market Survey Table 3.1.3, October 2025) per 100
-- renter households (2021 Census). Every other renter lives in a rented
-- house, condo, basement or other unit the survey does not cover, so the
-- rent and vacancy figures of Stories 2 and 4 describe only part of the
-- rental market.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_rental_stock AS
WITH stock AS (
    SELECT
        cma_name,
        MAX(value) FILTER (WHERE period_year = 2024) AS rental_units_2024,
        MAX(value) FILTER (WHERE period_year = 2025) AS rental_units_2025
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = 'CMHC RMS 3.1.3' AND indicator = 'rental_universe'
    GROUP BY cma_name
),
renters AS (
    SELECT cma_name, value AS renter_households
    FROM warehouse.fact_peer_cma_context
    WHERE source_table = '98-401-X2021002' AND indicator = 'renter_households'
)
SELECT
    s.cma_name AS city,
    (s.cma_name = 'Windsor CMA') AS is_windsor,
    s.rental_units_2024,
    s.rental_units_2025,
    s.rental_units_2025 - s.rental_units_2024 AS rental_units_added,
    r.renter_households,
    ROUND(100.0 * s.rental_units_2025 / r.renter_households, 1) AS units_per_100_renter_households,
    ROUND(100.0 * (r.renter_households - s.rental_units_2025) / r.renter_households, 1)
        AS pct_renters_outside_purpose_built
FROM stock s
JOIN renters r ON r.cma_name = s.cma_name;


-- ---------------------------------------------------------------------------
-- v_story5_city_profile (all stories, one row per city)
-- Windsor and the four comparison cities side by side on rental-market
-- conditions and renter characteristics: rent, vacancy, rental stock,
-- renter incomes, affordability pressure (all renters and ages 15-24) and
-- construction. Every column comes from another Story 5 view or Story 4's
-- vacancy view, so the figures match the rest of the dashboard.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW warehouse.v_story5_city_profile AS
WITH build AS (
    SELECT city, ROUND(1000.0 * SUM(starts) / MAX(private_households) / COUNT(DISTINCT period_year), 1)
               AS starts_per_1000_households
    FROM warehouse.v_story5_peer_construction
    GROUP BY city
)
SELECT
    a.city,
    a.is_windsor,
    a.average_rent_2br,
    v.vacancy_rate_pct AS vacancy_rate,
    s.units_per_100_renter_households,
    a.median_renter_income,
    a.rent_pct_of_median_renter_income,
    a.pct_renters_spending_30pct_plus,
    y.pct_30pct_plus AS pct_young_renters_spending_30pct_plus,
    b.starts_per_1000_households,
    ROUND(100.0 * d.homes_built_per_home_needed, 0) AS pct_needed_homes_built
FROM warehouse.v_story5_peer_affordability a
JOIN warehouse.v_story4_vacancy_comparison v ON v.market = a.city AND v.period_label = 'Oct-25'
JOIN warehouse.v_story5_rental_stock s ON s.city = a.city
JOIN warehouse.v_story5_renter_burden_by_age y ON y.city = a.city AND y.age_sort = 15
JOIN build b ON b.city = a.city
JOIN warehouse.v_story5_supply_vs_demand d ON d.city = a.city;
