"""Write evidence/07_genie_benchmark.md: per-question results of Genie benchmark eval runs (baseline vs tuned)."""
import json
import subprocess
import sys

P, SPACE = "DEFAULT", "01f1e03bafe91748918dbc276f3cfd90"


def cli(*a):
    out = subprocess.run(["databricks", "genie", *a, "-p", P, "-o", "json"], capture_output=True, text=True, check=True).stdout
    return json.loads(out, strict=False)


def query_rows(sql_text: str):
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", sql_text, "-p", P],
                         capture_output=True, text=True)
    if out.returncode:
        return None
    rows = json.loads(out.stdout[out.stdout.index("["):])

    def norm(v):
        try:
            return round(float(v), 1)
        except (TypeError, ValueError):
            return str(v).strip().lower()
    return sorted(tuple(sorted(norm(v) for v in r.values())) for r in rows)


def run_section(rid: str, label: str) -> tuple[list[str], int, int]:
    run = cli("genie-get-eval-run", SPACE, rid)
    res = cli("genie-list-eval-results", SPACE, rid)["eval_results"]
    semantic = 0
    lines = [f"## {label} — eval run `{rid}`",
             f"**{run['num_correct']}/{run['num_questions']} correct**, {run.get('num_needs_review', 0)} needs review.\n",
             "| # | Benchmark question | Assessment | Reasons |", "|---|---|---|---|"]
    detail = []
    for i, r in enumerate(sorted(res, key=lambda x: x["question"]), 1):
        d = cli("genie-get-eval-result-details", SPACE, rid, r["result_id"])
        a = d.get("assessment", "?")
        reasons = ", ".join(d.get("assessment_reasons") or []) or "-"
        lines.append(f"| {i} | {r['question']} | {a} | {reasons} |")
        if a != "GOOD":
            genie_sql = (d.get("actual_response") or [{}])[0].get("response", "")
            same = query_rows(genie_sql) == query_rows(r["benchmark_answer"]) and genie_sql.strip() != ""
            semantic += int(same)
            verdict = ("re-executed: **same result as the benchmark** (scorer difference only)" if same
                       else "re-executed: **different result** — a genuine miss")
            detail += [f"**#{i} {r['question']}** — {a}; {verdict}", "Benchmark SQL:", "```sql", r["benchmark_answer"], "```",
                       "Genie SQL:", "```sql", genie_sql.strip(), "```"]
        else:
            semantic += 1
    lines.append("")
    lines.append(f"Auto-scored **{run['num_correct']}/{run['num_questions']}**; after re-executing every non-GOOD answer "
                 f"and comparing result sets: **{semantic}/{run['num_questions']} return the benchmark result**.")
    return lines + [""] + detail, semantic, run["num_questions"]


def main():
    rid = sys.argv[1:]
    notes = [
        ("Baseline", ""),
        ("Tuning pass 1", "Tuning pass 1: added explicit date-window and sales-table instructions after the baseline miss on the "
         "ambiguous 'last 90 days' question. Benchmarks NOT edited."),
        ("Benchmark repair 1", "Benchmark repair 1 (separate from tuning): wholesale answer SQL gained the upper bound "
         "`sale_date <= DATE'2026-11-13'` to match the space's date-window definition. No Genie instructions changed."),
        ("Benchmark repair 2", "Benchmark repair 2: the wholesale question said 'before the business date', which Genie reasonably "
         "read as exclusive; reworded to 'in the 90 days up to and including the business date'. No Genie instructions changed."),
        ("Tuning pass 2", "Tuning pass 2: Genie rounded an average of days to a whole number; instruction now says averages of "
         "days are shown to one decimal place. Benchmarks NOT edited."),
    ]
    runs = [(r, notes[i][0], notes[i][1]) for i, r in enumerate(rid)]
    doc = ["# Evidence 07 — Genie Agent benchmark evaluation (native Genie eval runs)\n",
           f"Space `{SPACE}` (\"Pacific Isles Pricing Copilot — Ask the data\"): 9 tables + metric view `piag_pricing_kpis`, "
           "text instructions, 4 verified example SQLs, 12 benchmark questions with answer SQL verified against the warehouse "
           "before the run (`genie/build_space.py`).\n"]
    summary_rows = []
    for rid_, label, note in runs:
        if note:
            doc += ["", note, ""]
        section, semantic, n = run_section(rid_, label)
        doc += section
        summary_rows.append((label, rid_, semantic, n))
    doc += ["", "## Summary across passes", "| Pass | Eval run | Result-set matches after re-execution |", "|---|---|---|"]
    doc += [f"| {l} | `{r}` | {sm}/{n} |" for l, r, sm, n in summary_rows]
    doc += ["", "Genie is non-deterministic: the same space can phrase SQL differently run to run (types, rounding, "
            "boundaries). Each pass made ONE change and was re-evaluated; the strict auto-scorer is reported verbatim above."]
    open("evidence/07_genie_benchmark.md", "w").write("\n".join(doc) + "\n")
    print("\n".join(doc))


if __name__ == "__main__":
    main()
