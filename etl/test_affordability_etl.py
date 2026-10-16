"""
Unit tests for the Story 1 affordability ETL (etl/extract_windsor_shelter_cost.py,
etl/reshape_shelter_cost_long.py). No database and no 1.28 GB raw source
required -- tiny synthetic fixtures built from the real column names stand
in for both, except the last test class, which checks the real staging CSV
when it's present (skipped otherwise) so "totals match the raw file" is
checked against the actual file, not just a fixture.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe -m pytest etl\\test_affordability_etl.py -v
"""

from pathlib import Path

import pandas as pd
import pytest

import reshape_shelter_cost_long as reshape_mod
from extract_windsor_shelter_cost import extract_windsor_rows
from reshape_shelter_cost_long import SYMBOL_FLAG_MAP, reshape_long, verify_preserves_original

WINDSOR_GEO = "Windsor (CMA), Ont."
WINDSOR_DGUID = "2021S0503559"


def _wide_row(coordinate: str, total=("1000", None), owner=("700", None), renter=("300", None)) -> dict:
    """One synthetic wide-format row using the real StatCan column names
    reshape_shelter_cost_long.py expects, with per-tenure (value, symbol) pairs."""
    return {
        "REF_DATE": "2021",
        "GEO": WINDSOR_GEO,
        "DGUID": WINDSOR_DGUID,
        reshape_mod.INCOME_COL: "Total - Total income of household",
        reshape_mod.HOUSEHOLD_COL: "Total - Household type including census family structure",
        "household_type_member_id": "1",
        reshape_mod.SUITABILITY_COL: "Total - Housing suitability",
        reshape_mod.DWELLING_COL: "Total - Dwelling condition",
        reshape_mod.STATISTIC_COL: "Number of private households",
        reshape_mod.RATIO_COL: "Total - Shelter-cost-to-income ratio",
        "Coordinate": coordinate,
        "Tenure (3):Total - Tenure[1]": total[0], "Symbol": total[1],
        "Tenure (3):Owner[2]": owner[0], "Symbol.1": owner[1],
        "Tenure (3):Renter[3]": renter[0], "Symbol.2": renter[1],
    }


class TestSymbolHandling:
    def test_value_is_null_where_symbol_present(self):
        source = pd.DataFrame([_wide_row("1.1.1", renter=("..", "x"))])
        long_df = reshape_long(source)
        renter_row = long_df[long_df["tenure"] == "Renter"].iloc[0]
        assert pd.isna(renter_row["value"])
        assert renter_row["symbol"] == "x"

    def test_value_is_preserved_where_no_symbol(self):
        source = pd.DataFrame([_wide_row("1.1.1")])
        long_df = reshape_long(source)
        assert long_df[long_df["tenure"] == "Owner"].iloc[0]["value"] == 700
        assert pd.isna(long_df[long_df["tenure"] == "Owner"].iloc[0]["symbol"])

    @pytest.mark.parametrize("symbol,expected_flag", sorted(SYMBOL_FLAG_MAP.items()))
    def test_each_legend_symbol_maps_to_its_standard_flag(self, symbol, expected_flag):
        source = pd.DataFrame([_wide_row("1.1.1", total=("..", symbol))])
        long_df = reshape_long(source)
        total_row = long_df[long_df["tenure"] == "Total"].iloc[0]
        assert total_row["data_quality_flag"] == expected_flag
        assert pd.isna(total_row["value"])

    def test_no_symbol_means_no_flag(self):
        source = pd.DataFrame([_wide_row("1.1.1")])
        long_df = reshape_long(source)
        assert long_df["data_quality_flag"].isna().all()

    def test_unrecognized_symbol_raises(self):
        source = pd.DataFrame([_wide_row("1.1.1", total=("..", "Q"))])
        with pytest.raises(ValueError, match="Unrecognized StatCan symbol"):
            reshape_long(source)

    def test_standard_column_names_not_raw_statcan_names(self):
        source = pd.DataFrame([_wide_row("1.1.1")])
        long_df = reshape_long(source)
        for clean in ("ref_date", "geo", "dguid", "source_coordinate"):
            assert clean in long_df.columns
        for raw in ("REF_DATE", "GEO", "DGUID", "Coordinate"):
            assert raw not in long_df.columns


class TestRowCounts:
    def test_each_wide_row_becomes_exactly_3_long_rows(self):
        source = pd.DataFrame([_wide_row("1.1.1"), _wide_row("1.1.2"), _wide_row("1.1.3")])
        long_df = reshape_long(source)
        assert len(long_df) == len(source) * 3

    def test_extract_keeps_only_windsor_rows(self, tmp_path: Path):
        source_csv = tmp_path / "raw.csv"
        output_csv = tmp_path / "windsor.csv"
        rows = pd.DataFrame([
            {"GEO": WINDSOR_GEO, "DGUID": WINDSOR_DGUID, "value": "1"},
            {"GEO": WINDSOR_GEO, "DGUID": WINDSOR_DGUID, "value": "2"},
            {"GEO": "Toronto (CMA), Ont.", "DGUID": "2021S0503535", "value": "3"},
            {"GEO": "London (CMA), Ont.", "DGUID": "2021S0503555", "value": "4"},
        ])
        rows.to_csv(source_csv, index=False, encoding="utf-8-sig")

        stats = extract_windsor_rows(source_csv=source_csv, output_csv=output_csv, chunksize=10)

        assert stats["total_source_rows"] == 4
        assert stats["total_written_rows"] == 2
        written = pd.read_csv(output_csv, dtype=str)
        assert len(written) == 2
        assert (written["GEO"] == WINDSOR_GEO).all()


class TestTotalsMatchRawFile:
    def test_reshape_preserves_wide_totals_on_a_fixture(self):
        """Round-trip check on a small, fully-controlled fixture: the long
        table's values must sum back to the wide fixture's own totals, per
        tenure, with zero round-trip mismatches."""
        source = pd.DataFrame([
            _wide_row("1.1.1", total=("1000", None), owner=("700", None), renter=("300", None)),
            _wide_row("1.1.2", total=("2000", None), owner=("1500", None), renter=("..", "x")),
        ])
        long_df = reshape_long(source)
        checks = verify_preserves_original(source, long_df)

        assert checks["cell_count_preserved"]
        assert checks["non_null_value_count_preserved"]
        assert checks["symbol_count_preserved"]
        assert checks["round_trip_mismatches"] == []

        assert long_df[long_df["tenure"] == "Owner"]["value"].sum() == 700 + 1500
        assert long_df[long_df["tenure"] == "Renter"]["value"].sum() == 300  # the 'x' row is NULL, not 0

    @pytest.mark.skipif(
        not reshape_mod.SOURCE_CSV.exists(),
        reason="requires data/staging/windsor_shelter_cost.csv (run etl/extract_windsor_shelter_cost.py first)",
    )
    def test_known_total_matches_the_real_raw_file(self):
        """Confirms against the actual extracted raw data (not a fixture):
        30,240 Windsor rows, and the Owner 30%-or-more shelter-cost-burden
        household count StatCan publishes for Windsor CMA, 2021 -- the same
        value independently confirmed in docs/peer_test_affordability_etl.md."""
        source = reshape_mod.load_source()
        assert len(source) == 30_240

        long_df = reshape_long(source)
        row = long_df[
            (long_df["tenure"] == "Owner")
            & (long_df["household_type"] == "Total - Household type including census family structure")
            & (long_df["income_group"] == "Total - Total income of household")
            & (long_df["housing_suitability"] == "Total - Housing suitability")
            & (long_df["dwelling_condition"] == "Total - Dwelling condition")
            & (long_df["statistic"] == "Number of private households")
            & (long_df["shelter_cost_ratio"] == "Spending 30% or more of income on shelter costs")
        ]
        assert len(row) == 1
        assert row.iloc[0]["value"] == 13_005
