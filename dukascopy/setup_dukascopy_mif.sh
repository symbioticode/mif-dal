#!/usr/bin/env bash
# setup_dukascopy_mif.sh — Installation dukascopy-node pour mif-dal
# Version : 2.0 (unifie setup_dukascopy_mif.sh + setup_dukascopy_nixos_fixed.sh)
#
# Contexte NixOS :
#   Le nix store est read-only → npm install -g échoue si prefix = nix store.
#   Solution : forcer le prefix vers ~/.npm-global (répertoire utilisateur).
#
# Détection binaire :
#   IMPORTANT — dukascopy-node --version retourne TOUJOURS exit code 1 (bug upstream).
#   Utiliser --help (exit 0) pour détecter la présence du binaire.
#   Référence : DUKASCOPY_COMPLETE_GUIDE.md §"Note sur le bug --version"
#
# Usage :
#   bash dukascopy/setup_dukascopy_mif.sh
#
# Prérequis :
#   Node.js dans le PATH (fourni par flake.nix via pkgs.nodejs_20)

set -euo pipefail

# ─── Couleurs ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "  ${GREEN}✓${RESET} $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET} $*"; }

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  INSTALLATION DUKASCOPY-NODE — mif-dal v2.0${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"

# ─── 1. Vérifier Node.js ─────────────────────────────────────────────────────

echo ""
echo "→ Vérification Node.js..."
if ! command -v node &>/dev/null; then
    fail "Node.js absent du PATH."
    echo "    Vérifier que flake.nix inclut pkgs.nodejs_20 dans buildInputs."
    echo "    Lancer : nix develop  (ou entrer dans nix-shell)"
    exit 1
fi
ok "Node.js : $(node --version)"

# ─── 2. Configurer npm global → ~/.npm-global ────────────────────────────────

NPM_GLOBAL="${NPM_GLOBAL:-$HOME/.npm-global}"
echo ""
echo "→ Configuration npm global : $NPM_GLOBAL"
mkdir -p "$NPM_GLOBAL"
npm config set prefix "$NPM_GLOBAL"
export PATH="$NPM_GLOBAL/bin:$PATH"
ok "npm prefix : $(npm config get prefix)"

# ─── 3. Installer dukascopy-node ─────────────────────────────────────────────

echo ""
echo "→ Installation dukascopy-node..."

_is_dukascopy_available() {
    npx dukascopy-node --help &>/dev/null 2>&1 && return 0
    dukascopy-node --help &>/dev/null 2>&1 && return 0
    return 1
}

if _is_dukascopy_available; then
    DUKA_VER=$(npm list -g dukascopy-node --depth=0 2>/dev/null \
        | grep dukascopy-node | tr -d ' ' | cut -d@ -f2 || echo "?")
    ok "Déjà installé : dukascopy-node@${DUKA_VER}"
else
    echo "  → Installation en cours..."
    npm install --prefix "$NPM_GLOBAL" -g dukascopy-node

    if _is_dukascopy_available; then
        DUKA_VER=$(npm list -g dukascopy-node --depth=0 2>/dev/null \
            | grep dukascopy-node | tr -d ' ' | cut -d@ -f2 || echo "?")
        ok "Installé : dukascopy-node@${DUKA_VER}"
    else
        fail "Installation échouée — dukascopy-node introuvable après npm install."
        echo "    Diagnostic : ls $NPM_GLOBAL/bin/ | grep duka"
        exit 1
    fi
fi

# ─── 4. Vérification --help (jamais --version) ───────────────────────────────

echo ""
echo "→ Vérification installation (via --help, pas --version)..."
if npx dukascopy-node --help &>/dev/null; then
    ok "dukascopy-node installé et fonctionnel"
else
    fail "npx dukascopy-node --help a échoué."
    exit 1
fi

# ─── 5. Test de téléchargement réel ─────────────────────────────────────────

echo ""
echo "→ Test de téléchargement (BTC/USD daily, 5 jours)..."
echo "  ⏳ Patience — Dukascopy peut prendre 30s à 2min selon la charge serveur"

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Calcul dates portables (Linux GNU date + macOS BSD date)
if date -d "5 days ago" +%Y-%m-%d &>/dev/null 2>&1; then
    START_DATE=$(date -d "5 days ago" +%Y-%m-%d)
else
    START_DATE=$(date -v-5d +%Y-%m-%d 2>/dev/null || echo "2026-05-04")
fi
END_DATE=$(date +%Y-%m-%d)

echo "  Période : $START_DATE → $END_DATE"
echo ""

if npx dukascopy-node \
    --instrument btcusd \
    --date-from "$START_DATE" \
    --date-to   "$END_DATE" \
    --timeframe d1 \
    --format    csv \
    --dir       "$TMPDIR_TEST"; then

    CSV_COUNT=$(find "$TMPDIR_TEST" -name "*.csv" | wc -l)
    if [ "$CSV_COUNT" -gt 0 ]; then
        CSV_FILE=$(find "$TMPDIR_TEST" -name "*.csv" | head -1)
        LINES=$(tail -n +2 "$CSV_FILE" | wc -l)
        ok "Téléchargement OK : $LINES lignes ($START_DATE → $END_DATE)"
        echo ""
        echo "  Aperçu :"
        head -3 "$CSV_FILE" | sed 's/^/    /'
    else
        warn "Aucun CSV produit — réseau inaccessible ou rate limited."
    fi
else
    warn "Téléchargement échoué — installé mais réseau inaccessible."
    warn "Les tests unitaires mockés fonctionneront quand même."
fi

# ─── 6. Test intégration Python subprocess ───────────────────────────────────

echo ""
echo "→ Test intégration Python..."

PYTHON_BIN=""
for p in ".venv/bin/python" "python3" "python"; do
    if command -v "$p" &>/dev/null 2>&1; then
        PYTHON_BIN="$p"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    warn "Python introuvable — test subprocess ignoré."
else
    "$PYTHON_BIN" - <<'PYEOF'
import subprocess, sys

# CORRECT : --help retourne exit 0 (--version retourne exit 1 — bug upstream)
for cmd in [
    ["npx", "dukascopy-node", "--help"],
    ["dukascopy-node", "--help"],
]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        if r.returncode == 0:
            print(f"  \033[0;32m✓\033[0m Python subprocess OK : {' '.join(cmd)}")
            sys.exit(0)
    except FileNotFoundError:
        continue
    except Exception as e:
        print(f"  ⚠ Exception [{' '.join(cmd)}] : {e}")
        continue

print("  \033[0;31m✗\033[0m Python subprocess échoué")
sys.exit(1)
PYEOF
fi

# ─── 7. Résumé ───────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo -e "  ${GREEN}✓ INSTALLATION COMPLÈTE ET VALIDÉE${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo ""
echo "IMPORTANT — shellHook à vérifier dans flake.nix :"
echo ""
cat <<'HOOK'
    export NPM_GLOBAL="$HOME/.npm-global"
    mkdir -p "$NPM_GLOBAL"
    npm config set prefix "$NPM_GLOBAL" 2>/dev/null || true
    export PATH="$NPM_GLOBAL/bin:$PATH"

    # Détection via --help (exit 0) — jamais --version (exit 1, bug upstream)
    if npx dukascopy-node --help &>/dev/null; then
        DUKA_VER=$(npm list -g dukascopy-node --depth=0 2>/dev/null \
          | grep dukascopy-node | tr -d ' ' | cut -d@ -f2 || echo "?")
        echo "  ✓ dukascopy-node: ${DUKA_VER}"
    else
        echo "  ⚠  dukascopy-node absent — exécuter : bash dukascopy/setup_dukascopy_mif.sh"
    fi
HOOK
echo ""
echo "IMPORTANT — Dans votre code Python, utiliser --help (pas --version) :"
echo ""
echo '    r = subprocess.run(["npx", "dukascopy-node", "--help"],'
echo '                       capture_output=True, timeout=10, stdin=subprocess.DEVNULL)'
echo '    is_available = r.returncode == 0'
