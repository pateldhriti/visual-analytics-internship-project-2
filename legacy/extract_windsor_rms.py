"""
Extract the 6 "standard-shape" sheets from the CMHC Windsor RMS 2025
workbook directly into a tidy long-format staging CSV, ready to load into
warehouse.fact_rental_market.

docs/cmhc_rms_sheet_catalogue.md documents the workbook's structure but
never turned it into data -- this is that extraction, for the 6 sheets
that share one of two simple grid layouts (zone rows x bedroom-type
column-groups):

  "Rate" layout (3.1.1, 3.1.2, 3.1.6 -- combined market; 1.1.1, 1.1.2 --
  apartment only): each bedroom-type group is 5 columns wide
  (Oct-24 value, Oct-24 reliability letter, Oct-25 value,
  Oct-25 reliability letter, YoY trend symbol).

  "Universe" layout (3.1.3 -- combined market): each bedroom-type group is
  2 columns wide (Oct-24 value, Oct-25 value) -- no reliability letters or
  YoY trend exist for unit-count tables (confirmed in the catalogue).

3 more sheets, each with its own layout, are also extracted:
  - Table 3.1.7 (new rental stock profile): same 9 zone rows, but each
    bedroom-type group is [universe, vacancy value/reliability, rent
    value/reliability] -- a single current snapshot (no Oct-24/Oct-25
    comparison), covering stock completed July 2022-June 2025.
  - Table 3.1.9 (vacant vs. occupied rent): same 9 zone rows, each
    bedroom-type group is [vacant-unit rent value/reliability,
    occupied-unit rent value/reliability, Y/N significance flag] -- a
    single current snapshot, not two time periods. The Y/N flag is stored
    in the fact table's yoy_trend column (repurposed: both columns hold a
    short "how do these two values compare" signal, just from a different
    kind of comparison than year-over-year).
  - Table 3.1.8 (zone x income quintile): the most complex sheet -- 63 real
    data rows (9 zones x 7 quintile-scheme rows: N/A, Q1-Q5, Total), each
    row is zone + quintile label, each bedroom-type group [universe,
    vacancy value/reliability]. Real data rows are found by an explicit
    zone-label allowlist, since this sheet's footer legend rows share the
    same column as the data and aren't bounded by a fixed row count like
    the other sheets. The quintile label maps to
    warehouse.dim_income_band's 'cmhc_quintile' scheme.

Every zone label and bedroom-type label is read as-is from the sheet and
matches warehouse.dim_zone / warehouse.dim_bedroom_type's seeded labels
exactly (verified below), so no renaming/mapping step is needed before
loading. This source is rental-only, so tenure is always 'Renter' --
not a column in the sheet, added when loading into the fact table.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_windsor_rms.py
"""

from pathlib import Path

import openpyxl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_XLSX = PROJECT_ROOT / "data" / "raw" / "cmhc" / "rmr-windsor-2025-en.xlsx"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_rental_market.csv"

ZONE_ROWS = 9  # Zone 1-4, Windsor City subtotal, Zone 5-7, Windsor CMA total
FIRST_ZONE_ROW = 8
BEDROOM_HEADER_ROW = 6
BEDROOM_TYPES = ["Studio", "1 Bedroom", "2 Bedroom", "3 Bedroom +", "Total"]
ZONE_LABELS = [
    "Zone 1 - Centre", "Zone 2 - East Inner", "Zone 3 - East Outer", "Zone 4 - West",
    "Windsor City (Zones 1-4)", "Zone 5 - Amherstburg", "Zone 6 - North Essex County",
    "Zone 7 - South Essex County", "Windsor CMA",
]
QUINTILE_LABELS = ["N/A", "Q1", "Q2", "Q3", "Q4", "Q5", "Total"]

# sheet name -> (metric_type, dwelling_type, layout)
SHEETS = {
    "Table 3.1.1": ("vacancy_rate", "Combined", "rate"),
    "Table 3.1.2": ("average_rent", "Combined", "rate_no_yoy"),
    "Table 3.1.3": ("universe", "Combined", "universe"),
    "Table 3.1.6": ("turnover_rate", "Combined", "rate"),
    "Table 1.1.1": ("vacancy_rate", "Apartment", "rate"),
    "Table 1.1.2": ("average_rent", "Apartment", "rate_no_yoy"),
}


def parse_rate_sheet(ws, metric_type: str, dwelling_type: str, has_yoy: bool = True) -> list[dict]:
    """Bedroom groups of Oct-24 value/reliability, Oct-25 value/reliability,
    and -- only for vacancy/turnover tables -- a trailing YoY column.

    Average-rent tables (3.1.2, 1.1.2) have NO YoY column, making their
    bedroom groups 4 columns wide instead of 5 -- confirmed by reading
    Windsor CMA's real row in Table 1.1.2 (2BR Oct-25 = 1454, matching the
    Canada RMS comparison table's independently-sourced figure) and in
    Table 3.1.2's header (4-wide groups: Studio at col 2, 1BR at col 6,
    4 apart, vs. 5 apart on the vacancy/turnover tables). Passing
    has_yoy=True (the vacancy_rate/turnover_rate default) against one of
    these tables silently reads every bedroom group 1 column short,
    misattributing the next group's Oct-24 value as this group's Oct-25
    value -- caught by cross-checking against the Canada RMS comparison
    table's independently-extracted Windsor figure."""
    group_width = 5 if has_yoy else 4
    rows = []
    for i in range(ZONE_ROWS):
        r = FIRST_ZONE_ROW + i
        zone = ws.cell(row=r, column=1).value
        for b, bedroom_type in enumerate(BEDROOM_TYPES):
            base_col = 2 + b * group_width
            oct24_value = ws.cell(row=r, column=base_col).value
            oct24_reliability = ws.cell(row=r, column=base_col + 1).value
            oct25_value = ws.cell(row=r, column=base_col + 2).value
            oct25_reliability = ws.cell(row=r, column=base_col + 3).value
            yoy_trend = ws.cell(row=r, column=base_col + 4).value if has_yoy else None
            rows.append({
                "metric_type": metric_type, "dwelling_type": dwelling_type,
                "zone": zone, "bedroom_type": bedroom_type,
                "period_label": "Oct-24", "value": oct24_value,
                "reliability_letter": oct24_reliability, "yoy_trend": None,
            })
            rows.append({
                "metric_type": metric_type, "dwelling_type": dwelling_type,
                "zone": zone, "bedroom_type": bedroom_type,
                "period_label": "Oct-25", "value": oct25_value,
                "reliability_letter": oct25_reliability, "yoy_trend": yoy_trend,
            })
    return rows


def parse_universe_sheet(ws, metric_type: str, dwelling_type: str) -> list[dict]:
    """2-column bedroom groups: Oct-24 value, Oct-25 value. No reliability/YoY."""
    rows = []
    for i in range(ZONE_ROWS):
        r = FIRST_ZONE_ROW + i
        zone = ws.cell(row=r, column=1).value
        for b, bedroom_type in enumerate(BEDROOM_TYPES):
            base_col = 2 + b * 2
            oct24_value = ws.cell(row=r, column=base_col).value
            oct25_value = ws.cell(row=r, column=base_col + 1).value
            rows.append({
                "metric_type": metric_type, "dwelling_type": dwelling_type,
                "zone": zone, "bedroom_type": bedroom_type,
                "period_label": "Oct-24", "value": oct24_value,
                "reliability_letter": None, "yoy_trend": None,
            })
            rows.append({
                "metric_type": metric_type, "dwelling_type": dwelling_type,
                "zone": zone, "bedroom_type": bedroom_type,
                "period_label": "Oct-25", "value": oct25_value,
                "reliability_letter": None, "yoy_trend": None,
            })
    return rows


def parse_new_stock_sheet(ws) -> list[dict]:
    """Table 3.1.7: 5-column bedroom groups [universe, vacancy value,
    vacancy reliability, rent value, rent reliability]. Single snapshot
    (stock completed July 2022-June 2025) -- labeled period 'Oct-25' since
    that's the survey date this edition reports as of.

    Unlike the other sheets, this one has no separate bedroom-group header
    row above its column header -- row 5 is the only header row, so zone
    data starts at row 6, not FIRST_ZONE_ROW (8)."""
    first_row = 6
    rows = []
    for i in range(ZONE_ROWS):
        r = first_row + i
        zone = ws.cell(row=r, column=1).value
        for b, bedroom_type in enumerate(BEDROOM_TYPES):
            base_col = 2 + b * 5
            universe = ws.cell(row=r, column=base_col).value
            vacancy_value = ws.cell(row=r, column=base_col + 1).value
            vacancy_reliability = ws.cell(row=r, column=base_col + 2).value
            rent_value = ws.cell(row=r, column=base_col + 3).value
            rent_reliability = ws.cell(row=r, column=base_col + 4).value
            common = {"dwelling_type": "Combined", "zone": zone,
                      "bedroom_type": bedroom_type, "period_label": "Oct-25"}
            rows.append({**common, "metric_type": "new_stock_universe",
                         "value": universe, "reliability_letter": None, "yoy_trend": None})
            rows.append({**common, "metric_type": "new_stock_vacancy_rate",
                         "value": vacancy_value, "reliability_letter": vacancy_reliability, "yoy_trend": None})
            rows.append({**common, "metric_type": "new_stock_average_rent",
                         "value": rent_value, "reliability_letter": rent_reliability, "yoy_trend": None})
    return rows


def parse_vacant_occupied_sheet(ws) -> list[dict]:
    """Table 3.1.9: 5-column bedroom groups [vacant-unit rent value/
    reliability, occupied-unit rent value/reliability, Y/N significance
    flag]. Single snapshot (October 2025) -- the Y/N flag goes in
    yoy_trend (see module docstring)."""
    rows = []
    for i in range(ZONE_ROWS):
        r = FIRST_ZONE_ROW + i
        zone = ws.cell(row=r, column=1).value
        for b, bedroom_type in enumerate(BEDROOM_TYPES):
            base_col = 2 + b * 5
            vacant_value = ws.cell(row=r, column=base_col).value
            vacant_reliability = ws.cell(row=r, column=base_col + 1).value
            occupied_value = ws.cell(row=r, column=base_col + 2).value
            occupied_reliability = ws.cell(row=r, column=base_col + 3).value
            significance = ws.cell(row=r, column=base_col + 4).value
            common = {"dwelling_type": "Combined", "zone": zone,
                      "bedroom_type": bedroom_type, "period_label": "Oct-25"}
            rows.append({**common, "metric_type": "rent_vacant_units",
                         "value": vacant_value, "reliability_letter": vacant_reliability,
                         "yoy_trend": significance})
            rows.append({**common, "metric_type": "rent_occupied_units",
                         "value": occupied_value, "reliability_letter": occupied_reliability,
                         "yoy_trend": significance})
    return rows


def parse_income_quintile_sheet(ws) -> list[dict]:
    """Table 3.1.8: zone x income-quintile rows (real data rows found via
    ZONE_LABELS allowlist -- the sheet's footer legend text shares column A
    with the data and isn't bounded by a fixed row count). Each
    bedroom-type group is 4 columns: [universe value, universe reliability,
    vacancy value, vacancy reliability] -- unlike the plain universe tables
    (3.1.3 etc.), this table's universe column does carry a reliability
    letter (confirmed from real data, e.g. Zone 1 x Q2 x 1BR = 1054 'c')."""
    rows = []
    for r in range(7, ws.max_row + 1):
        zone = ws.cell(row=r, column=1).value
        if zone not in ZONE_LABELS:
            continue
        quintile = ws.cell(row=r, column=2).value
        for b, bedroom_type in enumerate(BEDROOM_TYPES):
            base_col = 5 + b * 4
            universe_value = ws.cell(row=r, column=base_col).value
            universe_reliability = ws.cell(row=r, column=base_col + 1).value
            vacancy_value = ws.cell(row=r, column=base_col + 2).value
            vacancy_reliability = ws.cell(row=r, column=base_col + 3).value
            common = {"dwelling_type": "Combined", "zone": zone, "bedroom_type": bedroom_type,
                      "period_label": "Oct-25", "income_quintile": quintile}
            rows.append({**common, "metric_type": "quintile_universe",
                         "value": universe_value, "reliability_letter": universe_reliability, "yoy_trend": None})
            rows.append({**common, "metric_type": "quintile_vacancy_rate",
                         "value": vacancy_value, "reliability_letter": vacancy_reliability, "yoy_trend": None})
    return rows


def clean_value(raw):
    """'**' = suppressed -> null. Strip thousands-separator commas from
    universe counts (e.g. '3,009') so the column parses as numeric."""
    if raw is None or raw == "**":
        return None
    if isinstance(raw, str):
        return raw.replace(",", "")
    return raw


def extract(source_xlsx: Path = SOURCE_XLSX, output_csv: Path = OUTPUT_CSV) -> dict:
    if not source_xlsx.exists():
        raise FileNotFoundError(f"Source workbook not found: {source_xlsx}")

    wb = openpyxl.load_workbook(source_xlsx, data_only=True)

    all_rows = []
    for sheet_name, (metric_type, dwelling_type, layout) in SHEETS.items():
        ws = wb[sheet_name]
        if layout == "rate":
            all_rows.extend(parse_rate_sheet(ws, metric_type, dwelling_type, has_yoy=True))
        elif layout == "rate_no_yoy":
            all_rows.extend(parse_rate_sheet(ws, metric_type, dwelling_type, has_yoy=False))
        else:
            all_rows.extend(parse_universe_sheet(ws, metric_type, dwelling_type))

    expected_standard_rows = len(SHEETS) * ZONE_ROWS * len(BEDROOM_TYPES) * 2  # x2 for Oct-24/Oct-25

    new_stock_rows = parse_new_stock_sheet(wb["Table 3.1.7"])
    vacant_occupied_rows = parse_vacant_occupied_sheet(wb["Table 3.1.9"])
    quintile_rows = parse_income_quintile_sheet(wb["Table 3.1.8"])

    all_rows.extend(new_stock_rows)
    all_rows.extend(vacant_occupied_rows)
    all_rows.extend(quintile_rows)

    df = pd.DataFrame(all_rows)
    df["value"] = pd.to_numeric(df["value"].map(clean_value), errors="coerce")

    expected_rows = (
        expected_standard_rows
        + ZONE_ROWS * len(BEDROOM_TYPES) * 3  # 3.1.7: 3 metrics/cell
        + ZONE_ROWS * len(BEDROOM_TYPES) * 2  # 3.1.9: 2 metrics/cell
        + 9 * len(QUINTILE_LABELS) * len(BEDROOM_TYPES) * 2  # 3.1.8: 9 zones x 7 quintile rows x 2 metrics
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    return {
        "source_xlsx": str(source_xlsx),
        "output_csv": str(output_csv),
        "sheets_read": list(SHEETS) + ["Table 3.1.7", "Table 3.1.9", "Table 3.1.8"],
        "expected_rows": expected_rows,
        "actual_rows": len(df),
        "match": expected_rows == len(df),
        "metric_types": sorted(df["metric_type"].unique()),
        "dwelling_types": sorted(df["dwelling_type"].unique()),
        "zones": sorted(df["zone"].unique()),
        "quintile_labels": sorted(df["income_quintile"].dropna().unique()),
        "null_values_suppressed_or_blank": int(df["value"].isna().sum()),
    }


if __name__ == "__main__":
    stats = extract()
    print("Extraction complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
