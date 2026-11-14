"""E2E: Lakebase serving tables match Unity Catalog, decision integrity is enforced, Lakehouse Sync is on."""
import subprocess

from tests.workspace import FQ, PROFILE, e2e, sql


def psql(q: str) -> str:
    r = subprocess.run(["databricks", "psql", "--project", "piag-pricing", "-p", PROFILE, "--", "-d",
                        "databricks_postgres", "-At", "-c", q], capture_output=True, text=True)
    return (r.stdout.strip() + "\n" + r.stderr.strip()).strip()  # query output first, banner/errors after


@e2e
def test_serving_tables_match_unity_catalog():
    uc = sql(f"SELECT (SELECT count(*) FROM {FQ}.gold_inventory_current) inv, (SELECT count(*) FROM {FQ}.pricing_recommendations) rec")[0]
    out = psql("SELECT (SELECT count(*) FROM serving.inventory_current) || ',' || (SELECT count(*) FROM serving.recommendations)")
    assert f"{uc['inv']},{uc['rec']}" in out.splitlines()


@e2e
def test_override_without_reason_is_rejected():
    out = psql("BEGIN; INSERT INTO pricing_ops.pricing_decisions (vin, stock_number, rooftop_id, list_price_before, model_value, "
               "model_version, override_value, final_discount, decision, decided_by) VALUES ('T','T','R01',1,1,'t',2,2,"
               "'overridden','e2e'); ROLLBACK;")
    assert "override_needs_reason" in out


@e2e
def test_lakehouse_sync_history_tables_exist():
    names = {r["tableName"] for r in sql(f"SHOW TABLES IN {FQ} LIKE 'lb_*'")}
    assert {"lb_pricing_decisions_history", "lb_override_reasons_history"} <= names
