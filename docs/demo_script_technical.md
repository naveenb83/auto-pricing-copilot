# Demo script — technical stakeholder (Head of Data / Platform / DS lead)

**Goal:** show that the solution is one governed, production-shaped data journey on Databricks, and that the model is
sound. **Time:** 15 minutes. Have the repo, the workspace and the app open.

## 1. Architecture in one breath (deck slide 8, 1 min)
DMS weekly drops → **Lakeflow Declarative Pipeline** (Auto Loader, expectations) → **Unity Catalog** gold + ABAC +
metric view → **MLflow** model in UC → **Model Serving** (real time) + **AI Functions** (GenAI) → **Lakebase** serving +
decisions → **Lakehouse Sync** back to UC → **Genie Agent** + **Databricks App** (AppKit). One **Lakeflow Job** runs it nightly.

## 2. Ingest + quality (2 min) — `pipelines/pricing/`, evidence/02
- 8 bronze streaming tables (Auto Loader); silver MVs dedupe and enforce expectations; 6 gold MVs.
- Show the event-log evidence: incremental ingestion (377,835 → 0 → 3,733 rows) and expectations catching every injected
  defect. Design call worth mentioning: a $0 sale price is **warn + null**, not drop — dropping made 31 sold cars look on hand.

## 3. Governance (3 min) — `governance/`, evidence/03
- Governed tags `piag_sensitivity` (financial/pii) and `piag_scope` (rooftop); **three schema-level ABAC policies**, so new
  tables are protected by tagging, not by code.
- Policy functions are a single `is_member()` check — no lookup tables (lookup-table masks multiply compile time per masked column).
- Show the two-lens evidence: 17,862 → 2,940 rows, costs NULL, PII masked; lineage bronze → metric view.
- Honest limitation: demo groups are workspace-local; production uses SCIM account groups (`04_grants_account_groups.sql`).

## 4. The model (4 min) — `ml/`, evidence/04, 04b
- **Problem framing:** discrete-time hazard — P(sell this week | state). Price enters only via price-to-market with a
  **monotone constraint**, so the model can't learn "discounts cause slow sales" from historic discounting habits.
- **Decision layer:** expected-profit optimiser over a 16-week horizon (floor-plan + lot + depreciation, auction/dealer-trade
  exit), inside business guardrails.
- **Validation:** out-of-time AUC 0.647 vs 0.546 naive, calibrated by decile, 0 monotonicity violations, **recovers the
  simulator's hidden elasticity ranking (0.72)** but ~40% conservative (noisy comps → attenuation; safe direction).
- **Proof of value:** digital-twin A/B with common random numbers — +$80k / 120 days, CI +$47k..+$114k, 17/20 wins.
- **Serving:** pyfunc (model + optimiser) on Model Serving with an AI Gateway inference table; the retrain job promotes the
  endpoint to `@champion`; nightly scoring never creates versions.
- Live: in the app, open a unit → `/api/recommend` → ~0.3 s warm. Features are read **server-side from Lakebase**, never
  trusted from the browser.

## 5. GenAI with a grounding check (1 min) — `ml/genai_rationale.py`, evidence/05
`ai_query` (Claude Haiku 5.5) writes the rationale + SMS; segment targeting is deterministic SQL. Every number the LLM
writes is checked against the facts (592/592 pass); ungrounded text is never shown. Gotchas: newer Claude models reject
`responseFormat` → JSON-in-text + parse; reasoning tokens need max_tokens ≈ 2,500.

## 6. Lakebase + closed loop (2 min) — `lakebase/`, evidence/06, 08
- `serving.*` published from gold with an atomic swap (synced tables are the production path; they need the DB
  registered as a UC catalog, not granted in this workspace).
- `pricing_ops.pricing_decisions`: **CHECK constraints** enforce override ⇒ value + reason. App SP can INSERT, not DELETE.
- **Lakehouse Sync** CDC lands every change in `lb_pricing_decisions_history`; a UC view rebuilds current state for Genie.
  Show decision #1006 arriving in UC.

## 7. Genie (1 min) — `genie/`, evidence/07
Curated agent (9 tables + metric view, instructions, verified examples). Native benchmark: 5 passes, one change each,
non-GOOD answers re-executed and compared → 12/12 result-set matches. In the app Genie runs **on-behalf-of the user**,
so ABAC applies per person.

## 8. Operate it (1 min) — `resources/orchestration.yml`, evidence/09
`piag-nightly-end-to-end`: ingest → score → GenAI → publish → `verify_journey` (7 cross-stage checks, 7/7 PASS). Everything
is a Declarative Automation Bundle; `PIAG_E2E=1 uv run pytest` runs 36 tests including workspace e2e per stage.

## Likely questions
| Question | Answer |
|---|---|
| Why not a price-elasticity regression? | We need *time to sell* under any price to trade discount against holding cost; a hazard model gives the full survival curve, and the monotone constraint keeps it causal-ish. |
| Confounding — managers discount slow cars | Price only enters as price-to-market, monotone; discount-to-date is excluded. The backtest on hidden ground truth is the check. |
| Cold starts on the endpoint? | Scale-to-zero in the demo (first call ~30 s, then ~0.3 s). Production: min provisioned concurrency; the app falls back to the batch score. |
| Why Lakebase and not query the warehouse? | Sub-second lookups and OLTP writes with constraints for the pricing queue; analytics (KPIs, Genie) stay on the warehouse. |
| How does the model learn from overrides? | Decisions land in UC via Lakehouse Sync with reason codes; the retrain job can use outcome-joined overrides as features or as a policy-evaluation set. |
| Drift / monitoring? | Inference table on the endpoint + nightly `verify_journey`; next step is Lakehouse Monitoring on scores vs realised sales. |
