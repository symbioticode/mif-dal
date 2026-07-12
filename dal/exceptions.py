"""DAL exception hierarchy.

Spec: docs/DAL_SPECIFICATION_v1.0.md Section 8
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dqf import DQFReport


_VALID_HANDOFF_REASONS: frozenset[str] = frozenset(
    {
        "DQF_VOID",
        "DQF_UNEXPECTED_STATUS",
        "ALL_SOURCES_FAILED",
    }
)


class DALError(Exception):
    """Base class for all MIF-DAL exceptions."""


class DALConfigError(DALError):
    """Missing or invalid configuration before any network call.

    Example: `calendar` omitted in `get_certified_stream()`.
    """


class DALVersionError(DALError):
    """Installed `mif-dqf` version is below `dqf_version_target`.

    Raised before any DQF call.
    """

    def __init__(
        self,
        message: str,
        *,
        installed_version: str,
        required_version: str,
    ) -> None:
        super().__init__(message)
        self.installed_version = installed_version
        self.required_version = required_version


class DALHandoffError(DALError):
    """Handoff could not be emitted.

    `reason` is one of:
        - "DQF_VOID"              — DQF returned VOID; `dqf_report` is set.
        - "DQF_UNEXPECTED_STATUS" — DQF returned a status DAL does not
                                    recognize (forward-compat guard);
                                    `dqf_report` is set.
        - "ALL_SOURCES_FAILED"    — every source in preference list failed;
                                    `source_failures` lists each attempt.

    DQF has no `FAIL` status — any CORE check failure produces `VOID`.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        dqf_report: DQFReport | None = None,
        source_failures: list[dict[str, Any]] | None = None,
    ) -> None:
        if reason not in _VALID_HANDOFF_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(_VALID_HANDOFF_REASONS)}, "
                f"got {reason!r}"
            )
        super().__init__(message)
        self.reason = reason
        self.dqf_report = dqf_report
        self.source_failures = source_failures
