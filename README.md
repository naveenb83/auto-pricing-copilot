# Aged-Inventory Pricing Copilot — Pacific Isles Auto Group (fictional)

> **Every day a car sits on the lot it costs the dealer money.** This copilot tells pricing managers *which* aged units to
> discount, *by how much* and *which customers to target* — live, per car — and records every human override with a
> reason so the model and the policy keep learning.

**Industry:** automotive retail (multi-rooftop new + used dealer group). **Buyer:** Dealer Principal / CFO (executive
sponsor) and the Used/New-Car & Pricing Managers (domain owners).
**All data is synthetic** — Pacific Isles Auto Group is fictional. Vehicle photos are openly licensed Wikimedia Commons
images (attribution in [`datagen/vehicle_images_manifest.csv`](datagen/vehicle_images_manifest.csv)).

| | |
|---|---|
| Live app | https://piag-pricing-copilot-7474651524368619.aws.databricksapps.com (Databricks workspace SSO) |
| Deck | [`deck/deck.pdf`](deck/deck.pdf) · text export [`deck/deck.md`](deck/deck.md) |
| Demo scripts | [business](docs/demo_script_business.md) · [technical](docs/demo_script_technical.md) |
| **Execution evidence (text)** | [`evidence/README.md`](evidence/README.md) — one file per stage |
| Screens | [`docs/screens/`](docs/screens/) |

## The problem
At the business date (13 Nov 2026) the group has **1,411 units, 279 (19.8%) aged 90+ days**, costing **$7,625/day**
(≈ $229k/month) in floor-plan interest, lot cost and depreciation; **384 auction exits** last year lost **$704k**. Discounting
is a flat rule — $250 at 45 days, $500 at 90 — applied by judgement, and for most aged units it has already been applied,
so it now adds nothing.

## The outcome (digital-twin A/B on today's lot, 120 days, 20 paired futures)
| | Flat rule | **Copilot (model + guardrails)** |
|---|---|---|
| Net profit | $1,639,152 | **$1,719,425 (+$80,273; 95% CI +$46.8k..+$113.7k; wins 17/20)** |
| Units aged 90+ at day 60 | 291 | **186 (−36%)** |
| Carrying cost | $823,761 | **$642,102 (−$182k)** |
| Auction exits | 192 | **98** |

## End-to-end data journey (integrated, not siloed)
```
DMS weekly file drops (synthetic, 79 drops, dirty)            datagen/  jobs/generate_data.py
  └─ Lakeflow Declarative Pipeline: Auto Loader bronze → silver (expectations) → gold        pipelines/pricing/
       └─ Unity Catalog: governed tags → ABAC masks (cost/gross, PII) + rooftop row filter,
          KPI metric view, lineage                                                             governance/
            ├─ ML: weekly sale-hazard model (monotone in price) + expected-profit optimiser +
            │  guardrails → MLflow → UC registry @champion → Model Serving (real time)         ml/
            ├─ Gen AI: AI Functions (Claude Haiku) rationale + promo copy, grounding check      ml/genai_rationale.py
            ├─ Lakebase: serving tables for the app; pricing_decisions (Model/DS value vs
            │  override value + reason) → Lakehouse Sync CDC back into UC                       lakebase/
            ├─ Genie Agent over gold + metric view (benchmarked)                               genie/
            └─ Databricks App (AppKit): queue · live Model/DS value · override + reason ·
               decisions & impact · ask the data (Genie, on-behalf-of user)                    app/
One Lakeflow Job runs it nightly with cross-stage health checks                                resources/orchestration.yml
```

| Stage | Product | Key result | Evidence |
|---|---|---|---|
| Ingest | Lakeflow Declarative Pipelines | 26 datasets; incremental (377,835 → 0 → 3,733 rows); gold reconciles with ground truth | [02](evidence/02_lakeflow_pipeline.md) |
| Govern | Unity Catalog (ABAC, governed tags, metric view, lineage) | 17,862 → 2,940 rows under a rooftop lens; cost/gross NULL; PII masked | [03](evidence/03_unity_catalog_governance.md) |
| Intelligence | MLflow, Model Serving, AI Functions | AUC 0.647 vs 0.546; elasticity recovery 0.72; +$80k backtest; live ~0.3 s; 592/592 grounded | [04](evidence/04_ml_model.md) · [04b](evidence/04b_realtime_endpoint.md) · [05](evidence/05_genai_rationale.md) |
| Operational serving | Lakebase + Lakehouse Sync | UC = PG counts; Postgres-enforced override ⇒ value + reason; decisions back in UC in seconds | [06](evidence/06_lakebase.md) |
| Natural language | Genie Agent | 12-q benchmark, 5 passes, final 12/12 result-set matches | [07](evidence/07_genie_benchmark.md) · [07b](evidence/07b_genie_transcript.md) |
| Business surface | Databricks Apps (AppKit) | deployed; full API run incl. live model, override + reason, closed loop | [08](evidence/08_app_e2e.md) |
| Operate | Lakeflow Jobs + DABs | nightly job 7/7 cross-stage checks | [09](evidence/09_orchestration.md) |

## Design choices worth noting
- **Model/DS value vs Override value + Reason** is a first-class record: the app shows the model's value live, lets the
  manager check an override with the model before saving, and Postgres CHECK constraints refuse an override without a reason.
- **Price enters the model only via price-to-market, monotone-decreasing** → no learning "discounts slow sales" from the
  historic habit of discounting struggling cars. Validated against the simulator's hidden ground truth.
- **Guardrails** (max 8% per cut, $500 cap under 14 days, margin floor) are the pricing manager's — and in the backtest
  they *add* profit (+$80k vs +$70k unconstrained).
- **GenAI never invents numbers**: segment targeting is SQL; the LLM writes words; every figure is checked, ungrounded
  text is hidden.
- **ABAC functions are a single `is_member()` check** — no lookup tables (per-masked-column compile cost).
- **Least privilege:** app SP has UC SELECT + READ VOLUME; in Lakebase SELECT on serving, INSERT (no DELETE) on decisions.

## Known limitations (honest)
- Synthetic data; backtest proves method, not a forecast. The model is ~40% conservative on price sensitivity.
- Lakebase **synced tables** need the DB registered as a UC catalog (metastore `CREATE CATALOG`, not granted here) → a
  publish job performs the same snapshot; sources already have CDF for the production switch.
- Demo governance groups are workspace-local (no account admin) → ABAC via `is_member()`; production grants for SCIM
  account groups are in `governance/04_grants_account_groups.sql`.
- Genie is non-deterministic; the strict auto-scorer is reported verbatim alongside re-executed result comparisons.

## Run it
```bash
uv sync && uv run pytest                                   # unit tests
databricks bundle deploy -p <profile>                      # data, pipeline, ML, GenAI, Lakebase jobs
databricks bundle run generate_data -p <profile>           # synthetic DMS drops
databricks bundle run pricing_pipeline -p <profile>        # Lakeflow bronze → gold
governance/setup_identity.sh <profile> <you@company.com>   # groups + governed tags
uv run python scripts/run_sql.py governance/0[123]*.sql    # tags, ABAC, metric view
databricks bundle run train_pricing_model -p <profile>     # train, register, score, promote, backtest
databricks bundle run genai_rationale -p <profile>
# Lakebase: create project piag-pricing, then lakebase/01_schema.sql + Lakehouse Sync (lakebase/README.md)
cd app && databricks bundle deploy -p <profile> && databricks bundle run app -p <profile>
databricks bundle run end_to_end -p <profile>              # nightly orchestration
PIAG_E2E=1 uv run pytest                                   # workspace e2e (36 tests)
```
