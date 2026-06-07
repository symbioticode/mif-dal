"""Tests for dal/interfaces/source.py — Protocol + transfer types."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from dal.interfaces.source import (
    FetchRequest,
    FetchResult,
    Source,
    SourceFetchError,
)


class TestFetchRequest:
    def test_defaults_timeframe(self) -> None:
        req = FetchRequest(asset_id="BTC-USD", start="2024-01-01", end="2024-12-31")
        assert req.timeframe == "1D"

    def test_immutable(self) -> None:
        req = FetchRequest(asset_id="BTC-USD", start="2024-01-01", end="2024-12-31")
        with pytest.raises(Exception):
            req.asset_id = "ETH-USD"  # type: ignore[misc]


class TestFetchResult:
    def test_construct(self, sample_stream: pd.DataFrame) -> None:
        ts = datetime.now(UTC)
        r = FetchResult(
            data=sample_stream,
            source_id="kraken",
            status="success",
            rows=3,
            fetched_at=ts,
            hash="a" * 64,
            timeframe="1D",
        )
        assert r.source_id == "kraken"
        assert r.status == "success"


class TestSourceFetchError:
    def test_carries_source_id(self) -> None:
        err = SourceFetchError("timeout", source_id="yahoo")
        assert err.source_id == "yahoo"
        assert "timeout" in str(err)


class TestSourceProtocol:
    def test_runtime_checkable(self) -> None:
        class FakeSource:
            source_id = "fake"

            def supports(self, asset_id: str) -> bool:
                return True

            def fetch(self, request: FetchRequest) -> FetchResult:  # noqa: ARG002
                raise NotImplementedError

        assert isinstance(FakeSource(), Source)

    def test_missing_method_fails_isinstance(self) -> None:
        class Incomplete:
            source_id = "x"
            # missing supports + fetch

        assert not isinstance(Incomplete(), Source)
