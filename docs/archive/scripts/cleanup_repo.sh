#!/usr/bin/env bash
# cleanup_repo.sh — Nettoyage et archivage du repo mif-dal avant publication
# Usage : bash scripts/cleanup_repo.sh [--dry-run]
# Pattern : RESTAURATION_INCREMENTALE — 1 action → vérification → suivant
#
# Ce script ne supprime rien. Il archive dans docs/archive/ et met à jour .gitignore.

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== MODE DRY-RUN (aucune modification) ==="
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
ARCHIVE="$ROOT/docs/archive"

echo "=== cleanup_repo.sh — nettoyage mif-dal avant publication ==="
echo ""

# ─── Fonction d'archivage ────────────────────────────────────────────────────
archive() {
  local src="$1"
  local reason="$2"
  if [ ! -e "$src" ]; then
    echo "  ~ skip (absent) : $src"
    return
  fi
  local dest="$ARCHIVE/$(basename "$src")"
  if $DRY_RUN; then
    echo "  [DRY] ARCHIVE : $src  →  docs/archive/  ($reason)"
  else
    mkdir -p "$ARCHIVE"
    git mv "$src" "$dest" 2>/dev/null || mv "$src" "$dest"
    echo "  ✓ archivé : $src  →  docs/archive/  ($reason)"
  fi
}

# ─── 1. Fichiers de backup explicites ────────────────────────────────────────
echo "[1] Fichiers backup (.old, .bak)"
archive "tests/conftest.py.old"      "backup — remplacé par tests/conftest.py"
archive "tests/test_integration.py.bak" "backup — remplacé par tests/test_integration.py"
archive "halo/anamnese_state.yaml.bak"  "backup — état supersédé"

# ─── 2. Docs de plan supersédés ──────────────────────────────────────────────
echo ""
echo "[2] Docs de plan supersédés (v1.0, v1.1 → v1.2 est la référence)"
archive "docs/DAL_Phase3_Plan_v1.1.md" "supersédé par DAL_Phase3_Plan_v1.2.md"
# v1.2 reste dans docs/ — c'est la référence courante

# ─── 3. Docs de progression sprint (archivage, pas suppression) ───────────────
echo ""
echo "[3] Summaries de sprint (terminés — archivage pour historique)"
archive "docs/progression/sprint_dal-001-summary.md" "sprint terminé"
archive "docs/progression/sprint_dal-002-summary.md" "sprint terminé"
# Le répertoire progression sera vide → peut être supprimé si vide
if $DRY_RUN; then
  echo "  [DRY] RMDIR si vide : docs/progression/"
else
  rmdir "docs/progression" 2>/dev/null && echo "  ✓ docs/progression/ supprimé (vide)" || true
fi

# ─── 4. Issues fermées ───────────────────────────────────────────────────────
echo ""
echo "[4] Issues fermées"
archive "docs/issues/ISSUE-DAL-P3-001.md" "issue résolue — 65/65 PASS"
if $DRY_RUN; then
  echo "  [DRY] RMDIR si vide : docs/issues/"
else
  rmdir "docs/issues" 2>/dev/null && echo "  ✓ docs/issues/ supprimé (vide)" || true
fi

# ─── 5. shell.nix racine → flake.nix est la référence ────────────────────────
echo ""
echo "[5] shell.nix racine (flake.nix est la référence NixOS)"
archive "shell.nix" "remplacé par flake.nix (environnement reproducible)"
# dukascopy/shell.nix est spécifique au module dukascopy — on garde

# ─── 6. Session scripts — utilitaires de session (pas de prod) ───────────────
echo ""
echo "[6] Scripts de session (session_start.sh, session_end.sh)"
archive "session_start.sh" "script de session — pas de prod, halo/ est la référence"
archive "session_end.sh"   "script de session — pas de prod, halo/ est la référence"

# ─── 7. deploy.sh — remplacé par gate publication dans DAL_Phase3_Plan ────────
echo ""
echo "[7] deploy.sh"
archive "deploy.sh" "remplacé par gate publication documentée dans DAL_Phase3_Plan_v1.2.md"

# ─── 8. halo_bootstrap.py — bootstrap one-shot terminé ──────────────────────
echo ""
echo "[8] halo_bootstrap.py (one-shot — HALO déjà initialisé)"
archive "scripts/halo_bootstrap.py" "bootstrap one-shot — HALO initialisé, ne plus exécuter"

# ─── 9. Résumé ────────────────────────────────────────────────────────────────
echo ""
if $DRY_RUN; then
  echo "=== DRY-RUN terminé — aucune modification effectuée ==="
  echo "    Relancer sans --dry-run pour appliquer."
else
  echo "=== cleanup_repo.sh terminé ==="
  echo ""
  echo "Vérifications post-nettoyage :"
  echo "  git status"
  echo "  pytest tests/ -q --tb=no"
  echo "  python scripts/adversarial_dal_check_p3.py"
  echo ""
  echo "Si tout est vert → git add -A && git commit -m 'chore: archive obsolete files pre-v0.1.0'"
fi
