"""
Story 5 (Q2 only): CMA rental universe, October 2021, from CMHC Canada RMR
2021 Table 5.0 (rental arrears table) column "Universe" (audit section 2.3).

Table 5.0 (2021 edition) title: "Rental Arrears - Privately Initiated Row
(Townhouse) and Apartment Structures of Three Units and Over" -> dwelling scope
row_and_apartment_3plus_private. The 2021 edition carries no 2021-census
geography note -> geography_basis pre_2021_census (2016-census CMA boundaries).

Deliberately NOT used: the 2020 edition (title says apartment-only but values
look like row + apartment), and any other edition (no 2019-2025 universe trend
is constructed). The ratio to Census renter households is not computed here;
the material boundary-mismatch warning (decision D3) is carried as a column.

Grain: one row per matched CMA (36).
Output: data/staging/canada_cma_rental_universe.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pandas as pd

from cleaning_common import raw_text
from story5_common import (
    CMHC_CANADA, GEOGRAPHY_MAP_PATH, OUTPUTS, RAW_DIR, STAGING_DIR, data_rows, is_cmhc_cma_label,
    load_geography_map, lookup, raw_path, text, universe_header,
)

EDITION = 2021
TABLE = "Table 5.0"
TITLE_FRAGMENT = "Row (Townhouse) and Apartment Structures of Three Units and Over"
GEO_NOTE = "2021 census geographic definitions"
COUNT_RATIO_WARNING = (
    "WARNING: this CMHC Oct-2021 rental universe uses 2016-census CMA boundaries; Census 2021 renter "
    "households use 2021-census boundaries. Any units-per-renter-household ratio is affected materially "
    "(Windsor's apartment universe was about 10% larger on the 2021 boundary: 15,629 vs 17,196 in Oct-2022).")

COLUMNS = ["year", "period_label", "cma_dguid", "statcan_geo_name", "cmhc_centre_name", "universe_units",
           "raw_value", "value_status", "dwelling_scope", "geography_basis", "boundary_changed_flag",
           "focus_peer", "boundary_mismatch_severity", "count_ratio_warning", "source_edition_year",
           "source_workbook", "source_table", "source_cell"]


def build(raw_dir: Path = RAW_DIR, map_path: Path = GEOGRAPHY_MAP_PATH) -> pd.DataFrame:
    geo_map = load_geography_map(map_path)
    rel = CMHC_CANADA[EDITION]
    wb = openpyxl.load_workbook(raw_path(rel, raw_dir), read_only=True, data_only=True)
    ws = wb[TABLE]
    titles = [text(r[0]) or "" for r in ws.iter_rows(min_row=1, max_row=5, values_only=True)]
    if not any(TITLE_FRAGMENT in t for t in titles):
        raise ValueError(f"{rel} {TABLE}: dwelling scope title not found: {titles}")
    if any(GEO_NOTE in (text(r[0]) or "") for r in ws.iter_rows(values_only=True)):
        raise ValueError(f"{rel} {TABLE}: unexpected 2021-census geography note")
    hdr = universe_header(ws)
    rows = []
    for rownum, label, row in data_rows(ws, hdr):
        if not is_cmhc_cma_label(label):
            continue
        g = lookup(geo_map, label)
        raw = row[4]
        t = text(raw)
        if t is None or not t.replace(",", "").isdigit():
            raise ValueError(f"{rel} {TABLE}!E{rownum} ({label}): non-integer universe {raw!r}")
        rows.append({
            "year": EDITION, "period_label": "Oct-21", "cma_dguid": g["cma_dguid"],
            "statcan_geo_name": g["statcan_geo_name"], "cmhc_centre_name": label,
            "universe_units": int(t.replace(",", "")), "raw_value": raw_text(raw), "value_status": "published",
            "dwelling_scope": "row_and_apartment_3plus_private", "geography_basis": "pre_2021_census",
            "boundary_changed_flag": g["boundary_changed_flag"] == "True", "focus_peer": g["focus_peer"] == "True",
            "boundary_mismatch_severity": "material", "count_ratio_warning": COUNT_RATIO_WARNING,
            "source_edition_year": EDITION, "source_workbook": f"data/raw/{rel}", "source_table": TABLE,
            "source_cell": f"{TABLE}!E{rownum}",
        })
    wb.close()
    df = pd.DataFrame(rows, columns=COLUMNS).sort_values("cma_dguid", ignore_index=True)
    if df.cma_dguid.duplicated().any():
        raise ValueError("duplicate cma_dguid in rental universe")
    return df


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR, map_path: Path = GEOGRAPHY_MAP_PATH) -> dict:
    df = build(raw_dir, map_path)
    out = out_dir / OUTPUTS["rental_universe"]
    df.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    return {"output": out, "rows": len(df)}


if __name__ == "__main__":
    r = clean()
    print(f"{r['output']}: {r['rows']} rows")
    sys.exit(0)
