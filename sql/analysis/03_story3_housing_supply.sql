-- =============================================================================
-- STORY 3 -- WINDSOR HOUSING SUPPLY (CMHC starts / completions, August 2026)
-- Source: clean.starts_completions_windsor only (Windsor row of Tables A4_1,
-- A5_1, A6_1). Windsor CMA only; no Ontario or Canada values.
--
-- Periods: 'August 2026' (month; under construction = stock at month end) and
-- 'January to August 2026' (year to date). One edition: no trend, no
-- annualisation.
--
-- The published 'Total' row is never added to the components. Component sums
-- use the four dwelling types (Singles, Semis, Row, Apt. and Other) and are
-- compared with the published Total. CMHC '-' (Nil or Zero) is 0 in clean.*
-- (value_flag = 'nil_or_zero') and is kept visible here.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- analysis.story3_supply_totals
-- Question: do the dwelling-type components reconcile with CMHC's Total?
-- Grain: one row per activity x period (5 rows).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_supply_totals AS
SELECT
    geography,
    source_table,
    activity,
    period_label,
    period_type,
    sum(units) FILTER (WHERE dwelling_type <> 'Total')   AS component_sum_units,
    count(*)   FILTER (WHERE dwelling_type <> 'Total')   AS component_count,
    count(units) FILTER (WHERE dwelling_type <> 'Total') AS components_with_value,
    max(units) FILTER (WHERE dwelling_type = 'Total')    AS published_total_units,
    max(units) FILTER (WHERE dwelling_type = 'Total')
      - sum(units) FILTER (WHERE dwelling_type <> 'Total') AS total_minus_component_sum,
    (sum(units) FILTER (WHERE dwelling_type <> 'Total') = max(units) FILTER (WHERE dwelling_type = 'Total')
     AND count(units) FILTER (WHERE dwelling_type <> 'Total') = count(*) FILTER (WHERE dwelling_type <> 'Total'))
                                                        AS total_reconciles
FROM clean.starts_completions_windsor
GROUP BY geography, source_table, activity, period_label, period_type;

COMMENT ON VIEW analysis.story3_supply_totals IS
    'Grain: activity x period. Sum of the four dwelling-type components vs the published Total.';


-- -----------------------------------------------------------------------------
-- analysis.story3_supply_by_dwelling_type
-- Question: what is the dwelling-type composition of starts, completions and
-- units under construction?
-- Grain: one row per activity x period x component dwelling type (Total row
-- excluded; it is carried as published_total_units). share_of_total_pct uses
-- the component sum as denominator, and is only computed when every component
-- has a value and the components reconcile with the published Total.
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_supply_by_dwelling_type AS
SELECT
    s.geography,
    s.source_table,
    s.activity,
    s.period_label,
    s.period_type,
    s.dwelling_type,
    CASE s.dwelling_type WHEN 'Singles' THEN 1 WHEN 'Semis' THEN 2 WHEN 'Row' THEN 3
                         WHEN 'Apt. and Other' THEN 4 END AS dwelling_type_order,
    s.units,
    s.value_flag,
    t.component_sum_units,
    t.published_total_units,
    t.total_reconciles,
    CASE WHEN t.total_reconciles
         THEN round(100.0 * s.units / NULLIF(t.component_sum_units, 0), 4) END AS share_of_total_pct,
    s.source_cell
FROM clean.starts_completions_windsor s
JOIN analysis.story3_supply_totals t
  ON t.source_table = s.source_table
 AND t.activity = s.activity
WHERE s.dwelling_type <> 'Total';

COMMENT ON VIEW analysis.story3_supply_by_dwelling_type IS
    'Grain: activity x period x dwelling type (components only). Units and share of the reconciled total.';


-- -----------------------------------------------------------------------------
-- analysis.story3_starts_by_dwelling_type
-- Question: what was started in August 2026, by dwelling type?
-- Grain: one row per dwelling type (month = August 2026).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_starts_by_dwelling_type AS
SELECT * FROM analysis.story3_supply_by_dwelling_type
WHERE activity = 'Starts' AND period_type = 'month';

COMMENT ON VIEW analysis.story3_starts_by_dwelling_type IS
    'Grain: dwelling type. Housing starts in August 2026 and share of the total.';


-- -----------------------------------------------------------------------------
-- analysis.story3_completions_by_dwelling_type
-- Question: what was completed in August 2026, by dwelling type?
-- Grain: one row per dwelling type (month = August 2026).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_completions_by_dwelling_type AS
SELECT * FROM analysis.story3_supply_by_dwelling_type
WHERE activity = 'Completions' AND period_type = 'month';

COMMENT ON VIEW analysis.story3_completions_by_dwelling_type IS
    'Grain: dwelling type. Completions in August 2026 and share of the total.';


-- -----------------------------------------------------------------------------
-- analysis.story3_under_construction_by_dwelling_type
-- Question: how many units were under construction at the end of August 2026?
-- Grain: one row per dwelling type (stock at month end).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_under_construction_by_dwelling_type AS
SELECT * FROM analysis.story3_supply_by_dwelling_type
WHERE activity = 'Under Construction' AND period_type = 'stock_at_month_end';

COMMENT ON VIEW analysis.story3_under_construction_by_dwelling_type IS
    'Grain: dwelling type. Units under construction at the end of August 2026 and share of the total.';


-- -----------------------------------------------------------------------------
-- analysis.story3_ytd_starts_completions
-- Question: what was started and completed from January to August 2026?
-- Grain: one row per dwelling type, starts and completions side by side.
-- completions_minus_starts is a plain difference of two YTD counts (not a
-- trend and not a forecast).
-- -----------------------------------------------------------------------------
CREATE VIEW analysis.story3_ytd_starts_completions AS
SELECT
    geography,
    period_label,
    dwelling_type,
    dwelling_type_order,
    max(units)              FILTER (WHERE activity = 'Starts')      AS ytd_starts_units,
    max(share_of_total_pct) FILTER (WHERE activity = 'Starts')      AS ytd_starts_share_pct,
    max(units)              FILTER (WHERE activity = 'Completions') AS ytd_completions_units,
    max(share_of_total_pct) FILTER (WHERE activity = 'Completions') AS ytd_completions_share_pct,
    max(units) FILTER (WHERE activity = 'Completions')
      - max(units) FILTER (WHERE activity = 'Starts')               AS completions_minus_starts_units,
    max(published_total_units) FILTER (WHERE activity = 'Starts')      AS ytd_starts_published_total,
    max(published_total_units) FILTER (WHERE activity = 'Completions') AS ytd_completions_published_total
FROM analysis.story3_supply_by_dwelling_type
WHERE period_type = 'year_to_date'
GROUP BY geography, period_label, dwelling_type, dwelling_type_order;

COMMENT ON VIEW analysis.story3_ytd_starts_completions IS
    'Grain: dwelling type. January-August 2026 starts and completions with shares of each total.';
