"""
Shared profiling utilities for Statistics Canada CSV exports.

Every StatCan bulk-download CSV in this project shares the same conventions:
UTF-8 with a byte-order mark, and a documented set of suppression/quality
symbols (see the Symbol Legend section of each table's *_MetaData.csv). These
functions centralize reading and profiling so every team member handles both
consistently instead of re-deriving it per dataset.

Usage from a sibling script in etl/ (python adds the script's own directory
to sys.path automatically):
    from statcan_profiling import profile_file

Usage from a notebook in notebooks/:
    import sys
    sys.path.append("../etl")
    from statcan_profiling import profile_file
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

STATCAN_ENCODING = "utf-8-sig"

# Full StatCan Symbol Legend -- confirmed against table 98-10-0252-01's own
# metadata CSV; the same symbol set is used across StatCan's bulk CSV exports.
STATCAN_SYMBOLS = {
    "..": "not available for a specific reference period",
    "...": "not applicable",
    "<LOD": "less than the limit of detection",
    "0s": "value rounded to 0 where there is a meaningful distinction from true zero",
    "A": "data quality: excellent",
    "B": "data quality: very good",
    "C": "data quality: good",
    "D": "data quality: acceptable",
    "E": "use with caution",
    "F": "too unreliable to be published",
    "p": "preliminary",
    "r": "revised",
    "x": "suppressed to meet confidentiality requirements",
    "t": "terminated",
}


def read_statcan_csv(path: str | Path, chunksize: int | None = None, **kwargs):
    """Read a StatCan CSV with the correct encoding and safe defaults.

    Every column is read as a string by default so published values
    (including symbols like 'x' or 'F') are preserved exactly rather than
    coerced. Pass chunksize to stream large files instead of loading them in
    full; the return value is then an iterator of DataFrame chunks. Extra
    kwargs are passed through to pandas.read_csv.
    """
    kwargs.setdefault("encoding", STATCAN_ENCODING)
    kwargs.setdefault("dtype", str)
    return pd.read_csv(path, chunksize=chunksize, **kwargs)


def detect_symbol_values(series: pd.Series) -> dict[str, int]:
    """Count occurrences of known StatCan symbols in a column."""
    counts = series.value_counts(dropna=True)
    return {sym: int(counts[sym]) for sym in STATCAN_SYMBOLS if sym in counts.index}


def profile_column(series: pd.Series) -> dict:
    """Summarize one column: row/null/distinct counts, numeric range, symbols."""
    non_null = series.dropna()
    numeric = pd.to_numeric(non_null, errors="coerce")
    has_numeric = bool(numeric.notna().any())
    return {
        "n_rows": len(series),
        "n_null": int(series.isna().sum()),
        "n_distinct": int(non_null.nunique()),
        "min": numeric.min() if has_numeric else None,
        "max": numeric.max() if has_numeric else None,
        "symbols": detect_symbol_values(series),
    }


def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Profile every column of a dataframe. Returns one row per column."""
    rows = []
    for col in df.columns:
        stats = profile_column(df[col])
        stats["column"] = col
        rows.append(stats)
    return pd.DataFrame(rows).set_index("column")[
        ["n_rows", "n_null", "n_distinct", "min", "max", "symbols"]
    ]


def profile_file(path: str | Path, chunksize: int | None = None, **kwargs) -> pd.DataFrame:
    """Profile a StatCan CSV end-to-end: read it and summarize every column.

    Pass chunksize for large files -- the file is streamed and per-column
    stats (nulls, distinct values, numeric range, symbols) are accumulated
    across chunks so the full file is never held in memory at once.
    """
    if chunksize is None:
        return profile_dataframe(read_statcan_csv(path, **kwargs))

    state: dict[str, dict] = {}
    for chunk in read_statcan_csv(path, chunksize=chunksize, **kwargs):
        for col in chunk.columns:
            acc = state.setdefault(
                col, {"n_rows": 0, "n_null": 0, "distinct": set(), "min": None, "max": None, "symbols": {}}
            )
            series = chunk[col]
            non_null = series.dropna()
            numeric = pd.to_numeric(non_null, errors="coerce")

            acc["n_rows"] += len(series)
            acc["n_null"] += int(series.isna().sum())
            acc["distinct"].update(non_null.unique())
            if numeric.notna().any():
                cmin, cmax = numeric.min(), numeric.max()
                acc["min"] = cmin if acc["min"] is None else min(acc["min"], cmin)
                acc["max"] = cmax if acc["max"] is None else max(acc["max"], cmax)
            for sym, count in detect_symbol_values(series).items():
                acc["symbols"][sym] = acc["symbols"].get(sym, 0) + count

    rows = []
    for col, acc in state.items():
        rows.append(
            {
                "column": col,
                "n_rows": acc["n_rows"],
                "n_null": acc["n_null"],
                "n_distinct": len(acc["distinct"]),
                "min": acc["min"],
                "max": acc["max"],
                "symbols": acc["symbols"],
            }
        )
    return pd.DataFrame(rows).set_index("column")[["n_rows", "n_null", "n_distinct", "min", "max", "symbols"]]
