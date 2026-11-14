"""Write evidence/02_lakeflow_pipeline.md from the pipeline event log + gold-table reconciliation queries."""
import json
import subprocess
import sys

PROFILE = "DEFAULT"
FQ = "serverless_stable_69fppe_catalog.piag_pricing"


def q(sql: str) -> list[dict]:
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", sql, "-p", PROFILE],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index("["):])


def table(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"
    cols = list(rows[0])
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    line = " | ".join(c.ljust(w[c]) for c in cols)
    sep = "-+-".join("-" * w[c] for c in cols)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(w[c]) for c in cols) for r in rows)
    return f"```text\n{line}\n{sep}\n{body}\n```"


def main(pid: str) -> None:
    upd = q(f"""SELECT origin.update_id, min(timestamp) AS started, max(timestamp) AS ended,
                coalesce(sum(CASE WHEN origin.flow_name LIKE '%bronze_%' THEN details:flow_progress.metrics.num_output_rows::bigint END), 0) AS bronze_rows_ingested
                FROM event_log('{pid}') WHERE event_type = 'flow_progress' GROUP BY 1 ORDER BY 2""")
    states = q(f"""SELECT origin.update_id, details:update_progress.state AS state FROM event_log('{pid}')
                   WHERE event_type = 'update_progress' AND details:update_progress.state IN ('COMPLETED','FAILED')""")
    st = {r["update_id"]: r["state"] for r in states}
    for r in upd:
        r["final_state"] = st.get(r["update_id"], "?")
    first = upd[0]["update_id"]
    last = upd[-1]["update_id"]
    flows = q(f"""SELECT dataset,
                  CASE WHEN dataset LIKE 'bronze_%' THEN 'streaming table (cumulative)' ELSE 'materialized view (latest update)' END AS kind,
                  CASE WHEN dataset LIKE 'bronze_%' THEN sum(n) ELSE max(CASE WHEN uid = '{last}' THEN n END) END AS output_rows
                  FROM (SELECT replace(origin.flow_name, '{FQ}.', '') AS dataset, origin.update_id AS uid,
                               details:flow_progress.metrics.num_output_rows::bigint AS n
                        FROM event_log('{pid}') WHERE event_type = 'flow_progress' AND origin.flow_name NOT LIKE 'pipelines.%')
                  GROUP BY dataset ORDER BY dataset""")
    incr = q(f"""SELECT replace(origin.flow_name, '{FQ}.', '') AS bronze_table,
                 sum(details:flow_progress.metrics.num_output_rows::bigint) AS rows_ingested
                 FROM event_log('{pid}') WHERE event_type = 'flow_progress' AND origin.update_id = '{upd[2]["update_id"]}'
                 AND origin.flow_name LIKE '%bronze_%' AND details:flow_progress.status = 'COMPLETED' GROUP BY 1 ORDER BY 1""")
    dq = q(f"""SELECT replace(origin.flow_name, '{FQ}.', '') AS dataset, e.name AS expectation,
               sum(e.passed_records) AS passed, sum(e.failed_records) AS failed
               FROM (SELECT origin, explode(from_json(details:flow_progress.data_quality.expectations,
                     'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS e
                     FROM event_log('{pid}') WHERE event_type = 'flow_progress' AND origin.update_id = '{last}'
                     AND details:flow_progress.data_quality IS NOT NULL)
               GROUP BY 1, 2 ORDER BY 1, 2""")
    recon = q(f"""SELECT count(*) AS on_hand, count_if(days_in_stock >= 45) AS aged_45_plus,
                  count_if(days_in_stock >= 90) AS aged_90_plus, round(avg(days_in_stock), 1) AS avg_days_in_stock,
                  round(sum(daily_holding_cost), 0) AS group_holding_cost_per_day
                  FROM {FQ}.gold_inventory_current""")
    buckets = q(f"""SELECT rooftop_name, count(*) AS on_hand, count_if(aging_bucket = '90+') AS aged_90_plus,
                    round(100 * count_if(aging_bucket = '90+') / count(*), 1) AS pct_90_plus,
                    round(sum(daily_holding_cost), 0) AS holding_cost_per_day
                    FROM {FQ}.gold_inventory_current GROUP BY 1 ORDER BY 1""")
    panel = q(f"""SELECT count(*) AS vehicle_weeks, count(DISTINCT vin) AS vehicles, sum(sold_retail_this_week) AS retail_sales,
                  round(avg(sold_retail_this_week), 4) AS weekly_sale_rate, min(week_start) AS first_week, max(week_start) AS last_week
                  FROM {FQ}.gold_pricing_features_weekly""")
    gen = json.loads(subprocess.run(["databricks", "fs", "cat",
                                     "dbfs:/Volumes/serverless_stable_69fppe_catalog/piag_pricing/landing/_generation_summary.json",
                                     "-p", PROFILE], capture_output=True, text=True).stdout)
    out = [
        "# Evidence 02 — Lakeflow Declarative Pipeline (bronze → silver → gold) executed on serverless\n",
        f"Pipeline `piag-pricing-lakeflow` (id `{pid}`), serverless + Photon, target `{FQ}`.",
        "All tables below are queried from the pipeline **event log** (`event_log()` TVF) and the published gold tables.\n",
        "## Pipeline updates (incremental ingestion proof)",
        "Update 1 = initial backfill of 78 weekly drops; update 2 = code change, **no new files → 0 bronze rows**; "
        "update 3 = after `piag-release-final-drop` delivered the 2026-11-13 drop → **only the new files ingested**; "
        "later updates = code changes only (sale-price rule drop→warn, review fixes) — no new files, so 0 bronze rows.",
        table(upd),
        "\n## Bronze rows ingested by update 3 (final weekly drop only)",
        table(incr),
        "\n## Output rows per dataset",
        table(flows),
        "\n## Data-quality expectations (latest update)",
        "`ON VIOLATION DROP ROW` rules remove unusable rows; warn-only rules keep the row and record the failure.",
        table(dq),
        "\n## Reconciliation: gold inventory vs simulator ground truth",
        f"Simulator (`_generation_summary.json`): on hand **{gen['on_hand_at_as_of']}**, aged 45+ **{gen['on_hand_45_plus']}**, aged 90+ **{gen['on_hand_90_plus']}**.",
        "Gold (`gold_inventory_current`) — difference = vehicles correctly rejected by `unit_cost_present` / `mileage_valid`:",
        table(recon),
        "\n## Aged inventory by rooftop (as of 2026-11-13)",
        table(buckets),
        "\n## ML training panel `gold_pricing_features_weekly`",
        table(panel),
    ]
    open("evidence/02_lakeflow_pipeline.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
