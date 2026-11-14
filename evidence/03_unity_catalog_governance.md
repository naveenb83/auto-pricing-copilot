# Evidence 03 — Unity Catalog governance (ABAC masks + row filter, tags, metric view, lineage)

Schema `serverless_stable_69fppe_catalog.piag_pricing`. Captured live from `information_schema`, `SHOW POLICIES` and `system.access.table_lineage`.

## ABAC policies attached to the schema (apply to every current and future tagged table)
```text
Policy Name         | Policy Type | on_securable_type | Comment                                                                    
--------------------+-------------+-------------------+----------------------------------------------------------------------------
piag_filter_rooftop | ROW_FILTER  | SCHEMA            | Row-level security by dealership (tag piag_scope = rooftop).               
piag_mask_financial | COLUMN_MASK | SCHEMA            | Mask unit cost and gross profit columns (tag piag_sensitivity = financial).
piag_mask_pii       | COLUMN_MASK | SCHEMA            | Mask customer contact details (tag piag_sensitivity = pii).                
```
Policy functions are a single group-membership check each — no lookup tables, so no per-column compile cost:
```text
comment                                                                                                                                 | routine_name  
----------------------------------------------------------------------------------------------------------------------------------------+---------------
ABAC row filter: group leadership sees every rooftop; rooftop staff see rows for rooftops whose piag_rooftop_<id> group they belong to. | filter_rooftop
ABAC column mask: unit cost / gross visible only to members of piag_margin_viewers, otherwise NULL.                                     | mask_financial
ABAC column mask: customer contact details visible only to piag_crm_admins; others see first character + ****.                          | mask_pii      
```
## Governed column tags that drive the policies
```text
column_name           | table_name               | tag_name            | tag_value
----------------------+--------------------------+---------------------+----------
vin                   | gold_inventory_current   | class.vin           |          
rooftop_id            | gold_rooftop_weekly_kpis | piag_scope          | rooftop  
fi_gross              | gold_sales_enriched      | piag_sensitivity    | financial
front_gross           | gold_sales_enriched      | piag_sensitivity    | financial
net_gross_after_carry | gold_sales_enriched      | piag_sensitivity    | financial
rooftop_id            | gold_sales_enriched      | piag_scope          | rooftop  
total_gross           | gold_sales_enriched      | piag_sensitivity    | financial
unit_cost             | gold_sales_enriched      | piag_sensitivity    | financial
fi_gross              | gold_vehicle_status      | piag_sensitivity    | financial
front_gross           | gold_vehicle_status      | piag_sensitivity    | financial
rooftop_id            | gold_vehicle_status      | piag_scope          | rooftop  
total_gross           | gold_vehicle_status      | piag_sensitivity    | financial
unit_cost             | gold_vehicle_status      | piag_sensitivity    | financial
vin                   | gold_vehicle_status      | class.vin           |          
email                 | silver_customers         | class.email_address |          
email                 | silver_customers         | piag_sensitivity    | pii      
first_name            | silver_customers         | class.name          |          
last_name             | silver_customers         | class.name          |          
last_name             | silver_customers         | piag_sensitivity    | pii      
phone                 | silver_customers         | class.phone_number  |          
phone                 | silver_customers         | piag_sensitivity    | pii      
unit_cost             | silver_vehicles          | piag_sensitivity    | financial
```
## Table tags
```text
table_name                   | tag_name          | tag_value        
-----------------------------+-------------------+------------------
gold_inventory_current       | piag_layer        | gold             
gold_inventory_current       | piag_owner        | pricing          
gold_inventory_current       | piag_serving      | lakebase_sync    
gold_pricing_features_weekly | piag_layer        | gold             
gold_pricing_features_weekly | piag_ml           | training_features
gold_pricing_features_weekly | piag_owner        | data_science     
gold_rooftop_weekly_kpis     | piag_layer        | gold             
gold_rooftop_weekly_kpis     | piag_owner        | group_leadership 
gold_sales_enriched          | piag_layer        | gold             
gold_sales_enriched          | piag_owner        | sales_finance    
gold_segment_response        | piag_layer        | gold             
gold_segment_response        | piag_owner        | marketing        
gold_vehicle_status          | piag_layer        | gold             
gold_vehicle_status          | piag_owner        | pricing          
silver_customers             | contains_pii      | true             
silver_customers             | layer             | silver           
silver_customers             | piag_contains_pii | true             
silver_customers             | piag_layer        | silver           
```
## Same queries, two identities (`governance/lens_check.sql`)
**Full lens** — member of piag_margin_viewers, piag_crm_admins, piag_group_leadership:
```text
[OK    1.5s] SELECT current_user() AS user_name, is_member('piag_margin_viewers') AS margin_viewer, is_member('piag_crm_admins') AS crm_admin, is_member('piag_grou  -> [['naveen.balachandran@databricks.com', 'true', 'true', 'true', 'false']]
[OK    0.8s] SELECT count(*) AS vehicle_rows_visible, count(DISTINCT rooftop_id) AS rooftops_visible, count(unit_cost) AS unit_cost_values_visible, round(avg(front  -> [['17862', '6', '17862', '1651.0']]
[OK    0.9s] SELECT rooftop_id, count(*) AS sales, round(sum(total_gross), 0) AS total_gross FROM gold_sales_enriched GROUP BY 1 ORDER BY 1  -> [['R01', '2712', '8438130.0'], ['R02', '2728', '8169886.0'], ['R03', '2676', '8160586.0']]
[OK    0.8s] SELECT customer_id, first_name, last_name, email, phone, segment FROM silver_customers ORDER BY customer_id LIMIT 3  -> [['C100000', 'Isabella', 'Sato', 'isabella.sato0@example.com', '(555) 494-2018', 'trades_and_fleet'], ['C100001', 'Noah', 'Santos', 'noah.santos1@example.com', '(555) 624-8138', 'young_family'], ['C100002', 'Elena', 'Young', 'elena.young2@example.com', '(555) 585-130
[OK    1.4s] SELECT `Rooftop`, MEASURE(`Units On Hand`) AS units_on_hand, MEASURE(`Aged 90+ Units`) AS aged_90_plus, round(MEASURE(`Aged 90+ Share`), 3) AS aged_90  -> [['Bayside Auto Centre', '216', '39', '0.181', '4809.0', '1942.0'], ['Eastgate Motors', '264', '62', '0.235', '6147.0', '1860.0'], ['Harbourview Motors', '194', '48', '0.247', '4298.0', '1920.0']]
```
**Rooftop lens** — removed from those groups, added to piag_rooftop_R03 only (`governance/lens_switch.sh`):
```text
[OK    1.4s] SELECT current_user() AS user_name, is_member('piag_margin_viewers') AS margin_viewer, is_member('piag_crm_admins') AS crm_admin, is_member('piag_grou  -> [['naveen.balachandran@databricks.com', 'false', 'false', 'false', 'true']]
[OK    1.2s] SELECT count(*) AS vehicle_rows_visible, count(DISTINCT rooftop_id) AS rooftops_visible, count(unit_cost) AS unit_cost_values_visible, round(avg(front  -> [['2940', '1', '0', None]]
[OK    1.1s] SELECT rooftop_id, count(*) AS sales, round(sum(total_gross), 0) AS total_gross FROM gold_sales_enriched GROUP BY 1 ORDER BY 1  -> [['R03', '2676', None]]
[OK    1.2s] SELECT customer_id, first_name, last_name, email, phone, segment FROM silver_customers ORDER BY customer_id LIMIT 3  -> [['C100000', 'Isabella', 'S****', 'i****', '(****', 'trades_and_fleet'], ['C100001', 'Noah', 'S****', 'n****', '(****', 'young_family'], ['C100002', 'Elena', 'Y****', 'e****', '(****', 'value_retiree']]
```
Result: 17,862 → 2,940 vehicle rows (R03 only), unit cost 17,862 → 0 visible, gross → NULL, customer surname/email/phone → masked; segment stays visible for marketing.

Governed KPI metric view `piag_pricing_kpis` under the rooftop lens (gross masked through the metric view):
```text
[OK    2.6s] SELECT `Rooftop`, MEASURE(`Units On Hand`) AS units_on_hand, MEASURE(`Aged 90+ Units`) AS aged_90_plus, round(MEASURE(`Aged 90+ Share`), 3) AS aged_90  -> [['Eastgate Motors', '264', '62', '0.235', '6147.0', None]]
```
## Table lineage recorded by Unity Catalog (bronze → silver → gold → metric view)
```text
source                    | target                      
--------------------------+-----------------------------
gold_vehicle_status       | gold_inventory_current      
silver_web_leads          | gold_inventory_current      
silver_market_comps       | gold_pricing_features_weekly
silver_price_changes      | gold_pricing_features_weekly
silver_sales              | gold_pricing_features_weekly
silver_vehicles           | gold_pricing_features_weekly
silver_web_leads          | gold_pricing_features_weekly
gold_vehicle_status       | gold_rooftop_weekly_kpis    
gold_vehicle_status       | gold_sales_enriched         
silver_customers          | gold_sales_enriched         
silver_campaign_responses | gold_segment_response       
silver_campaigns          | gold_segment_response       
silver_customers          | gold_segment_response       
ref_floorplan_rates       | gold_vehicle_status         
ref_rooftops              | gold_vehicle_status         
ref_vehicle_images        | gold_vehicle_status         
silver_market_comps       | gold_vehicle_status         
silver_price_changes      | gold_vehicle_status         
silver_sales              | gold_vehicle_status         
silver_vehicles           | gold_vehicle_status         
gold_vehicle_status       | piag_pricing_kpis           
bronze_campaign_responses | silver_campaign_responses   
bronze_campaigns          | silver_campaigns            
bronze_customers          | silver_customers            
bronze_market_comps       | silver_market_comps         
bronze_price_changes      | silver_price_changes        
bronze_sales              | silver_sales                
bronze_vehicles           | silver_vehicles             
bronze_web_leads          | silver_web_leads            
```
## Every table is self-describing (comments used by Genie and Catalog search)
```text
comment                                                                                                                                                                                                                             | table_name                                                                                | table_type       
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------+------------------
Bronze. Customer-level responses to each promotion. Raw, append-only, one row per delivered record (duplicates kept).                                                                                                               | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_campaign_responses_1    | MANAGED          
Bronze. Marketing promotions (offer amount by body class). Raw, append-only, one row per delivered record (duplicates kept).                                                                                                        | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_campaigns_1             | MANAGED          
Bronze. CRM customer records (synthetic PII). Raw, append-only, one row per delivered record (duplicates kept).                                                                                                                     | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_customers_1             | MANAGED          
Bronze. Weekly market pricing comps per vehicle from the pricing-tool feed. Raw, append-only, one row per delivered record (duplicates kept).                                                                                       | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_market_comps_1          | MANAGED          
Bronze. Every list-price change made by pricing managers. Raw, append-only, one row per delivered record (duplicates kept).                                                                                                         | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_price_changes_1         | MANAGED          
Bronze. Vehicle dispositions: retail deals, wholesale auction exits and dealer trades. Raw, append-only, one row per delivered record (duplicates kept).                                                                            | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_sales_1                 | MANAGED          
Bronze. Vehicle acquisitions (new factory allocations and used trade-ins/auction buys) from the DMS. Raw, append-only, one row per delivered record (duplicates kept).                                                              | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_vehicles_1              | MANAGED          
Bronze. Weekly website demand signals per vehicle (vehicle detail page views, leads, test drives). Raw, append-only, one row per delivered record (duplicates kept).                                                                | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_bronze_web_leads_1             | MANAGED          
Gold. Current on-hand inventory (one row per VIN) with aging, price-to-market, holding cost, last-week and 4-week web demand, and the flat-rule discount baseline. Source for Lakebase sync and the pricing model.                  | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_inventory_current_1       | MANAGED          
Gold / ML. Vehicle-week panel for the time-to-sell model: features known at the start of each week (age, price-to-market, discount to date, prior-week demand, market days supply) and label sold_retail_this_week.                 | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_pricing_features_weekly_1 | MANAGED          
Gold. Weekly KPIs per rooftop: units on hand at week end, aged 45+/90+ units and share, retail units sold, average front gross, and floor-plan + lot carrying cost burned that week.                                                | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_rooftop_weekly_kpis_1     | MANAGED          
Gold. Every vehicle disposition with vehicle attributes, buyer segment, days in stock, discount given and front/total gross. Use for sales, gross and aging-at-sale questions.                                                      | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_sales_enriched_1          | MANAGED          
Gold. Promotion response by customer segment x target body class x offer amount x channel: sends, open/click/lead/purchase rates. Answers 'which segments respond to which promotion'.                                              | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_segment_response_1        | MANAGED          
Gold. One row per vehicle: status (on_hand / retail / wholesale / dealer_trade), days in stock, current price, discount, price-to-market, daily holding cost and realised gross. Business date = pipeline as_of_date.               | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_gold_vehicle_status_1          | MANAGED          
Reference. Monthly floor-plan finance APR and lot cost per unit per day (drives holding cost).                                                                                                                                      | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_ref_floorplan_rates_1          | MANAGED          
Reference. Make/model catalogue with body class and base MSRP.                                                                                                                                                                      | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_ref_models_1                   | MANAGED          
Reference. Pacific Isles Auto Group rooftops (dealerships), franchises and lot capacity.                                                                                                                                            | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_ref_rooftops_1                 | MANAGED          
Reference. One openly licensed Wikimedia Commons photo per make/model, with author and licence for attribution.                                                                                                                     | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_ref_vehicle_images_1           | MANAGED          
Silver. One row per customer per promotion with open/click/lead/purchase outcomes.                                                                                                                                                  | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_campaign_responses_1    | MANAGED          
Silver. Promotions: target body class, offer amount and channel.                                                                                                                                                                    | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_campaigns_1             | MANAGED          
Silver. CRM customers with marketing segment. Contains PII (name, email, phone) — masked by Unity Catalog policy.                                                                                                                   | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_customers_1             | MANAGED          
Silver. Weekly market average price, comparable-listing count and market days supply per vehicle.                                                                                                                                   | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_market_comps_1          | MANAGED          
Silver. Deduplicated list-price changes with the reason (flat aged rule, manager discretion, market adjustment).                                                                                                                    | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_price_changes_1         | MANAGED          
Silver. One row per vehicle disposition (retail deal, wholesale auction exit or dealer trade).                                                                                                                                      | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_sales_1                 | MANAGED          
Silver. One row per vehicle (VIN) acquired by the group, deduplicated and validated.                                                                                                                                                | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_vehicles_1              | MANAGED          
Silver. Weekly website demand per vehicle: detail-page views, leads, test drives.                                                                                                                                                   | __materialization_mat_9cd13098_a413_48f6_bff8_eadf9c20b653_silver_web_leads_1             | MANAGED          
Digital-twin A/B: today's lot replayed 120 days under hidden ground-truth demand, flat $250/$500 rule vs model pricing, one row per policy x future.                                                                                | backtest_policy_results                                                                   | MANAGED          
Bronze. Customer-level responses to each promotion. Raw, append-only, one row per delivered record (duplicates kept).                                                                                                               | bronze_campaign_responses                                                                 | STREAMING_TABLE  
Bronze. Marketing promotions (offer amount by body class). Raw, append-only, one row per delivered record (duplicates kept).                                                                                                        | bronze_campaigns                                                                          | STREAMING_TABLE  
Bronze. CRM customer records (synthetic PII). Raw, append-only, one row per delivered record (duplicates kept).                                                                                                                     | bronze_customers                                                                          | STREAMING_TABLE  
Bronze. Weekly market pricing comps per vehicle from the pricing-tool feed. Raw, append-only, one row per delivered record (duplicates kept).                                                                                       | bronze_market_comps                                                                       | STREAMING_TABLE  
Bronze. Every list-price change made by pricing managers. Raw, append-only, one row per delivered record (duplicates kept).                                                                                                         | bronze_price_changes                                                                      | STREAMING_TABLE  
Bronze. Vehicle dispositions: retail deals, wholesale auction exits and dealer trades. Raw, append-only, one row per delivered record (duplicates kept).                                                                            | bronze_sales                                                                              | STREAMING_TABLE  
Bronze. Vehicle acquisitions (new factory allocations and used trade-ins/auction buys) from the DMS. Raw, append-only, one row per delivered record (duplicates kept).                                                              | bronze_vehicles                                                                           | STREAMING_TABLE  
Bronze. Weekly website demand signals per vehicle (vehicle detail page views, leads, test drives). Raw, append-only, one row per delivered record (duplicates kept).                                                                | bronze_web_leads                                                                          | STREAMING_TABLE  
                                                                                                                                                                                                                                    | event_log_9cd13098_a413_48f6_bff8_eadf9c20b653                                            | MANAGED          
Gold. Current on-hand inventory (one row per VIN) with aging, price-to-market, holding cost, last-week and 4-week web demand, and the flat-rule discount baseline. Source for Lakebase sync and the pricing model.                  | gold_inventory_current                                                                    | MATERIALIZED_VIEW
Gold / ML. Vehicle-week panel for the time-to-sell model: features known at the start of each week (age, price-to-market, discount to date, prior-week demand, market days supply) and label sold_retail_this_week.                 | gold_pricing_features_weekly                                                              | MATERIALIZED_VIEW
Gold. Weekly KPIs per rooftop: units on hand at week end, aged 45+/90+ units and share, retail units sold, average front gross, and floor-plan + lot carrying cost burned that week.                                                | gold_rooftop_weekly_kpis                                                                  | MATERIALIZED_VIEW
Gold. Every vehicle disposition with vehicle attributes, buyer segment, days in stock, discount given and front/total gross. Use for sales, gross and aging-at-sale questions.                                                      | gold_sales_enriched                                                                       | MATERIALIZED_VIEW
Gold. Promotion response by customer segment x target body class x offer amount x channel: sends, open/click/lead/purchase rates. Answers 'which segments respond to which promotion'.                                              | gold_segment_response                                                                     | MATERIALIZED_VIEW
Gold. One row per vehicle: status (on_hand / retail / wholesale / dealer_trade), days in stock, current price, discount, price-to-market, daily holding cost and realised gross. Business date = pipeline as_of_date.               | gold_vehicle_status                                                                       | MATERIALIZED_VIEW
Pacific Isles Auto Group aged-inventory and retail KPIs (business date 2026-11-13). One row per vehicle in the source.                                                                                                              | piag_pricing_kpis                                                                         | METRIC_VIEW      
Model-recommended additional discount per on-hand vehicle (batch score of @champion v2): expected days to sell, sell probability and expected profit now vs recommended vs the flat $250/$500 rule. Synced to Lakebase for the app. | pricing_recommendations                                                                   | MANAGED          
Reference. Monthly floor-plan finance APR and lot cost per unit per day (drives holding cost).                                                                                                                                      | ref_floorplan_rates                                                                       | MATERIALIZED_VIEW
Reference. Make/model catalogue with body class and base MSRP.                                                                                                                                                                      | ref_models                                                                                | MATERIALIZED_VIEW
Reference. Pacific Isles Auto Group rooftops (dealerships), franchises and lot capacity.                                                                                                                                            | ref_rooftops                                                                              | MATERIALIZED_VIEW
Reference. One openly licensed Wikimedia Commons photo per make/model, with author and licence for attribution.                                                                                                                     | ref_vehicle_images                                                                        | MATERIALIZED_VIEW
Silver. One row per customer per promotion with open/click/lead/purchase outcomes.                                                                                                                                                  | silver_campaign_responses                                                                 | MATERIALIZED_VIEW
Silver. Promotions: target body class, offer amount and channel.                                                                                                                                                                    | silver_campaigns                                                                          | MATERIALIZED_VIEW
Silver. CRM customers with marketing segment. Contains PII (name, email, phone) — masked by Unity Catalog policy.                                                                                                                   | silver_customers                                                                          | MATERIALIZED_VIEW
Silver. Weekly market average price, comparable-listing count and market days supply per vehicle.                                                                                                                                   | silver_market_comps                                                                       | MATERIALIZED_VIEW
Silver. Deduplicated list-price changes with the reason (flat aged rule, manager discretion, market adjustment).                                                                                                                    | silver_price_changes                                                                      | MATERIALIZED_VIEW
Silver. One row per vehicle disposition (retail deal, wholesale auction exit or dealer trade).                                                                                                                                      | silver_sales                                                                              | MATERIALIZED_VIEW
Silver. One row per vehicle (VIN) acquired by the group, deduplicated and validated.                                                                                                                                                | silver_vehicles                                                                           | MATERIALIZED_VIEW
Silver. Weekly website demand per vehicle: detail-page views, leads, test drives.                                                                                                                                                   | silver_web_leads                                                                          | MATERIALIZED_VIEW
```
## Grants note
UC `GRANT` requires account-level principals. This demo workspace's `piag_*` groups are workspace-local (creating account groups needs account admin), so `governance/04_grants_account_groups.sql` is the production grant set for SCIM-synced account groups; it returned `PRINCIPAL_DOES_NOT_EXIST` here and is documented, not applied. The app's service principal (account-level) is granted explicitly in the app PR.
