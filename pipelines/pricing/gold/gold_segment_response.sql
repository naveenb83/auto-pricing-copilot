CREATE OR REFRESH MATERIALIZED VIEW gold_segment_response
COMMENT "Gold. Promotion response by customer segment x target body class x offer amount x channel: sends, open/click/lead/purchase rates. Answers 'which segments respond to which promotion'."
TBLPROPERTIES ("quality" = "gold")
AS SELECT cu.segment, ca.target_body_class, ca.offer_amount, ca.channel,
          count(*) AS sends, sum(CAST(r.opened AS INT)) AS opens, sum(CAST(r.clicked AS INT)) AS clicks,
          sum(CAST(r.lead_created AS INT)) AS leads, sum(CAST(r.purchased_within_30d AS INT)) AS purchases,
          round(avg(CAST(r.opened AS INT)), 4) AS open_rate,
          round(avg(CAST(r.clicked AS INT)), 4) AS click_rate,
          round(avg(CAST(r.lead_created AS INT)), 4) AS lead_rate,
          round(avg(CAST(r.purchased_within_30d AS INT)) * 1000, 2) AS purchases_per_1000_sends
FROM silver_campaign_responses r
JOIN silver_customers cu ON cu.customer_id = r.customer_id
JOIN silver_campaigns ca ON ca.campaign_id = r.campaign_id
GROUP BY ALL;
