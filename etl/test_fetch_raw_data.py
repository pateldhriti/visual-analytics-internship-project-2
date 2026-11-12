"""Tests for etl/fetch_raw_data.py, with a fake downloader (no network).

Run: .venv\Scripts\python.exe -m pytest etl\test_fetch_raw_data.py
"""

import zipfile

import fetch_raw_data as f


def _fake_download(calls):
    def fetch(url, target, unzip=()):
        calls.append(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        if unzip:
            for name in unzip:
                (target.parent / name).write_text("x")
        else:
            target.write_bytes(b"x")
    return fetch


def test_downloads_what_is_missing_and_lists_the_manual_files(tmp_path):
    calls = []
    missing = f.run(raw=tmp_path, fetch=_fake_download(calls))
    assert len(calls) == len([s for s in f.SOURCES if s.url])
    assert (tmp_path / "shelter_cost/98100252.csv").exists()  # taken out of its zip
    assert {s.path for s in missing} == {s.path for s in f.SOURCES if not s.url}


def test_existing_files_are_not_downloaded_again_unless_refreshing(tmp_path):
    f.run(raw=tmp_path, fetch=_fake_download([]))
    calls = []
    f.run(raw=tmp_path, fetch=_fake_download(calls))
    assert calls == []
    f.run(raw=tmp_path, refresh=True, fetch=_fake_download(calls))
    assert len(calls) == len([s for s in f.SOURCES if s.url])


def test_check_only_downloads_nothing(tmp_path):
    calls = []
    missing = f.run(raw=tmp_path, check_only=True, fetch=_fake_download(calls))
    assert calls == [] and len(missing) == len(f.SOURCES)


def test_census_profile_csv_is_unzipped_when_only_the_zip_is_there(tmp_path):
    zip_path = tmp_path / f.CENSUS_ZIP
    zip_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("98-401-X2021002_English_CSV_data.csv", "a,b\n")
    assert f.unzip_census_profile(tmp_path)
    assert (tmp_path / "statcan/98-401-X2021002_English_CSV_data.csv").read_text() == "a,b\n"
