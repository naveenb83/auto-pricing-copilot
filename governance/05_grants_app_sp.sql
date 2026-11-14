-- Least-privilege grants for the Databricks App's service principal (account-level identity, so UC GRANT works).
-- Read-only on the pricing schema (KPIs, charts, typegen) + the photo volume; nothing else.
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;
GRANT USE CATALOG ON CATALOG serverless_stable_69fppe_catalog TO `18d1bc33-eabe-4547-82e1-24cc3f835482`;
GRANT USE SCHEMA ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `18d1bc33-eabe-4547-82e1-24cc3f835482`;
GRANT SELECT ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing TO `18d1bc33-eabe-4547-82e1-24cc3f835482`;
GRANT READ VOLUME ON VOLUME serverless_stable_69fppe_catalog.piag_pricing.media TO `18d1bc33-eabe-4547-82e1-24cc3f835482`;
SHOW GRANTS `18d1bc33-eabe-4547-82e1-24cc3f835482` ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing;
