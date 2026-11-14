"""Build the Genie Agent definition (serialized_space v2) for the pricing copilot — deterministic ids so
re-running produces the same payload (diff-able, CI-friendly).

    uv run python genie/build_space.py > genie/space.json
"""

from __future__ import annotations

import hashlib
import json

FQ = "serverless_stable_69fppe_catalog.piag_pricing"


def hid(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


TABLES = {
    "gold_inventory_current": {
        "aging_bucket": (["Days-in-stock band: 0-29, 30-44, 45-59, 60-89, 90+"], ["age band"]),
        "daily_holding_cost": (["USD per day to carry this unit: floor-plan interest + lot cost + market depreciation"],
                               ["carrying cost", "holding cost", "daily burn"]),
        "price_to_market": (["Current list price divided by market average price (1.05 = 5% above market)"], ["price position"]),
        "rooftop_name": (["Dealership name"], ["store", "dealership", "location"]),
    },
    "pricing_recommendations": {
        "recommended_discount": (["Model/DS recommended ADDITIONAL discount in USD (0 = hold price)"], ["model value", "recommended cut"]),
        "flat_rule_discount": (["Additional discount the old flat $250 (45+ days) / $500 (90+ days) rule would give"], ["flat rule", "old rule"]),
        "uplift_vs_flat_rule": (["Expected profit of the model recommendation minus expected profit of the flat rule, USD"], ["uplift"]),
        "expected_days_to_sell_recommended": (["Expected days to sell if the recommended discount is applied"], []),
        "expected_days_to_sell_now": (["Expected days to sell at today's price"], []),
    },
    "pricing_rationale": {"top_segment": (["Customer segment most likely to respond to a promotion for this vehicle"], ["target segment"])},
    "pricing_decisions": {
        "model_value": (["Model/DS recommended discount at decision time, USD"], ["model value", "DS value"]),
        "override_value": (["Pricing manager's discount when they overrode the model, USD"], ["override value"]),
        "reason_code": (["Why the model was overridden"], ["override reason"]),
        "decision": (["accepted | overridden | held"], []),
    },
    "gold_sales_enriched": {
        "front_gross": (["Sale price minus unit cost (masked unless the user is a margin viewer)"], ["gross", "PVR", "front-end gross"]),
        "customer_segment": (["Buyer marketing segment"], ["segment"]),
    },
    "gold_vehicle_status": {},
    "gold_rooftop_weekly_kpis": {},
    "segment_targeting": {"leads_per_1000_sends": (["Leads created per 1,000 promotion sends"], ["response rate"])},
    "backtest_policy_results": {"policy": (["flat_rule | model_guardrails | model_unconstrained"], [])},
}

TEXT = [
    "Business: Pacific Isles Auto Group (fictional, synthetic data), 6 rooftops (dealerships), new + used vehicles.",
    "The business date is 2026-11-13 (as_of_date). 'Today', 'now', 'current' mean as of 2026-11-13, not current_date().",
    "Aged inventory = on-hand units with days_in_stock >= 90. 'Aging' units = 45+ days. Use gold_inventory_current for anything about today's lot.",
    "Holding / carrying cost per day = daily_holding_cost (floor-plan interest + $6 lot cost + market depreciation). Monthly cost = daily x 30.",
    "Model/DS value = pricing_recommendations.recommended_discount (additional cut on top of the current price). The old policy is the flat rule: $250 at 45+ days, $500 at 90+ days (flat_rule_discount).",
    "Pricing decisions made by managers in the app are in pricing_decisions (one row per decision): decision = accepted / overridden / held; override_value + reason_code when overridden.",
    "Customer segment responsiveness to promotions: use segment_targeting (segment_rank 1 = best) or gold_segment_response for offer-level detail.",
    "Backtest (digital twin, 120 days, 20 paired futures): backtest_policy_results; compare policies on avg(net_profit) and avg(aged90_day60).",
    "Gross profit and unit cost columns are masked (NULL) for users who are not margin viewers — if they come back NULL, say the user lacks access rather than reporting zero.",
    "Date windows: 'last N days' means date > DATE'2026-11-13' - INTERVAL N DAYS AND date <= DATE'2026-11-13' (inclusive of the business date).",
    "Sales, wholesale auction exits and dealer trades: use gold_sales_enriched (channel = retail | wholesale | dealer_trade, sale_date, sale_month).",
    "Always show money in USD rounded to whole dollars and percentages to one decimal place.",
]

SAMPLES = [
    "How many units are aged 90+ days at each rooftop and what do they cost us per day?",
    "Which aged units does the model recommend cutting by $1,500 or more?",
    "How much more profit does the model expect than the flat rule, by rooftop?",
    "Which customer segments respond best to pickup promotions?",
    "How often are pricing managers overriding the model, and why?",
    "What was the average days to sell and front gross for retail sales by month?",
]

EXAMPLES = [
    ("Aged units and daily holding cost by rooftop",
     f"SELECT rooftop_name, count(*) AS units_on_hand, count_if(days_in_stock >= 90) AS aged_90_plus, "
     f"round(100 * count_if(days_in_stock >= 90) / count(*), 1) AS pct_aged_90_plus, "
     f"round(sum(CASE WHEN days_in_stock >= 90 THEN daily_holding_cost END), 0) AS aged_holding_cost_per_day "
     f"FROM {FQ}.gold_inventory_current GROUP BY rooftop_name ORDER BY aged_90_plus DESC"),
    ("Model recommendation vs flat rule for aged units",
     f"SELECT r.stock_number, r.make, r.model, r.model_year, r.days_in_stock, r.current_price, "
     f"r.recommended_discount, r.flat_rule_discount, r.expected_days_to_sell_now, r.expected_days_to_sell_recommended, "
     f"r.uplift_vs_flat_rule FROM {FQ}.pricing_recommendations r WHERE r.days_in_stock >= 90 ORDER BY r.uplift_vs_flat_rule DESC LIMIT 20"),
    ("Override rate and reasons",
     f"SELECT reason_code, count(*) AS decisions, round(avg(override_delta), 0) AS avg_override_delta_usd "
     f"FROM {FQ}.pricing_decisions WHERE decision = 'overridden' GROUP BY reason_code ORDER BY decisions DESC"),
    ("Best responding segments for a body class",
     f"SELECT segment, leads_per_1000_sends, lift_vs_body_class_avg, offer_sensitivity FROM {FQ}.segment_targeting "
     f"WHERE body_class = 'pickup' ORDER BY segment_rank"),
]

BENCH = [
    ("How many vehicles are on hand today?", f"SELECT count(*) AS units_on_hand FROM {FQ}.gold_inventory_current"),
    ("How many on-hand units are 90 or more days old?", f"SELECT count(*) FROM {FQ}.gold_inventory_current WHERE days_in_stock >= 90"),
    ("Which rooftop has the highest share of units aged 90+ days?",
     f"SELECT rooftop_name, round(100 * count_if(days_in_stock >= 90) / count(*), 1) AS pct FROM {FQ}.gold_inventory_current GROUP BY 1 ORDER BY 2 DESC LIMIT 1"),
    ("What is the total daily holding cost of all on-hand inventory?",
     f"SELECT round(sum(daily_holding_cost), 0) FROM {FQ}.gold_inventory_current"),
    ("How many on-hand units does the model recommend holding price on?",
     f"SELECT count(*) FROM {FQ}.pricing_recommendations WHERE recommended_discount = 0"),
    ("What is the total expected profit uplift of the model over the flat rule across today's lot?",
     f"SELECT round(sum(uplift_vs_flat_rule), 0) FROM {FQ}.pricing_recommendations"),
    ("In the backtest, what was the average net profit for each policy?",
     f"SELECT policy, round(avg(net_profit), 0) AS avg_net_profit FROM {FQ}.backtest_policy_results GROUP BY policy ORDER BY 2 DESC"),
    ("Which segment is the best target for minivan promotions?",
     f"SELECT segment FROM {FQ}.segment_targeting WHERE body_class = 'minivan' AND segment_rank = 1"),
    ("How many retail units were sold in October 2026?",
     f"SELECT count(*) FROM {FQ}.gold_sales_enriched WHERE channel = 'retail' AND sale_month = DATE'2026-10-01'"),
    ("What is the average days in stock of on-hand used vehicles?",
     f"SELECT round(avg(days_in_stock), 1) FROM {FQ}.gold_inventory_current WHERE condition = 'used'"),
    ("How many units were wholesaled at auction in the last 90 days before the business date?",
     f"SELECT count(*) FROM {FQ}.gold_sales_enriched WHERE channel = 'wholesale' AND sale_date > DATE'2026-11-13' - INTERVAL 90 DAYS"),
    ("Which make has the most aged 90+ day units on hand?",
     f"SELECT make, count(*) FROM {FQ}.gold_inventory_current WHERE days_in_stock >= 90 GROUP BY make ORDER BY 2 DESC LIMIT 1"),
]


def build() -> dict:
    tables = []
    for t, cols in sorted(TABLES.items(), key=lambda kv: f"{FQ}.{kv[0]}"):
        cc = [{"column_name": c, "description": d, **({"synonyms": s} if s else {})} for c, (d, s) in sorted(cols.items())]
        tables.append({"identifier": f"{FQ}.{t}", **({"column_configs": cc} if cc else {})})
    return {
        "version": 2,
        "config": {"sample_questions": sorted([{"id": hid("s" + q), "question": [q]} for q in SAMPLES], key=lambda x: x["id"])},
        "data_sources": {"tables": tables, "metric_views": [{"identifier": f"{FQ}.piag_pricing_kpis"}]},
        "instructions": {
            "text_instructions": [{"id": hid("text-instructions"), "content": [line + "\n" for line in TEXT]}],
            "example_question_sqls": sorted([{"id": hid("e" + q), "question": [q], "sql": [s]} for q, s in EXAMPLES],
                                            key=lambda x: x["id"]),
        },
        "benchmarks": {"questions": sorted([{"id": hid("b" + q), "question": [q], "answer": [{"format": "SQL", "content": [s]}]}
                                            for q, s in BENCH], key=lambda x: x["id"])},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
