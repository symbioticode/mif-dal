# scripts/ cleanup + docs/ structure — pre-PyPI publication plan
# Reference: mif-dqf structure (API.md, ARCHITECTURE.md, TROUBLESHOOTING.md)
# Status: to execute AFTER initial symbioticode commit

# ═══════════════════════════════════════════════════════════════════════════
# SCRIPTS/ — current state (11 files) → target (3-4 files)
# ═══════════════════════════════════════════════════════════════════════════

# ── KEEP (public-facing, useful for contributors) ────────────────────────
#
# scripts/dev.sh                ✓ — pre-commit gate, entry point for contributors
# scripts/validate_dal_state.py ✓ — GO/NO-GO check, documented in README
#
# ── MERGE into validate_dal_state.py (or keep separate) ─────────────────
#
# scripts/adversarial_dal_check_p3.py  → MERGE into validate_dal_state.py
# scripts/adversarial_dal_check.py     → MERGE (Phase 2 checks are subset of P3)
#   Rationale: one script, two modes:
#     python scripts/validate_dal_state.py          # quick GO/NO-GO
#     python scripts/validate_dal_state.py --full   # full adversarial suite
#
# ── MOVE to scripts/local/ (internal tools, not for contributors) ────────
#
# scripts/cleanup_repo.sh           → scripts/local/  (one-time, already run)
# scripts/diagnose_and_fix_en.sh    → scripts/local/  (one-time, i18n process)
# scripts/fix_ruff.sh               → scripts/local/  (one-time, already run)
# scripts/translate_to_english.py   → scripts/local/  (i18n tooling)
# scripts/final_commit.sh           → scripts/local/  (one-time process doc)
# scripts/verify_install.py         → scripts/local/  OR scripts/test_install.py
#   (mirror DQF pattern: scripts/test_install.py)
#
# ── ARCHIVE (no longer needed after execution) ──────────────────────────
#
# scripts/validate_environment.py   → docs/archive/  (one-time NixOS setup check)

# Result after cleanup:
# scripts/
#   dev.sh                    # pre-commit gate
#   validate_dal_state.py     # full GO/NO-GO + adversarial (merged)
#   test_install.py           # post-install verification (renamed verify_install.py)
#   local/                    # internal tools (not for contributors)
#       cleanup_repo.sh
#       diagnose_and_fix_en.sh
#       fix_ruff.sh
#       translate_to_english.py
#       final_commit.sh
#       validate_environment.py

# ═══════════════════════════════════════════════════════════════════════════
# DOCS/ — current state → target (mirror DQF structure)
# ═══════════════════════════════════════════════════════════════════════════

# DQF has: API.md · ARCHITECTURE.md · TROUBLESHOOTING.md · DQF_SPECIFICATION.md
# DAL should mirror:

# docs/
#   API.md                    → TO CREATE  (public API reference)
#   ARCHITECTURE.md           → TO CREATE  (pipeline, decisions, component map)
#   TROUBLESHOOTING.md        → TO CREATE  (NixOS, Kraken dates, dukascopy-node)
#   DAL_SPECIFICATION_v1.0.md → KEEP AS-IS (the spec is the source of truth)
#   archive/                  → KEEP (already populated)
#   kb/                       → KEEP (KB-DAL-001..005)

# Content map:
#
# API.md — from DAL_SPECIFICATION_v1.0.md §7 (public API)
#   DAL(config), get_certified_stream(), get_diagnostic_stream()
#   DALHandoff fields table
#   Exception hierarchy
#   AQI formula
#
# ARCHITECTURE.md — from DAL_SPECIFICATION_v1.0.md §1-6 + anamnese decisions
#   Pipeline sequence (S1→S5)
#   Component responsibilities (DAL vs DQF vs MIF-Core)
#   Key architectural decisions (D-DAL-001..008)
#   assembly_hash rationale
#
# TROUBLESHOOTING.md — from KB-DAL-*.md lessons
#   Kraken: data only available for last 12 months
#   PAXG-USD on Kraken: blocked for Canadian users → Yahoo fallback
#   dukascopy-node: NixOS setup (--help not --version)
#   NixOS: pytest-cov not available → skip coverage
#   SettingWithCopyWarning: fixed in v0.1.0
#   yfinance: pinned >=1.3.0,<2.0.0

# ═══════════════════════════════════════════════════════════════════════════
# INITIAL SYMBIOTICODE COMMIT — what goes in now
# ═══════════════════════════════════════════════════════════════════════════

# This is a working snapshot, not a release.
# Clearly marked as pre-publication in the commit message.
# PyPI publication happens AFTER scripts cleanup + docs completion.

# What the initial commit includes (current state):
#   ✓ Full translated dal/ (English)
#   ✓ Full translated tests/
#   ✓ README.md + CHANGELOG.md in English
#   ✓ 65/65 adversarial PASS · 169/177 pytest · Ruff clean
#   ✓ Cleanup done (docs/archive/ populated)
#   ~ scripts/ not yet cleaned (documented as TODO)
#   ~ docs/ not yet complete (API.md, ARCHITECTURE.md, TROUBLESHOOTING.md missing)
#   ~ verify_install.py 3/7 (DAL API issue — known, documented)
#   ~ 3 QA scripts still in French (adversarial_check*.py, dev.sh was FR — now EN)

# Commit message:
#   "feat: initial public snapshot — mif-dal v0.1.0-dev
#
#    Working state, pre-publication. Not yet on PyPI.
#    65/65 adversarial PASS · 169/177 pytest · Ruff clean
#    
#    TODO before PyPI:
#    - scripts/ cleanup (merge adversarial checks, move one-time scripts to local/)
#    - docs/ complete (API.md, ARCHITECTURE.md, TROUBLESHOOTING.md)
#    - verify_install.py: DAL(config) API fix
#    - translate 3 remaining QA scripts to English"
