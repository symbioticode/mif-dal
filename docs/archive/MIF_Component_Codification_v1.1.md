# MIF Ecosystem — Component Codification v1.1
**Status**: Reference — use this document to resolve any naming ambiguity  
**Supersedes**: MIF_Component_Codification_v1.0.md  
**Date**: 2026-05-03  
**Authors**: dravitch, Claude (Anthropic)

---

## 1. Vocabulary Rules

**The word "MIF" alone is ambiguous and must always be qualified.**

Accepted uses: *MIF ecosystem*, *MIF-DQF*, *MIF-DAL*, *MIF-Core*, *MIF-UID*.
Unqualified "MIF" in any document is a drafting error — flag and correct it.

**Prefix convention:**

| Prefix | Scope | Examples |
|--------|-------|---------|
| `MIF-` | PyPI packages — infrastructure, reusable | MIF-DQF, MIF-DAL, MIF-Core |
| `QS-` | QAAF Studio only — research protocols, not packages | QS-PAF, QS-MÉTIS |

`QS-` components are research opinions calibrated to specific asset pairs.
Publishing them as packages would imply a universal standard that does not
exist. They depend on QAAF Studio; QAAF Studio does not depend on them.

---

## 2. Published Packages (PyPI — `mif-*` namespace)

These are the only components published or planned for PyPI.
Nothing else belongs in the `mif-*` namespace.

---

### MIF-DQF
**Code**: `MIF-DQF`  
**Package**: `mif-dqf`  
**Status**: STABLE — v1.2.0.post1 — 224/224 tests passing  
**Single responsibility**: Guarantee that OHLCV data entering any MIF
computation is physically valid and traceable.

DQF answers one question: *"Are these prices physically possible?"*

It enforces OHLCV physics and stream identity. It does not evaluate
strategies, signals, or market probability. Any component above DQF
may assume DQF guarantees hold.

**Internal concepts (do not reuse these identifiers without qualification):**

| Identifier | Type | Definition |
|------------|------|------------|
| `MIF-UID` | String | SHA-256 fingerprint of a certification event. Computed as `SHA-256(raw_data_hash ‖ dqf_version ‖ calendar ‖ mode)`. Anchored on raw data (D-DQF-001). Invalidated on any CORE check change. |
| `MPI` | Score 0–100 | MIF Purity Index. Measures DQF-layer intervention cost (how much DQF had to clean). 100 = zero intervention. D-SIG compatible (§3.3). |
| `PROD` | Envelope | Signed identity envelope on every DQF output. Carries: `source_id`, `dqf_version`, `timestamp`, `ttl`, `mode`, `sig_type`. Current sig_type: `sha256_provisional` (Ed25519 deferred to v1.2.0). |
| `precondition_gate` | Multiplier | Applied to downstream MIF-Core scores: 1.0 (PASS), MPI-capped (WARNING), 0.2 (FAIL), 0.0 (VOID). Not a penalty — a non-contamination condition. |

**Checks:**

| Check | Class | Name | Notes |
|-------|-------|------|-------|
| PROD | CORE | Stream Identity & Signature | sha256_provisional in v1.2 |
| C2 | CORE | OHLCV Physics | H ≥ max(O,C), L ≤ min(O,C), V ≥ 0 |
| C3 | CORE | Calendar Alignment | Forex order before Crypto in suffix tests (D-DQF-005) |
| C5 | CORE | Index Traceability | DatetimeIndex, tz-aware, no duplicates |
| C1 | ADVISORY | Stream Integrity | `c1_enabled: false` until DALHandoff stable (D-DAL-004) |
| C4 | ADVISORY | Forward-Fill Limits | Records fill extent in MPI |

**Known technical debt:**

| ID | Description | Target |
|----|-------------|--------|
| TD-001 | `cleaning_log_uri: null` placeholder | v1.3.0 |
| TD-002 | `trend` hardcoded `"STABLE"` in DQFReport | v1.3.0 |
| TD-003 | `PENDING`, `UNCERTIFIED` absent from DQFStatus enum | v1.3.0 (conditional on DAL observations) |
| TD-004 | `epistemic_weight` absent from manifeste | v1.3.0 |

---

### MIF-DAL
**Code**: `MIF-DAL`  
**Package**: `mif-dal`  
**Status**: SPECIFICATION COMPLETE — implementation ready to begin  
**Spec reference**: DAL_SPECIFICATION_v1.0.md  
**Single responsibility**: Assemble a certified, traceable OHLCV stream
from external sources and expose it as a `DALHandoff` object.

DAL answers one question: *"Can I produce a reproducible, hash-anchored
OHLCV stream from available sources for this asset?"*

DAL calls DQF; it does not replace DQF. DAL does not know about pairs,
signals, or research methods.

**Internal concepts:**

| Identifier | Type | Definition |
|------------|------|------------|
| `DALHandoff` | Frozen dataclass | Single output type. Carries: cleaned stream, assembly_hash, source_manifest, DQF report, AQI, timestamps. Immutable after emission. |
| `assembly_hash` | String | SHA-256 of raw OHLCV bytes **before** any transformation (calendar alignment, ffill, cleaning). Consistent with D-DQF-001. Differs per source — intentional. |
| `AQI` | Score 0–100 | Assembly Quality Index. Measures DAL-layer interventions. Distinct from MPI. D-SIG compatible (`dimensions.assembly_quality`). |
| `source_manifest` | tuple[dict] | Immutable ordered list of source attempts. Each entry: `{source_id, status, hash, fetched_at, rows, timeframe, fallback}`. |

**Operations:**

| Code | Class | Name | Description |
|------|-------|------|-------------|
| S1 | ADVISORY | Source Resolution & Fetch | Resolve source from preference list, fetch raw OHLCV, record full chain |
| S2 | ADVISORY | Stream Completeness | Measure coverage vs requested range, classify FULL/PARTIAL/DEGRADED |
| S3 | CORE | Assembly Hash | SHA-256 on raw bytes before any transformation. Immutable once set. |
| S4 | CORE | DQF Gate | FAIL/VOID → raise DALHandoffError. WARNING → emit with dqf_status flag. PASS → emit. |
| S5 | CORE | Handoff Emission | Exactly one DALHandoff or exception. No intermediate states. |

**One asset per call (D-DAL-007):** DAL assembles one stream per call.
Multi-asset composition is the caller's responsibility. Rationale: zero
coupling between assets in infrastructure layer, independent DQF
certifications, faster and independently reproducible tests.

---

### MIF-Core
**Code**: `MIF-Core`  
**Package**: `mif-core`  
**Status**: NOT STARTED — depends on MIF-DAL stable  
**Single responsibility**: Certify that a metric or signal measures what
it claims to measure, using a structured four-gate protocol.

MIF-Core answers one question: *"Is this metric mathematically clean,
generalizable, and transferable across assets?"*

MIF-Core does not source data (→ MIF-DAL). It does not qualify pairs
for research methods (→ QS-PAF). It does not validate OOS value
(→ QS-MÉTIS).

**Internal concepts:**

| Identifier | Type | Definition |
|------------|------|------------|
| `SignalData` | Dataclass | Standardized input to every filter. Fields: `alloc_primary`, `prices_pair`, `prices_base_usd`, `prices_quote_usd`, IS/OOS date boundaries. Built by the caller from two DALHandoff objects. |
| `FilterConfig` | Dataclass | Configuration for one filter. Max 5 parameters. All thresholds documented with empirical justification. No hardcoded thresholds in filter code. |
| `FilterVerdict` | Dataclass | Output of every filter. Fields: `passed` (bool), `filter_name` (str), `metrics` (dict), `diagnosis` (str ≥ 20 chars). The `diagnosis` field is mandatory and must state what to change to pass — not just what failed. |
| `Filter` | ABC | Abstract base class. Every phase, every test implements this. `evaluate()` is side-effect-free, never raises on invalid signal, always returns `FilterVerdict`. |
| `MIFCertification` | Dataclass | Final pipeline output. Status: `CERTIFIED` / `ARCHIVED` / `SUSPECT`. Contains all FilterVerdicts, blocking filter if failed, full diagnosis chain. |
| `oracle_signal` | Test fixture | Trend-following signal with volatility filter, constructed to be certifiable by a well-calibrated pipeline. Lives in `tests/` only — not a production component. |

**Critical constraint (D-MIF-005):** `strategy_fn` must recompute
allocation from `r_pair`. Capturing pre-computed allocations via closure
is a silent bug (documented in `bug_make_strategy_fn().md`). The test
`test_strategy_fn_is_not_constant()` is mandatory before `run_phase1()`.

**Phases (v0.1 scope):**

| Code | Name | Gate | Question answered |
|------|------|------|-------------------|
| P0 | Mathematical Isolation | 6/6 tests PASS | Does the metric compute what it claims on controlled synthetic data? |
| P1 | OOS Generalization | ≥ 3/5 regimes PASS | Does the signal generalize beyond the training regime? Uses relative dominance criterion (cnsr_strat > cnsr_bench), not absolute threshold (D-MIF-006). |
| P2 | Multi-Asset Transfer | ≥ 3/4 pairs PASS | Is the signal robust across different asset pairs? |
| P3 | Production Monitoring | continuous | Out of scope for v0.1. Optional module in v1.0. |

**Phase 0 filters:**

| Code | Name | What it enforces |
|------|------|-----------------|
| T1 | Variance | Signal varies sufficiently (std > threshold) |
| T2 | Discrimination | Signal detects extremes (extreme ratio in range) |
| T3 | R² Forward | Signal has predictive content (R² > min threshold) |
| T4 | No Lookahead | Signal uses no future data (incremental vs full comparison) |
| T5 | Persistence | Autocorrelation appropriate to domain |
| T6 | Orthogonality | Signal non-redundant vs reference signals (\|corr\| < 0.5) |

---

## 3. Research Protocols (QAAF Studio — `QS-` prefix, not on PyPI)

`QS-` components are decision tools for quantitative research.
They run inside QAAF Studio and consume output from MIF-DAL and MIF-Core.
They will not be published as packages.

**Rationale for `QS-` prefix**: These components encode research opinions
about method-market compatibility and OOS validity. They are calibrated
to specific asset pair properties (e.g., PAXG/BTC kurtosis ≈ 17).
The `QS-` prefix makes their QAAF Studio scope unambiguous in any document.

---

### QS-PAF
**Code**: `QS-PAF`  
**Full name**: Pair Adequacy Framework  
**Location**: QAAF Studio — `qaaf_studio/research/paf.py`  
**Status**: PROTOCOL DOCUMENTED (`PAF_Pair_Adequacy_Framework.md`)  
**Single responsibility**: Determine whether an asset pair has the
structural properties required for a given class of research methods,
*before* any metric or signal is developed.

QS-PAF answers one question: *"Is this pair adapted to this method?"*

Operates on data from MIF-DAL. Produces `HIERARCHIE_CONFIRMEE` or `STOP`.
A `STOP` verdict gates the launch of MIF-Core certification — it means:
archive the hypothesis, do not continue on this pair.

**Three sequential directions**: D1 (structural properties), D2
(method compatibility), D3 (regime robustness). D1 must pass before D2
is evaluated; D2 before D3.

---

### QS-MÉTIS
**Code**: `QS-MÉTIS`  
**Full name**: Méthode d'Évaluation des Transitions et des Indicateurs Statistiques  
**Location**: QAAF Studio — `qaaf_studio/research/metis.py`  
**Status**: PROTOCOL DOCUMENTED (`protocole_metis_2.1.md`)  
**Single responsibility**: Validate that a MIF-Core certified signal
generates non-trivial OOS value using adversarial tests.

QS-MÉTIS answers one question: *"Does this signal generate value that
cannot be explained by chance or benchmark drift?"*

**Gates**: Q1 (walk-forward), Q2 (permutation), Q3 (DSR). All three
must pass for a PASS verdict.

**Post-NON protocol (AM-005, open)**: A NON verdict archives the signal
with its metrics. The next step is to explore alternatives via QS-PAF
D2/D3, not to iterate on the same signal. This protocol is not yet
fully operationalized.

**Known open item (AM-004)**: `compute_n_effectif()` for DSR correction
(inter-variant correlation) is not yet implemented. N_trials brut
(e.g., N=101 for an EMA grid) is overly conservative when inter-variant
correlation ≈ 0.97 → N_effectif ≈ 3. Must be implemented before any
DSR-based QS-MÉTIS run.

---

## 4. External Standards

### D-SIG (EXT-DSIG)
**Full name**: Distilled Signal Standard v0.5  
**Origin**: NetPulse — CC0 public domain  
**Relation to MIF ecosystem**: Output interpretation layer. Not a MIF
component. Not implemented by MIF. Consumed by QAAF Studio's decision
and reporting layer.

**Native compatibility** (no transformation required):

| Component | Field | D-SIG dimension |
|-----------|-------|----------------|
| MIF-DQF | `MPI` | `dimensions.data_purity` |
| MIF-DAL | `AQI` | `dimensions.assembly_quality` |

Both are on the 0–100 scale defined by D-SIG Standard v0.5 §3.3.
MIF components do not emit D-SIG signals — this is the caller's
responsibility (QAAF Studio or a dedicated monitoring layer).

---

## 5. Sequence Summary

```
External data sources
        │
        ▼
[MIF-DAL]   one call per asset — assembles stream, computes assembly_hash,
            delegates to DQF — emits DALHandoff
        │
        ▼ DALHandoff (one per asset)
[MIF-DQF]   certifies physical validity, computes MPI, emits PROD envelope
            result embedded in DALHandoff.dqf_report
        │
        ▼ (caller builds SignalData from two DALHandoff objects)
[QS-PAF]    qualifies pair for research method — QAAF Studio only
            HIERARCHIE_CONFIRMEE required to continue
        │
        ▼
[MIF-Core]  certifies metric/signal integrity — P0 → P1 → P2
            emits MIFCertification
        │
        ▼
[QS-MÉTIS]  validates OOS value — QAAF Studio only
            Q1 + Q2 + Q3 required for PASS
        │
        ▼
[D-SIG]     output interpretation and monitoring — QAAF Studio reporting
```

Each layer assumes the previous layer's guarantees hold.
A failure at any layer stops the chain — no degraded result propagates.

---

## 6. Eliminated Terms

Any document using these terms should be considered superseded.

| Eliminated term | Reason | Replacement |
|----------------|--------|-------------|
| "MIF" (unqualified) | Three different meanings in corpus | Always qualify: MIF ecosystem / MIF-DQF / MIF-DAL / MIF-Core |
| "MIF Layer 1–5" | Old naming from v4 framework | Explicit component names |
| "mif-data" | From 2024 Project Charter, never built | MIF-DAL |
| "mif-metrics" | From 2024 Project Charter, never built | MIF-Core |
| "mif-research" | From 2024 Project Charter, never built | QS-PAF + QS-MÉTIS |
| "mif-execution" | From 2024 Project Charter, never built | Out of scope indefinitely |
| "DQF Gate" (informal) | Informal synonym | `precondition_gate` |
| "QAAF v1.1 / v2.0 / v2.2.1 / v3.0" | Historical versions | QAAF Studio 3.1 (current) |
| "Check 6 (Statistical Sanity)" | Migrated out of DQF | MIF-Core Phase 0 (T1–T6) |
| "MIF-UID" in DAL context | MIF-UID belongs to MIF-DQF | `assembly_hash` (DAL concept) |
| "PAF" without QS- prefix | Ambiguous with older internal naming | `QS-PAF` |
| "MÉTIS" without QS- prefix | Ambiguous | `QS-MÉTIS` |
| "get_pair_data()" | Coupled two assets in one call | Two `get_certified_stream()` calls |
| "get_certified_streams(also_fetch=...)" | Multi-asset complexity | Two separate calls |

---

*Supersedes: MIF_Component_Codification_v1.0.md*  
*For DAL implementation details, see DAL_SPECIFICATION_v1.0.md.*  
*For DQF implementation details, see DQF_SPECIFICATION.md v1.2.*
