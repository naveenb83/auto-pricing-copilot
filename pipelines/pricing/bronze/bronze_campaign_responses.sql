-- Bronze: raw campaign_responses as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_campaign_responses
COMMENT "Bronze. Customer-level responses to each promotion. Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/campaign_responses/',
  format => 'json',
  schemaHints => 'campaign_id STRING, customer_id STRING, sent_date DATE, opened BOOLEAN, clicked BOOLEAN, lead_created BOOLEAN, purchased_within_30d BOOLEAN'
);
