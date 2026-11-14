-- One row per vehicle with lifecycle status as of the business date, current price, market position
-- and unit economics (holding cost per day = floor-plan interest + lot cost + observed market depreciation).
CREATE OR REFRESH MATERIALIZED VIEW gold_vehicle_status
COMMENT "Gold. One row per vehicle: status (on_hand / retail / wholesale / dealer_trade), days in stock, current price, discount, price-to-market, daily holding cost and realised gross. Business date = pipeline as_of_date."
TBLPROPERTIES ("quality" = "gold")
AS WITH
asof AS (SELECT DATE '${as_of_date}' AS d),
disp AS (
  SELECT vin, sale_date, channel, sale_price, fi_gross, customer_id, deal_id, list_price_at_sale
  FROM silver_sales QUALIFY row_number() OVER (PARTITION BY vin ORDER BY sale_date) = 1),
px AS (
  SELECT pc.vin, max_by(pc.new_price, pc.change_date) AS last_price, max(pc.change_date) AS last_price_change_date,
         count(*) AS price_change_count,
         sum(CASE WHEN pc.reason IN ('aged_45_rule','aged_90_rule') THEN 1 ELSE 0 END) AS rule_price_changes
  FROM silver_price_changes pc CROSS JOIN asof WHERE pc.change_date <= asof.d GROUP BY pc.vin),
comps AS (
  SELECT c.vin, max_by(c.market_avg_price, c.snapshot_date) AS market_price, max(c.snapshot_date) AS market_snapshot_date,
         max_by(c.market_days_supply, c.snapshot_date) AS market_days_supply,
         max_by(c.comp_count, c.snapshot_date) AS comp_count,
         regr_slope(c.market_avg_price, unix_date(c.snapshot_date)) AS market_slope_per_day,
         count(*) AS comp_snapshots
  FROM silver_market_comps c CROSS JOIN asof WHERE c.snapshot_date <= asof.d GROUP BY c.vin),
-- robust daily depreciation: per-vehicle trend when >= 4 weekly comps, else the average trend of
-- similar vehicles (same condition + body class)
cls AS (
  SELECT v.condition, v.body_class, avg(c.market_slope_per_day) AS class_slope_per_day
  FROM comps c JOIN silver_vehicles v ON v.vin = c.vin WHERE c.comp_snapshots >= 4 GROUP BY ALL),
dep AS (
  SELECT v.vin, round(greatest(0, -coalesce(CASE WHEN c.comp_snapshots >= 4 THEN c.market_slope_per_day END,
                                              cls.class_slope_per_day, 0)), 2) AS daily_market_depreciation
  FROM silver_vehicles v LEFT JOIN comps c ON c.vin = v.vin
  LEFT JOIN cls ON cls.condition = v.condition AND cls.body_class = v.body_class),
fp AS (SELECT apr, lot_cost_per_day FROM ref_floorplan_rates ORDER BY month DESC LIMIT 1)
SELECT
  v.vin, v.stock_number, v.rooftop_id, r.rooftop_name, v.condition, v.make, v.model, v.trim, v.body_class,
  v.model_year, v.exterior_colour, v.mileage, v.msrp, v.unit_cost, v.initial_list_price,
  v.acquisition_date, v.acquisition_source,
  CASE WHEN d.vin IS NULL THEN 'on_hand' ELSE d.channel END AS status,
  d.sale_date AS disposed_date,
  datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) AS days_in_stock,
  CASE WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 90 THEN '90+'
       WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 60 THEN '60-89'
       WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 45 THEN '45-59'
       WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 30 THEN '30-44'
       ELSE '0-29' END AS aging_bucket,
  coalesce(d.list_price_at_sale, px.last_price, v.initial_list_price) AS current_price,
  v.initial_list_price - coalesce(d.list_price_at_sale, px.last_price, v.initial_list_price) AS total_discount,
  coalesce(px.price_change_count, 0) AS price_change_count,
  px.last_price_change_date,
  c.market_price, c.market_days_supply, c.comp_count,
  round(coalesce(d.list_price_at_sale, px.last_price, v.initial_list_price) / c.market_price, 4) AS price_to_market,
  round(v.unit_cost * fp.apr / 365, 2) AS daily_floorplan_interest,
  fp.lot_cost_per_day,
  dep.daily_market_depreciation,
  round(v.unit_cost * fp.apr / 365 + fp.lot_cost_per_day + dep.daily_market_depreciation, 2) AS daily_holding_cost,
  round(datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) * (v.unit_cost * fp.apr / 365 + fp.lot_cost_per_day), 0) AS carrying_cost_to_date,
  CASE WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 90 THEN 500
       WHEN datediff(coalesce(d.sale_date, asof.d), v.acquisition_date) >= 45 THEN 250 ELSE 0 END AS flat_rule_discount,
  d.deal_id, d.sale_price, d.customer_id, d.fi_gross,
  d.sale_price - v.unit_cost AS front_gross,
  d.sale_price - v.unit_cost + coalesce(d.fi_gross, 0) AS total_gross,
  img.image_path, img.author AS image_author, img.licence AS image_licence, img.source_page AS image_source_page
FROM silver_vehicles v
CROSS JOIN asof
CROSS JOIN fp
LEFT JOIN disp d ON d.vin = v.vin AND d.sale_date <= asof.d
LEFT JOIN px ON px.vin = v.vin
LEFT JOIN comps c ON c.vin = v.vin
LEFT JOIN dep ON dep.vin = v.vin
LEFT JOIN ref_rooftops r ON r.rooftop_id = v.rooftop_id
LEFT JOIN ref_vehicle_images img ON img.make = v.make AND img.model = v.model
WHERE v.acquisition_date <= asof.d;
