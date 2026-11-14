# BUILD PLAN — Aged-Inventory Pricing Copilot (FE Bar submission)

Resume file. Read this first if the session restarts.

## Context
- Purpose: FE Bar build (Product / Industry / Build+AI Mindset / Customer Skills). Re-build of a problem
  discovered at a customer AI dev day — **no customer names, data, URLs or people in the repo**.
- Fictional customer: **Pacific Isles Auto Group (PIAG)** — 6 rooftops, multi-brand new + used.
- Problem: aged units burn floor-plan interest + depreciation; discounting is a flat gut-feel rule
  ($250 at 45–89 days, $500 at 90+). Goal: cut 90+ day stock 30% and floor-plan cost without lowering gross/unit.
- Workspace: `DEFAULT` profile = https://fevm-serverless-stable-69fppe.cloud.databricks.com
  - Catalog `serverless_stable_69fppe_catalog`, schema **`piag_pricing`**, volume `landing` (raw drops), volume `media` (car photos)
  - Warehouse `8b226d8722ba3ab2` (Serverless Starter)
  - Lakebase Autoscaling project **`piag-pricing`**
- Repo: **github.com/naveenb83/auto-pricing-copilot** (gh account `naveenb83`; PRIVATE during build → PUBLIC at end after scrub + user OK)
- Local dir: `~/projects/auto-pricing-copilot`
- Workflow: PR per chunk → tests green → self-merge → Naveen final review at end.
- As-of date for the simulation: **2026-11-13** (`DEMO_NOW`).

## Architecture
```
generator (serverless job) → /Volumes/.../landing/{entity}/dt=YYYY-MM-DD/*.csv|json
  → Lakeflow Declarative Pipeline (Auto Loader, expectations) bronze → silver → gold
  → UC: comments, tags, column mask (unit_cost, gross), row filter (rooftop), metric view, lineage
  → ML: weekly sale-hazard model (sklearn HGB, monotone in discount) + profit optimiser,
        MLflow → UC model registry → Model Serving endpoint `piag-pricing-model` (REAL-TIME)
        + batch scoring → gold.pricing_recommendations ; backtest vs flat rule
  → GenAI: ai_query rationale + segment pitch per aged unit
  → Lakebase: synced tables (inventory_current, pricing_recommendations) ; app-owned pricing_decisions
        → write-back job lands decisions into Delta (closed loop)
  → Genie Agent over gold + metric view (instructions, trusted SQL, benchmarks)
  → Databricks App (AppKit): Overview · Pricing queue · Vehicle detail (photo, LIVE model call,
        Model/DS value vs Override value + Reason) · Decisions & impact · Ask Genie
  → One Lakeflow Job orchestrates end to end; everything in a DAB
```

## Data model (synthetic, ground truth embedded)
- rooftops (6), vehicles (~9k acquired over 18 months, ~1.8k on hand), price_changes, sales,
  customers (~25k, 5 segments), leads_web (VDP views/leads/test drives), promotions, promo_responses,
  floorplan_rates, market_comps; vehicle_images (model → Wikimedia CC photo + attribution).
- Truth: daily sale hazard = f(model popularity, price-to-market, age, season, demand signals,
  segment fit) × discount elasticity (varies by segment/class). Historical managers discount with
  noise (identifiable elasticity). Used units wholesaled at a loss if unsold by ~120 days.
- Holding cost/day = floor-plan APR × unit cost / 365 + depreciation + lot cost.

## Car photos
- One CC-licensed (PD / CC0 / CC BY / CC BY-SA) Wikimedia Commons photo per make+model, stored in
  UC volume `media`; manifest table `vehicle_images` with author, licence, source URL; app shows credit.

## PRs (sequential backbone unless noted)
| # | PR | Evidence committed |
|---|----|--------------------|
| 1 | Scaffold + plan + synthetic generator + photos fetch | generator job run log, row counts, photo manifest |
| 2 | Lakeflow pipeline bronze/silver/gold | pipeline event log: rows + expectation metrics; incremental run |
| 3 | UC governance + metric view | DESCRIBE, masked vs unmasked results, lineage query |
| 4 | ML train + register + backtest + serving endpoint + batch score | metrics, backtest vs rule ($), endpoint query JSON |
| 5 | GenAI rationale + segment response | sample outputs |
| 6 | Lakebase project, synced tables, decisions table, write-back job | psql outputs, round-trip counts |
| 7 | Genie Agent | Q&A transcript + benchmark results |
| 8 | App (AppKit) | API curl outputs, deploy log, app status |
| 9 | Orchestration job + e2e run + evidence index | job run JSON |
| 10 | Deck (PDF + md) + demo scripts (business + technical) + README | deck |

## Status log
- 2026-11-14: plan agreed with Naveen (full ML optimiser scope; real-time model call with Model/DS value,
  Override value, Reason; realistic car photos).
