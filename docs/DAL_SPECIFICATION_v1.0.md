# DAL Specification — v1.0
**Status**: ACTIVE — all decisions closed · ready for implementation  
**Supersedes**: DAL_SPECIFICATION_DRAFT_v0.1.md  
**Reference format**: DQF Specification v1.2  
**Date**: 2026-05-03  
**Authors**: dravitch, Claude (Anthropic)

> **All decisions in this document are CLOSED.**  
> Implementation may begin. No `[OPEN]` items remain.  
> Changes to this document require explicit validation by Andrei + Orchestratrice.

---

## 1. Purpose and Scope

DAL (Data Abstraction Layer) is the assembly layer of the MIF ecosystem.
Its single responsibility: **produce a traceable, hash-anchored OHLCV
stream from external sources, and expose it as a `DALHandoff` object
ready for DQF certification**.

DAL does not evaluate strategies. It does not qualify asset pairs for
research methods. It does not certify metrics. It does not know what a
"signal" is. DAL is infrastructure — its output is data, not judgment.

DAL answers one question: *"Can I assemble a reproducible, hash-anchored
OHLCV stream from available sources for this asset and date range?"*

**What DAL owns**: source resolution, stream fetching, assembly hashing,
DQF delegation, and `DALHandoff` emission.

**What DAL does not own**: OHLCV physics validation (→ MIF-DQF),
asset pair qualification (→ QS-PAF, QAAF Studio only), metric
certification (→ MIF-Core), OOS validation (→ QS-MÉTIS, QAAF Studio only).

**One asset per call** (D-DAL-007, CLOSED): DAL assembles one stream
at a time. Multi-asset composition — including ratio construction — is
the caller's responsibility. MIF-Core builds `SignalData` from two
separate `DALHandoff` objects.

DAL is published as an **independent Python package** (`mif-dal`).
It depends on MIF-DQF. MIF-Core depends on MIF-DAL.

---

## 2. Operational Modes

DAL does not have its own operational modes. It inherits DQF's mode
from the calling method.

| Method | DQF mode triggered | Use case |
|--------|--------------------|----------|
| `get_certified_stream(...)` | CERTIFICATION | MIF-Core runs, reproducible results |
| `get_diagnostic_stream(...)` | DIAGNOSTIC | Exploratory research, data inspection |

DAL never infers or defaults the DQF mode. `calendar` is mandatory
in `get_certified_stream` — omitting it raises `DALConfigError`
before any network call or DQF invocation.

`dqf_version_target` is mandatory in CERTIFICATION, optional in
DIAGNOSTIC. If the installed `mif-dqf` version is lower than
`dqf_version_target`, DAL raises `DALVersionError` before any DQF call.

---

## 3. Operation Classification

### 3.1 DAL-CORE (Non-negotiable)

Failure in any CORE operation raises `DALHandoffError`.
No `DALHandoff` is emitted in that case.

| Code | Name | What it enforces |
|------|------|-----------------|
| S3 | Assembly Hash | SHA-256 on raw data before any transformation |
| S4 | DQF Gate | DQF result gates emission (FAIL/VOID → exception, WARNING → emit with flag) |
| S5 | Handoff Emission | Atomic: either a complete DALHandoff or an exception. No partial state. |

### 3.2 DAL-ADVISORY (Recorded, not blocking)

These operations produce metadata included in `DALHandoff`.
Deviations are recorded in `source_manifest` and reflected in the
AQI score but do not block emission.

| Code | Name | What it records |
|------|------|----------------|
| S1 | Source Resolution & Fetch | Which source was used, fallback chain, fetch timestamps |
| S2 | Stream Completeness | Whether delivered date range matches requested range |

---

## 4. The DAL Pipeline

### S1 — Source Resolution & Fetch [ADVISORY]

DAL resolves which source to use from a declared preference list
(e.g., `["kraken", "yahoo"]`) and fetches the raw OHLCV stream.

- **Primary source succeeds, full range**: `source_used = preferred`,
  `fallback_triggered = false`, recorded in `source_manifest`.
- **Primary source fails or returns incomplete data**: DAL attempts
  the next source. `fallback_triggered = true` recorded per entry.
- **All sources fail**: raises `DALHandoffError` with the full
  failure chain (each source, its error, its timestamp).

Each `source_manifest` entry records:

```python
{
    "source_id": str,        # e.g., "kraken", "yahoo"
    "status": str,           # "success" | "partial" | "failed"
    "hash": str,             # SHA-256 of raw bytes from this source
    "fetched_at": datetime,  # UTC timestamp of fetch
    "rows": int,             # rows delivered
    "timeframe": str,        # e.g., "1D"
    "fallback": bool,        # True if this was not the first choice
}
```

### S2 — Stream Completeness [ADVISORY]

After fetch, DAL computes coverage against the requested date range.

| Coverage | Condition | Effect on AQI |
|----------|-----------|---------------|
| `FULL` | Delivered range = requested range | No penalty |
| `PARTIAL` | Start or end truncated | −0.10 per truncation |
| `DEGRADED` | < 80% of requested range delivered | −0.30 |

`truncated_days` is set to the number of calendar days missing.
`PARTIAL` and `DEGRADED` are advisory — they do not block emission.

### S3 — Assembly Hash [CORE]

**CLOSED — D-DAL-006**: The `assembly_hash` is computed on raw OHLCV
bytes **before** calendar alignment, before forward-fill, and before
any other transformation.

Sequence: `fetch → hash → DQF(clean) → expose`

The hash is computed once and never recomputed:

```python
raw_bytes = raw_dataframe.to_parquet()  # deterministic, no index shuffling
assembly_hash = hashlib.sha256(raw_bytes).hexdigest()
# Immutable from this point forward
```

This makes the hash reproducible independent of DQF version or
configuration, consistent with D-DQF-001 (MIF-UID on raw data).

**Hash stability note**: If a fallback source is used instead of the
preferred source, the `assembly_hash` will differ for the same
asset and date range. This is correct and intentional — two
different sources are two different facts. The `source_manifest`
records which source produced which hash.

### S4 — DQF Gate [CORE]

**CLOSED — D-DAL-005**: DAL delegates the raw stream to DQF.
The DQF mode is determined by the calling method (Section 2).

DAL passes the precomputed `assembly_hash` to DQF as `raw_data_hash`,
so both layers anchor on the same SHA-256 value (D-DAL-006). DQF does
not recompute it.

```python
report = dqf_validator.validate(
    raw_stream,
    calendar=calendar,
    raw_data_hash=assembly_hash,
)
```

DQF's `overall_status` is one of `CERTIFIED | WARNING | VOID`
(verified against `dqf` 1.2.0.post1). DAL renames `CERTIFIED → "PASS"`
at the boundary so `DALHandoff.dqf_status ∈ {PASS, WARNING}`.

| DQF `overall_status` | DAL behavior |
|----------------------|--------------|
| `CERTIFIED` | Emit `DALHandoff(dqf_status="PASS")` |
| `WARNING`   | Emit `DALHandoff(dqf_status="WARNING")`. Log warning with MPI score and check details. |
| `VOID`      | Raise `DALHandoffError(reason="DQF_VOID", dqf_report=report)` |
| _other_     | Raise `DALHandoffError(reason="DQF_UNEXPECTED_STATUS", dqf_report=report)` — guard for future DQF status values. |

`WARNING` is emitted — not blocked — because it represents degraded
but physically valid data. The caller (MIF-Core, QAAF Studio) has the
context to decide whether to proceed. DAL records and exposes the
warning; it does not suppress or promote it.

DQF has no `FAIL` status: any CORE check failure produces `VOID`
(see upstream `DQF_SPECIFICATION §3.1`).

### S5 — Handoff Emission [CORE]

DAL emits exactly one `DALHandoff` per successful call, or raises
`DALHandoffError`. There is no intermediate state visible to the caller.

The emitted `DALHandoff` contains the **cleaned** stream (post-DQF
transformation). The raw stream hash is preserved in `assembly_hash`.
The caller receives data ready for computation.

---

## 5. DALHandoff — The Transfer Object

`DALHandoff` is the single output type of MIF-DAL. Every consumer
of DAL output works exclusively through this object. There is no
other return type.

```python
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from dqf import DQFReport  # package: mif-dqf, module: dqf (per upstream README)


@dataclass(frozen=True)
class DALHandoff:
    """
    Immutable transfer object from MIF-DAL to its callers.

    Produced by get_certified_stream() or get_diagnostic_stream().
    Carries one OHLCV stream for one asset, along with full provenance
    and DQF certification result.

    Stream contract:
        - DatetimeIndex, tz-aware UTC
        - Columns: open, high, low, close, volume (float64)
        - No NaN values (DQF has cleaned)
        - Sorted ascending, no duplicate index entries

    Composition note (D-DAL-007):
        DALHandoff carries one asset. To work with a pair (e.g., PAXG/BTC),
        the caller assembles two DALHandoff objects independently and
        constructs the ratio externally. Example:

            h_paxg = dal.get_certified_stream("PAXG-USD", ...)
            h_btc  = dal.get_certified_stream("BTC-USD", ...)
            prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]
    """

    # ── Stream ──────────────────────────────────────────────────────────────
    stream: pd.DataFrame        # OHLCV, DatetimeIndex UTC, no NaN, sorted asc

    # ── Asset identity ──────────────────────────────────────────────────────
    asset_id: str               # Stable identifier, e.g. "PAXG-USD"
    calendar: str               # Declared calendar: "CRYPTO_247" | "NYSE" | ...

    # ── Assembly provenance ─────────────────────────────────────────────────
    assembly_hash: str          # SHA-256 of raw bytes before any transformation
    handoff_timestamp: datetime # UTC — when DAL emitted this handoff
    dal_version: str            # mif-dal package version, e.g. "0.1.0"
    source_manifest: tuple      # Immutable list of dicts — see S1 for schema

    # ── Coverage ────────────────────────────────────────────────────────────
    coverage: str               # "FULL" | "PARTIAL" | "DEGRADED"
    truncated_days: int         # 0 if FULL

    # ── DQF result ──────────────────────────────────────────────────────────
    dqf_status: str             # "PASS" (CERTIFIED) | "WARNING" — renamed at boundary
    dqf_mpi: float              # MIF Purity Index 0–100 — copied from dqf_report.purity_index
    dqf_version: str            # mif-dqf package version used — surface convenience, copied from dqf_report.dqf_version at emission
    dqf_version_target: str     # Minimum DQF version declared by caller ("" if DIAGNOSTIC)
    dqf_report: DQFReport       # Full DQF report object

    # ── Assembly quality ────────────────────────────────────────────────────
    aqi: float                  # Assembly Quality Index 0–100 (see §6)
```

**Why `frozen=True`**: `DALHandoff` is a certification artifact. It must
not be mutated after emission. If the caller needs to annotate it, wrap
it in their own dataclass.

**Why `source_manifest: tuple`**: `frozen=True` requires immutable
fields. The manifest is converted from `list[dict]` to `tuple[dict]`
at construction. Callers iterate it normally.

---

## 6. Assembly Quality Index (AQI)

The AQI measures DAL-layer intervention to produce usable raw data.
It is distinct from MPI (which measures DQF-layer intervention on
already-assembled data).

### Formula

```
AQI = max(0, 100 × (1 − Σ(gravity_i for each intervention_i)))
```

The `max(0, ...)` floor prevents negative values when penalties accumulate.

| Intervention | Gravity | Trigger condition |
|-------------|---------|-------------------|
| Source fallback triggered | 0.20 | Preferred source unavailable or incomplete |
| Retry required | 0.05 per retry | Transient source failure, up to 3 retries |
| Date range truncated (start) | 0.10 | Source history starts after requested start |
| Date range truncated (end) | 0.10 | Source ends before requested end |
| Coverage DEGRADED | 0.30 | < 80% of requested range delivered |

### Interpretation

| AQI | Label | Meaning |
|-----|-------|---------|
| 100 | EXCELLENT | Preferred source, full range, no retries |
| 80–99 | GOOD | Minor fallback or single retry |
| 60–79 | ADVISORY | Fallback + partial range — verify source quality |
| < 60 | REVIEW | Heavy intervention — flag for investigation |

### D-SIG compatibility

AQI is on the 0–100 scale defined by D-SIG Standard v0.5 §3.3.
It can be used as `dimensions.assembly_quality` in a D-SIG signal
without transformation. DAL does not emit D-SIG signals — this is
the caller's responsibility.

Combined data quality score (for caller use in D-SIG):
```
data_quality_score = 0.60 × dqf_mpi + 0.40 × aqi
```
*(Weights are suggestions — the caller defines the profile per D-SIG §3.4.)*

---

## 7. DQF Integration

```
MIF-DQF   — no dependency on MIF-DAL
MIF-DAL   — depends on mif-dqf (declared in pyproject.toml)
MIF-Core  — depends on mif-dal (and transitively on mif-dqf)
```

### Public API

```python
from mif_dal import DAL, DALConfig

config = DALConfig(
    cache_dir=".dal_cache",     # Optional local cache
    request_timeout=30,         # Seconds per source request
)
dal = DAL(config)

# ── CERTIFICATION — reproducible, strict ──────────────────────────────
handoff = dal.get_certified_stream(
    asset_id="PAXG-USD",
    source_preference=["kraken", "yahoo"],
    start="2020-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)
# Returns DALHandoff with dqf_status "PASS" or "WARNING".
# Raises DALHandoffError if DQF returns FAIL or VOID.
# Raises DALVersionError if installed mif-dqf < dqf_version_target.
# Raises DALConfigError if calendar is missing.

# ── DIAGNOSTIC — exploratory, permissive ─────────────────────────────
handoff = dal.get_diagnostic_stream(
    asset_id="PAXG-USD",
    source_preference=["yahoo"],
    start="2020-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",          # required (DALHandoff invariant)
)
# Always returns a DALHandoff (DQF result is informational).
# dqf_report carries DIAGNOSTIC mode annotation.
# dqf_version_target defaults to "" (no version enforcement).
# calendar is required even in DIAGNOSTIC because DALHandoff.calendar
# must be non-empty for traceability. DQF does not auto-detect the
# calendar from the data (`report.calendar = "UNKNOWN"` if omitted) —
# see TD-009 for the v0.2.0 path toward auto-derivation.
```

### Pair assembly (caller responsibility)

```python
# Two independent certified streams — two DQF certifications
h_paxg = dal.get_certified_stream(
    "PAXG-USD", source_preference=["kraken"], calendar="CRYPTO_247",
    start="2020-01-01", end="2024-12-31", dqf_version_target="1.2.0",
)
h_btc = dal.get_certified_stream(
    "BTC-USD", source_preference=["kraken"], calendar="CRYPTO_247",
    start="2020-01-01", end="2024-12-31", dqf_version_target="1.2.0",
)

# Caller constructs SignalData for MIF-Core
from mif_core import SignalData
signal_data = SignalData(
    prices_base_usd  = h_paxg.stream["close"],
    prices_quote_usd = h_btc.stream["close"],
    prices_pair      = h_paxg.stream["close"] / h_btc.stream["close"],
    # ... IS/OOS boundaries
)
```

---

## 8. Error Hierarchy

```python
class DALError(Exception):
    """Base class for all MIF-DAL exceptions."""

class DALConfigError(DALError):
    """Missing or invalid configuration before any network call.
    Example: calendar omitted in get_certified_stream()."""

class DALVersionError(DALError):
    """Installed mif-dqf version < dqf_version_target.
    Raised before any DQF call.
    Carries: installed_version, required_version."""

class DALHandoffError(DALError):
    """Handoff could not be emitted.
    Carries: reason ('DQF_FAIL' | 'DQF_VOID' | 'ALL_SOURCES_FAILED'),
             dqf_report (if reason is DQF-related),
             source_failures (list[dict] if reason is ALL_SOURCES_FAILED)."""
```

All exceptions carry a human-readable `message` describing:
- What failed
- Which asset and date range were requested
- What action the caller should take

---

## 9. DAL Version Policy

| Bump | Condition | Effect on prior handoffs |
|------|-----------|--------------------------|
| Patch (0.1.x) | Bug fix, no schema change, no hash logic change | Prior handoffs remain comparable |
| Minor (0.x.0) | New advisory operation, new optional DALHandoff field, new source adapter | Prior handoffs remain valid |
| Major (x.0.0) | Change to `assembly_hash` computation OR `DALHandoff` schema | All prior handoffs **invalidated** for strict comparison — new assembly run required |

---

## 10. Deprecations

The following patterns from earlier documents are eliminated.
Do not implement them.

| Eliminated | Reason | Replacement |
|-----------|--------|-------------|
| `DataManager.load_pair()` | Computed ratio, lost USD series | Two `get_certified_stream()` calls per asset |
| `IntelligentCache` with `pickle` | Non-deterministic serialization breaks hash | Explicit `to_parquet()` for hash; separate optional cache layer |
| `UnifiedDataManager` with 5+ sources | Implicit source selection, no fallback log | Explicit `source_preference` list in `DALConfig` |
| Calendar auto-detection in CERTIFICATION | Non-deterministic, inherited from DQF CORE | Mandatory `calendar` parameter |
| `DataAbstractionLayer.get_pair_data()` | Coupled two assets in one call | Two separate `get_certified_stream()` calls (D-DAL-007) |
| `get_certified_streams(also_fetch=[...])` | Multi-asset complexity, atomicity issues | Two separate calls (D-DAL-007) |

---

## 11. Deferred to MIF-Core

The following are explicitly out of DAL scope:

- Statistical sanity checks (extreme returns, zero-volume days,
  volatility spikes) — market probability questions, not physical validity
- Pair compatibility assessment — QS-PAF's responsibility in QAAF Studio
- Cross-asset consistency validation — MIF-Core `SignalData` invariants
- `SignalData` construction — MIF-Core caller responsibility

---

## 12. Known Technical Debt

| ID | Description | Target | Condition |
|----|-------------|--------|-----------|
| TD-005 | `assembly_hash` differs when fallback source is used for same asset/range | mif-dal v0.2.0 | Only if automatic fallback is implemented; for v0.1 fallback is manual |
| AM-002 | Verify PyPI namespace collision before first release | Pre-release | Run `pip index versions dal` and `pip index versions mif-dal` |

---

*Supersedes: DAL_SPECIFICATION_DRAFT_v0.1.md,*
*Data_Abstraction_Layer__DAL__-_Architecture.md*  
*For DQF interface details, see DQF_SPECIFICATION.md §7.*  
*Implementation session instructions: see project_instructions.md + anamnese_state.yaml.*
