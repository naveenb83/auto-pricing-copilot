-- Bronze: raw market_comps as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_market_comps
COMMENT "Bronze. Weekly market pricing comps per vehicle from the pricing-tool feed. Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/market_comps/',
  format => 'csv', header => true,
  schemaHints => 'vin STRING, snapshot_date DATE, market_avg_price DOUBLE, comp_count INT, market_days_supply DOUBLE'
);
