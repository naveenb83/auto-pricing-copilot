\timing on
-- 1) single-vehicle lookup the app does when a pricing manager opens a unit
SELECT i.stock_number, i.make, i.model, i.days_in_stock, i.current_price, r.recommended_discount, r.expected_days_to_sell_recommended, left(x.rationale, 80) AS rationale
FROM serving.inventory_current i JOIN serving.recommendations r USING (vin) LEFT JOIN serving.rationale x USING (vin)
WHERE i.stock_number = 'R03-24504';
-- 2) the pricing queue: aged units, biggest uplift first
SELECT stock_number, make, model, days_in_stock, recommended_discount, uplift_vs_flat_rule
FROM serving.recommendations WHERE days_in_stock >= 45 ORDER BY uplift_vs_flat_rule DESC LIMIT 5;
\timing off
-- 3) integrity: an override without a reason must be rejected by Postgres itself
BEGIN;
INSERT INTO pricing_ops.pricing_decisions (vin, stock_number, rooftop_id, list_price_before, model_value, model_version, override_value, final_discount, decision, decided_by)
VALUES ('CHECK000000000000', 'CHECK', 'R01', 20000, 500, '3', 1000, 1000, 'overridden', 'integrity-check');
ROLLBACK;
BEGIN;
INSERT INTO pricing_ops.pricing_decisions (vin, stock_number, rooftop_id, list_price_before, model_value, model_version, final_discount, decision, decided_by)
VALUES ('CHECK000000000000', 'CHECK', 'R01', 20000, 500, '3', 900, 'accepted', 'integrity-check');
ROLLBACK;
SELECT table_schema, table_name, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS rows
FROM information_schema.tables WHERE table_schema IN ('serving', 'pricing_ops') ORDER BY 1, 2;
