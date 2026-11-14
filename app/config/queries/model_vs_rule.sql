-- Today's batch recommendations vs the flat $250/$500 rule
SELECT count(*) AS vehicles_scored,
       count_if(recommended_discount > 0) AS recommend_cut,
       count_if(recommended_discount = 0) AS recommend_hold,
       count_if(guardrail_applied) AS guardrail_applied,
       sum(uplift_vs_flat_rule) AS expected_uplift_vs_rule,
       max(model_version) AS model_version,
       max(scored_at) AS scored_at
FROM serverless_stable_69fppe_catalog.piag_pricing.pricing_recommendations
