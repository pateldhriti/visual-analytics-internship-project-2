"""
Tests for the Windsor historical rental extension
(etl/clean_windsor_rental_history.py, etl/validate_rental_history.py).

Unit tests use tiny in-memory sheets laid out like the CMHC tables.
Integration tests run the cleaner on the real workbooks into the session temp
directory from conftest.py (next to the 2025 pipeline output it reconciles
with) and never write to data/staging/.

    .venv\\Scripts\\python.exe -m pytest tests\\test_rental_history.py -v
"""

import math

import openpyxl
import pandas as pd
import pytest

import clean_windsor_rental_history as hist
import validate_rental_history as vrh


def vacancy_sheet(cma_cells: dict, periods=("Oct-22", "Oct-23"), bedroom="Total"):
    """Minimal Table 1.1.1-like sheet: Total group at V..Z, header row 7, CMA row 8."""
    ws = openpyxl.Workbook().active
    ws.title = "Table 1.1.1"
    ws["A3"] = "1.1.1 Private Apartment Vacancy Rates (%), by Zone and Bedroom Type - Windsor CMA"
    ws["B6"], ws["V6"] = "2 Bedroom", bedroom
    ws["A7"], ws["V7"], ws["X7"] = "Zone", periods[0], periods[1]
    ws["A8"] = "Windsor CMA"
    ws.cell(9, 26)  # real sheets always span the full group width (V..Z)
    for ref, value in cma_cells.items():
        ws[ref] = value
    return ws


class TestReadCell:
    def test_published_value_reliability_and_trend(self):
        ws = vacancy_sheet({"V8": "1.8", "W8": "a", "X8": "2.0", "Y8": "a", "Z8": "↑"})
        cell = hist.read_cell(ws, 2023, "vacancy_rate", "current")
        assert cell["value"] == 2.0 and cell["value_status"] == "published"
        assert cell["reliability_code"] == "a" and cell["yoy_trend"] == "significant_increase"
        assert cell["source_cell"] == "Table 1.1.1!X8" and cell["period_label"] == "Oct-23"

    def test_suppressed_stays_nan_never_zero(self):
        ws = vacancy_sheet({"V8": "1.8", "W8": "a", "X8": "**"})
        cell = hist.read_cell(ws, 2023, "vacancy_rate", "current")
        assert math.isnan(cell["value"]) and cell["value_status"] == "suppressed" and cell["raw_value"] == "**"

    def test_2019_minus_sign_trend_marker(self):
        ws = vacancy_sheet({"X8": 2.9, "Y8": "a", "Z8": "−"})
        assert hist.read_cell(ws, 2023, "vacancy_rate", "current")["yoy_trend"] == "not_significant"

    def test_previous_column_has_no_trend(self):
        ws = vacancy_sheet({"V8": "1.8", "W8": "a", "X8": "2.0", "Z8": "↑"})
        cell = hist.read_cell(ws, 2023, "vacancy_rate", "previous")
        assert cell["value"] == 1.8 and cell["yoy_trend"] is None and cell["period_label"] == "Oct-22"

    def test_unexpected_period_headers_stop_the_run(self):
        ws = vacancy_sheet({"X8": "2.0"}, periods=("Oct-21", "Oct-22"))
        with pytest.raises(ValueError, match="period headers"):
            hist.read_cell(ws, 2023, "vacancy_rate", "current")

    def test_missing_bedroom_group_stops_the_run(self):
        ws = vacancy_sheet({"X8": "2.0"}, bedroom="All")
        with pytest.raises(ValueError, match="bedroom group"):
            hist.read_cell(ws, 2023, "vacancy_rate", "current")

    def test_unknown_marker_stops_the_run(self):
        ws = vacancy_sheet({"X8": "n/a"})
        with pytest.raises(ValueError):
            hist.read_cell(ws, 2023, "vacancy_rate", "current")


@pytest.fixture(scope="session")
def history_dir(cleaned_dir):
    hist.clean(out_dir=cleaned_dir)
    return cleaned_dir


def history(path):
    return pd.read_csv(path / hist.OUTPUT_NAME, keep_default_na=False, na_values=[""], dtype={"raw_value": str})


class TestHistoryOutput:
    def test_every_validation_check_passes(self, history_dir):
        failed = [f"{c.name} -- {c.detail}" for c in vrh.run_checks(staging_dir=history_dir) if not c.passed]
        assert not failed, "\n".join(failed)

    def test_shape_years_and_metrics(self, history_dir):
        df = history(history_dir)
        assert len(df) == 32
        assert sorted(df["year"].unique()) == list(range(2019, 2026))
        assert set(df["metric"]) == {"vacancy_rate", "average_rent", "rental_universe", "turnover_rate"}

    def test_2022_bridge_values(self, history_dir):
        df = history(history_dir)
        rent = df[(df["year"] == 2022) & (df["metric"] == "average_rent")].set_index("geography_basis")["value"]
        assert rent.to_dict() == {"2021_census": 1174.0, "pre_2021_census": 1197.0}

    def test_2025_matches_existing_pipeline(self, history_dir):
        df = history(history_dir)
        row = df[(df["year"] == 2025) & (df["metric"] == "average_rent")]
        assert row["value"].item() == 1454.0 and row["source_workbook"].item() == "data/raw/cmhc/rmr-windsor-2025-en.xlsx"


class TestValidatorCatchesProblems:
    def tampered(self, history_dir, tmp_path, change):
        for name in (hist.OUTPUT_NAME, vrh.EXISTING_RENTAL):
            (tmp_path / name).write_bytes((history_dir / name).read_bytes())
        df = history(tmp_path)
        change(df)
        df.to_csv(tmp_path / hist.OUTPUT_NAME, index=False)
        return {c.name for c in vrh.run_checks(staging_dir=tmp_path) if not c.passed}

    def test_changed_value_fails_reconciliation(self, history_dir, tmp_path):
        def change(df):
            df.loc[(df["year"] == 2020) & (df["metric"] == "vacancy_rate"), "value"] = 9.9
        failed = self.tampered(history_dir, tmp_path, change)
        assert "every row reconciles to its source cell (label, period, bedroom, value)" in failed

    def test_suppressed_turned_into_zero_fails(self, history_dir, tmp_path):
        def change(df):
            mask = (df["year"] == 2021) & (df["metric"] == "turnover_rate")
            df.loc[mask, ["value", "raw_value", "value_status"]] = [0.0, "**", "suppressed"]
        failed = self.tampered(history_dir, tmp_path, change)
        assert "suppression handling: NaN ⇔ suppressed, raw '**', never 0" in failed

    def test_missing_year_and_duplicate_fail(self, history_dir, tmp_path):
        def change(df):
            df.drop(df[df["year"] == 2019].index, inplace=True)
            df.loc[len(df) + 100] = df.iloc[0]
        failed = self.tampered(history_dir, tmp_path, change)
        assert "years are exactly 2019-2025" in failed
        assert "unique at declared grain (year × metric × geography_basis)" in failed
