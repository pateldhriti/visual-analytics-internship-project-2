"""
Production job for the Story 1 affordability pipeline (StatCan table
98-10-0252-01, shelter-cost-to-income ratio by tenure): one command that
runs extract -> reshape -> warehouse load end-to-end and logs row counts at
every stage, replacing the old prototype workflow of running 4 separate
scripts by hand.

Reuses the existing, already-verified building blocks rather than
duplicating their logic:
  - etl/extract_windsor_shelter_cost.py      (raw CSV -> staging wide CSV)
  - etl/reshape_shelter_cost_long.py         (staging wide CSV -> long CSV;
    now also standardizes column names to snake_case and adds
    `data_quality_flag`, a readable translation of StatCan's raw symbol --
    see docs/peer_test_affordability_etl.md problems 1 and 2)
  - etl/load_warehouse_facts.py's load_shelter_cost_facts() (long CSV ->
    warehouse.fact_shelter_cost)

Safe to re-run: truncates warehouse.fact_shelter_cost before loading (only
this one table -- not the other fact tables load_warehouse_facts.py's own
__main__ block truncates together).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\run_affordability_etl.py
"""

import logging

from sqlalchemy import text

import extract_windsor_shelter_cost as extract_stage
import reshape_shelter_cost_long as reshape_stage
from load_warehouse_facts import load_shelter_cost_facts
from load_windsor_shelter_cost_to_postgres import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger("affordability_etl")


def run() -> dict:
    logger.info("Stage 1/3: extract Windsor rows from the raw StatCan source")
    extract_stats = extract_stage.extract_windsor_rows()
    logger.info("Stage 1/3 complete: %d rows extracted -> %s",
                extract_stats["total_written_rows"], extract_stats["output_csv"])

    logger.info("Stage 2/3: reshape wide -> long, add data_quality_flag")
    source = reshape_stage.load_source()
    long_df = reshape_stage.reshape_long(source)
    checks = reshape_stage.verify_preserves_original(source, long_df)
    if checks["round_trip_mismatches"]:
        raise RuntimeError(
            f"Reshape integrity check failed: {len(checks['round_trip_mismatches'])} "
            f"round-trip mismatches, e.g. {checks['round_trip_mismatches'][:3]}"
        )
    if not checks["cell_count_preserved"] or not checks["non_null_value_count_preserved"] \
            or not checks["symbol_count_preserved"]:
        raise RuntimeError(f"Reshape integrity check failed: {checks}")
    reshape_stage.OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(reshape_stage.OUTPUT_CSV, index=False)
    logger.info("Stage 2/3 complete: %d rows -> %s (integrity checks passed)",
                len(long_df), reshape_stage.OUTPUT_CSV)

    logger.info("Stage 3/3: load into warehouse.fact_shelter_cost")
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE warehouse.fact_shelter_cost"))
    load_stats = load_shelter_cost_facts(engine)
    if any(load_stats["unmatched_dimension_keys"].values()):
        raise RuntimeError(f"Unmatched dimension keys on load: {load_stats['unmatched_dimension_keys']}")
    logger.info("Stage 3/3 complete: %d rows loaded into warehouse.fact_shelter_cost",
                load_stats["loaded_rows"])

    return {
        "extracted_rows": extract_stats["total_written_rows"],
        "reshaped_rows": len(long_df),
        "loaded_rows": load_stats["loaded_rows"],
    }


if __name__ == "__main__":
    summary = run()
    logger.info("Affordability ETL complete: %s", summary)
