# MIF-DAL v0.1.0 — Publication Protocol
# symbioticode/mif-dal · May 2026
# Status: READY TO EXECUTE
#
# Reference state: checklist_pass65-65_cleaning.txt
#   65/65 adversarial PASS · 169/177 pytest · Ruff clean · cleanup done
#
# Open items before publish:
#   P1. mypy --quiet flag not recognized in dev.sh → fix dev.sh
#   P2. verify_install.py 3/7 → DAL(config) requires 'sources' arg → fix DAL API or verify_install
#   P3. .gitignore deleted (unstaged) → restore from outputs
#   P4. Ruff-fixed files + new scripts unstaged → git add
#   P5. All French comments/docs → English (this protocol)
#
# Agents:
#   Claude Haiku  — translation review (French → English), fast, low cost
#   Nemotron 3    — code comment translation in-place, already in the loop
#   Claude Chat   — orchestration, gate decisions (this document)
#   Claude Code   — execution only, no architecture decisions

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 0 — IMMEDIATE FIXES (local, before any translation)
# Time estimate: ~30 min
# ═══════════════════════════════════════════════════════════════════════════════

## P1 — Fix dev.sh mypy --quiet flag
# mypy 2.0.0 dropped --quiet. Replace with 2>/dev/null redirect or remove flag.
# Pattern: Delta-Only Refactoring — touch only the broken line.

# In scripts/dev.sh, find the mypy invocation and change:
#   mypy dal/ --quiet
# to:
#   mypy dal/ 2>/dev/null
# or if mypy is optional in dev gate:
#   mypy dal/ || true   # TD — mypy 2.0.0 flag change, track separately

## P2 — Fix verify_install.py: DAL.__init__ requires 'sources'
# The DAL class requires a 'sources' argument beyond DALConfig.
# verify_install.py must reflect the real constructor signature.
# Two sub-options:
#
#   P2-A (preferred): DAL(config) should work with default sources
#     → Add default: def __init__(self, config: DALConfig, sources=None)
#     → sources=None means "use default adapters from config"
#     → This is the correct public API for an installable library
#
#   P2-B (fallback): verify_install.py passes explicit sources
#     → from dal.adapters.kraken import KrakenAdapter
#     → dal_instance = DAL(config, sources=[KrakenAdapter()])
#
# DECISION REQUIRED from Andrei before execution.
# Recommendation: P2-A — a library that requires internal implementation
# details at construction is not user-friendly. DAL(config) must work.

## P3 — Restore .gitignore
# cp outputs/.gitignore .gitignore
# git add .gitignore

## P4 — Stage all pending changes
# git add dal/adapters/dukascopy.py dal/adapters/kraken.py dal/adapters/yahoo.py
# git add dal/core/handoff.py dal/interfaces/source.py
# git add halo/anamnese_state.yaml scripts/verify_install.py
# git add tests/test_dukascopy_adapter.py tests/test_integration.py tests/test_yahoo_adapter.py
# git add scripts/cleanup_repo.sh scripts/fix_ruff.sh .gitignore
# git commit -m "fix: ruff corrections + cleanup + gitignore pre-v0.1.0"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — TRANSLATION INVENTORY
# What needs to be in English for open-source publication
# ═══════════════════════════════════════════════════════════════════════════════

## Scope: what MUST be translated
# Priority 1 — PUBLIC SURFACE (user-facing, PyPI, GitHub)
#   README.md                    → full rewrite in English (already has English example)
#   CHANGELOG.md                 → translate section headers and descriptions
#   pyproject.toml               → description field (already English?)
#
# Priority 2 — CODE (inline comments, docstrings, error messages)
#   dal/adapters/yahoo.py        → French comments in fetch(), _normalize()
#   dal/adapters/kraken.py       → French comments in pagination loop
#   dal/adapters/dukascopy.py    → French comments
#   dal/core/handoff.py          → French docstrings + comments
#   dal/core/pipeline.py         → French comments
#   dal/core/sources.py          → French comments
#   dal/core/assembler.py        → French comments (if any)
#   dal/core/config.py           → French comments (if any)
#   dal/exceptions.py            → French error messages in exceptions
#   dal/interfaces/source.py     → French comments
#
# Priority 3 — TESTS (pytest output is public on CI)
#   tests/conftest.py            → French skip messages
#   tests/test_*.py              → French docstrings + assert messages
#
# Priority 4 — SCRIPTS (semi-public, visible on GitHub)
#   scripts/dev.sh               → French echo messages
#   scripts/adversarial_dal_check_p3.py  → French section headers, messages
#   scripts/adversarial_dal_check.py     → same
#   scripts/validate_dal_state.py        → French messages
#   scripts/validate_environment.py      → French messages
#   scripts/verify_install.py            → French messages (to be rewritten anyway)
#
# Scope: what can STAY in French (internal, not public)
#   halo/                        → internal governance, not on GitHub public
#   docs/archive/                → archived, not surfaced
#   DAL_Phase3_Plan_v1.2.md      → internal plan, can move to halo/
#   DAL_SPECIFICATION_v1.0.md    → DECISION: translate or keep internal?
#     Recommendation: keep as-is in docs/ for now, add English summary in README
#     → Translating the full spec is a Phase 2 task, not a blocker for v0.1.0

## Files NOT to translate (keep as-is)
#   flake.nix / flake.lock       → Nix, universal
#   pyproject.toml               → TOML, mostly already English
#   uv.lock                      → generated
#   halo/protocols.yaml          → internal
#   halo/profil_stable.yaml      → internal
#   docs/kb/KB-DAL-*.md          → internal knowledge base


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — TRANSLATION EXECUTION (Haiku + Nemotron protocol)
# ═══════════════════════════════════════════════════════════════════════════════

## Agent assignment

# Claude Haiku — documents (README, CHANGELOG, long docstrings)
#   Strengths: fast, consistent tone, good technical English
#   Task: translate README.md fully, CHANGELOG.md headers,
#         review Nemotron output for Python files
#   Prompt template: see HAIKU_PROMPT below

# Nemotron 3 (OpenCode) — code comments in-place
#   Strengths: already has repo context, can edit files directly
#   Task: translate inline comments and short docstrings in dal/ and tests/
#   Constraint: MUST NOT change logic, only string literals in comments/docstrings
#   Prompt template: see NEMOTRON_PROMPT below

## Translation rules (to embed in prompts)
TRANSLATION_RULES = """
1. Translate French → English only. Do not modify any Python logic.
2. Preserve formatting: indentation, line length ≤ 88 chars (Ruff E501).
3. Technical terms are NOT translated: DALHandoff, assembly_hash, MIF-UID,
   AQI, MPI, OHLCV, DQF, DAL, SHA-256, NixOS, PyPI, PAXG, BTC.
4. Error messages in exceptions must be concise and actionable in English.
5. Test docstrings: use present tense ("Returns True when...", not "Retourne").
6. Comments explaining WHY are more important than comments explaining WHAT.
   Keep the meaning, not a word-for-word translation.
7. After translation, the file must pass: ruff check <file> --select E501
"""

## HAIKU_PROMPT — for README and CHANGELOG
HAIKU_PROMPT = """
You are translating technical documentation for an open-source Python library
called mif-dal (MIF Data Abstraction Layer), part of the MIF ecosystem for
quantitative finance data quality.

Translation rules:
{TRANSLATION_RULES}

Target audience: quantitative developers, data engineers, open-source contributors.
Tone: precise, technical, no marketing language. Follow numpy/pandas README style.

File to translate:
<file>
{FILE_CONTENT}
</file>

Return ONLY the translated file content. No preamble, no explanation.
"""

## NEMOTRON_PROMPT — for code files (inline comments only)
NEMOTRON_PROMPT = """
Translate all French comments and docstrings to English in the following Python file.
Do NOT modify any Python code logic, variable names, imports, or string literals
that are not comments or docstrings.

Rules:
- Line length ≤ 88 characters after translation (Ruff E501)
- Technical terms unchanged: DALHandoff, assembly_hash, AQI, MPI, DQF, OHLCV
- Error messages in raise statements: translate to concise English
- Preserve all indentation exactly
- After translation: ruff check <filename> must pass

File: {FILENAME}
<code>
{FILE_CONTENT}
</code>

Return ONLY the complete translated file. No explanation.
"""

## Execution sequence (Nemotron in OpenCode)
NEMOTRON_EXECUTION_ORDER = [
    # Lowest risk first (few French strings)
    "dal/exceptions.py",
    "dal/core/config.py",
    "dal/interfaces/source.py",
    # Core files
    "dal/core/handoff.py",
    "dal/core/pipeline.py",
    "dal/core/sources.py",
    # Adapters (most French content)
    "dal/adapters/yahoo.py",
    "dal/adapters/kraken.py",
    "dal/adapters/dukascopy.py",
    # Tests
    "tests/conftest.py",
    "tests/test_handoff.py",
    "tests/test_pipeline.py",
    "tests/test_sources.py",
    "tests/test_assembler.py",
    "tests/test_dal.py",
    "tests/test_config.py",
    "tests/test_exceptions.py",
    "tests/test_in_memory_source.py",
    "tests/test_source_interface.py",
    "tests/test_integration.py",
    "tests/test_kraken_adapter.py",
    "tests/test_yahoo_adapter.py",
    "tests/test_dukascopy_adapter.py",
    # Scripts
    "scripts/dev.sh",
    "scripts/adversarial_dal_check_p3.py",
    "scripts/adversarial_dal_check.py",
    "scripts/validate_dal_state.py",
    "scripts/validate_environment.py",
]

## Gate after each file (Nemotron executes this after translating each file)
POST_TRANSLATE_GATE = """
After translating {filename}:
1. ruff check {filename} --select E501,F401,F841
   → must pass (0 errors)
2. If {filename} is in dal/:
   python -m pytest tests/ -q --tb=no -x
   → must pass (no new failures)
3. If gate fails: revert the file (git checkout -- {filename})
   and flag for manual review.
"""

## Haiku review pass (after Nemotron completes all files)
HAIKU_REVIEW_PROMPT = """
Review the following translated Python file for:
1. Natural English (not literal translation artifacts)
2. Technical accuracy (does the comment still describe the correct behavior?)
3. Consistency with standard Python library documentation style
4. Any remaining French words or phrases

File: {FILENAME}
<code>
{FILE_CONTENT}
</code>

Return a list of issues only. Format:
  Line N: [issue type] description
  Example: Line 47: [awkward] "it permits to obtain" → "retrieves"

If no issues: return "LGTM"
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — GITHUB PUBLICATION (symbioticode account)
# ═══════════════════════════════════════════════════════════════════════════════

## 3.1 — Final local gate (run after all translations)
FINAL_LOCAL_GATE = """
# Must ALL pass before pushing to symbioticode

./scripts/dev.sh check
# → Ruff clean · mypy clean · (tests via pytest)

python -m pytest tests/ -q --tb=no
# → 169 passed, 8 skipped, 0 failed

python scripts/adversarial_dal_check_p3.py
# → 65/65 PASS

python scripts/verify_install.py
# → 7/7 PASS

grep -r "TODO\|FIXME\|HACK\|XXX" dal/ --include="*.py"
# → review list, resolve or convert to # TD-NNN format

grep -rl "[À-ÿ]" dal/ tests/ scripts/ --include="*.py" --include="*.sh"
# → must return empty (no French chars remaining in translated scope)
"""

## 3.2 — Commit strategy before push
COMMIT_STRATEGY = """
# Atomic commits — one per concern

git add .gitignore
git commit -m "chore: restore .gitignore"

git add dal/ tests/ scripts/
git commit -m "i18n: translate all French comments and docstrings to English"

git add README.md CHANGELOG.md
git commit -m "docs: rewrite README and CHANGELOG in English for open-source publication"

git add halo/anamnese_state.yaml
git commit -m "halo: update state post-cleanup and i18n"

# Tag
git tag -a v0.1.0 -m "mif-dal v0.1.0 — first public release
- DALHandoff: certified, traceable, immutable OHLCV stream
- Adapters: Kraken, Yahoo Finance, Dukascopy, InMemorySource
- 169/177 tests · 65/65 adversarial · coverage ≥ 80%
- Depends on mif-dqf ≥ 1.2.0"
"""

## 3.3 — Push to symbioticode (NOT to personal account)
GITHUB_PUSH = """
# Prerequisites:
#   - symbioticode org membership with write access to mif-dal repo
#   - SSH key or PAT configured for symbioticode

# Option A: repo already exists as symbioticode/mif-dal (forked or created)
git remote set-url origin git@github.com:symbioticode/mif-dal.git
git push origin main --tags

# Option B: repo does not exist yet
gh repo create symbioticode/mif-dal \\
  --public \\
  --description "MIF Data Abstraction Layer — certified OHLCV stream assembly" \\
  --homepage "https://pypi.org/project/mif-dal/" \\
  --push \\
  --source .

# After push: verify on GitHub
#   - README renders correctly (English, code example visible)
#   - No French text visible in top-level files
#   - Tags visible: v0.1.0
"""

## 3.4 — PyPI publication (from local, authenticated as symbioticode)
PYPI_PUBLICATION = """
# Build
uv build
# → dist/mif_dal-0.1.0-py3-none-any.whl
# → dist/mif_dal-0.1.0.tar.gz

# Test on TestPyPI first (always)
uv publish --index testpypi
pip install --index-url https://test.pypi.org/simple/ mif-dal==0.1.0
python -c "import dal; print(dal.__version__)"
# → 0.1.0

# Production PyPI (authenticated as symbioticode API token)
uv publish
# → https://pypi.org/project/mif-dal/

# Verify
pip install mif-dal==0.1.0
python scripts/verify_install.py
# → 7/7 PASS
"""

## 3.5 — Post-publication checklist
POST_PUBLICATION = """
□ PyPI page renders: https://pypi.org/project/mif-dal/
□ GitHub README renders correctly
□ pip install mif-dal works from a clean venv
□ verify_install.py passes from installed package (not editable)
□ mif-dqf README updated to mention mif-dal as companion package
□ anamnese_state.yaml updated: dal_status → "PUBLISHED v0.1.0"
□ KB-DAL-006.md created: lessons from Phase 3 + i18n process
□ MIF-Core Phase 0 spec: READY TO START
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION REQUIRED BEFORE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

DECISIONS_NEEDED = """
[D1] DAL API: should DAL(config) work without explicit 'sources' arg?
     → YES (recommended) → fix DAL.__init__ to have default sources
     → NO → fix verify_install.py to pass explicit sources
     Impact: affects public API, must decide before translation starts.

[D2] DAL_SPECIFICATION_v1.0.md: translate or keep French?
     → TRANSLATE (recommended for full open-source) → add to Haiku queue
     → KEEP FRENCH → add note in README: "Internal spec in French, English summary above"
     Impact: cosmetic only, does not affect publication gate.

[D3] halo/ directory: include in GitHub repo or .gitignore?
     → INCLUDE (current behavior) → halo/ visible on GitHub (governance docs in French)
     → EXCLUDE → add halo/ to .gitignore, keep only locally
     Recommendation: EXCLUDE from public repo. halo/ is internal governance.
     The public repo does not need to expose session protocols.
     Impact: cleaner public repo, no loss of functionality.

[D4] dukascopy/ directory (integration tests, shell.nix, guide):
     → INCLUDE → visible on GitHub, useful for NixOS users
     → EXCLUDE → add to .gitignore
     Recommendation: INCLUDE but translate DUKASCOPY_COMPLETE_GUIDE.md
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY — EXECUTION ORDER
# ═══════════════════════════════════════════════════════════════════════════════

EXECUTION_ORDER = """
[TODAY — local fixes]
  1. Decide D1–D4 (Andrei)
  2. Fix P1: dev.sh mypy flag
  3. Fix P2: DAL API or verify_install (depends on D1)
  4. Restore P3: .gitignore
  5. Stage P4: git add all pending
  6. git commit "fix: pre-publication local fixes"
  7. Run final local gate → all green

[SESSION 1 — translation (Nemotron + Haiku)]
  8. Nemotron: translate dal/ files in order (NEMOTRON_EXECUTION_ORDER)
     Gate after each file: ruff + pytest
  9. Haiku: translate README.md + CHANGELOG.md
 10. Haiku: review pass on Nemotron output (flag issues)
 11. Nemotron: apply Haiku fixes
 12. grep check: no French chars remaining in scope
 13. Full gate: dev.sh + pytest + adversarial + verify_install

[SESSION 2 — publication]
 14. git tag v0.1.0
 15. git remote set-url → symbioticode
 16. git push origin main --tags
 17. uv build + uv publish (TestPyPI first)
 18. uv publish (production PyPI)
 19. Post-publication checklist
 20. Update anamnese_state.yaml
 21. Create KB-DAL-006.md
 22. Open MIF-Core Phase 0
"""
