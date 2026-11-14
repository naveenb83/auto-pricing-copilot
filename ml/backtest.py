"""Digital-twin A/B backtest: replay TODAY's real lot forward 120 days under the simulator's hidden
ground-truth buyer behaviour, once with the flat $250/$500 rule and once with the model, using common
random numbers (same buyer arrivals in both arms) across many simulated futures.

Policies
  flat_rule : total discount >= $250 once a unit reaches 45 days and >= $500 at 90 days (100% compliance)
  model     : every Monday re-price every unit to the @champion model's recommended additional cut
Outcome per arm: retail units, wholesale exits, aged 90+ units at day 30/60, discount given, carrying
cost, realised gross, terminal value of unsold stock, and NET PROFIT (the KPI the CFO cares about).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())

from pricing_core import GUARDRAILS, recommend_batch, state_from_inventory_row  # noqa: E402

AS_OF = date(2026, 11, 13)
DAYS = 120
LOT_COST = 6.0
APR = 0.0710
FI = 1350.0
SEASON = {1: 0.85, 2: 0.90, 3: 1.10, 4: 1.12, 5: 1.08, 6: 1.02, 7: 1.00, 8: 1.00, 9: 0.94, 10: 0.97,
          11: 1.03, 12: 1.15}
COLOUR = {"White": 1.0, "Black": 1.0, "Silver": 0.98, "Grey": 1.0, "Blue": 0.95, "Red": 0.93, "Green": 0.82,
          "Orange": 0.78, "Brown": 0.75}


def simulate(lot: pd.DataFrame, policy: str, model, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = len(lot)
    U_sell = rng.random((DAYS, n))       # common random numbers: identical across policies for a seed
    U_exit = rng.random((DAYS, n))
    neg = rng.normal(0.006, 0.006, n).clip(0)
    price = lot["current_price"].to_numpy(float).copy()
    list0 = lot["initial_list_price"].to_numpy(float)
    cost = lot["unit_cost"].to_numpy(float)
    age0 = lot["days_in_stock"].to_numpy(int)
    used = (lot["condition"] == "used").to_numpy()
    on = np.ones(n, bool)
    gross = carry = discount_given = 0.0
    retail = wholesale = 0
    aged90 = {}
    rows = lot.to_dict("records")
    for t in range(1, DAYS + 1):
        d = AS_OF + timedelta(days=t)
        age = age0 + t
        mv = lot["market0"].to_numpy() * (1 + lot["drift_eff"].to_numpy()) ** (age)
        # ---- pricing policy
        if policy == "flat_rule":
            disc = list0 - price
            target = np.where(age >= 90, 500.0, np.where(age >= 45, 250.0, 0.0))
            cut = np.clip(target - disc, 0, None) * on
            price -= cut
            discount_given += cut.sum()
        elif policy.startswith("model") and d.weekday() == 0:
            idx = np.where(on)[0]
            states = []
            for i in idx:
                r = dict(rows[i])
                r.update(current_price=price[i], market_price=mv[i], days_in_stock=age[i],
                         as_of_date=d.isoformat(), weeks_listed=float(r["weeks_listed"]) + t / 7,
                         flat_rule_additional_discount=0.0)
                states.append(state_from_inventory_row(r))
            recs = recommend_batch(model, states, GUARDRAILS if policy == "model_guardrails" else None)
            cut = np.array([x["recommended_discount"] for x in recs])
            price[idx] -= cut
            discount_given += cut.sum()
        # ---- ground-truth daily sale hazard (identical to the simulator)
        gap = (price - mv) / mv
        h = (lot["base_hazard"].to_numpy() * lot["colour_f"].to_numpy() * SEASON[d.month] * lot["appeal"].to_numpy()
             * np.exp(-lot["elasticity"].to_numpy() * gap) * np.exp(-0.002 * np.minimum(age, 240))
             * np.where(used, 1.10, 1.0) * (0.55 if d.weekday() == 6 else 1.05))
        p = 1 - np.exp(-np.minimum(h, 0.30))
        sold = on & (U_sell[t - 1] < p)
        gross += ((price * (1 - neg) - cost + FI) * sold).sum()
        retail += int(sold.sum())
        on &= ~sold
        ex_used = on & used & (age >= 120) & (U_exit[t - 1] < 0.035)
        ex_new = on & ~used & (age >= 240) & (U_exit[t - 1] < 0.012)
        gross += ((0.895 * mv - cost) * ex_used).sum() + ((0.985 * cost - cost) * ex_new).sum()
        wholesale += int(ex_used.sum() + ex_new.sum())
        on &= ~(ex_used | ex_new)
        carry += ((cost * APR / 365 + LOT_COST) * on).sum()
        if t in (30, 60, 90):
            aged90[t] = int((on & (age >= 90)).sum())
    mv_end = lot["market0"].to_numpy() * (1 + lot["drift_eff"].to_numpy()) ** (age0 + DAYS)
    terminal = (np.where(used, 0.90, 0.96) * mv_end - cost)[on].sum()
    return {"retail_units": retail, "wholesale_exits": wholesale, "unsold_at_day_120": int(on.sum()),
            "aged90_day30": aged90[30], "aged90_day60": aged90[60], "aged90_day90": aged90[90],
            "discount_given": discount_given, "carrying_cost": carry, "realised_gross": gross,
            "terminal_value": terminal, "net_profit": gross - carry + terminal}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--volume_root", required=True)
    ap.add_argument("--seeds", type=int, default=20)
    a, _ = ap.parse_known_args()
    fq = f"{a.catalog}.{a.schema}"
    import mlflow
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    mlflow.set_registry_uri("databricks-uc")
    model = mlflow.pyfunc.load_model(f"models:/{fq}.aged_inventory_pricing_model@champion").unwrap_python_model().model

    inv = spark.table(f"{fq}.gold_inventory_current").toPandas()
    inv["as_of_date"] = inv["as_of_date"].astype(str)
    truth = pd.read_csv(os.path.join(a.volume_root, "landing", "_truth", "vehicle_truth.csv"))
    lot = inv.merge(truth[["vin", "appeal", "elasticity", "base_hazard", "daily_market_drift",
                           "market_value_at_acquisition"]], on="vin")
    # effective daily drift incl. prior-model-year rollover for new units (as in the simulator)
    rollover = (lot["condition"] == "new") & (lot["model_year"] < 2027)
    lot["drift_eff"] = lot["daily_market_drift"] - np.where(rollover, 0.00035, 0.0)
    lot["market0"] = lot["market_value_at_acquisition"]  # exact hidden market value, as in the simulator
    lot["colour_f"] = lot["exterior_colour"].map(COLOUR).fillna(1.0)
    print(f"== Digital twin: {len(lot):,} on-hand vehicles as of {AS_OF}, {DAYS}-day horizon, {a.seeds} paired futures")

    res = []
    for s in range(a.seeds):
        for pol in ("flat_rule", "model_guardrails", "model_unconstrained"):
            res.append({"seed": s, "policy": pol, **simulate(lot, pol, model, 1000 + s)})
    df = pd.DataFrame(res)
    mean = df.groupby("policy").mean(numeric_only=True).drop(columns="seed").T
    mean["guardrails_minus_rule"] = mean["model_guardrails"] - mean["flat_rule"]
    mean["unconstrained_minus_rule"] = mean["model_unconstrained"] - mean["flat_rule"]
    print("== Mean outcome per policy over paired futures (USD / units)")
    print(mean.round(0).to_string())
    paired = df.pivot(index="seed", columns="policy", values="net_profit")
    summary = {"vehicles": int(len(lot)), "futures": a.seeds, "horizon_days": DAYS, "guardrails": GUARDRAILS}
    for pol in ("model_guardrails", "model_unconstrained"):
        diff = paired[pol] - paired["flat_rule"]
        se = diff.std(ddof=1) / math.sqrt(len(diff))
        wins = int((diff > 0).sum())
        lo, hi = diff.mean() - 1.96 * se, diff.mean() + 1.96 * se
        print(f"== {pol}: net-profit uplift vs flat rule ${diff.mean():,.0f} per 120 days "
              f"(95% CI ${lo:,.0f} .. ${hi:,.0f}); wins {wins}/{len(diff)} paired futures")
        extra_disc = mean.loc["discount_given", pol] - mean.loc["discount_given", "flat_rule"]
        summary[pol] = {
            "net_profit": round(float(mean.loc["net_profit", pol]), 0),
            "net_profit_uplift": round(float(diff.mean()), 0), "uplift_ci95": [round(float(lo), 0), round(float(hi), 0)],
            "wins": f"{wins}/{len(diff)}",
            "aged90_day60": round(float(mean.loc["aged90_day60", pol]), 1),
            "aged90_day60_reduction_pct": round(100 * (1 - mean.loc["aged90_day60", pol] / mean.loc["aged90_day60", "flat_rule"]), 1),
            "carrying_cost_saved": round(float(mean.loc["carrying_cost", "flat_rule"] - mean.loc["carrying_cost", pol]), 0),
            "wholesale_exits_avoided": round(float(mean.loc["wholesale_exits", "flat_rule"] - mean.loc["wholesale_exits", pol]), 1),
            "extra_discount_given": round(float(extra_disc), 0),
            "profit_per_extra_discount_dollar": round(float(diff.mean() / extra_disc), 3) if extra_disc else None,
        }
    summary["flat_rule"] = {"net_profit": round(float(mean.loc["net_profit", "flat_rule"]), 0),
                            "aged90_day60": round(float(mean.loc["aged90_day60", "flat_rule"]), 1)}
    out = spark.createDataFrame(df)
    out.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.backtest_policy_results")
    spark.sql(f"COMMENT ON TABLE {fq}.backtest_policy_results IS 'Digital-twin A/B: today''s lot replayed 120 days "
              f"under hidden ground-truth demand, flat \\$250/\\$500 rule vs model pricing, one row per policy x future.'")
    print("== SUMMARY " + json.dumps(summary))


if __name__ == "__main__":
    main()
