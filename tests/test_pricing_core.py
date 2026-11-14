"""Unit tests for the expected-profit optimiser with a transparent stand-in hazard model."""
import json

import numpy as np

from ml.pricing_core import DISCOUNT_GRID, VehicleState, evaluate, recommend


class FakeHazard:
    """Weekly sale probability falls steeply with price-to-market (elasticity `e`)."""
    def __init__(self, base=0.12, e=15.0):
        self.base, self.e = base, e

    def predict_proba(self, X):
        h = self.base * np.exp(-self.e * (X["price_to_market"].to_numpy() - 1.0))
        p = 1 - np.exp(-h)
        return np.column_stack([1 - p, p])


def state(price=30000, cost=27000, market=29000, hold=25.0, cond="used", rule=250.0):
    feats = {"price_to_market": price / market, "age_days": 70.0, "vehicle_age_years": 3.0, "mileage": 36000.0,
             "month": 11, "market_days_supply": 60.0, "prev_vdp_views": 40.0, "prev_leads": 1.0,
             "prev_test_drives": 0.0, "weeks_listed_before": 10.0, "condition": cond, "body_class": "compact_suv",
             "make": "Toyota", "model": "RAV4", "exterior_colour": "White", "rooftop_id": "R01"}
    return VehicleState(price, cost, market, 12.0, hold, cond, rule, feats)


def test_more_discount_sells_faster():
    curve = evaluate(FakeHazard(), state())
    days = [c["expected_days_to_sell"] for c in curve]
    p30 = [c["p_sell_30d"] for c in curve]
    assert days == sorted(days, reverse=True) and p30 == sorted(p30)


def test_overpriced_aged_unit_gets_a_bigger_cut_than_flat_rule():
    r = recommend(FakeHazard(), state(price=31500, market=29000))  # 8.6% over market
    assert r["recommended_discount"] > r["flat_rule_discount"]
    assert r["expected_profit_recommended"] >= r["expected_profit_flat_rule"]
    assert r["uplift_vs_flat_rule"] >= 0


def test_well_priced_hot_unit_needs_no_discount():
    r = recommend(FakeHazard(base=0.35), state(price=28500, market=29000, rule=0.0))
    assert r["recommended_discount"] == 0.0


def test_inelastic_unit_keeps_its_gross():
    r = recommend(FakeHazard(e=2.0), state(price=30000, market=29000, hold=8.0))
    assert r["recommended_discount"] <= 250


def test_never_far_below_cost_and_curve_json_is_grid():
    r = recommend(FakeHazard(e=40.0), state(price=27500, cost=27400, market=29000))
    assert r["recommended_price"] - 27400 >= -1500
    assert [c["discount"] for c in json.loads(r["curve_json"])] == [float(d) for d in DISCOUNT_GRID]


def test_guardrails_cap_fresh_units_and_big_cuts():
    st = state(price=31500, market=29000)
    st.features["age_days"] = 5.0
    r = recommend(FakeHazard(e=30.0), st)
    assert r["recommended_discount"] <= 500 and r["guardrail_applied"]
    assert r["unconstrained_discount"] > r["recommended_discount"]
    st.features["age_days"] = 60.0
    r2 = recommend(FakeHazard(e=30.0), st)
    assert r2["recommended_discount"] <= 0.08 * 31500
