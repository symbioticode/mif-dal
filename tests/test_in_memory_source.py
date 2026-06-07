"""Tests for dal/adapters/in_memory.py — InMemorySource."""

from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from dal.adapters.in_memory import InMemorySource
from dal.interfaces.source import FetchRequest, Source, SourceFetchError


@pytest.fixture
def long_stream() -> pd.DataFrame:
    """30-day OHLCV stream for slicing/truncation tests."""
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


class TestProtocolConformance:
    def test_satisfies_source_protocol(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        assert isinstance(src, Source)


class TestSupports:
    def test_known_asset(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        assert src.supports("BTC-USD") is True

    def test_unknown_asset(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        assert src.supports("AAPL") is False


class TestFetchSuccess:
    def test_returns_full_range(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        req = FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")
        result = src.fetch(req)
        assert result.source_id == "kraken"
        assert result.status == "success"
        assert result.rows == 30

    def test_hash_is_sha256_of_parquet(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        req = FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")
        result = src.fetch(req)
        expected = hashlib.sha256(long_stream.to_parquet()).hexdigest()
        assert result.hash == expected
        assert len(result.hash) == 64

    def test_filters_to_requested_range(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        req = FetchRequest("BTC-USD", "2024-01-05", "2024-01-10")
        result = src.fetch(req)
        assert result.rows == 6


class TestFailureSimulation:
    def test_permanent_failure_raises(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("broken", {"BTC-USD": long_stream}, permanent_failure=True)
        with pytest.raises(SourceFetchError) as exc:
            src.fetch(FetchRequest("BTC-USD", "2024-01-01", "2024-01-30"))
        assert exc.value.source_id == "broken"

    def test_transient_then_success(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("flaky", {"BTC-USD": long_stream}, fail_attempts=2)
        req = FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")
        with pytest.raises(SourceFetchError):
            src.fetch(req)
        with pytest.raises(SourceFetchError):
            src.fetch(req)
        result = src.fetch(req)
        assert result.status == "success"

    def test_unknown_asset_raises(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("kraken", {"BTC-USD": long_stream})
        with pytest.raises(SourceFetchError):
            src.fetch(FetchRequest("AAPL", "2024-01-01", "2024-01-30"))


class TestTruncationSimulation:
    def test_truncate_start(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("yahoo", {"BTC-USD": long_stream}, truncate_start_days=5)
        req = FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")
        result = src.fetch(req)
        assert result.rows == 25

    def test_truncate_end(self, long_stream: pd.DataFrame) -> None:
        src = InMemorySource("yahoo", {"BTC-USD": long_stream}, truncate_end_days=10)
        req = FetchRequest("BTC-USD", "2024-01-01", "2024-01-30")
        result = src.fetch(req)
        assert result.rows == 20
