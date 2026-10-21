"""
Shared ETL framework: one config file per dataset, one loader that applies
to all of them. Each dataset declares its own expected column set; the
loader validates the staging CSV against that declaration and stops
(raises) on any unexpected or missing column instead of silently loading
whatever happens to be in the file, logs every step via `logging`, and
records one row per load attempt -- success or failed -- in
raw.load_audit (see sql/load_audit_schema.sql), regardless of outcome.

Scope: this framework targets already-cleaned, flat staging CSVs with a
known, stable column set (produced by this project's extract/reshape
scripts) -- not the raw-landing load (etl/load_raw_files_to_postgres.py,
which deliberately has NO schema, by design, since it accepts any raw file
as-is) and not the warehouse fact loaders (etl/load_warehouse_facts.py,
which additionally resolve dimension foreign keys, a different job from a
flat schema-validated load).

Config file shape (see etl/configs/*.yaml for real examples):
    name: windsor_shelter_cost_long
    csv_path: data/staging/windsor_shelter_cost_long.csv
    schema: public
    table: windsor_shelter_cost_long
    expected_columns: [ref_date, geo, dguid, ...]
    column_rename: {}            # optional, applied before validation
    numeric_columns: [value]     # optional, coerced via pd.to_numeric

Run a single dataset:
    .venv\\Scripts\\python.exe -c "from etl_framework import load_dataset, get_engine; load_dataset('configs/windsor_shelter_cost_long.yaml', get_engine())"

Or run every configured dataset:
    .venv\\Scripts\\python.exe etl\\run_framework_loads.py
"""

import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy import text

from load_windsor_shelter_cost_to_postgres import get_engine  # noqa: F401 (re-exported for callers)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger("etl_framework")


@dataclass
class DatasetConfig:
    name: str
    csv_path: str
    schema: str
    table: str
    expected_columns: list[str]
    column_rename: dict[str, str] = field(default_factory=dict)
    numeric_columns: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "DatasetConfig":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            name=raw["name"],
            csv_path=raw["csv_path"],
            schema=raw["schema"],
            table=raw["table"],
            expected_columns=raw["expected_columns"],
            column_rename=raw.get("column_rename", {}),
            numeric_columns=raw.get("numeric_columns", []),
        )


class SchemaValidationError(ValueError):
    """Raised when a staging CSV's columns don't exactly match what its config declares."""


def _write_audit_row(engine, *, dataset_name, file_name, target_table,
                      rows_loaded, started_at, finished_at, status, error_message) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO raw.load_audit "
                "(dataset_name, file_name, target_table, rows_loaded, started_at, finished_at, status, error_message) "
                "VALUES (:dataset_name, :file_name, :target_table, :rows_loaded, :started_at, :finished_at, :status, :error_message)"
            ),
            {
                "dataset_name": dataset_name, "file_name": file_name, "target_table": target_table,
                "rows_loaded": rows_loaded, "started_at": started_at, "finished_at": finished_at,
                "status": status, "error_message": error_message,
            },
        )


def load_dataset(config_path: str | Path, engine) -> dict:
    """Load one dataset per its config: validate columns, load, log, audit.

    Raises SchemaValidationError (after still recording the failed attempt
    in raw.load_audit) if the CSV's columns -- after applying
    column_rename -- don't exactly match expected_columns: extra columns
    the config doesn't know about, or columns the config expects that
    aren't there, both count as drift and both stop the load.
    """
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / "etl" / config_path
    config = DatasetConfig.from_yaml(config_path)

    csv_path = PROJECT_ROOT / config.csv_path
    target_table = f"{config.schema}.{config.table}"
    started_at = datetime.datetime.now(datetime.timezone.utc)
    logger.info("[%s] loading %s -> %s", config.name, csv_path, target_table)

    if not csv_path.exists():
        finished_at = datetime.datetime.now(datetime.timezone.utc)
        error = f"Staging CSV not found: {csv_path}"
        _write_audit_row(engine, dataset_name=config.name, file_name=str(config.csv_path),
                          target_table=target_table, rows_loaded=None, started_at=started_at,
                          finished_at=finished_at, status="failed", error_message=error)
        raise FileNotFoundError(error)

    df = pd.read_csv(csv_path, dtype=str)
    if config.column_rename:
        df = df.rename(columns=config.column_rename)

    actual = set(df.columns)
    expected = set(config.expected_columns)
    if actual != expected:
        unexpected = sorted(actual - expected)
        missing = sorted(expected - actual)
        finished_at = datetime.datetime.now(datetime.timezone.utc)
        error = f"Schema drift in {csv_path}: unexpected columns {unexpected}, missing columns {missing}"
        logger.error("[%s] %s", config.name, error)
        _write_audit_row(engine, dataset_name=config.name, file_name=str(config.csv_path),
                          target_table=target_table, rows_loaded=None, started_at=started_at,
                          finished_at=finished_at, status="failed", error_message=error)
        raise SchemaValidationError(error)

    for col in config.numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    try:
        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.schema}"))
        df.to_sql(config.table, engine, schema=config.schema, if_exists="replace", index=False)
    except Exception as exc:
        finished_at = datetime.datetime.now(datetime.timezone.utc)
        _write_audit_row(engine, dataset_name=config.name, file_name=str(config.csv_path),
                          target_table=target_table, rows_loaded=None, started_at=started_at,
                          finished_at=finished_at, status="failed", error_message=str(exc))
        raise

    finished_at = datetime.datetime.now(datetime.timezone.utc)
    rows = len(df)
    _write_audit_row(engine, dataset_name=config.name, file_name=str(config.csv_path),
                      target_table=target_table, rows_loaded=rows, started_at=started_at,
                      finished_at=finished_at, status="success", error_message=None)
    logger.info("[%s] loaded %d rows into %s", config.name, rows, target_table)

    return {"dataset": config.name, "target_table": target_table, "rows_loaded": rows,
            "started_at": started_at.isoformat(), "finished_at": finished_at.isoformat()}
