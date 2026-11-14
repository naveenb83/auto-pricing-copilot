# Evidence 04 — Pricing model: training, out-of-time validation, truth recovery, batch scoring, endpoint promotion, digital-twin backtest

Single serverless job, four tasks (train_register → batch_score, promote_endpoint, backtest_vs_flat_rule). Model: weekly sale-hazard HistGradientBoosting, monotone-decreasing in price-to-market, wrapped with an expected-profit optimiser (16-week horizon: floor-plan + lot + depreciation holding cost, auction/dealer-trade exit risk) and pricing-manager guardrails (max 8% cut, max $500 on units < 14 days).

Job `piag-train-pricing-model` (job_id 1077639647439960), run_id 326177653311750 — captured 2026-11-14T14:21Z via `databricks jobs get-run(-output)`.

```text
result_state : SUCCESS
start (UTC)  : 2026-11-14T14:11:11Z
end (UTC)    : 2026-11-14T14:20:11Z
task batch_score                  SUCCESS  2026-11-14T14:12:08Z -> 2026-11-14T14:13:30Z
task promote_endpoint             SUCCESS  2026-11-14T14:12:08Z -> 2026-11-14T14:20:11Z
task train_register               SUCCESS  2026-11-14T14:11:11Z -> 2026-11-14T14:12:08Z
task backtest_vs_flat_rule        SUCCESS  2026-11-14T14:12:08Z -> 2026-11-14T14:19:58Z
```

### Task `batch_score` stdout
```text
== Recommendation mix by aging bucket
              units  avg_model_discount  avg_flat_rule  uplift_vs_rule  share_hold_price  share_guardrail_applied
aging_bucket                                                                                                     
0-29            644               339.0            0.0         86015.0             0.585                    0.272
30-44           175               516.0            0.0         23165.0             0.577                    0.126
45-59           124               629.0           33.0         26312.0             0.476                    0.161
60-89           189               735.0           38.0         47049.0             0.354                    0.116
90+             279              1015.0           15.0         97406.0             0.262                    0.129
== Top 10 recommended cuts
stock_number      make      model  model_year  days_in_stock  current_price  price_to_market  recommended_discount  flat_rule_discount  expected_days_to_sell_now  expected_days_to_sell_recommended  uplift_vs_flat_rule
   R04-27175      Ford     Escape        2026             23        36055.0           1.0248                2500.0                 0.0                       65.8                               33.3               2882.0
   R02-27256       Kia        EV6        2025             20        38595.0           1.0434                3000.0                 0.0                       83.9                               53.6               2197.0
   R01-20774    Toyota    Corolla        2026            237        25600.0           1.0476                2000.0                 0.0                       85.8                               39.0               1773.0
   R01-27216    Toyota Highlander        2027             21        46595.0           1.0374                3000.0                 0.0                       62.9                               42.0               1617.0
   R03-24504      Ford     Escape        2023            117        19095.0           1.0521                1500.0                 0.0                       77.9                               37.6               1572.0
   R04-24698      Ford     Escape        2026            111        35105.0           1.0521                2500.0                 0.0                       75.7                               36.4               1556.0
   R06-25687       Kia        EV6        2024             76        31195.0           1.0218                2000.0                 0.0                       82.9                               53.6               1519.0
   R01-27212    Toyota    Corolla        2027             22        27920.0           1.0193                2000.0                 0.0                       58.4                               24.2               1442.0
   R02-25593 Chevrolet Equinox EV        2025             80        27595.0           1.0221                2000.0                 0.0                       76.3                               43.9               1435.0
   R04-27129      Ford   Explorer        2027             24        50745.0           1.0216                3000.0                 0.0                       59.4                               39.4               1398.0
== SUMMARY {"model_version": "3", "vehicles_scored": 1411, "recommend_hold_price": 677, "recommend_cut": 734, "guardrail_applied": 275, "aged45_units": 592, "aged45_model_total_discount": 500250.0, "aged45_flat_rule_total_discount": 15250.0, "expected_profit_uplift_vs_flat_rule_total": 279947.0, "mean_expected_days_now": 58.1, "mean_expected_days_recommended": 49.2}
```

### Task `promote_endpoint` stdout
```text
updating endpoint piag-pricing-model: v2 -> v3 (champion)
endpoint piag-pricing-model now serves v3
```

### Task `train_register` stdout
```text
== Data: 123,450 vehicle-weeks | train 101,292 (< 2026-08-01) | out-of-time test 22,158 (>= 2026-08-01) | weekly sale rate 0.1263




== Out-of-time performance (higher AUC / lower loss is better)
{
  "test_auc": 0.6465,
  "test_log_loss": 0.3511,
  "test_brier": 0.102,
  "naive_auc": 0.5455,
  "naive_log_loss": 0.364,
  "test_rows": 22158.0,
  "train_rows": 101292.0,
  "test_base_rate": 0.1193,
  "test_mean_pred": 0.1242,
  "n_iter": 80.0
}
== Calibration by predicted-probability decile (test)
     rows  predicted  actual
bin                         
0    2216     0.0454  0.0406
1    2216     0.0646  0.0636
2    2216     0.0792  0.0835
3    2215     0.0921  0.0894
4    2216     0.1046  0.1042
5    2216     0.1181  0.1218
6    2215     0.1333  0.1291
7    2216     0.1547  0.1417
8    2216     0.1859  0.1864
9    2216     0.2637  0.2329
== Permutation importance (AUC drop, test sample)
prev_vdp_views         0.0381
price_to_market        0.0355
model                  0.0133
age_days               0.0074
body_class             0.0029
market_days_supply     0.0020
exterior_colour        0.0015
mileage                0.0013
make                   0.0001
month                  0.0001
rooftop_id             0.0000
condition              0.0000
prev_test_drives      -0.0001
weeks_listed_before   -0.0002
vehicle_age_years     -0.0002
prev_leads            -0.0003
== Price-response recovery: % hazard change per 1% price cut (model vs hidden simulator truth)
             model_implied_elasticity  ground_truth_elasticity  ratio_model_to_truth
body_class                                                                          
compact_car                      9.14                     17.0                  0.54
compact_suv                      8.00                     13.0                  0.62
ev                               7.16                     19.0                  0.38
large_suv                        6.49                      9.0                  0.72
midsize_car                      8.88                     15.0                  0.59
midsize_suv                      7.29                     11.5                  0.63
minivan                          8.32                     12.0                  0.69
performance                      4.07                      8.0                  0.51
pickup                           5.72                     10.0                  0.57
   Spearman rank correlation model vs truth across body classes: 0.72
== Monotonicity check over price_to_market grid [1.1, 1.05, 1.0, 0.97, 0.94]: 0 violations across 6,000 vehicles
== Example served prediction (3 on-hand vehicles)
                 vin  recommended_discount  recommended_price  p_sell_30d_now  p_sell_30d_recommended  expected_days_to_sell_now  expected_days_to_sell_recommended  expected_profit_now  expected_profit_recommended  expected_profit_flat_rule  flat_rule_discount  uplift_vs_flat_rule  guardrail_applied  unconstrained_discount model_version
0  1FT01E755LR408907                 500.0            11595.0          0.3851                  0.5367                       53.7                               38.4               -637.0                       -395.0                     -637.0                 0.0                242.0               True                   750.0     candidate
1  1FT098434SL244905                1500.0            33295.0          0.3594                  0.4613                       56.9                               45.1                110.0                        111.0                      110.0                 0.0                  1.0              False                  1500.0     candidate
2  1FT0LVHH8PX832831                   0.0            22595.0          0.3058                  0.3058                       60.0                               60.0               1838.0                       1838.0                     1838.0                 0.0                  0.0              False                     0.0     candidate


  warnings.warn(
2026/11/14 14:12:00 WARNING mlflow.models.model: `artifact_path` is deprecated. Please use `name` instead.
🔗 View Logged Model at: https://fevm-serverless-stable-69fppe.cloud.databricks.com/ml/experiments/1259616973424337/models/m-4eeef63ee60e4c11bed4c6a59106e36d?o=7474651524368619
Registered model 'serverless_stable_69fppe_catalog.piag_pricing.aged_inventory_pricing_model' already exists. Creating a new version of this model...
🔗 Created version '3' of model 'serverless_stable_69fppe_catalog.piag_pricing.aged_inventory_pricing_model': https://fevm-serverless-stable-69fppe.cloud.databricks.com/explore/data/models/serverless_stable_69fppe_catalog/piag_pricing/aged_inventory_pricing_model/version/3?o=7474651524368619


== Registered serverless_stable_69fppe_catalog.piag_pricing.aged_inventory_pricing_model version 3 with alias @champion (run 8ca3a57ed70e4441974640aae50165fd)
== SUMMARY {"registered_model": "serverless_stable_69fppe_catalog.piag_pricing.aged_inventory_pricing_model", "version": "3", "run_id": "8ca3a57ed70e4441974640aae50165fd", "test_auc": 0.6465, "test_log_loss": 0.3511, "test_brier": 0.102, "naive_auc": 0.5455, "naive_log_loss": 0.364, "test_rows": 22158.0, "train_rows": 101292.0, "test_base_rate": 0.1193, "test_mean_pred": 0.1242, "n_iter": 80.0, "elasticity_rank_corr": 0.717, "monotonicity_violations": 0}
🏃 View run hazard_hgb_monotone at: https://fevm-serverless-stable-69fppe.cloud.databricks.com/ml/experiments/1259616973424337/runs/8ca3a57ed70e4441974640aae50165fd
🧪 View experiment at: https://fevm-serverless-stable-69fppe.cloud.databricks.com/ml/experiments/1259616973424337
```

### Task `backtest_vs_flat_rule` stdout
```text
== Digital twin: 1,411 on-hand vehicles as of 2026-11-13, 120-day horizon, 20 paired futures
== Mean outcome per policy over paired futures (USD / units)
policy             flat_rule  model_guardrails  model_unconstrained  guardrails_minus_rule  unconstrained_minus_rule
retail_units          1007.0            1194.0               1206.0                  188.0                     199.0
wholesale_exits        192.0              98.0                 91.0                  -94.0                    -101.0
unsold_at_day_120      213.0             119.0                114.0                  -94.0                     -99.0
aged90_day30           285.0             220.0                219.0                  -64.0                     -66.0
aged90_day60           291.0             186.0                183.0                 -105.0                    -108.0
aged90_day90           341.0             200.0                190.0                 -141.0                    -151.0
discount_given      212390.0         1401825.0            1498700.0              1189435.0                 1286310.0
carrying_cost       823761.0          642102.0             626393.0              -181659.0                 -197368.0
realised_gross     2796901.0         2511418.0            2478050.0              -285483.0                 -318851.0
terminal_value     -333988.0         -149891.0            -142911.0               184097.0                  191076.0
net_profit         1639152.0         1719425.0            1708745.0                80273.0                   69593.0
== model_guardrails: net-profit uplift vs flat rule $80,273 per 120 days (95% CI $46,828 .. $113,718); wins 17/20 paired futures
== model_unconstrained: net-profit uplift vs flat rule $69,593 per 120 days (95% CI $36,799 .. $102,386); wins 17/20 paired futures
== SUMMARY {"vehicles": 1411, "futures": 20, "horizon_days": 120, "guardrails": {"max_cut_pct": 0.08, "fresh_days": 14, "fresh_max_cut": 500}, "model_guardrails": {"net_profit": 1719425.0, "net_profit_uplift": 80273.0, "uplift_ci95": [46828.0, 113718.0], "wins": "17/20", "aged90_day60": 185.9, "aged90_day60_reduction_pct": 36.1, "carrying_cost_saved": 181659.0, "wholesale_exits_avoided": 93.6, "extra_discount_given": 1189435.0, "profit_per_extra_discount_dollar": 0.067}, "model_unconstrained": {"net_profit": 1708745.0, "net_profit_uplift": 69593.0, "uplift_ci95": [36799.0, 102386.0], "wins": "17/20", "aged90_day60": 183.1, "aged90_day60_reduction_pct": 37.1, "carrying_cost_saved": 197368.0, "wholesale_exits_avoided": 100.5, "extra_discount_given": 1286310.0, "profit_per_extra_discount_dollar": 0.054}, "flat_rule": {"net_profit": 1639152.0, "aged90_day60": 290.9}}
```
