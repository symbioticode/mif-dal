"""DALConfig — runtime configuration for the DAL.

Spec: docs/DAL_SPECIFICATION_v1.0.md Section 7
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DALConfig:
    cache_dir: str | None = None
    request_timeout: int = 30

    def __post_init__(self) -> None:
        if self.request_timeout <= 0:
            raise ValueError(f"request_timeout must be > 0, got {self.request_timeout}")
        if self.cache_dir is not None and not self.cache_dir:
            raise ValueError(
                "cache_dir must be a non-empty path (use None to disable caching)"
            )
