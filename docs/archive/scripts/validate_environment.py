#!/usr/bin/env python3
"""
validate_environment.py — mif-dal v0.1.0 prerequisites
Usage: python scripts/validate_environment.py
"""

import platform
import subprocess
import sys

CHECKS = []


def check(label):
    def decorator(fn):
        CHECKS.append((label, fn))
        return fn

    return decorator


# ── Python & packages ────────────────────────────────────────────────────────


@check("Python >= 3.11")
def python_version():
    assert sys.version_info >= (3, 11), f"Python {sys.version_info} < 3.11"


@check("mif-dqf importable")
def dqf_import():
    from dqf import DQFReport  # noqa


@check("yfinance >= 1.3.0")
def yfinance_version():
    import yfinance as yf
    from packaging.version import Version

    assert Version(yf.__version__) >= Version("1.3.0"), f"yfinance {yf.__version__}"


@check("pandas importable")
def pandas_import():
    import pandas as pd  # noqa


# ── Node.js & dukascopy-node ─────────────────────────────────────────────────


@check("Node.js available")
def node_available():
    r = subprocess.run(
        ["node", "--version"], capture_output=True, timeout=10, stdin=subprocess.DEVNULL
    )
    assert r.returncode == 0, "node not found in PATH"


@check("dukascopy-node installed (--help, not --version)")
def dukascopy_available():
    # IMPORTANT: --version returns exit code 1 even if installed
    # (upstream bug). Use --help (exit 0) for verification —
    # DUKASCOPY_COMPLETE_GUIDE §Installation
    for cmd in [["npx", "dukascopy-node", "--help"], ["dukascopy-node", "--help"]]:
        try:
            r = subprocess.run(
                cmd, capture_output=True, timeout=10, stdin=subprocess.DEVNULL
            )
            if r.returncode == 0:
                return  # OK
        except FileNotFoundError:
            continue
    raise AssertionError(
        "dukascopy-node not accessible.\n"
        "NixOS  : export NPM_GLOBAL=$HOME/.npm-global && "
        "npm install --prefix $NPM_GLOBAL -g dukascopy-node\n"
        "Others : npm install -g dukascopy-node"
    )


# ── Encoding (Windows) ────────────────────────────────────────────────────────


@check("Encoding stdout UTF-8 or compatible")
def encoding_check():
    enc = sys.stdout.encoding or ""
    if platform.system() == "Windows" and enc.upper() == "CP1252":
        # Warning, not a blocking failure
        print("  WARN : Windows CP1252 — avoid emojis in logs")


# ── mif-dal itself ────────────────────────────────────────────────────────


@check("dal importable")
def dal_import():
    import dal  # noqa


@check("dal.__version__ defined")
def dal_version():
    import dal

    assert hasattr(dal, "__version__"), "dal.__version__ missing"
    assert dal.__version__, "dal.__version__ empty"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Environment: {platform.system()} / Python {sys.version.split()[0]}")
    print("=" * 60)
    failed = []
    for label, fn in CHECKS:
        try:
            fn()
            print(f"  OK  {label}")
        except Exception as e:
            print(f"  FAIL {label}: {e}")
            failed.append(label)
    print("=" * 60)
    if failed:
        print(f"RESULT: NO-GO — {len(failed)} check(s) failed")
        sys.exit(1)
    else:
        print("RESULT: GO — environment ready")
