"""
Story 5: CMA rental market history 2019-2025 from CMHC Canada RMR Table 1.0.

Table 1.0 "Rental Market Indicators - Privately Initiated Apartment Structures
of Three Units and Over - Provinces and Major Centres" is the only table
present in all seven editions (audit sections 2.2 and 3). Each edition holds
the previous and the current October. Selection rule (audit section 3.2):
  year Y (2019-2021, 2023-2025)  edition Y, current column
  2022 pre_2021_census           edition 2022, current column  (not primary)
  2022 2021_census               edition 2023, previous column (primary)
The geography basis is asserted from each edition's own footnote: editions
2023+ state "based on the 2021 census geographic definitions"; 2019-2022 have
no such note (2016-census CMA definitions).

Metrics (apartment structures of 3+ units, privately initiated):
  vacancy_rate                  bedroom total      percent         + trend flag
  turnover_rate                 bedroom total      percent         + trend flag
  average_rent_2br              2 bedroom          dollars (monthly; new and existing structures)
  fixed_sample_rent_change_2br  2 bedroom          percent_change  (existing structures only)

Markers: '**' -> NULL, suppressed;  '++' -> NULL, change_not_significant.
Nothing unavailable is ever turned into 0. Province, national and CA rows are
excluded; every CMA label is mapped through etl/cma_geography_map.csv only.

Grain: cma_dguid x year x metric x geography_basis.
Output: data/staging/canada_cma_rental_history.csv
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from cleaning_common import raw_text
from story5_common import (
    CMHC_CANADA, GEOGRAPHY_MAP_PATH, METRICS, OUTPUTS, RAW_DIR, RELIABILITY_CODES, STAGING_DIR, TREND,
    VALUE_MARKERS, data_rows, header_row, is_cmhc_cma_label, load_geography_map, lookup, raw_path, text,
)

TABLE = "Table 1.0"
# metric -> (previous value col, current value col, trend col or None), 0-based; reliability = value col + 1
COLS = {
    "vacancy_rate": (1, 3, 5),
    "turnover_rate": (6, 8, 10),
    "average_rent_2br": (11, 13, None),
    "fixed_sample_rent_change_2br": (15, 17, None),
}
SCOPE = {
    "vacancy_rate": ("total", "percent"),
    "turnover_rate": ("total", "percent"),
    "average_rent_2br": ("2_bedroom", "dollars"),
    "fixed_sample_rent_change_2br": ("2_bedroom", "percent_change"),
}
GROUP_PREFIX = {1: "Vacancy Rates (%)", 6: "Turnover Rates (%)", 11: "Average Rent Two Bedroom ($)",
                15: "Percentage Change of Average Rent Two Bedroom From Fixed Sample"}
GEO_NOTE = "2021 census geographic definitions"
DWELLING_SCOPE = "apartment_3plus_private"

COLUMNS = ["year", "period_label", "cma_dguid", "statcan_geo_name", "cmhc_centre_name", "geography_basis",
           "is_primary_series", "boundary_changed_flag", "focus_peer", "metric", "bedroom_scope",
           "dwelling_scope", "unit", "value", "raw_value", "value_status", "reliability_code", "yoy_trend",
           "source_edition_year", "source_column_role", "source_workbook", "source_table", "source_cell"]


def oct_label(year: int) -> str:
    return f"Oct-{year % 100:02d}"


def change_label(year: int) -> str:
    return f"{oct_label(year - 1)} to {oct_label(year)}"


def check_layout(ws, edition: int) -> int:
    hdr = header_row(ws)
    rows = list(ws.iter_rows(min_row=hdr - 1, max_row=hdr, values_only=True))
    group, head = rows[0], rows[1]
    want = {1: oct_label(edition - 1), 3: oct_label(edition), 6: oct_label(edition - 1), 8: oct_label(edition),
            11: oct_label(edition - 1), 13: oct_label(edition), 15: change_label(edition - 1),
            17: change_label(edition)}
    bad = [f"col {get_column_letter(c + 1)}: {head[c]!r} != {w!r}" for c, w in want.items() if text(head[c]) != w]
    bad += [f"group col {get_column_letter(c + 1)}: {group[c]!r}" for c, p in GROUP_PREFIX.items()
            if not (text(group[c]) or "").startswith(p)]
    if bad:
        raise ValueError(f"Edition {edition} {TABLE}: unexpected layout: " + "; ".join(bad))
    return hdr


def geography_basis(ws, edition: int) -> str:
    noted = any(GEO_NOTE in (text(r[0]) or "") for r in ws.iter_rows(values_only=True))
    expected = edition >= 2023
    if noted != expected:
        raise ValueError(f"Edition {edition}: 2021-census geography note present={noted}, expected {expected}")
    return "2021_census" if noted else "pre_2021_census"


def parse_value(raw) -> tuple[float, str]:
    t = text(raw)
    if t is None:
        raise ValueError("blank value cell where a value or marker is required")
    if t in VALUE_MARKERS:
        return math.nan, VALUE_MARKERS[t]
    return float(t.replace(",", "")), "published"


def parse_reliability(raw) -> str | None:
    t = text(raw)
    if t is not None and t not in RELIABILITY_CODES:
        raise ValueError(f"unrecognised reliability code {raw!r}")
    return t


def parse_trend(raw) -> str | None:
    t = text(raw)
    if t is None:
        return None
    if t not in TREND:
        raise ValueError(f"unrecognised trend marker {raw!r}")
    return TREND[t]


def extract(edition: int, role: str, raw_dir: Path, geo_map: dict) -> list[dict]:
    rel = CMHC_CANADA[edition]
    wb = openpyxl.load_workbook(raw_path(rel, raw_dir), read_only=True, data_only=True)
    ws = wb[TABLE]
    hdr = check_layout(ws, edition)
    edition_basis = geography_basis(ws, edition)
    year = edition if role == "current" else edition - 1
    basis = edition_basis
    primary = not (year == 2022 and basis == "pre_2021_census")
    out = []
    for rownum, label, row in data_rows(ws, hdr):
        if not is_cmhc_cma_label(label):
            continue
        g = lookup(geo_map, label)
        row = list(row) + [None] * 20
        for metric in METRICS:
            prev_c, cur_c, trend_c = COLS[metric]
            c = cur_c if role == "current" else prev_c
            try:
                value, status = parse_value(row[c])
                reliability = parse_reliability(row[c + 1])
                trend = parse_trend(row[trend_c]) if (trend_c is not None and role == "current") else None
            except ValueError as exc:
                raise ValueError(f"{rel} {TABLE}!{get_column_letter(c + 1)}{rownum} ({label}, {metric}): {exc}")
            bedroom, unit = SCOPE[metric]
            out.append({
                "year": year,
                "period_label": change_label(year) if metric == "fixed_sample_rent_change_2br" else oct_label(year),
                "cma_dguid": g["cma_dguid"], "statcan_geo_name": g["statcan_geo_name"], "cmhc_centre_name": label,
                "geography_basis": basis, "is_primary_series": primary,
                "boundary_changed_flag": g["boundary_changed_flag"] == "True", "focus_peer": g["focus_peer"] == "True",
                "metric": metric, "bedroom_scope": bedroom, "dwelling_scope": DWELLING_SCOPE, "unit": unit,
                "value": value, "raw_value": raw_text(row[c]), "value_status": status,
                "reliability_code": reliability, "yoy_trend": trend,
                "source_edition_year": edition, "source_column_role": role,
                "source_workbook": f"data/raw/{rel}", "source_table": TABLE,
                "source_cell": f"{TABLE}!{get_column_letter(c + 1)}{rownum}",
            })
    wb.close()
    return out


def build(raw_dir: Path = RAW_DIR, map_path: Path = GEOGRAPHY_MAP_PATH) -> pd.DataFrame:
    geo_map = load_geography_map(map_path)
    rows = []
    for edition in CMHC_CANADA:
        rows += extract(edition, "current", raw_dir, geo_map)
    rows += extract(2023, "previous", raw_dir, geo_map)   # 2022 revised to 2021-census geography
    df = pd.DataFrame(rows, columns=COLUMNS).sort_values(
        ["cma_dguid", "metric", "year", "geography_basis"], ignore_index=True)
    key = ["cma_dguid", "year", "metric", "geography_basis"]
    if df.duplicated(key).any():
        raise ValueError(f"duplicate grain rows: {df[df.duplicated(key, keep=False)][key].values.tolist()[:5]}")
    prim = df[df.is_primary_series]
    if prim.duplicated(["cma_dguid", "year", "metric"]).any():
        raise ValueError("more than one primary row for a cma/year/metric")
    return df


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR, map_path: Path = GEOGRAPHY_MAP_PATH) -> dict:
    df = build(raw_dir, map_path)
    out = out_dir / OUTPUTS["rental_history"]
    df.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    return {"output": out, "rows": len(df)}


if __name__ == "__main__":
    r = clean()
    print(f"{r['output']}: {r['rows']} rows")
    sys.exit(0)
