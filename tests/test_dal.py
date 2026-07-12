"""Tests for dal/dal.py — DAL public class."""

from __future__ import annotations

import pandas as pd
import pytest

from dal import (
    DAL,
    DALConfig,
    DALConfigError,
    DALHandoff,
    DALHandoffError,
    DALVersionError,
)
from dal.adapters.in_memory import InMemorySource


@pytest.fixture
def long_stream() -> pd.DataFrame:
    n = 30
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n)],
            "high": [105.0 + i for i in range(n)],
            "low": [98.0 + i for i in range(n)],
            "close": [103.0 + i for i in range(n)],
            "volume": [1000.0 + i for i in range(n)],
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
    )


@pytest.fixture
def kraken(long_stream: pd.DataFrame) -> InMemorySource:
    return InMemorySource("kraken", {"BTC-USD": long_stream})


@pytest.fixture
def yahoo(long_stream: pd.DataFrame) -> InMemorySource:
    return InMemorySource("yahoo", {"BTC-USD": long_stream})


@pytest.fixture
def dal(kraken: InMemorySource, yahoo: InMemorySource) -> DAL:
    return DAL(DALConfig(), (kraken, yahoo))


class TestRegistry:
    def test_register_two_sources(self, kraken, yahoo) -> None:
        d = DAL(DALConfig(), (kraken, yahoo))
        assert isinstance(d, DAL)

    def test_duplicate_source_id_raises(self, long_stream) -> None:
        a = InMemorySource("kraken", {"BTC-USD": long_stream})
        b = InMemorySource("kraken", {"BTC-USD": long_stream})
        with pytest.raises(DALConfigError, match="Duplicate"):
            DAL(DALConfig(), (a, b))


class TestCertifiedStream:
    def test_happy_path(self, dal: DAL) -> None:
        h = dal.get_certified_stream(
            asset_id="BTC-USD",
            source_preference=["kraken"],
            start="2024-01-01",
            end="2024-01-30",
            calendar="CRYPTO_247",
            dqf_version_target="1.2.0",
        )
        assert isinstance(h, DALHandoff)
        assert h.dqf_status == "PASS"
        assert h.calendar == "CRYPTO_247"
        assert h.aqi == 100.0

    def test_missing_calendar_raises(self, dal: DAL) -> None:
        with pytest.raises(DALConfigError, match="calendar"):
            dal.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=["kraken"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="",
                dqf_version_target="1.2.0",
            )

    def test_missing_dqf_version_target_raises(self, dal: DAL) -> None:
        with pytest.raises(DALConfigError, match="dqf_version_target"):
            dal.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=["kraken"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="CRYPTO_247",
                dqf_version_target="",
            )

    def test_version_too_high_raises(self, dal: DAL) -> None:
        with pytest.raises(DALVersionError):
            dal.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=["kraken"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="CRYPTO_247",
                dqf_version_target="99.0.0",
            )


class TestDiagnosticStream:
    def test_happy_path(self, dal: DAL) -> None:
        h = dal.get_diagnostic_stream(
            asset_id="BTC-USD",
            source_preference=["yahoo"],
            start="2024-01-01",
            end="2024-01-30",
            calendar="CRYPTO_247",
        )
        assert h.dqf_status == "PASS"
        assert h.dqf_version_target == ""

    def test_missing_calendar_raises(self, dal: DAL) -> None:
        with pytest.raises(DALConfigError, match="calendar"):
            dal.get_diagnostic_stream(
                asset_id="BTC-USD",
                source_preference=["yahoo"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="",
            )

    def test_no_dqf_version_target_required(self, dal: DAL) -> None:
        h = dal.get_diagnostic_stream(
            asset_id="BTC-USD",
            source_preference=["yahoo"],
            start="2024-01-01",
            end="2024-01-30",
            calendar="CRYPTO_247",
        )
        assert h.dqf_version_target == ""


class TestSourceResolution:
    def test_unknown_source_raises(self, dal: DAL) -> None:
        with pytest.raises(DALConfigError, match="not registered"):
            dal.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=["coinbase"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="CRYPTO_247",
                dqf_version_target="1.2.0",
            )

    def test_empty_preference_raises(self, dal: DAL) -> None:
        with pytest.raises(DALConfigError, match="empty"):
            dal.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=[],
                start="2024-01-01",
                end="2024-01-30",
                calendar="CRYPTO_247",
                dqf_version_target="1.2.0",
            )

    def test_preference_order_respected(self, long_stream: pd.DataFrame) -> None:
        # Both sources work — first in preference list wins
        a = InMemorySource("kraken", {"BTC-USD": long_stream})
        b = InMemorySource("yahoo", {"BTC-USD": long_stream})
        d = DAL(DALConfig(), (a, b))
        h = d.get_certified_stream(
            asset_id="BTC-USD",
            source_preference=["yahoo", "kraken"],
            start="2024-01-01",
            end="2024-01-30",
            calendar="CRYPTO_247",
            dqf_version_target="1.2.0",
        )
        assert h.source_manifest[0]["source_id"] == "yahoo"
        assert h.source_manifest[0]["fallback"] is False

    def test_fallback_through_dal(self, long_stream: pd.DataFrame) -> None:
        primary = InMemorySource(
            "kraken", {"BTC-USD": long_stream}, permanent_failure=True
        )
        backup = InMemorySource("yahoo", {"BTC-USD": long_stream})
        d = DAL(DALConfig(), (primary, backup))
        h = d.get_certified_stream(
            asset_id="BTC-USD",
            source_preference=["kraken", "yahoo"],
            start="2024-01-01",
            end="2024-01-30",
            calendar="CRYPTO_247",
            dqf_version_target="1.2.0",
        )
        # primary failed (3 retries + fallback = 0.35) → AQI 65
        assert h.aqi == pytest.approx(65.0)
        assert len(h.source_manifest) == 2

    def test_all_sources_fail_propagates(self, long_stream: pd.DataFrame) -> None:
        a = InMemorySource("kraken", {"BTC-USD": long_stream}, permanent_failure=True)
        b = InMemorySource("yahoo", {"BTC-USD": long_stream}, permanent_failure=True)
        d = DAL(DALConfig(), (a, b))
        with pytest.raises(DALHandoffError) as exc:
            d.get_certified_stream(
                asset_id="BTC-USD",
                source_preference=["kraken", "yahoo"],
                start="2024-01-01",
                end="2024-01-30",
                calendar="CRYPTO_247",
                dqf_version_target="1.2.0",
            )
        assert exc.value.reason == "ALL_SOURCES_FAILED"


class TestPublicAPIExports:
    def test_all_exports_importable(self) -> None:
        from dal import DAL as _DAL
        from dal import DALConfig as _Config
        from dal import DALHandoff as _Handoff
        from dal import __version__

        assert _DAL is not None
        assert _Config is not None
        assert _Handoff is not None
        assert __version__
