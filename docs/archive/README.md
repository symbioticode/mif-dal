# MIF-DAL — Data Abstraction Layer

Data Abstraction Layer of the Metric Integrity Framework.

## Role

Assemble multi-source data streams, submit them to DQF for certification, and expose an atomic result `(DataFrame, DQFReport)`.

## Status

| Sprint | Module | Status |
|--------|--------|--------|
| DAL-000 | Structure + HALO | ✅ |
| DAL-001 | `dal/core/handoff.py` | ✅ |
| DAL-002 | `dal/core/assembler.py` | ⏳ |

## Quick Start

```bash
uv sync --extra dev
./scripts/dev.sh check
```

## Example

```python
from dal import DAL, DALConfig

config = DALConfig()
dal = DAL(config)

# One call per asset — caller builds the pair (D-DAL-007)
h_paxg = dal.get_certified_stream(
    asset_id="PAXG-USD",
    source_preference=["kraken", "yahoo"],
    start="2023-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

h_btc = dal.get_certified_stream(
    asset_id="BTC-USD",
    source_preference=["kraken", "yahoo"],
    start="2023-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

# Caller constructs the ratio
prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]

print(f"PAXG/BTC — {len(prices_pair)} days")
print(f"DQF status : {h_paxg.dqf_status} / {h_btc.dqf_status}")
print(f"AQI        : {h_paxg.aqi:.0f} / {h_btc.aqi:.0f}")
print(f"Hash PAXG  : {h_paxg.assembly_hash[:16]}...")
print(f"Hash BTC   : {h_btc.assembly_hash[:16]}...")
```


## Documentation

- `halo/project_instructions.md` — session entry point
- `halo/anamnese_state.yaml` — current project state
- `KB-DAL-001.md` — HALO founding document