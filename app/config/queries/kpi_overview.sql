-- Governed KPIs from the Unity Catalog metric view (business date 2026-11-13)
SELECT MEASURE(`Units On Hand`) AS units_on_hand,
       MEASURE(`Aged 90+ Units`) AS aged_90_plus,
       MEASURE(`Aged 45+ Units`) AS aged_45_plus,
       MEASURE(`Aged 90+ Share`) AS aged_90_share,
       MEASURE(`Holding Cost Per Day`) AS holding_cost_per_day,
       MEASURE(`Holding Cost Per Day Aged 90+`) AS aged_holding_cost_per_day,
       MEASURE(`Avg Days In Stock`) AS avg_days_in_stock
FROM serverless_stable_69fppe_catalog.piag_pricing.piag_pricing_kpis
