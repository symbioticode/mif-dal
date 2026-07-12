# tests/conftest.py
"""
Pytest configuration for mif-dal.

Registered marks:
  @pytest.mark.network — tests that make real network calls.
  These tests are skipped by default in CI and in environments without network.

Usage:
  pytest                          # excludes network tests
  pytest -m network               # only network tests
  pytest -m "not network"         # explicitly without network
  pytest --run-network            # includes network tests
"""

import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Include tests that make real network calls.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "network: test that makes real network calls — skipped by default in CI.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Auto-skip @pytest.mark.network tests unless --run-network is set."""
    if config.getoption("--run-network"):
        return  # let everything pass

    skip_network = pytest.mark.skip(
        reason="Network test skipped by default. Use --run-network to include it."
    )
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


# ─── Common Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def valid_handoff_kwargs(
    sample_stream: pd.DataFrame,
    utc_now: datetime,
    sample_manifest_entry: dict[str, Any],
) -> dict[str, Any]:
    """Complete kwargs for a valid DALHandoff — tests override specific fields."""
    return {
        "stream": sample_stream,
        "asset_id": "PAXG-USD",
        "calendar": "CRYPTO_247",
        "assembly_hash": _VALID_HASH,
        "handoff_timestamp": utc_now,
        "dal_version": "0.1.0",
        "source_manifest": (sample_manifest_entry,),
        "coverage": "FULL",
        "truncated_days": 0,
        "dqf_status": "PASS",
        "dqf_mpi": 95.0,
        "dqf_version": "1.2.0.post1",
        "dqf_version_target": "1.2.0",
        "dqf_report": object(),  # opaque sentinel — handoff does not introspect it
        "aqi": 85.0,
    }


@pytest.fixture
def sample_stream() -> pd.DataFrame:
    """Minimal OHLCV DataFrame with DatetimeIndex UTC."""
    return pd.DataFrame(
        {
            "open": [1.0, 1.1, 1.2],
            "high": [1.1, 1.2, 1.3],
            "low": [0.9, 1.0, 1.1],
            "close": [1.05, 1.15, 1.25],
            "volume": [100.0, 110.0, 120.0],
        },
        index=pd.date_range("2023-01-01", periods=3, tz="UTC"),
    )


@pytest.fixture
def sample_manifest_entry() -> dict[str, Any]:
    """Minimal source manifest entry."""
    return {
        "source_id": "test_source",
        "status": "success",
        "hash": "a" * 64,
        "fetched_at": datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        "rows": 3,
        "timeframe": "1D",
        "fallback": False,
    }


@pytest.fixture
def utc_now() -> datetime:
    """Fixed UTC timestamp for deterministic tests."""
    return datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)


_VALID_HASH = "a" * 64


@pytest.fixture
def dukascopy_available() -> bool:
    """True if dukascopy-node is installed and accessible."""
    return shutil.which("dukascopy-node") is not None or _npx_dukascopy_available()


def _npx_dukascopy_available() -> bool:
    try:
        result = subprocess.run(
            ["npx", "dukascopy-node", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
def skip_if_no_dukascopy(dukascopy_available: bool) -> None:
    """Skip the test if dukascopy-node is not available."""
    if not dukascopy_available:
        pytest.skip(
            "dukascopy-node not available. " "Run setup_dukascopy_mif.sh then restart."
        )


@pytest.fixture
def skip_if_no_network() -> None:
    """Skip the test if network is not accessible."""
    try:
        import socket

        socket.create_connection(("api.kraken.com", 443), timeout=3)
    except OSError:
        pytest.skip("Network not accessible.")
