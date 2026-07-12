"""Tests for dal/exceptions.py — exception hierarchy per spec §8."""

from __future__ import annotations

import pytest

from dal.exceptions import (
    DALConfigError,
    DALError,
    DALHandoffError,
    DALVersionError,
)


class TestHierarchy:
    def test_dal_error_is_exception(self) -> None:
        assert issubclass(DALError, Exception)

    def test_config_error_inherits_dal_error(self) -> None:
        assert issubclass(DALConfigError, DALError)

    def test_version_error_inherits_dal_error(self) -> None:
        assert issubclass(DALVersionError, DALError)

    def test_handoff_error_inherits_dal_error(self) -> None:
        assert issubclass(DALHandoffError, DALError)

    def test_subclass_caught_as_base(self) -> None:
        with pytest.raises(DALError):
            raise DALConfigError("missing calendar")


class TestDALConfigError:
    def test_message_preserved(self) -> None:
        err = DALConfigError("calendar required in CERTIFICATION mode")
        assert "calendar" in str(err)


class TestDALVersionError:
    def test_carries_versions(self) -> None:
        err = DALVersionError(
            "installed mif-dqf 1.1.0 < required 1.2.0",
            installed_version="1.1.0",
            required_version="1.2.0",
        )
        assert err.installed_version == "1.1.0"
        assert err.required_version == "1.2.0"
        assert "1.2.0" in str(err)

    def test_versions_are_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            DALVersionError("msg", "1.1.0", "1.2.0")  # type: ignore[misc]


class TestDALHandoffError:
    def test_dqf_void_reason(self) -> None:
        err = DALHandoffError(
            "DQF gate VOID for PAXG-USD 2020–2024",
            reason="DQF_VOID",
            dqf_report=object(),
        )
        assert err.reason == "DQF_VOID"
        assert err.dqf_report is not None
        assert err.source_failures is None

    def test_dqf_unexpected_status_reason(self) -> None:
        err = DALHandoffError(
            "DQF returned an unrecognised status",
            reason="DQF_UNEXPECTED_STATUS",
            dqf_report=object(),
        )
        assert err.reason == "DQF_UNEXPECTED_STATUS"
        assert err.dqf_report is not None

    def test_dqf_fail_reason_rejected(self) -> None:
        # DQF has no FAIL status; DAL never raises with this reason.
        with pytest.raises(ValueError, match="reason"):
            DALHandoffError("oops", reason="DQF_FAIL")

    def test_all_sources_failed_reason(self) -> None:
        failures = [
            {"source_id": "kraken", "error": "timeout"},
            {"source_id": "yahoo", "error": "404"},
        ]
        err = DALHandoffError(
            "All sources failed for PAXG-USD",
            reason="ALL_SOURCES_FAILED",
            source_failures=failures,
        )
        assert err.reason == "ALL_SOURCES_FAILED"
        assert err.source_failures == failures
        assert err.dqf_report is None

    def test_invalid_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            DALHandoffError("oops", reason="UNKNOWN")

    def test_reason_is_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            DALHandoffError("msg", "DQF_VOID")  # type: ignore[misc]

    def test_optional_fields_default_none(self) -> None:
        err = DALHandoffError("msg", reason="DQF_VOID")
        assert err.dqf_report is None
        assert err.source_failures is None

    def test_raise_and_catch(self) -> None:
        with pytest.raises(DALHandoffError) as excinfo:
            raise DALHandoffError("test", reason="DQF_VOID")
        assert excinfo.value.reason == "DQF_VOID"
