-- Current state of every pricing decision, rebuilt from the Lakehouse Sync CDC history
-- (latest post-image per decision_id; deleted decisions drop out). Used by Genie and the impact KPIs.
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;
CREATE OR REPLACE VIEW pricing_decisions
COMMENT 'Current pricing decisions made in the app (Model/DS value vs pricing-manager override value + reason), from Lakebase via Lakehouse Sync CDC. One row per decision.'
AS SELECT decision_id, vin, stock_number, rooftop_id, days_in_stock, list_price_before, model_value, model_version,
          model_source, model_expected_profit, model_p_sell_30d, override_value, final_discount, decision,
          reason_code, reason_text, override_expected_profit, decided_by, decided_at,
          final_discount - model_value AS override_delta, _timestamp AS synced_at
FROM (
  SELECT *, row_number() OVER (PARTITION BY decision_id ORDER BY _sort_by DESC) AS rn
  FROM lb_pricing_decisions_history
  WHERE _pg_change_type IN ('insert', 'update_postimage', 'delete'))
WHERE rn = 1 AND _pg_change_type <> 'delete';
