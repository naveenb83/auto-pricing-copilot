"""Shared pricing logic: model features + the expected-profit discount optimiser.

Used by training (ml/train.py), the MLflow pyfunc served in real time (ml/pyfunc_model.py) and the
digital-twin backtest (ml/backtest.py), so the app, batch scores and backtest all price identically.

Model: discrete-time hazard — P(vehicle sells at retail during the next week | state). Price enters
ONLY through price_to_market with a monotone-decreasing constraint, so "a lower price never lowers the
chance of selling" holds by construction and discounts are not confounded with the historic habit
of discounting units that were already struggling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

CATEGORICAL = ["condition", "body_class", "make", "model", "exterior_colour", "rooftop_id"]
NUMERIC = ["price_to_market", "age_days", "vehicle_age_years", "mileage", "month", "market_days_supply",
           "prev_vdp_views", "prev_leads", "prev_test_drives", "weeks_listed_before"]
FEATURES = NUMERIC + CATEGORICAL
MONOTONIC = {"price_to_market": -1}
LABEL = "sold_retail_this_week"

DISCOUNT_GRID = [0, 250, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000]
HORIZON_WEEKS = 16
FI_GROSS = 1350.0          # expected back-end gross on a retail sale
WHOLESALE_RECOVERY = 0.90  # used units unsold at the horizon exit at auction ~90% of market
NEW_EXIT_RECOVERY = 0.96   # new units unsold at the horizon: dealer trade / deep clearance
MIN_FRONT_GROSS = -1500.0  # never recommend a price this far below cost
# Business guardrails owned by the pricing manager (shown in the app; the model optimises inside them)
GUARDRAILS = {"max_cut_pct": 0.08,   # no single cut above 8% of the current price
              "fresh_days": 14,      # units younger than this ...
              "fresh_max_cut": 500}  # ... get at most a $500 cut


def to_frame(rows: pd.DataFrame) -> pd.DataFrame:
    """Coerce feature dtypes exactly as at training time."""
    X = rows[FEATURES].copy()
    for c in NUMERIC:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype("float64")
    for c in CATEGORICAL:
        X[c] = X[c].astype("string").fillna("unknown")
    return X


@dataclass
class VehicleState:
    """What the optimiser needs to know about one on-hand vehicle right now."""
    current_price: float
    unit_cost: float
    market_price: float
    daily_market_depreciation: float
    daily_holding_cost: float
    condition: str
    flat_rule_additional_discount: float
    features: dict  # FEATURES at decision time (price_to_market recomputed per candidate)


def _horizon_rows(state: VehicleState, discounts: list[float]) -> list[dict]:
    rows = []
    for d in discounts:
        price = state.current_price - d
        for k in range(HORIZON_WEEKS):
            f = dict(state.features)
            mk = max(1000.0, state.market_price - state.daily_market_depreciation * 7 * k)
            f["price_to_market"] = price / mk
            f["age_days"] = float(f["age_days"]) + 7 * k
            f["weeks_listed_before"] = float(f.get("weeks_listed_before") or 0) + k
            f["month"] = ((int(f["month"]) - 1 + (k * 7) // 30) % 12) + 1
            rows.append(f)
    return rows


def _curve(state: VehicleState, discounts: list[float], p: np.ndarray) -> list[dict]:
    out = []
    hold_week = state.daily_holding_cost * 7
    mk_end = max(1000.0, state.market_price - state.daily_market_depreciation * 7 * HORIZON_WEEKS)
    recovery = WHOLESALE_RECOVERY if state.condition == "used" else NEW_EXIT_RECOVERY
    for i, d in enumerate(discounts):
        price = state.current_price - d
        surv, exp_profit, exp_weeks, p_sell, p4 = 1.0, 0.0, 0.0, 0.0, 0.0
        for k in range(HORIZON_WEEKS):
            sell = surv * p[i, k]
            exp_profit += sell * (price - state.unit_cost + FI_GROSS - hold_week * (k + 0.5))
            exp_weeks += sell * (k + 0.5)
            p_sell += sell
            surv *= 1 - p[i, k]
            if k == 3:
                p4 = p_sell
        exp_profit += surv * (recovery * mk_end - state.unit_cost - hold_week * HORIZON_WEEKS)
        exp_weeks += surv * HORIZON_WEEKS
        out.append({
            "discount": float(d), "price": float(price),
            "p_sell_30d": round(float(p4), 4), "p_sell_16w": round(float(p_sell), 4),
            "expected_days_to_sell": round(float(exp_weeks * 7), 1),
            "expected_profit": round(float(exp_profit), 0),
            "front_gross_at_price": round(float(price - state.unit_cost), 0),
        })
    return out


def evaluate_batch(model, states: list[VehicleState], discounts: list[list[float]]) -> list[list[dict]]:
    """Expected outcome per candidate discount for MANY vehicles with a single model call."""
    rows, sizes = [], []
    for st, ds in zip(states, discounts):
        r = _horizon_rows(st, ds)
        rows.extend(r)
        sizes.append(len(ds))
    if not rows:
        return []
    p = model.predict_proba(to_frame(pd.DataFrame(rows)))[:, 1]
    out, i = [], 0
    for st, ds, n in zip(states, discounts, sizes):
        block = p[i: i + n * HORIZON_WEEKS].reshape(n, HORIZON_WEEKS)
        i += n * HORIZON_WEEKS
        out.append(_curve(st, ds, block))
    return out


def evaluate(model, state: VehicleState, discounts: list[float] | None = None) -> list[dict]:
    """Expected outcome for each candidate additional discount over a 16-week horizon."""
    return evaluate_batch(model, [state], [list(discounts if discounts is not None else DISCOUNT_GRID)])[0]


def _allowed(state: VehicleState, c: dict, guardrails: dict | None) -> bool:
    if c["front_gross_at_price"] < MIN_FRONT_GROSS:
        return False
    if not guardrails:
        return True
    if c["discount"] > guardrails["max_cut_pct"] * state.current_price:
        return False
    if float(state.features.get("age_days", 0)) < guardrails["fresh_days"] and c["discount"] > guardrails["fresh_max_cut"]:
        return False
    return True


def _pick(state: VehicleState, curve: list[dict], guardrails: dict | None = GUARDRAILS) -> dict:
    feasible = [c for c in curve if _allowed(state, c, guardrails)] or curve[:1]
    best = max(feasible, key=lambda c: c["expected_profit"])
    unconstrained = max([c for c in curve if _allowed(state, c, None)] or curve[:1], key=lambda c: c["expected_profit"])
    by_d = {c["discount"]: c for c in curve}
    now = by_d[0.0]
    rule = by_d[float(state.flat_rule_additional_discount)]
    return {
        "recommended_discount": best["discount"],
        "recommended_price": best["price"],
        "p_sell_30d_now": now["p_sell_30d"], "p_sell_30d_recommended": best["p_sell_30d"],
        "expected_days_to_sell_now": now["expected_days_to_sell"],
        "expected_days_to_sell_recommended": best["expected_days_to_sell"],
        "expected_profit_now": now["expected_profit"], "expected_profit_recommended": best["expected_profit"],
        "expected_profit_flat_rule": rule["expected_profit"],
        "flat_rule_discount": float(state.flat_rule_additional_discount),
        "uplift_vs_flat_rule": round(best["expected_profit"] - rule["expected_profit"], 0),
        "guardrail_applied": bool(unconstrained["discount"] != best["discount"]),
        "unconstrained_discount": unconstrained["discount"],
        "curve_json": json.dumps([c for c in curve if c["discount"] in DISCOUNT_GRID]),
    }


def _grid(state: VehicleState) -> list[float]:
    return sorted({float(d) for d in DISCOUNT_GRID} | {float(state.flat_rule_additional_discount)})


def recommend_batch(model, states: list[VehicleState], guardrails: dict | None = GUARDRAILS) -> list[dict]:
    """Best discount by expected profit (incl. future holding cost and exit risk) for many vehicles,
    within the pricing manager's guardrails (pass guardrails=None for the unconstrained optimum)."""
    grids = [_grid(s) for s in states]
    return [_pick(s, c, guardrails) for s, c in zip(states, evaluate_batch(model, states, grids))]


def recommend(model, state: VehicleState, guardrails: dict | None = GUARDRAILS) -> dict:
    return recommend_batch(model, [state], guardrails)[0]


def state_from_inventory_row(r: dict, month: int | None = None) -> VehicleState:
    """Build a VehicleState from a gold_inventory_current / Lakebase row."""
    f = {
        "price_to_market": float(r["current_price"]) / float(r["market_price"]),
        "age_days": float(r["days_in_stock"]),
        "vehicle_age_years": float(max(0, int(str(r.get("as_of_date", "2026-11-13"))[:4]) - int(r["model_year"]))),
        "mileage": float(r["mileage"]),
        "month": month or int(str(r.get("as_of_date", "2026-11-13"))[5:7]),
        "market_days_supply": float(r.get("market_days_supply") or 60),
        "prev_vdp_views": float(r.get("vdp_views_last_week") or 0),
        "prev_leads": float(r.get("leads_last_week") or 0),
        "prev_test_drives": float(r.get("test_drives_last_week") or 0),
        "weeks_listed_before": float(r.get("weeks_listed") or 0),
        "condition": r["condition"], "body_class": r["body_class"], "make": r["make"], "model": r["model"],
        "exterior_colour": r["exterior_colour"], "rooftop_id": r["rooftop_id"],
    }
    return VehicleState(
        current_price=float(r["current_price"]), unit_cost=float(r["unit_cost"]),
        market_price=float(r["market_price"]), daily_market_depreciation=float(r.get("daily_market_depreciation") or 0),
        daily_holding_cost=float(r["daily_holding_cost"]), condition=r["condition"],
        flat_rule_additional_discount=float(r.get("flat_rule_additional_discount") or 0), features=f)


def feature_frame_for_training(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    return to_frame(df), df[LABEL].astype(int).to_numpy()
