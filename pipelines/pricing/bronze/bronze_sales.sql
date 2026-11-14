-- Bronze: raw sales as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_sales
COMMENT "Bronze. Vehicle dispositions: retail deals, wholesale auction exits and dealer trades. Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/sales/',
  format => 'csv', header => true,
  schemaHints => 'deal_id STRING, vin STRING, rooftop_id STRING, sale_date DATE, channel STRING, sale_price DOUBLE, list_price_at_sale DOUBLE, customer_id STRING, payment_type STRING, fi_gross DOUBLE, days_in_stock INT, salesperson_id STRING'
);
