USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;
SELECT `Rooftop`, MEASURE(`Units On Hand`) AS units_on_hand, MEASURE(`Aged 90+ Units`) AS aged_90_plus, round(MEASURE(`Aged 90+ Share`), 3) AS aged_90_share, round(MEASURE(`Holding Cost Per Day`), 0) AS holding_cost_per_day, round(MEASURE(`Avg Front Gross`), 0) AS avg_front_gross FROM piag_pricing_kpis GROUP BY ALL ORDER BY 1;
