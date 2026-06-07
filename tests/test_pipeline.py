"""Tests for dal/core/pipeline.py — assemble_handoff (S3+S4+S5)."""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from dqf import DQFMode

from dal.core.handoff import DALHandoff
from dal.core.pipeline import assemble_handoff
from dal.exceptions import DALHandoffError, DALVersionError


@pytest.fixture
def void_stream(sample_stream: pd.DataFrame) -> pd.DataFrame:
    """Stream that triggers a DQF CORE failure (negative price)."""
    s = sample_stream.copy()
    s.iloc[0, 0] = -100.0
    return s


@pytest.fixture
def base_kwargs(
    sample_stream: pd.DataFrame, sample_manifest_entry: dict[str, Any]
) -> dict[str, Any]:
    return {
        "raw_stream": sample_stream,
        "asset_id": "PAXG-USD",
        "calendar": "NYSE",
        "dqf_mode": DQFMode.DIAGNOSTIC,
        "dqf_version_target": "",
        "source_manifest": (sample_manifest_entry,),
        "coverage": "FULL",
        "truncated_days": 0,
        "aqi": 100.0,
    }


def _fake_report(status: str, mpi: float = 95.0) -> MagicMock:
    """Build a DQFReport-like mock with a real cleaned_data DataFrame."""
    fake = MagicMock()
    fake.overall_status = status
    fake.purity_index = mpi
    fake.dqf_version = "1.2.0"
    fake.cleaned_data = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [98.0, 99.0],
            "close": [103.0, 104.0],
            "volume": [1000.0, 1100.0],
        },
        index=pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC"),
    )
    return fake


class TestHappyPath:
    def test_certified_returns_handoff_with_pass(
        self, base_kwargs: dict[str, Any]
    ) -> None:
        h = assemble_handoff(**base_kwargs)
        assert isinstance(h, DALHandoff)
        assert h.dqf_status == "PASS"
        assert h.asset_id == "PAXG-USD"
        assert h.calendar == "NYSE"

    def test_handoff_carries_cleaned_data(self, base_kwargs: dict[str, Any]) -> None:
        h = assemble_handoff(**base_kwargs)
        assert h.stream is h.dqf_report.cleaned_data

    def test_dqf_mpi_from_purity_index(self, base_kwargs: dict[str, Any]) -> None:
        h = assemble_handoff(**base_kwargs)
        assert h.dqf_mpi == h.dqf_report.purity_index

    def test_dqf_version_from_report(self, base_kwargs: dict[str, Any]) -> None:
        h = assemble_handoff(**base_kwargs)
        assert h.dqf_version == h.dqf_report.dqf_version

    def test_aqi_passed_through(self, base_kwargs: dict[str, Any]) -> None:
        base_kwargs["aqi"] = 80.0
        h = assemble_handoff(**base_kwargs)
        assert h.aqi == 80.0

    def test_coverage_passed_through(self, base_kwargs: dict[str, Any]) -> None:
        base_kwargs["coverage"] = "PARTIAL"
        base_kwargs["truncated_days"] = 5
        h = assemble_handoff(**base_kwargs)
        assert h.coverage == "PARTIAL"
        assert h.truncated_days == 5


class TestAssemblyHash:
    def test_hash_matches_parquet_sha256(
        self, base_kwargs: dict[str, Any], sample_stream: pd.DataFrame
    ) -> None:
        h = assemble_handoff(**base_kwargs)
        expected = hashlib.sha256(sample_stream.to_parquet()).hexdigest()
        assert h.assembly_hash == expected

    def test_raw_data_hash_passed_to_validator(
        self, base_kwargs: dict[str, Any]
    ) -> None:
        from dal.core import pipeline as p

        with patch.object(p, "DQFValidator") as MockValidator:
            instance = MockValidator.return_value
            instance.validate.return_value = _fake_report("CERTIFIED")
            assemble_handoff(**base_kwargs)
            call = instance.validate.call_args
            expected_hash = hashlib.sha256(
                base_kwargs["raw_stream"].to_parquet()
            ).hexdigest()
            assert call.kwargs["raw_data_hash"] == expected_hash
            assert call.kwargs["calendar"] == "NYSE"


class TestVoidPath:
    def test_void_raises_handoff_error(
        self, base_kwargs: dict[str, Any], void_stream: pd.DataFrame
    ) -> None:
        base_kwargs["raw_stream"] = void_stream
        base_kwargs["dqf_mode"] = DQFMode.CERTIFICATION
        with pytest.raises(DALHandoffError) as exc:
            assemble_handoff(**base_kwargs)
        assert exc.value.reason == "DQF_VOID"
        assert exc.value.dqf_report is not None


class TestUnexpectedStatus:
    def test_unrecognised_status_raises(self, base_kwargs: dict[str, Any]) -> None:
        from dal.core import pipeline as p

        with patch.object(p, "DQFValidator") as MockValidator:
            instance = MockValidator.return_value
            instance.validate.return_value = _fake_report("WEIRD")
            with pytest.raises(DALHandoffError) as exc:
                assemble_handoff(**base_kwargs)
            assert exc.value.reason == "DQF_UNEXPECTED_STATUS"
            assert "WEIRD" in str(exc.value)


class TestWarningPath:
    def test_warning_emits_handoff_with_warning_status(
        self, base_kwargs: dict[str, Any]
    ) -> None:
        from dal.core import pipeline as p

        with patch.object(p, "DQFValidator") as MockValidator:
            instance = MockValidator.return_value
            instance.validate.return_value = _fake_report("WARNING", mpi=70.0)
            h = assemble_handoff(**base_kwargs)
            assert h.dqf_status == "WARNING"
            assert h.dqf_mpi == 70.0


class TestVersionGate:
    def test_target_below_installed_passes(self, base_kwargs: dict[str, Any]) -> None:
        base_kwargs["dqf_version_target"] = "1.0.0"
        h = assemble_handoff(**base_kwargs)
        assert h.dqf_version_target == "1.0.0"

    def test_target_above_installed_raises(self, base_kwargs: dict[str, Any]) -> None:
        base_kwargs["dqf_version_target"] = "99.0.0"
        with pytest.raises(DALVersionError) as exc:
            assemble_handoff(**base_kwargs)
        assert exc.value.required_version == "99.0.0"
        assert exc.value.installed_version  # non-empty

    def test_empty_target_skips_check(self, base_kwargs: dict[str, Any]) -> None:
        base_kwargs["dqf_version_target"] = ""
        h = assemble_handoff(**base_kwargs)
        assert h.dqf_version_target == ""
