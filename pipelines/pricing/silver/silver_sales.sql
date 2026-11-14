CREATE OR REFRESH MATERIALIZED VIEW silver_sales (
  CONSTRAINT deal_id_present   EXPECT (deal_id IS NOT NULL) ON VIOLATION DROP ROW,
  -- warn only: the disposition really happened (the car left the lot); only the price value is bad,
  -- so keep the event and null the price rather than make a sold car look like it is still on hand
  CONSTRAINT sale_price_valid  EXPECT (sale_price > 0),
  CONSTRAINT channel_known     EXPECT (channel IN ('retail', 'wholesale', 'dealer_trade'))
)
COMMENT "Silver. One row per vehicle disposition (retail deal, wholesale auction exit or dealer trade)."
TBLPROPERTIES ("quality" = "silver")
AS SELECT deal_id, vin, rooftop_id, sale_date, channel,
          CASE WHEN sale_price > 0 THEN sale_price END AS sale_price,
          sale_price > 0 AS sale_price_is_valid, list_price_at_sale, customer_id,
          payment_type, fi_gross, days_in_stock, salesperson_id
FROM bronze_sales
QUALIFY row_number() OVER (PARTITION BY deal_id ORDER BY ingested_at) = 1;
