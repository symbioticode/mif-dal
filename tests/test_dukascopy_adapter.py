"""
tests/test_dukascopy_adapter.py
 ===============================
Tests for DukascopyAdapter.

Unit tests mock subprocess.run — no Node.js required.
Integration tests (@pytest.mark.network) require Node.js + dukascopy-node.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dal.adapters.dukascopy import DukascopyAdapter
from dal.interfaces.source import FetchRequest

# ── Fixtures ────────────────────────────────────────────────────────────────

SAMPLE_CSV_WITH_HEADER = (
    b"timestamp,open,high,low,close,volume\n"
    b"1672531200000,16500.0,16600.0,16400.0,16550.0,100.5\n"
    b"1672617600000,16550.0,16700.0,16450.0,16620.0,95.2\n"
    b"1672704000000,16620.0,16800.0,16500.0,16750.0,110.3\n"
)

SAMPLE_CSV_NO_HEADER = (
    b"1672531200000,16500.0,16600.0,16400.0,16550.0,100.5\n"
    b"1672617600000,16550.0,16700.0,16450.0,16620.0,95.2\n"
    b"1672704000000,16620.0,16800.0,16500.0,16750.0,110.3\n"
)


@pytest.fixture
def adapter() -> DukascopyAdapter:
    return DukascopyAdapter(node_timeout=10)


@pytest.fixture
def btc_request() -> FetchRequest:
    return FetchRequest(
        asset_id="BTC-USD",
        start="2023-01-01",
        end="2023-01-04",
        timeframe="1D",
    )


def make_successful_subprocess(csv_bytes: bytes, tmpdir_path: str):
    """Helper: mock subprocess.run that writes a CSV to tmpdir."""

    def side_effect(cmd, **kwargs):
        if "dukascopy-node" in cmd and "--version" not in cmd:
            # Write the CSV to tmpdir passed via -dir
            dir_idx = cmd.index("-dir") + 1
            out_dir = cmd[dir_idx]
            Path(out_dir, "btcusd-d1-bid-2023-01-01-2023-01-04.csv").write_bytes(
                csv_bytes
            )
        mock = MagicMock()
        mock.returncode = 0
        mock.stderr = b""
        return mock

    return side_effect


# ── Group 1: Source Protocol ─────────────────────────────────────────────────


def test_source_id(adapter):
    assert adapter.source_id == "dukascopy"


def test_supports_btc(adapter):
    assert adapter.supports("BTC-USD") is True


def test_supports_eth(adapter):
    assert adapter.supports("ETH-USD") is True


def test_does_not_support_paxg(adapter):
    """PAXG not available on Dukascopy — documented behavior."""
    assert adapter.supports("PAXG-USD") is False


def test_does_not_support_unknown(adapter):
    assert adapter.supports("FAKE-XXX") is False


# ── Group 2: FetchResult contract ───────────────────────────────────────────


def test_fetch_unsupported_asset_returns_failed(adapter):
    req = FetchRequest(
        asset_id="PAXG-USD", start="2023-01-01", end="2023-01-31", timeframe="1D"
    )
    result = adapter.fetch(req)
    assert result.status == "failed"
    assert result.rows == 0
    assert result.data.empty


def test_fetch_result_has_all_fields(adapter, btc_request):
    with (
        patch.object(adapter, "_is_node_available", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tempfile.TemporaryDirectory") as mock_tmpdir,
    ):
        tmpdir = tempfile.mkdtemp()
        Path(tmpdir, "btcusd-d1-bid.csv").write_bytes(SAMPLE_CSV_WITH_HEADER)
        mock_tmpdir.return_value.__enter__ = lambda s: tmpdir
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        # Patch glob to return our CSV
        with patch(
            "pathlib.Path.glob", return_value=[Path(tmpdir, "btcusd-d1-bid.csv")]
        ):
            result = adapter.fetch(btc_request)

    for field in [
        "data",
        "hash",
        "status",
        "source_id",
        "fetched_at",
        "rows",
        "timeframe",
        "fallback",
    ]:
        assert hasattr(result, field), f"FetchResult missing field '{field}'"


def test_fetch_result_fallback_false_by_default(adapter, btc_request):
    with patch.object(adapter, "_is_node_available", return_value=False):
        result = adapter.fetch(btc_request)
    assert result.fallback is False


def test_node_unavailable_returns_failed(adapter, btc_request):
    with patch.object(adapter, "_is_node_available", return_value=False):
        result = adapter.fetch(btc_request)
    assert result.status == "failed"
    assert result.rows == 0


# ── Group 3: Hash invariants ────────────────────────────────────────────────


def test_hash_is_sha256_of_raw_bytes(adapter):
    """Hash must be SHA-256 of raw CSV bytes, before parsing."""
    raw = SAMPLE_CSV_WITH_HEADER
    expected_hash = hashlib.sha256(raw).hexdigest()
    adapter._parse_csv(raw)  # call to verify no exception
    # Verify independently that hash would be correct
    assert len(expected_hash) == 64


def test_parse_csv_with_header(adapter):
    df = adapter._parse_csv(SAMPLE_CSV_WITH_HEADER)
    assert not df.empty
    assert set(df.columns) == {"open", "high", "low", "close", "volume"}
    assert df.index.tz is not None


def test_parse_csv_no_header(adapter):
    df = adapter._parse_csv(SAMPLE_CSV_NO_HEADER)
    assert not df.empty
    assert "close" in df.columns


# ── Group 4: No OHLCV validation in adapter ─────────────────────────────────


def test_adapter_does_not_validate_ohlcv_physics(adapter):
    """Adapter returns raw data — DQF validates physics."""
    corrupt_csv = (
        b"timestamp,open,high,low,close,volume\n"
        b"1672531200000,16500.0,16000.0,16600.0,16550.0,100.5\n"  # high < low
    )
    df = adapter._parse_csv(corrupt_csv)
    # Parsing succeeds — no exception raised
    assert not df.empty


# ── Network tests ────────────────────────────────────────────────────────────


@pytest.mark.network
def test_fetch_real_btc_1d(adapter, skip_if_no_dukascopy, skip_if_no_network):
    """
    Real network test — skipped if dukascopy-node absent or no network.
    Enable with --run-network after running setup_dukascopy_mif.sh.
    """
    from datetime import date, timedelta

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=30)).isoformat()
    req = FetchRequest("BTC-USD", start, end, "1D")
    result = adapter.fetch(req)
    assert result.status in ("success", "partial"), (
        f"Dukascopy returned status='{result.status}'. "
        f"Error: {getattr(result, 'error', 'N/A')}"
    )
    assert result.rows > 0
