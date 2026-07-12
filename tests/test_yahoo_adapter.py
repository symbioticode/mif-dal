"""
tests/test_yahoo_adapter.py
 ===========================
Tests for YahooAdapter.

Unit tests mock yfinance and requests.
Integration tests (@pytest.mark.network) require internet connection.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from dal.adapters.yahoo import YahooAdapter
from dal.interfaces.source import FetchRequest

# ── Fixtures ────────────────────────────────────────────────────────────────

SAMPLE_OHLC_DATA = pd.DataFrame(
    {
        "open": [16500.0] * 35,
        "high": [16600.0] * 35,
        "low": [16400.0] * 35,
        "close": [16550.0] * 35,
        "volume": [100.5] * 35,
    },
    index=pd.to_datetime(
        [
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
            "2023-01-07",
            "2023-01-08",
            "2023-01-09",
            "2023-01-10",
            "2023-01-11",
            "2023-01-12",
            "2023-01-13",
            "2023-01-14",
            "2023-01-15",
            "2023-01-16",
            "2023-01-17",
            "2023-01-18",
            "2023-01-19",
            "2023-01-20",
            "2023-01-21",
            "2023-01-22",
            "2023-01-23",
            "2023-01-24",
            "2023-01-25",
            "2023-01-26",
            "2023-01-27",
            "2023-01-28",
            "2023-01-29",
            "2023-01-30",
            "2023-01-31",
            "2023-02-01",
            "2023-02-02",
            "2023-02-03",
            "2023-02-04",
        ],
        utc=True,
    ),
)

SAMPLE_OHLC_DATA_MULTIINDEX = SAMPLE_OHLC_DATA.copy()
SAMPLE_OHLC_DATA_MULTIINDEX.columns = pd.MultiIndex.from_tuples(
    [
        ("Open", "BTC-USD"),
        ("High", "BTC-USD"),
        ("Low", "BTC-USD"),
        ("Close", "BTC-USD"),
        ("Volume", "BTC-USD"),
    ]
)


@pytest.fixture
def adapter() -> YahooAdapter:
    return YahooAdapter(request_timeout=10)


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
    assert adapter.source_id == "yahoo"


def test_supports_btc(adapter):
    assert adapter.supports("BTC-USD") is True


def test_supports_eth(adapter):
    assert adapter.supports("ETH-USD") is True


def test_supports_paxg(adapter):
    """PAXG is available on Yahoo Finance."""
    assert adapter.supports("PAXG-USD") is True


def test_does_not_support_unknown(adapter):
    assert adapter.supports("FAKE-XXX") is False


# ── Group 2: FetchResult contract ──────────────────────────────────────────


def test_fetch_returns_fetchresult(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    assert result is not None
    assert result.source_id == "yahoo"
    assert result.timeframe == "1D"
    assert isinstance(result.fetched_at, pd.Timestamp) or hasattr(
        result.fetched_at, "tzinfo"
    )


def test_fetch_result_hash_is_sha256(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    assert len(result.hash) == 64, f"SHA-256 = 64 hex chars, got {len(result.hash)}"
    # Verify it is valid hex
    int(result.hash, 16)


def test_fetch_result_has_all_required_fields(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
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
    """fallback=False by default — resolver sets it to True if needed."""
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)
    assert result.fallback is False


# ── Group 3: DataFrame OHLCV ────────────────────────────────────────────────


def test_fetch_data_has_ohlcv_columns(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    required = {"open", "high", "low", "close", "volume"}
    assert required.issubset(set(result.data.columns))


def test_fetch_data_index_is_utc(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    assert result.data.index.tz is not None
    assert str(result.data.index.tz) == "UTC"


def test_fetch_data_no_nan(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    assert not result.data.isnull().any().any()


def test_fetch_data_rows_matches_result_rows(adapter, btc_request):
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        result = adapter.fetch(btc_request)

    assert result.rows == len(result.data)


def test_fetch_data_handles_multiindex_columns(adapter, btc_request):
    """Test critical handling of MultiIndex from yfinance 1.3.0+."""
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA_MULTIINDEX
        result = adapter.fetch(btc_request)

    # Columns must be normalized to lowercase without MultiIndex
    assert not isinstance(result.data.columns, pd.MultiIndex)
    expected_cols = {"open", "high", "low", "close", "volume"}
    assert set(result.data.columns) == expected_cols
    assert not result.data.empty


# ── Group 4: Reproducibility (invariant D-DAL-006) ────────────────────────


def test_same_data_same_hash(adapter, btc_request):
    """Two identical calls → same hash."""
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        r1 = adapter.fetch(btc_request)
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = SAMPLE_OHLC_DATA
        r2 = adapter.fetch(btc_request)

    assert (
        r1.hash == r2.hash
    ), "Reproducibility violated: identical data → different hashes"


def test_different_data_different_hash_mocked(adapter):
    """
    Verify that two different DataFrames produce different hashes.
    Pure unit test — no network call.
    """
    from unittest.mock import patch

    import pandas as pd

    idx = pd.date_range("2023-01-01", periods=10, freq="D", tz="UTC")

    df_btc = pd.DataFrame(
        {
            "open": [40000.0 + i for i in range(10)],
            "high": [41000.0 + i for i in range(10)],
            "low": [39000.0 + i for i in range(10)],
            "close": [40500.0 + i for i in range(10)],
            "volume": [1000.0] * 10,
        },
        index=idx,
    )

    df_paxg = pd.DataFrame(
        {
            "open": [1800.0 + i for i in range(10)],
            "high": [1810.0 + i for i in range(10)],
            "low": [1790.0 + i for i in range(10)],
            "close": [1805.0 + i for i in range(10)],
            "volume": [500.0] * 10,
        },
        index=idx,
    )

    req_btc = FetchRequest("BTC-USD", "2023-01-01", "2023-01-10", "1D")
    req_paxg = FetchRequest("PAXG-USD", "2023-01-01", "2023-01-10", "1D")

    with patch("yfinance.download") as mock_download:
        mock_download.return_value = df_btc
        r1 = adapter.fetch(req_btc)

    with patch("yfinance.download") as mock_download:
        mock_download.return_value = df_paxg
        r2 = adapter.fetch(req_paxg)

    assert r1.hash != r2.hash, (
        "BTC and PAXG have same hash — different data must produce "
        "different hashes (fundamental DAL reproducibility invariant)."
    )
    assert r1.rows == 10
    assert r2.rows == 10


# ── Group 5: Fallback and limits ────────────────────────────────────────────


def test_fallback_when_yfinance_returns_few_rows(adapter, btc_request):
    """When yfinance returns < 30 rows, fallback must be used."""
    small_df = SAMPLE_OHLC_DATA.iloc[:2]  # Only 2 rows

    with (
        patch("yfinance.download") as mock_yf,
        patch.object(adapter, "_fallback_fetch") as mock_fallback,
    ):
        mock_yf.return_value = small_df
        # Fallback returns normal data
        mock_fallback.return_value = SAMPLE_OHLC_DATA

        result = adapter.fetch(btc_request)

        # Verify fallback was called
        mock_fallback.assert_called_once()
        # And that fallback was used
        assert result.fallback is True


def test_fallback_disabled_returns_data_on_few_rows(adapter, btc_request):
    """When fallback is disabled and few rows are returned,
    return available data."""
    adapter_no_fallback = YahooAdapter(fallback_enabled=False)
    small_df = SAMPLE_OHLC_DATA.iloc[:2]  # Only 2 rows

    with patch("yfinance.download") as mock_yf:
        mock_yf.return_value = small_df
        result = adapter_no_fallback.fetch(btc_request)

    # When fallback is disabled, return available data even if few
    assert result.status == "success"
    assert result.rows == 2
    assert not result.data.empty


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


# ── Group 6: Network integration tests ──────────────────────────────────────


@pytest.mark.network
def test_fetch_real_btc_usd(adapter, skip_if_no_network):
    """
    Network integration test — skip in CI, run locally only.
    Verify adapter works against real Yahoo Finance.
    """
    adapter = YahooAdapter()
    req = FetchRequest(
        asset_id="BTC-USD",
        start="2024-01-01",
        end="2024-01-07",
        timeframe="1D",
    )
    result = adapter.fetch(req)

    assert result.status in ("success", "partial")
    assert result.rows > 0
    assert len(result.hash) == 64
    assert not result.data.empty
    assert result.data.index.tz is not None


@pytest.mark.network
@pytest.mark.network
def test_fetch_real_paxg_usd(adapter, skip_if_no_network):
    """PAXG-USD must be available on Yahoo Finance."""
    adapter = YahooAdapter()
    req = FetchRequest(
        asset_id="PAXG-USD",
        start="2024-01-01",
        end="2024-01-07",
        timeframe="1D",
    )
    result = adapter.fetch(req)
    assert result.status in ("success", "partial"), (
        "PAXG-USD unavailable on Yahoo Finance: "
        f"{getattr(result, 'error', 'unknown')}"
    )
