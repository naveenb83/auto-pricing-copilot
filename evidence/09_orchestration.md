# Evidence 09 — One Lakeflow Job orchestrates the whole data journey

Job `piag-nightly-end-to-end` (schedule 02:00 Pacific/Honolulu, paused in the demo workspace): Lakeflow pipeline refresh → batch score with @champion → GenAI rationale → Lakebase publish → `verify_journey` health checks across every stage. Retraining is a separate job (`piag-train-pricing-model`, evidence 04) that promotes the endpoint when it finishes.

Job `piag-nightly-end-to-end` (job_id 652977737643614), run_id 316963850087596 — captured 2026-11-14T16:13Z via `databricks jobs get-run(-output)`.

```text
result_state : SUCCESS
start (UTC)  : 2026-11-14T16:05:47Z
end (UTC)    : 2026-11-14T16:12:52Z
task lakeflow_ingest              SUCCESS  2026-11-14T16:05:47Z -> 2026-11-14T16:07:10Z
task genai_rationale              SUCCESS  2026-11-14T16:08:06Z -> 2026-11-14T16:11:29Z
task lakebase_publish             SUCCESS  2026-11-14T16:11:30Z -> 2026-11-14T16:12:05Z
task score_with_champion          SUCCESS  2026-11-14T16:07:10Z -> 2026-11-14T16:08:05Z
task verify_journey               SUCCESS  2026-11-14T16:12:05Z -> 2026-11-14T16:12:52Z
```

### Task `verify_journey` stdout
```text
== Data journey health report
[PASS] every on-hand unit scored                     1411/1411
[PASS] endpoint serves @champion                     champion v3, served ['3']
[PASS] GenAI rationale grounded                      592/592
[PASS] rationale for every aged unit                 592/592
[PASS] Lakebase serving == UC gold                   inventory 1411/1411, recs 1411/1411
[PASS] Lakehouse Sync: decisions in UC == Lakebase   UC 2 / Lakebase 2
[PASS] Genie space reachable                         Pacific Isles Pricing Copilot — Ask the data
== KPIs: 1411 on hand, 279 aged 90+, $31,429/day holding cost
== SUMMARY {"checks": 7, "passed": 7, "failed": []}
```
