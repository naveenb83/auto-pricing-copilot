"""Write evidence/03_unity_catalog_governance.md from live UC metadata + the captured lens runs."""
import json
import subprocess

P = "DEFAULT"
C, S = "serverless_stable_69fppe_catalog", "piag_pricing"


def q(sql):
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", sql, "-p", P],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index("["):])


def tbl(rows, cols=None):
    if not rows:
        return "(none)"
    cols = cols or list(rows[0])
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    return "```text\n" + " | ".join(c.ljust(w[c]) for c in cols) + "\n" + "-+-".join("-" * w[c] for c in cols) + "\n" + \
        "\n".join(" | ".join(str(r.get(c, "")).ljust(w[c]) for c in cols) for r in rows) + "\n```"


def log(path):
    return "```text\n" + "\n".join(l[:400] for l in open(path).read().splitlines() if l.startswith("[OK")) + "\n```"


pol = q(f"SHOW POLICIES ON SCHEMA {C}.{S}")
tags = q(f"SELECT table_name, column_name, tag_name, tag_value FROM {C}.information_schema.column_tags "
         f"WHERE schema_name = '{S}' AND (tag_name LIKE 'piag%' OR tag_name LIKE 'class.%') ORDER BY 1, 2, 3")
ttags = q(f"SELECT table_name, tag_name, tag_value FROM {C}.information_schema.table_tags WHERE schema_name = '{S}' ORDER BY 1, 2")
funcs = q(f"SELECT routine_name, comment FROM {C}.information_schema.routines WHERE routine_schema = '{S}' ORDER BY 1")
lineage = q(f"SELECT DISTINCT replace(source_table_full_name, '{C}.{S}.', '') AS source, replace(target_table_full_name, '{C}.{S}.', '') AS target "
            f"FROM system.access.table_lineage WHERE target_table_full_name LIKE '{C}.{S}.%' AND source_table_full_name IS NOT NULL "
            f"AND source_table_full_name <> target_table_full_name AND event_date >= '2026-11-14' ORDER BY target, source")
comments = q(f"SELECT table_name, table_type, comment FROM {C}.information_schema.tables WHERE table_schema = '{S}' ORDER BY 1")
doc = [
    "# Evidence 03 — Unity Catalog governance (ABAC masks + row filter, tags, metric view, lineage)\n",
    f"Schema `{C}.{S}`. Captured live from `information_schema`, `SHOW POLICIES` and `system.access.table_lineage`.\n",
    "## ABAC policies attached to the schema (apply to every current and future tagged table)",
    tbl(pol, ["Policy Name", "Policy Type", "on_securable_type", "Comment"]),
    "Policy functions are a single group-membership check each — no lookup tables, so no per-column compile cost:",
    tbl(funcs),
    "## Governed column tags that drive the policies",
    tbl(tags),
    "## Table tags",
    tbl(ttags),
    "## Same queries, two identities (`governance/lens_check.sql`)",
    "**Full lens** — member of piag_margin_viewers, piag_crm_admins, piag_group_leadership:",
    log("governance/_lens_full.log"),
    "**Rooftop lens** — removed from those groups, added to piag_rooftop_R03 only (`governance/lens_switch.sh`):",
    log("governance/_lens_rooftop_R03.log"),
    "Result: 17,862 → 2,940 vehicle rows (R03 only), unit cost 17,862 → 0 visible, gross → NULL, customer "
    "surname/email/phone → masked; segment stays visible for marketing.\n",
    "Governed KPI metric view `piag_pricing_kpis` under the rooftop lens (gross masked through the metric view):",
    log("governance/_lens_rooftop_R03_metric_view.log"),
    "## Table lineage recorded by Unity Catalog (bronze → silver → gold → metric view)",
    tbl(lineage),
    "## Every table is self-describing (comments used by Genie and Catalog search)",
    tbl(comments),
    "## Grants note",
    "UC `GRANT` requires account-level principals. This demo workspace's `piag_*` groups are workspace-local "
    "(creating account groups needs account admin), so `governance/04_grants_account_groups.sql` is the production "
    "grant set for SCIM-synced account groups; it returned `PRINCIPAL_DOES_NOT_EXIST` here and is documented, not applied. "
    "The app's service principal (account-level) is granted explicitly in the app PR.",
]
open("evidence/03_unity_catalog_governance.md", "w").write("\n".join(doc) + "\n")
print("\n".join(doc)[:3000])
