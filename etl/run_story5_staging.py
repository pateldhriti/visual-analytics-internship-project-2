"""
Story 5 staging orchestrator (additive; never touches existing outputs).

  1. verify raw integrity: etl/raw_manifest.json (StatsCan ZIP, CMHC 2025 ...),
     etl/raw_history_manifest.json (Windsor history workbooks) and
     etl/raw_canada_history_manifest.json (CMHC Canada 2019-2024)
  2. on first run only, fingerprint the existing verified staging outputs
     (etl/story5_pre_staging_baseline.json; never overwritten)
  3. build etl/cma_geography_map.csv
  4. write the three Story 5 staging files
  5. re-verify raw integrity and that existing staging outputs are unchanged

    .venv\\Scripts\\python.exe etl\\run_story5_staging.py [--init-manifest]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import build_cma_geography_map
import clean_cma_housing_profile
import clean_cma_rental_history
import clean_cma_rental_universe
from clean_windsor_rental_history import verify_history_manifest
from cleaning_common import verify_raw_manifest
from story5_common import (
    CANADA_HISTORY_MANIFEST, EXISTING_STAGING, GEOGRAPHY_MAP_PATH, NEW_HISTORY_WORKBOOKS, RAW_DIR,
    STAGING_BASELINE_PATH, STAGING_DIR, snapshot_files, verify_snapshot,
)


def init_manifest(raw_dir: Path = RAW_DIR, path: Path = CANADA_HISTORY_MANIFEST) -> bool:
    if path.exists():
        return False
    path.write_text(json.dumps(snapshot_files(NEW_HISTORY_WORKBOOKS, raw_dir), indent=2) + "\n", encoding="utf-8")
    return True


def raw_problems(raw_dir: Path = RAW_DIR) -> list[str]:
    return (verify_raw_manifest(raw_dir) + verify_history_manifest(raw_dir)
            + verify_snapshot(CANADA_HISTORY_MANIFEST, raw_dir))


def run(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR, map_path: Path = GEOGRAPHY_MAP_PATH,
        guard_existing: bool = True) -> dict:
    problems = raw_problems(raw_dir)
    if problems:
        raise RuntimeError("raw integrity check failed before run: " + "; ".join(problems))
    if guard_existing:
        if not STAGING_BASELINE_PATH.exists():
            STAGING_BASELINE_PATH.write_text(
                json.dumps(snapshot_files(EXISTING_STAGING, STAGING_DIR), indent=2) + "\n", encoding="utf-8")
        problems = verify_snapshot(STAGING_BASELINE_PATH, STAGING_DIR)
        if problems:
            raise RuntimeError("existing staging outputs differ from baseline: " + "; ".join(problems))
    geo = build_cma_geography_map.write(raw_dir, map_path)
    results = {
        "geography_map": {"output": map_path, "rows": len(geo)},
        "rental_history": clean_cma_rental_history.clean(raw_dir, out_dir, map_path),
        "housing_profile": clean_cma_housing_profile.clean(raw_dir, out_dir),
        "rental_universe": clean_cma_rental_universe.clean(raw_dir, out_dir, map_path),
    }
    problems = raw_problems(raw_dir)
    if guard_existing:
        problems += verify_snapshot(STAGING_BASELINE_PATH, STAGING_DIR)
    if problems:
        raise RuntimeError("post-run integrity check failed: " + "; ".join(problems))
    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--init-manifest", action="store_true", help="record SHA-256 of the 6 new CMHC workbooks (once)")
    a = p.parse_args()
    if a.init_manifest:
        print("manifest written" if init_manifest() else f"manifest exists, not overwritten: {CANADA_HISTORY_MANIFEST}")
    for name, r in run().items():
        print(f"{name:16s} {r['rows']:5d} rows -> {r['output']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
