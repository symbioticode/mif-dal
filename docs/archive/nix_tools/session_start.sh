#!/usr/bin/env bash
# =============================================================================
# MIF-DAL — session_start.sh
# Lance une session de travail : vérifie l'infra, bootstrap HALO, ouvre Claude Code
#
# Usage :
#   ./session_start.sh                    # session standard
#   ./session_start.sh --sync             # sync git seulement
#   ./session_start.sh --status           # état git + infra seulement
#   ./session_start.sh --gemma            # ouvre Gemma (tâches documentaires)
#   ./session_start.sh --check            # gate pré-commit seulement
#
# Rôles :
#   Claude Code  → développement DAL (défaut)
#   Gemma local  → documentation, YAML validation, résumés (--gemma)
# =============================================================================

set -euo pipefail

DAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HALO_DIR="$DAL_DIR/halo"
DOCS_DIR="$DAL_DIR/docs"
LOG_DIR="$DAL_DIR/logs"

# =============================================================================
# COULEURS
# =============================================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()      { echo -e "${GREEN}[OK]${NC}   $*"; }
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()    { echo -e "${RED}[ERR]${NC}  $*"; }
section() { echo -e "\n${BOLD}=== $* ===${NC}"; }

# =============================================================================
# ARGUMENTS
# =============================================================================
MODE="claude"
case "${1:-}" in
  --sync)   MODE="sync" ;;
  --status) MODE="status" ;;
  --gemma)  MODE="gemma" ;;
  --check)  MODE="check" ;;
  --help)
    echo "Usage: $0 [--sync|--status|--gemma|--check]"
    exit 0 ;;
esac

# =============================================================================
# ÉTAPE 0 — Répertoires
# =============================================================================
mkdir -p "$LOG_DIR"
SESSION_DATE=$(date +%Y-%m-%d)
SESSION_LOG="$LOG_DIR/session-$SESSION_DATE.log"

# =============================================================================
# ÉTAPE 1 — Git sync
# =============================================================================
git_sync() {
  section "Git"
  cd "$DAL_DIR"

  git fetch origin 2>/dev/null || warn "fetch échoué — mode offline"

  local dirty
  dirty=$(git status --short 2>/dev/null | wc -l)
  local branch
  branch=$(git branch --show-current 2>/dev/null || echo "?")

  info "Branch : $branch | Changements locaux : $dirty"

  if [[ "$MODE" == "status" ]]; then
    git status
    git log --oneline -5
    return 0
  fi

  if [[ "$MODE" == "sync" ]]; then
    git add -A
    git commit -m "sync: $SESSION_DATE $(date +%H:%M)" 2>/dev/null || ok "Rien à commiter"
    git push origin main && ok "Push OK" || warn "Push échoué"
    return 0
  fi

  ok "Git OK (branch: $branch)"
}

# =============================================================================
# ÉTAPE 2 — Infrastructure
# =============================================================================
check_infra() {
  section "Infrastructure"

  # PostgreSQL
  if psql -U mifdal -d mifdal -c "SELECT 1" &>/dev/null; then
    ok "PostgreSQL mifdal"
  else
    warn "PostgreSQL — base mifdal inaccessible"
  fi

  # Ollama
  if curl -sf http://localhost:11434 &>/dev/null; then
    ok "Ollama ($(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(len(d.get('models',[]))) + ' modèles')" 2>/dev/null || echo "running"))"
  else
    warn "Ollama — non accessible sur :11434"
  fi

  # venv
  if [[ -f "$DAL_DIR/.venv/bin/python" ]]; then
    local pyver
    pyver=$("$DAL_DIR/.venv/bin/python" --version 2>&1)
    ok "venv ($pyver)"
  else
    warn "venv absent — lancer : uv sync --extra dev"
  fi

  # numpy (vieux CPU check)
  if "$DAL_DIR/.venv/bin/python" -c "import numpy" &>/dev/null; then
    ok "numpy importable"
  else
    warn "numpy non importable — vérifier numpy<2.0.0 dans pyproject.toml"
  fi
}

# =============================================================================
# ÉTAPE 3 — HALO Bootstrap
# =============================================================================
halo_bootstrap() {
  section "HALO Bootstrap"

  if [[ ! -f "$HALO_DIR/anamnese_state.yaml" ]]; then
    fail "anamnese_state.yaml introuvable dans $HALO_DIR"
    exit 1
  fi

  # Lire l'état courant via Python
  "$DAL_DIR/.venv/bin/python" - << 'PYEOF'
import yaml, sys
with open("halo/anamnese_state.yaml") as f:
    s = yaml.safe_load(f)
ec = s["etat_courant"]
m  = s.get("metriques_session", {})

print(f"Phase active     : {ec['phase']}")
print(f"Module courant   : {ec['module']}")
print(f"Prochaine action :")
for line in str(ec['prochaine_action']).strip().splitlines():
    print(f"  {line.strip()}")
print(f"Bloquants        : {ec['bloquants']}")
print(f"Dernière session : {ec.get('derniere_session', 'N/A')}")
print()
print(f"Métriques session précédente :")
print(f"  Tests   : {m.get('tests_passing', '?')} passing / {m.get('tests_failing', '?')} failing")
print(f"  Coverage: {m.get('coverage_pct', '?')}%")
print(f"  Mypy    : {m.get('mypy_errors', '?')} errors")
PYEOF

  echo ""
  ok "HALO bootstrap complet"
}

# =============================================================================
# ÉTAPE 4 — Gate pré-commit (optionnel au démarrage)
# =============================================================================
run_check() {
  section "Gate pré-commit"
  cd "$DAL_DIR"

  info "1/3 Ruff..."
  "$DAL_DIR/.venv/bin/python" -m ruff check dal/ tests/ --quiet && ok "Ruff clean" || { fail "Ruff errors"; return 1; }

  info "2/3 Mypy..."
  "$DAL_DIR/.venv/bin/python" -m mypy dal/ --ignore-missing-imports --quiet && ok "Mypy clean" || { fail "Mypy errors"; return 1; }

  info "3/3 Pytest..."
  "$DAL_DIR/.venv/bin/python" -m pytest tests/ -q && ok "Tests verts" || { fail "Tests failing"; return 1; }

  echo ""
  ok "Gate pré-commit : tout vert ✓"
}

# =============================================================================
# ÉTAPE 5 — Vérification Claude Code
# =============================================================================
check_claude() {
  section "Claude Code"

  if command -v claude &>/dev/null; then
    local ver
    ver=$(claude --version 2>/dev/null | head -1 || echo "version inconnue")
    ok "claude disponible ($ver)"
    return 0
  fi

  # Chercher dans npm global
  local npm_bin="$HOME/.npm-global/bin"
  if [[ -f "$npm_bin/claude" ]]; then
    export PATH="$npm_bin:$PATH"
    ok "claude trouvé dans $npm_bin"
    return 0
  fi

  warn "claude introuvable"
  info "Installation : npm install -g @anthropic-ai/claude-code"
  info "Ou via nix-shell : nix-shell -p nodejs_20 --run 'npm install -g @anthropic-ai/claude-code'"
  return 1
}

# =============================================================================
# ÉTAPE 6 — Résumé et lancement
# =============================================================================
print_header() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║  MIF-DAL — Session Start  $(date '+%Y-%m-%d %H:%M')  ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
}

print_footer_claude() {
  echo ""
  section "Lancement Claude Code"
  echo ""
  echo -e "  ${YELLOW}Instruction d'ouverture pour Claude Code :${NC}"
  echo ""
  echo -e "  ${BOLD}Lis halo/project_instructions.md et produis la confirmation de bootstrap.${NC}"
  echo ""
  info "Lancement dans 3 secondes... (Ctrl+C pour annuler)"
  sleep 3
  cd "$DAL_DIR"
  claude
}

print_footer_gemma() {
  section "Mode Gemma"
  echo ""
  echo -e "  ${YELLOW}Périmètre Gemma dans cette session :${NC}"
  echo "  - Mise à jour docs/kb/ (KB-DAL-001, KB-DAL-002)"
  echo "  - Validation syntaxique YAML halo/"
  echo "  - Résumés SESSION_REPORT"
  echo ""
  echo -e "  ${YELLOW}Répertoire de travail Gemma : $DOCS_DIR${NC}"
  echo ""
  info "Lancement Ollama/Gemma..."
  ollama run gemma2:9b 2>/dev/null || ollama run gemma3:4b 2>/dev/null || {
    warn "Aucun modèle Gemma disponible"
    info "Télécharger : ollama pull gemma2:9b"
  }
}

# =============================================================================
# MAIN
# =============================================================================
print_header

case "$MODE" in
  sync)
    git_sync
    exit 0
    ;;
  status)
    git_sync
    check_infra
    exit 0
    ;;
  check)
    run_check
    exit 0
    ;;
  gemma)
    git_sync
    check_infra
    halo_bootstrap
    print_footer_gemma
    ;;
  claude)
    git_sync
    check_infra
    halo_bootstrap
    check_claude && print_footer_claude || {
      warn "Claude Code non disponible — session interrompue"
      exit 1
    }
    ;;
esac

# Log de session
echo "$(date '+%Y-%m-%d %H:%M') | mode=$MODE" >> "$SESSION_LOG"
