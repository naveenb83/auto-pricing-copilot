"""E2E: the nightly orchestration job exists, chains every stage, and its latest run succeeded."""
from databricks.sdk import WorkspaceClient

from tests.workspace import PROFILE, e2e


@e2e
def test_nightly_job_chains_all_stages_and_last_run_succeeded():
    w = WorkspaceClient(profile=PROFILE)
    job = next(j for j in w.jobs.list(name="piag-nightly-end-to-end"))
    deps = {t.task_key: [d.task_key for d in (t.depends_on or [])] for t in w.jobs.get(job.job_id).settings.tasks}
    # the API returns tasks alphabetically: assert the dependency CHAIN instead of list order
    assert deps == {"lakeflow_ingest": [], "score_with_champion": ["lakeflow_ingest"],
                    "genai_rationale": ["score_with_champion"], "lakebase_publish": ["genai_rationale"],
                    "verify_journey": ["lakebase_publish"]}
    last = next(iter(w.jobs.list_runs(job_id=job.job_id, completed_only=True, limit=1)))
    assert last.state.result_state.value == "SUCCESS"
