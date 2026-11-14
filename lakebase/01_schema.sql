-- Lakebase Postgres (project piag-pricing, database databricks_postgres)
-- serving   : read-optimised copies of governed gold tables for the app (published by lakebase_publish)
-- pricing_ops: OLTP tables the app WRITES — every pricing decision with model vs override value + reason
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS pricing_ops;

CREATE TABLE IF NOT EXISTS pricing_ops.pricing_decisions (
  decision_id            BIGSERIAL PRIMARY KEY,
  vin                    TEXT        NOT NULL,
  stock_number           TEXT        NOT NULL,
  rooftop_id             TEXT        NOT NULL,
  days_in_stock          INT,
  list_price_before      NUMERIC(12,2) NOT NULL,
  model_value            NUMERIC(12,2) NOT NULL,       -- Model/DS recommended additional discount
  model_version          TEXT        NOT NULL,
  model_source           TEXT        NOT NULL DEFAULT 'realtime_endpoint', -- realtime_endpoint | batch_score
  model_expected_profit  NUMERIC(12,2),
  model_p_sell_30d       NUMERIC(6,4),
  override_value         NUMERIC(12,2),               -- pricing manager's discount when they disagree
  final_discount         NUMERIC(12,2) NOT NULL,
  decision               TEXT        NOT NULL CHECK (decision IN ('accepted', 'overridden', 'held')),
  reason_code            TEXT,                         -- required when overridden
  reason_text            TEXT,
  override_expected_profit NUMERIC(12,2),             -- model's view of the override (what-if call)
  decided_by             TEXT        NOT NULL,
  decided_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT override_needs_reason CHECK (decision <> 'overridden' OR (override_value IS NOT NULL AND reason_code IS NOT NULL)),
  CONSTRAINT final_matches CHECK (final_discount = COALESCE(override_value, model_value) OR decision = 'held')
);
CREATE INDEX IF NOT EXISTS pricing_decisions_vin_idx ON pricing_ops.pricing_decisions (vin, decided_at DESC);
CREATE INDEX IF NOT EXISTS pricing_decisions_rooftop_idx ON pricing_ops.pricing_decisions (rooftop_id, decided_at DESC);
-- Lakehouse Sync (CDC to Unity Catalog) requires full replica identity
ALTER TABLE pricing_ops.pricing_decisions REPLICA IDENTITY FULL;

CREATE TABLE IF NOT EXISTS pricing_ops.override_reasons (
  reason_code TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  sort_order  INT  NOT NULL
);
ALTER TABLE pricing_ops.override_reasons REPLICA IDENTITY FULL;
INSERT INTO pricing_ops.override_reasons VALUES
  ('customer_in_negotiation', 'Customer already negotiating on this unit', 1),
  ('reconditioning_pending',  'Reconditioning / photos not finished yet', 2),
  ('manufacturer_incentive',  'Manufacturer incentive or holdback changes the maths', 3),
  ('local_market_knowledge',  'Local market knowledge (event, competitor, season)', 4),
  ('trade_or_wholesale_plan', 'Planned dealer trade or wholesale exit', 5),
  ('margin_protection',       'Protect margin — unit is rare / high demand', 6),
  ('other',                   'Other (explain in notes)', 9)
ON CONFLICT (reason_code) DO UPDATE SET label = EXCLUDED.label, sort_order = EXCLUDED.sort_order;
