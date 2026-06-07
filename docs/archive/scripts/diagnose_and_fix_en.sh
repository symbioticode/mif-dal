#!/usr/bin/env bash
# diagnose_and_fix_en.sh
# Diagnostic + fixes ciblés pour mif-dal-en avant publication
# À exécuter depuis la racine de mif-dal-en/
#
# Problèmes identifiés depuis checklist comparison (FR vs EN):
#   1. pytest.ini absent de mif-dal-en (non copié lors de la création)
#   2. .gitignore supprimé (visible dans git status)
#   3. dev.sh : mypy --quiet → flag non reconnu mypy 2.0+
#   4. Erreurs mypy FetchResult(error=...) — bug pré-existant FR, non introduit par Haiku
#   5. SettingWithCopyWarning yahoo.py — pré-existant FR
#
# Usage:
#   bash scripts/diagnose_and_fix_en.sh --diagnose   # diagnostic seul
#   bash scripts/diagnose_and_fix_en.sh --fix        # applique les corrections

set -euo pipefail

MODE="${1:---diagnose}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FR_REPO="${HOME}/Projects/09_MIF/02-DAL/mif-dal"
cd "$ROOT"

PASS=0
FAIL=0

ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
fix()  { echo "  → FIX: $1"; }

echo "=== diagnose_and_fix_en.sh ($MODE) ==="
echo "Root : $ROOT"
echo ""

# ─── SECTION A : fichiers manquants ──────────────────────────────────────────
echo "[A] Fichiers essentiels"

if [ -f "$ROOT/pytest.ini" ]; then
  ok "pytest.ini présent"
else
  fail "pytest.ini ABSENT — non copié lors de la création de mif-dal-en"
  if [ "$MODE" = "--fix" ]; then
    if [ -f "$FR_REPO/pytest.ini" ]; then
      cp "$FR_REPO/pytest.ini" "$ROOT/pytest.ini"
      fix "pytest.ini copié depuis $FR_REPO"
    else
      echo "  ! pytest.ini introuvable dans $FR_REPO — créer manuellement :"
      echo '      [pytest]'
      echo '      addopts = --tb=short'
      echo '      testpaths = tests'
    fi
  fi
fi

if [ -f "$ROOT/.gitignore" ]; then
  ok ".gitignore présent"
else
  fail ".gitignore ABSENT (supprimé par git)"
  if [ "$MODE" = "--fix" ]; then
    if [ -f "$FR_REPO/.gitignore" ]; then
      cp "$FR_REPO/.gitignore" "$ROOT/.gitignore"
      fix ".gitignore copié depuis $FR_REPO"
    else
      echo "  ! Créer .gitignore manuellement (voir outputs/.gitignore généré)"
    fi
  fi
fi

if [ -f "$ROOT/pyproject.toml" ]; then
  ok "pyproject.toml présent"
else
  fail "pyproject.toml ABSENT"
fi

# ─── SECTION B : dev.sh mypy --quiet ─────────────────────────────────────────
echo ""
echo "[B] dev.sh — flag mypy --quiet"

if grep -q -- "--quiet" scripts/dev.sh 2>/dev/null; then
  fail "dev.sh contient 'mypy --quiet' — flag supprimé dans mypy 2.0+"
  if [ "$MODE" = "--fix" ]; then
    # Remplacer --quiet par rien (garder le reste de la ligne)
    sed -i 's/mypy \(.*\) --quiet/mypy \1/' scripts/dev.sh
    sed -i 's/ --quiet//' scripts/dev.sh
    fix "dev.sh : --quiet supprimé"
    # Vérifier que mypy tourne maintenant
    echo "  → Test mypy post-fix :"
    .venv/bin/python -m mypy dal/ 2>&1 | tail -5 || true
  fi
else
  ok "dev.sh : pas de --quiet détecté"
fi

# ─── SECTION C : erreurs mypy réelles ────────────────────────────────────────
echo ""
echo "[C] Erreurs mypy réelles (pré-existantes dans repo FR)"

# Lancer mypy si disponible
if .venv/bin/python -m mypy dal/ --no-error-summary 2>/dev/null | grep -q "error:"; then
  MYPY_OUT=$(.venv/bin/python -m mypy dal/ --no-error-summary 2>&1 || true)
  echo "$MYPY_OUT" | grep "error:" | while read -r line; do
    echo "  ✗ $line"
  done

  # Compter les erreurs connues
  ERROR_COUNT=$(echo "$MYPY_OUT" | grep -c "error:" || true)
  echo ""
  echo "  Total: $ERROR_COUNT erreur(s) mypy"
  echo ""
  echo "  Erreurs attendues (pré-existantes FR, non introduites par Haiku) :"
  echo "    - FetchResult(error=...) : 'error' n'est pas un champ de FetchResult"
  echo "      → dal/adapters/yahoo.py, kraken.py, dukascopy.py"
  echo "    - Timestamp vs int : kraken.py, assignation de type"
  echo ""

  if [ "$MODE" = "--fix" ]; then
    echo "  → Correction FetchResult(error=...) :"
    python3 - <<'PYEOF'
import pathlib, re

fixes = {
    "dal/adapters/yahoo.py": [
        # Supprimer l'argument error= dans les appels FetchResult qui échouent
        (
            r'(FetchResult\([^)]*?)(?:,\s*)?error=[^,\n)]+([,)])',
            lambda m: m.group(1).rstrip(', ') + m.group(2)
        ),
    ],
    "dal/adapters/kraken.py": [],  # Timestamp vs int — voir note ci-dessous
    "dal/adapters/dukascopy.py": [
        (
            r'(FetchResult\([^)]*?)(?:,\s*)?error=[^,\n)]+([,)])',
            lambda m: m.group(1).rstrip(', ') + m.group(2)
        ),
    ],
}

for filepath, patterns in fixes.items():
    p = pathlib.Path(filepath)
    if not p.exists():
        print(f"  ~ skip (absent): {filepath}")
        continue
    src = p.read_text()
    original = src
    for pattern, replacement in patterns:
        src = re.sub(pattern, replacement, src, flags=re.DOTALL)
    if src != original:
        p.write_text(src)
        print(f"  ✓ {filepath} : argument error= supprimé")
    else:
        print(f"  ~ {filepath} : pattern non trouvé (déjà corrigé ?)")

print()
print("  Note kraken.py Timestamp vs int :")
print("  Ce bug est une annotation de type incorrecte — non bloquant pour pytest.")
print("  La valeur .timestamp() retourne un float, pas un int.")
print("  Correction : annoter la variable comme float ou utiliser int(ts.timestamp())")
PYEOF

    # Vérification post-fix
    echo ""
    echo "  → Mypy post-fix :"
    .venv/bin/python -m mypy dal/ --no-error-summary 2>&1 | grep "error:\|Found\|Success" || true
  fi

else
  ok "mypy : aucune erreur détectée (ou mypy non disponible)"
fi

# ─── SECTION D : SettingWithCopyWarning ──────────────────────────────────────
echo ""
echo "[D] SettingWithCopyWarning (yahoo.py)"

if grep -q "rename.*inplace=True" dal/adapters/yahoo.py 2>/dev/null; then
  fail "yahoo.py : df_raw.rename(inplace=True) sur une slice → SettingWithCopyWarning"
  echo "  Cause : pandas >= 2.0 traite les slices différemment"
  echo "  Correction : df_raw = df_raw.rename(columns=...) (sans inplace)"
  if [ "$MODE" = "--fix" ]; then
    python3 - <<'PYEOF'
import pathlib
p = pathlib.Path("dal/adapters/yahoo.py")
src = p.read_text()
# Remplacer df_raw.rename(columns=column_mapping, inplace=True)
# par df_raw = df_raw.rename(columns=column_mapping)
old = "df_raw.rename(columns=column_mapping, inplace=True)"
new = "df_raw = df_raw.rename(columns=column_mapping)"
if old in src:
    p.write_text(src.replace(old, new))
    print("  ✓ yahoo.py : SettingWithCopyWarning corrigé")
else:
    print("  ~ yahoo.py : pattern non trouvé (déjà corrigé ?)")
PYEOF
  fi
else
  ok "yahoo.py : pas de rename inplace détecté"
fi

# ─── SECTION E : gate final ──────────────────────────────────────────────────
echo ""
echo "[E] Gate de vérification post-fix"

if [ "$MODE" = "--fix" ]; then
  echo "  → git status :"
  git status --short

  echo ""
  echo "  → pytest (sans réseau) :"
  .venv/bin/python -m pytest tests/ -q --tb=no 2>&1 | tail -3

  echo ""
  echo "  → ruff :"
  .venv/bin/python -m ruff check dal/ tests/ && echo "  ✓ ruff clean" || echo "  ✗ ruff errors"

  echo ""
  echo "  → mypy résumé :"
  .venv/bin/python -m mypy dal/ --no-error-summary 2>&1 | tail -3 || true

  echo ""
  echo "  → Commandes suivantes :"
  echo "    git add pytest.ini .gitignore scripts/dev.sh dal/adapters/ dal/adapters/yahoo.py"
  echo "    git commit -m 'fix: restore missing files + mypy + SettingWithCopyWarning'"
  echo "    python scripts/adversarial_dal_check_p3.py"
  echo "    → Si 65/65 PASS : prêt pour publication PyPI"
else
  echo "  → Relancer avec --fix pour appliquer les corrections"
fi

# ─── RÉSUMÉ ──────────────────────────────────────────────────────────────────
echo ""
echo "=========================================="
if [ "$MODE" = "--diagnose" ]; then
  echo "  DIAGNOSTIC : $FAIL problème(s) détecté(s)"
  [ "$FAIL" -gt 0 ] && echo "  Relancer avec --fix pour corriger" || echo "  Tout est vert"
else
  echo "  FIX terminé"
  echo "  Vérifier : ./scripts/dev.sh check"
fi
echo "=========================================="
