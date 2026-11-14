"""E2E: the Genie Agent exists with the governed data sources and answers a business question with SQL."""
from databricks.sdk import WorkspaceClient

from tests.workspace import PROFILE, e2e

SPACE = "01f1e03bafe91748918dbc276f3cfd90"


@e2e
def test_space_has_tables_metric_view_and_benchmarks():
    import json
    sp = WorkspaceClient(profile=PROFILE).genie.get_space(SPACE, include_serialized_space=True)
    d = json.loads(sp.serialized_space)
    assert len(d["data_sources"]["tables"]) == 9
    assert d["data_sources"]["metric_views"][0]["identifier"].endswith("piag_pricing_kpis")
    assert len(d["benchmarks"]["questions"]) == 12


@e2e
def test_genie_answers_aged_inventory_question_with_sql():
    w = WorkspaceClient(profile=PROFILE)
    msg = w.genie.start_conversation_and_wait(space_id=SPACE, content="How many on-hand units are 90 or more days old?")
    assert msg.status.value == "COMPLETED"
    sql = next(a.query.query for a in msg.attachments if a.query)
    assert "gold_inventory_current" in sql and "90" in sql
