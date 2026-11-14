"""Final task of the nightly job: assert every stage of the data journey is consistent, and print a
one-screen health report (captured as evidence).

Checks: gold vs recommendations coverage, model champion == served version, rationale grounding,
Lakebase serving counts == UC, decisions in Lakebase == decisions in UC (Lakehouse Sync lag), Genie space reachable.
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("--catalog", required=True)
ap.add_argument("--schema", required=True)
a, _ = ap.parse_known_args()
fq = f"{a.catalog}.{a.schema}"

import psycopg  # noqa: E402
from databricks.sdk import WorkspaceClient  # noqa: E402
from pyspark.sql import SparkSession  # noqa: E402

spark = SparkSession.builder.getOrCreate()
w = WorkspaceClient()
one = lambda q: spark.sql(q).first()[0]  # noqa: E731

checks = {}
inv = one(f"SELECT count(*) FROM {fq}.gold_inventory_current")
recs = one(f"SELECT count(*) FROM {fq}.pricing_recommendations")
checks["every on-hand unit scored"] = (inv == recs, f"{recs}/{inv}")
champ = w.model_versions.get_by_alias(f"{fq}.aged_inventory_pricing_model", "champion").version
served = w.serving_endpoints.get("piag-pricing-model").config.served_entities[0].entity_version
checks["endpoint serves @champion"] = (str(champ) == str(served), f"champion v{champ}, served v{served}")
g, n = spark.sql(f"SELECT count_if(grounded), count(*) FROM {fq}.pricing_rationale").first()
checks["GenAI rationale grounded"] = (g == n and n > 0, f"{g}/{n}")
aged = one(f"SELECT count(*) FROM {fq}.pricing_recommendations WHERE days_in_stock >= 45")
checks["rationale for every aged unit"] = (n == aged, f"{n}/{aged}")

ep = "projects/piag-pricing/branches/production/endpoints/primary"
host = w.postgres.get_endpoint(name=ep).status.hosts.host
tok = w.postgres.generate_database_credential(endpoint=ep).token
with psycopg.connect(host=host, dbname="databricks_postgres", user=w.current_user.me().user_name, password=tok,
                     sslmode="require") as c:
    pg_inv = c.execute("SELECT count(*) FROM serving.inventory_current").fetchone()[0]
    pg_rec = c.execute("SELECT count(*) FROM serving.recommendations").fetchone()[0]
    pg_dec = c.execute("SELECT count(*) FROM pricing_ops.pricing_decisions").fetchone()[0]
checks["Lakebase serving == UC gold"] = (pg_inv == inv and pg_rec == recs, f"inventory {pg_inv}/{inv}, recs {pg_rec}/{recs}")
uc_dec = one(f"SELECT count(*) FROM {fq}.pricing_decisions")
checks["Lakehouse Sync: decisions in UC == Lakebase"] = (uc_dec == pg_dec, f"UC {uc_dec} / Lakebase {pg_dec}")
sp = w.genie.get_space("01f1e03bafe91748918dbc276f3cfd90")
checks["Genie space reachable"] = (bool(sp.space_id), sp.title)

kpi = spark.sql(f"SELECT MEASURE(`Units On Hand`) u, MEASURE(`Aged 90+ Units`) a, round(MEASURE(`Holding Cost Per Day`)) h "
                f"FROM {fq}.piag_pricing_kpis").first()
print("== Data journey health report")
for k, (ok, detail) in checks.items():
    print(f"[{'PASS' if ok else 'FAIL'}] {k:<45} {detail}")
print(f"== KPIs: {kpi.u} on hand, {kpi.a} aged 90+, ${kpi.h:,.0f}/day holding cost")
failed = [k for k, (ok, _) in checks.items() if not ok]
print("== SUMMARY " + json.dumps({"checks": len(checks), "passed": len(checks) - len(failed), "failed": failed}))
if failed:
    raise SystemExit(f"journey checks failed: {failed}")
