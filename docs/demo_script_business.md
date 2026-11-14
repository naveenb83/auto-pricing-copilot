# Demo script — business stakeholder (Dealer Principal / CFO, with the Used-Car Manager)

**Goal of the meeting:** agree a 6-week, two-rooftop pilot. **Time:** 12 minutes + questions.
**Open:** https://piag-pricing-copilot-7474651524368619.aws.databricksapps.com (warm the model by opening one vehicle 5 min before).

## 1. Start with their money (Overview, 2 min)
> "Right now 279 units — about one in five — have been on the lot more than 90 days. Keeping them costs **$7,625 a day,
> roughly $229,000 a month** in floor-plan interest, lot cost and depreciation. Last year 384 units went to auction at an
> average loss of $1,833. Today's policy is the flat $250 / $500 rule — and for most of these cars the rule has already
> been applied, so it now adds **nothing** while they keep burning cash."

Point at the four KPI tiles and the 26-week trend (aged share drifting up from ~15% to ~20%).

## 2. The outcome (Overview → backtest table, 2 min)
> "We replayed **today's exact lot** for 120 days, twenty times, with the same buyers walking in under both policies.
> Pricing each car individually earned **$80,000 more net profit** in 120 days, cut 90+ day stock by **a third**, and
> avoided about **94 auction exits**. And notice the guardrails your team sets don't cost money — they *add* it: $80k
> with guardrails vs $70k without."

## 3. A day in the life (Pricing queue → one vehicle, 5 min) — talk to the Used-Car Manager
- Queue: "Every aged unit, biggest expected gain first. The shield means your guardrail capped the cut."
- Open **R01-20774, 2026 Corolla, 237 days**: "The model answers live: cut **$2,000** — chance of selling in 30 days goes
  from 15% to 55%, expected time to sell from 86 to 39 days. The flat rule would do nothing."
- Read the **Why** panel aloud — "plain English, and every number in it is checked against the model."
- Show **who to target**: first-time buyers respond 2.4× better to compact-car offers; draft SMS ready to send.
- **Override:** choose *Override*, type **$1,000**, reason *Reconditioning / photos not finished yet*, click
  **Check my override with the model** → "Before you save, it tells you what your call is worth versus its own. You stay
  in charge; it just makes the trade-off visible." Save.
- Decisions & impact: "Every decision and reason is recorded. Your override reasons become next month's improvements."

## 4. Ask anything (Ask the data, 1 min)
Click *"How many units are aged 90+ days at each rooftop and what do they cost us per day?"* → "Answer plus the SQL that
produced it. It runs with *your* permissions — a rooftop manager only sees their rooftop; cost and gross only show for finance."

## 5. The ask (deck slide 9, 2 min)
> "Six weeks, two rooftops on the copilot, two on the flat rule. We measure aged-90+ share, carrying cost per unit and
> auction exits, and hold gross per unit within ±3%. We need read access to the inventory ledger with days in stock and
> unit cost, and one owner for floor-plan and margin policy to confirm the guardrails."

## Likely questions — short answers
| Question | Answer |
|---|---|
| "Isn't this just discounting more?" | It discounts **where it buys speed** and holds where it doesn't (199 aged units: hold). Discount spend goes up; net profit goes up more because carrying cost and auction losses fall. Net profit is the KPI, not discount. |
| "Will it give away margin on hot units?" | Guardrails: max 8% per cut, max $500 on units under 14 days, never more than $1,500 below cost, overrides above 15% need sign-off. The model also *holds* price on units that will sell anyway. |
| "Can my managers ignore it?" | Yes — override with a value and a reason. The tool shows what the override is worth first. Reasons are reported weekly. |
| "Are these your numbers or ours?" | Synthetic, built to behave like a multi-rooftop group. That's why the next step is a pilot on your ledger, measured against control rooftops. |
| "Who sees cost and gross?" | Only finance / margin viewers. Rooftop managers see their own rooftop. Customer contact details are masked. |
| "How long to go live?" | Pilot data connection in 2 weeks; the components already exist on your Databricks platform. |
