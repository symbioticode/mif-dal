#!/bin/bash
# ============================================
# deploy.sh — IDEeS Proposal Deploy Workflow
# Linux / macOS
#
# Usage:
#   bash deploy.sh                    # auto-detect branch, pre-check, push
#   bash deploy.sh -m "feat: message" # custom commit message
#   bash deploy.sh --pull             # pull only
#   bash deploy.sh --status           # show status only
#   bash deploy.sh --check            # pre-checks only (no commit)
#
# Branch rules (enforced automatically):
#   main          → Andrei only (blocked for collaborator)
#   collab/*      → Thierry only
#   feature/*     → anyone
#   research/*    → anyone
#   governance/*  → Andrei only
# ============================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

# ── Colors ────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }

# ── Config ────────────────────────────────────
PROTECTED_BRANCHES=("main" "governance/.*")
COLLAB_BRANCHES=("collab/.*")
GIT_USER=$(git config user.email 2>/dev/null || echo "unknown")

# ── Parse args ────────────────────────────────
CUSTOM_MSG=""
MODE="deploy"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message) CUSTOM_MSG="$2"; shift 2 ;;
    --pull)   MODE="pull";   shift ;;
    --status) MODE="status"; shift ;;
    --check)  MODE="check";  shift ;;
    *) shift ;;
  esac
done

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

info "User    : $GIT_USER"
info "Branch  : $CURRENT_BRANCH"
info "Repo    : $REPO_ROOT"
echo ""

# ── Branch access control ─────────────────────
check_branch_access() {
  local branch="$1"
  local user="$2"

  # Protected branches: main and governance/*
  if [[ "$branch" == "main" ]] || [[ "$branch" =~ ^governance/ ]]; then
    # Allow only if IDEES_OWNER is set (Andrei sets this in his shell profile)
    if [[ -z "${IDEES_OWNER:-}" ]]; then
      err "Branch '$branch' is protected. Push not allowed.
  → If you are Andrei: add 'export IDEES_OWNER=1' to your ~/.bashrc or ~/.zshrc
  → If you are Thierry: push to collab/YOUR-FEATURE instead"
    fi
    ok "Owner access confirmed — protected branch allowed"
  fi
}

# ── Pre-checks (ruff + black + markdownlint) ──
run_prechecks() {
  info "Running pre-checks..."
  local failed=0

  # Python checks (only if .py files staged)
  STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
  if [[ -n "$STAGED_PY" ]]; then
    # Check for uv / ruff / black
    if command -v uv &>/dev/null; then
      info "  ruff (via uv)..."
      if ! uv run ruff check $STAGED_PY --quiet 2>/dev/null; then
        warn "  ruff: issues found — run 'uv run ruff check --fix' to auto-fix"
        failed=1
      else
        ok "  ruff: clean"
      fi

      info "  black (via uv)..."
      if ! uv run black --check $STAGED_PY --quiet 2>/dev/null; then
        warn "  black: formatting issues — run 'uv run black .' to fix"
        failed=1
      else
        ok "  black: clean"
      fi
    else
      warn "  uv not found — skipping Python checks (install: curl -LsSf https://astral.sh/uv/install.sh | sh)"
    fi
  fi

  # Markdown checks (only if .md files staged)
  STAGED_MD=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$' || true)
  if [[ -n "$STAGED_MD" ]]; then
    if command -v markdownlint &>/dev/null; then
      info "  markdownlint..."
      if ! markdownlint $STAGED_MD --quiet 2>/dev/null; then
        warn "  markdownlint: issues found (non-blocking)"
      else
        ok "  markdownlint: clean"
      fi
    fi
  fi

  # Governance files protection
  STAGED_GOV=$(git diff --cached --name-only | grep -E '^(CHARTER\.md|STATUS\.md|governance/)' || true)
  if [[ -n "$STAGED_GOV" ]]; then
    if [[ -z "${IDEES_OWNER:-}" ]]; then
      err "Governance files staged: $STAGED_GOV
  Only Andrei (IDEES_OWNER=1) can commit to CHARTER.md, STATUS.md, or governance/"
    fi
    warn "  Governance files modified — owner confirmed"
  fi

  if [[ "$failed" -eq 1 ]] && [[ "${FORCE_PUSH:-}" != "1" ]]; then
    err "Pre-checks failed. Fix issues above, or run 'FORCE_PUSH=1 bash deploy.sh' to override."
  fi

  ok "Pre-checks passed"
}

# ── Modes ─────────────────────────────────────

if [[ "$MODE" == "status" ]]; then
  git status
  echo ""
  git log --oneline -5
  exit 0
fi

if [[ "$MODE" == "pull" ]]; then
  info "Pulling from origin/$CURRENT_BRANCH..."
  git fetch origin
  git pull --ff-only origin "$CURRENT_BRANCH" || git pull --rebase origin "$CURRENT_BRANCH"
  ok "Up to date"
  exit 0
fi

if [[ "$MODE" == "check" ]]; then
  git add --all
  run_prechecks
  git reset HEAD -- . &>/dev/null || true
  ok "Check complete — nothing committed"
  exit 0
fi

# ── Full deploy ───────────────────────────────
check_branch_access "$CURRENT_BRANCH" "$GIT_USER"

git fetch origin 2>/dev/null || true

LOCAL_CHANGES=$(git status --porcelain 2>/dev/null || echo "")
if [[ -z "$LOCAL_CHANGES" ]]; then
  info "No local changes — pulling latest..."
  git pull --ff-only origin "$CURRENT_BRANCH" 2>/dev/null || true
  ok "Repository clean and up to date"
  git log --oneline -3
  exit 0
fi

info "Local changes:"
git status --short
echo ""

# Stage
info "Staging changes..."
git add --all

# Pre-checks
run_prechecks

# Commit message
if [[ -z "$CUSTOM_MSG" ]]; then
  CHANGED=$(git diff --cached --name-only 2>/dev/null)
  SCOPE=""
  echo "$CHANGED" | grep -qE '^proposal/' && SCOPE="${SCOPE}proposal,"
  echo "$CHANGED" | grep -qE '^research/' && SCOPE="${SCOPE}research,"
  echo "$CHANGED" | grep -qE '^specs/'    && SCOPE="${SCOPE}specs,"
  echo "$CHANGED" | grep -qE '^tests/'    && SCOPE="${SCOPE}tests,"
  echo "$CHANGED" | grep -qE '^brainstorm/' && SCOPE="${SCOPE}brainstorm,"
  echo "$CHANGED" | grep -qE '^governance/' && SCOPE="${SCOPE}governance,"
  SCOPE="${SCOPE%,}"
  [[ -z "$SCOPE" ]] && SCOPE="misc"

  # Tag external contributions
  if [[ "$CURRENT_BRANCH" =~ ^collab/ ]]; then
    CUSTOM_MSG="[EXTERNE:collab] ${SCOPE}: $(date '+%Y-%m-%d %H:%M')"
  else
    CUSTOM_MSG="${SCOPE}: $(date '+%Y-%m-%d %H:%M')"
  fi
fi

info "Commit: $CUSTOM_MSG"
git commit -m "$CUSTOM_MSG"

# Rebase
info "Rebasing on origin/$CURRENT_BRANCH..."
if git pull --rebase origin "$CURRENT_BRANCH" 2>/dev/null; then
  ok "Rebase clean"
else
  CONFLICTS=$(git diff --name-only --diff-filter=U 2>/dev/null || echo "")
  if [[ -n "$CONFLICTS" ]]; then
    err "Conflicts:
$CONFLICTS
Fix conflicts then: git add --all && git rebase --continue && bash deploy.sh"
  fi
fi

# Push
info "Pushing to origin/$CURRENT_BRANCH..."
git push origin "$CURRENT_BRANCH"
ok "Deployed to $CURRENT_BRANCH"

echo ""
ok "=== DEPLOY COMPLETE ==="
git log --oneline -3
echo ""
