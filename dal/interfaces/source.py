"""Source interface and transfer types for S1 fetch.

Spec: docs/DAL_SPECIFICATION_v1.0.md §S1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class FetchRequest:
    asset_id: str
    start: str  # YYYY-MM-DD (UTC)
    end: str  # YYYY-MM-DD (UTC)
    timeframe: str = "1D"


@dataclass(frozen=True)
class FetchResult:
    data: pd.DataFrame  # raw OHLCV — DAL pipeline computes assembly_hash on this
    source_id: str
    status: str  # "success" | "partial" | "failed"
    rows: int
    fetched_at: datetime
    hash: str  # SHA-256 of raw bytes from THIS source (per-source provenance)
    timeframe: str
    # Adapter cannot know its own rank in the fallback chain;
    # the resolver sets this authoritatively in the source manifest.
    fallback: bool = False


class SourceFetchError(Exception):
    """Raised by an adapter when it cannot deliver data.

    Caught by the resolver — never propagates to DAL callers.
    The resolver wraps aggregated failures in DALHandoffError(ALL_SOURCES_FAILED).
    """

    def __init__(self, message: str, *, source_id: str) -> None:
        super().__init__(message)
        self.source_id = source_id


@runtime_checkable
class Source(Protocol):
    """Structural interface every source adapter must satisfy.

    Implementations need not inherit from this class — duck typing
    via @runtime_checkable is sufficient.
    """

    source_id: str

    def supports(self, asset_id: str) -> bool:
        """Return True if this source can fetch the given asset."""
        ...

    def fetch(self, request: FetchRequest) -> FetchResult:
        """Fetch raw OHLCV data. Raises SourceFetchError on failure."""
        ...
