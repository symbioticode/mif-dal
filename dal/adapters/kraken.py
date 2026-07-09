"""
dal/adapters/kraken.py
 ========================
KrakenAdapter — implementation of Source Protocol for Kraken public API.

Responsibility:
    Fetch raw OHLCV data from Kraken REST API,
    calculate SHA-256 hash of raw bytes, and return a FetchResult.

What this adapter does NOT do:
    - Validate OHLCV physics (→ DQF)
    - Calculate assembly_hash of final stream (→ S3 pipeline)
    - Decide on fallback (→ resolve_and_fetch in sources.py)
    - Certify anything (→ DQF via S4 pipeline)

Documented limitations:
    - Max 720 candles per API call → automatic pagination
    - PAXG available as PAXGUSDT (verify pair availability)
    - Kraken public rate limit: ~1 req/s recommended
    - No auth required for public OHLCV data
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from typing import Any, ClassVar

import pandas as pd
import requests

from dal.interfaces.source import FetchRequest, FetchResult


class KrakenAdapter:
    """
    Kraken adapter for MIF-DAL.

    Implements Source Protocol. Uses Kraken public REST API,
    without authentication, for OHLCV data.

    Usage:
        src = KrakenAdapter()
        req = FetchRequest(
            asset_id="BTC-USD",
            start="2023-01-01",
            end="2024-01-01",
            timeframe="1D",
        )
        result = src.fetch(req)
        # result.hash  = SHA-256 of raw Kraken bytes
        # result.data  = normalized OHLCV DataFrame, UTC DatetimeIndex
    """

    BASE_URL: ClassVar[str] = "https://api.kraken.com/0/public/OHLC"

    # Mapping DAL asset_id → Kraken pair
    # Reference: https://api.kraken.com/0/public/AssetPairs
    SYMBOL_MAP: ClassVar[dict[str, str]] = {
        "BTC-USD": "XBTUSD",
        "ETH-USD": "ETHUSD",
        "PAXG-USD": "PAXGUSD",
        "SOL-USD": "SOLUSD",
        "ADA-USD": "ADAUSD",
        "DOT-USD": "DOTUSD",
        "LINK-USD": "LINKUSD",
        "AVAX-USD": "AVAXUSD",
    }

    # Mapping DAL timeframe → Kraken interval (minutes)
    TIMEFRAME_MAP: ClassVar[dict[str, int]] = {
        "1M": 1,
        "5M": 5,
        "15M": 15,
        "30M": 30,
        "1H": 60,
        "4H": 240,
        "1D": 1440,
        "1W": 10080,
    }

    # Kraken returns max 720 candles per call
    MAX_CANDLES_PER_CALL: ClassVar[int] = 720

    def __init__(
        self,
        request_timeout: int = 30,
        rate_limit_delay: float = 1.0,
    ) -> None:
        """
        Args:
            request_timeout: Seconds before HTTP call timeout.
            rate_limit_delay: Seconds between calls (polite rate limiting).
        """
        self._timeout = request_timeout
        self._rate_limit = rate_limit_delay
        self._last_request_at: float = 0.0

    # ── Source Protocol ──────────────────────────────────────────────────────

    @property
    def source_id(self) -> str:
        return "kraken"

    def supports(self, asset_id: str) -> bool:
        """Return True if asset is available on Kraken."""
        return asset_id in self.SYMBOL_MAP

    def fetch(self, request: FetchRequest) -> FetchResult:
        """
        Fetch OHLCV data from Kraken for requested asset and period.

        Handles pagination automatically if period exceeds 720 candles.

        Returns:
            FetchResult with SHA-256 hash of concatenated raw bytes
            from all calls.

        Raises:
            ValueError: If asset_id or timeframe not supported.
            requests.RequestException: If Kraken API is unreachable.
            RuntimeError: If API returns business error.
        """
        fetched_at = datetime.now(tz=UTC)

        if not self.supports(request.asset_id):
            return FetchResult(
                data=pd.DataFrame(),
                hash="",
                status="failed",
                source_id=self.source_id,
                fetched_at=fetched_at,
                rows=0,
                timeframe=request.timeframe,
                fallback=False,
            )

        if request.timeframe not in self.TIMEFRAME_MAP:
            return FetchResult(
                data=pd.DataFrame(),
                hash="",
                status="failed",
                source_id=self.source_id,
                fetched_at=fetched_at,
                rows=0,
                timeframe=request.timeframe,
                fallback=False,
            )

        kraken_pair = self.SYMBOL_MAP[request.asset_id]
        interval = self.TIMEFRAME_MAP[request.timeframe]

        start_ts = int(pd.Timestamp(request.start, tz="UTC").timestamp())

        all_raw_bytes = b""
        all_frames: list[pd.DataFrame] = []
        since = start_ts

        while True:
            self._respect_rate_limit()
            raw_bytes, df_chunk, last_ts = self._fetch_chunk(
                kraken_pair, interval, since
            )
            all_raw_bytes += raw_bytes

            # If Kraken returned no data at all, we're done
            if df_chunk.empty:
                break

            # Truncate to requested period
            # après — nouveaux noms, aucune collision avec les int du haut de fonction
            req_start = pd.Timestamp(request.start, tz="UTC")
            req_end = pd.Timestamp(request.end, tz="UTC")
            df_chunk = df_chunk[
                (df_chunk.index >= req_start) & (df_chunk.index <= req_end)
            ]

            # If we have data in our requested range, keep it
            if not df_chunk.empty:
                all_frames.append(df_chunk)

            # If we got no data in our requested range, we're done
            # (since we can only get newer data with 'since',
            #  and we're looking for older data)
            if df_chunk.empty:
                break

            # Update 'since' to get older data next time
            # Kraken's 'since' parameter returns data NEWER than the given
            # timestamp. To get older data, use the oldest timestamp from
            # what we just received.
            if last_ts > since:
                # We got data, so we can try to get older data
                since = last_ts
            else:
                # We're not getting older data, so we're done
                break

            # Safety break to prevent infinite loops
            # Kraken returns max 720 candles per call,
            # so we break after reasonable attempts
            # The logic above handles termination based on data availability

        if not all_frames:
            return FetchResult(
                data=pd.DataFrame(),
                hash="",
                status="failed",
                source_id=self.source_id,
                fetched_at=fetched_at,
                rows=0,
                timeframe=request.timeframe,
                fallback=False,
            )

        df = pd.concat(all_frames).sort_index()
        df = df[~df.index.duplicated(keep="first")]

        # Hash of concatenated raw bytes from all calls
        assembly_hash = hashlib.sha256(all_raw_bytes).hexdigest()

        coverage_status = "success"
        expected_start = pd.Timestamp(request.start, tz="UTC")
        expected_end = pd.Timestamp(request.end, tz="UTC")
        if len(df) > 0:
            if df.index[0] > expected_start or df.index[-1] < expected_end:
                coverage_status = "partial"

        return FetchResult(
            data=df,
            hash=assembly_hash,
            status=coverage_status,
            source_id=self.source_id,
            fetched_at=fetched_at,
            rows=len(df),
            timeframe=request.timeframe,
            fallback=False,
        )

    # ── Internal methods ─────────────────────────────────────────────────────

    def _fetch_chunk(
        self,
        pair: str,
        interval: int,
        since: int,
    ) -> tuple[bytes, pd.DataFrame, int]:
        """
        Single Kraken API call. Return (raw_bytes, DataFrame, last_timestamp).

        Raises:
            requests.RequestException: Network error.
            RuntimeError: Kraken business error (e.g., invalid pair).
        """
        params: dict[str, Any] = {"pair": pair, "interval": interval, "since": since}
        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=self._timeout,
            headers={"User-Agent": "mif-dal/0.1 (github.com/dravitch/mif-dal)"},
        )
        response.raise_for_status()
        raw_bytes = response.content

        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Kraken API error: {data['error']}")

        result = data.get("result", {})
        last_ts = result.get("last", since)

        # Pair may be returned under slightly different name
        # (e.g., "XXBTZUSD" instead of "XBTUSD")
        ohlc_data = None
        for key in result:
            if key != "last":
                ohlc_data = result[key]
                break

        if not ohlc_data:
            return raw_bytes, pd.DataFrame(), last_ts

        df = self._parse_ohlcv(ohlc_data)
        return raw_bytes, df, last_ts

    def _parse_ohlcv(self, ohlc_data: list) -> pd.DataFrame:
        """
        Parse Kraken response into normalized OHLCV DataFrame.

        Kraken returns: [time, open, high, low, close, vwap, volume, count]
        We keep: open, high, low, close, volume
        Index: UTC DatetimeIndex
        """
        df = pd.DataFrame(
            ohlc_data,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "vwap",
                "volume",
                "count",
            ],
        )
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("time")
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        df.index.name = None
        return df

    def _respect_rate_limit(self) -> None:
        """Pause if necessary to respect Kraken rate limit."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request_at = time.monotonic()
