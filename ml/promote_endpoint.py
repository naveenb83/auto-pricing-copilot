"""Point the real-time endpoint at the current @champion version (runs after every retrain) so batch
scores and live recommendations always come from the same model."""
import argparse

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServedEntityInput

ap = argparse.ArgumentParser()
ap.add_argument("--catalog", required=True)
ap.add_argument("--schema", required=True)
ap.add_argument("--endpoint", default="piag-pricing-model")
a, _ = ap.parse_known_args()
name = f"{a.catalog}.{a.schema}.aged_inventory_pricing_model"
w = WorkspaceClient()
champion = w.model_versions.get_by_alias(name, "champion").version
ep = w.serving_endpoints.get(a.endpoint)
current = ep.config.served_entities[0]
if str(current.entity_version) == str(champion):
    print(f"endpoint {a.endpoint} already serves {name} v{champion}")
else:
    print(f"updating endpoint {a.endpoint}: v{current.entity_version} -> v{champion} (champion)")
    w.serving_endpoints.update_config_and_wait(
        name=a.endpoint,
        served_entities=[ServedEntityInput(name=current.name, entity_name=name, entity_version=str(champion),
                                           workload_size=current.workload_size,
                                           scale_to_zero_enabled=current.scale_to_zero_enabled)])
    print(f"endpoint {a.endpoint} now serves v{champion}")
