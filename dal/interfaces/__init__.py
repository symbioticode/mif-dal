"""DAL interfaces — abstract Protocols and transfer types."""

from dal.interfaces.source import (
    FetchRequest,
    FetchResult,
    Source,
    SourceFetchError,
)

__all__ = [
    "FetchRequest",
    "FetchResult",
    "Source",
    "SourceFetchError",
]
