CREATE OR REFRESH MATERIALIZED VIEW gold_sales_enriched
COMMENT "Gold. Every vehicle disposition with vehicle attributes, buyer segment, days in stock, discount given and front/total gross. Use for sales, gross and aging-at-sale questions."
TBLPROPERTIES ("quality" = "gold")
AS SELECT s.deal_id, s.vin, s.rooftop_id, s.rooftop_name, s.status AS channel, s.disposed_date AS sale_date,
          date_trunc('MONTH', s.disposed_date) AS sale_month, s.condition, s.make, s.model, s.trim, s.body_class,
          s.model_year, s.exterior_colour, s.days_in_stock, s.aging_bucket AS aging_bucket_at_sale,
          s.initial_list_price, s.current_price AS list_price_at_sale, s.total_discount, s.sale_price, s.unit_cost,
          s.front_gross, s.fi_gross, s.total_gross,
          round(s.days_in_stock * (s.daily_floorplan_interest + s.lot_cost_per_day), 0) AS carrying_cost,
          s.total_gross - round(s.days_in_stock * (s.daily_floorplan_interest + s.lot_cost_per_day), 0) AS net_gross_after_carry,
          s.customer_id, c.segment AS customer_segment, c.region AS customer_region
FROM gold_vehicle_status s LEFT JOIN silver_customers c ON c.customer_id = s.customer_id
WHERE s.status <> 'on_hand';
