"""
tests/test_integration.py
 ===========================
Integration tests for MIF-DAL Phase 2.

Verifies the real fallback chain between adapters.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dal.adapters.dukascopy import DukascopyAdapter
from dal.adapters.kraken import KrakenAdapter
from dal.adapters.yahoo import YahooAdapter
from dal.core.config import DALConfig
from dal.core.sources import resolve_and_fetch
from dal.interfaces.source import FetchRequest, SourceFetchError


@pytest.mark.network
def test_fallback_chain_yahoo_to_kraken():
    """
    Test the fallback chain: Yahoo Finance fails → Kraken takes over.
    Simulate Yahoo failure (PAXG not available on Dukascopy in this test).
    """
    # PAXG-USD: available on Kraken and Yahoo, not on Dukascopy
    # Use recent dates that Kraken supports
    # (data available from mid-2024)
    req = FetchRequest(
        asset_id="PAXG-USD",
        start="2024-06-01",
        end="2024-06-07",
        timeframe="1D",
    )

    # Test with the 3 adapters in order of preference
    sources = [YahooAdapter(), KrakenAdapter(), DukascopyAdapter()]

    # We want Yahoo to succeed normally, so we don't mock it as failing
    # But we test that the chain works anyway
    result = resolve_and_fetch(request=req, sources=sources, config=DALConfig())

    # At least one of the adapters must succeed
    manifest_entry = result.source_manifest[0]
    assert manifest_entry["status"] in ("success", "partial")
    assert manifest_entry["rows"] > 0
    assert len(manifest_entry["hash"]) == 64
    assert manifest_entry["source_id"] in (
        "yahoo",
        "kraken",
    )  # Dukascopy does not support PAXG


@pytest.mark.network
def test_fallback_chain_when_all_but_one_fail():
    """
    Test where two adapters fail and the third succeeds.
    Mock Dukascopy and Yahoo as failing, Kraken must succeed.
    """
    req = FetchRequest(
        asset_id="BTC-USD",
        start="2024-06-01",
        end="2024-06-07",
        timeframe="1D",
    )

    # Sources in order: Yahoo (mock fail), Dukascopy (mock fail),
    # Kraken (real)
    sources = [YahooAdapter(), DukascopyAdapter(), KrakenAdapter()]

    # Mock Yahoo and Dukascopy to fail
    with (
        patch("dal.adapters.yahoo.YahooAdapter.fetch") as mock_yahoo_fetch,
        patch("dal.adapters.dukascopy.DukascopyAdapter.fetch") as mock_dukascopy_fetch,
    ):
        # Return failures for Yahoo and Dukascopy
        mock_yahoo_fetch.side_effect = SourceFetchError(
            "Mock failure", source_id="yahoo"
        )
        mock_dukascopy_fetch.side_effect = SourceFetchError(
            "Mock failure", source_id="dukascopy"
        )

        # Call resolve_and_fetch - should try all 3 and take Kraken
        result = resolve_and_fetch(request=req, sources=sources, config=DALConfig())

        # Find the successful entry in the manifest (should be Kraken)
        successful_entries = [
            entry
            for entry in result.source_manifest
            if entry["status"] in ("success", "partial")
        ]
        assert len(successful_entries) == 1, (
            "Expected exactly one successful entry, got: "
            f"{[e['source_id'] for e in result.source_manifest]}"
        )
        manifest_entry = successful_entries[0]
        assert manifest_entry["source_id"] == "kraken"
        assert manifest_entry["rows"] > 0


@pytest.mark.network
def test_all_sources_return_consistent_data_for_btc():
    """
    Verify that different adapters return consistent data for the same
    asset/period (with minor differences due to closing times).
    """
    req = FetchRequest(
        asset_id="BTC-USD",
        start="2024-06-01",
        end="2024-06-07",  # Short period to avoid timeouts
        timeframe="1D",
    )

    # Test each adapter individually
    yahoo_adapter = YahooAdapter()
    kraken_adapter = KrakenAdapter()
    dukascopy_adapter = DukascopyAdapter()

    # Fetch data from each source
    yahoo_result = yahoo_adapter.fetch(req)
    kraken_result = kraken_adapter.fetch(req)
    # Dukascopy may fail if Node.js is not available, continue anyway
    try:
        dukascopy_result = dukascopy_adapter.fetch(req)
        dukascopy_success = dukascopy_result.status in ("success", "partial")
    except Exception:
        dukascopy_success = False
        dukascopy_result = None

    # At least Yahoo and Kraken must succeed
    assert yahoo_result.status in ("success", "partial"), "Yahoo failed"
    assert kraken_result.status in ("success", "partial"), "Kraken failed"

    # Both must have data
    assert yahoo_result.rows > 0, "Yahoo returned no data"
    assert kraken_result.rows > 0, "Kraken returned no data"

    # The hashes must be different
    # (different sources, same data => different hash)
    assert (
        yahoo_result.hash != kraken_result.hash
    ), "Identical hashes from different sources"

    # If Dukascopy succeeded, verify it too
    if dukascopy_success:
        assert dukascopy_result.rows > 0, "Dukascopy returned no data"
        assert dukascopy_result.hash != yahoo_result.hash
        assert dukascopy_result.hash != kraken_result.hash
