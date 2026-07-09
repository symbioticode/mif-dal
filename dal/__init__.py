"""MIF-DAL — Data Abstraction Layer."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("mif-dal")
except PackageNotFoundError:
    __version__ = "0.1.0"

from dal.core.config import DALConfig
from dal.core.handoff import DALHandoff
from dal.dal import DAL
from dal.exceptions import (
    DALConfigError,
    DALError,
    DALHandoffError,
    DALVersionError,
)

__all__ = [
    "DAL",
    "DALConfig",
    "DALConfigError",
    "DALError",
    "DALHandoff",
    "DALHandoffError",
    "DALVersionError",
]
