"""S1 source resolution + S2 completeness + AQI computation.

Spec: docs/DAL_SPECIFICATION_v1.0.md §S1, §S2, §6.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from dal.core.config import DALConfig
from dal.exceptions import DALHandoffError
from dal.interfaces.source import (
    FetchRequest,
    FetchResult,
    Source,
    SourceFetchError,
)

_GRAVITY_FALLBACK = 0.20
_GRAVITY_RETRY = 0.05
_GRAVITY_TRUNC_PER_SIDE = 0.10
_GRAVITY_DEGRADED = 0.30
_DEGRADED_RATIO_THRESHOLD = 0.80


@dataclass(frozen=True)
class CompletenessReport:
    coverage: str  # "FULL" | "PARTIAL" | "DEGRADED"
    truncated_days: int
    truncated_start: bool
    truncated_end: bool


@dataclass(frozen=True)
class ResolutionResult:
    """Output of resolve_and_fetch — feeds into pipeline.assemble_handoff."""

    raw_stream: pd.DataFrame
    source_manifest: tuple[dict[str, Any], ...]
    coverage: str
    truncated_days: int
    aqi: float


def resolve_and_fetch(
    *,
    request: FetchRequest,
    sources: tuple[Source, ...],
    config: DALConfig,
    max_retries: int = 3,
) -> ResolutionResult:
    """Iterate the source preference list, retrying transient failures.

    Returns the first successful fetch, with completeness assessed
    and AQI computed from accumulated penalties.

    Raises:
        DALHandoffError(reason="ALL_SOURCES_FAILED"): no source delivered.
    """
    del config  # request_timeout / cache_dir not yet wired (DAL-008+)

    candidates = tuple(s for s in sources if s.supports(request.asset_id))
    if not candidates:
        raise DALHandoffError(
            f"No source supports asset {request.asset_id}.",
            reason="ALL_SOURCES_FAILED",
            source_failures=[],
        )

    manifest_entries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total_penalty = 0.0

    for idx, source in enumerate(candidates):
        is_fallback = idx > 0
        result, retries_used, last_error = _try_source_with_retries(
            source, request, max_retries
        )
        total_penalty += _GRAVITY_RETRY * retries_used

        if result is None:
            manifest_entries.append(
                _failure_manifest_entry(source, request, is_fallback)
            )
            failures.append(
                {
                    "source_id": source.source_id,
                    "error": str(last_error) if last_error else "unknown",
                    "retries": retries_used,
                }
            )
            if idx < len(candidates) - 1:
                total_penalty += _GRAVITY_FALLBACK
            continue

        report = _check_completeness(result.data, request.start, request.end)
        total_penalty += _coverage_penalty(report)

        entry_status = "success" if report.coverage == "FULL" else "partial"
        manifest_entries.append(
            {
                "source_id": source.source_id,
                "status": entry_status,
                "hash": result.hash,
                "fetched_at": result.fetched_at,
                "rows": result.rows,
                "timeframe": result.timeframe,
                "fallback": is_fallback,
            }
        )

        aqi = max(0.0, 100.0 * (1.0 - total_penalty))
        return ResolutionResult(
            raw_stream=result.data,
            source_manifest=tuple(manifest_entries),
            coverage=report.coverage,
            truncated_days=report.truncated_days,
            aqi=aqi,
        )

    raise DALHandoffError(
        f"All sources failed for {request.asset_id}.",
        reason="ALL_SOURCES_FAILED",
        source_failures=failures,
    )


def _try_source_with_retries(
    source: Source, request: FetchRequest, max_retries: int
) -> tuple[FetchResult | None, int, SourceFetchError | None]:
    """Attempt a fetch up to (1 + max_retries) times.

    Returns (result, retries_used, last_error). retries_used counts the
    retry attempts (i.e., attempts after the first), not the total.
    """
    retries_used = 0
    last_error: SourceFetchError | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            retries_used += 1
        try:
            return source.fetch(request), retries_used, None
        except SourceFetchError as exc:
            last_error = exc
    return None, retries_used, last_error


def _failure_manifest_entry(
    source: Source, request: FetchRequest, is_fallback: bool
) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "status": "failed",
        "hash": "",
        "fetched_at": datetime.now(UTC),
        "rows": 0,
        "timeframe": request.timeframe,
        "fallback": is_fallback,
    }


def _check_completeness(df: pd.DataFrame, start: str, end: str) -> CompletenessReport:
    req_start = pd.Timestamp(start, tz="UTC")
    req_end = pd.Timestamp(end, tz="UTC")
    requested_days = max(1, (req_end - req_start).days + 1)

    if df.empty:
        return CompletenessReport("DEGRADED", requested_days, True, True)

    delivered_start = df.index.min()
    delivered_end = df.index.max()
    truncated_start_days = max(0, (delivered_start - req_start).days)
    truncated_end_days = max(0, (req_end - delivered_end).days)
    truncated_days = truncated_start_days + truncated_end_days
    truncated_start = truncated_start_days > 0
    truncated_end = truncated_end_days > 0

    delivered_ratio = len(df) / requested_days

    if truncated_days == 0:
        coverage = "FULL"
    elif delivered_ratio < _DEGRADED_RATIO_THRESHOLD:
        coverage = "DEGRADED"
    else:
        coverage = "PARTIAL"

    return CompletenessReport(coverage, truncated_days, truncated_start, truncated_end)


def _coverage_penalty(report: CompletenessReport) -> float:
    if report.coverage == "FULL":
        return 0.0
    if report.coverage == "DEGRADED":
        return _GRAVITY_DEGRADED
    # PARTIAL — 0.10 per truncated side
    penalty = 0.0
    if report.truncated_start:
        penalty += _GRAVITY_TRUNC_PER_SIDE
    if report.truncated_end:
        penalty += _GRAVITY_TRUNC_PER_SIDE
    return penalty
