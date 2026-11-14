"""Capture the latest successful run of a Databricks job as a readable-text evidence block.

    uv run python scripts/job_evidence.py <job_id> [--profile DEFAULT]   -> markdown on stdout
Includes run state/timings, per-task results and each task's stdout (ANSI colour codes stripped).
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def cli(*args: str, profile: str) -> dict:
    out = subprocess.run(["databricks", *args, "-p", profile, "-o", "json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout, strict=False)


def ts(ms) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ms else "-"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    ap.add_argument("--profile", default="DEFAULT")
    ap.add_argument("--run_id", default="")
    ap.add_argument("--max_log_lines", type=int, default=120)
    a = ap.parse_args()
    if a.run_id:
        run = cli("jobs", "get-run", a.run_id, profile=a.profile)
    else:
        runs = cli("jobs", "list-runs", "--job-id", a.job_id, "--completed-only", profile=a.profile)
        ok = [r for r in runs if r.get("state", {}).get("result_state") == "SUCCESS"]
        run = cli("jobs", "get-run", str(ok[0]["run_id"]), profile=a.profile)
    print(f"Job `{run.get('run_name')}` (job_id {run['job_id']}), run_id {run['run_id']} — "
          f"captured {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} via `databricks jobs get-run(-output)`.\n")
    print("```text")
    print(f"result_state : {run['state'].get('result_state')}")
    print(f"start (UTC)  : {ts(run.get('start_time'))}")
    print(f"end (UTC)    : {ts(run.get('end_time'))}")
    for t in run.get("tasks", []):
        print(f"task {t['task_key']:<28} {t['state'].get('result_state', t['state'].get('life_cycle_state'))}"
              f"  {ts(t.get('start_time'))} -> {ts(t.get('end_time'))}")
    print("```")
    for t in run.get("tasks", []):
        try:
            out = cli("jobs", "get-run-output", str(t["run_id"]), profile=a.profile)
        except subprocess.CalledProcessError:
            continue
        logs = ANSI.sub("", out.get("logs") or (out.get("notebook_output") or {}).get("result") or "").strip()
        if not logs:
            continue
        lines = logs.splitlines()
        if len(lines) > a.max_log_lines:
            lines = lines[: a.max_log_lines] + [f"... ({len(lines) - a.max_log_lines} more lines truncated)"]
        print(f"\n### Task `{t['task_key']}` stdout\n```text")
        print("\n".join(lines))
        print("```")


if __name__ == "__main__":
    main()
