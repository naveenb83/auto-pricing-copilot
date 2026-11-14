-- Bronze: raw vehicles as delivered in weekly DMS drops (Auto Loader, incremental, exactly-once).
CREATE OR REFRESH STREAMING TABLE bronze_vehicles
COMMENT "Bronze. Vehicle acquisitions (new factory allocations and used trade-ins/auction buys) from the DMS. Raw, append-only, one row per delivered record (duplicates kept)."
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_path}/vehicles/',
  format => 'csv', header => true,
  schemaHints => 'vin STRING, rooftop_id STRING, stock_number STRING, condition STRING, make STRING, model STRING, trim STRING, body_class STRING, model_year INT, exterior_colour STRING, mileage INT, msrp DOUBLE, unit_cost DOUBLE, initial_list_price DOUBLE, acquisition_date DATE, acquisition_source STRING'
);
