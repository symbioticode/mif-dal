"""DALHandoff — immutable transfer object from MIF-DAL to its callers.

Spec: docs/DAL_SPECIFICATION_v1.0.md Section 5
Decisions: D-DAL-002 (single transfer object), D-DAL-006 (raw-bytes hash),
           D-DAL-007 (one asset per handoff)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from dqf import DQFReport


_OHLCV_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")
_VALID_COVERAGE: frozenset[str] = frozenset({"FULL", "PARTIAL", "DEGRADED"})
_VALID_DQF_STATUS: frozenset[str] = frozenset({"PASS", "WARNING"})
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class DALHandoff:
    stream: pd.DataFrame
    asset_id: str
    calendar: str
    assembly_hash: str
    handoff_timestamp: datetime
    dal_version: str
    source_manifest: tuple[dict[str, Any], ...]
    coverage: str
    truncated_days: int
    dqf_status: str
    dqf_mpi: float
    dqf_version: str
    dqf_version_target: str
    dqf_report: DQFReport
    aqi: float

    def __post_init__(self) -> None:
        self._validate_stream()
        self._validate_identity()
        self._validate_provenance()
        self._validate_coverage()
        self._validate_dqf()
        self._validate_aqi()

    def _validate_stream(self) -> None:
        if not isinstance(self.stream, pd.DataFrame):
            raise TypeError("stream must be a pandas DataFrame")
        if self.stream.empty:
            raise ValueError("stream cannot be empty")

        missing = [c for c in _OHLCV_COLUMNS if c not in self.stream.columns]
        if missing:
            raise ValueError(f"stream missing OHLCV columns: {missing}")

        non_float = [c for c in _OHLCV_COLUMNS if self.stream[c].dtype != "float64"]
        if non_float:
            raise ValueError(
                f"stream OHLCV columns must be float64, got non-float64: {non_float}"
            )

        if not isinstance(self.stream.index, pd.DatetimeIndex):
            raise ValueError("stream must have a DatetimeIndex")
        if self.stream.index.tz is None:
            raise ValueError("stream DatetimeIndex must be timezone-aware (UTC)")
        if self.stream[list(_OHLCV_COLUMNS)].isna().any().any():
            raise ValueError(
                "stream contains NaN values (DQF must clean before handoff)"
            )
        if not self.stream.index.is_monotonic_increasing:
            raise ValueError("stream index must be sorted ascending")
        if self.stream.index.has_duplicates:
            raise ValueError("stream index has duplicate entries")

    def _validate_identity(self) -> None:
        if not self.asset_id:
            raise ValueError("asset_id cannot be empty")
        if not self.calendar:
            raise ValueError("calendar cannot be empty")

    def _validate_provenance(self) -> None:
        if not _HEX64_RE.match(self.assembly_hash):
            raise ValueError(
                "assembly_hash must be a 64-char lowercase SHA-256 hex digest"
            )
        if self.handoff_timestamp.tzinfo is None:
            raise ValueError("handoff_timestamp must be timezone-aware (UTC)")
        if not self.dal_version:
            raise ValueError("dal_version cannot be empty")
        if not isinstance(self.source_manifest, tuple):
            raise TypeError(
                "source_manifest must be a tuple (frozen dataclass requires immutable)"
            )
        if not self.source_manifest:
            raise ValueError("source_manifest cannot be empty")

    def _validate_coverage(self) -> None:
        if self.coverage not in _VALID_COVERAGE:
            raise ValueError(
                f"coverage must be one of "
                f"{sorted(_VALID_COVERAGE)}, got {self.coverage!r}"
            )
        if self.truncated_days < 0:
            raise ValueError("truncated_days must be >= 0")
        if self.coverage == "FULL" and self.truncated_days != 0:
            raise ValueError("coverage=FULL requires truncated_days=0")

    def _validate_dqf(self) -> None:
        # FAIL/VOID never reach a DALHandoff — they raise
        # DALHandoffError upstream (D-DAL-005).
        if self.dqf_status not in _VALID_DQF_STATUS:
            raise ValueError(
                f"dqf_status must be one of {sorted(_VALID_DQF_STATUS)}, "
                f"got {self.dqf_status!r}"
            )
        if not 0.0 <= self.dqf_mpi <= 100.0:
            raise ValueError("dqf_mpi must be in [0, 100]")
        if not self.dqf_version:
            raise ValueError("dqf_version cannot be empty")

    def _validate_aqi(self) -> None:
        if not 0.0 <= self.aqi <= 100.0:
            raise ValueError("aqi must be in [0, 100]")
