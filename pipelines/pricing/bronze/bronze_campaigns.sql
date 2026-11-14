-- Bronze: raw campaigns as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_campaigns
COMMENT "Bronze. Marketing promotions (offer amount by body class). Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/campaigns/',
  format => 'csv', header => true,
  schemaHints => 'campaign_id STRING, launch_date DATE, target_body_class STRING, offer_amount INT, channel STRING, name STRING'
);
