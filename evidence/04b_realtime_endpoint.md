# Evidence 04b — Real-time Model Serving endpoint `piag-pricing-model` (champion v2)

Real on-hand vehicles read from `gold_inventory_current`, sent to the endpoint via the Databricks SDK (`serving_endpoints.query`). Raw request and response JSON below.

## Batch of 3 vehicles (aged used, aged used, fresh new)
Round-trip latency: **1,060 ms** (client-measured, warm endpoint)

Request `dataframe_records`:
```json
[
 {
  "vin": "JTDL79AD0TF094588",
  "current_price": 24925.0,
  "unit_cost": 22987.27,
  "market_price": 23275.0,
  "daily_market_depreciation": 12.98,
  "daily_holding_cost": 23.45,
  "flat_rule_additional_discount": 0.0,
  "days_in_stock": 155,
  "model_year": 2026,
  "mileage": 7,
  "market_days_supply": 67.0,
  "vdp_views_last_week": 18,
  "leads_last_week": 0,
  "test_drives_last_week": 0,
  "weeks_listed": 23,
  "condition": "new",
  "body_class": "compact_car",
  "make": "Toyota",
  "model": "Corolla",
  "exterior_colour": "White",
  "rooftop_id": "R05",
  "as_of_date": "2026-11-13",
  "price_override": null
 },
 {
  "vin": "1FT85MUNXPV186402",
  "current_price": 19095.0,
  "unit_cost": 17262.21,
  "market_price": 18149.0,
  "daily_market_depreciation": 11.49,
  "daily_holding_cost": 20.84,
  "flat_rule_additional_discount": 0.0,
  "days_in_stock": 117,
  "model_year": 2023,
  "mileage": 50476,
  "market_days_supply": 74.0,
  "vdp_views_last_week": 23,
  "leads_last_week": 0,
  "test_drives_last_week": 0,
  "weeks_listed": 18,
  "condition": "used",
  "body_class": "compact_suv",
  "make": "Ford",
  "model": "Escape",
  "exterior_colour": "Grey",
  "rooftop_id": "R03",
  "as_of_date": "2026-11-13",
  "price_override": null
 },
 {
  "vin": "1FTDJ7WR0VL683060",
  "current_price": 30640.0,
  "unit_cost": 28751.81,
  "market_price": 30526.0,
  "daily_market_depreciation": 6.21,
  "daily_holding_cost": 17.79,
  "flat_rule_additional_discount": 0.0,
  "days_in_stock": 8,
  "model_year": 2027,
  "mileage": 59,
  "market_days_supply": 89.0,
  "vdp_views_last_week": 54,
  "leads_last_week": 1,
  "test_drives_last_week": 1,
  "weeks_listed": 2,
  "condition": "new",
  "body_class": "compact_suv",
  "make": "Ford",
  "model": "Escape",
  "exterior_colour": "Blue",
  "rooftop_id": "R04",
  "as_of_date": "2026-11-13",
  "price_override": null
 }
]
```
Response `predictions`:
```json
[
 {
  "vin": "JTDL79AD0TF094588",
  "recommended_discount": 1500.0,
  "recommended_price": 23425.0,
  "p_sell_30d_now": 0.1192,
  "p_sell_30d_recommended": 0.3105,
  "expected_days_to_sell_now": 90.3,
  "expected_days_to_sell_recommended": 65.0,
  "expected_profit_now": -2292.0,
  "expected_profit_recommended": -1194.0,
  "expected_profit_flat_rule": -2292.0,
  "flat_rule_discount": 0.0,
  "uplift_vs_flat_rule": 1098.0,
  "guardrail_applied": true,
  "unconstrained_discount": 2500.0,
  "curve_json": [
   {
    "discount": 0.0,
    "price": 24925.0,
    "p_sell_30d": 0.1192,
    "p_sell_16w": 0.35,
    "expected_days_to_sell": 90.3,
    "expected_profit": -2292.0,
    "front_gross_at_price": 1938.0
   },
   {
    "discount": 250.0,
    "price": 24675.0,
    "p_sell_30d": 0.1291,
    "p_sell_16w": 0.3666,
    "expected_days_to_sell": 88.7,
    "expected_profit": -2257.0,
    "front_gross_at_price": 1688.0
   },
   {
    "discount": 500.0,
    "price": 24425.0,
    "p_sell_30d": 0.139,
    "p_sell_16w": 0.385,
    "expected_days_to_sell": 87.0,
    "expected_profit": -2221.0,
    "front_gross_at_price": 1438.0
   },
   {
    "discount": 750.0,
    "price": 24175.0,
    "p_sell_30d": 0.1797,
    "p_sell_16w": 0.4294,
    "expected_days_to_sell": 82.5,
    "expected_profit": -2008.0,
    "front_gross_at_price": 1188.0
   },
   {
    "discount": 1000.0,
    "price": 23925.0,
    "p_sell_30d": 0.2344,
    "p_sell_16w": 0.4924,
    "expected_days_to_sell": 76.1,
    "expected_profit": -1694.0,
    "front_gross_at_price": 938.0
   },
   {
    "discount": 1250.0,
    "price": 23675.0,
    "p_sell_30d": 0.2781,
    "p_sell_16w": 0.5564,
    "expected_days_to_sell": 70.4,
    "expected_profit": -1420.0,
    "front_gross_at_price": 688.0
   },
   {
    "discount": 1500.0,
    "price": 23425.0,
    "p_sell_30d": 0.3105,
    "p_sell_16w": 0.6189,
    "expected_days_to_sell": 65.0,
    "expected_profit": -1194.0,
    "front_gross_at_price": 438.0
   },
   {
    "discount": 2000.0,
    "price": 22925.0,
    "p_sell_30d": 0.356,
    "p_sell_16w": 0.7286,
    "expected_days_to_sell": 56.7,
    "expected_profit": -945.0,
    "front_gross_at_price": -62.0
   },
   {
    "discount": 2500.0,
    "price": 22425.0,
    "p_sell_30d": 0.5683,
    "p_sell_16w": 0.8786,
    "expected_days_to_sell": 37.4,
    "expected_profit": -433.0,
    "front_gross_at_price": -562.0
   },
   {
    "discount": 3000.0,
    "price": 21925.0,
    "p_sell_30d": 0.6471,
    "p_sell_16w": 0.9512,
    "expected_days_to_sell": 28.2,
    "expected_profit": -488.0,
    "front_gross_at_price": -1062.0
   }
  ],
  "model_version": "3"
 },
 {
  "vin": "1FT85MUNXPV186402",
  "recommended_discount": 1500.0,
  "recommended_price": 17595.0,
  "p_sell_30d_now": 0.2118,
  "p_sell_30d_recommended": 0.5877,
  "expected_days_to_sell_now": 77.9,
  "expected_days_to_sell_recommended": 37.6,
  "expected_profit_now": -1203.0,
  "expected_profit_recommended": 369.0,
  "expected_profit_flat_rule": -1203.0,
  "flat_rule_discount": 0.0,
  "uplift_vs_flat_rule": 1572.0,
  "guardrail_applied": true,
  "unconstrained_discount": 2000.0,
  "curve_json": [
   {
    "discount": 0.0,
    "price": 19095.0,
    "p_sell_30d": 0.2118,
    "p_sell_16w": 0.4756,
    "expected_days_to_sell": 77.9,
    "expected_profit": -1203.0,
    "front_gross_at_price": 1833.0
   },
   {
    "discount": 250.0,
    "price": 18845.0,
    "p_sell_30d": 0.2471,
    "p_sell_16w": 0.5148,
    "expected_days_to_sell": 73.9,
    "expected_profit": -1042.0,
    "front_gross_at_price": 1583.0
   },
   {
    "discount": 500.0,
    "price": 18595.0,
    "p_sell_30d": 0.2913,
    "p_sell_16w": 0.5706,
    "expected_days_to_sell": 68.4,
    "expected_profit": -790.0,
    "front_gross_at_price": 1333.0
   },
   {
    "discount": 750.0,
    "price": 18345.0,
    "p_sell_30d": 0.3487,
    "p_sell_16w": 0.6479,
    "expected_days_to_sell": 61.1,
    "expected_profit": -432.0,
    "front_gross_at_price": 1083.0
   },
   {
    "discount": 1000.0,
    "price": 18095.0,
    "p_sell_30d": 0.3986,
    "p_sell_16w": 0.7136,
    "expected_days_to_sell": 54.7,
    "expected_profit": -179.0,
    "front_gross_at_price": 833.0
   },
   {
    "discount": 1250.0,
    "price": 17845.0,
    "p_sell_30d": 0.4491,
    "p_sell_16w": 0.7796,
    "expected_days_to_sell": 48.0,
    "expected_profit": 46.0,
    "front_gross_at_price": 583.0
   },
   {
    "discount": 1500.0,
    "price": 17595.0,
    "p_sell_30d": 0.5877,
    "p_sell_16w": 0.8592,
    "expected_days_to_sell": 37.6,
    "expected_profit": 369.0,
    "front_gross_at_price": 333.0
   },
   {
    "discount": 2000.0,
    "price": 17095.0,
    "p_sell_30d": 0.7421,
    "p_sell_16w": 0.9617,
    "expected_days_to_sell": 23.0,
    "expected_profit": 577.0,
    "front_gross_at_price": -167.0
   },
   {
    "discount": 2500.0,
    "price": 16595.0,
    "p_sell_30d": 0.8736,
    "p_sell_16w": 0.9919,
    "expected_days_to_sell": 14.8,
    "expected_profit": 352.0,
    "front_gross_at_price": -667.0
   },
   {
    "discount": 3000.0,
    "price": 16095.0,
    "p_sell_30d": 0.8736,
    "p_sell_16w": 0.9972,
    "expected_days_to_sell": 14.1,
    "expected_profit": -118.0,
    "front_gross_at_price": -1167.0
   }
  ],
  "model_version": "3"
 },
 {
  "vin": "1FTDJ7WR0VL683060",
  "recommended_discount": 0.0,
  "recommended_price": 30640.0,
  "p_sell_30d_now": 0.6491,
  "p_sell_30d_recommended": 0.6491,
  "expected_days_to_sell_now": 27.5,
  "expected_days_to_sell_recommended": 27.5,
  "expected_profit_now": 2649.0,
  "expected_profit_recommended": 2649.0,
  "expected_profit_flat_rule": 2649.0,
  "flat_rule_discount": 0.0,
  "uplift_vs_flat_rule": 0.0,
  "guardrail_applied": false,
  "unconstrained_discount": 0.0,
  "curve_json": [
   {
    "discount": 0.0,
    "price": 30640.0,
    "p_sell_30d": 0.6491,
    "p_sell_16w": 0.9705,
    "expected_days_to_sell": 27.5,
    "expected_profit": 2649.0,
    "front_gross_at_price": 1888.0
   },
   {
    "discount": 250.0,
    "price": 30390.0,
    "p_sell_30d": 0.6741,
    "p_sell_16w": 0.9808,
    "expected_days_to_sell": 25.2,
    "expected_profit": 2480.0,
    "front_gross_at_price": 1638.0
   },
   {
    "discount": 500.0,
    "price": 30140.0,
    "p_sell_30d": 0.701,
    "p_sell_16w": 0.9865,
    "expected_days_to_sell": 23.6,
    "expected_profit": 2280.0,
    "front_gross_at_price": 1388.0
   },
   {
    "discount": 750.0,
    "price": 29890.0,
    "p_sell_30d": 0.744,
    "p_sell_16w": 0.9901,
    "expected_days_to_sell": 21.3,
    "expected_profit": 2084.0,
    "front_gross_at_price": 1138.0
   },
   {
    "discount": 1000.0,
    "price": 29640.0,
    "p_sell_30d": 0.8183,
    "p_sell_16w": 0.9953,
    "expected_days_to_sell": 17.2,
    "expected_profit": 1921.0,
    "front_gross_at_price": 888.0
   },
   {
    "discount": 1250.0,
    "price": 29390.0,
    "p_sell_30d": 0.8491,
    "p_sell_16w": 0.9979,
    "expected_days_to_sell": 14.8,
    "expected_profit": 1721.0,
    "front_gross_at_price": 638.0
   },
   {
    "discount": 1500.0,
    "price": 29140.0,
    "p_sell_30d": 0.8948,
    "p_sell_16w": 0.9993,
    "expected_days_to_sell": 12.9,
    "expected_profit": 1508.0,
    "front_gross_at_price": 388.0
   },
   {
    "discount": 2000.0,
    "price": 28640.0,
    "p_sell_30d": 0.9278,
    "p_sell_16w": 0.9999,
    "expected_days_to_sell": 11.1,
    "expected_profit": 1041.0,
    "front_gross_at_price": -112.0
   },
   {
    "discount": 2500.0,
    "price": 28140.0,
    "p_sell_30d": 0.9705,
    "p_sell_16w": 1.0,
    "expected_days_to_sell": 8.5,
    "expected_profit": 587.0,
    "front_gross_at_price": -612.0
   },
   {
    "discount": 3000.0,
    "price": 27640.0,
    "p_sell_30d": 0.9705,
    "p_sell_16w": 1.0,
    "expected_days_to_sell": 8.5,
    "expected_profit": 87.0,
    "front_gross_at_price": -1112.0
   }
  ],
  "model_version": "3"
 }
]
```
## What-if: first vehicle re-evaluated as if listed $1,500 lower (price_override)
Round-trip latency: **370 ms** (client-measured, warm endpoint)

Request `dataframe_records`:
```json
[
 {
  "vin": "JTDL79AD0TF094588",
  "current_price": 24925.0,
  "unit_cost": 22987.27,
  "market_price": 23275.0,
  "daily_market_depreciation": 12.98,
  "daily_holding_cost": 23.45,
  "flat_rule_additional_discount": 0.0,
  "days_in_stock": 155,
  "model_year": 2026,
  "mileage": 7,
  "market_days_supply": 67.0,
  "vdp_views_last_week": 18,
  "leads_last_week": 0,
  "test_drives_last_week": 0,
  "weeks_listed": 23,
  "condition": "new",
  "body_class": "compact_car",
  "make": "Toyota",
  "model": "Corolla",
  "exterior_colour": "White",
  "rooftop_id": "R05",
  "as_of_date": "2026-11-13",
  "price_override": 23425.0
 }
]
```
Response `predictions`:
```json
[
 {
  "vin": "JTDL79AD0TF094588",
  "recommended_discount": 1250.0,
  "recommended_price": 22175.0,
  "p_sell_30d_now": 0.3105,
  "p_sell_30d_recommended": 0.6262,
  "expected_days_to_sell_now": 65.0,
  "expected_days_to_sell_recommended": 31.0,
  "expected_profit_now": -1194.0,
  "expected_profit_recommended": -382.0,
  "expected_profit_flat_rule": -1194.0,
  "flat_rule_discount": 0.0,
  "uplift_vs_flat_rule": 812.0,
  "guardrail_applied": false,
  "unconstrained_discount": 1250.0,
  "curve_json": [
   {
    "discount": 0.0,
    "price": 23425.0,
    "p_sell_30d": 0.3105,
    "p_sell_16w": 0.6189,
    "expected_days_to_sell": 65.0,
    "expected_profit": -1194.0,
    "front_gross_at_price": 438.0
   },
   {
    "discount": 250.0,
    "price": 23175.0,
    "p_sell_30d": 0.3228,
    "p_sell_16w": 0.6713,
    "expected_days_to_sell": 61.4,
    "expected_profit": -1078.0,
    "front_gross_at_price": 188.0
   },
   {
    "discount": 500.0,
    "price": 22925.0,
    "p_sell_30d": 0.356,
    "p_sell_16w": 0.7286,
    "expected_days_to_sell": 56.7,
    "expected_profit": -945.0,
    "front_gross_at_price": -62.0
   },
   {
    "discount": 750.0,
    "price": 22675.0,
    "p_sell_30d": 0.4643,
    "p_sell_16w": 0.8062,
    "expected_days_to_sell": 47.3,
    "expected_profit": -667.0,
    "front_gross_at_price": -312.0
   },
   {
    "discount": 1000.0,
    "price": 22425.0,
    "p_sell_30d": 0.5683,
    "p_sell_16w": 0.8786,
    "expected_days_to_sell": 37.4,
    "expected_profit": -433.0,
    "front_gross_at_price": -562.0
   },
   {
    "discount": 1250.0,
    "price": 22175.0,
    "p_sell_30d": 0.6262,
    "p_sell_16w": 0.9254,
    "expected_days_to_sell": 31.0,
    "expected_profit": -382.0,
    "front_gross_at_price": -812.0
   },
   {
    "discount": 1500.0,
    "price": 21925.0,
    "p_sell_30d": 0.6471,
    "p_sell_16w": 0.9512,
    "expected_days_to_sell": 28.2,
    "expected_profit": -488.0,
    "front_gross_at_price": -1062.0
   },
   {
    "discount": 2000.0,
    "price": 21425.0,
    "p_sell_30d": 0.7804,
    "p_sell_16w": 0.982,
    "expected_days_to_sell": 20.2,
    "expected_profit": -718.0,
    "front_gross_at_price": -1562.0
   },
   {
    "discount": 2500.0,
    "price": 20925.0,
    "p_sell_30d": 0.7804,
    "p_sell_16w": 0.9922,
    "expected_days_to_sell": 18.5,
    "expected_profit": -1157.0,
    "front_gross_at_price": -2062.0
   },
   {
    "discount": 3000.0,
    "price": 20425.0,
    "p_sell_30d": 0.7804,
    "p_sell_16w": 0.9963,
    "expected_days_to_sell": 18.4,
    "expected_profit": -1646.0,
    "front_gross_at_price": -2562.0
   }
  ],
  "model_version": "3"
 }
]
```
