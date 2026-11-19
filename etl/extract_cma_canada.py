r"""
Every Canadian census metropolitan area (CMA), for Story 4's tabs "Windsor
in 2021", "Since 2019, with Toronto" and "All Canadian Cities, 2021".

    .venv\Scripts\python.exe etl\extract_cma_canada.py

Sources (all in data/raw):
    98-401-X2021002  Census Profile 2021: characteristic 1492, % of tenant
                     households spending 30% or more of income on shelter
                     (incomes for 2020); characteristic 1416, renter households
    34-10-0133-01    CMHC average rent each October 2019-2025, 2-bedroom units in
                     apartment structures of three units and over
    34-10-0130-01    CMHC vacancy rate each October 2019-2025 (apartments and row
                     houses: StatCan publishes no apartment-only series)
    CMHC Rental Market Survey, Canada, 2021 (rmr-canada-2021-en.xlsx)
                     Table 5.0: rental universe (row and apartment structures).
    CMHC Rental Market Survey, Canada, 2019-2025 (rmr-canada-<year>-en.xlsx)
                     Table 1.0: apartment vacancy rate and average 2-bedroom
                     rent each October (apartment structures of three units
                     and over). Each workbook gives last October and this
                     October; the later workbook's figure is kept, because
                     CMHC revises last October's (e.g. Windsor's 2022 rent,
                     $1,197 in the 2022 report, $1,174 in the 2023 report,
                     after the move to 2021 Census boundaries). Only the
                     larger centres are listed.

Cities are matched on the three-digit CMA code at the end of each DGUID
(2021S0503559 in the Census, 2011S0503559 in the StatCan tables), only for
whole CMAs (S0503); the CMHC workbook lists names, matched to the Census
names with spaces and hyphens ignored. A CMA missing from the Census or the
2021 rent and vacancy is left out.

Output: data/staging/cma_canada.csv, one row per CMA x indicator x year.
"""

import csv
import io
import zipfile
from pathlib import Path

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
PROFILE_CSV = RAW / "statcan" / "98-401-X2021002_English_CSV_data.csv"
RENT_ZIP = RAW / "statcan" / "34100133-eng.zip"
VACANCY_ZIP = RAW / "statcan" / "34100130-eng.zip"
RMS_2021 = RAW / "cmhc" / "rmr-canada-2021-en.xlsx"
RMS_YEARS = range(2019, 2026)  # one national workbook per October survey
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "cma_canada.csv"

CENSUS_YEAR = 2021
FIRST_YEAR = 2019
CMA_PREFIX = "S0503"  # a whole census metropolitan area
COLUMNS = ["cma_code", "cma_name", "indicator", "period_year", "value"]
CENSUS_CHARACTERISTICS = {"1492": ("renter_burden_pct", "C10_RATE_TOTAL"),
                          "1416": ("renter_households", "C1_COUNT_TOTAL")}


def _code(dguid: str) -> str | None:
    """'2021S0503559' -> '559'; None for anything that is not a whole CMA."""
    return dguid[-3:] if dguid[4:9] == CMA_PREFIX and len(dguid) == 12 else None


def _key(name: str) -> str:
    """'Kitchener - Cambridge - Waterloo' and 'Kitchener-Cambridge-Waterloo CMA'
    -> 'kitchenercambridgewaterloo'."""
    name = name.strip()
    if name.endswith(" CMA"):
        name = name[:-4]
    return "".join(ch for ch in name.lower() if ch.isalnum())


def census(path: Path = PROFILE_CSV) -> tuple[dict, dict]:
    """({code: name}, {(code, indicator): value}), read row by row (the file is large)."""
    names, values = {}, {}
    with open(path, encoding="latin-1", newline="") as fh:
        for row in csv.DictReader(fh):
            wanted = CENSUS_CHARACTERISTICS.get(row["CHARACTERISTIC_ID"])
            code = _code(row["DGUID"]) if wanted else None
            if code and row[wanted[1]]:
                names[code] = row["GEO_NAME"]
                values[(code, wanted[0])] = float(row[wanted[1]])
    return names, values


def _statcan(path: Path, keep) -> dict:
    """{(code, year): value} for October FIRST_YEAR onward, for the rows `keep` accepts."""
    out = {}
    with zipfile.ZipFile(path) as zf, zf.open(path.name.split("-")[0] + ".csv") as raw:
        for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")):
            code = _code(row["DGUID"])
            year = int(row["REF_DATE"][:4]) if row["REF_DATE"][:4].isdigit() else 0
            if code and year >= FIRST_YEAR and row["VALUE"] and keep(row):
                out[(code, year)] = float(row["VALUE"])
    return out


def _number(cell):
    try:
        return float(str(cell).replace(",", "").strip())
    except ValueError:
        return None  # "**" (suppressed) or blank


def _cma_rows(ws):
    for row in ws.iter_rows(values_only=True):
        if row and isinstance(row[0], str) and row[0].strip().endswith("CMA"):
            yield row


def rms_2021(path: Path = RMS_2021) -> dict:
    """{(name key, "rental_universe"): value} from the 2021 national rental market report."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    try:
        for row in _cma_rows(wb["Table 5.0"]):
            # centre, (blank), units in arrears, grade, rental universe, ...
            value = _number(row[4])
            if value is not None:
                out[(_key(row[0]), "rental_universe")] = value
    finally:
        wb.close()
    return out


# Table 1.0 columns: centre, then for each measure last October's value,
# grade, this October's value, grade (and a trend column).
TABLE_1_COLUMNS = {"vacancy_rate_apartments": (1, 3), "average_rent_2br_rms": (11, 13)}


def rms_table_1(years=RMS_YEARS) -> dict:
    """{(name key, indicator, year): value} from each year's national report,
    oldest first, so a later report's revised figure for last October wins."""
    out = {}
    for year in sorted(years):
        wb = openpyxl.load_workbook(RAW / "cmhc" / f"rmr-canada-{year}-en.xlsx", read_only=True, data_only=True)
        try:
            for row in _cma_rows(wb["Table 1.0"]):
                for indicator, (last_col, this_col) in TABLE_1_COLUMNS.items():
                    for col, y in ((last_col, year - 1), (this_col, year)):
                        value = _number(row[col]) if len(row) > col else None
                        if value is not None and y >= FIRST_YEAR:
                            out[(_key(row[0]), indicator, y)] = value
        finally:
            wb.close()
    return out


def extract() -> list[dict]:
    names, values = census()
    rent = _statcan(RENT_ZIP, lambda r: r["Type of structure"] == "Apartment structures of three units and over"
                    and r["Type of unit"] == "Two bedroom units")
    vacancy = _statcan(VACANCY_ZIP, lambda r: True)
    rms = rms_2021()
    table_1 = rms_table_1()
    rows = []
    for code in sorted(names):
        if (code, CENSUS_YEAR) not in rent or (code, CENSUS_YEAR) not in vacancy:
            continue
        name = names[code]

        def add(indicator, year, value):
            rows.append({"cma_code": code, "cma_name": name, "indicator": indicator,
                         "period_year": year, "value": value})

        for indicator in ("renter_burden_pct", "renter_households"):
            if (code, indicator) in values:
                add(indicator, CENSUS_YEAR, values[(code, indicator)])
        for (c, year), value in sorted(rent.items()):
            if c == code:
                add("average_rent_2br_apartments", year, value)
        for (c, year), value in sorted(vacancy.items()):
            if c == code:
                add("vacancy_rate", year, value)
        if (_key(name), "rental_universe") in rms:
            add("rental_universe", CENSUS_YEAR, rms[(_key(name), "rental_universe")])
        for indicator in TABLE_1_COLUMNS:
            for year in RMS_YEARS:
                if (_key(name), indicator, year) in table_1:
                    add(indicator, year, table_1[(_key(name), indicator, year)])
    return rows


def check(rows: list[dict]) -> None:
    codes = {r["cma_code"] for r in rows}
    for code, name in (("559", "Windsor"), ("555", "London"), ("537", "Hamilton"),
                       ("539", "St. Catharines-Niagara"), ("541", "Kitchener-Cambridge-Waterloo"),
                       ("535", "Toronto")):
        if code not in codes:
            raise ValueError(f"{name} (CMA {code}) is missing from one of the sources")
        have = {r["indicator"] for r in rows if r["cma_code"] == code}
        if not {"rental_universe", "renter_households"} <= have:
            raise ValueError(f"{name} (CMA {code}) has no 2021 rental universe or renter households")
        years = {r["period_year"] for r in rows if r["cma_code"] == code and r["indicator"] == "vacancy_rate_apartments"}
        if years and set(RMS_YEARS) - years:
            raise ValueError(f"{name} (CMA {code}) has no apartment vacancy for {sorted(set(RMS_YEARS) - years)}")
    if len(codes) < 30:
        raise ValueError(f"Only {len(codes)} CMAs matched across the sources")


def main() -> None:
    rows = extract()
    check(rows)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len({r['cma_code'] for r in rows})} CMAs) to "
          f"{OUTPUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
