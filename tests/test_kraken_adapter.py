"""
tests/test_kraken_adapter.py
 ============================
Tests for KrakenAdapter.

Structure:
- Unit tests (no network): mock requests.get
- Network integration tests: @pytest.mark.network (skip in CI)

Convention: unit tests verify the Source Protocol contract,
not Kraken's internal implementation.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dal.adapters.kraken import KrakenAdapter
from dal.interfaces.source import FetchRequest

# ── Fixtures ────────────────────────────────────────────────────────────────

SAMPLE_OHLC = [
    [1672531200, "16500.0", "16600.0", "16400.0", "16550.0", "16525.0", "100.5", 42],
    [1672617600, "16550.0", "16700.0", "16450.0", "16620.0", "16580.0", "95.2", 38],
    [1672704000, "16620.0", "16800.0", "16500.0", "16750.0", "16680.0", "110.3", 51],
]

KRAKEN_RESPONSE = {
    "error": [],
    "result": {
        "XXBTZUSD": SAMPLE_OHLC,
        "last": 1672704000,
    },
}


def make_mock_response(data: dict) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = data
    mock.content = json.dumps(data).encode()
    return mock


@pytest.fixture
def adapter() -> KrakenAdapter:
    return KrakenAdapter(request_timeout=10, rate_limit_delay=0.0)


@pytest.fixture
def btc_request() -> FetchRequest:
    return FetchRequest(
        asset_id="BTC-USD",
        start="2023-01-01",
        end="2023-01-04",
        timeframe="1D",
    )


# ── Group 1: Source Protocol ────────────────────────────────────────────────


def test_source_id(adapter):
    assert adapter.source_id == "kraken"
    assert isinstance(adapter.source_id, str)
    assert len(adapter.source_id) > 0


def test_supports_known_assets(adapter):
    assert adapter.supports("BTC-USD") is True
    assert adapter.supports("ETH-USD") is True
    assert adapter.supports("PAXG-USD") is True


def test_supports_unknown_asset(adapter):
    assert adapter.supports("INVALID-XYZ") is False
    assert adapter.supports("") is False


# ── Group 2: FetchResult contract ──────────────────────────────────────────


def test_fetch_returns_fetchresult(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert result is not None
    assert result.source_id == "kraken"
    assert result.timeframe == "1D"
    assert isinstance(result.fetched_at, datetime)
    assert result.fetched_at.tzinfo is not None  # timezone-aware


def test_fetch_result_hash_is_sha256(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert len(result.hash) == 64, f"SHA-256 = 64 hex chars, got {len(result.hash)}"
    # Verify that it is valid hex
    int(result.hash, 16)


def test_fetch_result_has_all_required_fields(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert hasattr(result, "data")
    assert hasattr(result, "hash")
    assert hasattr(result, "status")
    assert hasattr(result, "source_id")
    assert hasattr(result, "fetched_at")
    assert hasattr(result, "rows")
    assert hasattr(result, "timeframe")
    assert hasattr(result, "fallback")


def test_fetch_result_fallback_is_false_by_default(adapter, btc_request):
    """fallback=False by default — the resolver sets it to True if necessary."""
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)
    assert result.fallback is False


# ── Group 3: DataFrame OHLCV ────────────────────────────────────────────────


def test_fetch_data_has_ohlcv_columns(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    required = {"open", "high", "low", "close", "volume"}
    assert required.issubset(set(result.data.columns))


def test_fetch_data_index_is_utc(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert result.data.index.tz is not None
    assert str(result.data.index.tz) == "UTC"


def test_fetch_data_no_nan(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert not result.data.isnull().any().any()


def test_fetch_data_rows_matches_result_rows(adapter, btc_request):
    with patch("requests.get", return_value=make_mock_response(KRAKEN_RESPONSE)):
        result = adapter.fetch(btc_request)

    assert result.rows == len(result.data)


# ── Group 4: Reproducibility (invariant D-DAL-006) ────────────────────────


def test_same_data_same_hash(adapter, btc_request):
    """Two identical calls → same hash."""
    mock = make_mock_response(KRAKEN_RESPONSE)
    with patch("requests.get", return_value=mock):
        r1 = adapter.fetch(btc_request)
    with patch("requests.get", return_value=mock):
        r2 = adapter.fetch(btc_request)

    assert r1.hash == r2.hash, "Reproducibility violated: same data → different hashes"


def test_different_data_different_hash(adapter):
    """Different data → different hashes."""
    response_a = {
        "error": [],
        "result": {"XXBTZUSD": SAMPLE_OHLC[:2], "last": 1672617600},
    }
    response_b = {
        "error": [],
        "result": {
            "XXBTZUSD": [
                [
                    1672531200,
                    "20000.0",
                    "20100.0",
                    "19900.0",
                    "20050.0",
                    "20000.0",
                    "50.0",
                    10,
                ],
            ],
            "last": 1672531200,
        },
    }
    req = FetchRequest(
        asset_id="BTC-USD", start="2023-01-01", end="2023-01-03", timeframe="1D"
    )

    with patch("requests.get", return_value=make_mock_response(response_a)):
        r1 = adapter.fetch(req)
    with patch("requests.get", return_value=make_mock_response(response_b)):
        r2 = adapter.fetch(req)

    assert r1.hash != r2.hash


# ── Group 5: Edge cases ────────────────────────────────────────────────────


def test_unsupported_asset_returns_failed_status(adapter):
    req = FetchRequest(
        asset_id="INVALID-XYZ", start="2023-01-01", end="2023-01-31", timeframe="1D"
    )
    result = adapter.fetch(req)
    assert result.status == "failed"
    assert result.rows == 0
    assert result.data.empty


def test_unsupported_timeframe_returns_failed_status(adapter):
    req = FetchRequest(
        asset_id="BTC-USD", start="2023-01-01", end="2023-01-31", timeframe="3M"
    )
    result = adapter.fetch(req)
    assert result.status == "failed"


def test_api_error_raises_runtime_error(adapter, btc_request):
    error_response = {"error": ["EQuery:Unknown asset pair"], "result": {}}
    with pytest.raises(RuntimeError, match="Kraken API error"):
        with patch("requests.get", return_value=make_mock_response(error_response)):
            adapter.fetch(btc_request)


def test_kraken_adapter_does_not_validate_ohlcv_physics(adapter, btc_request):
    """
    The adapter does not validate OHLCV physics. DQF does that.
    This test documents the expected behavior: invalid data passes
    through the adapter and is captured by DQF downstream.
    """
    corrupt_ohlc = [
        # high < low — physically invalid, but adapter returns anyway
        [
            1672531200,
            "16500.0",
            "16000.0",
            "16600.0",
            "16550.0",
            "16525.0",
            "100.5",
            42,
        ],
    ]
    corrupt_response = {
        "error": [],
        "result": {"XXBTZUSD": corrupt_ohlc, "last": 1672531200},
    }
    with patch("requests.get", return_value=make_mock_response(corrupt_response)):
        result = adapter.fetch(btc_request)
    # The adapter does NOT raise an exception — it returns raw data
    # DQF will detect the anomaly via C2 (OHLCV Physics)
    assert result.status in ("success", "partial")
    assert not result.data.empty


# ── Group 6: Network integration tests ────────────────────────────────────


@pytest.mark.network
def test_fetch_real_btc_usd(adapter, skip_if_no_network):
    """Real network test — skipped by default, enable with --run-network."""
    from datetime import date, timedelta

    # Use a recent period guaranteed to have data
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=30)).isoformat()
    req = FetchRequest("BTC-USD", start, end, "1D")
    result = adapter.fetch(req)
    # Kraken may return partial if data is recent
    assert result.status in ("success", "partial"), (
        f"Kraken returned status='{result.status}'. "
        f"Error: {getattr(result, 'error', 'N/A')}"
    )
    assert result.rows > 0, (
        f"Kraken returned 0 rows for BTC-USD {start}→{end}. "
        "Check network connectivity."
    )


@pytest.mark.network
def test_fetch_real_paxg_usd(adapter, skip_if_no_network):
    """PAXG-USD is the central pair for QAAF Studio — verify availability."""
    from datetime import date, timedelta

    # Use a recent period guaranteed to have data
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=30)).isoformat()
    req = FetchRequest("PAXG-USD", start, end, "1D")
    result = adapter.fetch(req)
    assert result.status in (
        "success",
        "partial",
    ), f"PAXG-USD unavailable on Kraken: {getattr(result, 'error', 'unknown')}"
    assert result.rows > 0, (
        f"Kraken returned 0 rows for PAXG-USD {start}→{end}. "
        "Check network connectivity."
    )
