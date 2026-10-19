"""
Extract Windsor CMA characteristics from Statistics Canada table 98-401-X2021002
(Census Profile, 2021 - Census Metropolitan Areas and Census Agglomerations).

The source CSV covers every CMA/CA in Canada with ~2,631 characteristics each
(population, age, income, tenure, shelter cost, etc.), one row per
(geography, characteristic) pair. This script keeps only Windsor CMA rows,
then narrows further to a curated set of ~60 characteristics covering
population, income, tenure, and shelter cost -- the dimensions this project
actually needs, out of the full census topic list.

The source file is cp1252-encoded (see etl/load_raw_files_to_postgres.py's
detect_encoding()), not utf-8.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\extract_windsor_census_profile.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "raw" / "statcan" / "98-401-X2021002_English_CSV_data.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "staging" / "windsor_census_profile.csv"

GEO_FILTER = "Windsor"
CHUNK_SIZE = 150_000
ENCODING = "cp1252"

# Curated characteristic IDs (of 2,631 total), grouped by topic. Each id is a
# row in the source -- some are header/"Total" rows, kept because they carry
# the denominator count needed to interpret the detail rows beneath them.
CHARACTERISTIC_IDS = {
    # Population and dwellings
    "1": "Population, 2021",
    "4": "Total private dwellings",
    "5": "Private dwellings occupied by usual residents",
    "6": "Population density per square kilometre",
    "7": "Land area in square kilometres",
    # Age structure (summary)
    "8": "Total - Age groups of the population - 100% data",
    "34": "Total - Distribution (%) of the population by broad age groups - 100% data",
    "39": "Average age of the population",
    "40": "Median age of the population",
    # Household composition
    "50": "Total - Private households by household size - 100% data",
    "56": "Number of persons in private households",
    "57": "Average household size",
    # Income
    "243": "Median total income of household in 2020 ($)",
    "244": "Median after-tax income of household in 2020 ($)",
    "252": "Average total income of household in 2020 ($)",
    "253": "Average after-tax income of household in 2020 ($)",
    # Tenure
    "1414": "Total - Private households by tenure - 25% sample data",
    "1415": "Owner",
    "1416": "Renter",
    "1417": "Dwelling provided by the local government, First Nation or Indian band",
    # Bedrooms
    "1421": "Total - Occupied private dwellings by number of bedrooms - 25% sample data",
    "1422": "No bedrooms",
    "1423": "1 bedroom",
    "1424": "2 bedrooms",
    "1425": "3 bedrooms",
    "1426": "4 or more bedrooms",
    # Housing suitability
    "1437": "Total - Private households by housing suitability - 25% sample data",
    "1438": "Suitable",
    "1439": "Not suitable",
    # Dwelling condition
    "1449": "Total - Occupied private dwellings by dwelling condition - 25% sample data",
    "1450": "Only regular maintenance and minor repairs needed",
    "1451": "Major repairs needed",
    # Shelter-cost-to-income ratio
    "1465": "Total - Owner and tenant households with household total income greater than "
            "zero, in non-farm, non-reserve private dwellings by shelter-cost-to-income "
            "ratio - 25% sample data",
    "1466": "Spending less than 30% of income on shelter costs",
    "1467": "Spending 30% or more of income on shelter costs",
    "1468": "30% to less than 100%",
    # Housing indicators / core housing need
    "1469": "Total - Occupied private dwellings by housing indicators - 25% sample data",
    "1470": "Total - Households 'spending 30% or more of income on shelter costs' or "
            "'not suitable' or 'major repairs needed'",
    "1478": "Acceptable housing",
    "1479": "Total - Owner and tenant households with household total income greater than "
            "zero and shelter-cost-to-income ratio less than 100%, in non-farm, "
            "non-reserve private dwellings - 25% sample data",
    "1480": "In core need",
    "1481": "Not in core need",
    # Owner households detail
    "1482": "Total - Owner households in non-farm, non-reserve private dwellings - 25% "
            "sample data",
    "1483": "% of owner households with a mortgage",
    "1484": "% of owner households spending 30% or more of its income on shelter costs",
    "1485": "% in core housing need",
    "1486": "Median monthly shelter costs for owned dwellings ($)",
    "1487": "Average monthly shelter costs for owned dwellings ($)",
    "1488": "Median value of dwellings ($)",
    "1489": "Average value of dwellings ($)",
    # Tenant households detail
    "1490": "Total - Tenant households in non-farm, non-reserve private dwellings - 25% "
            "sample data",
    "1491": "% of tenant households in subsidized housing",
    "1492": "% of tenant households spending 30% or more of its income on shelter costs",
    "1493": "% in core housing need",
    "1494": "Median monthly shelter costs for rented dwellings ($)",
    "1495": "Average monthly shelter costs for rented dwellings ($)",
    # Dwellings provided by local government/First Nation/Indian band
    "1496": "Total - Households living in a dwelling provided by the local government, "
            "First Nation or Indian band in non-farm private dwellings - 25% sample data",
    "1497": "% of households living in a dwelling provided by the local government, First "
            "Nation or Indian band spending more than 30% on shelter costs",
    "1498": "Median monthly shelter costs for dwellings provided by local government, "
            "First Nation or Indian band ($)",
    "1499": "Average monthly shelter costs for dwellings provided by local government, "
            "First Nation or Indian band ($)",
}


def extract_windsor_characteristics(
    source_csv: Path = SOURCE_CSV,
    output_csv: Path = OUTPUT_CSV,
    geo_filter: str = GEO_FILTER,
    characteristic_ids: dict[str, str] = CHARACTERISTIC_IDS,
    chunksize: int = CHUNK_SIZE,
) -> dict:
    """Stream `source_csv` in chunks, keep rows for `geo_filter` whose
    CHARACTERISTIC_ID is in `characteristic_ids`, and write them to `output_csv`.

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

    wanted_ids = set(characteristic_ids)
    total_source_rows = 0
    total_windsor_rows = 0
    total_written_rows = 0
    characteristic_ids_seen: set[str] = set()
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

        windsor = chunk[chunk["GEO_NAME"] == geo_filter]
        if windsor.empty:
            continue
        total_windsor_rows += len(windsor)
        dguid_values_seen.update(windsor["DGUID"].dropna().unique())

        match = windsor[windsor["CHARACTERISTIC_ID"].isin(wanted_ids)]
        if match.empty:
            continue

        characteristic_ids_seen.update(match["CHARACTERISTIC_ID"].unique())
        total_written_rows += len(match)

        match.to_csv(
            output_csv,
            mode="a",
            header=not header_written,
            index=False,
            encoding="utf-8",
        )
        header_written = True

    missing_ids = wanted_ids - characteristic_ids_seen

    return {
        "source_csv": str(source_csv),
        "output_csv": str(output_csv),
        "geo_filter": geo_filter,
        "total_source_rows": total_source_rows,
        "total_windsor_rows": total_windsor_rows,
        "total_written_rows": total_written_rows,
        "source_columns": source_columns,
        "characteristics_requested": len(wanted_ids),
        "characteristics_matched": len(characteristic_ids_seen),
        "characteristics_missing": sorted(missing_ids, key=int),
        "dguid_values_for_filter": sorted(dguid_values_seen),
    }


if __name__ == "__main__":
    stats = extract_windsor_characteristics()
    print("Extraction complete.")
    for key, value in stats.items():
        print(f"  {key}: {value}")
