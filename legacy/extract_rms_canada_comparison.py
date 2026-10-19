"""
Extract Windsor and 3 comparator CMAs' rent/vacancy indicators from the
CMHC Canada RMS workbook's Table 1.0 ("Rental Market Indicators -
Privately Initiated Apartment Structures of Three Units and Over -
Provinces and Major Centres"), ready to load into the same
warehouse.fact_rental_market table the Windsor-specific extraction uses.

Comparator CMAs chosen: London CMA, Kitchener-Cambridge-Waterloo CMA,
Hamilton CMA, and St. Catharines-Niagara CMA. See
docs/comparator_cmas_justification.md for the full selection
methodology (real 2021 Census population data, not estimated, plus
confirmation each one is on CMHC's actual "major centres" Rental Market
Report list alongside Windsor -- i.e. each one genuinely has the same
kind of full RMS 2025 workbook Windsor does, not just this one summary
row). Toronto CMA was in an earlier version of this list but has been
removed: at 6.2M population (14.7x Windsor), it fails "comparable by
size" outright -- it was never a size peer, just a different kind of
reference point that doesn't belong in this specific comparator set.

IMPORTANT SCOPE NOTE: Table 1.0 covers privately initiated APARTMENT
structures only (3+ units) -- not the Row+Apartment Combined scope the
Windsor-specific RMS workbook's 3.1.x tables use. So this table's Windsor
CMA vacancy rate (3.7%, Oct-25) legitimately differs from the Windsor
workbook's Table 3.1.1 Combined figure (3.6%, Oct-25) -- not a
contradiction, a different dwelling-type scope. Loaded with
dwelling_type = 'Apartment', same as the Windsor-specific 1.1.x tables.

Table 1.0 also has a narrower bedroom-type scope than the Windsor-specific
tables: vacancy and turnover are reported as one overall rate (not broken
out by bedroom type) -- mapped to bedroom_type = 'Total'. Average rent and
its percentage change are reported for 2-bedroom units only -- mapped to
bedroom_type = '2 Bedroom'.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_rms_canada_comparison.py
"""

from pathlib import Path

import openpyxl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_XLSX = PROJECT_ROOT / "data" / "raw" / "cmhc" / "rmr-canada-2025-en.xlsx"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "rms_canada_comparison.csv"

# CMA label (as it appears in column A) -> kept as-is in the output;
# matched against dim_zone after this script's caller seeds these as new
# zone_level = 'comparator_cma' rows (Windsor CMA is already seeded as
# zone_level = 'cma_total' and is included here for a same-table check).
CENTRES = [
    "Windsor CMA",
    "London CMA",
    "Kitchener-Cambridge-Waterloo CMA",
    "Hamilton CMA",
    "St. Catharines-Niagara CMA",
]


def find_centre_rows(ws) -> dict:
    rows = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(row=r, column=1).value
        if v in CENTRES:
            rows[v] = r
    missing = set(CENTRES) - set(rows)
    if missing:
        raise ValueError(f"Centre(s) not found in {ws.title}: {sorted(missing)}")
    return rows


def parse_row(ws, r: int, centre: str) -> list[dict]:
    common = {"centre": centre, "dwelling_type": "Apartment"}
    rows = []

    # Vacancy rate: 5-col group at col 2, bedroom_type = Total
    for period, base in (("Oct-24", 2), ("Oct-25", 4)):
        rows.append({
            **common, "bedroom_type": "Total", "metric_type": "vacancy_rate",
            "period_label": period,
            "value": ws.cell(row=r, column=base).value,
            "reliability_letter": ws.cell(row=r, column=base + 1).value,
            "yoy_trend": ws.cell(row=r, column=6).value if period == "Oct-25" else None,
        })

    # Turnover rate: 5-col group at col 7, bedroom_type = Total
    for period, base in (("Oct-24", 7), ("Oct-25", 9)):
        rows.append({
            **common, "bedroom_type": "Total", "metric_type": "turnover_rate",
            "period_label": period,
            "value": ws.cell(row=r, column=base).value,
            "reliability_letter": ws.cell(row=r, column=base + 1).value,
            "yoy_trend": ws.cell(row=r, column=11).value if period == "Oct-25" else None,
        })

    # Average rent, 2BR: 4-col group at col 12
    for period, base in (("Oct-24", 12), ("Oct-25", 14)):
        rows.append({
            **common, "bedroom_type": "2 Bedroom", "metric_type": "average_rent",
            "period_label": period,
            "value": ws.cell(row=r, column=base).value,
            "reliability_letter": ws.cell(row=r, column=base + 1).value,
            "yoy_trend": None,
        })

    # Percentage change of rent, 2BR: 4-col group at col 16.
    # Oct-23-to-24 change tagged to period 'Oct-24' (the change ending at
    # that period); Oct-24-to-25 change tagged to 'Oct-25'.
    for period, base in (("Oct-24", 16), ("Oct-25", 18)):
        rows.append({
            **common, "bedroom_type": "2 Bedroom", "metric_type": "pct_change_rent",
            "period_label": period,
            "value": ws.cell(row=r, column=base).value,
            "reliability_letter": ws.cell(row=r, column=base + 1).value,
            "yoy_trend": None,
        })

    return rows


def clean_value(raw):
    if raw is None or raw == "**":
        return None
    if isinstance(raw, str):
        return raw.replace(",", "")
    return raw


def extract(source_xlsx: Path = SOURCE_XLSX, output_csv: Path = OUTPUT_CSV) -> dict:
    if not source_xlsx.exists():
        raise FileNotFoundError(f"Source workbook not found: {source_xlsx}")

    wb = openpyxl.load_workbook(source_xlsx, data_only=True)
    ws = wb["Table 1.0"]
    centre_rows = find_centre_rows(ws)

    all_rows = []
    for centre, r in centre_rows.items():
        all_rows.extend(parse_row(ws, r, centre))

    df = pd.DataFrame(all_rows)
    df["value"] = pd.to_numeric(df["value"].map(clean_value), errors="coerce")

    expected_rows = len(CENTRES) * 8  # 2 metrics x Total (vac,turnover) + 2 metrics x 2BR (rent,pct_chg), x2 periods each
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    return {
        "source_xlsx": str(source_xlsx),
        "output_csv": str(output_csv),
        "centres": CENTRES,
        "expected_rows": expected_rows,
        "actual_rows": len(df),
        "match": expected_rows == len(df),
        "metric_types": sorted(df["metric_type"].unique()),
        "null_values_suppressed_or_blank": int(df["value"].isna().sum()),
    }


if __name__ == "__main__":
    stats = extract()
    print("Extraction complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
