"""
Tests for the schema guard and the scheduled refresh's stop-and-alert
behaviour. They use small files written to a temporary folder, so they
need no database, network or data/raw files.

Run from the etl directory:
    python -m pytest test_scheduled_refresh.py -v
"""

import json
import zipfile

import openpyxl
import pytest
import requests

import scheduled_refresh
import schema_guard
from schema_guard import Source

CSV_SOURCE = Source("csv_source", "raw/table.csv", "csv")
ZIP_SOURCE = Source("zip_source", "raw/table.zip", "zip_csv", "table.csv")
XLSX_SOURCE = Source("xlsx_source", "raw/book.xlsx", "xlsx")


def write_csv(root, header):
    path = root / "raw" / "table.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("﻿" + header + "\n1,2,3\n", encoding="utf-8")


def write_zip(root, header):
    path = root / "raw" / "table.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("table.csv", "﻿" + header + "\n1,2,3\n")


def write_xlsx(root, bedroom_heading="Studio", survey="Oct-25", extra_sheet=False):
    path = root / "raw" / "book.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Table 1.1.1"
    ws["A1"] = "1.1.1 Vacancy Rates (%) - Windsor CMA"
    ws.append([None, bedroom_heading, "1 Bedroom", "Total"])
    ws.append(["Zone", survey, survey, survey])
    # Data rows: values and grades change every edition and must not count.
    ws.append(["Zone 1 - Centre", 4.6, "c", "↑"])
    if extra_sheet:
        wb.create_sheet("Table 9.9")
    wb.save(path)


@pytest.fixture
def files(tmp_path):
    write_csv(tmp_path, "REF_DATE,GEO,VALUE")
    write_zip(tmp_path, '"REF_DATE","GEO","VALUE"')
    write_xlsx(tmp_path)
    sources = [CSV_SOURCE, ZIP_SOURCE, XLSX_SOURCE]
    snapshot_path = tmp_path / "snapshot.json"
    schema_guard.update(sources, tmp_path, snapshot_path)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return tmp_path, sources, snapshot


def test_unchanged_files_pass(files):
    root, sources, snapshot = files
    assert schema_guard.check(sources, root, snapshot) == []


def test_new_edition_with_new_years_and_values_passes(files):
    root, sources, snapshot = files
    write_xlsx(root, survey="Oct-26")
    assert schema_guard.check(sources, root, snapshot) == []


def test_renamed_csv_column_fails(files):
    root, sources, snapshot = files
    write_csv(root, "REF_DATE,GEOGRAPHY,VALUE")
    problems = schema_guard.check(sources, root, snapshot)
    assert len(problems) == 2  # GEO removed, GEOGRAPHY added
    assert "GEO" in problems[0]


def test_added_column_in_zip_fails(files):
    root, sources, snapshot = files
    write_zip(root, '"REF_DATE","GEO","VALUE","STATUS"')
    problems = schema_guard.check(sources, root, snapshot)
    assert problems == ["zip_source: new columns: ['STATUS']"]


def test_reordered_columns_fail(files):
    root, sources, snapshot = files
    write_csv(root, "GEO,REF_DATE,VALUE")
    assert schema_guard.check(sources, root, snapshot) == ["csv_source: columns are in a different order"]


def test_renamed_excel_heading_fails(files):
    # The real case between CMHC's 2024 and 2025 workbooks: "Bachelor" became "Studio".
    root, sources, snapshot = files
    write_xlsx(root, bedroom_heading="Bachelor")
    problems = schema_guard.check(sources, root, snapshot)
    assert len(problems) == 1 and "Bachelor" in problems[0]


def test_new_sheet_fails(files):
    root, sources, snapshot = files
    write_xlsx(root, extra_sheet=True)
    assert schema_guard.check(sources, root, snapshot) == ["xlsx_source: new sheet 'Table 9.9'"]


def test_missing_file_fails(files):
    root, sources, snapshot = files
    (root / "raw" / "table.csv").unlink()
    problems = schema_guard.check(sources, root, snapshot)
    assert len(problems) == 1 and "cannot read" in problems[0]


def test_data_rows_are_not_part_of_the_snapshot(files):
    _, _, snapshot = files
    rows = snapshot["xlsx_source"]["sheets"]["Table 1.1.1"]
    assert rows[-1] == ["Zone", "Oct-#", "Oct-#", "Oct-#"]


class FakeLog:
    def __init__(self, tmp_path):
        self.lines = []
        self.path = tmp_path / "run.log"

    def __call__(self, message=""):
        self.lines.append(message)


@pytest.fixture
def refresh_env(tmp_path, monkeypatch):
    """Point the alert log at a temp folder and record pipeline steps
    instead of running them."""
    monkeypatch.setattr(scheduled_refresh, "ALERT_LOG", tmp_path / "alerts.log")
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    ran = []
    monkeypatch.setattr(scheduled_refresh, "run_script", lambda script, log, args=None: ran.append(script) or True)
    return tmp_path, ran


def test_schema_drift_stops_the_pipeline_and_alerts(refresh_env, monkeypatch):
    tmp_path, ran = refresh_env
    monkeypatch.setattr(schema_guard, "check", lambda: ["csv_source: new columns: ['STATUS']"])

    code = scheduled_refresh.run(download=False, log=FakeLog(tmp_path))

    assert code == scheduled_refresh.EXIT_SCHEMA
    assert ran == []  # nothing extracted or loaded
    assert "schema guard found 1 change" in (tmp_path / "alerts.log").read_text(encoding="utf-8")


def test_clean_run_runs_every_step_in_order(refresh_env, monkeypatch):
    tmp_path, ran = refresh_env
    monkeypatch.setattr(schema_guard, "check", lambda: [])

    code = scheduled_refresh.run(download=False, log=FakeLog(tmp_path))

    assert code == scheduled_refresh.EXIT_OK
    assert ran == scheduled_refresh.EXTRACT_STEPS + [scheduled_refresh.LOAD_STEP]
    assert not (tmp_path / "alerts.log").exists()


def test_failed_step_stops_and_alerts(refresh_env, monkeypatch):
    tmp_path, ran = refresh_env
    monkeypatch.setattr(schema_guard, "check", lambda: [])
    monkeypatch.setattr(
        scheduled_refresh,
        "run_script",
        lambda script, log, args=None: ran.append(script) or script != "extract_windsor_rms.py",
    )

    code = scheduled_refresh.run(download=False, log=FakeLog(tmp_path))

    assert code == scheduled_refresh.EXIT_PIPELINE
    assert ran[-1] == "extract_windsor_rms.py"
    assert scheduled_refresh.LOAD_STEP not in ran
    assert "extract_windsor_rms.py failed" in (tmp_path / "alerts.log").read_text(encoding="utf-8")


def test_alert_is_posted_to_the_webhook(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduled_refresh, "ALERT_LOG", tmp_path / "alerts.log")
    posted = {}

    class Response:
        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        posted.update(url=url, json=json)
        return Response()

    monkeypatch.setattr(scheduled_refresh.requests, "post", fake_post)
    scheduled_refresh.send_alert("test failure", FakeLog(tmp_path), webhook_url="https://example.org/hook")

    assert posted["url"] == "https://example.org/hook"
    assert "test failure" in posted["json"]["text"]


def test_ten_year_tables_and_comparison_workbooks_are_guarded():
    guarded = {source.path for source in schema_guard.SOURCES}
    assert "data/raw/statcan/34100133-eng.zip" in guarded  # rents, downloaded every run
    assert "data/raw/statcan/34100130-eng.zip" in guarded  # vacancy, downloaded every run
    assert "data/raw/statcan/98100241-eng.zip" in guarded
    assert "data/raw/cmhc/peer_rms_2025/rmr-london-2025-en.xlsx" in guarded
    names = [source.name for source in schema_guard.SOURCES]
    assert len(names) == len(set(names))  # each source keeps its own snapshot entry


def test_downloads_happen_before_the_guard_and_not_again_after_it(refresh_env, monkeypatch):
    """The ten-year tables are downloaded before the schema guard checks them;
    the extract that reads them is told not to download them again."""
    tmp_path, _ = refresh_env
    events = []
    monkeypatch.setattr(scheduled_refresh, "download_latest", lambda log: events.append("download"))
    monkeypatch.setattr(schema_guard, "check", lambda: events.append("guard") or [])
    monkeypatch.setattr(
        scheduled_refresh,
        "run_script",
        lambda script, log, args=None: events.append((script, tuple(args or ()))) or True,
    )

    code = scheduled_refresh.run(download=True, log=FakeLog(tmp_path))

    assert code == scheduled_refresh.EXIT_OK
    assert events[:2] == ["download", "guard"]
    assert ("extract_peer_cma_context.py", ("--no-download",)) in events


def test_failed_download_stops_before_the_guard(refresh_env, monkeypatch):
    tmp_path, ran = refresh_env

    def fail(log):
        raise requests.ConnectionError("StatCan unreachable")

    monkeypatch.setattr(scheduled_refresh, "download_latest", fail)
    monkeypatch.setattr(schema_guard, "check", lambda: pytest.fail("guard ran after a failed download"))

    assert scheduled_refresh.run(download=True, log=FakeLog(tmp_path)) == scheduled_refresh.EXIT_DOWNLOAD
    assert ran == []
    assert "download of the latest StatCan tables failed" in (tmp_path / "alerts.log").read_text(encoding="utf-8")
