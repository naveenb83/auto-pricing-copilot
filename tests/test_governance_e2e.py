"""E2E: ABAC policies, governed tags and the KPI metric view are live and behave for the builder lens."""
from tests.workspace import FQ, e2e, sql

C, S = FQ.split(".")


@e2e
def test_three_abac_policies_on_schema():
    names = {r["Policy Name"]: r["Policy Type"] for r in sql(f"SHOW POLICIES ON SCHEMA {FQ}")}
    assert names == {"piag_mask_financial": "COLUMN_MASK", "piag_mask_pii": "COLUMN_MASK",
                     "piag_filter_rooftop": "ROW_FILTER"}


@e2e
def test_sensitive_columns_are_tagged():
    rows = sql(f"SELECT table_name, column_name, tag_value FROM {C}.information_schema.column_tags "
               f"WHERE schema_name = '{S}' AND tag_name = 'piag_sensitivity'")
    tagged = {(r["table_name"], r["column_name"]): r["tag_value"] for r in rows}
    assert tagged[("gold_vehicle_status", "unit_cost")] == "financial"
    assert tagged[("gold_sales_enriched", "front_gross")] == "financial"
    assert tagged[("silver_customers", "email")] == "pii"


@e2e
def test_mask_functions_follow_group_membership():
    r = sql(f"""SELECT is_member('piag_margin_viewers') mv, {FQ}.mask_financial(123.0) masked_value,
                       is_member('piag_crm_admins') crm, {FQ}.mask_pii('someone@example.com') pii,
                       {FQ}.filter_rooftop('R03') r03""")[0]
    assert (r["mv"] == "true") == (r["masked_value"] == "123.0")
    assert (r["crm"] == "true") == (r["pii"] == "someone@example.com")


@e2e
def test_metric_view_returns_kpis():
    r = sql(f"SELECT MEASURE(`Units On Hand`) u, MEASURE(`Aged 90+ Units`) a90, MEASURE(`Holding Cost Per Day`) hc "
            f"FROM {FQ}.piag_pricing_kpis")[0]
    assert 1300 < int(r["u"]) < 1500 and 200 < int(r["a90"]) < 400 and float(r["hc"]) > 10000
