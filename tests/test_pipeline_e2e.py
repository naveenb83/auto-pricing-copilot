"""E2E: the Lakeflow pipeline's gold layer reconciles with the simulator's ground truth."""
from tests.workspace import FQ, e2e, sql, volume_json


@e2e
def test_gold_inventory_reconciles_with_generator():
    gen = volume_json("/Volumes/serverless_stable_69fppe_catalog/piag_pricing/landing/_generation_summary.json")
    r = sql(f"SELECT count(*) n, count_if(days_in_stock >= 45) a45, count_if(days_in_stock >= 90) a90 "
            f"FROM {FQ}.gold_inventory_current")[0]
    # only vehicles rejected by DROP ROW expectations (null cost / negative mileage) may be missing
    assert 0 <= gen["on_hand_at_as_of"] - int(r["n"]) <= 10
    assert abs(gen["on_hand_45_plus"] - int(r["a45"])) <= 10
    assert abs(gen["on_hand_90_plus"] - int(r["a90"])) <= 10


@e2e
def test_silver_is_clean_and_deduplicated():
    r = sql(f"""SELECT (SELECT count(*) - count(DISTINCT vin) FROM {FQ}.silver_vehicles) dup_vins,
                       (SELECT count_if(unit_cost IS NULL OR mileage < 0) FROM {FQ}.silver_vehicles) bad_vehicles,
                       (SELECT count(*) - count(DISTINCT deal_id) FROM {FQ}.silver_sales) dup_deals,
                       (SELECT count_if(vin IS NULL) FROM {FQ}.silver_web_leads) null_lead_vins""")[0]
    assert all(int(v) == 0 for v in r.values()), r


@e2e
def test_every_on_hand_unit_is_priceable_and_has_a_photo():
    r = sql(f"""SELECT count_if(market_price IS NULL) no_market, count_if(image_path IS NULL) no_photo,
                       count_if(daily_holding_cost IS NULL OR daily_holding_cost <= 0) no_cost
                FROM {FQ}.gold_inventory_current""")[0]
    assert all(int(v) == 0 for v in r.values()), r


@e2e
def test_training_panel_has_labels_and_price_variation():
    r = sql(f"""SELECT count(*) n, sum(sold_retail_this_week) sales, stddev(price_to_market) sd_ptm,
                       count(DISTINCT discount_to_date) distinct_discounts
                FROM {FQ}.gold_pricing_features_weekly WHERE is_complete_week""")[0]
    assert int(r["n"]) > 100000 and 0.08 < int(r["sales"]) / int(r["n"]) < 0.2
    assert float(r["sd_ptm"]) > 0.02 and int(r["distinct_discounts"]) > 50
