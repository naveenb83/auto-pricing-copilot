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

Auto-scored **10/12**; after re-executing every non-GOOD answer and comparing result sets: **11/12 return the benchmark result**.

**#4 How many units were wholesaled at auction in the last 90 days before the business date?** — BAD; re-executed: **different result** — a genuine miss
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
**#7 What is the average days in stock of on-hand used vehicles?** — NEEDS_REVIEW; re-executed: **same result as the benchmark** (scorer difference only)
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

Tuning pass 1: added explicit date-window and sales-table instructions after the baseline miss on the ambiguous 'last 90 days' question. Benchmarks NOT edited.

## Tuning pass 1 — eval run `01f1e03c3a6a1249be4e7f5d8849eb9f`
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

Auto-scored **10/12**; after re-executing every non-GOOD answer and comparing result sets: **12/12 return the benchmark result**.

**#7 What is the average days in stock of on-hand used vehicles?** — NEEDS_REVIEW; re-executed: **same result as the benchmark** (scorer difference only)
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
**#9 What is the total expected profit uplift of the model over the flat rule across today's lot?** — BAD; re-executed: **same result as the benchmark** (scorer difference only)
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

Benchmark repair 1 (separate from tuning): wholesale answer SQL gained the upper bound `sale_date <= DATE'2026-11-13'` to match the space's date-window definition. No Genie instructions changed.

## Benchmark repair 1 — eval run `01f1e03d71f61f2789cd6f8d4ce56e3f`
**9/12 correct**, 0 needs review.

| # | Benchmark question | Assessment | Reasons |
|---|---|---|---|
| 1 | How many on-hand units are 90 or more days old? | GOOD | - |
| 2 | How many on-hand units does the model recommend holding price on? | GOOD | - |
| 3 | How many retail units were sold in October 2026? | GOOD | - |
| 4 | How many units were wholesaled at auction in the last 90 days before the business date? | BAD | SINGLE_CELL_DIFFERENCE, LLM_JUDGE_MISSING_OR_INCORRECT_FILTER |
| 5 | How many vehicles are on hand today? | GOOD | - |
| 6 | In the backtest, what was the average net profit for each policy? | GOOD | - |
| 7 | What is the average days in stock of on-hand used vehicles? | BAD | SINGLE_CELL_DIFFERENCE, LLM_JUDGE_INCORRECT_METRIC_CALCULATION |
| 8 | What is the total daily holding cost of all on-hand inventory? | GOOD | - |
| 9 | What is the total expected profit uplift of the model over the flat rule across today's lot? | BAD | COLUMN_TYPE_DIFFERENCE, SINGLE_CELL_DIFFERENCE, LLM_JUDGE_OTHER |
| 10 | Which make has the most aged 90+ day units on hand? | GOOD | - |
| 11 | Which rooftop has the highest share of units aged 90+ days? | GOOD | - |
| 12 | Which segment is the best target for minivan promotions? | GOOD | - |

Auto-scored **9/12**; after re-executing every non-GOOD answer and comparing result sets: **10/12 return the benchmark result**.

**#4 How many units were wholesaled at auction in the last 90 days before the business date?** — BAD; re-executed: **different result** — a genuine miss
Benchmark SQL:
```sql
SELECT count(*) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_sales_enriched WHERE channel = 'wholesale' AND sale_date > DATE'2026-11-13' - INTERVAL 90 DAYS AND sale_date <= DATE'2026-11-13'
```
Genie SQL:
```sql
SELECT COUNT(*) AS `wholesale_units_at_auction`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_sales_enriched`
WHERE `gold_sales_enriched`.`sale_date` >= DATE'2026-08-15'
  AND `gold_sales_enriched`.`sale_date` <= DATE'2026-11-12'
  AND `gold_sales_enriched`.`channel` = 'wholesale'
```
**#7 What is the average days in stock of on-hand used vehicles?** — BAD; re-executed: **different result** — a genuine miss
Benchmark SQL:
```sql
SELECT round(avg(days_in_stock), 1) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current WHERE condition = 'used'
```
Genie SQL:
```sql
SELECT ROUND(AVG(`days_in_stock`), 0) AS `avg_days_in_stock`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_inventory_current`
WHERE `condition` ILIKE '%used%'
  AND `days_in_stock` IS NOT NULL
```
**#9 What is the total expected profit uplift of the model over the flat rule across today's lot?** — BAD; re-executed: **same result as the benchmark** (scorer difference only)
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

Benchmark repair 2: the wholesale question said 'before the business date', which Genie reasonably read as exclusive; reworded to 'in the 90 days up to and including the business date'. No Genie instructions changed.

## Benchmark repair 2 — eval run `01f1e03e29551866a72a9c155a51564d`
**10/12 correct**, 0 needs review.

| # | Benchmark question | Assessment | Reasons |
|---|---|---|---|
| 1 | How many on-hand units are 90 or more days old? | GOOD | - |
| 2 | How many on-hand units does the model recommend holding price on? | GOOD | - |
| 3 | How many retail units were sold in October 2026? | GOOD | - |
| 4 | How many units were wholesaled at auction in the 90 days up to and including the business date? | GOOD | - |
| 5 | How many vehicles are on hand today? | GOOD | - |
| 6 | In the backtest, what was the average net profit for each policy? | GOOD | - |
| 7 | What is the average days in stock of on-hand used vehicles? | BAD | SINGLE_CELL_DIFFERENCE, LLM_JUDGE_MISSING_OR_INCORRECT_FILTER |
| 8 | What is the total daily holding cost of all on-hand inventory? | GOOD | - |
| 9 | What is the total expected profit uplift of the model over the flat rule across today's lot? | BAD | COLUMN_TYPE_DIFFERENCE, SINGLE_CELL_DIFFERENCE, LLM_JUDGE_OTHER |
| 10 | Which make has the most aged 90+ day units on hand? | GOOD | - |
| 11 | Which rooftop has the highest share of units aged 90+ days? | GOOD | - |
| 12 | Which segment is the best target for minivan promotions? | GOOD | - |

Auto-scored **10/12**; after re-executing every non-GOOD answer and comparing result sets: **11/12 return the benchmark result**.

**#7 What is the average days in stock of on-hand used vehicles?** — BAD; re-executed: **different result** — a genuine miss
Benchmark SQL:
```sql
SELECT round(avg(days_in_stock), 1) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current WHERE condition = 'used'
```
Genie SQL:
```sql
SELECT ROUND(AVG(`days_in_stock`), 0) AS `avg_days_in_stock`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_inventory_current`
WHERE `condition` ILIKE '%used%'
  AND `days_in_stock` IS NOT NULL
```
**#9 What is the total expected profit uplift of the model over the flat rule across today's lot?** — BAD; re-executed: **same result as the benchmark** (scorer difference only)
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

Tuning pass 2: Genie rounded an average of days to a whole number; instruction now says averages of days are shown to one decimal place. Benchmarks NOT edited.

## Tuning pass 2 — eval run `01f1e03e7bc0118496bfae498a672ee1`
**10/12 correct**, 1 needs review.

| # | Benchmark question | Assessment | Reasons |
|---|---|---|---|
| 1 | How many on-hand units are 90 or more days old? | GOOD | - |
| 2 | How many on-hand units does the model recommend holding price on? | GOOD | - |
| 3 | How many retail units were sold in October 2026? | GOOD | - |
| 4 | How many units were wholesaled at auction in the 90 days up to and including the business date? | GOOD | - |
| 5 | How many vehicles are on hand today? | GOOD | - |
| 6 | In the backtest, what was the average net profit for each policy? | GOOD | - |
| 7 | What is the average days in stock of on-hand used vehicles? | NEEDS_REVIEW | LLM_JUDGE_MISSING_OR_INCORRECT_FILTER |
| 8 | What is the total daily holding cost of all on-hand inventory? | GOOD | - |
| 9 | What is the total expected profit uplift of the model over the flat rule across today's lot? | BAD | COLUMN_TYPE_DIFFERENCE, SINGLE_CELL_DIFFERENCE, LLM_JUDGE_INCORRECT_FUNCTION_USAGE |
| 10 | Which make has the most aged 90+ day units on hand? | GOOD | - |
| 11 | Which rooftop has the highest share of units aged 90+ days? | GOOD | - |
| 12 | Which segment is the best target for minivan promotions? | GOOD | - |

Auto-scored **10/12**; after re-executing every non-GOOD answer and comparing result sets: **12/12 return the benchmark result**.

**#7 What is the average days in stock of on-hand used vehicles?** — NEEDS_REVIEW; re-executed: **same result as the benchmark** (scorer difference only)
Benchmark SQL:
```sql
SELECT round(avg(days_in_stock), 1) FROM serverless_stable_69fppe_catalog.piag_pricing.gold_inventory_current WHERE condition = 'used'
```
Genie SQL:
```sql
SELECT AVG(`days_in_stock`) AS `avg_days_in_stock`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`gold_inventory_current`
WHERE `condition` IS NOT NULL
  AND `condition` ILIKE '%used%'
  AND `days_in_stock` IS NOT NULL
```
**#9 What is the total expected profit uplift of the model over the flat rule across today's lot?** — BAD; re-executed: **same result as the benchmark** (scorer difference only)
Benchmark SQL:
```sql
SELECT round(sum(uplift_vs_flat_rule), 0) FROM serverless_stable_69fppe_catalog.piag_pricing.pricing_recommendations
```
Genie SQL:
```sql
SELECT CAST(COALESCE(ROUND(SUM(`uplift_vs_flat_rule`), 0), 0) AS BIGINT) AS `total_expected_profit_uplift_usd`
FROM `serverless_stable_69fppe_catalog`.`piag_pricing`.`pricing_recommendations`
```

## Summary across passes
| Pass | Eval run | Result-set matches after re-execution |
|---|---|---|
| Baseline | `01f1e03bb87a1784b8bd69078e4e2c6f` | 11/12 |
| Tuning pass 1 | `01f1e03c3a6a1249be4e7f5d8849eb9f` | 12/12 |
| Benchmark repair 1 | `01f1e03d71f61f2789cd6f8d4ce56e3f` | 10/12 |
| Benchmark repair 2 | `01f1e03e29551866a72a9c155a51564d` | 11/12 |
| Tuning pass 2 | `01f1e03e7bc0118496bfae498a672ee1` | 12/12 |

Genie is non-deterministic: the same space can phrase SQL differently run to run (types, rounding, boundaries). Each pass made ONE change and was re-evaluated; the strict auto-scorer is reported verbatim above.
