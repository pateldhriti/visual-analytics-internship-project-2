"""
Weekly scheduled refresh: download the latest monthly data, check every
source file's columns with the schema guard, and only then re-run the
pipeline. Any failure stops the run and raises an alert.

Steps:
  1. Download the latest StatCan 34-10-0154-01 zip (Windsor housing
     starts, updated monthly) and the two ten-year tables, 34-10-0133-01
     (rents) and 34-10-0130-01 (vacancy), which gain a year each October.
     The other sources are annual CMHC/Census files; they are checked but
     not downloaded. Skip with --no-download.
  2. Schema guard (etl/schema_guard.py). If any file's columns, sheets or
     header rows changed, stop before anything is read or loaded, so the
     database and dashboards keep the last good data.
  3. Extract and reshape every source into data/staging (EXTRACT_STEPS).
  4. etl/refresh_all.py: rebuild the warehouse, views and Superset datasets.

Alerts: on failure, a line is appended to logs/refresh_alerts.log and,
if ALERT_WEBHOOK_URL is set in .env, the message is posted to it as
{"text": ...} -- the format Microsoft Teams and Slack incoming webhooks
accept. Every run also writes its full output to
logs/scheduled_refresh_<UTC time>.log.

Exit codes: 0 success, 1 download failed, 2 schema guard failed,
3 a pipeline step failed. Task Scheduler and cron record a non-zero exit
as a failed run.

Schedule it weekly with etl/register_weekly_refresh.ps1 (Windows) or the
cron line in etl/README.md (Linux server).

Run from the project root:
    .venv\\Scripts\\python.exe etl\\scheduled_refresh.py
    .venv\\Scripts\\python.exe etl\\scheduled_refresh.py --no-download
    .venv\\Scripts\\python.exe etl\\scheduled_refresh.py --check-only   # download + guard, no loading
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

import schema_guard

ETL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ETL_DIR.parent
LOG_DIR = PROJECT_ROOT / "logs"
ALERT_LOG = LOG_DIR / "refresh_alerts.log"

# Source files -> data/staging, in the order etl/README.md documents.
EXTRACT_STEPS = [
    "extract_windsor_shelter_cost.py",
    "reshape_shelter_cost_long.py",
    "extract_windsor_census_profile.py",
    "reshape_census_profile_long.py",
    "extract_windsor_rms.py",
    "extract_windsor_rms_historical.py",
    "extract_rms_canada_comparison.py",
    "extract_cmhc_starts_completions.py",
    "extract_windsor_starts_completions.py",
    "extract_peer_cma_context.py",
]
# Steps run with extra arguments: the ten-year tables were downloaded and
# checked above, so the extract must not download them again after the guard.
STEP_ARGS = {"extract_peer_cma_context.py": ["--no-download"]}
LOAD_STEP = "refresh_all.py"

EXIT_OK, EXIT_DOWNLOAD, EXIT_SCHEMA, EXIT_PIPELINE = 0, 1, 2, 3


class RunLog:
    """Writes each line to the console and to this run's log file."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._fh = open(path, "a", encoding="utf-8")

    def __call__(self, message: str = "") -> None:
        print(message, flush=True)
        self._fh.write(message + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def send_alert(message: str, log: RunLog, webhook_url: str | None = None) -> None:
    """Record a failure where someone will see it."""
    line = f"{now_utc()}  {message}"
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERT_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    log(f"ALERT: {message}")

    webhook_url = webhook_url if webhook_url is not None else os.environ.get("ALERT_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        resp = requests.post(
            webhook_url,
            json={"text": f"Windsor Housing weekly refresh failed: {message}"},
            timeout=15,
        )
        resp.raise_for_status()
        log("Alert sent to webhook.")
    except requests.exceptions.RequestException as exc:
        # The alert log above still has it; don't let a webhook outage hide the real failure.
        log(f"Could not send alert to webhook: {exc}")


def run_script(script: str, log: RunLog, args: list[str] | None = None) -> bool:
    """Run one etl/ script, copying its output into the run log."""
    log(f"\n=== {script} {' '.join(args or [])} ===")
    proc = subprocess.Popen(
        [sys.executable, str(ETL_DIR / script), *(args or [])],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        # Single-threaded maths library: numpy's OpenBLAS reserves memory
        # per CPU thread at import and failed to start ("Memory allocation
        # still failed") on a machine with little free RAM; one thread is
        # plenty for these file-processing steps.
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "OPENBLAS_NUM_THREADS": "1"},
    )
    for line in proc.stdout:
        log(line.rstrip())
    return proc.wait() == 0


def download_latest(log: RunLog) -> None:
    import extract_peer_cma_context as peers
    import extract_windsor_starts_completions as starts

    log("\n=== Download latest StatCan 34-10-0154-01, 34-10-0133-01 and 34-10-0130-01 ===")
    for path in (
        starts.download_source(refresh=True),
        peers.download_table(peers.RENT_HISTORY_ZIP),
        peers.download_table(peers.VACANCY_HISTORY_ZIP),
    ):
        log(f"Downloaded {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size // 1024} KB)")


def run(download: bool = True, check_only: bool = False, log: RunLog | None = None) -> int:
    log = log or RunLog(LOG_DIR / f"scheduled_refresh_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.log")
    log(f"Scheduled refresh started {now_utc()}")

    if download:
        try:
            download_latest(log)
        except Exception as exc:  # network, HTTP or disk error
            send_alert(f"download of the latest StatCan tables failed: {exc}", log)
            return EXIT_DOWNLOAD

    log("\n=== Schema guard ===")
    problems = schema_guard.check()
    if problems:
        for problem in problems:
            log(f"  - {problem}")
        send_alert(
            f"schema guard found {len(problems)} change(s) in the source files; nothing was loaded. "
            f"First: {problems[0]}",
            log,
        )
        return EXIT_SCHEMA
    log(f"All {len(schema_guard.SOURCES)} source files match the saved snapshot.")

    if check_only:
        log("\n--check-only: stopping before the pipeline.")
        return EXIT_OK

    for script in EXTRACT_STEPS:
        if not run_script(script, log, STEP_ARGS.get(script)):
            send_alert(f"{script} failed; the warehouse was not reloaded. See {log.path.name}.", log)
            return EXIT_PIPELINE

    if not run_script(LOAD_STEP, log):
        send_alert(f"{LOAD_STEP} failed. See {log.path.name}.", log)
        return EXIT_PIPELINE

    log(f"\nScheduled refresh finished {now_utc()}")
    return EXIT_OK


def main(argv: list[str]) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    log = RunLog(LOG_DIR / f"scheduled_refresh_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.log")
    try:
        return run(download="--no-download" not in argv, check_only="--check-only" in argv, log=log)
    finally:
        log.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
