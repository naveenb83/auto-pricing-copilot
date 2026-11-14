# Evidence 05 — GenAI layer (AI Functions `ai_query`, Claude Haiku 5.5) with automatic grounding check

Serverless job `piag-genai-rationale`. Segment targeting is deterministic SQL over campaign responses; the LLM only writes the words. Every number in each rationale/promo is checked against the model facts (vehicle names stripped first) — ungrounded rows are flagged and hidden in the app. Iterations (all in this PR): v1 93.4% grounded (false positives from 'CX-90' / 'Ioniq 5'), v2 fixed names + prompt, v3 added the $500-cut counterfactual and margin-floor fact so 'hold price' explanations are truthful.

Job `piag-genai-rationale` (job_id 685652084999455), run_id 948257620685704 — captured 2026-11-14T14:46Z via `databricks jobs get-run(-output)`.

```text
result_state : SUCCESS
start (UTC)  : 2026-11-14T14:43:00Z
end (UTC)    : 2026-11-14T14:46:28Z
task rationale                    SUCCESS  2026-11-14T14:43:00Z -> 2026-11-14T14:46:28Z
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
  WHY: The Mazda3 has sat in stock for 115 days and is priced at 1.02 times market, so a $250 cut to $24,340 is recommended. That cut is expected to bring the sale forward from 55 to 52 days and matches the flat-rule discount, with no change in profit versus that rule.
  PROMO: Your First New Mazda3 Just Got Easier — Buying your first car? The new Mazda3 Base is now $250 off. Stop by for a test drive and see how simple it can be.
- R01-26054 | target value_retiree (then young_family)
  WHY: We recommend holding the price at $39,645 because a $500 cut would only shorten the expected 74 days to 73, saving about $32 in holding cost per day, while the discount would reduce profit by $42. The unit has been in stock 64 days and is priced at 1.052 times market, but the cut is still not expected to pay for itself.
  PROMO: Relaxed, Reliable Mazda CX-90 for Retirement Years — Relaxed, reliable Mazda SUV ready for your next chapter. Visit our dealership to test drive today and enjoy a comfortable, confident ride.
- R01-21211 | target value_retiree (then young_family)
  WHY: A $500 cut would shorten the expected sale from 60 to 54 days, but that faster sale is only worth about $63 in extra profit, so a cut is not expected to pay for itself and the recommended discount is $0. Because a cut would also take the deal below the group's minimum-margin floor, it would help only a little, so this unit needs another exit plan such as a dealer trade or wholesale review.
  PROMO: Relaxed Comfort: 2026 Mazda CX-90 Base — Hello from your local Mazda team: the CX-90 is ready for a relaxed, comfortable drive. Visit us for a no-pressure test drive this week.
- R01-24816 | target first_time_buyer (then value_retiree)
  WHY: The 2026 Mazda3 Base has sat in stock for 106 days and is priced at 1.02 times market, with holding costs of $21 per day. A $500 cut to $24,205 is expected to shorten the expected sale from 58 to 50 days and add $114 in profit compared with the flat rule.
  PROMO: Mazda3 Base: Your First New Car — Your first new Mazda is $500 off today. Test drive the Base trim and see how easy buying can be. Reply YES to book.
- R01-22366 | target value_retiree (then young_family)
  WHY: This new 2026 CX-90 has sat 188 days and is priced at 1.052 times the market, so a $3,000 cut to $35,295 is expected to shorten time-to-sale from 85 to 68 days and add $46 in profit versus the flat rule. Holding costs run $33 per day, so the faster sale is worth more than the discount's drag on this unit.
  PROMO: 2026 Mazda CX-90 Base: Now $3,000 Off — Hi! The Mazda CX-90 Base is now $3,000 off, offering reliable comfort and easy driving. Stop by for a test drive today.
== SUMMARY {"rationales": 592, "parse_failures": 0, "grounded": 592, "grounded_pct": 100.0, "llm": "databricks-claude-haiku-5-5"}
```
