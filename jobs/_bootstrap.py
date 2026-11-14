"""Make the repo root importable when a job runs a file from the synced bundle."""
import os
import sys


def add_repo_root() -> str:
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:  # some serverless runners exec the file without __file__
        here = os.getcwd()
    root = os.path.dirname(here) if os.path.basename(here) == "jobs" else here
    if root not in sys.path:
        sys.path.insert(0, root)
    return root
