"""MLflow pyfunc served on Model Serving: vehicle state in -> recommended discount + profit curve out.

Input  (one row per vehicle, columns as in gold_inventory_current / the Lakebase synced table):
  vin, current_price, unit_cost, market_price, daily_market_depreciation, daily_holding_cost,
  flat_rule_additional_discount, days_in_stock, model_year, mileage, market_days_supply,
  vdp_views_last_week, leads_last_week, test_drives_last_week, weeks_listed,
  condition, body_class, make, model, exterior_colour, rooftop_id, as_of_date
  Optional what-if: price_override (evaluate the vehicle as if listed at this price).
Output (one row per vehicle): recommended_discount, recommended_price, p_sell_30d_*, expected_days_*,
  expected_profit_* (now / recommended / flat rule), uplift_vs_flat_rule, curve_json, model_version.
"""

from __future__ import annotations

import pickle

import mlflow.pyfunc
import pandas as pd

try:  # inside the served/logged model the module is shipped via code_paths
    from pricing_core import recommend_batch, state_from_inventory_row
except ImportError:  # local / job usage
    from ml.pricing_core import recommend_batch, state_from_inventory_row

INPUT_COLUMNS = ["vin", "current_price", "unit_cost", "market_price", "daily_market_depreciation",
                 "daily_holding_cost", "flat_rule_additional_discount", "days_in_stock", "model_year", "mileage",
                 "market_days_supply", "vdp_views_last_week", "leads_last_week", "test_drives_last_week",
                 "weeks_listed", "condition", "body_class", "make", "model", "exterior_colour", "rooftop_id",
                 "as_of_date"]


class PricingModel(mlflow.pyfunc.PythonModel):
    def __init__(self, hazard_model=None, model_version: str = "dev"):
        self.model = hazard_model
        self.model_version = model_version

    def load_context(self, context):
        if self.model is None:
            with open(context.artifacts["hazard_model"], "rb") as f:
                self.model = pickle.load(f)

    def predict(self, context, model_input: pd.DataFrame, params=None) -> pd.DataFrame:
        recs = model_input.to_dict("records")
        for r in recs:
            if r.get("price_override") not in (None, "") and pd.notna(r.get("price_override")):
                r["current_price"] = float(r["price_override"])
        out = recommend_batch(self.model, [state_from_inventory_row(r) for r in recs])
        for r, res in zip(recs, out):
            res["vin"] = r.get("vin")
            res["model_version"] = self.model_version
        cols = ["vin", "recommended_discount", "recommended_price", "p_sell_30d_now", "p_sell_30d_recommended",
                "expected_days_to_sell_now", "expected_days_to_sell_recommended", "expected_profit_now",
                "expected_profit_recommended", "expected_profit_flat_rule", "flat_rule_discount",
                "uplift_vs_flat_rule", "guardrail_applied", "unconstrained_discount", "curve_json", "model_version"]
        return pd.DataFrame(out)[cols]
