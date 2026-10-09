"""
Short usage example for statcan_profiling.py.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\example_statcan_profiling.py
"""

from statcan_profiling import profile_file

if __name__ == "__main__":
    # Small file: full read, no chunking needed.
    report = profile_file("../data/staging/windsor_shelter_cost.csv")
    print("windsor_shelter_cost.csv --", len(report), "columns profiled\n")

    print(report[["n_rows", "n_null", "n_distinct"]])
    print()

    print("Symbol values found in the 'Symbol' column (suppression/quality flags):")
    print(report.loc["Symbol", "symbols"])
    print()

    tenure_total = report.loc["Tenure (3):Total - Tenure[1]"]
    print(f"Tenure (3):Total - Tenure[1] numeric range: {tenure_total['min']} to {tenure_total['max']}")

    # Large file: same function, just pass chunksize to stream it instead of
    # loading the whole file into memory.
    # report = profile_file("../data/raw/shelter_cost/98100252.csv", chunksize=200_000)
