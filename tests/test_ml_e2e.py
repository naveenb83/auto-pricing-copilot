"""E2E: champion model registered, batch scores + backtest written, and the real-time endpoint answers."""
import json

from databricks.sdk import WorkspaceClient

from tests.workspace import FQ, PROFILE, e2e, sql


@e2e
def test_champion_alias_points_at_served_version():
    w = WorkspaceClient(profile=PROFILE)
    mv = w.model_versions.get_by_alias(f"{FQ}.aged_inventory_pricing_model", "champion")
    ep = w.serving_endpoints.get("piag-pricing-model")
    assert ep.state.ready.value == "READY"
    assert str(ep.config.served_entities[0].entity_version) == str(mv.version)


@e2e
def test_every_on_hand_vehicle_has_a_recommendation():
    r = sql(f"""SELECT (SELECT count(*) FROM {FQ}.gold_inventory_current) inv,
                       count(*) recs, count_if(recommended_discount < 0) negative,
                       count_if(recommended_discount > 0.08 * current_price + 1) over_guardrail
                FROM {FQ}.pricing_recommendations""")[0]
    assert r["inv"] == r["recs"] and int(r["negative"]) == 0 and int(r["over_guardrail"]) == 0


@e2e
def test_backtest_model_beats_flat_rule():
    r = sql(f"""SELECT avg(CASE WHEN policy = 'model_guardrails' THEN net_profit END) -
                       avg(CASE WHEN policy = 'flat_rule' THEN net_profit END) uplift,
                       avg(CASE WHEN policy = 'model_guardrails' THEN aged90_day60 END) m90,
                       avg(CASE WHEN policy = 'flat_rule' THEN aged90_day60 END) r90
                FROM {FQ}.backtest_policy_results""")[0]
    assert float(r["uplift"]) > 0 and float(r["m90"]) < float(r["r90"])


@e2e
def test_realtime_endpoint_recommends_for_an_aged_unit():
    row = sql(f"SELECT * FROM {FQ}.gold_inventory_current WHERE days_in_stock >= 90 ORDER BY vin LIMIT 1")[0]
    cols = ["vin", "current_price", "unit_cost", "market_price", "daily_market_depreciation", "daily_holding_cost",
            "flat_rule_additional_discount", "days_in_stock", "model_year", "mileage", "market_days_supply",
            "vdp_views_last_week", "leads_last_week", "test_drives_last_week", "weeks_listed", "condition",
            "body_class", "make", "model", "exterior_colour", "rooftop_id", "as_of_date"]
    rec = {c: row[c] for c in cols}
    for c in cols[1:15]:
        rec[c] = float(rec[c])
    for c in ("days_in_stock", "model_year", "mileage", "vdp_views_last_week", "leads_last_week",
              "test_drives_last_week", "weeks_listed"):
        rec[c] = int(rec[c])
    rec["price_override"] = None
    p = WorkspaceClient(profile=PROFILE).serving_endpoints.query(
        name="piag-pricing-model", dataframe_records=[rec]).predictions[0]
    assert p["vin"] == row["vin"] and p["recommended_discount"] >= 0
    assert p["expected_profit_recommended"] >= p["expected_profit_now"]
    assert len(json.loads(p["curve_json"])) == 10
