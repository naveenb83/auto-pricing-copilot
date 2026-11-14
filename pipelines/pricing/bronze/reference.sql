-- Reference data (small, slowly changing) loaded as batch materialized views.
CREATE OR REFRESH MATERIALIZED VIEW ref_rooftops
COMMENT "Reference. Pacific Isles Auto Group rooftops (dealerships), franchises and lot capacity."
AS SELECT rooftop_id, rooftop_name, franchises, CAST(lot_capacity AS INT) AS lot_capacity
FROM read_files('${landing_path}/reference/rooftops.csv', format => 'csv', header => true);

CREATE OR REFRESH MATERIALIZED VIEW ref_models
COMMENT "Reference. Make/model catalogue with body class and base MSRP."
AS SELECT make, model, body_class, CAST(base_msrp AS DOUBLE) AS base_msrp
FROM read_files('${landing_path}/reference/models.csv', format => 'csv', header => true);

CREATE OR REFRESH MATERIALIZED VIEW ref_floorplan_rates
COMMENT "Reference. Monthly floor-plan finance APR and lot cost per unit per day (drives holding cost)."
AS SELECT CAST(month AS DATE) AS month, lender, CAST(apr AS DOUBLE) AS apr, CAST(lot_cost_per_day AS DOUBLE) AS lot_cost_per_day
FROM read_files('${landing_path}/reference/floorplan_rates.csv', format => 'csv', header => true);

CREATE OR REFRESH MATERIALIZED VIEW ref_vehicle_images
COMMENT "Reference. One openly licensed Wikimedia Commons photo per make/model, with author and licence for attribution."
AS SELECT make, model, image_file, concat('${media_path}/', image_file) AS image_path, source_page, author, licence, licence_url
FROM read_files('${media_path}/vehicle_images.csv', format => 'csv', header => true)
QUALIFY row_number() OVER (PARTITION BY make, model ORDER BY image_file) = 1;  -- exactly one photo per make/model
