-- Bronze: raw web_leads as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_web_leads
COMMENT "Bronze. Weekly website demand signals per vehicle (vehicle detail page views, leads, test drives). Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/web_leads/',
  format => 'json',
  schemaHints => 'vin STRING, week_start DATE, vdp_views INT, leads INT, test_drives INT, days_listed INT'
);
