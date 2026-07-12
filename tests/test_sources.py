"""Tests for dal/core/sources.py — resolve_and_fetch (S1+S2+AQI)."""

from __future__ import annotations

import pandas as pd
import pytest

from dal.adapters.in_memory import InMemorySource
from dal.core.config import DALConfig
from dal.core.sources import resolve_and_fetch
from dal.exceptions import DALHandoffError
from dal.interfaces.source import FetchRequest


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
def request_30d() -> FetchRequest:
    return FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")


@pytest.fixture
def cfg() -> DALConfig:
    return DALConfig()


class TestHappyPath:
    def test_first_source_full_range_aqi_100(
        self, long_stream, request_30d, cfg
    ) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        res = resolve_and_fetch(request=request_30d, sources=(src,), config=cfg)
        assert res.coverage == "FULL"
        assert res.truncated_days == 0
        assert res.aqi == 100.0
        assert len(res.source_manifest) == 1
        assert res.source_manifest[0]["status"] == "success"
        assert res.source_manifest[0]["fallback"] is False
        assert res.source_manifest[0]["source_id"] == "kraken"


class TestRetry:
    def test_one_retry_then_success_aqi_95(self, long_stream, request_30d, cfg) -> None:
        src = InMemorySource("flaky", {"BTC-USD": long_stream}, fail_attempts=1)
        res = resolve_and_fetch(
            request=request_30d, sources=(src,), config=cfg, max_retries=3
        )
        assert res.coverage == "FULL"
        # 1 retry × 0.05 = 0.05 → AQI 95
        assert res.aqi == pytest.approx(95.0)

    def test_three_retries_then_success_aqi_85(
        self, long_stream, request_30d, cfg
    ) -> None:
        src = InMemorySource("flaky", {"BTC-USD": long_stream}, fail_attempts=3)
        res = resolve_and_fetch(
            request=request_30d, sources=(src,), config=cfg, max_retries=3
        )
        # 3 retries × 0.05 = 0.15 → AQI 85
        assert res.aqi == pytest.approx(85.0)


class TestFallback:
    def test_first_source_fails_second_succeeds(
        self, long_stream, request_30d, cfg
    ) -> None:
        primary = InMemorySource(
            "kraken", {"BTC-USD": long_stream}, permanent_failure=True
        )
        backup = InMemorySource("yahoo", {"BTC-USD": long_stream})
        res = resolve_and_fetch(
            request=request_30d, sources=(primary, backup), config=cfg
        )
        # primary: 3 retries (0.15) + fallback (0.20) = 0.35
        # backup: success first try = 0
        # AQI = 100 × (1 - 0.35) = 65
        assert res.aqi == pytest.approx(65.0)
        assert len(res.source_manifest) == 2
        assert res.source_manifest[0]["status"] == "failed"
        assert res.source_manifest[0]["fallback"] is False
        assert res.source_manifest[1]["status"] == "success"
        assert res.source_manifest[1]["fallback"] is True

    def test_all_sources_fail_raises(self, long_stream, request_30d, cfg) -> None:
        s1 = InMemorySource("kraken", {"BTC-USD": long_stream}, permanent_failure=True)
        s2 = InMemorySource("yahoo", {"BTC-USD": long_stream}, permanent_failure=True)
        with pytest.raises(DALHandoffError) as exc:
            resolve_and_fetch(request=request_30d, sources=(s1, s2), config=cfg)
        assert exc.value.reason == "ALL_SOURCES_FAILED"
        assert len(exc.value.source_failures) == 2

    def test_no_source_supports_asset(self, long_stream, cfg) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        req = FetchRequest("AAPL", "2024-01-01", "2024-01-30")
        with pytest.raises(DALHandoffError) as exc:
            resolve_and_fetch(request=req, sources=(src,), config=cfg)
        assert exc.value.reason == "ALL_SOURCES_FAILED"

    def test_unsupported_sources_filtered_out(
        self, long_stream, request_30d, cfg
    ) -> None:
        only_eth = InMemorySource("kraken", {"ETH-USD": long_stream})
        has_btc = InMemorySource("yahoo", {"BTC-USD": long_stream})
        res = resolve_and_fetch(
            request=request_30d, sources=(only_eth, has_btc), config=cfg
        )
        # only_eth filtered out → has_btc is idx=0, no fallback penalty
        assert res.aqi == 100.0
        assert res.source_manifest[0]["fallback"] is False


class TestCompleteness:
    def test_partial_start_truncated_aqi_90(
        self, long_stream, request_30d, cfg
    ) -> None:
        src = InMemorySource("yahoo", {"BTC-USD": long_stream}, truncate_start_days=3)
        res = resolve_and_fetch(request=request_30d, sources=(src,), config=cfg)
        assert res.coverage == "PARTIAL"
        assert res.truncated_days == 3
        # 1 truncated side × 0.10 = 0.10 → AQI 90
        assert res.aqi == pytest.approx(90.0)
        assert res.source_manifest[0]["status"] == "partial"

    def test_partial_both_sides_aqi_80(self, long_stream, request_30d, cfg) -> None:
        src = InMemorySource(
            "yahoo",
            {"BTC-USD": long_stream},
            truncate_start_days=2,
            truncate_end_days=2,
        )
        res = resolve_and_fetch(request=request_30d, sources=(src,), config=cfg)
        assert res.coverage == "PARTIAL"
        # 2 truncated sides × 0.10 = 0.20 → AQI 80
        assert res.aqi == pytest.approx(80.0)

    def test_degraded_below_80pct_ratio_aqi_70(
        self, long_stream, request_30d, cfg
    ) -> None:
        # Drop 22 days from end → 8 rows / 30 requested = 26% delivered
        # → DEGRADED
        src = InMemorySource("yahoo", {"BTC-USD": long_stream}, truncate_end_days=22)
        res = resolve_and_fetch(request=request_30d, sources=(src,), config=cfg)
        assert res.coverage == "DEGRADED"
        # DEGRADED penalty = 0.30 → AQI 70
        assert res.aqi == pytest.approx(70.0)

    def test_empty_delivered_is_degraded(self, long_stream, cfg) -> None:
        src = InMemorySource("yahoo", {"BTC-USD": long_stream})
        req = FetchRequest("BTC-USD", "2034-01-01", "2034-01-30")
        res = resolve_and_fetch(request=req, sources=(src,), config=cfg)
        assert res.coverage == "DEGRADED"
        assert res.aqi == pytest.approx(70.0)


class TestAQIFloor:
    def test_aqi_clamped_at_zero(self, long_stream, request_30d, cfg) -> None:
        # Stack penalties: 2 dead sources (3 retries each + fallback each)
        # plus 3rd source DEGRADED.
        # Penalties: 2 × (0.15 + 0.20) + 0.30 = 1.00
        # → 100*(1-1.00) = 0 (floor)
        s1 = InMemorySource("a", {"BTC-USD": long_stream}, permanent_failure=True)
        s2 = InMemorySource("b", {"BTC-USD": long_stream}, permanent_failure=True)
        s3 = InMemorySource("c", {"BTC-USD": long_stream}, truncate_end_days=22)
        res = resolve_and_fetch(request=request_30d, sources=(s1, s2, s3), config=cfg)
        assert res.aqi == 0.0

    def test_aqi_never_negative_extreme(self, long_stream, request_30d, cfg) -> None:
        # Push past 1.0 in penalties.
        s1 = InMemorySource("a", {"BTC-USD": long_stream}, permanent_failure=True)
        s2 = InMemorySource("b", {"BTC-USD": long_stream}, permanent_failure=True)
        s3 = InMemorySource("c", {"BTC-USD": long_stream}, permanent_failure=True)
        s4 = InMemorySource("d", {"BTC-USD": long_stream}, truncate_end_days=22)
        res = resolve_and_fetch(
            request=request_30d, sources=(s1, s2, s3, s4), config=cfg
        )
        assert res.aqi == 0.0


class TestManifestSchema:
    def test_entry_has_all_fields(self, long_stream, request_30d, cfg) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        res = resolve_and_fetch(request=request_30d, sources=(src,), config=cfg)
        entry = res.source_manifest[0]
        expected = {
            "source_id",
            "status",
            "hash",
            "fetched_at",
            "rows",
            "timeframe",
            "fallback",
        }
        assert set(entry.keys()) == expected
