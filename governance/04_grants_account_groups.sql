-- PRODUCTION grants for ACCOUNT-level groups (SCIM-synced from the IdP). NOT applied in the demo
-- workspace: its piag_* groups are workspace-local, which UC GRANT rejects (PRINCIPAL_DOES_NOT_EXIST);
-- the ABAC masks/filters still apply there via is_member(). Least privilege: ABAC decides WHAT a reader
-- sees inside a table; grants decide WHICH tables a role can read at all.
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;

-- sales analysts: KPIs and sales history only (costs/gross masked by policy unless also margin viewers)
GRANT USE CATALOG ON CATALOG serverless_stable_69fppe_catalog TO `piag_sales_analysts`;
GRANT USE SCHEMA ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `piag_sales_analysts`;
GRANT SELECT ON TABLE piag_pricing_kpis TO `piag_sales_analysts`;
GRANT SELECT ON TABLE gold_sales_enriched TO `piag_sales_analysts`;
GRANT SELECT ON TABLE gold_rooftop_weekly_kpis TO `piag_sales_analysts`;
GRANT SELECT ON TABLE gold_segment_response TO `piag_sales_analysts`;

-- pricing managers: the whole pricing schema (row filter still scopes them to their rooftops)
GRANT USE CATALOG ON CATALOG serverless_stable_69fppe_catalog TO `piag_pricing_managers`;
GRANT USE SCHEMA ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `piag_pricing_managers`;
GRANT SELECT ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `piag_pricing_managers`;
GRANT EXECUTE ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `piag_pricing_managers`;
