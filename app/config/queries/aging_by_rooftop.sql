-- On-hand units per rooftop by days-in-stock band (stacked bar)
SELECT rooftop_name AS rooftop,
       count_if(aging_bucket = '0-29') AS `0-29 days`,
       count_if(aging_bucket = '30-44') AS `30-44 days`,
       count_if(aging_bucket = '45-59') AS `45-59 days`,
       count_if(aging_bucket = '60-89') AS `60-89 days`,
       count_if(aging_bucket = '90+') AS `90+ days`
FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current
GROUP BY rooftop_name
ORDER BY `90+ days` DESC
