# ISSUE-DAL-P3-001: Kraken Adapter Returns No Data for Historical Date Ranges

## Problem Description
The KrakenAdapter in MIF-DAL is returning empty DataFrames (0 rows) for historical date ranges, even though the Kraken API does return data. This affects integration tests that rely on fetching historical BTC-USD data from Kraken.

## Observed Behavior
- When requesting BTC-USD data for 2024-01-01 to 2024-01-07, KrakenAdapter returns status='failed' with 0 rows
- Direct API calls to Kraken show that data IS available, but it's for much more recent dates (May 2024 - May 2026)
- The Kraken API appears to only return the most recent 720 candles when using the 'since' parameter
- Our adapter is not correctly handling the case where requested historical dates are outside the available range

## Test Results
### Working Case (Recent Dates)
```python
req = FetchRequest(asset_id='BTC-USD', start='2024-05-20', end='2024-05-22', timeframe='1D')
# Result: Status=success, Rows=3
```

### Failing Case (Historical Dates)
```python
req = FetchRequest(asset_id='BTC-USD', start='2024-01-01', end='2024-01-07', timeframe='1D')
# Result: Status=failed, Rows=0
```

### Direct API Investigation
- Requesting since=1704067200 (2024-01-01) returns 721 candles from 2024-05-20 to 2026-05-10
- Requesting since=0 (earliest possible) returns 721 candles from 2024-05-20 to 2026-05-10
- This indicates Kraken only stores approximately 2 years of daily OHLCV data

## Root Cause Analysis
1. **Kraken API Limitation**: The OHLC endpoint only returns the most recent 720 candles (~2 years of daily data)
2. **Adapter Logic**: Our adapter was attempting to paginate backward in time using the 'since' parameter, but Kraken's API works differently:
   - When using 'since', Kraken returns candles NEWER than the specified timestamp
   - To get older data, we would need a different approach (which isn't available in the public API)
3. **Date Range Mismatch**: When requesting historical dates outside Kraken's available window, we get no overlapping data

## Current Blockers
The integration tests are failing because:
1. `test_fallback_chain_when_all_but_one_fail` - Mocks Yahoo and Dukascopy as failed, expects Kraken to succeed
2. `test_all_sources_return_consistent_data_for_btc` - Compares data from Yahoo, Kraken, and Dukascopy

Both tests use historical date ranges (2024-01-01 to 2024-01-03 or 2024-01-07) that fall outside Kraken's available data window.

## Proposed Solutions
1. **Adjust Test Date Ranges**: Use more recent dates that fall within Kraken's available data window
2. **Enhanced Adapter Logic**: Detect when requested dates are outside available range and return appropriate status
3. **Document Limitation**: Clearly document Kraken's 2-year data limitation in the adapter

## Recommended Immediate Action
For the Phase 3 deliverables, I recommend adjusting the integration test date ranges to use recent dates (e.g., 2024-06-01 to 2024-06-07) that are known to be available in Kraken's API, while documenting this limitation appropriately.

## Work Completed
- Updated integration tests to use date ranges that work with Kraken's API (June 2024)
- Fixed Kraken adapter to properly handle cases where requested date ranges don't overlap with available data
- Resolved test indentation issues in test_integration.py
- Updated halo/anamnese_state.yaml to reflect current test status

## Files to Review
- `dal/adapters/kraken.py` - The adapter implementation
- `tests/test_integration.py` - The failing integration tests
- `docs/kb/kb_kraken_bitget.md` - Existing Kraken documentation

## Expected Outcome
Integration tests should pass with appropriate date ranges that work with Kraken's API limitations, while maintaining the adapter's correctness for other use cases.
