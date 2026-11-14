"""GenAI layer (AI Functions): for every aged unit (45+ days) write a plain-English pricing rationale and
ready-to-send promo copy for the customer segment most likely to respond — then CHECK every number the
LLM wrote against the model's facts (grounding), so no invented statistics reach a pricing manager.

Segment targeting is deterministic (campaign response data), not generated: the LLM only writes words.
Outputs: <schema>.segment_targeting, <schema>.pricing_rationale
"""

from __future__ import annotations

import argparse
import json
import re

LLM = "databricks-claude-haiku-5-5"

SEGMENT_SQL = """
CREATE OR REPLACE TABLE {fq}.segment_targeting
COMMENT 'Which customer segments respond best to promotions for each body class: leads per 1,000 sends, lift vs the body-class average and offer sensitivity (lead rate at offers >= $1,000 vs <= $500). Source: gold_segment_response.'
AS WITH s AS (
  SELECT target_body_class AS body_class, segment, sum(sends) AS sends, sum(leads) AS leads, sum(purchases) AS purchases,
         sum(CASE WHEN offer_amount >= 1000 THEN leads END) / sum(CASE WHEN offer_amount >= 1000 THEN sends END) AS hi_rate,
         sum(CASE WHEN offer_amount <= 500 THEN leads END) / sum(CASE WHEN offer_amount <= 500 THEN sends END) AS lo_rate
  FROM {fq}.gold_segment_response GROUP BY 1, 2),
b AS (SELECT body_class, sum(leads) / sum(sends) AS avg_rate FROM s GROUP BY 1)
SELECT s.body_class, s.segment, s.sends, s.leads, s.purchases,
       round(1000 * s.leads / s.sends, 2) AS leads_per_1000_sends,
       round((s.leads / s.sends) / b.avg_rate, 2) AS lift_vs_body_class_avg,
       round(s.hi_rate / nullif(s.lo_rate, 0), 2) AS offer_sensitivity,
       rank() OVER (PARTITION BY s.body_class ORDER BY s.leads / s.sends DESC) AS segment_rank
FROM s JOIN b USING (body_class)
"""

FACTS_SQL = """
CREATE OR REPLACE TEMP VIEW rationale_input AS
WITH seg AS (
  SELECT body_class,
         max_by(segment, -segment_rank) AS top_segment,
         max(CASE WHEN segment_rank = 1 THEN lift_vs_body_class_avg END) AS top_segment_lift,
         max(CASE WHEN segment_rank = 2 THEN segment END) AS second_segment
  FROM {fq}.segment_targeting GROUP BY body_class)
SELECT r.vin, r.stock_number, r.rooftop_name, r.make, r.model, r.model_year, i.trim, i.condition, i.body_class,
       r.days_in_stock, round(r.price_to_market, 3) AS price_to_market, round(r.daily_holding_cost, 0) AS holding_cost_per_day,
       r.current_price, r.recommended_discount, r.recommended_price,
       round(r.expected_days_to_sell_now, 0) AS expected_days_now,
       round(r.expected_days_to_sell_recommended, 0) AS expected_days_after,
       r.uplift_vs_flat_rule AS profit_vs_flat_rule, r.flat_rule_discount, r.guardrail_applied,
       seg.top_segment, seg.second_segment, seg.top_segment_lift,
       -- counterfactual from the model's profit curve: what a $500 cut would do (explains "hold" decisions)
       round(element_at(filter(from_json(r.curve_json, 'array<struct<discount:double,expected_days_to_sell:double,expected_profit:double>>'),
                               c -> c.discount = 500), 1).expected_days_to_sell, 0) AS days_if_500_cut,
       round(element_at(filter(from_json(r.curve_json, 'array<struct<discount:double,expected_days_to_sell:double,expected_profit:double>>'),
                               c -> c.discount = 500), 1).expected_profit - r.expected_profit_now, 0) AS profit_change_if_500_cut,
       r.recommended_discount = 0 AND element_at(filter(from_json(r.curve_json,
            'array<struct<discount:double,expected_profit:double>>'), c -> c.discount = 500), 1).expected_profit
            > r.expected_profit_now AS cut_blocked_by_margin_floor
FROM {fq}.pricing_recommendations r
JOIN {fq}.gold_inventory_current i USING (vin)
LEFT JOIN seg ON seg.body_class = i.body_class
WHERE r.days_in_stock >= 45
"""

PROMPT = """You write for a car dealership pricing manager. Return ONLY a JSON object (no markdown) with keys
rationale, promo_headline, promo_message.
- rationale: 2 sentences, plain English, explaining the recommendation using ONLY numbers from FACTS
  (you may round them). If recommended_discount is 0, explain that a cut is not expected to pay for itself
  (the faster sale would not cover the discount) — use days_if_500_cut and profit_change_if_500_cut to show the
  trade-off; never claim a discount would not speed up the sale. If cut_blocked_by_margin_floor is true, say a cut
  would help a little but would take the deal below the group's minimum-margin floor, so the unit needs another
  exit plan (e.g. dealer trade or wholesale review).
  If guardrail_applied is true, mention the cut is capped by pricing policy.
- promo_headline: max 7 words for the vehicle, aimed at the top_segment.
- promo_message: max 30-word SMS to the top_segment customer segment. The only number allowed is the
  recommended_discount (or none if it is 0). Never invent finance rates, mileage or dates.
FACTS: """


def numbers(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")]


def grounded(text: str, facts: dict) -> tuple[bool, list[float]]:
    # vehicle names carry digits that are not statistics (CX-90, Ioniq 5, F-150, Mazda3)
    for name in sorted({str(facts.get(k) or "") for k in ("make", "model", "trim")}, key=len, reverse=True):
        if name:
            text = text.replace(name, " ")
    allowed = set()
    vals = [v for v in facts.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for v in vals:
        for x in (v, abs(v), round(v), round(v, 1), round(v, 2), round(v * 100), round(v * 100, 1),
                  round((v - 1) * 100), round((v - 1) * 100, 1), round(v / 7), round(v / 1000, 1), round(v / 30)):
            allowed.add(float(x))
    for a in vals:
        for b in vals:
            allowed.add(float(round(abs(a - b))))
    allowed |= {float(facts.get("model_year") or 0), 500.0}  # 500 = the counterfactual cut we supply
    bad = [n for n in numbers(text) if n > 3 and not any(abs(n - a) <= max(1.0, 0.01 * a) for a in allowed)]
    return (not bad), bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    a, _ = ap.parse_known_args()
    fq = f"{a.catalog}.{a.schema}"
    from pyspark.sql import SparkSession, functions as F
    spark = SparkSession.builder.getOrCreate()

    spark.sql(SEGMENT_SQL.format(fq=fq))
    print("== Segment targeting: top 2 responsive segments per body class")
    print(spark.sql(f"SELECT body_class, segment_rank, segment, sends, leads_per_1000_sends, lift_vs_body_class_avg, "
                    f"offer_sensitivity FROM {fq}.segment_targeting WHERE segment_rank <= 2 ORDER BY 1, 2").toPandas().to_string(index=False))

    spark.sql(FACTS_SQL.format(fq=fq))
    facts_cols = ["make", "model", "model_year", "trim", "condition", "days_in_stock", "price_to_market",
                  "holding_cost_per_day", "current_price", "recommended_discount", "recommended_price",
                  "expected_days_now", "expected_days_after", "profit_vs_flat_rule", "flat_rule_discount",
                  "guardrail_applied", "top_segment", "second_segment", "days_if_500_cut", "profit_change_if_500_cut",
                  "cut_blocked_by_margin_floor"]
    gen = spark.sql(f"""
        SELECT *, ai_query('{LLM}', concat('{PROMPT.replace("'", "''")}', to_json(named_struct({', '.join(f"'{c}', {c}" for c in facts_cols)}))),
                           modelParameters => named_struct('max_tokens', 2500), failOnError => false) AS llm
        FROM rationale_input""")
    pdf = gen.toPandas()
    rows, parse_fail = [], 0
    for r in pdf.to_dict("records"):
        resp = r["llm"] or {}
        raw = resp.get("result") if isinstance(resp, dict) else getattr(resp, "result", None)
        err = resp.get("errorMessage") if isinstance(resp, dict) else getattr(resp, "errorMessage", None)
        try:
            j = json.loads(re.sub(r"^```(json)?|```$", "", (raw or "").strip()).strip())
        except Exception:
            j, parse_fail = {}, parse_fail + 1
        facts = {c: r[c] for c in facts_cols}
        text = f"{j.get('rationale', '')} {j.get('promo_message', '')} {j.get('promo_headline', '')}"
        ok, bad = grounded(text, facts) if j else (False, [])
        rows.append({"vin": r["vin"], "stock_number": r["stock_number"], "rationale": j.get("rationale"),
                     "promo_headline": j.get("promo_headline"), "promo_message": j.get("promo_message"),
                     "top_segment": r["top_segment"], "second_segment": r["second_segment"],
                     "top_segment_lift": float(r["top_segment_lift"] or 0), "grounded": bool(ok),
                     "unmatched_numbers": json.dumps(bad), "llm_error": err, "llm_model": LLM})
    import pandas as pd
    out = pd.DataFrame(rows)
    (spark.createDataFrame(out).withColumn("generated_at", F.current_timestamp())
        .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.pricing_rationale"))
    spark.sql(f"COMMENT ON TABLE {fq}.pricing_rationale IS 'LLM-written ({LLM}, AI Functions ai_query) pricing rationale "
              f"and segment promo copy per aged unit, with an automatic grounding check: grounded = every number in the "
              f"text traces to the model facts.'")
    n = len(out)
    g = int(out["grounded"].sum())
    print(f"== Generated {n} rationales with {LLM}: parse failures {parse_fail}, grounded {g}/{n} ({100 * g / max(n, 1):.1f}%)")
    print("== 5 examples")
    for r in out[out["grounded"]].head(5).to_dict("records"):
        print(f"- {r['stock_number']} | target {r['top_segment']} (then {r['second_segment']})\n"
              f"  WHY: {r['rationale']}\n  PROMO: {r['promo_headline']} — {r['promo_message']}")
    ug = out[~out["grounded"]].head(5)
    if len(ug):
        print("== Ungrounded examples (flagged, hidden from the app's rationale panel)")
        for r in ug.to_dict("records"):
            print(f"- {r['stock_number']} unmatched={r['unmatched_numbers']} :: {r['rationale']}")
    print("== SUMMARY " + json.dumps({"rationales": n, "parse_failures": parse_fail, "grounded": g,
                                      "grounded_pct": round(100 * g / max(n, 1), 1), "llm": LLM}))


if __name__ == "__main__":
    main()
