#!/usr/bin/env bash
# final_commit.sh — Atomic commits before PyPI publication
# Run from root of mif-dal-en (51_MIF_DAL/mif-dal)
# Prerequisite: 65/65 adversarial PASS · 169/177 pytest · Ruff clean

set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "=== final_commit.sh — pre-publication commits ==="
echo ""

# ── Verify gate before touching anything ─────────────────────────────────────
echo "[0] Gate verification..."
.venv/bin/python -m pytest tests/ -q --tb=no 2>&1 | tail -1
python scripts/adversarial_dal_check_p3.py 2>&1 | tail -3
echo ""

# ── Commit 1: i18n — translated source files ─────────────────────────────────
echo "[1] Commit: i18n translations"
git add \
    dal/adapters/dukascopy.py \
    dal/adapters/in_memory.py \
    dal/adapters/kraken.py \
    dal/adapters/yahoo.py \
    dal/core/handoff.py \
    dal/core/sources.py \
    dal/exceptions.py \
    dal/interfaces/source.py \
    tests/conftest.py \
    tests/test_dukascopy_adapter.py \
    tests/test_in_memory_source.py \
    tests/test_integration.py \
    tests/test_kraken_adapter.py \
    tests/test_source_interface.py \
    tests/test_sources.py \
    tests/test_yahoo_adapter.py \
    scripts/validate_dal_state.py \
    scripts/validate_environment.py \
    scripts/test_install.py

git commit -m "i18n: translate French comments and docstrings to English

- dal/adapters/: yahoo, kraken, dukascopy, in_memory
- dal/core/: handoff, sources
- dal/exceptions.py, dal/interfaces/source.py
- tests/: all test files
- scripts/: validate_dal_state, validate_environment, test_install
Translated by Claude Haiku — logic unchanged, technical terms preserved."

# ── Commit 2: docs — README + CHANGELOG ──────────────────────────────────────
echo "[2] Commit: docs (README + CHANGELOG)"
git add README.md CHANGELOG.md
git commit -m "docs: rewrite README and CHANGELOG in English for open-source publication"

# ── Commit 3: fix — dev.sh + yahoo warning ───────────────────────────────────
echo "[3] Commit: fixes (dev.sh + yahoo SettingWithCopyWarning)"
git add scripts/dev.sh
# yahoo.py already staged above in commit 1 if modified there
# if yahoo fix was separate:
git add dal/adapters/yahoo.py 2>/dev/null || true
git commit -m "fix: dev.sh remove mypy --quiet flag (dropped in mypy 2.0)

- dev.sh: mypy now optional if not installed (SKIP instead of ERR)
- yahoo.py: fix SettingWithCopyWarning (df_raw = rename, not inplace)
Both issues pre-existed in FR repo — not introduced by translation."

# ── Commit 4: chore — cleanup + housekeeping ─────────────────────────────────
echo "[4] Commit: cleanup + housekeeping"
git add \
    .gitignore \
    pytest.ini \
    halo/anamnese_state.yaml \
    scripts/cleanup_repo.sh \
    scripts/diagnose_and_fix_en.sh \
    scripts/fix_ruff.sh \
    scripts/translate_to_english.py

# Staged renames from cleanup_repo.sh (already git mv'd)
git add docs/archive/ 2>/dev/null || true

# docs/PUBLICATION_PROTOCOL.md — internal, add if desired
git add docs/PUBLICATION_PROTOCOL.md 2>/dev/null || true

git commit -m "chore: archive obsolete files, restore .gitignore, update halo state

- docs/archive/: session scripts, plan v1.1, closed issues, backups
- .gitignore: restored and updated
- halo/anamnese_state.yaml: v4.2.0 — Phase 3 complete, publish ready
- scripts/: cleanup_repo, diagnose_and_fix_en, fix_ruff, translate_to_english"

# ── Commit 5: translation artifacts (optional — can be gitignored) ────────────
echo "[5] Commit: translation summary docs (optional)"
# These are internal process docs — include for transparency
git add TRADUCTION_SUMMARY_FR.md TRANSLATION_COMPLETED.md 2>/dev/null || true
if git diff --cached --name-only | grep -q "TRADUCTION\|TRANSLATION"; then
    git commit -m "docs: add translation process summary (internal reference)"
fi

# ── Exclusions — do NOT commit ────────────────────────────────────────────────
echo ""
echo "Not committed (intentional):"
echo "  halo/.gitignore   — internal halo tooling"
echo "  shell.nix (root)  — already in docs/archive/"
echo "  docs/archive/DAL_Phase3_Plan_v1.2.md — check if should stay in docs/"
echo ""
echo "Action needed for DAL_Phase3_Plan_v1.2.md:"
echo "  It appears as untracked in docs/archive/ — it was the reference plan."
echo "  Options:"
echo "    git add docs/archive/DAL_Phase3_Plan_v1.2.md  (keep archived)"
echo "    git add docs/DAL_Phase3_Plan_v1.2.md           (restore to docs/)"
echo "  Recommendation: restore to docs/ — it documents Phase 3 decisions."

# ── Tag ───────────────────────────────────────────────────────────────────────
echo ""
echo "[6] Tag v0.1.0"
git tag -a v0.1.0 -m "mif-dal v0.1.0 — first public release

Data Abstraction Layer for the MIF ecosystem.
Assembles certified, traceable OHLCV streams from external sources.

- DALHandoff: immutable, certified output (frozen dataclass, 15 fields)
- Adapters: KrakenAdapter, YahooAdapter, DukascopyAdapter, InMemorySource
- assembly_hash: SHA-256 of raw data before any transformation (D-DAL-006)
- AQI: Assembly Quality Index 0-100
- 169/177 tests (8 network skips) · 65/65 adversarial PASS · coverage ≥ 80%
- Requires mif-dqf >= 1.2.0"

echo ""
echo "=== All commits done. Next: ==="
echo ""
echo "  # Push to symbioticode"
echo "  git remote set-url origin git@github.com:symbioticode/mif-dal.git"
echo "  git push origin main --tags"
echo ""
echo "  # Build + publish"
echo "  uv build"
echo "  uv publish --index testpypi   # test first"
echo "  uv publish                    # production"
echo ""
echo "  # Verify from clean install"
echo "  pip install mif-dal==0.1.0"
  echo "  python scripts/test_install.py"
