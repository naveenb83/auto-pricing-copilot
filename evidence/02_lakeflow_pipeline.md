# Evidence 02 — Lakeflow Declarative Pipeline (bronze → silver → gold) executed on serverless

Pipeline `piag-pricing-lakeflow` (id `9cd13098-a413-48f6-bff8-eadf9c20b653`), serverless + Photon, target `serverless_stable_69fppe_catalog.piag_pricing`.
All tables below are queried from the pipeline **event log** (`event_log()` TVF) and the published gold tables.

## Pipeline updates (incremental ingestion proof)
Update 1 = initial backfill of 78 weekly drops; update 2 = code change, **no new files → 0 bronze rows**; update 3 = after `piag-release-final-drop` delivered the 2026-11-13 drop → **only the new files ingested**; update 4 = silver rule change (sale-price expectation switched from drop to warn).
```text
bronze_rows_ingested | ended                    | started                  | update_id                            | final_state
---------------------+--------------------------+--------------------------+--------------------------------------+------------
377835               | 2026-11-14T13:04:40.661Z | 2026-11-14T13:04:11.398Z | d12a23c5-1953-4b1b-9db1-366382e99e3d | COMPLETED  
0                    | 2026-11-14T13:07:00.753Z | 2026-11-14T13:06:12.951Z | 683e337c-673b-4717-8fd1-540250e8c1fb | COMPLETED  
3733                 | 2026-11-14T13:09:13.084Z | 2026-11-14T13:08:09.538Z | 0f4eb445-9266-4a54-a2d8-0e228a144c62 | COMPLETED  
0                    | 2026-11-14T13:11:06.557Z | 2026-11-14T13:10:16.087Z | 68b0fd1c-8915-4e1b-b174-d317431d24c3 | COMPLETED  
```

## Bronze rows ingested by update 3 (final weekly drop only)
```text
bronze_table              | rows_ingested
--------------------------+--------------
bronze_campaign_responses |              
bronze_campaigns          |              
bronze_customers          |              
bronze_market_comps       |              
bronze_price_changes      |              
bronze_sales              |              
bronze_vehicles           |              
bronze_web_leads          |              
```

## Output rows per dataset
```text
dataset                      | kind                              | output_rows
-----------------------------+-----------------------------------+------------
bronze_campaign_responses    | streaming table (cumulative)      | 57666      
bronze_campaigns             | streaming table (cumulative)      | 48         
bronze_customers             | streaming table (cumulative)      | 25000      
bronze_market_comps          | streaming table (cumulative)      | 125604     
bronze_price_changes         | streaming table (cumulative)      | 13122      
bronze_sales                 | streaming table (cumulative)      | 16536      
bronze_vehicles              | streaming table (cumulative)      | 17988      
bronze_web_leads             | streaming table (cumulative)      | 125604     
gold_inventory_current       | materialized view (latest update) | 1411       
gold_pricing_features_weekly | materialized view (latest update) | 125036     
gold_rooftop_weekly_kpis     | materialized view (latest update) | 468        
gold_sales_enriched          | materialized view (latest update) | 16451      
gold_segment_response        | materialized view (latest update) | 185        
gold_vehicle_status          | materialized view (latest update) | 17862      
ref_floorplan_rates          | materialized view (latest update) | 19         
ref_models                   | materialized view (latest update) | 43         
ref_rooftops                 | materialized view (latest update) | 6          
ref_vehicle_images           | materialized view (latest update) | 43         
silver_campaign_responses    | materialized view (latest update) | 57666      
silver_campaigns             | materialized view (latest update) | 48         
silver_customers             | materialized view (latest update) | 25000      
silver_market_comps          | materialized view (latest update) | 125604     
silver_price_changes         | materialized view (latest update) | 13083      
silver_sales                 | materialized view (latest update) | 16503      
silver_vehicles              | materialized view (latest update) | 17862      
silver_web_leads             | materialized view (latest update) | 125353     
```

## Data-quality expectations (latest update)
`ON VIOLATION DROP ROW` rules remove unusable rows; warn-only rules keep the row and record the failure.
```text
dataset                   | expectation           | failed | passed
--------------------------+-----------------------+--------+-------
silver_campaign_responses | funnel_order          | 0      | 57666 
silver_customers          | customer_id_present   | 0      | 25000 
silver_customers          | segment_known         | 0      | 25000 
silver_market_comps       | market_price_positive | 0      | 125604
silver_price_changes      | price_decreases       | 0      | 13083 
silver_sales              | channel_known         | 0      | 16503 
silver_sales              | deal_id_present       | 0      | 16503 
silver_sales              | sale_price_valid      | 33     | 16470 
silver_vehicles           | mileage_valid         | 18     | 17898 
silver_vehicles           | price_above_cost      | 37     | 17879 
silver_vehicles           | unit_cost_present     | 36     | 17880 
silver_vehicles           | vin_present           | 0      | 17916 
silver_web_leads          | funnel_consistent     | 0      | 125430
silver_web_leads          | vin_present           | 77     | 125353
```

## Reconciliation: gold inventory vs simulator ground truth
Simulator (`_generation_summary.json`): on hand **1413**, aged 45+ **592**, aged 90+ **279**.
Gold (`gold_inventory_current`) — difference = vehicles correctly rejected by `unit_cost_present` / `mileage_valid`:
```text
aged_45_plus | aged_90_plus | avg_days_in_stock | group_holding_cost_per_day | on_hand
-------------+--------------+-------------------+----------------------------+--------
592          | 279          | 53.6              | 31429.0                    | 1411   
```

## Aged inventory by rooftop (as of 2026-11-13)
```text
aged_90_plus | holding_cost_per_day | on_hand | pct_90_plus | rooftop_name                     
-------------+----------------------+---------+-------------+----------------------------------
39           | 4809.0               | 216     | 18.1        | Bayside Auto Centre              
62           | 6147.0               | 264     | 23.5        | Eastgate Motors                  
48           | 4298.0               | 194     | 24.7        | Harbourview Motors               
48           | 4715.0               | 220     | 21.8        | Northshore Auto                  
33           | 4927.0               | 266     | 12.4        | Pacific Isles Certified Pre-Owned
49           | 6532.0               | 251     | 19.5        | Ridgeline Ford Chevrolet         
```

## ML training panel `gold_pricing_features_weekly`
```text
first_week | last_week  | retail_sales | vehicle_weeks | vehicles | weekly_sale_rate
-----------+------------+--------------+---------------+----------+-----------------
2025-05-12 | 2026-11-09 | 15768        | 125036        | 17860    | 0.1261          
```
