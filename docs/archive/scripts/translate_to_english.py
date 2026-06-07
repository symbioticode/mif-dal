#!/usr/bin/env python3
"""
translate_to_english.py — French → English translation driver for mif-dal
Calls Claude Haiku API for each file in scope.

Usage:
  python scripts/translate_to_english.py --dry-run       # show what would be translated
  python scripts/translate_to_english.py --file dal/exceptions.py
  python scripts/translate_to_english.py --all            # all files in scope
  python scripts/translate_to_english.py --docs           # README + CHANGELOG only

Requirements:
  pip install anthropic
  ANTHROPIC_API_KEY set in environment

Gate after each file:
  ruff check <file> --select E501,F401,F841   → must pass
  pytest tests/ -q --tb=no -x                → must pass (for dal/ files)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Files in scope ────────────────────────────────────────────────────────────
CODE_FILES = [
    # Lowest risk first
    "dal/exceptions.py",
    "dal/core/config.py",
    "dal/interfaces/source.py",
    "dal/core/handoff.py",
    "dal/core/pipeline.py",
    "dal/core/sources.py",
    "dal/adapters/yahoo.py",
    "dal/adapters/kraken.py",
    "dal/adapters/dukascopy.py",
    "dal/adapters/in_memory.py",
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
    "scripts/adversarial_dal_check_p3.py",
    "scripts/adversarial_dal_check.py",
    "scripts/validate_dal_state.py",
    "scripts/validate_environment.py",
]

DOC_FILES = [
    "README.md",
    "CHANGELOG.md",
]

SHELL_FILES = [
    "scripts/dev.sh",
]

# ── Detection: does this file have French? ────────────────────────────────────
FRENCH_PATTERN = re.compile(
    r"[àâäéèêëîïôùûüÿœæçÀÂÄÉÈÊËÎÏÔÙÛÜŸŒÆÇ]|"
    r"\b(est|sont|avec|pour|dans|les|des|une|qui|par|sur|"
    r"pas|mais|tout|cette|tous|peut|doit|sera|après|avant|"
    r"Vérifier|Créer|Supprimer|Utiliser|Retourner|Calculer|"
    r"valide|invalide|données|résultat|erreur|fichier|source)\b"
)


def has_french(content: str) -> bool:
    """Quick heuristic: does file contain French text?"""
    return bool(FRENCH_PATTERN.search(content))


def detect_french_files(root: Path) -> list[Path]:
    """Scan all in-scope files for French content."""
    results = []
    for rel in CODE_FILES + DOC_FILES + SHELL_FILES:
        p = root / rel
        if p.exists():
            content = p.read_text(errors="replace")
            if has_french(content):
                results.append(p)
    return results


# ── Prompts ───────────────────────────────────────────────────────────────────
CODE_SYSTEM = """You are a technical translator working on an open-source Python library
for quantitative finance (mif-dal, part of the MIF ecosystem).

Your task: translate French comments and docstrings to English.

STRICT RULES:
1. Translate ONLY: # comments, docstrings (triple-quoted strings used as docs),
   and string literals inside raise statements.
2. Do NOT modify: Python logic, variable names, imports, f-string expressions,
   test assertions, or any non-comment string values.
3. Line length ≤ 88 characters after translation (PEP 8 / Ruff E501).
   Split long comments across multiple lines if needed.
4. Technical terms are NEVER translated:
   DALHandoff, assembly_hash, AQI, MPI, DQF, OHLCV, SHA-256,
   NixOS, PyPI, PAXG, BTC, MIF-UID, FetchRequest, FetchResult,
   DALConfig, DALError, InMemorySource, KrakenAdapter, YahooAdapter,
   DukascopyAdapter, get_certified_stream, get_diagnostic_stream.
5. Error messages must be concise and actionable in English.
6. Preserve all indentation exactly.
7. Return ONLY the complete translated file. No explanation, no markdown fences."""

DOC_SYSTEM = """You are a technical writer translating documentation for an open-source
Python library called mif-dal (MIF Data Abstraction Layer).

The library assembles certified OHLCV trading data streams for quantitative finance.
Target audience: quantitative developers and data engineers.

RULES:
1. Translate French → English fully.
2. Style: precise, technical, no marketing language. Follow numpy/pandas README style.
3. Technical terms unchanged: DALHandoff, assembly_hash, MIF-UID, AQI, MPI,
   OHLCV, DQF, DAL, SHA-256, PAXG, BTC, NixOS, PyPI.
4. Code blocks are NOT translated (Python, shell, TOML).
5. Return ONLY the translated document. No explanation."""

CODE_USER = """Translate all French in this file to English.

File: {filename}

<code>
{content}
</code>"""

DOC_USER = """Translate this document from French to English.

File: {filename}

<document>
{content}
</document>"""


# ── API call ──────────────────────────────────────────────────────────────────
def translate_file(path: Path, is_doc: bool = False) -> str:
    """Call Claude Haiku to translate a file. Returns translated content."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content = path.read_text()

    system = DOC_SYSTEM if is_doc else CODE_SYSTEM
    user_template = DOC_USER if is_doc else CODE_USER

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        system=system,
        messages=[
            {
                "role": "user",
                "content": user_template.format(
                    filename=path.name,
                    content=content,
                ),
            }
        ],
    )

    translated = response.content[0].text.strip()

    # Strip accidental markdown fences
    if translated.startswith("```"):
        lines = translated.split("\n")
        translated = (
            "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
        )

    return translated


# ── Gate: ruff + pytest ───────────────────────────────────────────────────────
def run_gate(path: Path, root: Path) -> bool:
    """Run ruff + pytest after translation. Returns True if all pass."""
    # Ruff
    result = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "ruff",
            "check",
            str(path),
            "--select",
            "E501,F401,F841",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ✗ RUFF FAIL:\n{result.stdout}")
        return False
    print("  ✓ ruff")

    # Pytest (only for dal/ and tests/ files)
    if str(path).startswith(str(root / "dal")) or str(path).startswith(
        str(root / "tests")
    ):
        result = subprocess.run(
            [".venv/bin/python", "-m", "pytest", "tests/", "-q", "--tb=short", "-x"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ✗ PYTEST FAIL:\n{result.stdout[-2000:]}")
            return False
        # Extract summary
        lines = result.stdout.strip().split("\n")
        summary = lines[-1] if lines else "no output"
        print(f"  ✓ pytest: {summary}")

    return True


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Translate mif-dal French → English")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show French files, don't translate"
    )
    parser.add_argument("--file", help="Translate a single file")
    parser.add_argument(
        "--all", action="store_true", help="Translate all in-scope files"
    )
    parser.add_argument(
        "--docs", action="store_true", help="Translate README + CHANGELOG only"
    )
    args = parser.parse_args()

    root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )

    if args.dry_run:
        print("=== French content detected in ===")
        french_files = detect_french_files(root)
        for f in french_files:
            print(f"  {f.relative_to(root)}")
        print(f"\nTotal: {len(french_files)} files")
        print("\nRun with --all to translate, or --file <path> for a single file.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Build file list
    if args.file:
        targets = [(Path(args.file), Path(args.file).suffix == ".md")]
    elif args.docs:
        targets = [(root / f, True) for f in DOC_FILES if (root / f).exists()]
    elif args.all:
        targets = []
        for rel in CODE_FILES + SHELL_FILES:
            p = root / rel
            if p.exists() and has_french(p.read_text(errors="replace")):
                targets.append((p, False))
        for rel in DOC_FILES:
            p = root / rel
            if p.exists():
                targets.append((p, True))
    else:
        parser.print_help()
        return

    print(f"=== Translation: {len(targets)} file(s) ===\n")
    failures = []

    for path, is_doc in targets:
        rel = path.relative_to(root) if path.is_absolute() else path
        print(f"[{rel}]")

        if not path.exists():
            print("  ~ skip (not found)")
            continue

        content = path.read_text()
        if not has_french(content) and not is_doc:
            print("  ~ skip (no French detected)")
            continue

        # Backup
        backup = path.with_suffix(path.suffix + ".pre-i18n")
        backup.write_text(content)

        # Translate
        print("  → calling Haiku...")
        try:
            translated = translate_file(path, is_doc=is_doc)
        except Exception as e:
            print(f"  ✗ API ERROR: {e}")
            failures.append(str(rel))
            backup.unlink()
            continue

        # Write
        path.write_text(translated)

        # Gate
        if not run_gate(path, root):
            print("  ✗ Gate failed — reverting")
            path.write_text(content)  # restore original
            backup.unlink()
            failures.append(str(rel))
            print(f"  ⚠ {rel} flagged for manual review")
        else:
            backup.unlink()
            print(f"  ✓ {rel} translated and gate passed\n")

    # Summary
    print("\n" + "=" * 60)
    total = len(targets)
    done = total - len(failures)
    print(f"Translation complete: {done}/{total} files")
    if failures:
        print("\nFailed / flagged for manual review:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("\nAll files translated. Run final gate:")
        print("  ./scripts/dev.sh check")
        print("  python -m pytest tests/ -q --tb=no")
        print("  python scripts/adversarial_dal_check_p3.py")
        print("  grep -rl '[À-ÿ]' dal/ tests/ --include='*.py'  # must be empty")


if __name__ == "__main__":
    main()
