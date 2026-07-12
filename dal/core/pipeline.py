"""S3 + S4 + S5: assembly hash, DQF gate, handoff emission.

Spec: docs/DAL_SPECIFICATION_v1.0.md §S3, §S4, §S5.
Decisions: D-DAL-002 (single transfer object), D-DAL-005 (DQF gate),
           D-DAL-006 (raw-bytes hash anchored both sides).
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING, Any

import pandas as pd
from dqf import DQFConfig, DQFMode, DQFValidator
from packaging.version import Version

from dal import __version__ as _DAL_VERSION
from dal.core.handoff import DALHandoff
from dal.exceptions import DALHandoffError, DALVersionError

if TYPE_CHECKING:
    from dqf import DQFReport


_DQF_STATUS_TO_DAL: dict[str, str] = {
    "CERTIFIED": "PASS",
    "WARNING": "WARNING",
}


def assemble_handoff(
    *,
    raw_stream: pd.DataFrame,
    asset_id: str,
    calendar: str,
    dqf_mode: DQFMode,
    dqf_version_target: str,
    source_manifest: tuple[dict[str, Any], ...],
    coverage: str,
    truncated_days: int,
    aqi: float,
    dqf_config: DQFConfig | None = None,
) -> DALHandoff:
    """Run S3+S4+S5: hash raw data, certify via DQF, emit DALHandoff or raise.

    Raises:
        DALVersionError: installed `mif-dqf` < `dqf_version_target`.
        DALHandoffError: DQF returned VOID or an unrecognised status.
    """
    _check_dqf_version(dqf_version_target)

    assembly_hash = _hash_raw_stream(raw_stream)

    config = dqf_config or DQFConfig(mode=dqf_mode)
    validator = DQFValidator(config)
    report = validator.validate(
        raw_stream,
        calendar=calendar,
        raw_data_hash=assembly_hash,
    )

    dqf_status = _map_dqf_status(report, asset_id)

    return DALHandoff(
        stream=report.cleaned_data,
        asset_id=asset_id,
        calendar=calendar,
        assembly_hash=assembly_hash,
        handoff_timestamp=datetime.now(UTC),
        dal_version=_DAL_VERSION,
        source_manifest=source_manifest,
        coverage=coverage,
        truncated_days=truncated_days,
        dqf_status=dqf_status,
        dqf_mpi=report.purity_index,
        dqf_version=report.dqf_version,
        dqf_version_target=dqf_version_target,
        dqf_report=report,
        aqi=aqi,
    )


def _hash_raw_stream(raw_stream: pd.DataFrame) -> str:
    raw_bytes = raw_stream.to_parquet()
    return sha256(raw_bytes).hexdigest()


def _check_dqf_version(target: str) -> None:
    if not target:
        return
    installed = _pkg_version("mif-dqf")
    if Version(installed) < Version(target):
        raise DALVersionError(
            f"Installed mif-dqf {installed} is below required {target}",
            installed_version=installed,
            required_version=target,
        )


def _map_dqf_status(report: DQFReport, asset_id: str) -> str:
    status = report.overall_status
    if status in _DQF_STATUS_TO_DAL:
        return _DQF_STATUS_TO_DAL[status]
    if status == "VOID":
        raise DALHandoffError(
            f"DQF returned VOID for {asset_id} — certification cannot proceed.",
            reason="DQF_VOID",
            dqf_report=report,
        )
    raise DALHandoffError(
        f"DQF returned unrecognised status {status!r} for {asset_id}.",
        reason="DQF_UNEXPECTED_STATUS",
        dqf_report=report,
    )
