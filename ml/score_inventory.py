"""Batch-score today's lot with the @champion pricing model -> <schema>.pricing_recommendations (Delta, CDF on).

The same pyfunc is served in real time; batch scores seed the app's pricing queue and Genie questions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())

import mlflow  # noqa: E402

from pyfunc_model import INPUT_COLUMNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    a, _ = ap.parse_known_args()
    fq = f"{a.catalog}.{a.schema}"
    from pyspark.sql import SparkSession, functions as F
    spark = SparkSession.builder.getOrCreate()
    mlflow.set_registry_uri("databricks-uc")
    uri = f"models:/{fq}.aged_inventory_pricing_model@champion"
    model = mlflow.pyfunc.load_model(uri)
    version = mlflow.MlflowClient(registry_uri="databricks-uc").get_model_version_by_alias(
        f"{fq}.aged_inventory_pricing_model", "champion").version

    inv = spark.table(f"{fq}.gold_inventory_current").toPandas()
    inv["as_of_date"] = inv["as_of_date"].astype(str)
    X = inv[INPUT_COLUMNS].copy()
    X["price_override"] = float("nan")
    preds = model.predict(X)
    preds["model_version"] = str(version)
    out = inv[["vin", "stock_number", "rooftop_id", "rooftop_name", "condition", "make", "model", "trim",
               "model_year", "days_in_stock", "aging_bucket", "current_price", "market_price", "price_to_market",
               "daily_holding_cost", "unit_cost"]].merge(preds, on="vin")
    out["recommended_action"] = out.apply(
        lambda r: "hold price" if r.recommended_discount == 0 else f"cut ${int(r.recommended_discount):,}", axis=1)
    sdf = spark.createDataFrame(out).withColumn("scored_at", F.current_timestamp())
    (sdf.write.mode("overwrite").option("overwriteSchema", "true")
        .option("delta.enableChangeDataFeed", "true").saveAsTable(f"{fq}.pricing_recommendations"))
    spark.sql(f"ALTER TABLE {fq}.pricing_recommendations SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    spark.sql(f"COMMENT ON TABLE {fq}.pricing_recommendations IS 'Model-recommended additional discount per on-hand "
              f"vehicle (batch score of @champion v{version}): expected days to sell, sell probability and expected "
              f"profit now vs recommended vs the flat $250/$500 rule. Synced to Lakebase for the app.'")

    aged = out[out.days_in_stock >= 45]
    summary = {
        "model_version": str(version), "vehicles_scored": int(len(out)),
        "recommend_hold_price": int((out.recommended_discount == 0).sum()),
        "recommend_cut": int((out.recommended_discount > 0).sum()),
        "guardrail_applied": int(out.guardrail_applied.sum()),
        "aged45_units": int(len(aged)),
        "aged45_model_total_discount": float(aged.recommended_discount.sum()),
        "aged45_flat_rule_total_discount": float(aged.flat_rule_discount.sum()),
        "expected_profit_uplift_vs_flat_rule_total": float(out.uplift_vs_flat_rule.sum()),
        "mean_expected_days_now": round(float(out.expected_days_to_sell_now.mean()), 1),
        "mean_expected_days_recommended": round(float(out.expected_days_to_sell_recommended.mean()), 1),
    }
    print("== Recommendation mix by aging bucket")
    print(out.groupby("aging_bucket").agg(units=("vin", "size"), avg_model_discount=("recommended_discount", "mean"),
                                          avg_flat_rule=("flat_rule_discount", "mean"),
                                          uplift_vs_rule=("uplift_vs_flat_rule", "sum")).round(0)
          .join(out.groupby("aging_bucket")["recommended_discount"].apply(lambda s: round(float((s == 0).mean()), 3)).rename("share_hold_price"))
          .join(out.groupby("aging_bucket")["guardrail_applied"].mean().round(3).rename("share_guardrail_applied")).to_string())
    print("== Top 10 recommended cuts")
    print(out.sort_values("uplift_vs_flat_rule", ascending=False).head(10)[
        ["stock_number", "make", "model", "model_year", "days_in_stock", "current_price", "price_to_market",
         "recommended_discount", "flat_rule_discount", "expected_days_to_sell_now",
         "expected_days_to_sell_recommended", "uplift_vs_flat_rule"]].to_string(index=False))
    print("== SUMMARY " + json.dumps(summary))


if __name__ == "__main__":
    main()
