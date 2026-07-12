# MIF-DAL — Data Abstraction Layer

[![tests](https://img.shields.io/badge/tests-169%2F169%20passing-brightgreen)](https://github.com/symbioticode/mif-dal/actions)
[![version](https://img.shields.io/badge/version-0.1.0-blue)](https://pypi.org/project/mif-dal/)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/mif-dal/)
[![license](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

**mif-dal** is the data assembly layer of the [MIF ecosystem](#the-mif-ecosystem).
It fetches OHLCV market data from external sources, certifies it through
[mif-dqf](https://github.com/symbioticode/mif-dqf), and delivers an immutable,
hash-anchored result ready for metric computation.

---

## Why mif-dal?

Quantitative research fails silently when its data foundation is uncertain.
A strategy that looks profitable on Yahoo Finance data may behave differently
on Kraken data — same asset, different gaps, different fills, different hashes.

**mif-dal makes data provenance explicit and mandatory:**

- Every stream carries a `assembly_hash` (SHA-256 of raw bytes before any transformation).
  Two calls with the same parameters produce the same hash, or the difference is auditable.
- Physical validity is guaranteed by [mif-dqf](https://github.com/symbioticode/mif-dqf)
  before any data reaches your computation layer.
- Source fallback is recorded, not hidden. If Kraken was unavailable and Yahoo
  was used instead, that decision is in the `source_manifest`.
- The output — `DALHandoff` — is frozen. It cannot be mutated after emission.

---

## The MIF Ecosystem

```
External data sources
        ↓
[mif-dal]   assembles stream, computes assembly_hash, delegates to mif-dqf
        ↓ DALHandoff
[mif-dqf]   certifies physical validity (OHLCV physics, calendar, gaps)
        ↓ DQFReport embedded in DALHandoff
[mif-core]  certifies metric/signal integrity (planned)
        ↓ MIFCertification
[QAAF Studio]  research layer (QS-PAF, QS-MÉTIS)
```

**mif-dal sits between your data sources and your computation.**
It does not evaluate strategies. It does not qualify asset pairs.
It answers one question: *"Can I assemble a reproducible, certified OHLCV stream
from available sources for this asset and date range?"*

---

## Installation

```bash
pip install mif-dal
```

Requires Python 3.11+ and `mif-dqf >= 1.2.0` (installed automatically).

### Optional: Dukascopy adapter

The Dukascopy adapter requires Node.js and `dukascopy-node`:

```bash
npm install -g dukascopy-node
```

---

## Quick Start

```python
from dal import DAL, DALConfig

config = DALConfig()
dal = DAL(config)

# One call per asset — caller composes the pair (architectural decision D-DAL-007)
h_paxg = dal.get_certified_stream(
    asset_id="PAXG-USD",
    source_preference=["kraken", "yahoo"],
    start="2024-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

h_btc = dal.get_certified_stream(
    asset_id="BTC-USD",
    source_preference=["kraken", "yahoo"],
    start="2024-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

# Caller constructs the ratio
prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]

print(f"DQF status : {h_paxg.dqf_status} / {h_btc.dqf_status}")
print(f"AQI        : {h_paxg.aqi:.0f} / {h_btc.aqi:.0f}")
print(f"Hash PAXG  : {h_paxg.assembly_hash[:16]}...")
print(f"Hash BTC   : {h_btc.assembly_hash[:16]}...")
```

### Diagnostic mode (exploratory, no version enforcement)

```python
h = dal.get_diagnostic_stream(
    asset_id="BTC-USD",
    source_preference=["yahoo"],
    start="2023-01-01",
    end="2023-12-31",
    calendar="CRYPTO_247",
)
print(h.dqf_report)
```

---

## The DALHandoff Object

Every successful call returns a `DALHandoff` — a frozen dataclass with 15 fields:

| Field | Type | Description |
|---|---|---|
| `stream` | `pd.DataFrame` | OHLCV, UTC DatetimeIndex, no NaN, sorted ascending |
| `asset_id` | `str` | e.g. `"PAXG-USD"` |
| `calendar` | `str` | e.g. `"CRYPTO_247"`, `"NYSE"` |
| `assembly_hash` | `str` | SHA-256 of raw bytes before any transformation |
| `handoff_timestamp` | `datetime` | UTC emission time |
| `dal_version` | `str` | mif-dal package version |
| `source_manifest` | `tuple` | Immutable record of sources used and fallback chain |
| `coverage` | `str` | `FULL` / `PARTIAL` / `DEGRADED` |
| `truncated_days` | `int` | 0 if FULL |
| `dqf_status` | `str` | `PASS` or `WARNING` |
| `dqf_mpi` | `float` | MIF Purity Index 0–100 (from mif-dqf) |
| `dqf_version` | `str` | mif-dqf version used |
| `dqf_version_target` | `str` | Minimum version declared by caller |
| `dqf_report` | `DQFReport` | Full mif-dqf report |
| `aqi` | `float` | Assembly Quality Index 0–100 |

`DALHandoff` is `frozen=True`. It cannot be mutated after emission.

---

## Assembly Quality Index (AQI)

AQI measures how much intervention was required to assemble the stream.
100 = preferred source, full range, no retries. Lower = more intervention.

| AQI | Label | Meaning |
|---|---|---|
| 100 | EXCELLENT | Preferred source, full range, no retries |
| 80–99 | GOOD | Minor fallback or single retry |
| 60–79 | ADVISORY | Fallback + partial range |
| < 60 | REVIEW | Heavy intervention — investigate |

AQI is on the D-SIG Standard v0.5 0–100 scale and can be used directly
as a `dimensions` entry in a D-SIG signal.

---

## Available Sources

| Source | Adapter | Assets | Notes |
|---|---|---|---|
| Kraken | `KrakenAdapter` | Crypto pairs | Data available ~last 12 months |
| Yahoo Finance | `YahooAdapter` | Equities, ETFs, Crypto | Broad coverage, variable quality |
| Dukascopy | `DukascopyAdapter` | Forex, Crypto | Requires `dukascopy-node` |
| In-memory | `InMemorySource` | Any | Testing and research |

---

## Error Handling

```python
from dal.exceptions import DALHandoffError, DALVersionError, DALConfigError

try:
    h = dal.get_certified_stream(...)
except DALConfigError as e:
    # Missing or invalid configuration (e.g. calendar omitted)
    print(e)
except DALVersionError as e:
    # Installed mif-dqf < dqf_version_target
    print(e)
except DALHandoffError as e:
    # DQF returned VOID, or all sources failed
    print(e.reason)          # "DQF_VOID" | "ALL_SOURCES_FAILED"
    print(e.source_failures) # list of per-source error details
```

Errors are atomic: either a complete `DALHandoff` is returned, or an exception
is raised. There is no partial or degraded return value.

---

## Development

```bash
git clone https://github.com/symbioticode/mif-dal.git
cd mif-dal
uv sync --extra dev
./scripts/dev.sh check   # Ruff + Mypy + Pytest
```

### Running tests

```bash
# Without network (fast, CI-suitable)
pytest tests/ -q

# With real network (Kraken, Yahoo, Dukascopy)
pytest tests/ --run-network
```

### Validation

```bash
python scripts/validate_dal_state.py          # Quick GO/NO-GO
python scripts/validate_dal_state.py --full   # Full adversarial suite (65 checks)
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/API.md](docs/API.md) | Full public API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline, decisions, component map |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues (Kraken limits, NixOS, Dukascopy) |
| [docs/DAL_SPECIFICATION_v1.0.md](docs/DAL_SPECIFICATION_v1.0.md) | Formal specification — source of truth |

---

## Relationship to mif-dqf

mif-dal depends on [mif-dqf](https://github.com/symbioticode/mif-dqf) for
physical data validation. mif-dal calls mif-dqf internally — you do not need
to call mif-dqf directly when using mif-dal.

The `assembly_hash` computed by mif-dal is passed to mif-dqf as `raw_data_hash`,
so both layers anchor on the same SHA-256 value. The `MIF-UID` produced by
mif-dqf is included in `DALHandoff.dqf_report`.

---

## License

MIT — see [LICENSE](LICENSE).

Part of the [MIF ecosystem](https://github.com/symbioticode) by symbioticode.
