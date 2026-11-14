"""Ask the Genie Agent the sample questions via the Conversation API and write a text transcript
(question → Genie's generated SQL → result rows) to evidence/07_genie_transcript.md."""
from __future__ import annotations

import sys
import time

from databricks.sdk import WorkspaceClient

SPACE = sys.argv[1] if len(sys.argv) > 1 else "01f1e03bafe91748918dbc276f3cfd90"
QUESTIONS = [
    "How many units are aged 90+ days at each rooftop and what do they cost us per day?",
    "Which aged units does the model recommend cutting by $1,500 or more?",
    "How much more profit does the model expect than the flat rule, by rooftop?",
    "Which customer segments respond best to pickup promotions?",
    "In the backtest, how did the model with guardrails compare with the flat rule on net profit and aged units at day 60?",
    "What was the average days to sell and front gross for retail sales by month in 2026?",
]


def main() -> None:
    w = WorkspaceClient(profile="DEFAULT")
    out = ["# Evidence 07b — Genie Agent conversation transcript (Conversation API)\n",
           f"Space `{SPACE}`. Each question asked in a fresh conversation; Genie's generated SQL and the first rows "
           "of the result are shown verbatim.\n"]
    for q in QUESTIONS:
        t0 = time.time()
        msg = w.genie.start_conversation_and_wait(space_id=SPACE, content=q)
        secs = time.time() - t0
        out.append(f"## Q: {q}\n_status {msg.status.value if msg.status else '?'}, {secs:.0f}s_\n")
        for att in msg.attachments or []:
            if att.text and att.text.content:
                out.append(f"**Genie:** {att.text.content.strip()}\n")
            if att.query:
                out += ["Generated SQL:", "```sql", (att.query.query or "").strip(), "```"]
                if att.query.description:
                    out.append(f"_{att.query.description.strip()}_\n")
                res = w.genie.get_message_attachment_query_result(SPACE, msg.conversation_id, msg.message_id,
                                                                  att.attachment_id)
                sr = res.statement_response
                cols = [c.name for c in (sr.manifest.schema.columns or [])] if sr and sr.manifest else []
                rows = (sr.result.data_array or [])[:12] if sr and sr.result else []
                out += ["Result:", "```text", " | ".join(cols)] + [" | ".join("" if v is None else str(v) for v in r)
                                                                    for r in rows] + ["```"]
        print(f"asked: {q[:70]}  ({secs:.0f}s)")
    open("evidence/07b_genie_transcript.md", "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
