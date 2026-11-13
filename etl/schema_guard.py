"""
Schema guard: check that every raw source file still has the columns the
extract scripts were written for, before the pipeline reads it.

StatCan and CMHC occasionally rename, add or drop columns, or move a
table to another sheet. The extract scripts read fixed column names and
fixed header rows, so a change like that would either crash halfway
through a refresh or, worse, load the wrong numbers. This guard compares
each file's structure with a saved snapshot (etl/configs/source_schemas.json)
and stops with a clear report if anything differs.

What is compared:
  - CSV files (and the CSV inside the StatCan zip): the header row.
  - Excel workbooks: the list of sheets, and every sheet's title and
    column-heading rows (up to HEADER_ROWS rows, stopping at the first row
    of values).
Numbers inside headers are replaced by "#" before comparing, so a new
edition with new years ("Oct-25" -> "Oct-26", "2025" -> "2026") passes,
while a renamed, added, removed or reordered column fails.

Usage (from the project root):
    .venv\\Scripts\\python.exe etl\\schema_guard.py            # check; exit 1 on drift
    .venv\\Scripts\\python.exe etl\\schema_guard.py --update   # save current files as the snapshot

Only run --update after reviewing a reported change and updating the
affected extract script to match it.
"""

import csv
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = Path(__file__).resolve().parent / "configs" / "source_schemas.json"
HEADER_ROWS = 8


@dataclass(frozen=True)
class Source:
    name: str
    path: str  # relative to the project root
    kind: str  # "csv" | "zip_csv" | "xlsx"
    member: str = ""  # file inside the zip, for kind == "zip_csv"


SOURCES = [
    Source("statcan_shelter_cost", "data/raw/shelter_cost/98100252.csv", "csv"),
    Source("statcan_census_profile", "data/raw/statcan/98-401-X2021002_English_CSV_data.csv", "csv"),
    Source("statcan_windsor_starts", "data/raw/statcan/34100154-eng.zip", "zip_csv", "34100154.csv"),
    Source("cmhc_rms_windsor_2025", "data/raw/cmhc/rmr-windsor-2025-en.xlsx", "xlsx"),
    Source("cmhc_rms_windsor_2024", "data/raw/cmhc/rmr-windsor-2024-en.xlsx", "xlsx"),
    Source("cmhc_rms_windsor_2023", "data/raw/cmhc/rmr-windsor-2023-en.xlsx", "xlsx"),
    Source("cmhc_rms_windsor_2022", "data/raw/cmhc/rmr-windsor-2022-en.xlsx", "xlsx"),
    Source("cmhc_rms_windsor_2021", "data/raw/cmhc/rmr-windsor-2021-en.xlsx", "xlsx"),
    Source("cmhc_rms_canada_2025", "data/raw/cmhc/rmr-canada-2025-en.xlsx", "xlsx"),
    Source(
        "cmhc_quarterly_starts",
        "data/raw/cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx",
        "xlsx",
    ),
    # Story 4's ten-year rents and vacancy and Story 5's comparison cities
    # (etl/extract_peer_cma_context.py). The two ten-year tables are
    # downloaded on every scheduled run, before this check.
    Source("statcan_rent_history", "data/raw/statcan/34100133-eng.zip", "zip_csv", "34100133.csv"),
    Source("statcan_vacancy_history", "data/raw/statcan/34100130-eng.zip", "zip_csv", "34100130.csv"),
    Source("statcan_housing_by_age", "data/raw/statcan/98100241-eng.zip", "zip_csv", "98100241.csv"),
    *[
        Source(f"cmhc_peer_rms_{city}_2025", f"data/raw/cmhc/peer_rms_2025/rmr-{city}-2025-en.xlsx", "xlsx")
        for city in ("windsor", "london", "hamilton", "st-catharines-niagara", "kitchener-cambridge-waterloo")
    ],
]


def normalize(value) -> str:
    """Header text with whitespace collapsed and every run of digits
    replaced by '#', so year changes don't count as drift."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return re.sub(r"\d+", "#", text)


DATA_CELL = re.compile(r"^(\*\*|[#.,%$+\- ]*#[#.,%$+\- ]*)$")


def is_data_row(cells: list[str]) -> bool:
    """True for the first row of table values rather than headings: a row
    with a number or CMHC's suppression mark ('**') in it. Header rows only
    hold text such as 'Studio' or 'Oct-#'. Data rows carry values, grades
    and arrows that change every edition, so they are not compared."""
    return any(DATA_CELL.match(cell) for cell in cells)


def csv_header(stream) -> list[str]:
    reader = csv.reader(stream)
    return [normalize(col) for col in next(reader, [])]


def read_structure(source: Source, root: Path = PROJECT_ROOT) -> dict:
    """Return the comparable structure of one source file."""
    path = root / source.path
    if not path.exists():
        raise FileNotFoundError(f"{source.path} not found")

    if source.kind == "csv":
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            return {"columns": csv_header(fh)}

    if source.kind == "zip_csv":
        with zipfile.ZipFile(path) as zf:
            with zf.open(source.member) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                return {"columns": csv_header(text)}

    if source.kind == "xlsx":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            sheets = {}
            for ws in wb.worksheets:
                rows = []
                for row in ws.iter_rows(min_row=1, max_row=HEADER_ROWS, values_only=True):
                    cells = [normalize(cell) for cell in row if cell not in (None, "")]
                    if is_data_row(cells):
                        break
                    rows.append(cells)
                sheets[ws.title] = rows
            return {"sheets": sheets}
        finally:
            wb.close()

    raise ValueError(f"unknown source kind: {source.kind}")


def compare(name: str, expected: dict, found: dict) -> list[str]:
    """Human-readable differences between a snapshot and the current file."""
    problems = []
    if "columns" in expected:
        exp, cur = expected["columns"], found.get("columns", [])
        missing = [c for c in exp if c not in cur]
        added = [c for c in cur if c not in exp]
        if missing:
            problems.append(f"{name}: columns removed or renamed: {missing}")
        if added:
            problems.append(f"{name}: new columns: {added}")
        if not missing and not added and exp != cur:
            problems.append(f"{name}: columns are in a different order")
        return problems

    exp_sheets, cur_sheets = expected["sheets"], found.get("sheets", {})
    for sheet in exp_sheets:
        if sheet not in cur_sheets:
            problems.append(f"{name}: sheet '{sheet}' is missing")
    for sheet in cur_sheets:
        if sheet not in exp_sheets:
            problems.append(f"{name}: new sheet '{sheet}'")
    for sheet, exp_rows in exp_sheets.items():
        cur_rows = cur_sheets.get(sheet)
        if cur_rows is None:
            continue
        for i, (exp_row, cur_row) in enumerate(zip(exp_rows, cur_rows), start=1):
            if exp_row != cur_row:
                problems.append(f"{name}: sheet '{sheet}' header row {i} changed: expected {exp_row}, found {cur_row}")
        if len(exp_rows) != len(cur_rows):
            problems.append(
                f"{name}: sheet '{sheet}' has {len(cur_rows)} header rows, expected {len(exp_rows)}"
            )
    return problems


def load_snapshot(path: Path | None = None) -> dict:
    with open(path or SNAPSHOT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def check(sources=SOURCES, root: Path = PROJECT_ROOT, snapshot: dict | None = None) -> list[str]:
    """Return a list of problems; an empty list means every source matches."""
    snapshot = load_snapshot() if snapshot is None else snapshot
    problems = []
    for source in sources:
        if source.name not in snapshot:
            problems.append(f"{source.name}: no saved snapshot (run schema_guard.py --update)")
            continue
        try:
            found = read_structure(source, root)
        except (FileNotFoundError, KeyError, zipfile.BadZipFile, OSError) as exc:
            problems.append(f"{source.name}: cannot read {source.path}: {exc}")
            continue
        problems.extend(compare(source.name, snapshot[source.name], found))
    return problems


def update(sources=SOURCES, root: Path = PROJECT_ROOT, path: Path | None = None) -> dict:
    snapshot = {source.name: {"path": source.path, **read_structure(source, root)} for source in sources}
    path = path or SNAPSHOT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(snapshot, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return snapshot


def main(argv: list[str]) -> int:
    if "--update" in argv:
        update()
        print(f"Snapshot saved for {len(SOURCES)} sources: {SNAPSHOT_PATH.relative_to(PROJECT_ROOT)}")
        return 0

    problems = check()
    if problems:
        print(f"SCHEMA GUARD FAILED: {len(problems)} change(s) in the source files:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"Schema guard passed: {len(SOURCES)} source files match the saved snapshot.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
