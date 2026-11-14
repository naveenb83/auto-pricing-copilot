CREATE OR REFRESH MATERIALIZED VIEW silver_market_comps (
  CONSTRAINT market_price_positive EXPECT (market_avg_price > 0) ON VIOLATION DROP ROW
)
COMMENT "Silver. Weekly market average price, comparable-listing count and market days supply per vehicle."
TBLPROPERTIES ("quality" = "silver")
AS SELECT vin, snapshot_date, market_avg_price, comp_count, market_days_supply
FROM bronze_market_comps
QUALIFY row_number() OVER (PARTITION BY vin, snapshot_date ORDER BY ingested_at) = 1;
