"""E2E: the Databricks App is deployed and running with least-privilege Lakebase access; if a local dev
server is up (npm run dev on :8000) the live model + decision validation paths are exercised too."""
import json
import subprocess
import urllib.request

import pytest
from databricks.sdk import WorkspaceClient

from tests.workspace import PROFILE, e2e

APP = "piag-pricing-copilot"


@e2e
def test_app_running_with_successful_deployment():
    a = WorkspaceClient(profile=PROFILE).apps.get(APP)
    assert a.app_status.state.value == "RUNNING"
    assert a.active_deployment.status.state.value == "SUCCEEDED"


@e2e
def test_app_sp_can_insert_but_not_delete_decisions():
    sp = WorkspaceClient(profile=PROFILE).apps.get(APP).service_principal_client_id
    q = (f"SELECT has_table_privilege('{sp}','pricing_ops.pricing_decisions','INSERT') || ',' || "
         f"has_table_privilege('{sp}','pricing_ops.pricing_decisions','DELETE') || ',' || "
         f"has_table_privilege('{sp}','serving.recommendations','SELECT')")
    out = subprocess.run(["databricks", "psql", "--project", "piag-pricing", "-p", PROFILE, "--", "-d",
                          "databricks_postgres", "-At", "-c", q], capture_output=True, text=True).stdout
    assert "true,false,true" in out.splitlines()


def _local(path: str, body: dict | None = None):
    req = urllib.request.Request(f"http://localhost:8000{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


@e2e
def test_local_server_live_model_and_validation():
    try:
        _local("/api/whoami")
    except Exception:
        pytest.skip("local dev server not running")
    _, q = _local("/api/queue?limit=1&minAge=90")
    vin = q["rows"][0]["vin"]
    status, rec = _local("/api/recommend", {"vin": vin})
    assert status == 200 and rec["prediction"]["model_version"] and len(rec["curve"]) == 10
    status, err = _local("/api/decisions", {"vin": vin, "decision": "overridden", "overrideValue": 123,
                                            "model": {"value": 0, "version": "x", "source": "batch_score",
                                                      "expectedProfit": None, "pSell30d": None}})
    assert status == 400 and "reason" in err["error"]
