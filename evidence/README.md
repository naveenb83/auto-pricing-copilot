# Execution evidence index

Every file here is **text captured from real runs** on Databricks (job stdout via `databricks jobs get-run-output`,
pipeline `event_log()`, SQL results, raw API JSON). Workspace: `fevm-serverless-stable` · catalog
`serverless_stable_69fppe_catalog` · schema `piag_pricing`. All data is synthetic (fictional Pacific Isles Auto Group).

| Stage (FE Bar) | What ran | Evidence |
|---|---|---|
| Raw data | 18-month dealer-group simulator on serverless → 79 weekly DMS file drops (CSV/JSONL) with injected dirt; 43 CC-licensed car photos | [01_synthetic_data_generation.md](01_synthetic_data_generation.md) |
| **Lakeflow** – ingest | Declarative Pipeline: 8 Auto Loader bronze STs → 8 silver MVs (expectations) → 6 gold MVs; incremental run ingested only the new drop (377,835 → 0 → 3,733 rows); gold reconciles exactly with ground truth | [02_lakeflow_pipeline.md](02_lakeflow_pipeline.md) |
| **Unity Catalog** – govern | Schema-level ABAC (financial mask, PII mask, rooftop row filter) driven by governed tags; same query under two identities (17,862 → 2,940 rows, costs hidden, PII masked); KPI metric view; lineage bronze → metric view | [03_unity_catalog_governance.md](03_unity_catalog_governance.md) |
| **ML** – intelligent | Monotone hazard model + expected-profit optimiser + guardrails: AUC 0.647 vs 0.546 naive, calibrated, 0 monotonicity violations, recovers hidden price elasticity (rank-corr 0.72); **digital-twin A/B: +$80k net profit / 120 days vs flat rule (95% CI +$47k..+$114k, 17/20 wins), aged 90+ −36%** | [04_ml_model.md](04_ml_model.md) |
| **ML** – real time | Model Serving endpoint `piag-pricing-model` (v3, AI Gateway inference table): raw request/response JSON incl. what-if price override | [04b_realtime_endpoint.md](04b_realtime_endpoint.md) |
| **Gen AI** | AI Functions (`ai_query`, Claude Haiku 5.5): rationale + promo copy for 592 aged units, **592/592 grounded** by an automatic number check; deterministic segment targeting | [05_genai_rationale.md](05_genai_rationale.md) |
| **Lakebase** – operational | Serving tables published (UC = PG row counts); decisions table with Postgres-enforced *override ⇒ value + reason*; **Lakehouse Sync CDC** back into UC | [06_lakebase.md](06_lakebase.md) |
| **Genie Agent** | 12-question native benchmark across 5 eval passes (one change per pass), non-GOOD answers re-executed and compared; final pass 12/12 result-set matches; Conversation-API transcript | [07_genie_benchmark.md](07_genie_benchmark.md), [07b_genie_transcript.md](07b_genie_transcript.md) |
| **Databricks App** | AppKit app deployed (RUNNING); raw JSON of queue → vehicle → **live Model/DS value** → what-if → accept / rejected overrides / **override + reason** → same decisions in UC | [08_app_e2e.md](08_app_e2e.md) |
| Integrated journey | One Lakeflow Job chains ingest → score → GenAI → Lakebase → 7 cross-stage health checks (7/7 PASS) | [09_orchestration.md](09_orchestration.md) |

Tests: `PIAG_E2E=1 uv run pytest` → 36 passed (unit + workspace e2e per stage). App: `databricks apps validate` ✅.
