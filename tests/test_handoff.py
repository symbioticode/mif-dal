"""Tests for dal/core/handoff.py — DALHandoff contract per spec §5."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from dal.core.handoff import DALHandoff


class TestHappyPath:
    def test_valid_kwargs_construct(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.asset_id == "PAXG-USD"
        assert h.coverage == "FULL"
        assert h.dqf_status == "PASS"

    def test_all_fifteen_fields_present(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        h = DALHandoff(**valid_handoff_kwargs)
        expected = {
            "stream",
            "asset_id",
            "calendar",
            "assembly_hash",
            "handoff_timestamp",
            "dal_version",
            "source_manifest",
            "coverage",
            "truncated_days",
            "dqf_status",
            "dqf_mpi",
            "dqf_version",
            "dqf_version_target",
            "dqf_report",
            "aqi",
        }
        assert {f.name for f in dataclasses.fields(h)} == expected


class TestFrozen:
    def test_setattr_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        h = DALHandoff(**valid_handoff_kwargs)
        with pytest.raises(dataclasses.FrozenInstanceError):
            h.asset_id = "BTC-USD"  # type: ignore[misc]

    def test_source_manifest_is_tuple(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        h = DALHandoff(**valid_handoff_kwargs)
        assert isinstance(h.source_manifest, tuple)


class TestStreamContract:
    def test_non_dataframe_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["stream"] = [1, 2, 3]
        with pytest.raises(TypeError, match="DataFrame"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_stream_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["stream"] = pd.DataFrame()
        with pytest.raises(ValueError, match="empty"):
            DALHandoff(**valid_handoff_kwargs)

    def test_missing_column_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["stream"] = valid_handoff_kwargs["stream"].drop(
            columns=["volume"]
        )
        with pytest.raises(ValueError, match="missing OHLCV"):
            DALHandoff(**valid_handoff_kwargs)

    def test_non_float64_column_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        s = valid_handoff_kwargs["stream"].copy()
        s["volume"] = s["volume"].astype("int64")
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="float64"):
            DALHandoff(**valid_handoff_kwargs)

    def test_non_datetime_index_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        s = valid_handoff_kwargs["stream"].reset_index(drop=True)
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="DatetimeIndex"):
            DALHandoff(**valid_handoff_kwargs)

    def test_naive_index_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        s = valid_handoff_kwargs["stream"].copy()
        s.index = s.index.tz_localize(None)
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="timezone-aware"):
            DALHandoff(**valid_handoff_kwargs)

    def test_nan_value_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        s = valid_handoff_kwargs["stream"].copy()
        s.iloc[0, 0] = float("nan")
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="NaN"):
            DALHandoff(**valid_handoff_kwargs)

    def test_unsorted_index_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        s = valid_handoff_kwargs["stream"].iloc[::-1]
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="sorted ascending"):
            DALHandoff(**valid_handoff_kwargs)

    def test_duplicate_index_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        s = valid_handoff_kwargs["stream"]
        s = pd.concat([s, s.iloc[[0]]]).sort_index()
        valid_handoff_kwargs["stream"] = s
        with pytest.raises(ValueError, match="duplicate"):
            DALHandoff(**valid_handoff_kwargs)


class TestIdentity:
    def test_empty_asset_id_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["asset_id"] = ""
        with pytest.raises(ValueError, match="asset_id"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_calendar_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["calendar"] = ""
        with pytest.raises(ValueError, match="calendar"):
            DALHandoff(**valid_handoff_kwargs)


class TestProvenance:
    def test_short_hash_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["assembly_hash"] = "abc123"
        with pytest.raises(ValueError, match="SHA-256"):
            DALHandoff(**valid_handoff_kwargs)

    def test_uppercase_hash_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["assembly_hash"] = "A" * 64
        with pytest.raises(ValueError, match="SHA-256"):
            DALHandoff(**valid_handoff_kwargs)

    def test_naive_handoff_timestamp_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["handoff_timestamp"] = datetime(2024, 1, 1)
        with pytest.raises(ValueError, match="timezone-aware"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_dal_version_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["dal_version"] = ""
        with pytest.raises(ValueError, match="dal_version"):
            DALHandoff(**valid_handoff_kwargs)

    def test_list_source_manifest_raises(
        self,
        valid_handoff_kwargs: dict[str, Any],
        sample_manifest_entry: dict[str, Any],
    ) -> None:
        valid_handoff_kwargs["source_manifest"] = [sample_manifest_entry]
        with pytest.raises(TypeError, match="tuple"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_source_manifest_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["source_manifest"] = ()
        with pytest.raises(ValueError, match="source_manifest"):
            DALHandoff(**valid_handoff_kwargs)


class TestCoverage:
    def test_invalid_coverage_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["coverage"] = "MOSTLY"
        with pytest.raises(ValueError, match="coverage"):
            DALHandoff(**valid_handoff_kwargs)

    def test_negative_truncated_days_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["truncated_days"] = -1
        with pytest.raises(ValueError, match="truncated_days"):
            DALHandoff(**valid_handoff_kwargs)

    def test_full_with_truncated_days_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["coverage"] = "FULL"
        valid_handoff_kwargs["truncated_days"] = 5
        with pytest.raises(ValueError, match="FULL"):
            DALHandoff(**valid_handoff_kwargs)

    def test_partial_with_truncated_days_ok(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["coverage"] = "PARTIAL"
        valid_handoff_kwargs["truncated_days"] = 7
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.coverage == "PARTIAL"
        assert h.truncated_days == 7

    def test_degraded_ok(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["coverage"] = "DEGRADED"
        valid_handoff_kwargs["truncated_days"] = 200
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.coverage == "DEGRADED"


class TestDQF:
    def test_fail_status_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        # D-DAL-005: FAIL/VOID must never reach a handoff — they raise upstream.
        valid_handoff_kwargs["dqf_status"] = "FAIL"
        with pytest.raises(ValueError, match="dqf_status"):
            DALHandoff(**valid_handoff_kwargs)

    def test_void_status_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["dqf_status"] = "VOID"
        with pytest.raises(ValueError, match="dqf_status"):
            DALHandoff(**valid_handoff_kwargs)

    def test_warning_status_ok(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["dqf_status"] = "WARNING"
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.dqf_status == "WARNING"

    def test_mpi_above_100_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["dqf_mpi"] = 101.0
        with pytest.raises(ValueError, match="dqf_mpi"):
            DALHandoff(**valid_handoff_kwargs)

    def test_mpi_negative_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["dqf_mpi"] = -0.1
        with pytest.raises(ValueError, match="dqf_mpi"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_dqf_version_raises(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        valid_handoff_kwargs["dqf_version"] = ""
        with pytest.raises(ValueError, match="dqf_version"):
            DALHandoff(**valid_handoff_kwargs)

    def test_empty_dqf_version_target_allowed_for_diagnostic(
        self, valid_handoff_kwargs: dict[str, Any]
    ) -> None:
        # Spec §2: dqf_version_target is "" in DIAGNOSTIC mode.
        valid_handoff_kwargs["dqf_version_target"] = ""
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.dqf_version_target == ""


class TestAQI:
    def test_aqi_at_zero_ok(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["aqi"] = 0.0
        h = DALHandoff(**valid_handoff_kwargs)
        assert h.aqi == 0.0

    def test_aqi_above_100_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["aqi"] = 100.01
        with pytest.raises(ValueError, match="aqi"):
            DALHandoff(**valid_handoff_kwargs)

    def test_aqi_negative_raises(self, valid_handoff_kwargs: dict[str, Any]) -> None:
        valid_handoff_kwargs["aqi"] = -1.0
        with pytest.raises(ValueError, match="aqi"):
            DALHandoff(**valid_handoff_kwargs)
