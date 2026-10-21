"""
Run every dataset configured under etl/configs/*.yaml through the shared
ETL framework (etl/etl_framework.py): schema-validated load, logged, with
one row per attempt written to raw.load_audit regardless of outcome.

One dataset's schema drift doesn't stop the others -- each is tried
independently and the run ends with a clear pass/fail summary, so a single
bad file doesn't hide whether the rest of the datasets loaded fine.

Run from the project virtual environment (after sql/load_audit_schema.sql
has been applied once, e.g. via a client against your Postgres instance):
    .venv\\Scripts\\python.exe etl\\run_framework_loads.py
"""

from pathlib import Path

from sqlalchemy import text

from etl_framework import get_engine, load_dataset, logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
AUDIT_SCHEMA_SQL = PROJECT_ROOT / "sql" / "load_audit_schema.sql"


def ensure_audit_table(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(AUDIT_SCHEMA_SQL.read_text(encoding="utf-8")))


def run() -> list[dict]:
    engine = get_engine()
    ensure_audit_table(engine)

    results = []
    for config_path in sorted(CONFIGS_DIR.glob("*.yaml")):
        try:
            result = load_dataset(config_path, engine)
            results.append({**result, "status": "success"})
        except Exception as exc:
            logger.error("Dataset at %s failed: %s", config_path.name, exc)
            results.append({"dataset": config_path.stem, "status": "failed", "error": str(exc)})

    return results


if __name__ == "__main__":
    summary = run()
    succeeded = sum(1 for r in summary if r["status"] == "success")
    logger.info("Framework run complete: %d/%d datasets loaded successfully", succeeded, len(summary))
    for r in summary:
        logger.info("  %s", r)
