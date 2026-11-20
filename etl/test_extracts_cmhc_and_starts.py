r"""Tests for the extracts that had none: the Windsor CMHC workbook
(etl/extract_windsor_rms.py), the CMHC Canada comparison
(etl/extract_rms_canada_comparison.py) and Windsor's monthly starts and
completions (etl/extract_windsor_starts_completions.py).

Each test builds a small worksheet or table in memory with the layout of the
real file, so no data file and no database are needed (they run in CI).

Run: .venv\Scripts\python.exe -m pytest etl\test_extracts_cmhc_and_starts.py
"""

import openpyxl
import pandas as pd
import pytest

import extract_rms_canada_comparison as canada
import extract_windsor_rms as rms
import extract_windsor_starts_completions as starts


# --- Windsor CMHC workbook ----------------------------------------------------

def _zone_sheet(group_width: int, values) -> openpyxl.worksheet.worksheet.Worksheet:
    """A sheet with the Windsor workbook's grid: zone labels in column A from
    row 8, then one group of `group_width` columns per unit size, filled by
    values(zone_index, unit_index) -> list of cells for that group."""
    ws = openpyxl.Workbook().active
    for z, zone in enumerate(rms.ZONE_LABELS):
        row = rms.FIRST_ZONE_ROW + z
        ws.cell(row=row, column=1, value=zone)
        for b in range(len(rms.BEDROOM_TYPES)):
            for i, cell in enumerate(values(z, b)):
                ws.cell(row=row, column=2 + b * group_width + i, value=cell)
    return ws


def test_rate_sheet_reads_both_surveys_with_reliability_and_trend():
    ws = _zone_sheet(5, lambda z, b: [f"{z}.{b}", "a", f"{z}.{b}5", "b", "↑"])
    rows = rms.parse_rate_sheet(ws, "vacancy_rate", "Apartment", has_yoy=True)
    assert len(rows) == len(rms.ZONE_LABELS) * len(rms.BEDROOM_TYPES) * 2
    cma_2br = [r for r in rows if r["zone"] == "Windsor CMA" and r["bedroom_type"] == "2 Bedroom"]
    by_period = {r["period_label"]: r for r in cma_2br}
    assert by_period["Oct-24"]["value"] == "8.2" and by_period["Oct-24"]["reliability_letter"] == "a"
    assert by_period["Oct-25"]["value"] == "8.25" and by_period["Oct-25"]["yoy_trend"] == "↑"
    assert by_period["Oct-24"]["yoy_trend"] is None  # the trend belongs to the latest survey
    assert {r["dwelling_type"] for r in rows} == {"Apartment"}


def test_rent_sheet_groups_are_four_columns_wide():
    # Rent tables have no trend column: reading them 5 wide would take the
    # next unit size's Oct-24 rent as this one's Oct-25 rent.
    ws = _zone_sheet(4, lambda z, b: [1000 + b, "a", 1100 + b, "a"])
    rows = rms.parse_rate_sheet(ws, "average_rent", "Combined", has_yoy=False)
    studio = {r["period_label"]: r["value"] for r in rows
              if r["zone"] == "Windsor CMA" and r["bedroom_type"] == "Studio"}
    one_bed = {r["period_label"]: r["value"] for r in rows
               if r["zone"] == "Windsor CMA" and r["bedroom_type"] == "1 Bedroom"}
    assert studio == {"Oct-24": 1000, "Oct-25": 1100}
    assert one_bed == {"Oct-24": 1001, "Oct-25": 1101}


def test_universe_sheet_has_no_reliability_letters():
    ws = _zone_sheet(2, lambda z, b: [100 * (z + 1) + b, 100 * (z + 1) + b + 10])
    rows = rms.parse_universe_sheet(ws, "universe", "Apartment")
    zone1_total = {r["period_label"]: r["value"] for r in rows
                   if r["zone"] == "Zone 1 - Centre" and r["bedroom_type"] == "Total"}
    assert zone1_total == {"Oct-24": 104, "Oct-25": 114}
    assert all(r["reliability_letter"] is None for r in rows)


def test_vacant_occupied_sheet_keeps_the_dwelling_scope_it_is_given():
    ws = _zone_sheet(5, lambda z, b: [1600 + b, "b", 1400 + b, "a", "Y"])
    rows = rms.parse_vacant_occupied_sheet(ws, "Apartment")
    assert {r["dwelling_type"] for r in rows} == {"Apartment"}
    two_bed = {r["metric_type"]: r["value"] for r in rows
               if r["zone"] == "Windsor CMA" and r["bedroom_type"] == "2 Bedroom"}
    assert two_bed == {"rent_vacant_units": 1602, "rent_occupied_units": 1402}
    assert rms.parse_vacant_occupied_sheet(ws)[0]["dwelling_type"] == "Combined"  # the default


@pytest.mark.parametrize("raw, expected", [("**", None), (None, None), ("3,009", "3009"), (4.2, 4.2)])
def test_clean_value_maps_suppressed_cells_and_thousands_separators(raw, expected):
    assert rms.clean_value(raw) == expected


# --- CMHC Canada comparison ---------------------------------------------------

def _canada_sheet(centres) -> openpyxl.worksheet.worksheet.Worksheet:
    ws = openpyxl.Workbook().active
    ws.title = "Table 1.0"
    ws.cell(row=1, column=1, value="Centre")
    for i, centre in enumerate(centres, start=3):
        ws.cell(row=i, column=1, value=centre)
        for col, value in {2: 3.3, 3: "b", 4: 3.7, 5: "b", 6: "-", 7: 11.8, 9: 12.2, 12: 1387, 14: 1454,
                           16: 5.4, 18: 3.6}.items():
            ws.cell(row=i, column=col, value=value)
    return ws


def test_canada_finds_every_comparison_centre_or_says_which_is_missing():
    ws = _canada_sheet(canada.CENTRES)
    assert set(canada.find_centre_rows(ws)) == set(canada.CENTRES)
    with pytest.raises(ValueError, match="Windsor CMA"):
        canada.find_centre_rows(_canada_sheet(canada.CENTRES[1:]))


def test_canada_row_reads_vacancy_turnover_rent_and_rent_change_for_both_surveys():
    ws = _canada_sheet(canada.CENTRES)
    r = canada.find_centre_rows(ws)["Windsor CMA"]
    got = {(x["metric_type"], x["period_label"]): x["value"] for x in canada.parse_row(ws, r, "Windsor CMA")}
    assert got[("vacancy_rate", "Oct-25")] == 3.7
    assert got[("turnover_rate", "Oct-24")] == 11.8
    assert got[("average_rent", "Oct-25")] == 1454
    assert got[("pct_change_rent", "Oct-25")] == 3.6


# --- Windsor monthly starts and completions ------------------------------------

def _statcan(rows):
    return pd.DataFrame(rows, columns=["REF_DATE", "DGUID", "Housing estimates", "Type of unit", "VALUE", "STATUS"])


def test_starts_reshape_keeps_2016_onward_and_uses_the_workbook_vocabulary():
    out = starts.reshape(_statcan([
        ("2015-12", "2011S0503559", "Housing starts", "Total units", "90", None),
        ("2016-01", "2011S0503559", "Housing starts", "Total units", "100", None),
        ("2026-09", "2011S0503559", "Housing completions", "Apartment and other unit types", "148", ".."),
    ]))
    assert list(out["ref_month"]) == ["2016-01", "2026-09"]  # before FIRST_YEAR dropped
    assert list(out["activity"]) == ["Starts", "Completions"]
    assert list(out["dwelling_type"]) == ["Total", "Apartment and Other"]
    assert list(out["period_month"]) == [1, 9] and list(out["units"]) == [100, 148]


def test_starts_reshape_fails_loudly_on_a_renamed_category():
    with pytest.raises(ValueError, match="Unmapped labels"):
        starts.reshape(_statcan([("2026-01", "x", "Housing starts", "Townhouse units", "5", None)]))
