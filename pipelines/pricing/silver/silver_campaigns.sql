CREATE OR REFRESH MATERIALIZED VIEW silver_campaigns
COMMENT "Silver. Promotions: target body class, offer amount and channel."
TBLPROPERTIES ("quality" = "silver")
AS SELECT DISTINCT campaign_id, launch_date, target_body_class, offer_amount, channel, name FROM bronze_campaigns;

CREATE OR REFRESH MATERIALIZED VIEW silver_campaign_responses (
  CONSTRAINT funnel_order EXPECT (NOT purchased_within_30d OR lead_created)
)
COMMENT "Silver. One row per customer per promotion with open/click/lead/purchase outcomes."
TBLPROPERTIES ("quality" = "silver")
AS SELECT campaign_id, customer_id, sent_date, opened, clicked, lead_created, purchased_within_30d
FROM bronze_campaign_responses
QUALIFY row_number() OVER (PARTITION BY campaign_id, customer_id ORDER BY ingested_at) = 1;
