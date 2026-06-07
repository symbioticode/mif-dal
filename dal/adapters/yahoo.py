"""
dal/adapters/yahoo.py
 =======================
YahooAdapter — implementation of Source Protocol via yfinance 1.3.0.

Responsibility:
    Download OHLCV data via yfinance (yahoo finance),
    normalize the DataFrame, calculate SHA-256 hash of raw bytes,
    and return a FetchResult.

Documented limitations:
    - yfinance 1.3.0+ returns a MultiIndex requiring normalization
    - Yahoo rate limiting possible -> fallback to direct requests
    - OHLCV data adjusted (auto_adjust=True by default)
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import ClassVar

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None  # Handle case where yfinance is not installed

import requests

from dal.interfaces.source import FetchRequest, FetchResult


class YahooAdapter:
    """
    Yahoo Finance adapter for MIF-DAL.

    Uses yfinance 1.3.0+ to download OHLCV data.
    Implements native requests fallback in case of rate limiting.

    Usage:
        src = YahooAdapter()
        req = FetchRequest(
            asset_id="BTC-USD",
            start="2023-01-01",
            end="2024-01-01",
            timeframe="1D",
        )
        result = src.fetch(req)
        # result.hash  = SHA-256 of raw bytes (parquet)
        # result.data  = normalized OHLCV DataFrame, DatetimeIndex UTC
    """

    # yfinance uses tickers as-is for crypto pairs
    SYMBOL_MAP: ClassVar[dict[str, str]] = {
        "BTC-USD": "BTC-USD",
        "ETH-USD": "ETH-USD",
        "PAXG-USD": "PAXG-USD",
        "SOL-USD": "SOL-USD",
        "ADA-USD": "ADA-USD",
        "DOT-USD": "DOT-USD",
        "LINK-USD": "LINK-USD",
        "AVAX-USD": "AVAX-USD",
    }

    # Mapping DAL timeframe → yfinance interval
    # yfinance accepts: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    TIMEFRAME_MAP: ClassVar[dict[str, str]] = {
        "1M": "1m",
        "2M": "2m",
        "5M": "5m",
        "15M": "15m",
        "30M": "30m",
        "90M": "90m",
        "1H": "1h",
        "1D": "1d",
        "5D": "5d",
        "1W": "1wk",
        "1Mo": "1mo",
        "3Mo": "3mo",
    }

    def __init__(
        self,
        request_timeout: int = 30,
        fallback_enabled: bool = True,
    ) -> None:
        """
        Args:
            request_timeout: Seconds before timeout for HTTP requests.
            fallback_enabled: Enable requests fallback in case of rate
                limiting.
        """
        self._timeout = request_timeout
        self._fallback_enabled = fallback_enabled

    # ── Source Protocol ────────────────────────────────────────────────────

    @property
    def source_id(self) -> str:
        return "yahoo"

    def supports(self, asset_id: str) -> bool:
        """Return True if the asset is available on Yahoo Finance."""
        # Yahoo Finance supports almost all major pairs
        # We rely on our mapping to remain consistent
        return asset_id in self.SYMBOL_MAP

    def fetch(self, request: FetchRequest) -> FetchResult:
        """
        Download OHLCV data via yfinance with requests fallback.

        Sequence:
            1. Try yf.download() with parameters
            2. If < 30 rows and fallback enabled -> use direct requests
            3. Normalize DataFrame (handle yfinance 1.3.0+ MultiIndex)
            4. Calculate SHA-256 on raw bytes (parquet)
            5. Return FetchResult

        Returns:
            FetchResult with status "success" | "partial" | "failed".
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

        symbol = self.SYMBOL_MAP[request.asset_id]
        yf_interval = self.TIMEFRAME_MAP[request.timeframe]

        # Main attempt with yfinance
        df_raw = None
        used_fallback = False

        if yf is not None:
            try:
                # yfinance 1.3.0+: auto_adjust=True for adjusted OHLCV
                df_raw = yf.download(
                    tickers=symbol,
                    start=request.start,
                    end=request.end,
                    interval=yf_interval,
                    auto_adjust=True,
                    progress=False,  # Disable progress bar
                    threads=False,  # Avoid issues in restricted environments
                )

                # Check if we have enough data (anti rate-limiting)
                if len(df_raw) >= 30:
                    # Success with yfinance
                    pass
                else:
                    # Too few rows, probably rate limiting
                    if self._fallback_enabled:
                        df_raw = None  # Force fallback
                    # Otherwise continue with what we have (may be empty)

            except Exception:
                # yfinance failed, try fallback
                if self._fallback_enabled:
                    df_raw = None
                # Otherwise propagate error below

        # Native requests fallback if yfinance unavailable or rate limited
        if df_raw is None and self._fallback_enabled:
            df_raw = self._fallback_fetch(
                symbol, request.start, request.end, yf_interval
            )
            used_fallback = True

        if df_raw is None or df_raw.empty:
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

        # Critical normalization for yfinance 1.3.0+: handle MultiIndex
        if isinstance(df_raw.columns, pd.MultiIndex):
            df_raw.columns = df_raw.columns.get_level_values(0).str.lower()
        else:
            # Ensure columns are lowercase
            df_raw.columns = [str(col).lower().strip() for col in df_raw.columns]

        # Standardize expected column names
        column_mapping = {
            "adj close": "adjclose",  # yfinance sometimes renames
        }
        df_raw = df_raw.rename(columns=column_mapping)

        # Ensure we have basic OHLCV columns
        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(set(df_raw.columns)):
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

        # Keep only OHLCV (remove adjclose if present)
        cols_to_keep = [
            c for c in df_raw.columns if c in required_cols or c == "adjclose"
        ]
        df = df_raw[cols_to_keep].copy()
        if "adjclose" in df.columns:
            # Yahoo Finance adjusted: use close as reference price
            # and remove adjclose to keep pure OHLCV
            df = df[["open", "high", "low", "close", "volume"]]

        # Ensure correct order and column types
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        # Yahoo Finance already returns a DatetimeIndex, ensure it is UTC
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        elif str(df.index.tz) != "UTC":
            df.index = df.index.tz_convert("UTC")

        # Remove duplicate index entries (precaution)
        df = df[~df.index.duplicated(keep="first")]

        # Calculate hash on raw bytes (parquet) of DataFrame
        # This ensures traceability identical to other adapters
        buffer = io.BytesIO()
        df.to_parquet(buffer)
        raw_bytes = buffer.getvalue()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Determine coverage status
        # Yahoo Finance is generally reliable;
        # consider "success" if we have data
        status = "success"

        return FetchResult(
            data=df,
            hash=file_hash,
            status=status,
            source_id=self.source_id,
            fetched_at=fetched_at,
            rows=len(df),
            timeframe=request.timeframe,
            fallback=used_fallback,
        )

    def _fallback_fetch(
        self, symbol: str, start: str, end: str, interval: str
    ) -> pd.DataFrame | None:
        """
        Native requests fallback for Yahoo Finance.
        Used when yfinance rate limits or returns too little data.
        """
        try:
            # Parameter conversion for undocumented Yahoo Finance API
            # This implementation is based on gate0_yfinance_troubleshooting.md

            # Convert dates to Unix timestamp
            start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
            end_ts = int(pd.Timestamp(end, tz="UTC").timestamp())

            # Mapping yfinance intervals to Yahoo parameters
            interval_mapping = {
                "1m": "1m",
                "2m": "2m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "60m": "60m",
                "90m": "90m",
                "1h": "60m",
                "1d": "1d",
                "5d": "5d",
                "1wk": "1wk",
                "1mo": "1mo",
                "3mo": "3mo",
            }
            yahoo_interval = interval_mapping.get(interval, "1d")

            # Undocumented but stable Yahoo Finance API URL
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                "period1": start_ts,
                "period2": end_ts,
                "interval": yahoo_interval,
                "includePrePost": "false",
                "events": "div%2Csplit%2Crename",
                "lang": "en-US",
                "region": "US",
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; mif-dal/0.1)",
                "Accept": "application/json",
            }

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("chart", {}).get("error"):
                return None

            result = data["chart"]["result"][0]
            if not result:
                return None

            # Extract OHLCV data
            timestamps = result["timestamp"]
            ohlc = result["indicators"]["quote"][0]

            # Build DataFrame
            df_data = {
                "open": ohlc["open"],
                "high": ohlc["high"],
                "low": ohlc["low"],
                "close": ohlc["close"],
                "volume": ohlc["volume"],
            }

            df = pd.DataFrame(
                df_data, index=pd.to_datetime(timestamps, unit="s", utc=True)
            )
            df.index.name = None

            # Remove rows with NaN (missing data)
            df = df.dropna()

            return df if not df.empty else None

        except Exception:
            # If fallback fails, return None to indicate failure
            return None
