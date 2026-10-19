-- =============================================================================
-- STORY 2 -- WINDSOR RENTAL MARKET (CMHC Rental Market Survey 2025)
-- Source: clean.rental_market_windsor only (Windsor CMA, 20 workbook tables).
--
-- Periods in the data: two October surveys (Oct-24, Oct-25) and two CMHC
-- same-sample rent-change periods (Oct-23 to Oct-24, Oct-24 to Oct-25).
-- "Latest" and "previous" are derived from those labels; no other years exist.
--
-- dwelling_scope is kept in every view and every calculation is within one
-- scope: apartment (tables 1.x), row_townhouse (2.x), row_and_apartment (3.x).
-- Suppressed ('**') and not-significant ('++') cells are NULL in clean.* and
-- stay NULL: they never enter arithmetic, and no value is filled in.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- analysis.story2_survey_periods
-- Question: which periods does the workbook actually contain?
-- Grain: one row per period_label present in clean.rental_market_windsor.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_survey_periods AS
WITH labels AS (
    SELECT DISTINCT period_label FROM clean.rental_market_windsor
),
parsed AS (
    SELECT
        period_label,
        CASE WHEN period_label LIKE '% to %' THEN 'rent_change' ELSE 'survey' END AS period_kind,
        CASE WHEN period_label LIKE '% to %' THEN split_part(period_label, ' to ', 1) END AS change_from_label,
        CASE WHEN period_label LIKE '% to %' THEN split_part(period_label, ' to ', 2) END AS change_to_label,
        2000 + right(period_label, 2)::int AS end_year  -- 'Oct-25' -> 2025; 'Oct-24 to Oct-25' -> 2025
    FROM labels
)
SELECT
    period_label,
    period_kind,
    change_from_label,
    change_to_label,
    end_year,
    end_year = max(end_year) OVER (PARTITION BY period_kind) AS is_latest,
    end_year = max(end_year) OVER (PARTITION BY period_kind) - 1 AS is_previous
FROM parsed;

COMMENT ON VIEW analysis.story2_survey_periods IS
    'Grain: period label. The survey and rent-change periods present in the workbook, with latest/previous flags.';


-- -----------------------------------------------------------------------------
-- analysis.story2_period_change
-- Question: what changed between the previous and latest October survey?
-- Grain: one row per source table x zone x bedroom type for every metric
-- published in both surveys (vacancy, turnover, average rent, rental universe).
-- change_value is NULL unless both values are published. For percent metrics
-- the change is in percentage points and no relative % change is computed.
-- For average rent this is a difference of two published averages (different
-- samples); CMHC's like-for-like measure is story2_same_sample_rent_change.
-- yoy_trend is CMHC's own significance marker on the latest row.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_period_change AS
SELECT
    l.source_table,
    l.dwelling_scope,
    l.geography,
    l.zone,
    l.zone_level,
    l.bedroom_type,
    CASE l.bedroom_type WHEN 'Studio' THEN 1 WHEN '1 Bedroom' THEN 2 WHEN '2 Bedroom' THEN 3
                        WHEN '3 Bedroom +' THEN 4 WHEN 'Total' THEN 5 END AS bedroom_order,
    l.metric,
    l.unit,
    p.period_label      AS previous_period_label,
    p.value             AS previous_value,
    p.value_status      AS previous_value_status,
    p.reliability_code  AS previous_reliability_code,
    l.period_label      AS latest_period_label,
    l.value             AS latest_value,
    l.value_status      AS latest_value_status,
    l.reliability_code  AS latest_reliability_code,
    l.yoy_trend,
    l.value - p.value   AS change_value,
    CASE l.unit WHEN 'percent' THEN 'percentage_points' ELSE l.unit END AS change_unit,
    CASE WHEN l.unit IN ('dollars', 'units')
         THEN round(100.0 * (l.value - p.value) / NULLIF(p.value, 0), 4) END AS change_pct,
    (l.value IS NOT NULL AND p.value IS NOT NULL) AS is_comparable,
    p.source_cell       AS previous_source_cell,
    l.source_cell       AS latest_source_cell
FROM clean.rental_market_windsor l
JOIN analysis.story2_survey_periods lp ON lp.period_label = l.period_label AND lp.period_kind = 'survey' AND lp.is_latest
JOIN clean.rental_market_windsor p
  ON p.source_table = l.source_table
 AND p.zone = l.zone
 AND p.bedroom_type = l.bedroom_type
 AND p.metric = l.metric
 AND p.income_quintile IS NOT DISTINCT FROM l.income_quintile
JOIN analysis.story2_survey_periods pp ON pp.period_label = p.period_label AND pp.period_kind = 'survey' AND pp.is_previous;

COMMENT ON VIEW analysis.story2_period_change IS
    'Grain: source table x zone x bedroom type (metrics in both surveys). Previous vs latest value, change (pct points for rates).';


-- -----------------------------------------------------------------------------
-- analysis.story2_same_sample_rent_change
-- Question: how much did rents of the same units change (CMHC fixed sample)?
-- Grain: one row per source table (x.1.5) x zone x bedroom type x change period.
-- Published values only as numbers; '++' (not different from zero) and '**'
-- stay NULL with their status.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_same_sample_rent_change AS
SELECT
    r.source_table,
    r.dwelling_scope,
    r.geography,
    r.zone,
    r.zone_level,
    r.bedroom_type,
    CASE r.bedroom_type WHEN 'Studio' THEN 1 WHEN '1 Bedroom' THEN 2 WHEN '2 Bedroom' THEN 3
                        WHEN '3 Bedroom +' THEN 4 WHEN 'Total' THEN 5 END AS bedroom_order,
    r.period_label AS change_period_label,
    sp.is_latest   AS is_latest_change,
    r.value        AS rent_change_pct,
    r.value_status,
    r.reliability_code,
    r.source_cell
FROM clean.rental_market_windsor r
JOIN analysis.story2_survey_periods sp ON sp.period_label = r.period_label AND sp.period_kind = 'rent_change'
WHERE r.metric = 'average_rent_pct_change';

COMMENT ON VIEW analysis.story2_same_sample_rent_change IS
    'Grain: x.1.5 table x zone x bedroom x change period. CMHC same-sample % change in average rent.';


-- -----------------------------------------------------------------------------
-- analysis.story2_latest_cma_kpis
-- Question: what are Windsor CMA's headline rental indicators now?
-- Grain: one row per dwelling scope x metric, zone = Windsor CMA, bedroom = Total.
-- For average rent, the latest CMHC same-sample rent change is attached.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_latest_cma_kpis AS
SELECT
    c.dwelling_scope,
    c.geography,
    c.metric,
    c.unit,
    c.previous_period_label,
    c.previous_value,
    c.previous_value_status,
    c.latest_period_label,
    c.latest_value,
    c.latest_value_status,
    c.latest_reliability_code,
    c.yoy_trend,
    c.change_value,
    c.change_unit,
    c.change_pct,
    s.change_period_label AS same_sample_rent_change_period,
    s.rent_change_pct     AS same_sample_rent_change_pct,
    s.value_status        AS same_sample_rent_change_status,
    c.latest_source_cell
FROM analysis.story2_period_change c
LEFT JOIN analysis.story2_same_sample_rent_change s
       ON c.metric = 'average_rent'
      AND s.dwelling_scope = c.dwelling_scope
      AND s.zone = c.zone
      AND s.bedroom_type = c.bedroom_type
      AND s.is_latest_change
WHERE c.zone = 'Windsor CMA'
  AND c.bedroom_type = 'Total';

COMMENT ON VIEW analysis.story2_latest_cma_kpis IS
    'Grain: dwelling scope x metric (Windsor CMA, all bedrooms). Latest vacancy, turnover, average rent, universe and change.';


-- -----------------------------------------------------------------------------
-- analysis.story2_rent_by_bedroom
-- Question: what is the average rent by bedroom type, and how did it change?
-- Grain: one row per dwelling scope x bedroom type, zone = Windsor CMA.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_rent_by_bedroom AS
SELECT
    c.dwelling_scope,
    c.geography,
    c.bedroom_type,
    c.bedroom_order,
    c.previous_period_label,
    c.previous_value            AS previous_average_rent,
    c.previous_value_status,
    c.previous_reliability_code,
    c.latest_period_label,
    c.latest_value              AS latest_average_rent,
    c.latest_value_status,
    c.latest_reliability_code,
    c.change_value              AS average_rent_difference_dollars,
    c.change_pct                AS average_rent_difference_pct,
    s.change_period_label       AS same_sample_rent_change_period,
    s.rent_change_pct           AS same_sample_rent_change_pct,
    s.value_status              AS same_sample_rent_change_status,
    s.reliability_code          AS same_sample_rent_change_reliability_code,
    c.latest_source_cell
FROM analysis.story2_period_change c
LEFT JOIN analysis.story2_same_sample_rent_change s
       ON s.dwelling_scope = c.dwelling_scope
      AND s.zone = c.zone
      AND s.bedroom_type = c.bedroom_type
      AND s.is_latest_change
WHERE c.metric = 'average_rent'
  AND c.zone = 'Windsor CMA';

COMMENT ON VIEW analysis.story2_rent_by_bedroom IS
    'Grain: dwelling scope x bedroom type (Windsor CMA). Average rent in both surveys, difference, and CMHC same-sample change.';


-- -----------------------------------------------------------------------------
-- analysis.story2_vacancy_by_bedroom
-- Question: how does the vacancy rate differ by bedroom type, and did it change?
-- Grain: one row per dwelling scope x bedroom type, zone = Windsor CMA.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_vacancy_by_bedroom AS
SELECT
    dwelling_scope, geography, bedroom_type, bedroom_order,
    previous_period_label, previous_value AS previous_vacancy_rate_pct, previous_value_status, previous_reliability_code,
    latest_period_label,   latest_value   AS latest_vacancy_rate_pct,   latest_value_status,   latest_reliability_code,
    change_value AS change_pct_points,
    yoy_trend,
    latest_source_cell
FROM analysis.story2_period_change
WHERE metric = 'vacancy_rate'
  AND zone = 'Windsor CMA';

COMMENT ON VIEW analysis.story2_vacancy_by_bedroom IS
    'Grain: dwelling scope x bedroom type (Windsor CMA). Vacancy rate in both surveys, change in pct points, CMHC trend.';


-- -----------------------------------------------------------------------------
-- analysis.story2_turnover_by_bedroom
-- Question: how often do tenants move (turnover rate) by bedroom type?
-- Grain: one row per dwelling scope x bedroom type, zone = Windsor CMA.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_turnover_by_bedroom AS
SELECT
    dwelling_scope, geography, bedroom_type, bedroom_order,
    previous_period_label, previous_value AS previous_turnover_rate_pct, previous_value_status, previous_reliability_code,
    latest_period_label,   latest_value   AS latest_turnover_rate_pct,   latest_value_status,   latest_reliability_code,
    change_value AS change_pct_points,
    yoy_trend,
    latest_source_cell
FROM analysis.story2_period_change
WHERE metric = 'turnover_rate'
  AND zone = 'Windsor CMA';

COMMENT ON VIEW analysis.story2_turnover_by_bedroom IS
    'Grain: dwelling scope x bedroom type (Windsor CMA). Turnover rate in both surveys, change in pct points, CMHC trend.';


-- -----------------------------------------------------------------------------
-- analysis.story2_rental_universe
-- Question: how large is the rental stock, by zone and bedroom type?
-- Grain: one row per dwelling scope x zone x bedroom type.
-- share_of_zone_universe_pct = bedroom type's share of the same zone's Total
-- universe (latest survey, same scope; NULL for the Total row itself).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_rental_universe AS
SELECT
    c.dwelling_scope,
    c.geography,
    c.zone,
    c.zone_level,
    c.bedroom_type,
    c.bedroom_order,
    c.previous_period_label,
    c.previous_value AS previous_universe_units,
    c.latest_period_label,
    c.latest_value   AS latest_universe_units,
    c.change_value   AS change_units,
    c.change_pct,
    t.latest_value   AS zone_total_latest_universe_units,
    CASE WHEN c.bedroom_type <> 'Total'
         THEN round(100.0 * c.latest_value / NULLIF(t.latest_value, 0), 4) END AS share_of_zone_universe_pct,
    c.latest_source_cell
FROM analysis.story2_period_change c
JOIN analysis.story2_period_change t
  ON t.source_table = c.source_table
 AND t.zone = c.zone
 AND t.bedroom_type = 'Total'
WHERE c.metric = 'rental_universe';

COMMENT ON VIEW analysis.story2_rental_universe IS
    'Grain: dwelling scope x zone x bedroom type. Rental universe (units) in both surveys and bedroom share of zone stock.';


-- -----------------------------------------------------------------------------
-- analysis.story2_zone_comparison
-- Question: how do Windsor's zones compare?
-- Grain: one row per dwelling scope x zone, bedroom = Total. Latest survey
-- values with status / reliability, plus the change from the previous survey.
-- zone_level separates zones from the City subtotal and the CMA total -- do
-- not add zone rows to those.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_zone_comparison AS
SELECT
    dwelling_scope,
    geography,
    zone,
    zone_level,
    max(latest_period_label) AS latest_period_label,
    max(latest_value)            FILTER (WHERE metric = 'vacancy_rate')    AS vacancy_rate_pct,
    max(latest_value_status)     FILTER (WHERE metric = 'vacancy_rate')    AS vacancy_rate_status,
    max(latest_reliability_code) FILTER (WHERE metric = 'vacancy_rate')    AS vacancy_rate_reliability_code,
    max(change_value)            FILTER (WHERE metric = 'vacancy_rate')    AS vacancy_rate_change_pct_points,
    max(yoy_trend)               FILTER (WHERE metric = 'vacancy_rate')    AS vacancy_rate_yoy_trend,
    max(latest_value)            FILTER (WHERE metric = 'average_rent')    AS average_rent,
    max(latest_value_status)     FILTER (WHERE metric = 'average_rent')    AS average_rent_status,
    max(latest_reliability_code) FILTER (WHERE metric = 'average_rent')    AS average_rent_reliability_code,
    max(change_value)            FILTER (WHERE metric = 'average_rent')    AS average_rent_difference_dollars,
    max(latest_value)            FILTER (WHERE metric = 'turnover_rate')   AS turnover_rate_pct,
    max(latest_value_status)     FILTER (WHERE metric = 'turnover_rate')   AS turnover_rate_status,
    max(latest_reliability_code) FILTER (WHERE metric = 'turnover_rate')   AS turnover_rate_reliability_code,
    max(latest_value)            FILTER (WHERE metric = 'rental_universe') AS rental_universe_units,
    max(change_value)            FILTER (WHERE metric = 'rental_universe') AS rental_universe_change_units
FROM analysis.story2_period_change
WHERE bedroom_type = 'Total'
GROUP BY dwelling_scope, geography, zone, zone_level;

COMMENT ON VIEW analysis.story2_zone_comparison IS
    'Grain: dwelling scope x zone (all bedrooms). Latest vacancy, rent, turnover and universe per zone.';


-- -----------------------------------------------------------------------------
-- analysis.story2_vacant_vs_occupied_rent
-- Question: are vacant units advertised at higher rents than occupied ones?
-- Grain: one row per dwelling scope x zone x bedroom type (tables x.1.9, latest
-- survey only). The difference is calculated only when both rents are
-- published; vacant_rent_higher_flag is CMHC's own significance test (Y/N).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_vacant_vs_occupied_rent AS
SELECT
    source_table,
    dwelling_scope,
    geography,
    zone,
    zone_level,
    bedroom_type,
    CASE bedroom_type WHEN 'Studio' THEN 1 WHEN '1 Bedroom' THEN 2 WHEN '2 Bedroom' THEN 3
                      WHEN '3 Bedroom +' THEN 4 WHEN 'Total' THEN 5 END AS bedroom_order,
    period_label,
    max(value)            FILTER (WHERE metric = 'average_rent_vacant_units')   AS vacant_units_average_rent,
    max(value_status)     FILTER (WHERE metric = 'average_rent_vacant_units')   AS vacant_units_rent_status,
    max(reliability_code) FILTER (WHERE metric = 'average_rent_vacant_units')   AS vacant_units_reliability_code,
    max(value)            FILTER (WHERE metric = 'average_rent_occupied_units') AS occupied_units_average_rent,
    max(value_status)     FILTER (WHERE metric = 'average_rent_occupied_units') AS occupied_units_rent_status,
    max(reliability_code) FILTER (WHERE metric = 'average_rent_occupied_units') AS occupied_units_reliability_code,
    max(value) FILTER (WHERE metric = 'average_rent_vacant_units')
      - max(value) FILTER (WHERE metric = 'average_rent_occupied_units')        AS vacant_minus_occupied_dollars,
    round(100.0 * (max(value) FILTER (WHERE metric = 'average_rent_vacant_units')
                   - max(value) FILTER (WHERE metric = 'average_rent_occupied_units'))
          / NULLIF(max(value) FILTER (WHERE metric = 'average_rent_occupied_units'), 0), 4) AS vacant_premium_pct,
    max(vacant_rent_higher_flag) AS cmhc_vacant_rent_significantly_higher
FROM clean.rental_market_windsor
WHERE metric IN ('average_rent_vacant_units', 'average_rent_occupied_units')
GROUP BY source_table, dwelling_scope, geography, zone, zone_level, bedroom_type, period_label;

COMMENT ON VIEW analysis.story2_vacant_vs_occupied_rent IS
    'Grain: dwelling scope x zone x bedroom (x.1.9, latest survey). Vacant vs occupied average rent and CMHC Y/N test.';


-- -----------------------------------------------------------------------------
-- analysis.story2_new_rental_stock
-- Question: how much recently built rental stock is there, and at what rent?
-- Grain: one row per zone x bedroom type (Table 3.1.7: row and apartment
-- structures completed July 2022 - June 2025, surveyed Oct-25). Most rent and
-- vacancy cells are suppressed by CMHC and stay NULL.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_new_rental_stock AS
SELECT
    source_table,
    dwelling_scope,
    geography,
    zone,
    zone_level,
    bedroom_type,
    CASE bedroom_type WHEN 'Studio' THEN 1 WHEN '1 Bedroom' THEN 2 WHEN '2 Bedroom' THEN 3
                      WHEN '3 Bedroom +' THEN 4 WHEN 'Total' THEN 5 END AS bedroom_order,
    period_label,
    max(value)            FILTER (WHERE metric = 'new_stock_universe')     AS new_stock_universe_units,
    max(value)            FILTER (WHERE metric = 'new_stock_vacancy_rate') AS new_stock_vacancy_rate_pct,
    max(value_status)     FILTER (WHERE metric = 'new_stock_vacancy_rate') AS new_stock_vacancy_rate_status,
    max(reliability_code) FILTER (WHERE metric = 'new_stock_vacancy_rate') AS new_stock_vacancy_rate_reliability_code,
    max(value)            FILTER (WHERE metric = 'new_stock_average_rent') AS new_stock_average_rent,
    max(value_status)     FILTER (WHERE metric = 'new_stock_average_rent') AS new_stock_average_rent_status,
    max(reliability_code) FILTER (WHERE metric = 'new_stock_average_rent') AS new_stock_average_rent_reliability_code
FROM clean.rental_market_windsor
WHERE source_table = 'Table 3.1.7'
GROUP BY source_table, dwelling_scope, geography, zone, zone_level, bedroom_type, period_label;

COMMENT ON VIEW analysis.story2_new_rental_stock IS
    'Grain: zone x bedroom (Table 3.1.7, Oct-25). Universe, vacancy and rent of structures completed Jul 2022-Jun 2025.';


-- -----------------------------------------------------------------------------
-- analysis.story2_income_quintile_rental_stock
-- Question: how much of the rental stock is affordable to each renter income
-- quintile, and how vacant is it?
-- Grain: one row per zone x bedroom type x income quintile (Table 3.1.8,
-- Oct-25). CMHC classifies units by the quintile whose income could afford
-- the rent (renter_income_range / affordable_rent_range are CMHC's own text).
-- share_of_universe_pct = quintile universe / the same zone x bedroom 'Total'
-- universe, only when both are published.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story2_income_quintile_rental_stock AS
WITH q AS (
    SELECT
        source_table, dwelling_scope, geography, zone, zone_level, bedroom_type, period_label,
        income_quintile, renter_income_range, affordable_rent_range,
        max(value)            FILTER (WHERE metric = 'quintile_universe')     AS universe_units,
        max(value_status)     FILTER (WHERE metric = 'quintile_universe')     AS universe_status,
        max(reliability_code) FILTER (WHERE metric = 'quintile_universe')     AS universe_reliability_code,
        max(value)            FILTER (WHERE metric = 'quintile_vacancy_rate') AS vacancy_rate_pct,
        max(value_status)     FILTER (WHERE metric = 'quintile_vacancy_rate') AS vacancy_rate_status,
        max(reliability_code) FILTER (WHERE metric = 'quintile_vacancy_rate') AS vacancy_rate_reliability_code
    FROM clean.rental_market_windsor
    WHERE source_table = 'Table 3.1.8'
    GROUP BY source_table, dwelling_scope, geography, zone, zone_level, bedroom_type, period_label,
             income_quintile, renter_income_range, affordable_rent_range
)
SELECT
    q.*,
    CASE q.income_quintile WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2 WHEN 'Q3' THEN 3 WHEN 'Q4' THEN 4
                           WHEN 'Q5' THEN 5 WHEN 'N/A' THEN 6 WHEN 'Total' THEN 7 END AS quintile_order,
    t.universe_units AS total_universe_units,
    CASE WHEN q.income_quintile <> 'Total'
         THEN round(100.0 * q.universe_units / NULLIF(t.universe_units, 0), 4) END AS share_of_universe_pct
FROM q
JOIN q t
  ON t.zone = q.zone
 AND t.bedroom_type = q.bedroom_type
 AND t.income_quintile = 'Total';

COMMENT ON VIEW analysis.story2_income_quintile_rental_stock IS
    'Grain: zone x bedroom x income quintile (Table 3.1.8, Oct-25). Units affordable to each quintile, share and vacancy.';
