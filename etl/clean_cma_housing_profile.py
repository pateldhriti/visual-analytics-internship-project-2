"""
Story 5: CMA housing profile from the StatsCan 2021 Census Profile (CMA/CA),
98-401-X2021002 (audit sections 1 and 9.2).

Rows kept: every CMA-level geography (GEO_LEVEL 'Census metropolitan area'
or 'Census metropolitan area part': 41 + 2 = 43) x exactly the audited
characteristic allowlist (19 IDs). No renter income is derived: the Census
Profile publishes none.

Values: C1_COUNT_TOTAL -> count_total, C10_RATE_TOTAL -> rate_total, each with
its own SYMBOL -> *_status ('' published, '...' not_applicable, 'x'
suppressed, ...). A symbol that withholds the number leaves the value NULL;
a published value is never blank and never zero-filled.

`unit` describes count_total (for %/$ characteristics count_total already
holds the percentage or dollars; rate_total repeats it). For count
characteristics rate_total is StatsCan's published % of the parent total.

Grain: cma_dguid x characteristic_id.
Output: data/staging/canada_cma_housing_profile.csv
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

from cleaning_common import STATCAN_KEEPS_VALUE, normalize_text, statcan_status
from story5_common import CENSUS_ALLOWLIST, CENSUS_ZIP, CMA_LEVELS, OUTPUTS, RAW_DIR, STAGING_DIR, census_rows

COLUMNS = ["census_year", "cma_dguid", "alt_geo_code", "geo_level", "geo_name", "tnr_sf", "tnr_lf",
           "data_quality_flag", "characteristic_id", "characteristic_name", "characteristic_note",
           "count_total", "count_status", "rate_total", "rate_status", "unit", "source_file"]


def parse(raw_value: str, raw_symbol: str, where: str) -> tuple[float, str]:
    status = statcan_status(raw_symbol)
    t = normalize_text(raw_value)
    if status in STATCAN_KEEPS_VALUE:
        if t is None:
            raise ValueError(f"{where}: status {status} but no value")
        return float(t), status
    if t is not None:
        raise ValueError(f"{where}: status {status} but a value {raw_value!r} is present")
    return math.nan, status


def build(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    rows = []
    for r in census_rows(raw_dir):
        if r[3] not in CMA_LEVELS:
            continue
        cid = int(r[8])
        if cid not in CENSUS_ALLOWLIST:
            continue
        where = f"{r[4]} / {cid}"
        count, count_status = parse(r[11], r[12], where + " count")
        rate, rate_status = parse(r[17], r[18], where + " rate")
        rows.append({
            "census_year": int(r[0]), "cma_dguid": r[1], "alt_geo_code": r[2], "geo_level": r[3],
            "geo_name": r[4], "tnr_sf": float(r[5]), "tnr_lf": float(r[6]), "data_quality_flag": r[7],
            "characteristic_id": cid, "characteristic_name": normalize_text(r[9]),
            "characteristic_note": normalize_text(r[10]),
            "count_total": count, "count_status": count_status, "rate_total": rate, "rate_status": rate_status,
            "unit": CENSUS_ALLOWLIST[cid], "source_file": f"data/raw/{CENSUS_ZIP}",
        })
    df = pd.DataFrame(rows, columns=COLUMNS).sort_values(["cma_dguid", "characteristic_id"], ignore_index=True)
    if df.duplicated(["cma_dguid", "characteristic_id"]).any():
        raise ValueError("duplicate cma_dguid x characteristic_id")
    return df


def clean(raw_dir: Path = RAW_DIR, out_dir: Path = STAGING_DIR) -> dict:
    df = build(raw_dir)
    out = out_dir / OUTPUTS["housing_profile"]
    df.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    return {"output": out, "rows": len(df)}


if __name__ == "__main__":
    r = clean()
    print(f"{r['output']}: {r['rows']} rows")
    sys.exit(0)
