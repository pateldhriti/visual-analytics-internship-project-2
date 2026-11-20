r"""
Windsor housing starts and completions by intended market (homeowner,
rental, condo, co-op), for Story 3's tab "Pipeline and Intended Market".

    .venv\Scripts\python.exe etl\extract_windsor_intended_market.py

Source: CMHC Housing Market Information Portal, Windsor (CMA), New Housing
Construction, by Intended Markets, exported as CSV (the portal names each
file TableExport.csv). The portal has no download link a script can use, so
the files are downloaded by hand (etl/fetch_raw_data.py lists them):

    windsor-starts-intended-market.csv        Starts (Actual), Historical
                                              Time Periods, Annual: one row
                                              per year
    windsor-starts-intended-market-ytd.csv    Starts (Actual), Survey Zones,
                                              Monthly + Cumulative to the
                                              latest month: the "Windsor"
                                              row is the CMA so far this year
    windsor-completions-intended-market-ytd.csv   the same for Completions

Each export is a small grid: a title line ("Windsor - Starts by Intended
Market ..."), a line naming the period ("2023 to 2025" or "January -
September 2026"), a header row (blank, then the markets), the data rows,
then notes. The activity is read from the title and, for the zone exports,
the period from the second line; zone rows other than the Windsor total are
left out.

Output: data/staging/windsor_intended_market.csv, one row per period x
activity x market, with is_ytd marking the year-to-date figures.
"""

import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw" / "cmhc"
SOURCE_CSVS = [
    RAW / "windsor-starts-intended-market.csv",
    RAW / "windsor-starts-intended-market-ytd.csv",
    RAW / "windsor-completions-intended-market-ytd.csv",
]
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_intended_market.csv"
COLUMNS = ["period_label", "is_ytd", "activity", "intended_market", "units"]
MARKETS = ("Homeowner", "Rental", "Condo")  # must be in every export
ACTIVITIES = ("Starts", "Completions")


def _units(cell: str) -> float:
    cell = cell.replace(",", "").strip()
    return float(cell) if cell not in ("", "-", "..") else 0.0  # CMHC writes nil as "-"


def _ytd_label(period_line: str) -> str:
    """'January - September 2026 Dwelling Types - All' -> 'Jan-Sep 2026'."""
    m = re.match(r"\s*([A-Za-z]+)\s*-\s*([A-Za-z]+)\s+(\d{4})", period_line)
    if not m:
        raise ValueError(f"Unrecognised period line: {period_line!r}")
    return f"{m.group(1)[:3]}-{m.group(2)[:3]} {m.group(3)}"


def parse(lines) -> list[dict]:
    """Rows of one CMHC portal export: the year rows of an annual export, or only the Windsor row of a by-zone (year-to-date) export."""
    rows_in = [[c.strip() for c in row] for row in csv.reader(lines)]
    title = rows_in[0][0] if rows_in and rows_in[0] else ""
    activity = next((a for a in ACTIVITIES if a in title), None)
    if activity is None:
        raise ValueError(f"No Starts or Completions in the title: {title!r}")
    by_zone = "by Zone" in title
    period = _ytd_label(rows_in[1][0]) if by_zone else None
    header, rows = None, []
    for cells in rows_in[2:]:
        if header is None and "Homeowner" in cells:
            header = cells
            continue
        if not header or not cells or not cells[0]:
            continue
        if by_zone and cells[0] != "Windsor":
            continue  # a zone row, not the CMA total
        if not by_zone and not (cells[0].isdigit() and len(cells[0]) == 4):
            continue
        label = period if by_zone else cells[0]
        for i, market in enumerate(header):
            if market and i < len(cells):
                rows.append({"period_label": label, "is_ytd": by_zone, "activity": activity,
                             "intended_market": market, "units": _units(cells[i])})
    return rows


def check(rows: list[dict]) -> None:
    """Stop if an export had no data rows, lacks the Homeowner, Rental or Condo column, or its markets do not add up to the total."""
    if not rows:
        raise ValueError("No data rows found: the export's layout has changed")
    for key in sorted({(r["period_label"], r["activity"]) for r in rows}):
        by_market = {r["intended_market"]: r["units"] for r in rows if (r["period_label"], r["activity"]) == key}
        missing = [m for m in (*MARKETS, "All") if m not in by_market]
        if missing:
            raise ValueError(f"{key[1]} {key[0]}: no {', '.join(missing)} column")
        parts = sum(v for m, v in by_market.items() if m != "All")
        if abs(parts - by_market["All"]) > 0.5:
            raise ValueError(f"{key[1]} {key[0]}: the markets add to {parts:,.0f}, not the total {by_market['All']:,.0f}")


def main() -> None:
    """Read the three hand-downloaded exports, check them and write data/staging/windsor_intended_market.csv."""
    rows = []
    for path in SOURCE_CSVS:
        # The portal writes Windows-1252 (an en dash in the title line).
        with open(path, encoding="cp1252", newline="") as fh:
            rows.extend(parse(fh))
    check(rows)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    periods = sorted({(r["activity"], r["period_label"]) for r in rows})
    print(f"Wrote {len(rows)} rows ({', '.join(f'{a} {p}' for a, p in periods)}) to "
          f"{OUTPUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
