# Technical Debt — mif-dal
# Reconciled: 2026-05-11
# Sources:
#   - anamnese_state.yaml v4.1.0 (TD-001..009)
#   - Post-translation sprint (TD-010, TD-011)
#   - DAL_SPECIFICATION_v1.0.md §12 (TD-005, AM-002)
#   - Session outputs (TD-012..014 from this session)
#
# Statuses:
#   CLOSED     — resolved, verified
#   OPEN       — active, unresolved
#   DEFERRED   — deliberate, condition not met yet

# ═══════════════════════════════════════════════════════════════════════
# CLOSED ITEMS — resolved before or during this session
# ═══════════════════════════════════════════════════════════════════════

| ID     | Description                                           | Resolved in      |
|--------|-------------------------------------------------------|------------------|
| TD-009 | yfinance pinned >=1.3.0,<2.0.0 (was 0.2.51)         | DAL-009          |
| AM-002 | PyPI namespace collision check for mif-dal            | Session 2026-05-06 |
| TD-RUFF | 11 Ruff errors (E501/F841/F601) in dal/ and tests/  | fix_ruff.sh      |
| TD-VERIFY | verify_install.py v1 bug (get_certified_stream self) | v2 generated  |
| TD-WARN | SettingWithCopyWarning in yahoo.py (inplace=True)   | diagnose_and_fix_en.sh |
| TD-QUIET | dev.sh mypy --quiet flag (dropped in mypy 2.0)      | diagnose_and_fix_en.sh |

# ═══════════════════════════════════════════════════════════════════════
# OPEN — must resolve before PyPI publication (v0.1.0)
# ═══════════════════════════════════════════════════════════════════════

| ID     | Description                                           | Target       | Condition / Action |
|--------|-------------------------------------------------------|--------------|--------------------|
| TD-011 | Coverage < 50% on pipeline.py, sources.py, handoff.py — error paths not tested | v0.1.0 pre-pub | BLOCKING for 95%+ confidence. Add tests for: DQF VOID path, ALL_SOURCES_FAILED, DALVersionError, PARTIAL/DEGRADED coverage, AQI penalty accumulation. |
| TD-014 | verify_install.py 3/7 — DAL(config) requires 'sources' arg | v0.1.0 pre-pub | Decision D1: add default sources to DAL.__init__ (recommended) OR fix test_install.py to pass explicit sources. |
| TD-015 | halo/ not yet in .gitignore — will appear in public repo | v0.1.0 pre-pub | git rm -r --cached halo/ && echo "halo/" >> .gitignore |

# ═══════════════════════════════════════════════════════════════════════
# OPEN — must resolve before PyPI, lower priority than above
# ═══════════════════════════════════════════════════════════════════════

| ID     | Description                                           | Target       | Condition / Action |
|--------|-------------------------------------------------------|--------------|--------------------|
| TD-010 | Timestamp.utcnow() deprecated in yfinance 1.3.x — non-blocking warning | v0.1.0 | Locate in yahoo.py, replace with datetime.now(timezone.utc). Not blocking but noisy in logs. |
| TD-013 | scripts/ not cleaned — 11 scripts, target 3-4 | v0.1.0 pre-pub | Merge adversarial_check*.py into validate_dal_state.py (--full flag). Move one-time scripts to scripts/local/. |
| TD-016 | 3 QA scripts still in French (adversarial_dal_check*.py) | v0.1.0 pre-pub | Translate with Haiku after scripts/ restructure. Translate the merged validate_dal_state.py directly. |
| TD-017 | CONTRIBUTING.md absent (mif-dqf has one) | v0.1.0 pre-pub | Create — mirror mif-dqf CONTRIBUTING.md structure. |

# ═══════════════════════════════════════════════════════════════════════
# DEFERRED — deliberate, post-v0.1.0
# ═══════════════════════════════════════════════════════════════════════

| ID     | Description                                           | Target       | Condition |
|--------|-------------------------------------------------------|--------------|-----------| 
| TD-001 | cleaning_log_uri: null — placeholder in DQFReport    | mif-dqf v1.3.0 | After mif-dal Phase 1 stable |
| TD-002 | trend hardcoded 'STABLE' in DQFReport                | mif-dqf v1.3.0 | After mif-dal Phase 1 stable |
| TD-003 | PENDING/UNCERTIFIED absent from DQFStatus enum       | mif-dqf v1.3.0 | Only if needed |
| TD-004 | epistemic_weight absent from DQF manifest            | mif-dqf v1.3.0 | After PCCD M5+M7 validation |
| TD-005 | Local cache absent — every call re-fetches           | mif-dal v0.2.0 | Implement dal/core/cache.py. Not blocking for v0.1.0 — InMemorySource covers test needs. |
| TD-006 | Oracle signal specific to PAXG/BTC — no generic oracle | mif-core v0.2.0 | v0.1 oracle can be PAXG/BTC |
| TD-007 | compute_n_effectif() for DSR not implemented (AM-004) | mif-core v0.1 | Blocking for QS-MÉTIS |
| TD-008 | AQI gravities (0.20/0.10/0.05/0.30) calibrated by intuition | mif-dal v0.2.0 | After 3+ assets in production |
| TD-012 | assembly_hash differs when fallback source used for same asset/range | mif-dal v0.2.0 | Documented in D-DAL-006. Intentional v0.1. Auto-fallback would need content-based hashing strategy. |

# ═══════════════════════════════════════════════════════════════════════
# ANGLES MORTS (open architectural risks — not technical debt per se)
# ═══════════════════════════════════════════════════════════════════════

| ID     | Description                                           | Status |
|--------|-------------------------------------------------------|--------|
| AM-001 | test_strategy_fn_is_not_constant() absent from mif-core | OPEN — first test to write in mif-core before any Phase 1 test |
| AM-004 | compute_n_effectif() for DSR not implemented         | OPEN — blocking for QS-MÉTIS |
| AM-005 | Post-NON QS-MÉTIS protocol not operationalized       | OPEN — QAAF Studio, not blocking for DAL |

# ═══════════════════════════════════════════════════════════════════════
# PRIORITY ORDER FOR REMAINING v0.1.0 WORK
# ═══════════════════════════════════════════════════════════════════════

# P1 — Blocking for publication confidence
#   TD-011 : coverage error paths
#   TD-015 : halo/ in .gitignore
#   TD-014 : verify_install / DAL API

# P2 — Should-fix before publication
#   TD-010 : Timestamp.utcnow() warning
#   TD-013 : scripts/ cleanup
#   TD-016 : translate remaining QA scripts
#   TD-017 : CONTRIBUTING.md

# P3 — Deferred (v0.2.0 or later)
#   TD-005, TD-008, TD-012 — all intentional deferral with documented rationale

# ═══════════════════════════════════════════════════════════════════════
# DELTA FROM anamnese_state.yaml v4.1.0
# ═══════════════════════════════════════════════════════════════════════

# Items in anamnese v4.1.0 that changed status:
#   TD-009 (yfinance pin) → CLOSED (done in DAL-009)
#   AM-002 (PyPI collision) → CLOSED
#   New since v4.1.0: TD-010 (Timestamp.utcnow), TD-011 (coverage),
#     TD-013 (scripts cleanup), TD-014 (DAL API), TD-015 (halo gitignore),
#     TD-016 (QA scripts FR), TD-017 (CONTRIBUTING.md)
#
# Key correction vs your message:
#   TD-005 in your message = "Cache local absent"
#   TD-005 in anamnese v4.1.0 = "assembly_hash differs on fallback" (→ TD-012 here)
#   Both are real. The numbering shifted between the sprint and the spec.
#   This table uses fresh sequential IDs to avoid confusion.
