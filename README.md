# Aged-Inventory Pricing Copilot — Pacific Isles Auto Group (fictional)

> **Every day a car sits on the lot it costs the dealer money.** This copilot tells pricing managers
> *which* aged units to discount, *by how much*, and *which customers to target* — in real time —
> and records every human override so the model and the policy keep learning.

All data is **synthetic** (see `datagen/`). Pacific Isles Auto Group is a fictional 6-rooftop,
multi-brand new + used dealer group. Vehicle photos are openly licensed from Wikimedia Commons
(attribution in `datagen/vehicle_images_manifest.csv`).

## The end-to-end data journey
| Stage | Databricks product | Where |
|---|---|---|
| Ingest raw weekly DMS drops | Lakeflow Declarative Pipelines (Auto Loader + expectations) | `pipelines/` |
| Govern | Unity Catalog (tags, column masks, row filters, metric view, lineage) | `governance/` |
| Operational serving | Lakebase Postgres (synced tables + app-written pricing decisions) | `lakebase/` |
| Make it intelligent | MLflow model → Model Serving (real-time discount recommendation) + AI Functions | `ml/` |
| Ask in natural language | Genie Agent | `genie/` |
| Surface to the business | Databricks App (AppKit) | `app/` |

## Execution evidence
Everything the evaluator needs to see as **text** is in [`evidence/`](evidence/).

## Run it
```bash
uv sync && uv run pytest                     # local e2e tests
databricks bundle deploy -p <profile>        # deploy all resources
databricks bundle run generate_data -p <profile>
```
