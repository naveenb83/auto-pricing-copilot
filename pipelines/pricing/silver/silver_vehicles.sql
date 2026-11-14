-- Silver vehicles: one clean row per VIN. Duplicated deliveries collapsed; rows that cannot be
-- priced (no unit cost) or are physically impossible (negative odometer) are dropped and counted.
CREATE OR REFRESH MATERIALIZED VIEW silver_vehicles (
  CONSTRAINT vin_present        EXPECT (vin IS NOT NULL AND length(vin) = 17) ON VIOLATION DROP ROW,
  CONSTRAINT unit_cost_present  EXPECT (unit_cost IS NOT NULL AND unit_cost > 0) ON VIOLATION DROP ROW,
  CONSTRAINT mileage_valid      EXPECT (mileage >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT price_above_cost   EXPECT (initial_list_price > unit_cost * 0.8)
)
COMMENT "Silver. One row per vehicle (VIN) acquired by the group, deduplicated and validated."
TBLPROPERTIES ("quality" = "silver")
AS SELECT vin, rooftop_id, stock_number, condition, make, model, trim, body_class, model_year,
          exterior_colour, mileage, msrp, unit_cost, initial_list_price, acquisition_date, acquisition_source
FROM bronze_vehicles
QUALIFY row_number() OVER (PARTITION BY vin ORDER BY ingested_at, source_file) = 1;
