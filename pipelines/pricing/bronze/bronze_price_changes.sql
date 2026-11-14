-- Bronze: raw price_changes as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_price_changes
COMMENT "Bronze. Every list-price change made by pricing managers. Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/price_changes/',
  format => 'csv', header => true,
  schemaHints => 'vin STRING, change_date DATE, old_price DOUBLE, new_price DOUBLE, reason STRING, changed_by STRING'
);
