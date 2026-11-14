"""Move the held-back final weekly drop from landing/_held into landing (simulates the next DMS delivery)."""
import argparse
import json
import os
import shutil

p = argparse.ArgumentParser()
p.add_argument("--landing", required=True)
a, _ = p.parse_known_args()
held = os.path.join(a.landing, "_held")
moved = []
if os.path.isdir(held):
    for entity in sorted(os.listdir(held)):
        for drop in sorted(os.listdir(os.path.join(held, entity))):
            src, dst = os.path.join(held, entity, drop), os.path.join(a.landing, entity, drop)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            moved.append(f"{entity}/{drop}")
    shutil.rmtree(held)
print(json.dumps({"released": moved}, indent=2))
