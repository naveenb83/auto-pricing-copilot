-- Governed KPI layer for Genie, the app and dashboards. One fact source (gold_vehicle_status):
-- inventory measures filter status = 'on_hand'; sales measures filter retail dispositions.
-- ABAC masks on the source flow through: gross measures return NULL for non-margin-viewers.
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;

CREATE OR REPLACE VIEW piag_pricing_kpis
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: serverless_stable_69fppe_catalog.piag_pricing.gold_vehicle_status
comment: "Pacific Isles Auto Group aged-inventory and retail KPIs (business date 2026-11-13). One row per vehicle in the source."
dimensions:
  - name: Rooftop
    expr: rooftop_name
    comment: "Dealership (rooftop) name"
    synonyms: ["dealership", "store", "location", "branch"]
  - name: Condition
    expr: condition
    comment: "new or used"
  - name: Make
    expr: make
    synonyms: ["brand", "manufacturer"]
  - name: Model
    expr: model
  - name: Body Class
    expr: body_class
    synonyms: ["vehicle type", "segment of vehicle"]
  - name: Model Year
    expr: model_year
  - name: Aging Bucket
    expr: aging_bucket
    comment: "Days-in-stock band: 0-29, 30-44, 45-59, 60-89, 90+"
    synonyms: ["age band", "days in stock band"]
  - name: Status
    expr: status
    comment: "on_hand, retail, wholesale or dealer_trade"
  - name: Disposed Month
    expr: date_trunc('MONTH', disposed_date)
    comment: "Month the vehicle was sold or exited"
    synonyms: ["sale month", "sold month"]
measures:
  - name: Units On Hand
    expr: COUNT(1) FILTER (WHERE status = 'on_hand')
    synonyms: ["inventory", "stock", "units in stock"]
  - name: Aged 90+ Units
    expr: COUNT(1) FILTER (WHERE status = 'on_hand' AND days_in_stock >= 90)
    synonyms: ["aged units", "stale inventory", "over 90 days"]
  - name: Aged 45+ Units
    expr: COUNT(1) FILTER (WHERE status = 'on_hand' AND days_in_stock >= 45)
  - name: Aged 90+ Share
    expr: COUNT(1) FILTER (WHERE status = 'on_hand' AND days_in_stock >= 90) / NULLIF(COUNT(1) FILTER (WHERE status = 'on_hand'), 0)
    comment: "Share of on-hand units older than 90 days"
    format:
      type: percentage
  - name: Avg Days In Stock
    expr: AVG(days_in_stock) FILTER (WHERE status = 'on_hand')
    synonyms: ["average age", "average days on lot"]
  - name: Holding Cost Per Day
    expr: SUM(daily_holding_cost) FILTER (WHERE status = 'on_hand')
    comment: "Daily cost of carrying current stock: floor-plan interest + lot cost + market depreciation (USD/day)"
    synonyms: ["carrying cost", "daily burn", "floor plan cost"]
    format:
      type: currency
      currency_code: USD
  - name: Holding Cost Per Day Aged 90+
    expr: SUM(daily_holding_cost) FILTER (WHERE status = 'on_hand' AND days_in_stock >= 90)
    format:
      type: currency
      currency_code: USD
  - name: Avg Discount On Hand
    expr: AVG(total_discount) FILTER (WHERE status = 'on_hand')
    format:
      type: currency
      currency_code: USD
  - name: Retail Units Sold
    expr: COUNT(1) FILTER (WHERE status = 'retail')
    synonyms: ["sales", "units sold", "deliveries"]
  - name: Avg Days To Sell
    expr: AVG(days_in_stock) FILTER (WHERE status = 'retail')
    synonyms: ["days to turn", "average turn time"]
  - name: Avg Front Gross
    expr: AVG(front_gross) FILTER (WHERE status = 'retail')
    comment: "Average sale price minus unit cost per retail unit (masked unless piag_margin_viewers)"
    synonyms: ["gross per unit", "PVR", "front-end gross"]
    format:
      type: currency
      currency_code: USD
  - name: Total Gross
    expr: SUM(total_gross) FILTER (WHERE status = 'retail')
    comment: "Front gross + F&I gross (masked unless piag_margin_viewers)"
    format:
      type: currency
      currency_code: USD
  - name: Wholesale Exits
    expr: COUNT(1) FILTER (WHERE status = 'wholesale')
    synonyms: ["auction exits", "wholesaled units"]
  - name: Wholesale Loss
    expr: SUM(front_gross) FILTER (WHERE status = 'wholesale')
    comment: "Gross on wholesale exits (usually negative) — the cost of letting units age out"
    format:
      type: currency
      currency_code: USD
$$;
