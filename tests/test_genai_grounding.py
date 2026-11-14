"""Unit tests for the LLM grounding check (no Spark needed)."""
from ml.genai_rationale import grounded

FACTS = {"make": "Mazda", "model": "CX-90", "trim": "Base", "model_year": 2026, "days_in_stock": 188,
         "price_to_market": 1.052, "holding_cost_per_day": 33, "recommended_discount": 3000, "recommended_price": 35295,
         "expected_days_now": 85, "expected_days_after": 68, "profit_vs_flat_rule": 46, "days_if_500_cut": 80,
         "profit_change_if_500_cut": -42}


def test_numbers_from_facts_pass_including_rounding_and_percent():
    ok, bad = grounded("The 2026 CX-90 Base sat 188 days, 5% above market (1.05x); a $3,000 cut to $35,295 sells in "
                       "68 days not 85 (17 days sooner), +$46 vs the flat rule, saving $33 a day. A $500 cut: 80 days.", FACTS)
    assert ok, bad


def test_invented_numbers_are_caught():
    ok, bad = grounded("Cut $4,100 and it sells in 777 days.", FACTS)
    assert not ok and 4100.0 in bad and 777.0 in bad


def test_model_name_digits_are_not_statistics():
    ok, _ = grounded("This CX-90 is ready now.", FACTS)
    assert ok


def test_missing_counterfactual_values_do_not_crash():
    f = dict(FACTS, days_if_500_cut=float("nan"), profit_change_if_500_cut=None)
    ok, _ = grounded("A $3,000 cut sells it in 68 days.", f)
    assert ok
