# HALO Migration Package — mif-dal
# Generated: 2026-05-11
# Trigger: Project directory corruption (cannot move conversations)
# Protocol: Standard HALO inter-session transfer
#
# HOW TO USE THIS DOCUMENT
# ─────────────────────────
# In the new Claude instance (new Project):
#   1. Upload this file as first message
#   2. Upload halo/anamnese_state.yaml
#   3. Upload docs/DAL_SPECIFICATION_v1.0.md
#   4. Say: "Reprends le projet MIF-DAL depuis ce snapshot HALO."
#
# The new instance reads Section 1 (state), then Section 2 (context),
# then asks for the current checklist output before proceeding.

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — CURRENT STATE (machine-readable)
# ═══════════════════════════════════════════════════════════════════════

state:
  date: "2026-05-11"
  module: "mif-dal"
  version: "v0.1.0"
  phase: "pre-publication — final cosmetic + GitHub push"
  repo_path: "~/Projects/51_MIF_DAL/mif-dal"
  repo_remote_target: "git@github.com:symbioticode/mif-dal.git"
  pypi_target: "mif-dal on PyPI (account: symbioticode)"

  gates:
    adversarial_p3: "65/65 PASS"
    pytest: "169/177 (8 skips réseau légitimes)"
    ruff: "CLEAN"
    mypy: "SKIP (not installed in venv — not a blocker)"
    dev_sh_check: "PASS (Ruff clean · Mypy SKIP · 169 passed)"

  open_items:
    - id: "OI-001"
      description: "verify_install.py 3/7 — DAL(config) requires 'sources' arg"
      priority: "medium — fix before PyPI, not before GitHub push"
      file: "scripts/verify_install.py"

    - id: "OI-002"
      description: "3 QA scripts not translated (adversarial_check*.py, dev.sh was FR — now EN)"
      priority: "low — scripts/local/ after restructure"
      note: "adversarial_dal_check_p3.py and adversarial_dal_check.py still in French"

    - id: "OI-003"
      description: "scripts/ not yet cleaned — too many scripts (11 → target 3-4)"
      priority: "medium — before PyPI"
      plan: |
        KEEP: dev.sh, validate_dal_state.py, test_install.py (renamed verify_install)
        MOVE to scripts/local/: cleanup_repo.sh, diagnose_and_fix_en.sh,
          fix_ruff.sh, translate_to_english.py, final_commit.sh, validate_environment.py
        MERGE into validate_dal_state.py: adversarial_dal_check*.py (--full flag)

    - id: "OI-004"
      description: "docs/ incomplete — API.md, ARCHITECTURE.md, TROUBLESHOOTING.md needed"
      priority: "medium — generated 2026-05-11, ready to copy"
      status: "GENERATED — files available in session outputs"

    - id: "OI-005"
      description: "README.md was a QUICKSTART — full README generated 2026-05-11"
      priority: "medium — generated, ready to copy"
      status: "GENERATED — file available in session outputs"

    - id: "OI-006"
      description: "halo/ must be added to .gitignore — internal governance, not public"
      priority: "HIGH — before GitHub push"

    - id: "OI-007"
      description: "GitHub push blocked — wrong SSH account (symbioticode vs dravitch)"
      priority: "HIGH — blocker for push"
      solution: "See Section 3 — SSH fix protocol"

    - id: "OI-008"
      description: "Project directory corruption — cannot move conversations"
      priority: "CRITICAL — this migration document is the response"

  completed_this_session:
    - "dev.sh --quiet flag removed (mypy 2.0 compat)"
    - "yahoo.py SettingWithCopyWarning fixed (inplace=True → reassignment)"
    - "diagnose_and_fix_en.sh run — 2 issues fixed"
    - "README.md rewritten (was QUICKSTART, now full explanation)"
    - "docs/API.md generated"
    - "docs/ARCHITECTURE.md generated"
    - "docs/TROUBLESHOOTING.md generated"
    - "pre_publication_plan.md finalized with arborescence cible"

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — PROJECT CONTEXT (human-readable, for new instance)
# ═══════════════════════════════════════════════════════════════════════

context: |
  MIF ECOSYSTEM — Architecture
  ─────────────────────────────
  Three PyPI packages in sequence:
    mif-dqf (STABLE v1.2.0.post1) → mif-dal (v0.1.0 pre-pub) → mif-core (not started)

  Two QAAF Studio protocols (NOT PyPI):
    QS-PAF (pair adequacy) · QS-MÉTIS (OOS validation)

  mif-dal SINGLE RESPONSIBILITY:
  "Assemble a certified, traceable OHLCV stream from external sources."
  One call per asset (D-DAL-007). Caller composes pairs.
  Output: DALHandoff (frozen dataclass, 15 fields, SHA-256 anchored).

  KEY ARCHITECTURAL DECISIONS (all CLOSED):
    D-DAL-006: assembly_hash on raw data BEFORE any transformation
    D-DAL-007: one asset per call — no pair logic in DAL
    D-DAL-008: Kraken data ~12 months rolling — tests use start >= today-11months
    D-DAL-005: DQF VOID → exception. DQF WARNING → emit with flag.

  GOVERNANCE SYSTEM (HALO):
    halo/anamnese_state.yaml — canonical state, read FIRST each session
    halo/protocols.yaml — collaboration rules
    halo/profil_stable.yaml — stable preferences
    KB-DAL-001..005 in docs/kb/ — session knowledge base

  COLLABORATION CONTRACT:
    - No code without validated architecture
    - Max 3 alternatives when proposing options
    - Pattern #19 (Spec Before Session): read anamnese_state.yaml first
    - Pattern #17 (Validate Before Automate): confirm manually before scripting

  INSTANCE ROLES:
    Claude Chat (Orchestratrice) — architecture decisions, this document
    Claude Code / Nemotron 3 — implementation execution

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3 — SSH FIX PROTOCOL (symbioticode push)
# ═══════════════════════════════════════════════════════════════════════

ssh_fix: |
  PROBLEM: Two GitHub accounts on same machine.
    dravitch    — personal account, default SSH key (id_ed25519)
    symbioticode — org account, named key (id_ed25519_symbioticode)

  DIAGNOSIS TOOL:
    ssh -T git@github.com
    → "Hi dravitch!"  means wrong key is being used

  SOLUTION A — ~/.ssh/config (recommended, permanent):

    # ~/.ssh/config — add at top
    Host github-symbioticode
        HostName github.com
        User git
        IdentityFile ~/.ssh/id_ed25519_symbioticode
        IdentitiesOnly yes

    Host github-dravitch
        HostName github.com
        User git
        IdentityFile ~/.ssh/id_ed25519_dravitch
        IdentitiesOnly yes

    Then change remote URL:
      git remote set-url origin git@github-symbioticode:symbioticode/mif-dal.git

    Verify:
      ssh -T git@github-symbioticode
      → "Hi symbioticode!"

  SOLUTION B — One-shot push with explicit identity:
    GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_symbioticode -o IdentitiesOnly=yes' \
      git push origin main --tags

  SOLUTION C — If no symbioticode SSH key exists yet:
    1. Generate: ssh-keygen -t ed25519 -C "symbioticode" -f ~/.ssh/id_ed25519_symbioticode
    2. Add public key to GitHub: github.com → Settings → SSH keys (logged in as symbioticode)
    3. Apply Solution A

  VERIFY BEFORE PUSH:
    ssh -T git@github-symbioticode
    git remote -v  # must show git@github-symbioticode:symbioticode/mif-dal.git

# ═══════════════════════════════════════════════════════════════════════
# SECTION 4 — TARGET FILE TREE (after pre-publication cleanup)
# ═══════════════════════════════════════════════════════════════════════

target_tree: |
  mif-dal/
  ├── CHANGELOG.md
  ├── CONTRIBUTING.md                    ← TO CREATE (mirror mif-dqf)
  ├── LICENSE
  ├── README.md                          ← DONE (2026-05-11)
  ├── pyproject.toml
  ├── pytest.ini
  ├── flake.nix
  ├── flake.lock
  ├── uv.lock
  │
  ├── dal/
  │   ├── __init__.py                    # dal.__all__, dal.__version__
  │   ├── dal.py                         # DAL class — public entry point
  │   ├── exceptions.py
  │   ├── adapters/
  │   │   ├── __init__.py
  │   │   ├── dukascopy.py
  │   │   ├── in_memory.py
  │   │   ├── kraken.py
  │   │   └── yahoo.py
  │   ├── core/
  │   │   ├── __init__.py
  │   │   ├── assembler.py
  │   │   ├── config.py
  │   │   ├── handoff.py
  │   │   ├── pipeline.py
  │   │   └── sources.py
  │   └── interfaces/
  │       ├── __init__.py
  │       └── source.py
  │
  ├── tests/
  │   ├── conftest.py
  │   ├── test_assembler.py
  │   ├── test_config.py
  │   ├── test_dal.py
  │   ├── test_dukascopy_adapter.py
  │   ├── test_exceptions.py
  │   ├── test_handoff.py
  │   ├── test_in_memory_source.py
  │   ├── test_integration.py
  │   ├── test_kraken_adapter.py
  │   ├── test_pipeline.py
  │   ├── test_source_interface.py
  │   ├── test_sources.py
  │   └── test_yahoo_adapter.py
  │
  ├── scripts/
  │   ├── dev.sh                         # pre-commit gate (public)
  │   ├── validate_dal_state.py          # GO/NO-GO + adversarial (public)
  │   │                                  # --full flag merges adversarial_check*.py
  │   ├── test_install.py                # post-install check (renamed verify_install)
  │   └── local/                         # internal tools — not for contributors
  │       ├── cleanup_repo.sh
  │       ├── diagnose_and_fix_en.sh
  │       ├── fix_ruff.sh
  │       ├── final_commit.sh
  │       ├── translate_to_english.py
  │       └── validate_environment.py
  │
  ├── docs/
  │   ├── API.md                         ← DONE (2026-05-11)
  │   ├── ARCHITECTURE.md                ← DONE (2026-05-11)
  │   ├── TROUBLESHOOTING.md             ← DONE (2026-05-11)
  │   ├── DAL_SPECIFICATION_v1.0.md      # formal spec — source of truth
  │   ├── kb/
  │   │   ├── KB-DAL-001.md
  │   │   ├── KB-DAL-002.md
  │   │   ├── KB-DAL-003.md
  │   │   ├── KB-DAL-004.md
  │   │   └── KB-DAL-005.md
  │   └── archive/
  │       ├── DAL_Phase3_Plan_v1.1.md
  │       ├── DAL_Phase3_Plan_v1.2.md
  │       ├── ISSUE-DAL-P3-001.md
  │       └── [other archived files]
  │
  ├── dukascopy/                         # NixOS setup for dukascopy-node
  │   ├── DUKASCOPY_COMPLETE_GUIDE.md
  │   ├── setup_dukascopy_mif.sh
  │   ├── shell.nix
  │   ├── conftest.py
  │   └── test_dukascopy_integration.py
  │
  └── .gitignore                         # includes: halo/ · .dal_cache/ · __pycache__/

  NOT in repo (gitignored):
    halo/                                # internal HALO governance
    .dal_cache/                          # runtime cache
    .venv/                               # Python environment
    __pycache__/                         # compiled Python

  NOT in repo (no examples/ directory):
    examples/                            # architectural decision — DAL has no examples
                                         # (mif-dqf has examples; DAL is infrastructure)

# ═══════════════════════════════════════════════════════════════════════
# SECTION 5 — IMMEDIATE NEXT ACTIONS (ordered)
# ═══════════════════════════════════════════════════════════════════════

next_actions:
  - step: 1
    action: "Copy generated docs to repo"
    commands: |
      cp README.md ~/Projects/51_MIF_DAL/mif-dal/README.md
      cp API.md ~/Projects/51_MIF_DAL/mif-dal/docs/API.md
      cp ARCHITECTURE.md ~/Projects/51_MIF_DAL/mif-dal/docs/ARCHITECTURE.md
      cp TROUBLESHOOTING.md ~/Projects/51_MIF_DAL/mif-dal/docs/TROUBLESHOOTING.md

  - step: 2
    action: "Add halo/ to .gitignore"
    commands: |
      echo "" >> .gitignore
      echo "# Internal HALO governance — not for public repo" >> .gitignore
      echo "halo/" >> .gitignore

  - step: 3
    action: "Remove halo/ from git tracking if already staged"
    commands: |
      git rm -r --cached halo/ 2>/dev/null || true
      git add .gitignore

  - step: 4
    action: "Fix SSH for symbioticode — apply Solution A from Section 3"
    note: "Required before any push"

  - step: 5
    action: "Initial commit to symbioticode/mif-dal"
    commands: |
      git add README.md docs/API.md docs/ARCHITECTURE.md docs/TROUBLESHOOTING.md
      git commit -m "docs: complete documentation suite (README, API, ARCHITECTURE, TROUBLESHOOTING)"
      git remote set-url origin git@github-symbioticode:symbioticode/mif-dal.git
      git push origin main

  - step: 6
    action: "scripts/ cleanup — merge adversarial checks + create scripts/local/"
    priority: "before PyPI, not before GitHub push"

  - step: 7
    action: "Fix verify_install.py → test_install.py (OI-001)"
    priority: "before PyPI"

  - step: 8
    action: "uv build + uv publish (TestPyPI first)"
    prerequisite: "All OI items resolved, dev.sh check PASS"

  - step: 9
    action: "Update anamnese_state.yaml → dal_status: PUBLISHED v0.1.0"

  - step: 10
    action: "Create KB-DAL-006.md — lessons from Phase 3 + i18n + publication"

  - step: 11
    action: "Open MIF-Core Phase 0 spec"
    prerequisite: "mif-dal v0.1.0 published on PyPI"
