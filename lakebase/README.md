# Lakebase: operational serving + the closed decision loop

Project `piag-pricing` (Autoscaling, Postgres 17), database `databricks_postgres`.

| Direction | What | How |
|---|---|---|
| Lakehouse → Lakebase | `serving.inventory_current`, `serving.recommendations`, `serving.rationale`, `serving.segment_targeting`, `serving.rooftops`, `serving.rooftop_weekly_kpis` | `piag-lakebase-publish` job (staging table + atomic swap). **Production:** Lakebase synced tables (TRIGGERED; CDF already on the sources) — needs the DB registered as a UC catalog (`CREATE CATALOG` on the metastore), not granted in this demo workspace. |
| App → Lakebase | `pricing_ops.pricing_decisions` — one row per decision: **model_value** (Model/DS), **override_value**, **reason_code / reason_text**, who/when, model version, expected profit of both | Databricks App (service principal: SELECT/INSERT only) |
| Lakebase → Lakehouse | `piag_pricing.lb_pricing_decisions_history`, `lb_override_reasons_history` (SCD2-style CDC with `_pg_change_type`, `_pg_lsn`) | **Lakehouse Sync** CDF config `piag_pricing_ops` on Postgres schema `pricing_ops` (native, no job) |

Integrity is enforced in Postgres, not just the UI: an override must carry a value **and** a reason code
(`override_needs_reason`), and the final discount must equal the override or the model value (`final_matches`).

Setup: `databricks psql --project piag-pricing -- -d databricks_postgres -f lakebase/01_schema.sql`, then
`databricks postgres create-cdf-config projects/piag-pricing/branches/production/databases/databricks-postgres <catalog> piag_pricing pricing_ops --cdf-config-id piag_pricing_ops`.
