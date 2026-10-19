# Legacy pipeline (superseded — do not use)

These files belong to the **earlier** ETL pipeline. They were moved here unchanged from `etl/`
(with `git mv`, so `git log --follow` still shows their history) when the cleaning pipeline was
rebaselined on the five official raw files.

| File | What it did |
|---|---|
| `extract_windsor_shelter_cost.py` | Filtered Windsor rows out of the 1.28 GB wide shelter-cost file `data/raw/shelter_cost/98100252.csv` |
| `reshape_shelter_cost_long.py` | Reshaped that wide staging file to long format |
| `run_affordability_etl.py` | Ran the two shelter-cost scripts above in sequence |
| `extract_windsor_census_profile.py` | Read an extracted `98-401-X2021002_English_CSV_data.csv` and kept 60 curated characteristics |
| `reshape_census_profile_long.py` | Reshaped that census output to long format |
| `extract_windsor_rms.py` | Parsed 9 sheets of the Windsor RMS workbook |
| `extract_rms_canada_comparison.py` | Parsed Table 1.0 for 5 hand-picked centres |
| `extract_cmhc_starts_completions.py` | Read Tables C1/C2 of `quarterly-starts-completions-under-construction-06-26-en.xlsx` (Ontario/Canada) |
| `validate_supply_data.py` | Validated the starts output and rewrote part of `docs/data_quality_report.md` |
| `test_affordability_etl.py` | Unit tests for the old shelter-cost scripts |

## Why they must not be used

- **They expect different raw files or formats** from the ones in `data/raw/` now: the 1.28 GB
  wide shelter-cost file (not the 2,389-row database-loading extract), an unzipped census CSV,
  and a quarterly starts workbook with C1/C2 sheets that isn't in the project.
- **Several write to the same file names as the current pipeline** in `data/staging/`
  (`windsor_shelter_cost.csv`, `windsor_census_profile.csv`, `windsor_rental_market.csv`), in a
  different format. Running them would overwrite the validated cleaned outputs.
- `test_affordability_etl.py` expects the old wide-format `windsor_shelter_cost.csv`. It is
  excluded from pytest (see `pytest.ini`) because it fails against the current file.
- The files were not edited after the move. `reshape_shelter_cost_long.py` (and so
  `test_affordability_etl.py` and `run_affordability_etl.py`) still imports
  `etl/statcan_profiling.py`, so it would need `etl/` on the import path.

## Current pipeline

Use the pipeline described in the main [README](../README.md#data-cleaning-pipeline):
`etl/run_cleaning_pipeline.py`, `etl/validate_cleaned_data.py`, the `etl/clean_*.py` modules,
and the tests in `tests/`.
