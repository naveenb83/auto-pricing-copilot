CREATE OR REFRESH MATERIALIZED VIEW silver_price_changes (
  CONSTRAINT price_decreases EXPECT (new_price < old_price) ON VIOLATION DROP ROW
)
COMMENT "Silver. Deduplicated list-price changes with the reason (flat aged rule, manager discretion, market adjustment)."
TBLPROPERTIES ("quality" = "silver")
AS SELECT vin, change_date, old_price, new_price, old_price - new_price AS reduction, reason, changed_by
FROM bronze_price_changes
QUALIFY row_number() OVER (PARTITION BY vin, change_date, new_price ORDER BY ingested_at) = 1;
