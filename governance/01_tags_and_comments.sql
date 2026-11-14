-- Unity Catalog classification for the PIAG pricing copilot.
-- Governed tags (tag policies created by setup_identity.sh): piag_sensitivity {financial, pii}, piag_scope {rooftop}.
-- Table-level tags describe domain / layer / owner so Genie, search and lineage stay self-describing.
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;

ALTER SCHEMA piag_pricing SET TAGS ('domain' = 'sales', 'piag_industry' = 'automotive_retail', 'piag_use_case' = 'aged_inventory_pricing', 'piag_data_origin' = 'synthetic');

-- financial: unit economics that only margin viewers (finance, pricing leadership) may see
ALTER MATERIALIZED VIEW silver_vehicles ALTER COLUMN unit_cost SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN unit_cost SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN front_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN total_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN fi_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN unit_cost SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN front_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN fi_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN total_gross SET TAGS ('piag_sensitivity' = 'financial');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN net_gross_after_carry SET TAGS ('piag_sensitivity' = 'financial');

-- pii: customer contact details (also carry the system classification tags)
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN email SET TAGS ('piag_sensitivity' = 'pii');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN email SET TAGS ('class.email_address');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN phone SET TAGS ('piag_sensitivity' = 'pii');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN phone SET TAGS ('class.phone_number');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN last_name SET TAGS ('piag_sensitivity' = 'pii');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN last_name SET TAGS ('class.name');
ALTER MATERIALIZED VIEW silver_customers ALTER COLUMN first_name SET TAGS ('class.name');

-- row scope: rooftop_id identifies the owning dealership on the analytical gold tables
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN rooftop_id SET TAGS ('piag_scope' = 'rooftop');
ALTER MATERIALIZED VIEW gold_sales_enriched ALTER COLUMN rooftop_id SET TAGS ('piag_scope' = 'rooftop');
ALTER MATERIALIZED VIEW gold_rooftop_weekly_kpis ALTER COLUMN rooftop_id SET TAGS ('piag_scope' = 'rooftop');

-- VIN is a vehicle identifier, not personal data here; classify it for discovery
ALTER MATERIALIZED VIEW gold_vehicle_status ALTER COLUMN vin SET TAGS ('class.vin');
ALTER MATERIALIZED VIEW gold_inventory_current ALTER COLUMN vin SET TAGS ('class.vin');

-- table-level layer / ownership tags (piag_ prefix: this shared workspace already governs
-- generic keys such as owner_team / ml with other teams' allowed values)
ALTER MATERIALIZED VIEW gold_inventory_current SET TAGS ('piag_layer' = 'gold', 'piag_serving' = 'lakebase_sync', 'piag_owner' = 'pricing');
ALTER MATERIALIZED VIEW gold_pricing_features_weekly SET TAGS ('piag_layer' = 'gold', 'piag_ml' = 'training_features', 'piag_owner' = 'data_science');
ALTER MATERIALIZED VIEW gold_vehicle_status SET TAGS ('piag_layer' = 'gold', 'piag_owner' = 'pricing');
ALTER MATERIALIZED VIEW gold_sales_enriched SET TAGS ('piag_layer' = 'gold', 'piag_owner' = 'sales_finance');
ALTER MATERIALIZED VIEW gold_segment_response SET TAGS ('piag_layer' = 'gold', 'piag_owner' = 'marketing');
ALTER MATERIALIZED VIEW gold_rooftop_weekly_kpis SET TAGS ('piag_layer' = 'gold', 'piag_owner' = 'group_leadership');
ALTER MATERIALIZED VIEW silver_customers SET TAGS ('piag_layer' = 'silver', 'piag_contains_pii' = 'true');
