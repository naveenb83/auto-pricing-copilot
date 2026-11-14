# Evidence 01 — Synthetic data generation (executed on Databricks serverless)

Job `piag-generate-synthetic-data` (job_id 298498322183881), run_id 23288830128253.
Captured with `databricks jobs get-run-output` on 2026-11-14T12:54Z.

```text
result_state     : SUCCESS
start (UTC)      : 2026-11-14T12:51:47Z
end (UTC)        : 2026-11-14T12:53:46Z
compute          : serverless (environment_version 4)
```

## Job stdout (generation summary, from `get-run-output`)
```json
{
  "as_of": "2026-11-13",
  "drops": 79,
  "held_drop": "2026-11-13",
  "rows": {
    "vehicles": 17988,
    "customers": 25000,
    "price_changes": 13122,
    "sales": 16536,
    "web_leads": 125604,
    "market_comps": 125604,
    "campaigns": 48,
    "campaign_responses": 57666
  },
  "vehicles_simulated": 17916,
  "on_hand_at_as_of": 1413,
  "on_hand_45_plus": 592,
  "on_hand_90_plus": 279,
  "retail_sales": 15849,
  "wholesale_exits": 580,
  "median_days_to_retail": 28.0,
  "price_change_reasons": {
    "market_adjustment": 4560,
    "manager_discretion": 3950,
    "aged_45_rule": 3554,
    "aged_90_rule": 1019
  }
}
```

## `_generation_summary.json` written by the job into the landing volume
```json
{
  "as_of": "2026-11-13",
  "drops": 79,
  "held_drop": "2026-11-13",
  "rows": {
    "vehicles": 17988,
    "customers": 25000,
    "price_changes": 13122,
    "sales": 16536,
    "web_leads": 125604,
    "market_comps": 125604,
    "campaigns": 48,
    "campaign_responses": 57666
  },
  "vehicles_simulated": 17916,
  "on_hand_at_as_of": 1413,
  "on_hand_45_plus": 592,
  "on_hand_90_plus": 279,
  "retail_sales": 15849,
  "wholesale_exits": 580,
  "median_days_to_retail": 28.0,
  "price_change_reasons": {
    "market_adjustment": 4560,
    "manager_discretion": 3950,
    "aged_45_rule": 3554,
    "aged_90_rule": 1019
  }
}
```

## Landing volume layout after the run
```text
_generation_summary.json
_held
_truth
campaign_responses
campaigns
customers
market_comps
price_changes
reference
sales
vehicles
web_leads
vehicles             78 weekly drop folders
customers            78 weekly drop folders
price_changes        78 weekly drop folders
sales                78 weekly drop folders
web_leads            78 weekly drop folders
market_comps         78 weekly drop folders
campaigns            48 weekly drop folders
campaign_responses   48 weekly drop folders
_held/vehicles       drop_date=2026-11-13  (final drop held back for the incremental-ingest demo)
```

## Vehicle photos in volume `media` (43 files) — licences
```text
licence
CC BY-SA 4.0    38
CC BY 4.0        2
CC BY-SA 3.0     2
CC BY 2.0        1
```
