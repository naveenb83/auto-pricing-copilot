# Evidence 07 — Genie Agent benchmark evaluation (native Genie eval runs)

Space `01f1e03bafe91748918dbc276f3cfd90` ("Pacific Isles Pricing Copilot — Ask the data"): 9 tables + metric view `piag_pricing_kpis`, text instructions, 4 verified example SQLs, 12 benchmark questions with answer SQL verified against the warehouse before the run (`genie/build_space.py`).

## Baseline — eval run `01f1e03bb87a1784b8bd69078e4e2c6f`
**10/12 correct**, 1 needs review.

| # | Benchmark question | Assessment | Reasons |
|---|---|---|---|
| 1 | How many on-hand units are 90 or more days old? | GOOD | - |
| 2 | How many on-hand units does the model recommend holding price on? | GOOD | - |
| 3 | How many retail units were sold in October 2026? | GOOD | - |
| 4 | How many units were wholesaled at auction in the last 90 days before the business date? | BAD | SINGLE_CELL_DIFFERENCE, LLM_JUDGE_INCORRECT_TABLE_OR_FIELD_USAGE |
| 5 | How many vehicles are on hand today? | GOOD | - |
| 6 | In the backtest, what was the average net profit for each policy? | GOOD | - |
| 7 | What is the average days in stock of on-hand used vehicles? | NEEDS_REVIEW | LLM_JUDGE_MISSING_OR_INCORRECT_FILTER |
| 8 | What is the total daily holding cost of all on-hand inventory? | GOOD | - |
| 9 | What is the total expected profit uplift of the model over the flat rule across today's lot? | GOOD | - |
| 10 | Which make has the most aged 90+ day units on hand? | GOOD | - |
| 11 | Which rooftop has the highest share of units aged 90+ days? | GOOD | - |
| 12 | Which segment is the best target for minivan promotions? | GOOD | - |

**#4 How many units were wholesaled at auction in the last 90 days before the business date?** — BAD
Benchmark SQL:
```sql
SELECT count(*) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_sales_enriched WHERE channel = 'wholesale' AND sale_date > DATE'2026-11-13' - INTERVAL 90 DAYS
```
Genie SQL:
```sql
SELECT COUNT(*) AS `wholesale_units`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_vehicle_status`
WHERE `disposed_date` BETWEEN date_sub(DATE '2026-11-13', 90) AND date_sub(DATE '2026-11-13', 1)
  AND `disposed_date` IS NOT NULL
  AND `status` ILIKE '%wholesale%'
```
**#7 What is the average days in stock of on-hand used vehicles?** — NEEDS_REVIEW
Benchmark SQL:
```sql
SELECT round(avg(days_in_stock), 1) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current WHERE condition = 'used'
```
Genie SQL:
```sql
SELECT AVG(`days_in_stock`) AS `avg_days_in_stock`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_inventory_current`
WHERE `condition` ILIKE '%used%'
  AND `days_in_stock` IS NOT NULL
```

Tuning pass 1 (one focused change): added explicit date-window and sales-table instructions after the baseline miss on the ambiguous 'last 90 days before the business date' question. Benchmarks were NOT edited.

## After tuning pass 1 — eval run `01f1e03c3a6a1249be4e7f5d8849eb9f`
**10/12 correct**, 1 needs review.

| # | Benchmark question | Assessment | Reasons |
|---|---|---|---|
| 1 | How many on-hand units are 90 or more days old? | GOOD | - |
| 2 | How many on-hand units does the model recommend holding price on? | GOOD | - |
| 3 | How many retail units were sold in October 2026? | GOOD | - |
| 4 | How many units were wholesaled at auction in the last 90 days before the business date? | GOOD | - |
| 5 | How many vehicles are on hand today? | GOOD | - |
| 6 | In the backtest, what was the average net profit for each policy? | GOOD | - |
| 7 | What is the average days in stock of on-hand used vehicles? | NEEDS_REVIEW | LLM_JUDGE_MISSING_OR_INCORRECT_FILTER |
| 8 | What is the total daily holding cost of all on-hand inventory? | GOOD | - |
| 9 | What is the total expected profit uplift of the model over the flat rule across today's lot? | BAD | COLUMN_TYPE_DIFFERENCE, SINGLE_CELL_DIFFERENCE, LLM_JUDGE_OTHER |
| 10 | Which make has the most aged 90+ day units on hand? | GOOD | - |
| 11 | Which rooftop has the highest share of units aged 90+ days? | GOOD | - |
| 12 | Which segment is the best target for minivan promotions? | GOOD | - |

**#7 What is the average days in stock of on-hand used vehicles?** — NEEDS_REVIEW
Benchmark SQL:
```sql
SELECT round(avg(days_in_stock), 1) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current WHERE condition = 'used'
```
Genie SQL:
```sql
SELECT AVG(`days_in_stock`) AS `avg_days_in_stock`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_inventory_current`
WHERE `condition` IS NOT NULL
  AND `days_in_stock` IS NOT NULL
  AND `condition` ILIKE '%used%'
```
**#9 What is the total expected profit uplift of the model over the flat rule across today's lot?** — BAD
Benchmark SQL:
```sql
SELECT round(sum(uplift_vs_flat_rule), 0) FROM serverless_stable_69fppe_catalog.piag_pricing.pricing_recommendations
```
Genie SQL:
```sql
SELECT CAST(ROUND(SUM(`uplift_vs_flat_rule`), 0) AS BIGINT) AS `total_expected_profit_uplift_usd`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`pricing_recommendations`
WHERE `uplift_vs_flat_rule` IS NOT NULL
```

### Manual review of the non-GOOD results
Both remaining non-GOOD answers return the same value as the benchmark: #9 is identical but cast to BIGINT (scorer flags COLUMN_TYPE_DIFFERENCE), #7 is the same average unrounded with an equivalent ILIKE filter. Result: **10/12 by the strict auto-scorer, 12/12 semantically correct on review.** The baseline miss on the ambiguous date-window question was fixed by tuning pass 1.
