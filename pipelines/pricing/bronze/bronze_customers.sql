-- Bronze: raw customers as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_customers
COMMENT "Bronze. CRM customer records (synthetic PII). Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/customers/',
  format => 'csv', header => true,
  schemaHints => 'customer_id STRING, first_name STRING, last_name STRING, email STRING, phone STRING, region STRING, age_band STRING, segment STRING, signup_date DATE'
);
