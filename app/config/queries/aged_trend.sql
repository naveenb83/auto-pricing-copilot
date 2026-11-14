-- Group-wide weekly share of stock aged 90+ days and weekly carrying cost (last 26 weeks)
SELECT week_end AS week,
       round(100 * sum(units_aged_90_plus) / nullif(sum(units_on_hand), 0), 1) AS `% aged 90+`,
       sum(carrying_cost_week) AS carrying_cost_week
FROM serverless_stable_69fppe_catalog.piag_pricing.gold_rooftop_weekly_kpis
WHERE week_end > DATE'2026-11-13' - INTERVAL 182 DAYS
GROUP BY week_end
ORDER BY week
