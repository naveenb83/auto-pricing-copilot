# Evidence 06 — Lakebase: operational serving + closed decision loop (Lakehouse Sync)

Project `piag-pricing` (Lakebase Autoscaling, Postgres 17), endpoint `primary`, database `databricks_postgres`. See `lakebase/README.md` for the design.

## 1. Lakehouse → Lakebase publish (job `piag-lakebase-publish`, staging + atomic swap, UC vs Postgres row counts)
Job `piag-lakebase-publish` (job_id 972427632414113), run_id 461897808692746 — captured 2026-11-14T14:48Z via `databricks jobs get-run(-output)`.

```text
result_state : SUCCESS
start (UTC)  : 2026-11-14T14:47:14Z
end (UTC)    : 2026-11-14T14:47:54Z
task publish                      SUCCESS  2026-11-14T14:47:14Z -> 2026-11-14T14:47:54Z
```

### Task `publish` stdout
```text
/Workspace/Users/naveen.balachandran@databricks.com/.bundle/auto-pricing-copilot/dev/files/lakebase/publish.py:80: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  note = f"Published from Unity Catalog {fq}.{src} at {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"


{"postgres_table": "serving.inventory_current", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current", "uc_rows": 1411, "postgres_rows": 1411, "match": true, "seconds": 9.1}
{"postgres_table": "serving.recommendations", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.pricing_recommendations", "uc_rows": 1411, "postgres_rows": 1411, "match": true, "seconds": 1.0}
{"postgres_table": "serving.rationale", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.pricing_rationale", "uc_rows": 592, "postgres_rows": 592, "match": true, "seconds": 0.7}
{"postgres_table": "serving.segment_targeting", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.segment_targeting", "uc_rows": 45, "postgres_rows": 45, "match": true, "seconds": 0.6}
{"postgres_table": "serving.rooftops", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.ref_rooftops", "uc_rows": 6, "postgres_rows": 6, "match": true, "seconds": 0.8}
{"postgres_table": "serving.rooftop_weekly_kpis", "uc_source": "serverless_stable_69fppe_catalog.piag_pricing.gold_rooftop_weekly_kpis", "uc_rows": 468, "postgres_rows": 468, "match": true, "seconds": 1.3}
== SUMMARY {"tables": 6, "all_counts_match": true, "rows": {"serving.inventory_current": 1411, "serving.recommendations": 1411, "serving.rationale": 592, "serving.segment_targeting": 45, "serving.rooftops": 6, "serving.rooftop_weekly_kpis": 468}}
```

## 2. App read paths + integrity constraints (psql session, `lakebase/03_checks.sql`; timings measured from a laptop over the internet)
```text
Timing is on.
 stock_number | make | model  | days_in_stock | current_price | recommended_discount | expected_days_to_sell_recommended |                                    rationale                                     
--------------+------+--------+---------------+---------------+----------------------+-----------------------------------+----------------------------------------------------------------------------------
 R03-24504    | Ford | Escape |           117 |         19095 |                 1500 |                              37.6 | The 2023 Ford Escape Limited has been in stock 117 days and is priced about 5% a
(1 row)

Time: 236.051 ms
 stock_number |   make    |   model    | days_in_stock | recommended_discount | uplift_vs_flat_rule 
--------------+-----------+------------+---------------+----------------------+---------------------
 R01-20774    | Toyota    | Corolla    |           237 |                 2000 |                1773
 R03-24504    | Ford      | Escape     |           117 |                 1500 |                1572
 R04-24698    | Ford      | Escape     |           111 |                 2500 |                1556
 R06-25687    | Kia       | EV6        |            76 |                 2000 |                1519
 R02-25593    | Chevrolet | Equinox EV |            80 |                 2000 |                1435
(5 rows)

Time: 228.628 ms
Timing is off.
BEGIN
psql:lakebase/03_checks.sql:13: ERROR:  new row for relation "pricing_decisions" violates check constraint "override_needs_reason"
DETAIL:  Failing row contains (1000, CHECK000000000000, CHECK, R01, null, 20000.00, 500.00, 3, realtime_endpoint, null, null, 1000.00, 1000.00, overridden, null, null, null, integrity-check, 2026-11-14 14:48:18.67191+00).
ROLLBACK
BEGIN
psql:lakebase/03_checks.sql:17: ERROR:  new row for relation "pricing_decisions" violates check constraint "final_matches"
DETAIL:  Failing row contains (1001, CHECK000000000000, CHECK, R01, null, 20000.00, 500.00, 3, realtime_endpoint, null, null, null, 900.00, accepted, null, null, null, integrity-check, 2026-11-14 14:48:19.401651+00).
ROLLBACK
 table_schema |     table_name      | rows 
--------------+---------------------+------
 pricing_ops  | override_reasons    |    7
 pricing_ops  | pricing_decisions   |    0
 serving      | inventory_current   | 1411
 serving      | rationale           |  592
 serving      | recommendations     | 1411
 serving      | rooftop_weekly_kpis |  468
 serving      | rooftops            |    6
 serving      | segment_targeting   |   45
(8 rows)

```

## 3. Lakebase → Lakehouse: Lakehouse Sync CDC (config `piag_pricing_ops` on Postgres schema `pricing_ops` → UC `piag_pricing.lb_*_history`)
A labelled smoke-test decision was inserted and then deleted in Postgres; both changes arrived in Unity Catalog within ~30 s:
```json
[
  {
    "_pg_change_type": "insert",
    "decided_by": "lakehouse-sync-smoke-test",
    "decision": "overridden",
    "decision_id": "1",
    "model_value": "250.00",
    "override_value": "100.00",
    "reason_code": "other",
    "stock_number": "SMOKE-TEST",
    "synced_at": "2026-11-14T14:15:26.518"
  },
  {
    "_pg_change_type": "delete",
    "decided_by": "lakehouse-sync-smoke-test",
    "decision": "overridden",
    "decision_id": "1",
    "model_value": "250.00",
    "override_value": "100.00",
    "reason_code": "other",
    "stock_number": "SMOKE-TEST",
    "synced_at": "2026-11-14T14:18:32.989"
  }
]
```
UC view `piag_pricing.pricing_decisions` rebuilds current state from the history (latest post-image, deletes removed) — 0 rows after the delete, as expected.
