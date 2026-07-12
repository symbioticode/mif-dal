# API Reference — mif-dal v0.1.0

## DAL

The main entry point.

```python
from dal import DAL, DALConfig

config = DALConfig()
dal = DAL(config)
```

### `DAL.get_certified_stream()`

Assembles a stream with full DQF certification. Use for reproducible,
production-grade data retrieval.

```python
handoff = dal.get_certified_stream(
    asset_id: str,
    source_preference: list[str],
    start: str,              # "YYYY-MM-DD"
    end: str,                # "YYYY-MM-DD"
    calendar: str,           # mandatory — "CRYPTO_247" | "NYSE" | "FOREX_24_5"
    dqf_version_target: str, # minimum mif-dqf version, e.g. "1.2.0"
) -> DALHandoff
```

**Raises:**

| Exception | Condition |
|---|---|
| `DALConfigError` | `calendar` missing or invalid before any network call |
| `DALVersionError` | Installed mif-dqf < `dqf_version_target` |
| `DALHandoffError` | DQF returned VOID, or all sources failed |

### `DAL.get_diagnostic_stream()`

Assembles a stream in diagnostic mode. DQF result is informational only.
Use for data exploration and debugging.

```python
handoff = dal.get_diagnostic_stream(
    asset_id: str,
    source_preference: list[str],
    start: str,
    end: str,
    calendar: str,           # required even in diagnostic (DALHandoff invariant)
    dqf_version_target: str = "",
) -> DALHandoff
```

Always returns a `DALHandoff`. Does not raise on DQF WARNING or VOID —
the DQF result is available in `handoff.dqf_report`.

---

## DALConfig

```python
from dal import DALConfig

config = DALConfig(
    cache_dir: str = ".dal_cache",   # local cache directory (optional)
    request_timeout: int = 30,       # seconds per source request
)
```

---

## DALHandoff

Immutable transfer object. `frozen=True` — cannot be mutated after emission.

```python
@dataclass(frozen=True)
class DALHandoff:
    stream: pd.DataFrame        # OHLCV, UTC DatetimeIndex, no NaN, sorted asc
    asset_id: str
    calendar: str
    assembly_hash: str          # SHA-256 hex (64 chars) of raw bytes
    handoff_timestamp: datetime # UTC
    dal_version: str
    source_manifest: tuple      # tuple[dict] — immutable, see schema below
    coverage: str               # "FULL" | "PARTIAL" | "DEGRADED"
    truncated_days: int         # 0 if FULL
    dqf_status: str             # "PASS" | "WARNING"
    dqf_mpi: float              # MIF Purity Index 0–100
    dqf_version: str
    dqf_version_target: str
    dqf_report: DQFReport
    aqi: float                  # Assembly Quality Index 0–100
```

### `stream` contract

- `DatetimeIndex`, timezone-aware UTC
- Columns: `open`, `high`, `low`, `close`, `volume` (all `float64`)
- No `NaN` values (mif-dqf has cleaned)
- Sorted ascending, no duplicate index entries

### `source_manifest` schema

Each entry in `source_manifest` is a dict:

```python
{
    "source_id": str,       # "kraken" | "yahoo" | "dukascopy" | "in_memory"
    "status": str,          # "success" | "partial" | "failed"
    "hash": str,            # SHA-256 of raw bytes from this source
    "fetched_at": datetime, # UTC
    "rows": int,
    "timeframe": str,       # "1D"
    "fallback": bool,       # True if this was not the first choice
}
```

### `assembly_hash` semantics

The `assembly_hash` is computed on raw OHLCV bytes **before** calendar
alignment, forward-fill, or any other transformation (D-DAL-006).

```python
raw_bytes = raw_dataframe.to_parquet()  # deterministic
assembly_hash = hashlib.sha256(raw_bytes).hexdigest()
```

Two calls with the same asset, date range, and source produce the same hash.
If a fallback source is used, the hash differs — this is intentional and
auditable via `source_manifest`.

---

## Exceptions

```python
from dal.exceptions import DALError, DALConfigError, DALVersionError, DALHandoffError

class DALError(Exception):
    """Base class for all mif-dal exceptions."""

class DALConfigError(DALError):
    """Invalid or missing configuration before any network call.
    Example: calendar omitted in get_certified_stream()."""

class DALVersionError(DALError):
    """Installed mif-dqf < dqf_version_target.
    Attributes: installed_version, required_version."""

class DALHandoffError(DALError):
    """Handoff could not be emitted.
    Attributes:
        reason: "DQF_VOID" | "ALL_SOURCES_FAILED" | "DQF_UNEXPECTED_STATUS"
        dqf_report: DQFReport | None
        source_failures: list[dict] | None"""
```

---

## Source Adapters

### KrakenAdapter

```python
from dal.adapters.kraken import KrakenAdapter
```

- Crypto pairs (e.g. `PAXG-USD`, `BTC-USD`, `ETH-USD`)
- Data available approximately last 12 months (Kraken API limit)
- PAXG-USD may be unavailable in some regions → Yahoo fallback

### YahooAdapter

```python
from dal.adapters.yahoo import YahooAdapter
```

- Equities, ETFs, crypto — broad coverage
- Requires `yfinance >= 1.3.0, < 2.0.0`
- Quality varies by asset and date range

### DukascopyAdapter

```python
from dal.adapters.dukascopy import DukascopyAdapter
```

- Forex pairs and crypto
- Requires Node.js and `dukascopy-node` installed globally
- Detected via `dukascopy-node --help` at runtime; tests skip if absent

### InMemorySource

For testing and research — pass a dict of DataFrames:

```python
from dal.adapters.in_memory import InMemorySource
from dal.interfaces.source import FetchRequest

source = InMemorySource({"TEST-USD": df})
req = FetchRequest(asset_id="TEST-USD", start="2024-01-01",
                   end="2024-12-31", timeframe="1D", calendar="NYSE")
result = source.fetch(req)
```

---

## Assembly Quality Index (AQI)

```
AQI = max(0, 100 × (1 − Σ gravity_i))
```

| Intervention | Gravity |
|---|---|
| Source fallback triggered | 0.20 |
| Retry required | 0.05 per retry |
| Date range truncated (start) | 0.10 |
| Date range truncated (end) | 0.10 |
| Coverage DEGRADED (< 80%) | 0.30 |

AQI is on the D-SIG Standard v0.5 §3.3 scale (0–100).
Combined data quality score for D-SIG: `0.60 × dqf_mpi + 0.40 × aqi`.

---

## Calendars

| Value | Market | Trading days |
|---|---|---|
| `CRYPTO_247` | Cryptocurrency | 24/7, 365 days |
| `NYSE` | US equities | Mon–Fri, US holidays excluded |
| `FOREX_24_5` | Foreign exchange | Mon–Fri, continuous |
