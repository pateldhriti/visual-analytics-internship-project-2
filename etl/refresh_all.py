"""
One-command refresh: re-runs every load in order, from a fresh or
already-populated database, safely.

Scope decision, stated explicitly rather than silently assumed: this
covers the LOAD side of the pipeline (staging CSV -> Postgres -> SQL
views -> Superset datasets), not the EXTRACT side (raw source file ->
staging CSV). The extract scripts (etl/extract_*.py) hit real external
sources (StatCan, CMHC) over the network and are a separate, slower,
network-dependent stage -- re-running them on every refresh would be
slow and puts unnecessary repeat load on those services for data that
doesn't change between runs. etl/README.md already documents them as
their own stage; this script picks up from the staging CSVs they
produce. If the staging CSVs don't exist yet, run the extract scripts
first (see etl/README.md).

Runs, in order:
    1. create_warehouse_schema.py  -- (re)creates the dimensional model
    2. load_warehouse_facts.py     -- bulk-loads all fact tables
    3. run_framework_loads.py      -- loads every etl/configs/*.yaml dataset
    4. apply_sql_views.py          -- applies all 4 story*_views.sql files
    5. register_superset_datasets.py -- registers views as Superset datasets
       (skipped automatically if Superset isn't reachable -- Postgres-only
       refreshes, e.g. in CI, are a legitimate use case and shouldn't fail
       just because Superset isn't running)

Every step is independently idempotent (each is documented and verified
safe to re-run on its own -- see each script's own docstring), which is
what makes running all 5 in sequence safe to run twice. Stops at the
first failing step rather than continuing, since every later step
depends on the ones before it having actually succeeded.

Requires a running Postgres instance and a .env file with
POSTGRES_HOST/PORT/DB/USER/PASSWORD/SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD (see .env.example). Superset is optional --
steps 1-4 only need Postgres.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\refresh_all.py
    .venv\\Scripts\\python.exe etl\\refresh_all.py --skip-superset
"""

import subprocess
import sys
import time
from pathlib import Path

import requests

ETL_DIR = Path(__file__).resolve().parent
SUPERSET_URL = "http://localhost:8088"
SUPERSET_HEALTH_TIMEOUT = 3

STEPS = [
    "create_warehouse_schema.py",
    "load_warehouse_facts.py",
    "run_framework_loads.py",
    "apply_sql_views.py",
]
SUPERSET_STEP = "register_superset_datasets.py"


def superset_reachable() -> bool:
    try:
        resp = requests.get(f"{SUPERSET_URL}/health", timeout=SUPERSET_HEALTH_TIMEOUT)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def run_step(script_name: str) -> float:
    script_path = ETL_DIR / script_name
    start = time.monotonic()
    print(f"\n=== {script_name} ===", flush=True)
    subprocess.run([sys.executable, str(script_path)], check=True)
    return time.monotonic() - start


def main(skip_superset: bool) -> None:
    results = []

    for script_name in STEPS:
        elapsed = run_step(script_name)
        results.append((script_name, elapsed))

    if skip_superset:
        print("\n=== register_superset_datasets.py: skipped (--skip-superset) ===", flush=True)
    elif superset_reachable():
        elapsed = run_step(SUPERSET_STEP)
        results.append((SUPERSET_STEP, elapsed))
    else:
        print(
            f"\n=== {SUPERSET_STEP}: skipped (Superset not reachable at {SUPERSET_URL}) ===",
            flush=True,
        )

    print("\n--- Refresh complete ---")
    for name, elapsed in results:
        print(f"  {name}: {elapsed:.1f}s")


if __name__ == "__main__":
    main(skip_superset="--skip-superset" in sys.argv)
