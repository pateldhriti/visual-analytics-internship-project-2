import sys
from pathlib import Path

import pytest

ETL_DIR = Path(__file__).resolve().parents[1] / "etl"
sys.path.insert(0, str(ETL_DIR))


@pytest.fixture(scope="session")
def cleaned_dir(tmp_path_factory):
    """Run the full cleaning pipeline once, into a temp directory (never into
    data/staging/ or docs/), and hand the directory to every test that needs it."""
    import run_cleaning_pipeline

    out = tmp_path_factory.mktemp("staging")
    run_cleaning_pipeline.run(out_dir=out, report_path=None)
    return out
