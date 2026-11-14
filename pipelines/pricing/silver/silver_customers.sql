CREATE OR REFRESH MATERIALIZED VIEW silver_customers (
  CONSTRAINT customer_id_present EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT segment_known EXPECT (segment IN ('first_time_buyer','young_family','active_lifestyle','trades_and_fleet','value_retiree'))
)
COMMENT "Silver. CRM customers with marketing segment. Contains PII (name, email, phone) — masked by Unity Catalog policy."
TBLPROPERTIES ("quality" = "silver")
AS SELECT customer_id, first_name, last_name, email, phone, region, age_band, segment, signup_date
FROM bronze_customers
QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY ingested_at) = 1;
