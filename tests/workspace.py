"""Helpers for e2e tests that run against the live Databricks workspace (set PIAG_E2E=1)."""
import json
import os
import subprocess

import pytest

PROFILE = os.environ.get("PIAG_PROFILE", "DEFAULT")
FQ = "serverless_stable_69fppe_catalog.piag_pricing"
e2e = pytest.mark.skipif(os.environ.get("PIAG_E2E") != "1", reason="set PIAG_E2E=1 to run workspace e2e tests")


def sql(query: str) -> list[dict]:
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", query, "-p", PROFILE],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index("["):])


def volume_json(path: str) -> dict:
    out = subprocess.run(["databricks", "fs", "cat", f"dbfs:{path}", "-p", PROFILE],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)
