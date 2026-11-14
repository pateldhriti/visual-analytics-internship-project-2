"""
Build etl/cma_geography_map.csv: the deterministic CMHC centre -> StatsCan
DGUID lookup for Story 5 (audit section 4.2).

Every CMA-level centre label found in CMHC Canada RMR Table 1.0 (2019-2025)
and in the 2021 Table 5.0 is mapped by Rule A (exact after removing the
trailing " CMA") or Rule B (the audited EXPLICIT_LOOKUP). Anything else, or
two different CMHC names landing on one DGUID within the same edition, stops
the run. No fuzzy matching.

One output row per distinct CMHC centre string (Belleville appears under two
names; both map to 2021S0503522, the old name flagged boundary_changed).

    .venv\\Scripts\\python.exe etl\\build_cma_geography_map.py
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import openpyxl
import pandas as pd

from story5_common import (
    CMHC_CANADA, EXPLICIT_LOOKUP, FOCUS_PEER_DGUIDS, GEOGRAPHY_MAP_PATH, RAW_DIR, census_cma_geographies,
    data_rows, header_row, is_cmhc_cma_label, raw_path, universe_header,
)

COLUMNS = ["cmhc_centre_name", "cma_dguid", "statcan_geo_name", "statcan_geo_level", "alt_geo_code",
           "match_rule", "match_note", "boundary_changed_flag", "focus_peer", "focus_peer_label",
           "cmhc_table_1_0_editions", "in_2021_table_5_0"]


def cmhc_centres(raw_dir: Path = RAW_DIR) -> tuple[dict[str, list[int]], set[str]]:
    """CMA labels per Table 1.0 edition, and the CMA labels of 2021 Table 5.0."""
    editions = collections.defaultdict(list)
    for year, rel in CMHC_CANADA.items():
        wb = openpyxl.load_workbook(raw_path(rel, raw_dir), read_only=True, data_only=True)
        ws = wb["Table 1.0"]
        for _, label, _ in data_rows(ws, header_row(ws)):
            if is_cmhc_cma_label(label):
                editions[label].append(year)
        wb.close()
    wb = openpyxl.load_workbook(raw_path(CMHC_CANADA[2021], raw_dir), read_only=True, data_only=True)
    ws = wb["Table 5.0"]
    t5 = {label for _, label, _ in data_rows(ws, universe_header(ws)) if is_cmhc_cma_label(label)}
    wb.close()
    return editions, t5


def build(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    geos = census_cma_geographies(raw_dir)
    by_name = {}
    for dguid, g in geos.items():
        if g["geo_level"] == "Census metropolitan area":
            if g["geo_name"] in by_name:
                raise ValueError(f"StatsCan GEO_NAME not unique: {g['geo_name']}")
            by_name[g["geo_name"]] = dguid
    editions, t5 = cmhc_centres(raw_dir)
    unknown_t5 = t5 - set(editions)
    labels = sorted(set(editions) | t5)
    rows, problems = [], []
    for label in labels:
        if label in EXPLICIT_LOOKUP:
            dguid, note, changed = EXPLICIT_LOOKUP[label]
            rule = "explicit_lookup"
            if dguid not in geos:
                problems.append(f"{label}: explicit DGUID {dguid} not in Census Profile")
                continue
        else:
            base = label[:-len(" CMA")] if label.endswith(" CMA") else None
            if base not in by_name:
                problems.append(f"unmapped CMHC centre: {label!r}")
                continue
            dguid, note, changed, rule = by_name[base], "", False, "exact_after_cma_suffix"
        g = geos[dguid]
        rows.append({
            "cmhc_centre_name": label, "cma_dguid": dguid, "statcan_geo_name": g["geo_name"],
            "statcan_geo_level": g["geo_level"], "alt_geo_code": g["alt_geo_code"], "match_rule": rule,
            "match_note": note, "boundary_changed_flag": changed, "focus_peer": dguid in FOCUS_PEER_DGUIDS,
            "focus_peer_label": FOCUS_PEER_DGUIDS.get(dguid, ""),
            "cmhc_table_1_0_editions": ";".join(str(y) for y in sorted(editions.get(label, []))),
            "in_2021_table_5_0": label in t5,
        })
    if unknown_t5:
        problems.append(f"Table 5.0 (2021) labels absent from every Table 1.0 edition: {sorted(unknown_t5)}")
    df = pd.DataFrame(rows, columns=COLUMNS)
    # a DGUID may carry two CMHC names only if they never co-occur in one edition
    for dguid, grp in df.groupby("cma_dguid"):
        if len(grp) > 1:
            seen = collections.Counter(y for e in grp["cmhc_table_1_0_editions"] for y in e.split(";") if y)
            if any(n > 1 for n in seen.values()):
                problems.append(f"{dguid}: two CMHC names in the same edition: {list(grp.cmhc_centre_name)}")
    if problems:
        raise ValueError("Geography map failed:\n  " + "\n  ".join(problems))
    return df


def write(raw_dir: Path = RAW_DIR, path: Path = GEOGRAPHY_MAP_PATH) -> pd.DataFrame:
    df = build(raw_dir)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return df


def main() -> int:
    df = write()
    print(f"{GEOGRAPHY_MAP_PATH}: {len(df)} CMHC centre names -> {df.cma_dguid.nunique()} DGUIDs "
          f"({(df.match_rule == 'explicit_lookup').sum()} explicit, "
          f"{(df.match_rule == 'exact_after_cma_suffix').sum()} exact)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
