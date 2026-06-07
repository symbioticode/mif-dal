"""Deterministic in-memory source adapter for tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pandas as pd

from dal.interfaces.source import FetchRequest, FetchResult, SourceFetchError


class InMemorySource:
    """Test adapter: pre-loaded data, optional failure simulation.

    Args:
        source_id: identifier exposed in source_manifest entries.
        data: mapping asset_id -> raw OHLCV DataFrame.
        fail_attempts: first N fetch() calls raise SourceFetchError;
            subsequent calls succeed. Used to test retry behavior.
        permanent_failure: every fetch() raises (used to test fallback).
        truncate_start_days: drop N rows from the start of returned data
            (simulates a source whose history starts after the request).
        truncate_end_days: drop N rows from the end (simulates source
            ending before the request).
    """

    source_id: str

    def __init__(
        self,
        source_id: str,
        data: dict[str, pd.DataFrame],
        *,
        fail_attempts: int = 0,
        permanent_failure: bool = False,
        truncate_start_days: int = 0,
        truncate_end_days: int = 0,
    ) -> None:
        self.source_id = source_id
        self._data = data
        self._fail_attempts = fail_attempts
        self._permanent_failure = permanent_failure
        self._truncate_start_days = truncate_start_days
        self._truncate_end_days = truncate_end_days
        self._call_count = 0

    def supports(self, asset_id: str) -> bool:
        return asset_id in self._data

    def fetch(self, request: FetchRequest) -> FetchResult:
        self._call_count += 1

        if self._permanent_failure:
            raise SourceFetchError(
                f"{self.source_id} permanent failure for {request.asset_id}",
                source_id=self.source_id,
            )

        if self._call_count <= self._fail_attempts:
            raise SourceFetchError(
                f"{self.source_id} transient failure (attempt " f"{self._call_count})",
                source_id=self.source_id,
            )

        if request.asset_id not in self._data:
            raise SourceFetchError(
                f"{self.source_id} does not have {request.asset_id}",
                source_id=self.source_id,
            )

        df = self._data[request.asset_id]
        start_ts = pd.Timestamp(request.start, tz="UTC")
        end_ts = pd.Timestamp(request.end, tz="UTC")
        df = df.loc[(df.index >= start_ts) & (df.index <= end_ts)]

        if self._truncate_start_days:
            df = df.iloc[self._truncate_start_days :]
        if self._truncate_end_days:
            df = df.iloc[: -self._truncate_end_days]

        raw_bytes = df.to_parquet()
        digest = hashlib.sha256(raw_bytes).hexdigest()

        return FetchResult(
            data=df,
            source_id=self.source_id,
            status="success",
            rows=len(df),
            fetched_at=datetime.now(UTC),
            hash=digest,
            timeframe=request.timeframe,
        )
