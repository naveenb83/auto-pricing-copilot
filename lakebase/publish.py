"""Publish governed gold tables into Lakebase Postgres (schema `serving`) for low-latency app reads.

Production path = Lakebase synced tables (TRIGGERED, CDF is already enabled on the sources). That needs
the Lakebase database registered as a UC catalog (metastore CREATE CATALOG), which this demo workspace
does not grant — so this job performs the same snapshot publish: load into a staging table, then swap it
in atomically inside one transaction so the app never reads a half-loaded table.
The reverse direction (app decisions -> UC) uses native Lakehouse Sync (CDC), see lakebase/README.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import json
import time

TABLES = {  # postgres table -> (UC source, primary key)
    "inventory_current": ("gold_inventory_current", ["vin"]),
    "recommendations": ("pricing_recommendations", ["vin"]),
    "rationale": ("pricing_rationale", ["vin"]),
    "segment_targeting": ("segment_targeting", ["body_class", "segment"]),
    "rooftops": ("ref_rooftops", ["rooftop_id"]),
    "rooftop_weekly_kpis": ("gold_rooftop_weekly_kpis", ["week_end", "rooftop_id"]),
}


def pg_type(values) -> str:
    v = next((x for x in values if x is not None), None)
    if isinstance(v, bool):
        return "BOOLEAN"
    if isinstance(v, int):
        return "BIGINT"
    if isinstance(v, (float, decimal.Decimal)):
        return "DOUBLE PRECISION"
    if isinstance(v, dt.datetime):
        return "TIMESTAMPTZ"
    if isinstance(v, dt.date):
        return "DATE"
    return "TEXT"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--project", default="piag-pricing")
    ap.add_argument("--app_sp", default="", help="app service principal client id to grant SELECT")
    a, _ = ap.parse_known_args()
    fq = f"{a.catalog}.{a.schema}"
    import psycopg
    import psycopg.sql
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    w = WorkspaceClient()
    ep_name = f"projects/{a.project}/branches/production/endpoints/primary"
    host = w.postgres.get_endpoint(name=ep_name).status.hosts.host
    token = w.postgres.generate_database_credential(endpoint=ep_name).token
    user = w.current_user.me().user_name
    report = []
    with psycopg.connect(host=host, dbname="databricks_postgres", user=user, password=token, sslmode="require") as conn:
        for pg_table, (src, pk) in TABLES.items():
            t0 = time.time()
            rows = [r.asDict() for r in spark.table(f"{fq}.{src}").collect()]
            cols = list(spark.table(f"{fq}.{src}").columns)
            types = {c: pg_type([r[c] for r in rows]) for c in cols}
            stage = f"{pg_table}__staging"
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS serving.{stage}")
                cur.execute(f"CREATE TABLE serving.{stage} (" + ", ".join(f'"{c}" {types[c]}' for c in cols) + ")")
                with cur.copy(f"COPY serving.{stage} (" + ", ".join(f'"{c}"' for c in cols) + ") FROM STDIN") as cp:
                    for r in rows:
                        cp.write_row([float(r[c]) if isinstance(r[c], decimal.Decimal) else r[c] for c in cols])
                cur.execute(f"ALTER TABLE serving.{stage} ADD PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pk) + ")")
                # atomic swap
                cur.execute(f"DROP TABLE IF EXISTS serving.{pg_table}")
                cur.execute(f"ALTER TABLE serving.{stage} RENAME TO {pg_table}")
                cur.execute(f"ALTER INDEX serving.{stage}_pkey RENAME TO {pg_table}_pkey")
                note = f"Published from Unity Catalog {fq}.{src} at {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"
                # utility statements cannot take bind parameters: quote the literal safely instead
                cur.execute(psycopg.sql.SQL("COMMENT ON TABLE serving.{} IS {}").format(
                    psycopg.sql.Identifier(pg_table), psycopg.sql.Literal(note)))
                if a.app_sp:
                    cur.execute(f'GRANT SELECT ON serving.{pg_table} TO "{a.app_sp}"')
                cur.execute(f"SELECT count(*) FROM serving.{pg_table}")
                n_pg = cur.fetchone()[0]
            conn.commit()
            report.append({"postgres_table": f"serving.{pg_table}", "uc_source": f"{fq}.{src}", "uc_rows": len(rows),
                           "postgres_rows": n_pg, "match": len(rows) == n_pg, "seconds": round(time.time() - t0, 1)})
            print(json.dumps(report[-1]))
        if a.app_sp:
            with conn.cursor() as cur:
                cur.execute(f'GRANT USAGE ON SCHEMA serving TO "{a.app_sp}"')
                cur.execute(f'GRANT USAGE ON SCHEMA pricing_ops TO "{a.app_sp}"')
                cur.execute(f'GRANT SELECT, INSERT ON pricing_ops.pricing_decisions TO "{a.app_sp}"')
                cur.execute(f'GRANT USAGE ON SEQUENCE pricing_ops.pricing_decisions_decision_id_seq TO "{a.app_sp}"')
                cur.execute(f'GRANT SELECT ON pricing_ops.override_reasons TO "{a.app_sp}"')
            conn.commit()
            print(f"granted app service principal {a.app_sp}: SELECT on serving.*, SELECT/INSERT on pricing_ops.pricing_decisions")
    ok = all(r["match"] for r in report)
    print("== SUMMARY " + json.dumps({"tables": len(report), "all_counts_match": ok,
                                      "rows": {r["postgres_table"]: r["postgres_rows"] for r in report}}))
    if not ok:
        raise SystemExit("row count mismatch between Unity Catalog and Lakebase")


if __name__ == "__main__":
    main()
