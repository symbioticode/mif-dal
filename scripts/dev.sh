#!/usr/bin/env bash
# dev.sh — Pre-commit gate for mif-dal
# Usage: ./scripts/dev.sh check
# All checks must pass before committing or publishing.

set -euo pipefail

CMD="${1:-help}"

if [ "$CMD" = "check" ]; then
    echo "=== Pre-commit gate ==="

    # 1/3 — Ruff
    echo "[INFO] 1/3 Ruff..."
    if .venv/bin/python -m ruff check dal/ tests/; then
        echo "[OK]   Ruff clean"
    else
        echo "[ERR]  Ruff errors"
        exit 1
    fi

    # 2/3 — Mypy (optional — skipped if not installed)
    echo "[INFO] 2/3 Mypy..."
    if .venv/bin/python -m mypy --version > /dev/null 2>&1; then
        if .venv/bin/python -m mypy dal/; then
            echo "[OK]   Mypy clean"
        else
            echo "[ERR]  Mypy errors"
            exit 1
        fi
    else
        echo "[SKIP] Mypy not installed — run: uv add --dev mypy"
    fi

    # 3/3 — Pytest
    echo "[INFO] 3/3 Pytest..."
    if .venv/bin/python -m pytest tests/ -q --tb=short; then
        echo "[OK]   All tests passed"
    else
        echo "[ERR]  Test failures"
        exit 1
    fi

    echo ""
    echo "[PASS] Gate complete"

elif [ "$CMD" = "help" ]; then
    echo "Usage: ./scripts/dev.sh check"
else
    echo "Unknown command: $CMD"
    exit 1
fi
