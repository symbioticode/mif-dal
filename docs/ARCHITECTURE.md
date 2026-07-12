# Architecture — mif-dal

## Single Responsibility

mif-dal answers one question:

> *"Can I assemble a reproducible, hash-anchored OHLCV stream from available
> sources for this asset and date range?"*

mif-dal does not evaluate strategies. It does not certify metrics. It does not
qualify asset pairs. It is infrastructure — its output is data, not judgment.

---

## Pipeline

```
Caller
  │
  ├─ get_certified_stream()  →  DQFMode.CERTIFICATION
  └─ get_diagnostic_stream() →  DQFMode.DIAGNOSTIC
          │
          ▼
    [S1] Source Resolution & Fetch         [ADVISORY]
          │  source_preference=["kraken","yahoo"]
          │  → primary source attempted
          │  → fallback on failure (recorded in source_manifest)
          │  → DALHandoffError if all sources fail
          ▼
    [S3] Assembly Hash                     [CORE]
          │  SHA-256(raw_bytes) before any transformation
          │  assembly_hash = immutable from this point
          ▼
    [S2] Stream Completeness               [ADVISORY]
          │  coverage = FULL | PARTIAL | DEGRADED
          │  truncated_days computed
          │  AQI penalties applied
          ▼
    [S4] DQF Gate                          [CORE]
          │  mif-dqf validates OHLCV physics, calendar, gaps
          │  CERTIFIED → dqf_status="PASS"
          │  WARNING   → dqf_status="WARNING" (emitted with flag)
          │  VOID      → DALHandoffError(reason="DQF_VOID")
          ▼
    [S5] Handoff Emission                  [CORE]
          │  DALHandoff (frozen, 15 fields)
          │  or DALHandoffError — no partial state
          ▼
        Caller
```

### Operation classification

**CORE** — failure raises `DALHandoffError`. No `DALHandoff` is emitted.

**ADVISORY** — deviations are recorded in `source_manifest` and reflected
in AQI, but do not block emission.

---

## Key Architectural Decisions

### D-DAL-001 — DAL is a view, not a container
DAL does not own the data. It assembles, certifies, and hands off.
Separation: DAL assembles, mif-dqf certifies, mif-core qualifies.

### D-DAL-002 — DALHandoff is the single transfer object
Every consumer works exclusively through `DALHandoff`. No other return type.
Atomicity: either a complete handoff, or an exception. No intermediate state.

### D-DAL-005 — DQF FAIL/VOID → exception. WARNING → emit with flag.
`VOID` = physically invalid data. Continuing would be a structural error.
`WARNING` = degraded but usable. The caller has context to decide.

### D-DAL-006 — assembly_hash anchored on raw data
Hash computed **before** calendar alignment, before forward-fill, before
any transformation. Consistent with mif-dqf's MIF-UID anchoring on raw data.

```python
raw_bytes = raw_dataframe.to_parquet()  # deterministic
assembly_hash = hashlib.sha256(raw_bytes).hexdigest()
# DQF is called after — hash is immutable
```

If a fallback source is used, the hash differs for the same asset/range.
This is intentional — two sources are two different facts.

### D-DAL-007 — one asset per call
DAL assembles one stream at a time. Multi-asset composition is the caller's
responsibility.

```python
# Correct — two independent certified streams
h_paxg = dal.get_certified_stream("PAXG-USD", ...)
h_btc  = dal.get_certified_stream("BTC-USD", ...)
prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]

# Wrong — DAL does not know about pairs
# h = dal.get_certified_stream("PAXG/BTC", ...)  # does not exist
```

Benefits: two independent DQF certifications, independent hashes,
faster tests, no coupling between assets in the infrastructure layer.

### D-DAL-008 — Kraken API: ~12 months rolling window
Kraken returns data for approximately the last 12 months only.
All integration tests using Kraken use `start >= (today - 11 months)`.
PAXG-USD may be unavailable in some regions — Yahoo is the declared fallback.

---

## Component Map

```
mif-dal/
├── dal/
│   ├── dal.py              # DAL class — public entry point
│   ├── __init__.py         # dal.__all__, dal.__version__
│   ├── exceptions.py       # DALError hierarchy
│   ├── core/
│   │   ├── config.py       # DALConfig
│   │   ├── handoff.py      # DALHandoff (frozen dataclass, 15 fields)
│   │   ├── pipeline.py     # S1→S5 orchestration
│   │   ├── sources.py      # source resolution, AQI computation
│   │   └── assembler.py    # stream assembly utilities
│   ├── adapters/
│   │   ├── kraken.py       # KrakenAdapter
│   │   ├── yahoo.py        # YahooAdapter
│   │   ├── dukascopy.py    # DukascopyAdapter (requires dukascopy-node)
│   │   └── in_memory.py    # InMemorySource (testing)
│   └── interfaces/
│       └── source.py       # Source Protocol, FetchRequest, FetchResult
├── tests/
│   ├── conftest.py         # fixtures, network skip markers
│   ├── test_handoff.py
│   ├── test_pipeline.py
│   ├── test_sources.py
│   ├── test_dal.py
│   └── test_*_adapter.py
├── scripts/
│   ├── dev.sh              # pre-commit gate (Ruff + Mypy + Pytest)
│   ├── validate_dal_state.py   # GO/NO-GO + adversarial suite
│   └── test_install.py     # post-install verification
└── docs/
    ├── API.md
    ├── ARCHITECTURE.md     # this file
    ├── TROUBLESHOOTING.md
    └── DAL_SPECIFICATION_v1.0.md   # formal spec, source of truth
```

---

## Relationship to mif-dqf

```
mif-dqf   ←  no dependency on mif-dal
mif-dal   →  depends on mif-dqf (declared in pyproject.toml)
mif-core  →  depends on mif-dal (and transitively on mif-dqf)
```

mif-dal calls mif-dqf internally. Users of mif-dal do not call mif-dqf directly.

The `assembly_hash` passes through as `raw_data_hash` to mif-dqf, so both
layers anchor on the same SHA-256. The `MIF-UID` produced by mif-dqf
(which includes dqf_version, calendar, and mode in its hash) is distinct
from `assembly_hash` (which is source-only, transformation-invariant).

---

## Versioning Policy

| Bump | Condition | Effect on prior handoffs |
|---|---|---|
| Patch (0.1.x) | Bug fix, no schema change | Prior handoffs remain comparable |
| Minor (0.x.0) | New advisory op, new optional field, new adapter | Prior handoffs remain valid |
| Major (x.0.0) | `assembly_hash` computation change OR DALHandoff schema change | All prior handoffs **invalidated** |
