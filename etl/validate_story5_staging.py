"""
Independent validation of the Story 5 staging layer.

Re-reads the raw sources itself (openpyxl / zipfile+csv) and does not reuse
the cleaners' parsers: expected values, allowlists and the audited explicit
mappings are restated here so a cleaner bug cannot validate itself.

Writes docs/STORY5_STAGING_VALIDATION.md whose first line is exactly
"STORY5 STAGING STATUS: PASS" or "STORY5 STAGING STATUS: FAIL"; exits non-zero on FAIL.

    .venv\\Scripts\\python.exe etl\\validate_story5_staging.py
"""

from __future__ import annotations

import csv
import io
import json
import math
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import column_index_from_string

from cleaning_common import PROJECT_ROOT, RAW_DIR, STAGING_DIR, sha256_file, verify_raw_manifest

ETL = Path(__file__).resolve().parent
MAP_PATH = ETL / "cma_geography_map.csv"
CANADA_MANIFEST = ETL / "raw_canada_history_manifest.json"
HISTORY_MANIFEST = ETL / "raw_history_manifest.json"
STAGING_BASELINE = ETL / "story5_pre_staging_baseline.json"
REPORT = PROJECT_ROOT / "docs" / "STORY5_STAGING_VALIDATION.md"
FILES = {"history": "canada_cma_rental_history.csv", "profile": "canada_cma_housing_profile.csv",
         "universe": "canada_cma_rental_universe.csv"}

# --- expectations restated from the approved audit ---------------------------
YEARS = set(range(2019, 2026))
METRICS = {"vacancy_rate", "average_rent_2br", "turnover_rate", "fixed_sample_rent_change_2br"}
ALLOWLIST = {1, 41, 46, 47, 50, 243, 244, 252, 1414, 1415, 1416, 1417, 1484, 1490, 1491, 1492, 1493, 1494, 1495}
KEY_PROFILE_IDS = [1414, 1416, 1490, 1491, 1492, 1493, 1494, 1495, 243]
EXPLICIT = {
    "Kitchener-Cambridge-Waterloo CMA": "2021S0503541", "St. Catharines-Niagara CMA": "2021S0503539",
    "Abbotsford-Mission CMA": "2021S0503932", "Greater Sudbury/Grand Sudbury CMA": "2021S0503580",
    "Ottawa-Gatineau CMA (Ont. part)": "2021S050535505", "Ottawa-Gatineau CMA (Qué. part)": "2021S050524505",
    "Belleville - Quinte West CMA": "2021S0503522", "Belleville CMA": "2021S0503522",
}
FOCUS = {"2021S0503559": "Windsor", "2021S0503555": "London", "2021S0503537": "Hamilton",
         "2021S0503541": "Kitchener-Cambridge-Waterloo", "2021S0503535": "Toronto"}
WINDSOR = "2021S0503559"
WINDSOR_BENCH = {(1416, "count_total"): 45625, (1416, "rate_total"): 27.5, (1492, "count_total"): 34.8,
                 (1493, "count_total"): 20.3, (1494, "count_total"): 980}
WINDSOR_UNIVERSE_2021 = 16314
WORKBOOKS = {y: f"data/raw/cmhc/canada_history/rmr-canada-{y}-en.xlsx" for y in range(2019, 2025)}
WORKBOOKS[2025] = "data/raw/cmhc/rmr-canada-2025-en.xlsx"
CENSUS_ZIP = "data/raw/statcan/98-401-X2021002_eng_CSV.zip"
# metric -> (current value col, previous value col, trend col) in Table 1.0
T10 = {"vacancy_rate": ("D", "B", "F"), "turnover_rate": ("I", "G", "K"),
       "average_rent_2br": ("N", "L", None), "fixed_sample_rent_change_2br": ("R", "P", None)}
TREND_GLYPH = {"↑": "significant_increase", "↓": "significant_decrease", "-": "not_significant",
               "–": "not_significant", "−": "not_significant"}


@dataclass
class Check:
    area: str
    name: str
    passed: bool
    detail: str


def t(v):
    if v is None:
        return None
    s = " ".join(str(v).split())
    return s or None


def num(v) -> float:
    return float(str(v).replace(",", "").strip())


def same(a, b, tol=1e-9) -> bool:
    a_nan = a is None or (isinstance(a, float) and math.isnan(a))
    b_nan = b is None or (isinstance(b, float) and math.isnan(b))
    if a_nan or b_nan:
        return a_nan and b_nan
    return abs(float(a) - float(b)) <= tol


def load(staging_dir: Path) -> dict:
    out = {}
    for k, f in FILES.items():
        p = staging_dir / f
        out[k] = pd.read_csv(p, dtype={"cma_dguid": str, "alt_geo_code": str, "reliability_code": str,
                                       "raw_value": str}, keep_default_na=True, encoding="utf-8") if p.exists() else None
    return out


def cmhc_cma_label(label: str) -> bool:
    return label.endswith(" CMA") or " CMA (" in label


def source_labels(raw_root: Path) -> tuple[dict[int, set], set]:
    """Independent scan of column A of every Table 1.0 and 2021 Table 5.0."""
    per_year = {}
    for y, rel in WORKBOOKS.items():
        ws = openpyxl.load_workbook(raw_root / rel, read_only=True, data_only=True)["Table 1.0"]
        per_year[y] = {t(r[0]) for r in ws.iter_rows(values_only=True) if t(r[0]) and cmhc_cma_label(t(r[0]))}
    ws = openpyxl.load_workbook(raw_root / WORKBOOKS[2021], read_only=True, data_only=True)["Table 5.0"]
    t5 = {t(r[0]) for r in ws.iter_rows(values_only=True) if t(r[0]) and cmhc_cma_label(t(r[0]))}
    return per_year, t5


def census_cma(raw_root: Path) -> tuple[dict, dict]:
    geos, cells = {}, {}
    with zipfile.ZipFile(raw_root / CENSUS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open("98-401-X2021002_English_CSV_data.csv"), encoding="cp1252", newline=""))
        next(rd)
        for r in rd:
            if r[3] not in ("Census metropolitan area", "Census metropolitan area part"):
                continue
            geos.setdefault(r[1], (r[4], r[3], r[2], r[5], r[6], r[7]))
            if int(r[8]) in ALLOWLIST:
                cells[(r[1], int(r[8]))] = r
    return geos, cells


# ---------------------------------------------------------------------------

def geography_checks(m: pd.DataFrame, labels: dict, t5: set, geos: dict, d: dict) -> list[Check]:
    c = []
    all_labels = set().union(*labels.values()) | t5
    c.append(Check("geography", "map: cmhc_centre_name unique, required columns present",
                   not m.cmhc_centre_name.duplicated().any() and {"cma_dguid", "statcan_geo_name", "cmhc_centre_name",
                   "match_rule", "boundary_changed_flag", "focus_peer"} <= set(m.columns), f"{len(m)} map rows"))
    missing, extra = all_labels - set(m.cmhc_centre_name), set(m.cmhc_centre_name) - all_labels
    c.append(Check("geography", "every source CMA label maps exactly once (none unmapped, none extra)",
                   not missing and not extra, f"{len(all_labels)} source labels; unmapped={sorted(missing)} extra={sorted(extra)}"))
    bad = []
    for r in m.itertuples():
        g = geos.get(r.cma_dguid)
        if g is None or g[0] != r.statcan_geo_name or g[1] != r.statcan_geo_level:
            bad.append(r.cmhc_centre_name); continue
        if r.match_rule == "exact_after_cma_suffix":
            if r.cmhc_centre_name in EXPLICIT or r.cmhc_centre_name[:-4] != g[0] or not r.cmhc_centre_name.endswith(" CMA"):
                bad.append(r.cmhc_centre_name)
        elif r.match_rule == "explicit_lookup":
            if EXPLICIT.get(r.cmhc_centre_name) != r.cma_dguid:
                bad.append(r.cmhc_centre_name)
        else:
            bad.append(r.cmhc_centre_name)
    c.append(Check("geography", "deterministic rules only: exact-after-suffix or the 8 audited explicit lookups; DGUID/name/level match Census",
                   not bad and set(m[m.match_rule == "explicit_lookup"].cmhc_centre_name) == set(EXPLICIT),
                   f"bad={bad}; explicit={int((m.match_rule == 'explicit_lookup').sum())}"))
    flagged = set(m[m.boundary_changed_flag].cmhc_centre_name)
    c.append(Check("geography", "boundary_changed_flag only on 'Belleville CMA'", flagged == {"Belleville CMA"}, f"{sorted(flagged)}"))
    fp = dict(zip(m[m.focus_peer].cma_dguid, m[m.focus_peer].focus_peer_label))
    c.append(Check("geography", "focus_peer flags exactly Windsor, London, Hamilton, Kitchener-Cambridge-Waterloo, Toronto",
                   fp == FOCUS, f"{sorted(fp.values())}"))
    h, u, p = d["history"], d["universe"], d["profile"]
    dup = h.groupby(["year", "geography_basis", "metric"]).cma_dguid.apply(lambda s: s.duplicated().any()).any()
    dup_names = h.groupby(["year", "geography_basis", "cma_dguid"]).cmhc_centre_name.nunique().max() > 1
    c.append(Check("geography", "no duplicate DGUID within any year/basis (history) or in the universe",
                   not dup and not dup_names and not u.cma_dguid.duplicated().any(), ""))
    n21 = h[h.year == 2021].cma_dguid.nunique()
    prof_dg = set(p.cma_dguid)
    matched21 = set(h[h.year == 2021].cma_dguid) & set(u.cma_dguid) & prof_dg
    c.append(Check("geography", "36 safely matched CMA-level geographies for 2021 (CMHC Table 1.0 ∩ Table 5.0 ∩ Census)",
                   n21 == 36 and len(matched21) == 36 and len(labels[2021]) == 36, f"T1.0 2021={n21}, matched={len(matched21)}"))
    counts = {y: h[(h.year == y) & (h.geography_basis == "2021_census")].cma_dguid.nunique() for y in (2022, 2023, 2024, 2025)}
    c.append(Check("geography", "42 CMA-level geographies on the 2021-census basis for 2022 (revised) and 2023-2025",
                   all(v == 42 for v in counts.values()) and all(len(labels[y]) == 42 for y in (2023, 2024, 2025)), f"{counts}"))
    missing_peers = [n for dg, n in FOCUS.items()
                     if not (set(h[(h.cma_dguid == dg) & h.is_primary_series].year) == YEARS
                             and dg in prof_dg and dg in set(u.cma_dguid))]
    c.append(Check("geography", "all 5 focus peers present every year 2019-2025, in the Census profile and the 2021 universe",
                   not missing_peers, f"missing={missing_peers}"))
    return c


def history_checks(h: pd.DataFrame, raw_root: Path, staging_dir: Path) -> list[Check]:
    c = []
    c.append(Check("history", "years exactly 2019-2025", set(h.year) == YEARS, f"{sorted(set(h.year))}"))
    c.append(Check("history", "metrics exactly the 4 audited metrics", set(h.metric) == METRICS, f"{sorted(set(h.metric))}"))
    c.append(Check("history", "row count = 1,248 (36x4x3 + 36x4 + 42x4x4)", len(h) == 1248, f"{len(h)}"))
    basis_ok = all(((r.year <= 2021 and r.geography_basis == "pre_2021_census") or
                    (r.year >= 2023 and r.geography_basis == "2021_census") or r.year == 2022)
                   for r in h.itertuples())
    y22 = h[h.year == 2022]
    pre, rev = y22[y22.geography_basis == "pre_2021_census"], y22[y22.geography_basis == "2021_census"]
    c.append(Check("history", "geography basis by year (2019-21 pre_2021_census, 2023-25 2021_census)", basis_ok, ""))
    c.append(Check("history", "2022 keeps both bases: pre_2021 (edition 2022, current, not primary) and 2021_census (edition 2023, previous, primary)",
                   pre.cma_dguid.nunique() == 36 and rev.cma_dguid.nunique() == 42 and not pre.is_primary_series.any()
                   and rev.is_primary_series.all() and set(pre.source_edition_year) == {2022}
                   and set(rev.source_edition_year) == {2023} and set(rev.source_column_role) == {"previous"},
                   f"pre={pre.cma_dguid.nunique()} CMAs, revised={rev.cma_dguid.nunique()} CMAs"))
    prim = h[h.is_primary_series].groupby(["cma_dguid", "year", "metric"]).size()
    allk = h.groupby(["cma_dguid", "year", "metric"]).size()
    c.append(Check("history", "exactly one primary row per CMA x year x metric",
                   (prim == 1).all() and len(prim) == len(allk), f"{len(prim)} primary keys / {len(allk)} keys"))
    ok_status = h.value_status.isin(["published", "suppressed", "change_not_significant"]).all()
    null_rule = (h.value.isna() == (h.value_status != "published")).all()
    marker = ((h.value_status != "suppressed") | (h.raw_value == "**")).all() and \
             ((h.value_status != "change_not_significant") | (h.raw_value == "++")).all() and \
             (~h.raw_value.isin(["**", "++"]) | (h.value_status != "published")).all()
    cns_only_fixed = set(h[h.value_status == "change_not_significant"].metric) <= {"fixed_sample_rent_change_2br"}
    c.append(Check("history", "'**' -> NULL+suppressed, '++' -> NULL+change_not_significant; NULL iff not published; never zero-filled",
                   ok_status and null_rule and marker and cns_only_fixed,
                   f"{h.value_status.value_counts().to_dict()}"))
    rel_ok = h.reliability_code.dropna().isin(list("abcd")).all() and \
        h[h.value_status == "published"].reliability_code.notna().all()
    c.append(Check("history", "reliability codes in {a,b,c,d}; every published value carries one", rel_ok,
                   f"{h.reliability_code.value_counts(dropna=False).to_dict()}"))
    tr = h[h.yoy_trend.notna()]
    trend_ok = tr.metric.isin(["vacancy_rate", "turnover_rate"]).all() and (tr.source_column_role == "current").all() \
        and tr.yoy_trend.isin(set(TREND_GLYPH.values())).all()
    c.append(Check("history", "trend flags only on vacancy/turnover current-column rows, valid values", trend_ok,
                   f"{len(tr)} trend values"))
    lin = ["cmhc_centre_name", "statcan_geo_name", "source_workbook", "source_table", "source_cell",
           "source_edition_year", "source_column_role"]
    c.append(Check("history", "source lineage complete and unique (workbook + cell)",
                   h[lin].notna().all().all() and not h.duplicated(["source_workbook", "source_cell"]).any(), ""))
    rates = h[h.metric.isin(["vacancy_rate", "turnover_rate"])].value.dropna()
    rents = h[h.metric == "average_rent_2br"].value.dropna()
    chg = h[h.metric == "fixed_sample_rent_change_2br"].value.dropna()
    c.append(Check("history", "ranges: rates 0-100, rents > 0, fixed-sample change -100..100",
                   rates.between(0, 100).all() and (rents > 0).all() and chg.between(-100, 100).all(), ""))
    # independent cell re-read
    mism, n = [], 0
    books = {}
    for r in h.itertuples():
        wb = books.get(r.source_workbook)
        if wb is None:
            wb = books[r.source_workbook] = openpyxl.load_workbook(raw_root / r.source_workbook, data_only=True)
        ws = wb[r.source_table]
        ref = r.source_cell.split("!")[1]
        col = "".join(ch for ch in ref if ch.isalpha()); row = int(ref[len(col):])
        cur, prev, trc = T10[r.metric]
        exp_col = cur if r.source_column_role == "current" else prev
        raw = ws[ref].value
        rv = t(raw)
        exp_status = {"**": "suppressed", "++": "change_not_significant"}.get(rv, "published")
        exp_val = math.nan if exp_status != "published" else num(raw)
        rel = t(ws.cell(row, column_index_from_string(col) + 1).value)
        hdr = next(i for i in range(1, 12) if t(ws.cell(i, 1).value) == "Centre")
        period = t(ws.cell(hdr, column_index_from_string(col)).value)
        yy = f"{r.year % 100:02d}"
        exp_period = f"Oct-{(r.year - 1) % 100:02d} to Oct-{yy}" if r.metric == "fixed_sample_rent_change_2br" else f"Oct-{yy}"
        trend = None
        if trc and r.source_column_role == "current":
            trend = TREND_GLYPH.get(t(ws[f"{trc}{row}"].value))
        n += 1
        problems = []
        if col != exp_col: problems.append("column")
        if t(ws.cell(row, 1).value) != r.cmhc_centre_name: problems.append("label")
        if period != exp_period: problems.append(f"period {period!r}")
        if exp_status != r.value_status or not same(exp_val, r.value): problems.append("value")
        if (rel or None) != (r.reliability_code if isinstance(r.reliability_code, str) else None): problems.append("reliability")
        if trend != (r.yoy_trend if isinstance(r.yoy_trend, str) else None): problems.append("trend")
        if problems:
            mism.append(f"{r.source_cell} {r.source_workbook[-17:]}: {problems}")
    c.append(Check("history", "every row re-read independently from its source cell (label, period header, value, marker, reliability, trend)",
                   not mism, f"{n} rows re-read; mismatches={mism[:5]}"))
    # Windsor vs the validated Windsor history pipeline
    wh = pd.read_csv(staging_dir / "windsor_rental_market_history.csv")
    wh = wh[wh.metric.isin(["vacancy_rate", "average_rent", "turnover_rate"])]
    w = h[h.cma_dguid == WINDSOR]
    diffs, k = [], 0
    for r in wh.itertuples():
        metric = "average_rent_2br" if r.metric == "average_rent" else r.metric
        mine = w[(w.year == r.year) & (w.geography_basis == r.geography_basis) & (w.metric == metric)]
        k += 1
        if len(mine) != 1 or not same(mine.value.iloc[0], r.value) or bool(mine.is_primary_series.iloc[0]) != bool(r.is_primary_series):
            diffs.append((r.year, r.geography_basis, r.metric, r.value, None if mine.empty else mine.value.iloc[0]))
    c.append(Check("history", "Windsor vacancy/2BR rent/turnover reconcile with validated windsor_rental_market_history.csv (value, basis, primary flag)",
                   not diffs and k == 24, f"{k} comparisons; diffs={diffs}"))
    # 2025 vs the existing verified Canada 2025 staging (Table 1.0 Oct-25)
    cc = pd.read_csv(staging_dir / "canada_rental_market_comparison.csv")
    cc = cc[cc.period_label.isin(["Oct-25", "Oct-24 to Oct-25"])]
    ren = {"rent_pct_change_2br": "fixed_sample_rent_change_2br"}
    h25 = h[h.year == 2025]
    diffs, k = [], 0
    for r in cc.itertuples():
        mine = h25[(h25.cmhc_centre_name == r.centre) & (h25.metric == ren.get(r.metric, r.metric))]
        k += 1
        if len(mine) != 1 or not same(mine.value.iloc[0], r.value) or mine.value_status.iloc[0] != r.value_status:
            diffs.append((r.centre, r.metric))
    c.append(Check("history", "2025 rows reconcile with existing verified canada_rental_market_comparison.csv (Oct-25)",
                   not diffs and k == 42 * 4, f"{k} comparisons; diffs={diffs[:5]}"))
    return c


def profile_checks(p: pd.DataFrame, geos: dict, cells: dict, mapped_dguids: set) -> list[Check]:
    c = []
    c.append(Check("statcan", "characteristic IDs exactly the approved allowlist (19)", set(p.characteristic_id) == ALLOWLIST,
                   f"{sorted(set(p.characteristic_id) ^ ALLOWLIST)}"))
    c.append(Check("statcan", "geography grain: all 43 CMA-level geographies (41 CMA + 2 parts), nothing else",
                   set(p.cma_dguid) == set(geos) and len(geos) == 43
                   and set(p.geo_level) == {"Census metropolitan area", "Census metropolitan area part"}
                   and len(p) == 43 * 19, f"{p.cma_dguid.nunique()} geographies, {len(p)} rows"))
    c.append(Check("statcan", "no duplicate cma_dguid x characteristic_id", not p.duplicated(["cma_dguid", "characteristic_id"]).any(), ""))
    null_ok = (p.count_total.isna() == ~p.count_status.isin(["published", "use_with_caution", "revised"])).all() and \
              (p.rate_total.isna() == ~p.rate_status.isin(["published", "use_with_caution", "revised"])).all()
    c.append(Check("statcan", "NULL iff status withholds the value (no zero-filling)", null_ok,
                   f"count {p.count_status.value_counts().to_dict()}; rate {p.rate_status.value_counts().to_dict()}"))
    key = p[p.cma_dguid.isin(mapped_dguids) & p.characteristic_id.isin(KEY_PROFILE_IDS)]
    bad = key[(key.count_status != "published") | key.count_total.isna()]
    c.append(Check("statcan", "key fields published for every CMHC-matched geography (1414, 1416, 1490-1495, 243)",
                   bad.empty and key.cma_dguid.nunique() == len(mapped_dguids), f"{key.cma_dguid.nunique()} geographies; unpublished={len(bad)}"))
    sym = {"": "published", "...": "not_applicable", "x": "suppressed", "..": "not_available", "F": "too_unreliable",
           "E": "use_with_caution", "r": "revised"}
    mism = []
    for r in p.itertuples():
        s = cells.get((r.cma_dguid, r.characteristic_id))
        if s is None:
            mism.append((r.cma_dguid, r.characteristic_id, "absent")); continue
        cv = math.nan if s[11].strip() == "" else float(s[11])
        rv = math.nan if s[17].strip() == "" else float(s[17])
        if not (same(cv, r.count_total) and same(rv, r.rate_total) and sym[s[12].strip()] == r.count_status
                and sym[s[18].strip()] == r.rate_status and t(s[9]) == r.characteristic_name
                and s[4] == r.geo_name and s[2] == r.alt_geo_code and s[7] == str(r.data_quality_flag).zfill(5)
                and same(float(s[6]), r.tnr_lf)):
            mism.append((r.cma_dguid, r.characteristic_id))
    c.append(Check("statcan", "every row reconciles cell by cell with the Census Profile ZIP", not mism and len(cells) == len(p),
                   f"{len(p)} rows; mismatches={mism[:5]}"))
    w = p[p.cma_dguid == WINDSOR].set_index("characteristic_id")
    got = {k: w.loc[k[0], k[1]] for k in WINDSOR_BENCH}
    c.append(Check("statcan", "Windsor benchmarks: renters 45,625; renter share 27.5; tenant 30%+ 34.8; core need 20.3; median rented shelter cost 980",
                   all(same(got[k], v) for k, v in WINDSOR_BENCH.items()),
                   ", ".join(f"{k[0]}.{k[1]}={float(got[k]):g}" for k in got)))
    income_ids = set(p[p.characteristic_name.str.contains(r"^(?:Median|Average) .*income", regex=True)].characteristic_id)
    c.append(Check("statcan", "no renter-income field present or derived (income measures only all-tenure 243/244/252; no extra columns)",
                   income_ids == {243, 244, 252}
                   and all("household" in n for n in p[p.characteristic_id.isin(income_ids)].characteristic_name)
                   and set(p.columns) == {"census_year", "cma_dguid", "alt_geo_code", "geo_level", "geo_name", "tnr_sf", "tnr_lf",
                   "data_quality_flag", "characteristic_id", "characteristic_name", "characteristic_note", "count_total",
                   "count_status", "rate_total", "rate_status", "unit", "source_file"}, ""))
    return c


def universe_checks(u: pd.DataFrame, h: pd.DataFrame, raw_root: Path) -> list[Check]:
    c = []
    c.append(Check("universe", "2021 only, edition 2021 Table 5.0 only (no 2020, no trend)",
                   set(u.year) == {2021} and set(u.source_edition_year) == {2021} and set(u.source_table) == {"Table 5.0"}
                   and set(u.source_workbook) == {WORKBOOKS[2021]}, ""))
    c.append(Check("universe", "coverage = the 36 CMA-level geographies of CMHC 2021 Table 1.0",
                   len(u) == 36 and set(u.cma_dguid) == set(h[h.year == 2021].cma_dguid), f"{len(u)} rows"))
    wv = u[u.cma_dguid == WINDSOR].universe_units.tolist()
    c.append(Check("universe", "Windsor Oct-2021 universe = 16,314", wv == [WINDSOR_UNIVERSE_2021], f"{wv}"))
    c.append(Check("universe", "scope/basis/warning columns fixed: row_and_apartment_3plus_private, pre_2021_census, severity 'material'",
                   set(u.dwelling_scope) == {"row_and_apartment_3plus_private"} and set(u.geography_basis) == {"pre_2021_census"}
                   and set(u.boundary_mismatch_severity) == {"material"} and u.count_ratio_warning.str.startswith("WARNING").all(), ""))
    ws = openpyxl.load_workbook(raw_root / WORKBOOKS[2021], data_only=True)["Table 5.0"]
    mism = []
    for r in u.itertuples():
        ref = r.source_cell.split("!")[1]; row = int(ref[1:])
        hdr = max(i for i in range(1, 30) if t(ws.cell(i, 1).value) == "Centre")
        if not (ref.startswith("E") and t(ws.cell(hdr, 5).value) == "Universe" and t(ws.cell(row, 1).value) == r.cmhc_centre_name
                and num(ws[ref].value) == r.universe_units and r.universe_units > 0):
            mism.append(r.source_cell)
    c.append(Check("universe", "every value re-read independently from Table 5.0 column 'Universe' (positive integers)", not mism,
                   f"mismatches={mism}"))
    return c


def integrity_checks(raw_root: Path) -> list[Check]:
    c = []
    p1 = verify_raw_manifest()
    c.append(Check("raw", "raw files unchanged vs etl/raw_manifest.json (incl. Census ZIP, CMHC Canada 2025)", not p1, "; ".join(p1)))
    for label, path in (("raw_history_manifest.json", HISTORY_MANIFEST), ("raw_canada_history_manifest.json", CANADA_MANIFEST)):
        exp = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        bad = ["manifest missing"] if exp is None else [rel for rel, meta in exp.items()
                                                       if sha256_file(RAW_DIR / rel) != meta["sha256"]]
        c.append(Check("raw", f"raw files unchanged vs etl/{label}", not bad, f"{0 if exp is None else len(exp)} files; changed={bad}"))
    return c


def regression_checks() -> list[Check]:
    c = []
    exp = json.loads(STAGING_BASELINE.read_text(encoding="utf-8")) if STAGING_BASELINE.exists() else None
    bad = ["baseline missing"] if exp is None else [f for f, meta in exp.items() if sha256_file(STAGING_DIR / f) != meta["sha256"]]
    c.append(Check("regression", "existing verified staging outputs byte-identical to pre-Story-5 baseline", not bad,
                   f"{0 if exp is None else len(exp)} files; changed={bad}"))
    import validate_cleaned_data as vcd
    import validate_rental_history as vrh
    a = vcd.run_checks()[0]
    b = vrh.run_checks()
    c.append(Check("regression", "existing cleaning validation still passes", all(x.passed for x in a), f"{sum(x.passed for x in a)}/{len(a)}"))
    c.append(Check("regression", "existing Windsor history validation still passes", all(x.passed for x in b), f"{sum(x.passed for x in b)}/{len(b)}"))
    return c


def run_checks(staging_dir: Path = STAGING_DIR, map_path: Path = MAP_PATH, raw_root: Path = PROJECT_ROOT,
               include_regression: bool = True) -> list[Check]:
    checks = integrity_checks(raw_root)
    d = load(staging_dir)
    missing = [FILES[k] for k, v in d.items() if v is None]
    checks.append(Check("files", "3 Story 5 staging files and the geography map exist", not missing and map_path.exists(), f"missing={missing}"))
    if missing or not map_path.exists():
        return checks
    m = pd.read_csv(map_path, dtype=str, keep_default_na=False, encoding="utf-8")
    m["boundary_changed_flag"] = m.boundary_changed_flag == "True"
    m["focus_peer"] = m.focus_peer == "True"
    m = m.rename(columns={})
    labels, t5 = source_labels(raw_root)
    geos, cells = census_cma(raw_root)
    for area, fn in (("geography", lambda: geography_checks(m, labels, t5, geos, d)),
                     ("history", lambda: history_checks(d["history"], raw_root, staging_dir)),
                     ("statcan", lambda: profile_checks(d["profile"], geos, cells, set(m.cma_dguid))),
                     ("universe", lambda: universe_checks(d["universe"], d["history"], raw_root))):
        try:
            checks += fn()
        except Exception as exc:  # a crashing check is a failed check
            checks.append(Check(area, "checks ran", False, f"{type(exc).__name__}: {exc}"))
    if include_regression:
        try:
            checks += regression_checks()
        except Exception as exc:
            checks.append(Check("regression", "checks ran", False, f"{type(exc).__name__}: {exc}"))
    return checks


def render(checks: list[Check], d: dict) -> str:
    failed = [x for x in checks if not x.passed]
    h, p, u = d["history"], d["profile"], d["universe"]
    lines = [f"STORY5 STAGING STATUS: {'FAIL' if failed else 'PASS'}", "",
             "# Story 5 staging validation", "",
             f"Generated {datetime.now():%Y-%m-%d %H:%M} by `etl/validate_story5_staging.py` "
             f"({len(checks) - len(failed)}/{len(checks)} checks passed).",
             "Design: `docs/STORY5_CROSS_DATASET_AUDIT.md` (decision D1: Census 2021 + CMHC October 2021).", "",
             "| Area | Check | Result | Detail |", "|---|---|---|---|"]
    for x in checks:
        lines.append(f"| {x.area} | {x.name} | {'PASS' if x.passed else '**FAIL**'} | {str(x.detail).replace('|', '/')} |")
    if h is not None and p is not None and u is not None:
        lines += ["", "## Benchmark values", "",
                  "Primary series, CMHC Table 1.0 (2BR rent $ / vacancy % / turnover %):", "",
                  "| CMA | 2019 | 2021 | 2025 |", "|---|---|---|---|"]
        for dg, name in FOCUS.items():
            cells_ = []
            for y in (2019, 2021, 2025):
                s = h[(h.cma_dguid == dg) & (h.year == y) & h.is_primary_series].set_index("metric").value
                cells_.append(f"{s['average_rent_2br']:,.0f} / {s['vacancy_rate']} / {s['turnover_rate']}")
            lines.append(f"| {name} | " + " | ".join(cells_) + " |")
        lines += ["", "Census 2021 (renters / renter share % / tenant 30%+ % / core need % / median rented shelter cost $) "
                  "and CMHC Oct-2021 row+apartment universe:", "",
                  "| CMA | Renters | Share | 30%+ | Core need | Median shelter cost | Universe 2021 |", "|---|---|---|---|---|---|---|"]
        for dg, name in FOCUS.items():
            w = p[p.cma_dguid == dg].set_index("characteristic_id")
            uv = u[u.cma_dguid == dg].universe_units.iloc[0]
            lines.append(f"| {name} | {w.loc[1416, 'count_total']:,.0f} | {w.loc[1416, 'rate_total']} | {w.loc[1492, 'count_total']} | "
                         f"{w.loc[1493, 'count_total']} | {w.loc[1494, 'count_total']:,.0f} | {uv:,} |")
        lines += ["", "## Caveats carried forward (audit D2/D3)", "",
                  "- CMHC 2019-2021 and the 2022 `pre_2021_census` rows use 2016-census CMA boundaries; Census 2021 and "
                  "CMHC 2022 (revised)-2025 use 2021-census boundaries. Do not draw a continuous line across 2021->2022 "
                  "except on `is_primary_series = true`, flagged as a basis change.",
                  "- `canada_cma_rental_universe.csv` is Oct-2021 row + apartment on 2016-census boundaries and carries "
                  "`boundary_mismatch_severity = 'material'` and `count_ratio_warning`. No ratio is computed at staging.",
                  "- `Belleville CMA` (2019-2022) and `Belleville - Quinte West CMA` (2023+) share DGUID 2021S0503522; the old "
                  "name is flagged `boundary_changed_flag = true`.",
                  "- Ottawa - Gatineau is represented only by its two CMA parts; the whole-CMA Census row has no CMHC match.",
                  "- The Census Profile has no renter-income field; none is derived."]
    return "\n".join(lines) + "\n"


def main() -> int:
    checks = run_checks()
    REPORT.write_text(render(checks, load(STAGING_DIR)), encoding="utf-8")
    failed = [x for x in checks if not x.passed]
    for x in failed:
        print(f"FAIL [{x.area}] {x.name}: {x.detail}")
    print(f"STORY5 STAGING STATUS: {'FAIL' if failed else 'PASS'} ({len(checks) - len(failed)}/{len(checks)} checks passed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
