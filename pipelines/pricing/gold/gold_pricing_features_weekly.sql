-- ML training panel: one row per vehicle per week on the lot (decision-time features) with the label
-- "sold at retail during this week". Discrete-time hazard model -> expected days to sell under any price.
CREATE OR REFRESH MATERIALIZED VIEW gold_pricing_features_weekly
COMMENT "Gold / ML. Vehicle-week panel for the time-to-sell model: features known at the start of each week (age, price-to-market, discount to date, prior-week demand, market days supply) and label sold_retail_this_week."
TBLPROPERTIES ("quality" = "gold")
CLUSTER BY (week_start)
AS WITH
base AS (
  SELECT l.vin, l.week_start, l.vdp_views, l.leads, l.test_drives, l.days_listed,
         lag(l.vdp_views) OVER (PARTITION BY l.vin ORDER BY l.week_start) AS prev_vdp_views,
         lag(l.leads) OVER (PARTITION BY l.vin ORDER BY l.week_start) AS prev_leads,
         lag(l.test_drives) OVER (PARTITION BY l.vin ORDER BY l.week_start) AS prev_test_drives,
         row_number() OVER (PARTITION BY l.vin ORDER BY l.week_start) - 1 AS weeks_listed_before
  FROM silver_web_leads l),
px AS (
  SELECT b.vin, b.week_start, max_by(pc.new_price, pc.change_date) AS price_at_week_start
  FROM base b JOIN silver_price_changes pc ON pc.vin = b.vin AND pc.change_date < b.week_start
  GROUP BY b.vin, b.week_start),
mk AS (
  SELECT b.vin, b.week_start, max_by(c.market_avg_price, c.snapshot_date) AS market_price,
         max_by(c.market_days_supply, c.snapshot_date) AS market_days_supply
  FROM base b JOIN silver_market_comps c ON c.vin = b.vin
   AND c.snapshot_date BETWEEN b.week_start AND date_add(b.week_start, 6)
  GROUP BY b.vin, b.week_start),
disp AS (  -- first disposition per VIN on or before the business date (one row per VIN)
  SELECT vin, sale_date, channel FROM silver_sales WHERE sale_date <= DATE '${as_of_date}'
  QUALIFY row_number() OVER (PARTITION BY vin ORDER BY sale_date, deal_id) = 1)
SELECT b.vin, b.week_start, month(b.week_start) AS month,
       v.rooftop_id, v.condition, v.make, v.model, v.body_class, v.model_year, v.exterior_colour, v.mileage,
       greatest(0, year(b.week_start) - v.model_year) AS vehicle_age_years,
       greatest(0, datediff(b.week_start, v.acquisition_date)) AS age_days,
       v.initial_list_price, coalesce(px.price_at_week_start, v.initial_list_price) AS price,
       v.initial_list_price - coalesce(px.price_at_week_start, v.initial_list_price) AS discount_to_date,
       round((v.initial_list_price - coalesce(px.price_at_week_start, v.initial_list_price)) / v.initial_list_price, 4) AS discount_to_date_pct,
       mk.market_price, mk.market_days_supply,
       round(coalesce(px.price_at_week_start, v.initial_list_price) / mk.market_price, 4) AS price_to_market,
       coalesce(b.prev_vdp_views, 0) AS prev_vdp_views, coalesce(b.prev_leads, 0) AS prev_leads,
       coalesce(b.prev_test_drives, 0) AS prev_test_drives, b.weeks_listed_before,
       b.days_listed,
       CASE WHEN s.channel = 'retail' AND s.sale_date BETWEEN b.week_start AND date_add(b.week_start, 6) THEN 1 ELSE 0 END AS sold_retail_this_week,
       CASE WHEN s.channel <> 'retail' AND s.sale_date BETWEEN b.week_start AND date_add(b.week_start, 6) THEN 1 ELSE 0 END AS exited_other_this_week,
       b.week_start <= date_sub(DATE '${as_of_date}', 7) AS is_complete_week
FROM base b
JOIN silver_vehicles v ON v.vin = b.vin
LEFT JOIN px ON px.vin = b.vin AND px.week_start = b.week_start
LEFT JOIN mk ON mk.vin = b.vin AND mk.week_start = b.week_start
LEFT JOIN disp s ON s.vin = b.vin
WHERE mk.market_price IS NOT NULL;
