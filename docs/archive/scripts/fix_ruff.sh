#!/usr/bin/env bash
# fix_ruff.sh — Corrections Ruff ciblées pour passer dev.sh check
# Source : checklist_pass65-65.txt + output dev.sh check
# Appliquer depuis la racine du projet mif-dal
# Usage : bash scripts/fix_ruff.sh

set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "=== fix_ruff.sh — corrections Ruff ciblées ==="

# ─── dal/adapters/dukascopy.py ────────────────────────────────────────────────
# F841 : stderr assigné mais non utilisé → supprimer l'assignation
# E501 : message d'erreur trop long → couper sur deux lignes
python3 - <<'PYEOF'
import re, pathlib

p = pathlib.Path("dal/adapters/dukascopy.py")
src = p.read_text()

# F841 : "stderr = proc.stderr.decode(errors="replace")[:200]"
# → utiliser directement dans l'appel (ou supprimer — la variable est inutilisée)
src = src.replace(
    '                stderr = proc.stderr.decode(errors="replace")[:200]\n',
    '',
)

# E501 ligne 245 : error=f"CSV Dukascopy trop petit..." > 88 chars
old = '                    error=f"CSV Dukascopy trop petit ({len(raw_bytes)} bytes) — données absentes",'
new = (
    '                    error=(\n'
    '                        f"CSV Dukascopy trop petit ({len(raw_bytes)} bytes)"'
    '\n                        " — données absentes"\n'
    '                    ),'
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ dukascopy.py patché")
PYEOF

# ─── dal/adapters/kraken.py ───────────────────────────────────────────────────
# E501 : 4 commentaires trop longs → couper
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("dal/adapters/kraken.py")
src = p.read_text()

replacements = [
    (
        "            # (since we can only get newer data with 'since', and we're looking for older data)",
        "            # (since we can only get newer data with 'since',\n"
        "            #  and we're looking for older data)",
    ),
    (
        "            # So to get older data, we use the oldest timestamp from what we just received",
        "            # So to get older data, use the oldest timestamp\n"
        "            # from what we just received",
    ),
    (
        "            # Kraken returns max 720 candles per call, so we should break after reasonable attempts",
        "            # Kraken returns max 720 candles per call,\n"
        "            # so we break after reasonable attempts",
    ),
    (
        "            # But we'll let the logic above handle termination based on data availability",
        "            # The logic above handles termination based on data availability",
    ),
]

for old, new in replacements:
    if old in src:
        src = src.replace(old, new)
        print(f"  ✓ kraken.py : ligne raccourcie")
    else:
        print(f"  ! kraken.py : pattern non trouvé (déjà corrigé ?): {old[:60]}...")

p.write_text(src)
print("  ✓ kraken.py patché")
PYEOF

# ─── dal/adapters/yahoo.py ────────────────────────────────────────────────────
# F601 : clé "1H" dupliquée → garder "1H": "1h" (format plus standard), supprimer "1H": "60m"
# E501 : commentaire trop long → couper
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("dal/adapters/yahoo.py")
src = p.read_text()

# F601 : supprimer la première occurrence "1H": "60m"
src = src.replace('        "1H": "60m",\n', '', 1)

# E501 : commentaire ligne 267
old = '        # Yahoo Finance est généralement fiable, on considère "success" si on a des données'
new = (
    '        # Yahoo Finance est généralement fiable ;\n'
    '        # on considère "success" si on a des données'
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ yahoo.py patché")
PYEOF

# ─── dal/core/handoff.py ─────────────────────────────────────────────────────
# E501 : deux lignes trop longues dans les commentaires/messages
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("dal/core/handoff.py")
src = p.read_text()

# E501 ligne 107 : f"coverage must be one of..."
old = '                f"coverage must be one of {sorted(_VALID_COVERAGE)}, got {self.coverage!r}"'
new = (
    '                f"coverage must be one of "\n'
    '                f"{sorted(_VALID_COVERAGE)}, got {self.coverage!r}"'
)
src = src.replace(old, new)

# E501 ligne 115 : commentaire FAIL/VOID
old = '        # FAIL/VOID never reach a DALHandoff — they raise DALHandoffError upstream (D-DAL-005).'
new = (
    '        # FAIL/VOID never reach a DALHandoff — they raise\n'
    '        # DALHandoffError upstream (D-DAL-005).'
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ handoff.py patché")
PYEOF

# ─── dal/interfaces/source.py ────────────────────────────────────────────────
# E501 ligne 32 : commentaire inline trop long → déplacer sur ligne séparée
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("dal/interfaces/source.py")
src = p.read_text()

old = '    fallback: bool = False  # adapter cannot know its rank; resolver authoritatively sets this in the manifest entry'
new = (
    '    # Adapter cannot know its own rank in the fallback chain;\n'
    '    # the resolver sets this authoritatively in the source manifest.\n'
    '    fallback: bool = False'
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ source.py patché")
PYEOF

# ─── tests/test_dukascopy_adapter.py ─────────────────────────────────────────
# F841 : df assigné mais non utilisé → remplacer par _
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("tests/test_dukascopy_adapter.py")
src = p.read_text()

src = src.replace(
    '    df = adapter._parse_csv(raw)\n',
    '    adapter._parse_csv(raw)  # appel pour vérifier l\'absence d\'exception\n',
)

p.write_text(src)
print("  ✓ test_dukascopy_adapter.py patché")
PYEOF

# ─── tests/test_integration.py ───────────────────────────────────────────────
# E501 : 3 lignes trop longues (commentaires + f-string)
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("tests/test_integration.py")
src = p.read_text()

# E501 ligne 30
old = '    # Utiliser des dates récentes que Kraken supporte (données disponibles à partir de mi-2024)'
new = (
    '    # Utiliser des dates récentes que Kraken supporte\n'
    '    # (données disponibles à partir de mi-2024)'
)
src = src.replace(old, new)

# E501 ligne 95 : f-string assertion trop longue
old = (
    '            f"Expected exactly one successful entry, got: '
    '{[e[\'source_id\'] for e in result.source_manifest]}"'
)
new = (
    '            "Expected exactly one successful entry, got: "\n'
    '            f"{[e[\'source_id\'] for e in result.source_manifest]}"'
)
src = src.replace(old, new)

# E501 ligne 139
old = '    # Les hashes doivent être différents (différentes sources, mêmes données => hash différent)'
new = (
    '    # Les hashes doivent être différents\n'
    '    # (différentes sources, mêmes données => hash différent)'
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ test_integration.py patché")
PYEOF

# ─── tests/test_yahoo_adapter.py ─────────────────────────────────────────────
# E501 : 2 lignes (docstring + f-string assertion)
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("tests/test_yahoo_adapter.py")
src = p.read_text()

# E501 ligne 315 : docstring trop longue
old = '    """Quand le fallback est désactivé et qu\'on a peu de lignes, on retourne les données disponibles."""'
new = (
    '    """Quand le fallback est désactivé et qu\'on a peu de lignes,\n'
    '    on retourne les données disponibles."""'
)
src = src.replace(old, new)

# E501 ligne 385
old = "        f\"PAXG-USD indisponible sur Yahoo Finance : {getattr(result, 'error', 'unknown')}\""
new = (
    "        \"PAXG-USD indisponible sur Yahoo Finance : \"\n"
    "        f\"{getattr(result, 'error', 'unknown')}\""
)
src = src.replace(old, new)

p.write_text(src)
print("  ✓ test_yahoo_adapter.py patché")
PYEOF

echo ""
echo "=== Vérification Ruff post-patch ==="
.venv/bin/python -m ruff check dal/ tests/ --select E501,F841,F601
echo "=== FIN fix_ruff.sh ==="
