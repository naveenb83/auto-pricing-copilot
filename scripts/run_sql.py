"""Run a .sql file statement-by-statement on a SQL warehouse and print a text log (evidence-friendly).

    uv run python scripts/run_sql.py governance/01_tags_and_comments.sql [--profile DEFAULT]
Statements are split on ';' at end of line; `USE CATALOG/SCHEMA` lines set the context for the rest.
"""
import argparse
import re
import sys
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

WAREHOUSE = "8b226d8722ba3ab2"


def statements(text: str) -> list[str]:
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in re.split(r";\s*\n", text + "\n") if s.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--profile", default="DEFAULT")
    a = ap.parse_args()
    w = WorkspaceClient(profile=a.profile)
    catalog, schema, failures = None, None, 0
    for f in a.files:
        print(f"## {f}")
        for stmt in statements(open(f).read()):
            m = re.match(r"USE\s+CATALOG\s+(\S+)", stmt, re.I)
            if m:
                catalog = m.group(1); print(f"[ctx] catalog={catalog}"); continue
            m = re.match(r"USE\s+SCHEMA\s+(\S+)", stmt, re.I)
            if m:
                schema = m.group(1); print(f"[ctx] schema={schema}"); continue
            t0 = time.time()
            r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WAREHOUSE, catalog=catalog,
                                                        schema=schema, wait_timeout="50s")
            while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
                time.sleep(2)
                r = w.statement_execution.get_statement(r.statement_id)
            head = " ".join(stmt.split())[:150]
            if r.status.state == StatementState.SUCCEEDED:
                rows = (r.result.data_array or []) if r.result else []
                print(f"[OK  {time.time() - t0:5.1f}s] {head}" + (f"  -> {rows[:3]}" if rows else ""))
            else:
                failures += 1
                print(f"[FAIL] {head}\n       {r.status.error.message if r.status.error else r.status.state}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
