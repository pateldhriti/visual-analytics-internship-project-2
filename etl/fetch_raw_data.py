r"""
Put every raw source file the ETL reads into data/raw/, on a fresh machine
(the university server) or after a clean clone: data/raw is not in git.

    .venv\Scripts\python.exe etl\fetch_raw_data.py            download what is missing
    .venv\Scripts\python.exe etl\fetch_raw_data.py --refresh  re-download every downloadable file
    .venv\Scripts\python.exe etl\fetch_raw_data.py --check    only report what is there

Files come straight from Statistics Canada and CMHC. Two cannot be fetched by
a script and are listed with the page to download them from:

    - the 2021 Census Profile comprehensive file (98-401-X2021002): the
      download service refuses non-browser requests. If only its zip is in
      data/raw/statcan/, this script unzips the CSV the ETL reads.
    - CMHC's quarterly starts and completions workbook (Ontario and Canada
      context on the overview): its file name changes every quarter.

The script exits with status 1 if any file is still missing at the end.
"""

import argparse
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
STATCAN_TABLE = "https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"
CMHC_RMS = (
    "https://assets.cmhc-schl.gc.ca/sites/cmhc/professional/housing-markets-data-and-research/"
    "housing-data-tables/rental-market/rental-market-report-data-tables/{year}/{name}-{year}-en.xlsx"
)


@dataclass(frozen=True)
class Source:
    path: str  # relative to data/raw
    url: str | None = None  # None: downloaded by hand
    unzip: tuple[str, ...] = ()  # files to take out of a downloaded zip (the zip itself is not kept)
    page: str = ""  # where to download it by hand
    note: str = ""


SOURCES = [
    # StatCan tables
    Source("shelter_cost/98100252.csv", STATCAN_TABLE.format(pid="98100252"),
           unzip=("98100252.csv", "98100252_MetaData.csv"), note="Story 1 shelter cost by income and tenure"),
    Source("statcan/34100154-eng.zip", STATCAN_TABLE.format(pid="34100154"), note="housing starts and completions"),
    Source("statcan/98100241-eng.zip", STATCAN_TABLE.format(pid="98100241"), note="housing indicators by age"),
    Source("statcan/34100130-eng.zip", STATCAN_TABLE.format(pid="34100130"), note="vacancy rates, 2015 onward"),
    Source("statcan/34100133-eng.zip", STATCAN_TABLE.format(pid="34100133"), note="average rents, 2015 onward"),
    # CMHC Rental Market Survey workbooks
    *[Source(f"cmhc/rmr-windsor-{y}-en.xlsx", CMHC_RMS.format(year=y, name="rmr-windsor"),
             note=f"Windsor rental market, October {y}") for y in range(2021, 2026)],
    Source("cmhc/rmr-canada-2025-en.xlsx", CMHC_RMS.format(year=2025, name="rmr-canada"),
           note="city comparison, October 2025"),
    *[Source(f"cmhc/peer_rms_2025/rmr-{c}-2025-en.xlsx", CMHC_RMS.format(year=2025, name=f"rmr-{c}"),
             note="comparison-city rental units, October 2025")
      for c in ("windsor", "london", "hamilton", "st-catharines-niagara", "kitchener-cambridge-waterloo")],
    # By hand
    Source("statcan/98-401-X2021002_English_CSV_data.csv",
           page="https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger.cfm?Lang=E",
           note="2021 Census Profile, comprehensive file for Canada, provinces, territories, CMAs and CAs "
                "(98-401-X2021002), CSV; save the zip as data/raw/statcan/98-401-X2021002_eng_CSV.zip"),
    Source("cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx",
           page="https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/"
                "data-tables/housing-market-data/starts-completions-units-under-construction-geography",
           note="CMHC quarterly starts, completions and units under construction (overview context)"),
]
CENSUS_ZIP = "statcan/98-401-X2021002_eng_CSV.zip"


def download(url: str, target: Path, unzip: tuple[str, ...] = ()) -> None:
    """Download to a temporary file first, so a failed download never leaves
    a partial file where the ETL would read it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        part = Path(tmp) / "download"
        with requests.get(url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(part, "wb") as fh:
                for block in resp.iter_content(1 << 20):
                    fh.write(block)
        if not zipfile.is_zipfile(part):  # .xlsx and StatCan tables are both zip files
            raise ValueError(f"{url} did not return a zip/xlsx file")
        if unzip:
            with zipfile.ZipFile(part) as zf:
                for name in unzip:
                    with zf.open(name) as src, open(target.parent / name, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        else:
            shutil.move(str(part), target)


def unzip_census_profile(raw: Path = RAW) -> bool:
    """The Census Profile CSV, from its zip if only the zip is there."""
    csv_path = raw / "statcan/98-401-X2021002_English_CSV_data.csv"
    zip_path = raw / CENSUS_ZIP
    if csv_path.exists() or not zip_path.exists():
        return csv_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(csv_path.name, csv_path.parent)
    return True


def run(refresh: bool = False, check_only: bool = False, raw: Path = RAW, fetch=download) -> list[Source]:
    """Fetch what is needed; return the sources still missing."""
    missing = []
    for src in SOURCES:
        target = raw / src.path
        if src.url and not check_only and (refresh or not target.exists()):
            print(f"downloading  {src.path}  ({src.note})")
            fetch(src.url, target, src.unzip)
        if src.path.endswith("98-401-X2021002_English_CSV_data.csv") and not check_only:
            unzip_census_profile(raw)
        status = "ok" if target.exists() else "MISSING"
        print(f"{status:<8} {src.path}")
        if not target.exists():
            missing.append(src)
    for src in missing:
        how = f"download by hand from {src.page}" if src.page else f"download failed or skipped: {src.url}"
        print(f"\nMissing: data/raw/{src.path}\n  {src.note}\n  {how}")
    return missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="re-download every downloadable file")
    parser.add_argument("--check", action="store_true", help="only report which files are there")
    args = parser.parse_args(argv)
    return 1 if run(refresh=args.refresh, check_only=args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
