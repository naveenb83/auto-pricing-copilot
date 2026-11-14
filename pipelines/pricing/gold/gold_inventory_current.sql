-- Today's lot: every on-hand unit with demand signals and the flat-rule baseline. Synced to Lakebase
-- for the app and used as real-time model input.
CREATE OR REFRESH MATERIALIZED VIEW gold_inventory_current
COMMENT "Gold. Current on-hand inventory (one row per VIN) with aging, price-to-market, holding cost, last-week and 4-week web demand, and the flat-rule discount baseline. Source for Lakebase sync and the pricing model."
TBLPROPERTIES ("quality" = "gold", "delta.enableChangeDataFeed" = "true")
AS WITH asof AS (SELECT DATE '${as_of_date}' AS d),
w AS (
  SELECT l.vin,
         max_by(l.vdp_views, l.week_start) AS vdp_views_last_week,
         max_by(l.leads, l.week_start) AS leads_last_week,
         max_by(l.test_drives, l.week_start) AS test_drives_last_week,
         sum(CASE WHEN l.week_start >= date_sub(asof.d, 28) THEN l.vdp_views END) AS vdp_views_4w,
         sum(CASE WHEN l.week_start >= date_sub(asof.d, 28) THEN l.leads END) AS leads_4w,
         sum(CASE WHEN l.week_start >= date_sub(asof.d, 28) THEN l.test_drives END) AS test_drives_4w,
         count(*) AS weeks_listed
  FROM silver_web_leads l CROSS JOIN asof WHERE l.week_start <= asof.d GROUP BY l.vin)
SELECT s.vin, s.stock_number, s.rooftop_id, s.rooftop_name, s.condition, s.make, s.model, s.trim, s.body_class,
       s.model_year, s.exterior_colour, s.mileage, s.msrp, s.unit_cost, s.initial_list_price, s.current_price,
       s.total_discount, s.price_change_count, s.acquisition_date, s.days_in_stock, s.aging_bucket,
       s.market_price, s.price_to_market, s.market_days_supply, s.comp_count,
       s.daily_floorplan_interest, s.daily_market_depreciation, s.daily_holding_cost, s.carrying_cost_to_date,
       s.flat_rule_discount, greatest(0, s.flat_rule_discount - s.total_discount) AS flat_rule_additional_discount,
       s.current_price - s.unit_cost AS front_gross_at_current_price,
       coalesce(w.vdp_views_last_week, 0) AS vdp_views_last_week, coalesce(w.leads_last_week, 0) AS leads_last_week,
       coalesce(w.test_drives_last_week, 0) AS test_drives_last_week,
       coalesce(w.vdp_views_4w, 0) AS vdp_views_4w, coalesce(w.leads_4w, 0) AS leads_4w,
       coalesce(w.test_drives_4w, 0) AS test_drives_4w, coalesce(w.weeks_listed, 0) AS weeks_listed,
       s.image_path, s.image_author, s.image_licence, s.image_source_page,
       DATE '${as_of_date}' AS as_of_date
FROM gold_vehicle_status s LEFT JOIN w ON w.vin = s.vin
WHERE s.status = 'on_hand';
