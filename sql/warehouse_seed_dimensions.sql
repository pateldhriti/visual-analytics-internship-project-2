-- Seed data for warehouse dimension tables. Every value here is a real
-- category confirmed during actual profiling work this project has already
-- done (docs/shelter_cost_audit.md, docs/cmhc_rms_sheet_catalogue.md) --
-- none of this is invented. Geography and period are seeded only with the
-- values this project has actually extracted/worked with so far (Windsor
-- CMA; the 2021 census year; the Oct-24/Oct-25 CMHC survey periods), not
-- the full set of geographies/periods that exist in the raw source files.

-- ---------- dim_geography ----------
INSERT INTO warehouse.dim_geography (geography_key, geography_name, geography_level) VALUES
    ('2021S0503559', 'Windsor (CMA), Ont.', 'CMA');

-- ---------- dim_period ----------
INSERT INTO warehouse.dim_period (period_label, period_type, period_year, period_month) VALUES
    ('2021',   'census_year',   2021, NULL),
    ('Oct-24', 'survey_month',  2024, 10),
    ('Oct-25', 'survey_month',  2025, 10);

-- ---------- dim_tenure ----------
INSERT INTO warehouse.dim_tenure (tenure_name) VALUES
    ('Total'), ('Owner'), ('Renter');

-- ---------- dim_income_band ----------
-- scheme = statcan_bracket: 14 members from table 98-10-0252-01's metadata
-- (dimension 2), member_id = StatCan's own ordering.
INSERT INTO warehouse.dim_income_band (scheme, member_id, band_label) VALUES
    ('statcan_bracket', 1,  'Total - Total income of household'),
    ('statcan_bracket', 2,  'Under $10,000'),
    ('statcan_bracket', 3,  '$10,000 to $19,999'),
    ('statcan_bracket', 4,  '$20,000 to $29,999'),
    ('statcan_bracket', 5,  '$30,000 to $39,999'),
    ('statcan_bracket', 6,  '$40,000 to $49,999'),
    ('statcan_bracket', 7,  '$50,000 to $59,999'),
    ('statcan_bracket', 8,  '$60,000 to $69,999'),
    ('statcan_bracket', 9,  '$70,000 to $79,999'),
    ('statcan_bracket', 10, '$80,000 to $89,999'),
    ('statcan_bracket', 11, '$90,000 to $99,999'),
    ('statcan_bracket', 12, '$100,000 and over'),
    ('statcan_bracket', 13, 'Median total income of household ($)'),
    ('statcan_bracket', 14, 'Average total income of household ($)');

-- scheme = cmhc_quintile: from CMHC Table 3.1.8's Income Quintile column
-- (N/A covers agricultural-operation / zero-or-negative-income households).
INSERT INTO warehouse.dim_income_band (scheme, member_id, band_label) VALUES
    ('cmhc_quintile', 0, 'N/A'),
    ('cmhc_quintile', 1, 'Q1'),
    ('cmhc_quintile', 2, 'Q2'),
    ('cmhc_quintile', 3, 'Q3'),
    ('cmhc_quintile', 4, 'Q4');

-- ---------- dim_household_type ----------
-- All 16 real StatCan member IDs, with parent_member_id preserving the
-- hierarchy -- this is also where the label collision documented in
-- docs/shelter_cost_audit.md lives: member 5 and member 10 both render as
-- "Without children" under different parent branches, same for 6 and 11
-- ("With children"). The household_type_key (= member_id) disambiguates
-- them even though household_type_label does not.
INSERT INTO warehouse.dim_household_type (household_type_key, household_type_label, parent_member_id) VALUES
    (1,  'Total - Household type including census family structure', NULL),
    (2,  'Census-family households', 1),
    (3,  'One-census-family households without additional person', 2),
    (4,  'One couple census family without other persons in the household', 3),
    (5,  'Without children', 4),
    (6,  'With children', 4),
    (7,  'One-census-family household without additional persons: one-parent family', 3),
    (8,  'One-census-family households with additional persons', 2),
    (9,  'One couple census family with other persons in the household', 8),
    (10, 'Without children', 9),
    (11, 'With children', 9),
    (12, 'One-census-family household with additional persons: one-parent family', 8),
    (13, 'Multiple-census-family household', 2),
    (14, 'Non-census-family household', 1),
    (15, 'Non-census-family household: one-person household', 14),
    (16, 'Non-census-family household: two-or-more-person non-census-family household', 14);

-- ---------- dim_bedroom_type ----------
INSERT INTO warehouse.dim_bedroom_type (bedroom_type_label) VALUES
    ('Studio'), ('1 Bedroom'), ('2 Bedroom'), ('3 Bedroom +'), ('Total');

-- ---------- dim_zone ----------
-- The 7 real CMHC zones plus the 2 published aggregate rows, same set
-- confirmed across every zone-based table in the RMS workbook.
INSERT INTO warehouse.dim_zone (zone_label, zone_level) VALUES
    ('Zone 1 - Centre', 'zone'),
    ('Zone 2 - East Inner', 'zone'),
    ('Zone 3 - East Outer', 'zone'),
    ('Zone 4 - West', 'zone'),
    ('Windsor City (Zones 1-4)', 'city_subtotal'),
    ('Zone 5 - Amherstburg', 'zone'),
    ('Zone 6 - North Essex County', 'zone'),
    ('Zone 7 - South Essex County', 'zone'),
    ('Windsor CMA', 'cma_total');

-- ---------- dim_dwelling_type ----------
-- CMHC's three workbook sections: 1.x = Apartment only, 2.x = Row
-- (Townhouse) only, 3.x = both combined (the full private rental market).
INSERT INTO warehouse.dim_dwelling_type (dwelling_type_label) VALUES
    ('Apartment'), ('Row (Townhouse)'), ('Combined');
