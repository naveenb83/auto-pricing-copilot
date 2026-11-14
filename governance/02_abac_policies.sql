-- Attribute-based access control: policies attach to the SCHEMA and match columns by governed tag,
-- so any current or future table tagged financial / pii / rooftop is protected automatically.
-- Functions are deliberately cheap and deterministic: a group-membership check only — no lookup
-- tables (lookup-table masks multiply query compile time per masked column).
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;

CREATE OR REPLACE FUNCTION mask_financial(v DOUBLE)
RETURNS DOUBLE
COMMENT 'ABAC column mask: unit cost / gross visible only to members of piag_margin_viewers, otherwise NULL.'
RETURN CASE WHEN is_member('piag_margin_viewers') THEN v ELSE NULL END;

CREATE OR REPLACE FUNCTION mask_pii(v STRING)
RETURNS STRING
COMMENT 'ABAC column mask: customer contact details visible only to piag_crm_admins; others see first character + ****.'
RETURN CASE WHEN is_member('piag_crm_admins') THEN v WHEN v IS NULL THEN NULL ELSE concat(left(v, 1), '****') END;

CREATE OR REPLACE FUNCTION filter_rooftop(rooftop STRING)
RETURNS BOOLEAN
COMMENT 'ABAC row filter: group leadership sees every rooftop; rooftop staff see rows for rooftops whose piag_rooftop_<id> group they belong to.'
RETURN is_member('piag_group_leadership') OR is_member(concat('piag_rooftop_', rooftop));

CREATE OR REPLACE POLICY piag_mask_financial
ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing
COMMENT 'Mask unit cost and gross profit columns (tag piag_sensitivity = financial).'
COLUMN MASK serverless_stable_69fppe_catalog.piag_pricing.mask_financial
TO `account users`
FOR TABLES
MATCH COLUMNS has_tag_value('piag_sensitivity', 'financial') AS c
ON COLUMN c;

CREATE OR REPLACE POLICY piag_mask_pii
ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing
COMMENT 'Mask customer contact details (tag piag_sensitivity = pii).'
COLUMN MASK serverless_stable_69fppe_catalog.piag_pricing.mask_pii
TO `account users`
FOR TABLES
MATCH COLUMNS has_tag_value('piag_sensitivity', 'pii') AS c
ON COLUMN c;

CREATE OR REPLACE POLICY piag_filter_rooftop
ON SCHEMA serverless_stable_69fppe_catalog.piag_pricing
COMMENT 'Row-level security by dealership (tag piag_scope = rooftop).'
ROW FILTER serverless_stable_69fppe_catalog.piag_pricing.filter_rooftop
TO `account users`
FOR TABLES
MATCH COLUMNS has_tag_value('piag_scope', 'rooftop') AS r
USING COLUMNS (r);
