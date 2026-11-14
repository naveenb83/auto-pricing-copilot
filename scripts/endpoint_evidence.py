"""Query the real-time pricing endpoint with real on-hand vehicles and write evidence/04b (request, response, latency)."""
import json
import subprocess
import time

from databricks.sdk import WorkspaceClient

P, FQ, EP = "DEFAULT", "serverless_stable_69fppe_catalog.piag_pricing", "piag-pricing-model"
COLS = ["vin", "current_price", "unit_cost", "market_price", "daily_market_depreciation", "daily_holding_cost",
        "flat_rule_additional_discount", "days_in_stock", "model_year", "mileage", "market_days_supply",
        "vdp_views_last_week", "leads_last_week", "test_drives_last_week", "weeks_listed", "condition", "body_class",
        "make", "model", "exterior_colour", "rooftop_id", "as_of_date"]
NUM = {"current_price", "unit_cost", "market_price", "daily_market_depreciation", "daily_holding_cost",
       "flat_rule_additional_discount", "days_in_stock", "model_year", "mileage", "market_days_supply",
       "vdp_views_last_week", "leads_last_week", "test_drives_last_week", "weeks_listed"}


def q(sql):
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", sql, "-p", P],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index("["):])


def rec(r):
    d = {c: (float(r[c]) if c in NUM and r[c] not in (None, "") else r[c]) for c in COLS}
    for c in ("days_in_stock", "model_year", "mileage", "vdp_views_last_week", "leads_last_week",
              "test_drives_last_week", "weeks_listed"):
        d[c] = int(d[c])
    d["price_override"] = None
    return d


w = WorkspaceClient(profile=P)
rows = q(f"SELECT {', '.join(COLS)}, stock_number FROM {FQ}.gold_inventory_current "
         f"WHERE stock_number IN ('R05-23373', 'R03-24504') OR (days_in_stock BETWEEN 3 AND 8 AND condition = 'new') "
         f"ORDER BY days_in_stock DESC LIMIT 3")
records = [rec(r) for r in rows]
whatif = dict(records[0])
whatif["price_override"] = float(records[0]["current_price"]) - 1500
out = ["# Evidence 04b — Real-time Model Serving endpoint `piag-pricing-model` (champion v2)\n",
       "Real on-hand vehicles read from `gold_inventory_current`, sent to the endpoint via the Databricks SDK "
       "(`serving_endpoints.query`). Raw request and response JSON below.\n"]
for title, payload in [("Batch of 3 vehicles (aged used, aged used, fresh new)", records),
                       ("What-if: first vehicle re-evaluated as if listed $1,500 lower (price_override)", [whatif])]:
    t0 = time.time()
    resp = w.serving_endpoints.query(name=EP, dataframe_records=payload)
    ms = (time.time() - t0) * 1000
    preds = resp.predictions
    for p in preds:
        p["curve_json"] = json.loads(p["curve_json"])
    out += [f"## {title}", f"Round-trip latency: **{ms:,.0f} ms** (client-measured, warm endpoint)\n",
            "Request `dataframe_records`:", "```json", json.dumps(payload, indent=1), "```",
            "Response `predictions`:", "```json", json.dumps(preds, indent=1), "```"]
    print(title, f"{ms:.0f}ms", [(p["vin"], p["recommended_discount"], p["expected_profit_recommended"],
                                  p["uplift_vs_flat_rule"], p["guardrail_applied"]) for p in preds])
open("evidence/04b_realtime_endpoint.md", "w").write("\n".join(out) + "\n")
