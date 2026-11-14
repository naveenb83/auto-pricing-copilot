# Evidence 05 — GenAI layer (AI Functions `ai_query`, Claude Haiku 5.5) with automatic grounding check

Serverless job `piag-genai-rationale`. Segment targeting is deterministic SQL over campaign responses; the LLM only writes the words. Every number in each rationale/promo is checked against the model facts (vehicle names stripped first) — ungrounded rows are flagged and hidden in the app. Iterations (all in this PR): v1 93.4% grounded (false positives from 'CX-90' / 'Ioniq 5'), v2 fixed names + prompt, v3 added the $500-cut counterfactual and margin-floor fact so 'hold price' explanations are truthful.

Job `piag-genai-rationale` (job_id 685652084999455), run_id 788827240099379 — captured 2026-11-14T14:38Z via `databricks jobs get-run(-output)`.

```text
result_state : SUCCESS
start (UTC)  : 2026-11-14T14:34:49Z
end (UTC)    : 2026-11-14T14:38:07Z
task rationale                    SUCCESS  2026-11-14T14:34:49Z -> 2026-11-14T14:38:06Z
```

### Task `rationale` stdout
```text
== Segment targeting: top 2 responsive segments per body class
 body_class  segment_rank          segment  sends  leads_per_1000_sends  lift_vs_body_class_avg  offer_sensitivity
compact_car             1 first_time_buyer    818                 18.34                    2.42                NaN
compact_car             2    value_retiree    773                  7.76                    1.02                NaN
compact_suv             1     young_family   1913                 14.11                    1.45               1.01
compact_suv             2    value_retiree   1669                 10.78                    1.11               1.21
         ev             1 active_lifestyle    703                 14.22                    1.92               0.00
         ev             2 first_time_buyer    918                 10.89                    1.47               1.17
  large_suv             1    value_retiree    752                  7.98                    1.37               4.16
  large_suv             2     young_family    917                  7.63                    1.31               0.36
midsize_car             1    value_retiree   1202                 13.31                    2.43               1.17
midsize_car             2 active_lifestyle    973                  6.17                    1.12               1.79
midsize_suv             1     young_family   2224                 11.24                    1.73               1.34
midsize_suv             2 trades_and_fleet   1047                  6.69                    1.03               2.49
    minivan             1     young_family   2335                 26.98                    2.65               2.49
    minivan             2 active_lifestyle   1669                  5.39                    0.53               4.53
performance             1 active_lifestyle   1113                 23.36                    3.03               2.27
performance             2    value_retiree   1307                  7.65                    0.99               1.43
     pickup             1 trades_and_fleet   1141                 28.05                    3.18               1.98
     pickup             2 active_lifestyle   1725                 11.01                    1.25               0.49
== Generated 592 rationales with databricks-claude-haiku-5-5: parse failures 0, grounded 592/592 (100.0%)
== 5 examples
- R01-24544 | target first_time_buyer (then value_retiree)
  WHY: The Mazda3 has been in stock 115 days and is priced at 102.3% of market, so a $250 cut from $24,590 to $24,340 is recommended. That cut is expected to shorten time to sell from 55 to 52 days and matches the flat-rule discount with no profit difference, while a $500 cut would only reduce it to 49 days and lower profit by $14.
  PROMO: Mazda3 Base: Smart First Car Pick — Starting your first car? The new Mazda3 Base is now $250 off. Come test drive one today and see why it's a smart first choice.
- R01-26054 | target value_retiree (then young_family)
  WHY: The new Mazda CX-90 has sat in stock 64 days and is priced about 5.2% above market, but a $500 cut would only shorten the expected sale from 74 to 73 days and change profit by -$42, so a cut is not expected to pay for itself. Holding the current $39,645 price is expected to earn $28 more than the flat $250 discount rule.
  PROMO: Relaxed Ride: Mazda CX-90 Base — Enjoy a smooth, comfortable drive in Mazda's new SUV. Stop by for a test drive and see how easy it is to enjoy the road.
- R01-21211 | target value_retiree (then young_family)
  WHY: The Base CX-90 has been in stock 223 days, costing $32 a day to hold, and a $500 cut would only shorten the expected sale from 60 to 54 days, adding about $63 in profit, so the cut is not expected to pay for itself. A cut would help a little but would take the deal below the group's minimum-margin floor, so this unit needs another exit plan, such as a dealer trade or wholesale review.
  PROMO: 2026 Mazda CX-90 Base: Comfortable Value Today — Looking for a comfortable, easy-to-drive SUV? Our new Mazda SUV is ready for a relaxed test drive. Stop by this week and see how easy it is to drive.
- R01-24816 | target first_time_buyer (then value_retiree)
  WHY: The Mazda3 has sat in stock for 106 days and is priced at 1.02 times market, so a $500 cut to $24205 is expected to shorten the expected sale from 58 to 50 days. That faster sale is worth about $114 more in profit than the flat rule, so we recommend the cut.
  PROMO: Mazda3 Base: Your Affordable First New Car — First-time buyer? Take $500 off the new Mazda3 Base today. Visit us for a test drive and see how affordable your first new car can be.
- R01-22366 | target value_retiree (then young_family)
  WHY: The 2026 Mazda CX-90 Base has sat 188 days and is priced about 5% above market, costing roughly $33 a day to hold. A $3,000 cut to $35,295 is expected to shorten time to sale from 85 to 68 days and add about $46 in profit versus the flat-rule price.
  PROMO: 2026 Mazda CX-90 Base, Now $3,000 Off — Enjoy $3,000 off a brand-new Mazda SUV at our dealership today. Comfortable, capable and ready for your next chapter. Stop by for a no-pressure test drive!
== SUMMARY {"rationales": 592, "parse_failures": 0, "grounded": 592, "grounded_pct": 100.0, "llm": "databricks-claude-haiku-5-5"}
```
