# tests/conftest.py
"""
Configuration pytest pour mif-dal.

Marks enregistrés :
  @pytest.mark.network — tests qui font de vrais appels réseau.
  Ces tests sont skippés par défaut en CI et en env sans réseau.

Usage :
  pytest                          # exclut les tests network
  pytest -m network               # uniquement les tests réseau
  pytest -m "not network"         # explicitement sans réseau
  pytest --run-network            # inclut les tests réseau
"""

import shutil
import subprocess

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Inclure les tests qui font de vrais appels réseau.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "network: test qui fait de vrais appels réseau — skippé par défaut en CI.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip automatique des tests @pytest.mark.network sauf si --run-network."""
    if config.getoption("--run-network"):
        return  # on laisse tout passer

    skip_network = pytest.mark.skip(
        reason="Test réseau ignoré par défaut. Utiliser --run-network pour l'inclure."
    )
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


# ─── Fixtures communes ────────────────────────────────────────────────────────


@pytest.fixture
def dukascopy_available() -> bool:
    """True si dukascopy-node est installé et accessible."""
    return shutil.which("dukascopy-node") is not None or _npx_dukascopy_available()


def _npx_dukascopy_available() -> bool:
    try:
        result = subprocess.run(
            ["npx", "dukascopy-node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
def skip_if_no_dukascopy(dukascopy_available: bool) -> None:
    """Skip le test si dukascopy-node n'est pas disponible."""
    if not dukascopy_available:
        pytest.skip(
            "dukascopy-node non disponible. "
            "Exécuter setup_dukascopy_mif.sh puis relancer."
        )


@pytest.fixture
def skip_if_no_network() -> None:
    """Skip le test si le réseau n'est pas accessible."""
    try:
        import socket

        socket.create_connection(("api.kraken.com", 443), timeout=3)
    except OSError:
        pytest.skip("Réseau non accessible.")
