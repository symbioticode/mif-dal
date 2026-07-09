#!/usr/bin/env bash
# =============================================================================
# MIF-DAL — session_end.sh
# Clôture une session : vérifie les gates, met à jour HALO, commit, push
#
# Usage :
#   ./session_end.sh                          # clôture standard
#   ./session_end.sh -m "DAL-002: assembler"  # message commit personnalisé
#   ./session_end.sh --skip-push              # commit sans push
#   ./session_end.sh --gemma                  # clôture session Gemma
#
# Appelé par : Claude Code (fin de sprint) ou Gemma (fin de tâche doc)
# =============================================================================

set -euo pipefail

DAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HALO_DIR="$DAL_DIR/halo"
LOG_DIR="$DAL_DIR/logs"

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
COMMIT_MSG=""
SKIP_PUSH=0
MODE="claude"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message) COMMIT_MSG="$2"; shift 2 ;;
    --skip-push)  SKIP_PUSH=1; shift ;;
    --gemma)      MODE="gemma"; shift ;;
    *) shift ;;
  esac
done

# =============================================================================
# ÉTAPE 1 — Gate pré-commit obligatoire
# =============================================================================
run_gates() {
  section "Gates pré-commit"
  cd "$DAL_DIR"

  local errors=0

  info "Ruff..."
  "$DAL_DIR/.venv/bin/python" -m ruff check dal/ tests/ --quiet && ok "Ruff clean" || { fail "Ruff errors — corriger avant commit"; errors=$((errors+1)); }

  info "Mypy..."
  "$DAL_DIR/.venv/bin/python" -m mypy dal/ --ignore-missing-imports --quiet && ok "Mypy clean" || { fail "Mypy errors — corriger avant commit"; errors=$((errors+1)); }

  info "Pytest..."
  local test_output
  test_output=$("$DAL_DIR/.venv/bin/python" -m pytest tests/ -q 2>&1)
  echo "$test_output" | tail -3
  if echo "$test_output" | grep -q "failed"; then
    fail "Tests failing — commit bloqué (règle protocols.yaml)"
    errors=$((errors+1))
  else
    ok "Tests verts"
  fi

  if [[ $errors -gt 0 ]]; then
    echo ""
    fail "$errors gate(s) en échec — session non clôturée"
    echo ""
    echo "Options :"
    echo "  1. Corriger les erreurs et relancer ./session_end.sh"
    echo "  2. ./session_end.sh --skip-push  (commit local seulement, push manuel)"
    exit 1
  fi

  ok "Tous les gates verts ✓"
}

# =============================================================================
# ÉTAPE 2 — Vérification SESSION_REPORT dans anamnese_state.yaml
# =============================================================================
check_halo_updated() {
  section "HALO — metriques_session"

  if [[ ! -f "$HALO_DIR/anamnese_state.yaml" ]]; then
    fail "anamnese_state.yaml introuvable"
    exit 1
  fi

  # Lire les métriques actuelles
  "$DAL_DIR/.venv/bin/python" - << 'PYEOF'
import yaml
with open("halo/anamnese_state.yaml") as f:
    s = yaml.safe_load(f)
m = s.get("metriques_session", {})
print(f"  Session ID   : {m.get('derniere_session_id', 'NON REMPLI')}")
print(f"  Tests        : {m.get('tests_passing', '?')} passing / {m.get('tests_failing', '?')} failing")
print(f"  Coverage     : {m.get('coverage_pct', '?')}%")
print(f"  Mypy errors  : {m.get('mypy_errors', '?')}")
print(f"  Violations   : {m.get('violations_protocols', '?')}")
PYEOF

  echo ""

  # Vérifier que session_id n'est pas "N/A" (non mis à jour)
  local session_id
  session_id=$("$DAL_DIR/.venv/bin/python" -c "
import yaml
with open('halo/anamnese_state.yaml') as f:
    s = yaml.safe_load(f)
print(s.get('metriques_session', {}).get('derniere_session_id', 'N/A'))
")

  if [[ "$session_id" == "N/A" ]]; then
    warn "metriques_session.derniere_session_id non mis à jour"
    warn "Claude Code doit mettre à jour anamnese_state.yaml avant de clôturer"
    echo ""
    read -rp "Continuer quand même ? [o/N] : " choice
    [[ "$choice" =~ ^[Oo]$ ]] || exit 1
  else
    ok "HALO mis à jour (session: $session_id)"
  fi
}

# =============================================================================
# ÉTAPE 3 — Commit et push
# =============================================================================
git_commit_push() {
  section "Git"
  cd "$DAL_DIR"

  local branch
  branch=$(git branch --show-current 2>/dev/null || echo "main")

  # Construire message de commit automatique si non fourni
  if [[ -z "$COMMIT_MSG" ]]; then
    local session_id
    session_id=$("$DAL_DIR/.venv/bin/python" -c "
import yaml
with open('halo/anamnese_state.yaml') as f:
    s = yaml.safe_load(f)
print(s.get('metriques_session', {}).get('derniere_session_id', 'session'))
" 2>/dev/null || echo "session")
    COMMIT_MSG="$session_id: $(date '+%Y-%m-%d %H:%M')"
  fi

  # Staging
  git add -A
  local dirty
  dirty=$(git diff --cached --name-only | wc -l)

  if [[ "$dirty" -eq 0 ]]; then
    ok "Rien à commiter — repo propre"
    return 0
  fi

  info "Fichiers à commiter : $dirty"
  git diff --cached --name-only | sed 's/^/  /'

  # Commit
  git commit -m "$COMMIT_MSG

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  local hash
  hash=$(git rev-parse --short HEAD)
  ok "Commit : $hash — $COMMIT_MSG"

  # Push
  if [[ $SKIP_PUSH -eq 0 ]]; then
    info "Push vers origin/main..."
    git push origin main && ok "Push OK" || {
      warn "Push échoué"
      info "Push manuel : git push origin main"
    }
  else
    warn "Push ignoré (--skip-push)"
  fi
}

# =============================================================================
# ÉTAPE 4 — SESSION_REPORT affiché
# =============================================================================
print_session_report() {
  section "SESSION_REPORT"
  echo ""

  "$DAL_DIR/.venv/bin/python" - << 'PYEOF'
import yaml
from datetime import datetime

with open("halo/anamnese_state.yaml") as f:
    s = yaml.safe_load(f)

m  = s.get("metriques_session", {})
ec = s["etat_courant"]

print(f"Session ID       : {m.get('derniere_session_id', '?')}")
print(f"Date             : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Tests            : {m.get('tests_passing', '?')} passing / {m.get('tests_failing', '?')} failing")
print(f"Coverage         : {m.get('coverage_pct', '?')}%")
print(f"Mypy             : {m.get('mypy_errors', '?')} errors")
print(f"Violations       : {m.get('violations_protocols', '?')}")
print(f"Fichiers créés   : {', '.join(m.get('fichiers_crees', [])) or 'aucun'}")
print(f"Fichiers modifiés: {', '.join(m.get('fichiers_modifies', [])) or 'aucun'}")
print()
print(f"Prochaine action : {ec['prochaine_action'].strip().splitlines()[0] if ec['prochaine_action'] else '?'}")
print(f"Bloquants        : {ec['bloquants']}")
PYEOF

  echo ""
}

# =============================================================================
# ÉTAPE 5 — Log de session
# =============================================================================
write_log() {
  mkdir -p "$LOG_DIR"
  local log_file="$LOG_DIR/session-$(date +%Y-%m-%d).log"
  echo "$(date '+%H:%M') | END | mode=$MODE | msg=$COMMIT_MSG" >> "$log_file"
  ok "Log : $log_file"
}

# =============================================================================
# MAIN
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  MIF-DAL — Session End    $(date '+%Y-%m-%d %H:%M')  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"

if [[ "$MODE" == "gemma" ]]; then
  section "Clôture session Gemma"
  info "Périmètre : docs/kb/ uniquement"
  check_halo_updated
  git_commit_push
  write_log
  echo ""
  ok "Session Gemma clôturée"
  exit 0
fi

# Mode Claude Code — gates obligatoires
run_gates
check_halo_updated
print_session_report
git_commit_push
write_log

echo ""
echo -e "${GREEN}${BOLD}Session clôturée ✓${NC}"
echo ""
echo "Checklist manuelle :"
echo "  [ ] anamnese_state.yaml.metriques_session mis à jour"
echo "  [ ] Décisions nouvelles → Orchestratrice pour D-DAL-NNN"
echo "  [ ] Intervention Andrei requise → formulée dans SESSION_REPORT"
echo ""
