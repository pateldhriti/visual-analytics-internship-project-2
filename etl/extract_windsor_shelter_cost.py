"""
Extract Windsor CMA records from Statistics Canada table 98-10-0252-01
(Shelter-cost-to-income ratio by tenure).

The source CSV is ~1.28 GB and covers every geography in Canada. This script
streams it in chunks, keeps only rows for Windsor (CMA), Ont., and writes the
matches incrementally to a staging CSV. The source file is opened read-only
and is never loaded into memory in full.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_windsor_shelter_cost.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "raw" / "shelter_cost" / "98100252.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_shelter_cost.csv"

GEO_FILTER = "Windsor (CMA), Ont."
CHUNK_SIZE = 150_000
ENCODING = "utf-8-sig"


def extract_windsor_rows(
    source_csv: Path = SOURCE_CSV,
    output_csv: Path = OUTPUT_CSV,
    geo_filter: str = GEO_FILTER,
    chunksize: int = CHUNK_SIZE,
) -> dict:
    """Stream `source_csv` in chunks and write rows matching `geo_filter` to `output_csv`.

    Every column is read as a string so published values (including special
    symbols like 'x', 'F', '..') are preserved exactly rather than coerced.
    Returns summary counts used to verify the extraction independently of
    any prior estimate.
    """
    if not source_csv.exists():
        raise FileNotFoundError(f"Source CSV not found: {source_csv}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if output_csv.exists():
        output_csv.unlink()

    total_source_rows = 0
    total_written_rows = 0
    geo_values_seen: set[str] = set()
    dguid_values_seen: set[str] = set()
    header_written = False
    source_columns: list[str] | None = None

    reader = pd.read_csv(
        source_csv,
        chunksize=chunksize,
        encoding=ENCODING,
        dtype=str,
        low_memory=False,
    )

    for chunk in reader:
        if source_columns is None:
            source_columns = list(chunk.columns)

        total_source_rows += len(chunk)
        geo_values_seen.update(chunk["GEO"].dropna().unique())

        match = chunk[chunk["GEO"] == geo_filter]
        if match.empty:
            continue

        dguid_values_seen.update(match["DGUID"].dropna().unique())
        total_written_rows += len(match)

        match.to_csv(
            output_csv,
            mode="a",
            header=not header_written,
            index=False,
            encoding="utf-8",
        )
        header_written = True

    return {
        "source_csv": str(source_csv),
        "output_csv": str(output_csv),
        "geo_filter": geo_filter,
        "total_source_rows": total_source_rows,
        "total_written_rows": total_written_rows,
        "source_columns": source_columns,
        "unique_geo_values_in_source": len(geo_values_seen),
        "dguid_values_for_filter": sorted(dguid_values_seen),
    }


if __name__ == "__main__":
    stats = extract_windsor_rows()
    print("Extraction complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
