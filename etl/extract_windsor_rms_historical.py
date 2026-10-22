"""
Extract the 6 "standard-shape" time-series sheets (vacancy, rent, universe,
turnover -- Combined and Apartment scope) from 4 additional Windsor RMS
editions (2021-2024), into the same long-format shape and the same
warehouse.fact_rental_market table etl/extract_windsor_rms.py already loads
from the 2025 edition.

Scope note, read before assuming this covers "10 years": CMHC's digital RMS
portal only has direct-download Windsor editions back to 2021 -- confirmed
by testing the URL pattern against 2015-2020 (all 404) and by searching for
an alternate access point (CMHC's own materials say survey data exists back
to 2006, but only through their Housing Knowledge Centre's browse/search
interface, which needs interactive browser access this project's tooling
doesn't have in an automated session -- same blocker
docs/starts_history_profile.md already hit for a different CMHC table).
2015-2020 remain genuinely unavailable, not just unextracted.

Only the 6 time-series sheets are extracted here, not 3.1.7/3.1.8/3.1.9 --
those are single-snapshot-as-of-this-edition tables (new-stock profile,
income quintile, vacant-vs-occupied rent), not a time series within a
single edition, so layering 4 more editions' worth of them doesn't add a
trend the way the 6 rate/universe sheets do. They're also what Story 2's
planned SQL views (rent YoY change, growth rate, vacancy trend, turnover by
bedroom type) actually need.

Zone and bedroom-type renames found by comparing real cell values across
all 5 editions (2021-2025), not assumed from labels alone -- see
ZONE_RENAME_MAP and BEDROOM_RENAME_MAP below for exactly what changed and
the evidence it's a rename, not a geography redraw.

Each edition covers 2 periods (e.g. the 2021 workbook has Oct-20 and
Oct-21 columns). To avoid loading the same real period twice from two
different editions' overlapping columns, every period with 2 available
sources is cross-checked for agreement first (logged in the extraction
summary), then loaded from exactly one of them -- never both.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_windsor_rms_historical.py
"""

from pathlib import Path

import openpyxl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "cmhc"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_rental_market_historical.csv"

FIRST_ZONE_ROW = 8
BEDROOM_HEADER_ROW = 6

# Editions genuinely available (confirmed by direct download, 2015-2020 all
# 404 -- see module docstring). Each maps to the (prior, latest) periods its
# own workbook covers.
EDITIONS = {
    2021: ("Oct-20", "Oct-21"),
    2022: ("Oct-21", "Oct-22"),
    2023: ("Oct-22", "Oct-23"),
    2024: ("Oct-23", "Oct-24"),
}

# sheet name -> (metric_type, dwelling_type, layout) -- same 6 sheets
# etl/extract_windsor_rms.py reads from the 2025 edition.
SHEETS = {
    "Table 3.1.1": ("vacancy_rate", "Combined", "rate"),
    "Table 3.1.2": ("average_rent", "Combined", "rate_no_yoy"),
    "Table 3.1.3": ("universe", "Combined", "universe"),
    "Table 3.1.6": ("turnover_rate", "Combined", "rate"),
    "Table 1.1.1": ("vacancy_rate", "Apartment", "rate"),
    "Table 1.1.2": ("average_rent", "Apartment", "rate_no_yoy"),
}

# Found by diffing real zone-column values across editions (not label text
# alone -- docs/starts_history_profile.md-style "don't assume, check the
# numbers" discipline): 2021-2023 call it "Zone 6 - Remainder of CMA"; 2024
# onward splits it into "North"/"South Essex County". The 2023 edition's
# "Zone 6 - Remainder of CMA" values are continuous with 2022's and 2024's
# "Zone 6 - North Essex County" (confirmed: the universe count in 2023's
# Zone 6 column matches 2022's Zone 6 value at the matching period, and
# 2024's Zone 6 continues the same trend) -- a rename, not a redraw, so it's
# safe to map directly rather than treat as a break. "Zone 7" (Essex /
# South Essex County) has NO data at all in 2021-2022 editions -- not a
# renamed zone, a zone that wasn't reported separately yet; flagged below,
# not silently backfilled.
ZONE_RENAME_MAP = {
    "Zone 6 - Remainder of CMA": "Zone 6 - North Essex County",
    "Zone 7 - Essex": "Zone 7 - South Essex County",
}

# 2021-2024 editions label the first bedroom type "Bachelor"; 2025 renamed
# it to "Studio" (confirmed: same column position, same row-6 header cell,
# only the 2025 edition differs) -- warehouse.dim_bedroom_type is seeded
# with "Studio", so this needs the same rename treatment as the zones.
BEDROOM_RENAME_MAP = {"Bachelor": "Studio"}
BEDROOM_TYPES_RAW = ["Bachelor", "1 Bedroom", "2 Bedroom", "3 Bedroom +", "Total"]

ZONES_WITH_NO_DATA_BEFORE = {
    "Zone 7 - South Essex County": 2023,  # first edition that reports it at all
}


def real_zone_rows(ws) -> list[int]:
    """Row numbers with a real zone label, starting at FIRST_ZONE_ROW --
    NOT a fixed count. 2021-2022 editions have only 8 zone rows (no Zone 7
    yet -- it wasn't introduced until the 2023 edition), not the 9 every
    2023+ edition has; a hardcoded ZONE_ROWS=9 silently reads one blank
    phantom row past the real data for those 2 editions. Confirmed by
    reading the actual cells (2021/2022: row 15 is 'Windsor CMA', row 16 is
    None; 2023+: row 15 is 'Zone 7 - Essex'/'...South Essex County', row 16
    is 'Windsor CMA') rather than assumed from the label count alone."""
    rows = []
    r = FIRST_ZONE_ROW
    while ws.cell(row=r, column=1).value is not None:
        rows.append(r)
        r += 1
    return rows


def parse_rate_sheet(ws, metric_type: str, dwelling_type: str, prior_label: str, latest_label: str,
                      has_yoy: bool = True) -> list[dict]:
    group_width = 5 if has_yoy else 4
    rows = []
    for r in real_zone_rows(ws):
        zone = ZONE_RENAME_MAP.get(ws.cell(row=r, column=1).value, ws.cell(row=r, column=1).value)
        for b, bedroom_type_raw in enumerate(BEDROOM_TYPES_RAW):
            bedroom_type = BEDROOM_RENAME_MAP.get(bedroom_type_raw, bedroom_type_raw)
            base_col = 2 + b * group_width
            prior_value = ws.cell(row=r, column=base_col).value
            prior_reliability = ws.cell(row=r, column=base_col + 1).value
            latest_value = ws.cell(row=r, column=base_col + 2).value
            latest_reliability = ws.cell(row=r, column=base_col + 3).value
            yoy_trend = ws.cell(row=r, column=base_col + 4).value if has_yoy else None
            rows.append({"metric_type": metric_type, "dwelling_type": dwelling_type, "zone": zone,
                         "bedroom_type": bedroom_type, "period_label": prior_label, "value": prior_value,
                         "reliability_letter": prior_reliability, "yoy_trend": None})
            rows.append({"metric_type": metric_type, "dwelling_type": dwelling_type, "zone": zone,
                         "bedroom_type": bedroom_type, "period_label": latest_label, "value": latest_value,
                         "reliability_letter": latest_reliability, "yoy_trend": yoy_trend})
    return rows


def parse_universe_sheet(ws, metric_type: str, dwelling_type: str, prior_label: str, latest_label: str) -> list[dict]:
    rows = []
    for r in real_zone_rows(ws):
        zone = ZONE_RENAME_MAP.get(ws.cell(row=r, column=1).value, ws.cell(row=r, column=1).value)
        for b, bedroom_type_raw in enumerate(BEDROOM_TYPES_RAW):
            bedroom_type = BEDROOM_RENAME_MAP.get(bedroom_type_raw, bedroom_type_raw)
            base_col = 2 + b * 2
            prior_value = ws.cell(row=r, column=base_col).value
            latest_value = ws.cell(row=r, column=base_col + 1).value
            rows.append({"metric_type": metric_type, "dwelling_type": dwelling_type, "zone": zone,
                         "bedroom_type": bedroom_type, "period_label": prior_label, "value": prior_value,
                         "reliability_letter": None, "yoy_trend": None})
            rows.append({"metric_type": metric_type, "dwelling_type": dwelling_type, "zone": zone,
                         "bedroom_type": bedroom_type, "period_label": latest_label, "value": latest_value,
                         "reliability_letter": None, "yoy_trend": None})
    return rows


def clean_value(raw):
    if raw is None or raw == "**":
        return None
    if isinstance(raw, str):
        return raw.replace(",", "")
    return raw


def extract_edition(year: int, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    source_xlsx = raw_dir / f"rmr-windsor-{year}-en.xlsx"
    if not source_xlsx.exists():
        raise FileNotFoundError(f"Source workbook not found: {source_xlsx}")
    prior_label, latest_label = EDITIONS[year]

    wb = openpyxl.load_workbook(source_xlsx, data_only=True)
    all_rows = []
    for sheet_name, (metric_type, dwelling_type, layout) in SHEETS.items():
        ws = wb[sheet_name]
        if layout == "rate":
            all_rows.extend(parse_rate_sheet(ws, metric_type, dwelling_type, prior_label, latest_label, has_yoy=True))
        elif layout == "rate_no_yoy":
            all_rows.extend(parse_rate_sheet(ws, metric_type, dwelling_type, prior_label, latest_label, has_yoy=False))
        else:
            all_rows.extend(parse_universe_sheet(ws, metric_type, dwelling_type, prior_label, latest_label))

    df = pd.DataFrame(all_rows)
    df["value"] = pd.to_numeric(df["value"].map(clean_value), errors="coerce")
    df["source_edition"] = year
    return df


def cross_check_overlap(older: pd.DataFrame, newer: pd.DataFrame, period_label: str) -> dict:
    """older's `latest` period and newer's `prior` period both claim to
    report the same real period -- compare them cell-by-cell (same zone,
    bedroom_type, dwelling_type, metric_type). Returns mismatches, if any,
    rather than assuming agreement."""
    key_cols = ["zone", "bedroom_type", "dwelling_type", "metric_type"]
    a = older[older["period_label"] == period_label].set_index(key_cols)["value"]
    b = newer[newer["period_label"] == period_label].set_index(key_cols)["value"]
    joined = a.to_frame("older_value").join(b.to_frame("newer_value"), how="outer")
    mismatches = joined[
        ~((joined["older_value"] == joined["newer_value"])
          | (joined["older_value"].isna() & joined["newer_value"].isna()))
    ]
    return {"period": period_label, "cells_compared": len(joined), "mismatches": len(mismatches),
            "mismatch_examples": mismatches.head(5).reset_index().to_dict("records")}


def extract(raw_dir: Path = RAW_DIR, output_csv: Path = OUTPUT_CSV, already_loaded_oct24=None) -> dict:
    """`already_loaded_oct24`, if given, is the Oct-24 slice of
    warehouse.fact_rental_market already loaded from the 2025 edition's
    prior-year column (same shape as extract_edition()'s output, zone/
    bedroom_type/dwelling_type/metric_type/value) -- used to cross-check the
    2024 edition's own "latest" column against what's already in the
    database, since that's the same real period and loading it again would
    either duplicate it or hit the UNIQUE constraint. Without it, that
    cross-check is skipped (reported as such), but the period is still
    correctly excluded from the output either way."""
    editions_data = {year: extract_edition(year, raw_dir) for year in sorted(EDITIONS)}
    years_sorted = sorted(EDITIONS)
    last_year = years_sorted[-1]

    # Pass 1: every real period appended exactly once, from exactly one
    # edition -- each edition contributes its own "latest" period only
    # (Oct-20 is the one exception: the oldest edition's *prior* period,
    # since no older edition exists to supply it as a "latest").
    kept_frames = [editions_data[years_sorted[0]].pipe(lambda d: d[d["period_label"] == EDITIONS[years_sorted[0]][0]])]
    for year in years_sorted:
        if year == last_year:
            continue  # Oct-24 already loaded from the 2025 edition -- see below, not appended here
        _, latest_label = EDITIONS[year]
        kept_frames.append(editions_data[year].pipe(lambda d, lbl=latest_label: d[d["period_label"] == lbl]))
    long_df = pd.concat(kept_frames, ignore_index=True).drop(columns=["source_edition"])

    # Pass 2: cross-check every edition-to-edition overlap for agreement
    # (informational + the one real correction below), independent of what
    # got kept in pass 1.
    cross_checks = []
    for i, year in enumerate(years_sorted):
        if i == 0:
            continue
        prior_label, _ = EDITIONS[year]
        prev_year = years_sorted[i - 1]
        check = cross_check_overlap(editions_data[prev_year], editions_data[year], prior_label)
        cross_checks.append({"years_compared": (prev_year, year), **check})

    if already_loaded_oct24 is not None:
        oct24_df = editions_data[last_year]
        check = cross_check_overlap(oct24_df[oct24_df["period_label"] == EDITIONS[last_year][1]],
                                     already_loaded_oct24, EDITIONS[last_year][1])
        cross_checks.append({"years_compared": (last_year, 2025), **check})

    # The one real correction found by the cross-checks (not a guess -- see
    # module docstring): the Oct-22 "Windsor CMA" rollup differs between the
    # 2022 and 2023 editions because the 2023 edition correctly recomputed
    # the citywide total under the newly-split 7-zone scheme; every
    # individual zone 1-6 is identical between editions. Replace the
    # already-kept (2022 edition's pre-split) Oct-22 Windsor CMA rows with
    # the 2023 edition's recomputed ones.
    editions_2022, editions_2023 = editions_data[2022], editions_data[2023]
    revised_cma_rows = editions_2023[
        (editions_2023["period_label"] == "Oct-22") & (editions_2023["zone"] == "Windsor CMA")
    ].drop(columns=["source_edition"])
    long_df = long_df[~((long_df["period_label"] == "Oct-22") & (long_df["zone"] == "Windsor CMA"))]
    long_df = pd.concat([long_df, revised_cma_rows], ignore_index=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(output_csv, index=False)

    total_mismatches = sum(c["mismatches"] for c in cross_checks)

    return {
        "editions_extracted": sorted(EDITIONS),
        "editions_unavailable": "2015-2020 (confirmed 404 on CMHC's direct-download URL pattern; "
                                  "not reachable without interactive browser access -- see module docstring)",
        "output_csv": str(output_csv),
        "periods_loaded": sorted(long_df["period_label"].unique()),  # "Oct-YY" sorts correctly as plain text
        "total_rows": len(long_df),
        "zone_renames_applied": ZONE_RENAME_MAP,
        "bedroom_rename_applied": BEDROOM_RENAME_MAP,
        "zones_with_no_data_before": ZONES_WITH_NO_DATA_BEFORE,
        "cross_edition_checks": [
            {"years_compared": c["years_compared"], "period": c["period"],
             "cells_compared": c["cells_compared"], "mismatches": c["mismatches"]}
            for c in cross_checks
        ],
        "total_cross_check_mismatches": total_mismatches,
    }


def fetch_already_loaded_oct24():
    """Pulls the real Oct-24 Windsor rows already in warehouse.fact_rental_market
    (loaded from the 2025 edition), in the same shape as extract_edition()'s
    output, so the 2024 historical edition's own Oct-24 column can be
    cross-checked against it instead of silently skipped unverified. Returns
    None (not an error) if the warehouse isn't reachable -- this check is a
    bonus verification, not a hard requirement for the extraction to run."""
    try:
        from load_windsor_shelter_cost_to_postgres import get_engine
        from sqlalchemy import text
    except Exception:
        return None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT z.zone_label AS zone, b.bedroom_type_label AS bedroom_type,
                       d.dwelling_type_label AS dwelling_type, f.metric_type, f.value
                FROM warehouse.fact_rental_market f
                JOIN warehouse.dim_zone z ON z.zone_key = f.zone_key
                JOIN warehouse.dim_period p ON p.period_key = f.period_key
                JOIN warehouse.dim_bedroom_type b ON b.bedroom_type_key = f.bedroom_type_key
                JOIN warehouse.dim_dwelling_type d ON d.dwelling_type_key = f.dwelling_type_key
                WHERE p.period_label = 'Oct-24'
                  AND f.metric_type IN ('vacancy_rate', 'average_rent', 'universe', 'turnover_rate')
                  AND d.dwelling_type_label IN ('Combined', 'Apartment')
                  AND z.zone_level IN ('zone', 'city_subtotal', 'cma_total')
            """)).fetchall()
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=["zone", "bedroom_type", "dwelling_type", "metric_type", "value"])
        # Postgres NUMERIC comes back as Decimal; comparing Decimal('4.2') ==
        # 4.2 (float) is False in Python (binary float imprecision), not
        # because the values actually differ -- cast both sides to float
        # before any comparison, same as extract_edition()'s own pd.to_numeric.
        df["value"] = df["value"].astype(float)
        df["period_label"] = "Oct-24"
        return df
    except Exception as exc:
        print(f"  (could not reach the warehouse to cross-check Oct-24 -- skipping that check: {exc})")
        return None


if __name__ == "__main__":
    stats = extract(already_loaded_oct24=fetch_already_loaded_oct24())
    print("Historical extraction complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
