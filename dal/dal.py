"""DAL — public class wiring S1→S5 behind get_certified / get_diagnostic.

Spec: docs/DAL_SPECIFICATION_v1.0.md §7.
"""

from __future__ import annotations

from dqf import DQFMode

from dal.core.config import DALConfig
from dal.core.handoff import DALHandoff
from dal.core.pipeline import assemble_handoff
from dal.core.sources import resolve_and_fetch
from dal.exceptions import DALConfigError
from dal.interfaces.source import FetchRequest, Source


class DAL:
    """Entry point. Holds a registry of source adapters and the runtime config."""

    def __init__(self, config: DALConfig, sources: tuple[Source, ...]) -> None:
        self._config = config
        self._sources_by_id: dict[str, Source] = {}
        for source in sources:
            if source.source_id in self._sources_by_id:
                raise DALConfigError(
                    f"Duplicate source_id in registry: {source.source_id!r}"
                )
            self._sources_by_id[source.source_id] = source

    def get_certified_stream(
        self,
        *,
        asset_id: str,
        source_preference: list[str],
        start: str,
        end: str,
        calendar: str,
        dqf_version_target: str,
    ) -> DALHandoff:
        """CERTIFICATION mode — strict, deterministic, reproducible."""
        if not calendar:
            raise DALConfigError("calendar is mandatory in get_certified_stream")
        if not dqf_version_target:
            raise DALConfigError(
                "dqf_version_target is mandatory in get_certified_stream"
            )
        return self._run_pipeline(
            asset_id=asset_id,
            source_preference=source_preference,
            start=start,
            end=end,
            calendar=calendar,
            dqf_mode=DQFMode.CERTIFICATION,
            dqf_version_target=dqf_version_target,
        )

    def get_diagnostic_stream(
        self,
        *,
        asset_id: str,
        source_preference: list[str],
        start: str,
        end: str,
        calendar: str,
        dqf_version_target: str = "",
    ) -> DALHandoff:
        """DIAGNOSTIC mode — exploratory, advisory DQF result."""
        # Calendar required in v0.1 — DQF does not auto-detect (see TD-009).
        if not calendar:
            raise DALConfigError(
                "calendar is mandatory in get_diagnostic_stream "
                "(DQF does not auto-detect; see TD-009)"
            )
        return self._run_pipeline(
            asset_id=asset_id,
            source_preference=source_preference,
            start=start,
            end=end,
            calendar=calendar,
            dqf_mode=DQFMode.DIAGNOSTIC,
            dqf_version_target=dqf_version_target,
        )

    def _run_pipeline(
        self,
        *,
        asset_id: str,
        source_preference: list[str],
        start: str,
        end: str,
        calendar: str,
        dqf_mode: DQFMode,
        dqf_version_target: str,
    ) -> DALHandoff:
        sources = self._resolve_sources(source_preference)
        request = FetchRequest(asset_id=asset_id, start=start, end=end)
        resolution = resolve_and_fetch(
            request=request, sources=sources, config=self._config
        )
        return assemble_handoff(
            raw_stream=resolution.raw_stream,
            asset_id=asset_id,
            calendar=calendar,
            dqf_mode=dqf_mode,
            dqf_version_target=dqf_version_target,
            source_manifest=resolution.source_manifest,
            coverage=resolution.coverage,
            truncated_days=resolution.truncated_days,
            aqi=resolution.aqi,
        )

    def _resolve_sources(self, preference: list[str]) -> tuple[Source, ...]:
        if not preference:
            raise DALConfigError("source_preference cannot be empty")
        missing = [s for s in preference if s not in self._sources_by_id]
        if missing:
            raise DALConfigError(
                f"Sources not registered: {missing}. "
                f"Available: {sorted(self._sources_by_id)}"
            )
        return tuple(self._sources_by_id[s] for s in preference)
