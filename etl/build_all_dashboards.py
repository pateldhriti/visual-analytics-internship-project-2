r"""
Register the datasets and build all six dashboards, in the order they depend
on each other, against one Superset.

    .venv\Scripts\python.exe etl\build_all_dashboards.py                 our local Superset (.env)
    .venv\Scripts\python.exe etl\build_all_dashboards.py --env .env.apss the university's Superset

An --env file's settings take precedence over .env. For the university's
Superset it holds (never commit it; .gitignore excludes .env.*):

    SUPERSET_URL=https://apss.cs.uwindsor.ca
    SUPERSET_TARGET=shared
    SUPERSET_DATABASE_NAME=psql_ss_whva
    SUPERSET_LOGIN_USER=<your university username>
    SUPERSET_LOGIN_PASSWORD=<your university password>

The data must already be in that database (etl/export_for_shared_db.py,
docs/deploy_university.md). Stops at the first step that fails.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ETL = Path(__file__).resolve().parent
PROJECT_ROOT = ETL.parent

STEPS = [
    "register_superset_datasets.py",  # datasets on our database connection
    "setup_superset_dashboard.py",  # Story 1's tenure bar (also on the overview)
    "finalize_story1_layout.py",  # Story 1, before the overview uses its charts
    "build_dashboard1_overview.py",
    "build_story2_dashboard.py",
    "build_story3_dashboard.py",
    "build_story4_dashboard.py",
    "build_story5_dashboard.py",
    "apply_dashboard_theme.py",
]
LOCAL_ONLY = ["enable_dashboard_embedding.py"]  # the shared Superset's admin controls embedding


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", help="settings file that overrides .env, e.g. .env.apss")
    args = parser.parse_args(argv)

    env = dict(os.environ)
    if args.env:
        path = Path(args.env) if Path(args.env).is_absolute() else PROJECT_ROOT / args.env
        if not path.exists():
            parser.error(f"{path} not found")
        env.update({k: v for k, v in dotenv_values(path).items() if v is not None})
    shared = env.get("SUPERSET_TARGET", "local").lower() == "shared"
    target = env.get("SUPERSET_URL", "http://localhost:8088")
    print(f"Building on {target} ({'shared' if shared else 'local'} Superset)")

    for step in STEPS + ([] if shared else LOCAL_ONLY):
        print(f"\n== {step}")
        if subprocess.run([sys.executable, str(ETL / step)], cwd=ETL, env=env).returncode != 0:
            print(f"\nStopped: {step} failed.")
            return 1
    print("\nAll dashboards built.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
