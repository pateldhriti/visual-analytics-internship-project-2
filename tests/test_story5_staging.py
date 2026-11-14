"""
Tests for the Story 5 staging layer (etl/story5_common.py, build_cma_geography_map.py,
clean_cma_*.py, run_story5_staging.py, validate_story5_staging.py).

Rebuilds go to tmp_path only; data/raw/ and the existing staging files are never written.

    .venv\\Scripts\\python.exe -m pytest tests\\test_story5_staging.py -v
"""

import math
import shutil

import pandas as pd
import pytest

import build_cma_geography_map as gmap
import clean_cma_housing_profile as prof
import clean_cma_rental_history as hist
import clean_cma_rental_universe as univ
import validate_story5_staging as v
from cleaning_common import STAGING_DIR
from story5_common import GEOGRAPHY_MAP_PATH, OUTPUTS, lookup


class TestUnits:
    def test_unmapped_centre_is_rejected_not_guessed(self):
        geo = {"Windsor CMA": {"cma_dguid": "2021S0503559"}}
        assert lookup(geo, "Windsor CMA")["cma_dguid"] == "2021S0503559"
        with pytest.raises(ValueError, match="no fuzzy"):
            lookup(geo, "Windsor  CMA")
        with pytest.raises(ValueError):
            lookup(geo, "windsor CMA")

    def test_markers_become_null_never_zero(self):
        val, status = hist.parse_value("**")
        assert math.isnan(val) and status == "suppressed"
        val, status = hist.parse_value("++")
        assert math.isnan(val) and status == "change_not_significant"
        assert hist.parse_value("1,154") == (1154.0, "published")
        with pytest.raises(ValueError):
            hist.parse_value(None)

    def test_trend_and_reliability_parsing(self):
        assert hist.parse_trend("−") == "not_significant"   # 2019 edition glyph U+2212
        assert hist.parse_trend("↑") == "significant_increase"
        with pytest.raises(ValueError):
            hist.parse_reliability("e")


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    out = tmp_path_factory.mktemp("story5")
    map_path = out / "cma_geography_map.csv"
    gmap.write(path=map_path)
    hist.clean(out_dir=out, map_path=map_path)
    prof.clean(out_dir=out)
    univ.clean(out_dir=out, map_path=map_path)
    return out, map_path


class TestRebuild:
    def test_rebuild_is_byte_identical_to_committed_outputs(self, rebuilt):
        out, map_path = rebuilt
        assert map_path.read_bytes() == GEOGRAPHY_MAP_PATH.read_bytes()
        for name in OUTPUTS.values():
            assert (out / name).read_bytes() == (STAGING_DIR / name).read_bytes(), name

    def test_row_counts(self, rebuilt):
        out, map_path = rebuilt
        assert len(pd.read_csv(map_path)) == 43
        assert len(pd.read_csv(out / OUTPUTS["rental_history"])) == 1248
        assert len(pd.read_csv(out / OUTPUTS["housing_profile"])) == 817
        assert len(pd.read_csv(out / OUTPUTS["rental_universe"])) == 36


class TestValidation:
    def test_every_check_passes_on_repo_outputs(self):
        checks = v.run_checks(include_regression=False)
        failed = [f"[{c.area}] {c.name} -- {c.detail}" for c in checks if not c.passed]
        assert not failed, "\n".join(failed)

    def test_validator_detects_tampering(self, tmp_path):
        for name in list(v.FILES.values()) + ["windsor_rental_market_history.csv", "canada_rental_market_comparison.csv"]:
            shutil.copy(STAGING_DIR / name, tmp_path / name)
        h = pd.read_csv(tmp_path / v.FILES["history"], dtype={"cma_dguid": str, "raw_value": str, "reliability_code": str})
        sup = h.index[h.value_status == "suppressed"][0]
        h.loc[sup, "value"] = 0.0                                    # zero-filled suppression
        win = h.index[(h.cma_dguid == v.WINDSOR) & (h.year == 2021) & (h.metric == "average_rent_2br")][0]
        h.loc[win, "value"] = 1155.0                                 # altered Windsor value
        h.loc[h.year == 2022, "is_primary_series"] = True            # two primaries in 2022
        h.to_csv(tmp_path / v.FILES["history"], index=False)
        u = pd.read_csv(tmp_path / v.FILES["universe"], dtype={"cma_dguid": str})
        u = u[u.cma_dguid != v.WINDSOR]                              # drop Windsor universe
        u.to_csv(tmp_path / v.FILES["universe"], index=False)
        failed = {c.name for c in v.run_checks(staging_dir=tmp_path, include_regression=False) if not c.passed}
        assert "'**' -> NULL+suppressed, '++' -> NULL+change_not_significant; NULL iff not published; never zero-filled" in failed
        assert "exactly one primary row per CMA x year x metric" in failed
        assert any(n.startswith("Windsor vacancy/2BR rent/turnover reconcile") for n in failed)
        assert any(n.startswith("every row re-read independently") for n in failed)
        assert "Windsor Oct-2021 universe = 16,314" in failed
