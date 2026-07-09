"""
dal/adapters/dukascopy.py
 ===========================
DukascopyAdapter — Source Protocol implementation via dukascopy-node (CLI).

Responsibility:
    Download OHLCV data via dukascopy-node CLI (Node.js),
    parse the resulting CSV, compute SHA-256 hash of raw bytes,
    and return a FetchResult.

System requirements:
    - Node.js ≥ 16
    - dukascopy-node installed globally: npm install -g dukascopy-node
    - Verify with: npx dukascopy-node --help

Documented limitations:
    - PAXG not available → supports("PAXG-USD") returns False
    - Max 12 months history per asset
    - Depends on Node.js subprocess → mandatory timeout
    - Bid price data only (no ask)

KB-008 pattern applied:
    subprocess with timeout=300 + stdin=subprocess.DEVNULL
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pandas as pd

from dal.interfaces.source import FetchRequest, FetchResult


class DukascopyAdapter:
    """
    Dukascopy adapter for MIF-DAL.

    Uses dukascopy-node CLI to download OHLCV data.
    Each download produces a temporary CSV whose raw bytes
    are hashed before parsing.

    Note: PAXG is not available on Dukascopy. This is not a bug.
    For PAXG, use KrakenAdapter or YahooAdapter.
    """

    # DAL asset_id → dukascopy-node symbol mapping
    SYMBOL_MAP: ClassVar[dict[str, str]] = {
        "BTC-USD": "btcusd",
        "ETH-USD": "ethusd",
        "XRP-USD": "xrpusd",
        "SOL-USD": "solusd",
        "ADA-USD": "adausd",
        "DOT-USD": "dotusd",
        "AVAX-USD": "avaxusd",
        "LINK-USD": "linkusd",
        # PAXG-USD: not available on Dukascopy
    }

    # DAL timeframe → dukascopy-node code mapping
    TIMEFRAME_MAP: ClassVar[dict[str, str]] = {
        "1D": "d1",
        "4H": "h4",
        "1H": "h1",
        "30M": "m30",
        "15M": "m15",
        "5M": "m5",
        "1M": "m1",
    }

    def __init__(
        self,
        node_timeout: int = 300,
        max_history_days: int = 365,
    ) -> None:
        """
        Args:
            node_timeout: Seconds before Node.js subprocess timeout.
            max_history_days: Dukascopy limit (12 months = 365 days).
        """
        self._timeout = node_timeout
        self._max_days = max_history_days
        self._node_available: bool | None = None

    # ── Source Protocol ────────────────────────────────────────────────────

    @property
    def source_id(self) -> str:
        return "dukascopy"

    def supports(self, asset_id: str) -> bool:
        """Return True if the asset is available on Dukascopy."""
        return asset_id in self.SYMBOL_MAP

    def fetch(self, request: FetchRequest) -> FetchResult:
        """
        Download OHLCV data via dukascopy-node.

        Sequence:
            1. Check Node.js and dukascopy-node availability
            2. Launch subprocess with timeout + stdin=DEVNULL
            3. Read raw bytes of produced CSV
            4. Compute SHA-256 on raw bytes
            5. Parse CSV to normalized OHLCV DataFrame
            6. Return FetchResult

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

        if not self._is_node_available():
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

        duka_symbol = self.SYMBOL_MAP[request.asset_id]
        duka_timeframe = self.TIMEFRAME_MAP[request.timeframe]

        # Dukascopy limited to 12 months — document truncation in FetchResult
        start_ts = pd.Timestamp(request.start, tz="UTC")
        end_ts = pd.Timestamp(request.end, tz="UTC")
        actual_start = start_ts
        truncated = False
        if (end_ts - start_ts).days > self._max_days:
            actual_start = end_ts - pd.Timedelta(days=self._max_days)
            truncated = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "npx",
                "dukascopy-node",
                "-i",
                duka_symbol,
                "-from",
                actual_start.strftime("%Y-%m-%d"),
                "-to",
                end_ts.strftime("%Y-%m-%d"),
                "-t",
                duka_timeframe,
                "-f",
                "csv",
                "-p",
                "bid",
                "-dir",
                tmpdir,
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,  # bytes, not str
                    timeout=self._timeout,
                    stdin=subprocess.DEVNULL,  # KB-008: avoid stdin blocking
                )
            except subprocess.TimeoutExpired:
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

            if proc.returncode != 0:
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

            # Find CSV produced in tmpdir
            csv_files = list(Path(tmpdir).glob("*.csv"))
            if not csv_files:
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

            csv_path = csv_files[0]
            raw_bytes = csv_path.read_bytes()

            if len(raw_bytes) < 50:
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

            # Hash on raw bytes before any parsing
            file_hash = hashlib.sha256(raw_bytes).hexdigest()

            df = self._parse_csv(raw_bytes)

        if df.empty:
            return FetchResult(
                data=pd.DataFrame(),
                hash=file_hash,
                status="failed",
                source_id=self.source_id,
                fetched_at=fetched_at,
                rows=0,
                timeframe=request.timeframe,
                fallback=False,
            )

        status = "partial" if truncated else "success"
        return FetchResult(
            data=df,
            hash=file_hash,
            status=status,
            source_id=self.source_id,
            fetched_at=fetched_at,
            rows=len(df),
            timeframe=request.timeframe,
            fallback=False,
        )

    # ── Internal methods ─────────────────────────────────────────────────

    def _is_node_available(self) -> bool:
        """
        Check Node.js + dukascopy-node availability once
        (result cached).
        """
        if self._node_available is not None:
            return self._node_available
        try:
            r = subprocess.run(
                ["npx", "dukascopy-node", "--help"],
                capture_output=True,
                timeout=15,
                stdin=subprocess.DEVNULL,
            )
            self._node_available = r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self._node_available = False
        return self._node_available

    def _parse_csv(self, raw_bytes: bytes) -> pd.DataFrame:
        """
        Parse Dukascopy CSV to normalized OHLCV DataFrame.

        Dukascopy CSV: timestamp (ms Unix), open, high, low, close, volume
        Header may or may not be present depending on dukascopy-node version.
        """
        import io

        text = raw_bytes.decode("utf-8", errors="replace")
        lines = text.strip().splitlines()

        if not lines:
            return pd.DataFrame()

        # Detect if CSV has header
        has_header = "timestamp" in lines[0].lower() or "time" in lines[0].lower()

        if has_header:
            df = pd.read_csv(io.StringIO(text))
            df.columns = [c.lower().strip() for c in df.columns]
        else:
            df = pd.read_csv(
                io.StringIO(text),
                header=None,
                names=["timestamp", "open", "high", "low", "close", "volume"],
            )

        if df.empty:
            return df

        # Normalize timestamp (milliseconds → DatetimeIndex UTC)
        time_col = "timestamp" if "timestamp" in df.columns else "time"
        if pd.api.types.is_numeric_dtype(df[time_col]):
            df["timestamp"] = pd.to_datetime(df[time_col], unit="ms", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(df[time_col], utc=True)

        df = df.set_index("timestamp")
        df.index.name = None

        # Keep only OHLCV columns
        cols = ["open", "high", "low", "close", "volume"]
        available = [c for c in cols if c in df.columns]
        if "volume" not in available:
            df["volume"] = 0.0
            available.append("volume")

        df = df[cols].astype(float)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="first")]
        df = df.dropna()

        return df
