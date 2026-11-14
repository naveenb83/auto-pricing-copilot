# Evidence 08 — Databricks App `piag-pricing-copilot` (AppKit): deployed + end-to-end API run

Deployed app (AppKit 0.76.1, plugins: analytics, files, genie, lakebase, serving, server):
```json
{"url":"https://piag-pricing-copilot-7474651524368619.aws.databricksapps.com","app":"RUNNING","deploy":"SUCCEEDED","deployment_id":"01f1e04239301bccb97060bedad5293d"}
```
Runtime log (deployed):
```text
2026-11-14T15:45:01Z [APP] ./.env not found. Continuing without it.
2026-11-14T15:45:03Z [APP] [appkit:lakebase] Lakebase SP pool initialized
2026-11-14T15:45:03Z [APP] [appkit:lakebase] Lakebase OBO pool manager initialized
2026-11-14T15:45:03Z [APP] [appkit:server] Server running on http://0.0.0.0:8000
2026-11-14T15:45:03Z [APP] [appkit:server] Mode: production (static)
```

The flows below were executed against the **same server code** running locally (`npm run dev`) with the CLI profile, hitting the live Lakebase project, the real-time Model Serving endpoint, the SQL warehouse and the Genie space (raw JSON responses):

## 1. Identity
```json
{"email":"local-dev@databricks.com","user":"local-dev@databricks.com","asOf":"2026-11-13","genieRunsAs":"signed-in user (on-behalf-of)","dataRunsAs":"app service principal"}
```
## 2. Pricing queue (Lakebase `serving.*` + latest decision), 90+ days, top 3
```json
{
  "total": 279,
  "rows": [
    {
      "stock_number": "R01-20774",
      "make": "Toyota",
      "model": "Corolla",
      "days_in_stock": "237",
      "current_price": 25600,
      "recommended_discount": 2000,
      "flat_rule_discount": 0,
      "uplift_vs_flat_rule": 1773,
      "decision_status": "pending",
      "image_file": "vehicles/toyota-corolla.jpg"
    },
    {
      "stock_number": "R03-24504",
      "make": "Ford",
      "model": "Escape",
      "days_in_stock": "117",
      "current_price": 19095,
      "recommended_discount": 1500,
      "flat_rule_discount": 0,
      "uplift_vs_flat_rule": 1572,
      "decision_status": "pending",
      "image_file": "vehicles/ford-escape.jpg"
    },
    {
      "stock_number": "R04-24698",
      "make": "Ford",
      "model": "Escape",
      "days_in_stock": "111",
      "current_price": 35105,
      "recommended_discount": 2500,
      "flat_rule_discount": 0,
      "uplift_vs_flat_rule": 1556,
      "decision_status": "pending",
      "image_file": "vehicles/ford-escape.jpg"
    }
  ]
}
```
## 3. Vehicle detail (facts + grounded GenAI rationale + target segments)
```json
{
  "vehicle": {
    "stock_number": "R01-20774",
    "make": "Toyota",
    "model": "Corolla",
    "trim": "Limited",
    "days_in_stock": "237",
    "current_price": 25600,
    "market_price": 24436,
    "daily_holding_cost": 24.71,
    "image_file": "vehicles/toyota-corolla.jpg",
    "image_licence": "CC BY-SA 4.0"
  },
  "rationale": {
    "rationale": "This new 2026 Toyota Corolla Limited has been in stock 237 days and is priced 4.8% above market, so a $2,000 cut to $23,600 is recommended. The cut is expected to shorten time to sale from about 86 days to 39 and earn about $1,773 more than the flat-rule approach.",
    "promo_headline": "2026 Corolla Limited: Your First New Car",
    "promo_message": "First car? The Toyota Corolla Limited is now $2,000 off. Come see a new car built for your first road trips. Book a test drive today.",
    "top_segment": "first_time_buyer",
    "grounded": true
  },
  "segments": [
    {
      "segment": "first_time_buyer",
      "leads_per_1000_sends": 18.34,
      "lift_vs_body_class_avg": 2.42
    },
    {
      "segment": "value_retiree",
      "leads_per_1000_sends": 7.76,
      "lift_vs_body_class_avg": 1.02
    },
    {
      "segment": "young_family",
      "leads_per_1000_sends": 4.17,
      "lift_vs_body_class_avg": 0.55
    }
  ]
}
```
## 4. LIVE Model/DS value — `POST /api/recommend` → Model Serving endpoint
```json
{
  "latencyMs": 1022,
  "endpoint": "piag-pricing-model",
  "prediction": {
    "vin": "JTDSHNDR4TP940711",
    "recommended_discount": 2000,
    "recommended_price": 23600,
    "p_sell_30d_now": 0.149,
    "p_sell_30d_recommended": 0.5504,
    "expected_days_to_sell_now": 85.8,
    "expected_days_to_sell_recommended": 39,
    "expected_profit_now": -3262,
    "expected_profit_recommended": -1489,
    "expected_profit_flat_rule": -3262,
    "flat_rule_discount": 0,
    "uplift_vs_flat_rule": 1773,
    "guardrail_applied": false,
    "unconstrained_discount": 2000,
    "model_version": "3"
  },
  "curve": [
    {
      "discount": 0,
      "price": 25600,
      "p_sell_30d": 0.149,
      "p_sell_16w": 0.3928,
      "expected_days_to_sell": 85.8,
      "expected_profit": -3262,
      "front_gross_at_price": 533
    },
    {
      "discount": 250,
      "price": 25350,
      "p_sell_30d": 0.1778,
      "p_sell_16w": 0.428,
      "expected_days_to_sell": 82.4,
      "expected_profit": -3109,
      "front_gross_at_price": 283
    },
    {
      "discount": 500,
      "price": 25100,
      "p_sell_30d": 0.2216,
      "p_sell_16w": 0.4878,
      "expected_days_to_sell": 76.8,
      "expected_profit": -2809,
      "front_gross_at_price": 33
    },
    {
      "discount": 750,
      "price": 24850,
      "p_sell_30d": 0.2643,
      "p_sell_16w": 0.5491,
      "expected_days_to_sell": 71.4,
      "expected_profit": -2538,
      "front_gross_at_price": -217
    },
    {
      "discount": 1000,
      "price": 24600,
      "p_sell_30d": 0.2921,
      "p_sell_16w": 0.6066,
      "expected_days_to_sell": 66.5,
      "expected_profit": -2326,
      "front_gross_at_price": -467
    },
    {
      "discount": 1250,
      "price": 24350,
      "p_sell_30d": 0.3129,
      "p_sell_16w": 0.6613,
      "expected_days_to_sell": 62.3,
      "expected_profit": -2171,
      "front_gross_at_price": -717
    },
    {
      "discount": 1500,
      "price": 24100,
      "p_sell_30d": 0.3353,
      "p_sell_16w": 0.7132,
      "expected_days_to_sell": 58.5,
      "expected_profit": -2061,
      "front_gross_at_price": -967
    },
    {
      "discount": 2000,
      "price": 23600,
      "p_sell_30d": 0.5504,
      "p_sell_16w": 0.8632,
      "expected_days_to_sell": 39,
      "expected_profit": -1489,
      "front_gross_at_price": -1467
    },
    {
      "discount": 2500,
      "price": 23100,
      "p_sell_30d": 0.6714,
      "p_sell_16w": 0.9497,
      "expected_days_to_sell": 27.1,
      "expected_profit": -1411,
      "front_gross_at_price": -1967
    },
    {
      "discount": 3000,
      "price": 22600,
      "p_sell_30d": 0.7727,
      "p_sell_16w": 0.9815,
      "expected_days_to_sell": 20.1,
      "expected_profit": -1650,
      "front_gross_at_price": -2467
    }
  ]
}
```
## 5. What-if: the model re-evaluates a manager's $750 override (`priceOverride`)
```json
{"prediction":{"vin":"JTDSHNDR4TP940711","recommended_discount":1250,"recommended_price":23600,"p_sell_30d_now":0.2643,"p_sell_30d_recommended":0.5504,"expected_days_to_sell_now":71.4,"expected_days_to_sell_recommended":39,"expected_profit_now":-2538,"expected_profit_recommended":-1489,"expected_profit_flat_rule":-2538,"flat_rule_discount":0,"uplift_vs_flat_rule":1049,"guardrail_applied":false,"unconstrained_discount":1250,"model_version":"3"},"curve":[{"discount":0,"price":24850,"p_sell_30d":0.2643,"p_sell_16w":0.5491,"expected_days_to_sell":71.4,"expected_profit":-2538,"front_gross_at_price":-217},{"discount":250,"price":24600,"p_sell_30d":0.2921,"p_sell_16w":0.6066,"expected_days_to_sell":66.5,"expected_profit":-2326,"front_gross_at_price":-467},{"discount":500,"price":24350,"p_sell_30d":0.3129,"p_sell_16w":0.6613,"expected_days_to_sell":62.3,"expected_profit":-2171,"front_gross_at_price":-717},{"discount":750,"price":24100,"p_sell_30d":0.3353,"p_sell_16w":0.7132,"expected_days_to_sell":58.5,"expected_profit":-2061,"front_gross_at_price":-967},{"discount":1000,"price":23850,"p_sell_30d":0.4657,"p_sell_16w":0.7942,"expected_days_to_sell":48,"expected_profit":-1719,"front_gross_at_price":-1217},{"discount":1250,"price":23600,"p_sell_30d":0.5504,"p_sell_16w":0.8632,"expected_days_to_sell":39,"expected_profit":-1489,"front_gross_at_price":-1467},{"discount":1500,"price":23350,"p_sell_30d":0.6308,"p_sell_16w":0.9163,"expected_days_to_sell":31.4,"expected_profit":-1371,"front_gross_at_price":-1717},{"discount":2000,"price":22850,"p_sell_30d":0.6758,"p_sell_16w":0.9647,"expected_days_to_sell":25.7,"expected_profit":-1581,"front_gross_at_price":-2217},{"discount":2500,"price":22350,"p_sell_30d":0.7981,"p_sell_16w":0.989,"expected_days_to_sell":18.4,"expected_profit":-1842,"front_gross_at_price":-2717},{"discount":3000,"price":21850,"p_sell_30d":0.7981,"p_sell_16w":0.9943,"expected_days_to_sell":17.8,"expected_profit":-2314,"front_gross_at_price":-3217}],"latencyMs":326,"endpoint":"piag-pricing-model","priceOverride":24850}
```
## 6. Decisions: accept, two rejected overrides (validation), one override with reason
```text
accept  -> {"decision_id":"1005","decision":"accepted","model_value":"2000.00","final_discount":"2000.00"}
override without reason -> {"error":"An override needs an override value and a reason"} HTTP 400
override equal to model -> {"error":"Override value equals the model value — accept the model value instead"} HTTP 400
override -> {"decision_id":"1006","decision":"overridden","model_value":"1500.00","override_value":"1000.00","final_discount":"1000.00","reason_code":"customer_in_negotiation","model_expected_profit":"369.00","override_expected_profit":"-179.00"}
```
## 7. Decisions & impact summary (`GET /api/decisions`)
```json
{
  "summary": {
    "decisions": "2",
    "accepted": "1",
    "overridden": "1",
    "held": "0",
    "total_discount_committed": "3000.00",
    "override_delta_total": "-500.00",
    "override_expected_profit_gap": "-548.00"
  },
  "reasons": [
    {
      "reason": "Customer already negotiating on this unit",
      "n": "1",
      "avg_delta": "-500"
    }
  ]
}
```
## 8. Closed loop: the same decisions in Unity Catalog via Lakehouse Sync (`piag_pricing.pricing_decisions`)
```json
[
  {
    "decided_at": "2026-11-14T15:34:28.634Z",
    "decision": "accepted",
    "decision_id": "1005",
    "final_discount": "2000.00",
    "model_value": "2000.00",
    "model_version": "3",
    "override_delta": "0.00",
    "override_value": "",
    "reason_code": "",
    "stock_number": "R01-20774",
    "synced_at": "2026-11-14T15:34:28.637"
  },
  {
    "decided_at": "2026-11-14T15:34:34.163Z",
    "decision": "overridden",
    "decision_id": "1006",
    "final_discount": "1000.00",
    "model_value": "1500.00",
    "model_version": "3",
    "override_delta": "-500.00",
    "override_value": "1000.00",
    "reason_code": "customer_in_negotiation",
    "stock_number": "R03-24504",
    "synced_at": "2026-11-14T15:34:34.165"
  }
]
```
## 9. KPI queries through the app's analytics route (SQL warehouse, SSE result events, truncated)
```text
kpi_overview       id: f38d8c75-e7ba-496f-a281-b8eb8eb4c5a7event: warehouse_statusdata: {"type":"warehouse_status","status":{"state":"RUNNING","elapsedMs":950}}id: d386eafb-0914-4f3c-a0e9-36131869bc75event: resultdata: {"type":"result","data":[{"units_on_hand":"1411","aged_90_plus":"279","aged_45_plus":"592","aged_90_share":"0.19773210489014884","
model_vs_rule      id: 2337aca8-f07e-4f18-9195-d4cd08daf91eevent: resultdata: {"type":"result","data":[{"vehicles_scored":"1411","recommend_cut":"734","recommend_hold":"677","guardrail_applied":"275","expected_uplift_vs_rule":"279947.0","model_version":"3","scored_at":"2026-11-14T14:13:22.273Z"}]}
backtest_summary   id: 032c395d-a793-4a12-9821-4497a4dd6116event: resultdata: {"type":"result","data":[{"policy":"flat_rule","net_profit":"1639152.2389929022","aged90_day60":"290.95","carrying_cost":"823761.0363791039","wholesale_exits":"191.7","retail_units":"1006.75","futures":"20"},{"policy":"model_guardrails","net_profit":"1719424.7852230072",
aging_by_rooftop   id: 6e42b492-d649-479e-982e-0ed8b07f9e45event: resultdata: {"type":"result","data":[{"rooftop":"Eastgate Motors","d0_29":"116","d30_44":"31","d45_59":"23","d60_89":"32","d90_plus":"62"},{"rooftop":"Ridgeline Ford Chevrolet","d0_29":"113","d30_44":"37","d45_59":"22","d60_89":"30","d90_plus":"49"},{"rooftop":"Northshore Auto","d0_
aged_trend         id: e449a0b4-93b2-4b7b-a9cc-47ac3fd65613event: resultdata: {"type":"result","data":[{"week_end":"2026-05-17","aged_90_share_pct":"16.6","carrying_cost_week":"104450.0"},{"week_end":"2026-05-24","aged_90_share_pct":"15.8","carrying_cost_week":"103605.0"},{"week_end":"2026-05-31","aged_90_share_pct":"15.3","carrying_cost_week":"10
```
## 10. Licensed photo served from the UC volume through the files plugin (read-only policy)
```text
GET /api/files/files/raw?path=vehicles/toyota-corolla.jpg -> HTTP 200 image/jpeg 167854 bytes
photo.jpg: JPEG image data, Exif standard: [TIFF image data, big-endian, direntries=3], baseline, precision 8, 1280x720, components 3
```
## 11. Least privilege for the app's service principal in Lakebase
```text
18d1bc33-eabe-4547-82e1-24cc3f835482
serving.recommendations SELECT=true
pricing_decisions INSERT=true
pricing_decisions DELETE=false
```
The app can read the serving tables and INSERT decisions, but cannot DELETE them — the audit trail cannot be erased from the app.

Decisions #1005/#1006 are labelled E2E test decisions (decided_by = local-dev); they remain as sample data for the Decisions page and Genie.
