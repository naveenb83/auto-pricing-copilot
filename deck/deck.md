# Aged-Inventory Pricing Copilot — Pacific Isles Auto Group (deck, text export)

_Text export of deck.pdf (10 slides). Pacific Isles Auto Group is fictional; all figures are from synthetic data and a digital-twin backtest._

---

## Slide 1

PACIFIC ISLES AUTO GROUP · AGED-INVENTORY PRICING
Stop paying to keep cars.
Price every aged unit to sell — and protect
the profit.
A pricing copilot that tells your pricing managers which units to cut, by how much and who to target —
in seconds — and learns from every override.
+$80k                                                                          −36%                                −94
net profit per 120 days on today's lot                                         units aged 90+ days (day 60)        auction exits avoided
Illustrative: Pacific Isles Auto Group is fictional; all figures from synthetic data and a digital-twin backtest                           Built on Databricks

---

## Slide 2

THE PROBLEM, IN YOUR NUMBERS
279 units are 90+ days old. Keeping them costs $7,625 a day — $229k a month.
1,411                                                      19.8%                                  $31.4k                                          $704k
units on hand, 6 rooftops                                  aged 90+ days                          holding cost per day, whole lot                 lost on 384 auction exits
592 are 45+ days old                                       avg 148 days in stock · target < 12%   floor-plan interest + lot cost + depreciation   last 12 months · −$1,833 per unit
· $943k / month
Today's policy is a flat rule                                                                     What it costs the business
$250 off at 45 days, $500 off at 90 days — the same for a hot SUV                                Every day an aged unit sits: ~$27 of floor-plan, lot and depreciation
and a slow EV                                                                                    cost
Discounts are a judgement call, made unit by unit, and the reasons                               Past ~120 days used units go to auction at a loss
are not recorded                                                                                 Over-discounting fast movers gives away gross that did not need
Most aged units already had their $250/$500 — the rule now                                       to go
adds $0 while they keep burning cash
Source: governed KPIs (Unity Catalog metric view) · business date 13 Nov 2026 · synthetic data                                                                                           2

---

## Slide 3

THE OUTCOME
Replayed against today's lot, model pricing earns $80k more in 120 days and cuts
90+ day stock by a third
Policy (same 1,411 units, same buyers, 20 simulated futures)                                      Net profit (120 days)            Aged 90+ at day 60        Carrying cost       Auction exits       Retail units
Flat rule ($250 @ 45 d / $500 @ 90 d)                                                                       $1,639,152                                 291      $823,761                   192            1,007
Pricing copilot (model + your guardrails)                                                                   $1,719,425                                 186      $642,102                        98        1,194
Model without guardrails                                                                                    $1,708,745                                 183      $626,393                        91        1,206
+$80,273                                                   −36%                                                      −$182k                                           +188
net profit vs flat rule                                    units aged 90+ (291 → 186)                                carrying cost                                    more retail deliveries
95% CI +$46.8k … +$113.7k · copilot wins                   at day 60                                                 floor-plan interest + lot cost                   94 fewer auction exits
17 of 20 futures
How: the copilot spends discount where it buys speed (393 aged units get a cut, avg $845) and holds price where it does not (199 aged units). Guardrails make it better, not just safer (+$80k vs +$70k
unconstrained). Annualised ≈ $240k for this lot — validate in a pilot before quoting.
Digital-twin A/B: today's lot replayed 120 days under the simulator's hidden buyer behaviour, common random numbers · synthetic                                                                                       3

---

## Slide 4

VALUE FOR EACH STAKEHOLDER
One decision, two wins: the CFO protects profit, the pricing manager moves units
faster
Executive sponsor · Dealer Principal / CFO                                                Domain owner · Used / New Car & Pricing Managers
Net profit +$80k per 120 days on today's lot (≈ $240k/yr                                 Days to turn: expected 58 → 49 days across the lot; aged units
illustrative)                                                                            sell weeks sooner
Floor-plan + lot cost −$182k per 120 days                                                Seconds per decision: open a unit → live recommended
Auction losses ~94 fewer exits (−$1,833 each historically)                               discount, chance to sell in 30 days, profit curve
Aged-inventory ratio 19.8% → on track for the < 12% target                               Your call stays yours: override with a value and a reason; the
model shows what your override is worth first
Control: guardrails you set (max 8% cut, $500 cap on fresh units,
margin floor); cost and gross visible only to finance                                    Who to target: best-responding customer segment + a draft SMS
for every aged unit
Ask anything in plain English — answers come with the SQL that
produced them
KPIs: net profit, carrying cost, auction losses, aged-90+ share, days to turn, gross per unit                                                                     4

---

## Slide 5

A DAY IN THE LIFE OF A PRICING MANAGER
See what's aging → get the Model/DS value → accept or override with a reason
Pricing queue: every 45+ day unit, Model/DS value vs flat rule, expected gain, decision status     Vehicle: live Model/DS value; override value + reason, checked against the model before saving
Live app on Databricks Apps · photos: Wikimedia Commons (CC BY / BY-SA), representative of model                                                                                                    5

---

## Slide 6

ONE UNIT, END TO END
2026 Corolla, 237 days, $25,600: the flat rule adds $0. The copilot says cut $2,000.
15% → 55%                                                                       86 → 39 days                                              +$1,773
chance to sell in 30 days                                                       expected days to sell                                     expected profit vs the flat rule
at today's price → after the cut                                                $25/day holding cost stops 7 weeks sooner                 answer in ~0.3 s from the live model
"Why", written for the manager (AI, every number checked)                                                        Who to target + draft message
"This new 2026 Toyota Corolla Limited has been in stock 237 days                                                 First-time buyers respond 2.4× better to compact-car offers. "First
and is priced 4.8% above market, so a $2,000 cut to $23,600 is                                                   car? The Toyota Corolla Limited is now $2,000 off. Come see a new
recommended. The cut is expected to shorten time to sale from about                                              car built for your first road trips. Book a test drive today."
86 days to 39 and earn about $1,773 more than the flat-rule
approach."
Override example recorded in the app: manager cut $1,000 instead of $1,500 ("customer already negotiating") — the model showed the override was worth $548 less before it was saved.
Real outputs from the deployed model endpoint and AI Functions on synthetic data                                                                                                          6

---

## Slide 7

TRUST AND CONTROL
The model advises, your people decide — and every decision is governed and
auditable
Guardrails you own                                                             Explainable, not a black box                 Governed data
No single cut above 8% of price                                              A lower price can never lower the            Unit cost and gross hidden unless you're
Max $500 on units under 14 days                                              predicted chance of selling (enforced in     in finance
the model)                                   Rooftop managers see only their rooftop
Never more than $1,500 below cost
Every AI sentence is number-checked          Customer contact details masked
Overrides above 15% need group sign-
against the model — 592/592 passed
off                                                                                                                       Every override + reason lands in the
Answers from "Ask the data" show their       governed lakehouse within seconds
SQL
The learning loop: override reasons (e.g. "reconditioning not finished", "manufacturer incentive") become training signal and a weekly report — the copilot
gets better where your managers know something it does not.
Unity Catalog ABAC policies · Lakebase + Lakehouse Sync · MLflow model registry                                                                                             7

---

## Slide 8

HOW IT WORKS (FOR THE TECHNICAL STAKEHOLDER)
One integrated data journey on Databricks — no copies, no silos
Lakeflow                                         Unity Catalog                              ML + Gen AI                              Lakebase                                 Genie + App
Weekly DMS drops → Auto                          Tag-based ABAC masks +                     Sale-hazard model + profit               Postgres serving copy for the            Genie Agent (on-behalf-of
Loader → bronze/silver/gold                      rooftop row filter, KPI metric             optimiser (MLflow, UC                    app; decisions written here;             user) and a Databricks App
with data-quality
→        view, lineage
→       registry) on Model Serving; AI
→      Lakehouse Sync streams
→       for the pricing team
expectations; incremental                                                                   Functions for grounded                   them back
rationale
Model quality (out-of-time)                                                  Operations                                                         Genie quality
AUC 0.647 vs 0.546 naive · calibrated by decile · recovers                   One nightly Lakeflow Job: ingest → score → AI → publish            12-question benchmark, 5 tuning passes, final 12/12
hidden price sensitivity (rank-corr 0.72) · 0 monotonicity                   → 7 cross-stage checks (7/7 pass) · retraining separate,           answers match the benchmark result sets
violations                                                                   auto-promotes the endpoint
Evidence for every stage is committed as text in the repo (evidence/)                                                                                                                                        8

---

## Slide 9

NEXT STEP
A 6-week pilot on two rooftops, measured against the flat rule
Pilot design                                                                    Success measures (agreed up front)
Weeks 1–2: connect the live inventory ledger (days in stock, unit              Aged 90+ share down ≥ 25% vs control rooftops
cost) and floor-plan rates; retrain on your history                            Floor-plan + lot cost per unit down; auction exits down
Weeks 3–6: two rooftops use the copilot, two stay on the flat rule             Front + F&I gross per retail unit held within ±3%
(matched by brand and stock age)
≥ 80% of aged units get a recorded decision within 48 hours
Weekly review of overrides and reasons with the pricing managers
What we need from you: read access to the inventory ledger with days-in-stock and unit cost; a named owner for floor-plan and margin policy to confirm
the guardrails and discount tiers; two pricing managers for weekly feedback.
Decision today: approve the pilot scope and nominate the policy owner                                                                                       9

---

## Slide 10

APPENDIX · ASSUMPTIONS AND CAVEATS
What these numbers are — and are not
Synthetic data. Pacific Isles Auto Group is fictional. The simulator embeds realistic dealer dynamics (floor-plan APR 7.1–7.9%, lot cost $6/day,
market depreciation, model-year rollover, auction exits at ~120 days, historic flat-rule discounting with noise).
Backtest. The digital twin replays today's lot for 120 days under the simulator's hidden buyer behaviour; both policies see identical buyers (common
random numbers). It is evidence of method, not a forecast for a real dealership.
Model is conservative. It under-estimates price sensitivity by ~40% (noisy market comps) — the safe direction; real elasticities are estimated in the
pilot.
Discount spend rises. The copilot gives ~$1.2M more discount over 120 days in the twin, recovered through lower carrying cost, fewer auction
losses and more retail gross — hence net profit, not discount, is the KPI.
Governance demo. Masks and filters run on workspace groups in the demo; production uses account-level groups synced from your identity
provider.
Photos are openly licensed Wikimedia Commons images, representative of each model.
Repo: github.com/naveenb83/auto-pricing-copilot · evidence/README.md maps every figure to its run                                                          10
