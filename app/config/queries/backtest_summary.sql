-- Digital-twin A/B (today's lot replayed 120 days, 20 paired futures)
SELECT policy,
       avg(net_profit) AS net_profit,
       avg(aged90_day60) AS aged90_day60,
       avg(carrying_cost) AS carrying_cost,
       avg(wholesale_exits) AS wholesale_exits,
       avg(retail_units) AS retail_units,
       count(*) AS futures
FROM serverless_stable_69fppe_catalog.piag_pricing.backtest_policy_results
GROUP BY policy
ORDER BY CASE policy WHEN 'flat_rule' THEN 0 WHEN 'model_guardrails' THEN 1 ELSE 2 END
