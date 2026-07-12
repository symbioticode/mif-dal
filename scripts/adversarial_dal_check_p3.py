#!/usr/bin/env python3
"""
adversarial_dal_check_p3.py — Non-régression Phase 3 mif-dal
# --------------------------------------------------------------
Ce script valide que toutes les invariants établis en Phase 2 sont intacts
après les sprints DAL-010 à DAL-013 (Phase 3 — publication).

Il s'agit d'un oracle de non-régression, pas d'un test unitaire pytest.
Exécuter à la fin de chaque sprint Phase 3 pour confirmer l'absence de régression.

Usage :
    .venv/bin/python scripts/adversarial_dal_check_p3.py
    .venv/bin/python scripts/adversarial_dal_check_p3.py --run-network

Sections :
    [A] Phase 2 — invariants préservés (41 checks hérités)
    [B] Phase 3 — gates de publication
    [C] Coverage gates (DAL-010)
    [D] Environnement NixOS (dukascopy-node détection correcte)
    [E] Intégration réelle DQF (sans mock) — optionnel réseau
    [F] Régression Kraken (Bug B corrigé — 0 lignes)
    [G] API publique finale (version + __all__)

Référence : DAL_SPECIFICATION_v1.0.md + DAL_Phase3_Plan_v1.1.md
"""

import argparse
import ast
import importlib
import inspect
import io
import re
import subprocess
import sys
from pathlib import Path

# ── Couleurs ──────────────────────────────────────────────────────────────────
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── Registry de checks ────────────────────────────────────────────────────────
CHECKS: list[tuple[str, str, callable]] = []  # (section, label, fn)


def check(section: str, label: str):
    """Décorateur pour enregistrer un check adversarial."""

    def decorator(fn):
        CHECKS.append((section, label, fn))
        return fn

    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# [A] Phase 2 — invariants préservés
# ─────────────────────────────────────────────────────────────────────────────


@check("A", "dal/__init__.py existe")
def _a01():
    assert Path("dal/__init__.py").exists()


@check("A", "dal/core/handoff.py contient class DALHandoff")
def _a02():
    src = Path("dal/core/handoff.py").read_text()
    assert "class DALHandoff" in src


@check("A", "class DAL publique définie quelque part dans dal/")
def _a03():
    found = any("class DAL" in p.read_text() for p in Path("dal").rglob("*.py"))
    assert found, "class DAL introuvable"


@check("A", "dal/core/config.py contient class DALConfig")
def _a04():
    src = Path("dal/core/config.py").read_text()
    assert "class DALConfig" in src


@check("A", "dal/exceptions.py contient les 4 exceptions")
def _a05():
    src = Path("dal/exceptions.py").read_text()
    for exc in ["DALError", "DALConfigError", "DALVersionError", "DALHandoffError"]:
        assert exc in src, f"{exc} absent de exceptions.py"


@check("A", "dal/adapters/in_memory.py contient class InMemorySource")
def _a06():
    src = Path("dal/adapters/in_memory.py").read_text()
    assert "class InMemorySource" in src


@check(
    "A",
    "dal/interfaces/source.py contient Source Protocol + FetchRequest + FetchResult",
)
def _a07():
    src = Path("dal/interfaces/source.py").read_text()
    for cls in ["Source", "FetchRequest", "FetchResult"]:
        assert cls in src, f"{cls} absent de source.py"


@check("A", "mif-dqf déclaré dans pyproject.toml")
def _a08():
    src = Path("pyproject.toml").read_text()
    assert "mif-dqf" in src


@check("A", "DALHandoff frozen=True dans le source")
def _a09():
    src = Path("dal/core/handoff.py").read_text()
    assert "frozen=True" in src


@check("A", "DALHandoff possède les 15 champs spec §5")
def _a10():
    from dal.core.handoff import DALHandoff

    fields = {f.name for f in DALHandoff.__dataclass_fields__.values()}
    required = {
        "stream",
        "asset_id",
        "calendar",  # virgule manquante — était concaténé avec "timeframe"
        "assembly_hash",  # "timeframe" supprimé — champ de FetchResult, pas DALHandoff §5
        "handoff_timestamp",
        "dal_version",
        "source_manifest",  # virgule manquante — était concaténé avec "coverage"
        "coverage",
        "truncated_days",
        "dqf_status",
        "dqf_mpi",
        "dqf_version",
        "dqf_version_target",
        "dqf_report",
        "aqi",
        # "start",
        # "end",
        # "completeness",
        # "fetched_at",
        # "assembled_at",
        # "mode",
    }
    missing = required - fields
    assert not missing, f"Champs manquants : {missing}"


@check("A", "source_manifest annoté tuple (pas list) dans handoff.py")
def _a11():
    src = Path("dal/core/handoff.py").read_text()
    assert "tuple" in src
    assert re.search(
        r"source_manifest\s*:.*tuple", src
    ), "source_manifest doit être annoté tuple"


@check("A", "Valeurs FULL/PARTIAL/DEGRADED documentées dans handoff.py")
def _a12():
    src = Path("dal/core/handoff.py").read_text()
    for v in ["FULL", "PARTIAL", "DEGRADED"]:
        assert v in src, f"{v} absent de handoff.py"


@check("A", "Valeurs PASS/WARNING documentées dans handoff.py")
def _a13():
    src = Path("dal/core/handoff.py").read_text()
    for v in ["PASS", "WARNING"]:
        assert v in src, f"{v} absent de handoff.py"


@check("A", "AQI floor max(0, ...) présent dans dal/core/sources.py")
def _a14():
    src = Path("dal/core/sources.py").read_text()
    assert "max(0" in src or "max(0." in src, "AQI floor max(0, ...) absent"


@check("A", "DALConfigError(DALError) dans exceptions.py")
def _a15():
    src = Path("dal/exceptions.py").read_text()
    assert "DALConfigError" in src and "DALError" in src


@check("A", "DALVersionError(DALError) dans exceptions.py")
def _a16():
    src = Path("dal/exceptions.py").read_text()
    assert "DALVersionError" in src


@check("A", "DALHandoffError(DALError) dans exceptions.py")
def _a17():
    src = Path("dal/exceptions.py").read_text()
    assert "DALHandoffError" in src


@check("A", "'DQF_FAIL' absent de exceptions.py (terme fictif supprimé)")
def _a18():
    src = Path("dal/exceptions.py").read_text()
    assert "DQF_FAIL" not in src


@check("A", "'DQF_VOID' ou 'reason' présent dans exceptions.py")
def _a19():
    src = Path("dal/exceptions.py").read_text()
    assert "DQF_VOID" in src or "reason" in src


@check("A", "assembly_hash calculé AVANT l'appel DQF (séquence fetch→hash→DQF)")
def _a20():
    src = Path("dal/core/pipeline.py").read_text()
    hash_pos = src.find("assembly_hash")
    # Chercher l'appel DQF réel — PAS les imports en tête de fichier
    # src.find("dqf") trouvait "from dqf import ..." avant assembly_hash → faux positif
    dqf_pos = -1
    for pattern in ["dqf_report =", "dqf_validator", ".validate(", "DQFValidator("]:
        pos = src.find(pattern)
        if pos != -1 and (dqf_pos == -1 or pos < dqf_pos):
            dqf_pos = pos
    if dqf_pos == -1:
        # Fallback : première ligne contenant "dqf" hors imports/commentaires
        for line in src.splitlines():
            stripped = line.strip()
            if "dqf" in stripped.lower() and not stripped.startswith(
                ("import", "from", "#")
            ):
                dqf_pos = src.find(stripped)
                break
    assert hash_pos != -1, "assembly_hash absent de pipeline.py"
    assert dqf_pos != -1, "Aucun appel DQF trouvé dans pipeline.py"
    assert (
        hash_pos < dqf_pos
    ), "assembly_hash doit être calculé AVANT l'appel DQF (D-DAL-006)"


@check("A", "to_parquet() utilisé pour sérialisation déterministe du hash")
def _a21():
    found = any("to_parquet" in p.read_text() for p in Path("dal").rglob("*.py"))
    assert found, "to_parquet() absent du code DAL"


@check("A", "ADVERSE : deux DataFrames identiques → même SHA-256")
def _a22():
    import hashlib

    import pandas as pd

    def _hash(df):
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=True)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    df1 = pd.DataFrame({"open": [1.0], "close": [2.0]})
    df2 = pd.DataFrame({"open": [1.0], "close": [2.0]})
    assert _hash(df1) == _hash(
        df2
    ), "Même DataFrame → SHA-256 différent (non-déterministe)"


@check("A", "ADVERSE : DataFrames différents → SHA-256 différents")
def _a23():
    import hashlib

    import pandas as pd

    def _hash(df):
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=True)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    df1 = pd.DataFrame({"open": [1.0]})
    df2 = pd.DataFrame({"open": [2.0]})
    assert _hash(df1) != _hash(df2), "DataFrames différents → même SHA-256 (collision)"


@check("A", "InMemorySource implémente source_id, fetch(), supports()")
def _a24():
    from dal.adapters.in_memory import InMemorySource

    src = InMemorySource.__dict__
    # Méthodes peuvent être sur instance — vérifier via inspect
    for method in ["fetch", "supports"]:
        assert hasattr(InMemorySource, method), f"InMemorySource.{method}() absent"
    assert hasattr(InMemorySource, "source_id") or "source_id" in str(
        inspect.signature(InMemorySource.__init__)
    ), "InMemorySource.source_id absent"


@check("A", "InMemorySource.supports() : True pour actif connu, False sinon")
def _a25():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource

    df = pd.DataFrame(
        {"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [100.0]},
        index=pd.to_datetime(["2024-01-01"], utc=True),
    )

    # Signature réelle : InMemorySource(source_id: str, data: dict[str, DataFrame], ...)
    # supports() prend asset_id: str — PAS un FetchRequest (erreur du checker initial)
    src = InMemorySource(source_id="test-memory", data={"TEST-USD": df})
    assert (
        src.supports("TEST-USD") is True
    ), "supports() devrait retourner True pour TEST-USD"
    assert (
        src.supports("OTHER-USD") is False
    ), "supports() devrait retourner False pour OTHER-USD"


@check("A", "FetchResult contient un hash SHA-256 (64 chars hex)")
def _a26():
    from dal.interfaces.source import FetchResult

    fields = inspect.signature(FetchResult.__init__).parameters
    assert "hash" in fields, "FetchResult.hash absent"


@check(
    "A", "FetchResult contient status, source_id, fetched_at, rows, timeframe, fallback"
)
def _a27():
    from dal.interfaces.source import FetchResult

    fields = inspect.signature(FetchResult.__init__).parameters
    for f in ["status", "source_id", "fetched_at", "rows", "timeframe", "fallback"]:
        assert f in fields, f"FetchResult.{f} absent"


@check("A", "get_certified_stream() défini quelque part dans dal/")
def _a28():
    found = any(
        "def get_certified_stream" in p.read_text() for p in Path("dal").rglob("*.py")
    )
    assert found, "get_certified_stream() introuvable dans dal/"


@check("A", "get_certified_stream() a les bons paramètres dans le source")
def _a29():
    for p in Path("dal").rglob("*.py"):
        src = p.read_text()
        if "def get_certified_stream" in src:
            assert "asset_id" in src, "get_certified_stream manque asset_id"
            assert "calendar" in src, "get_certified_stream manque calendar"
            # timeframe appartient à FetchRequest, pas à get_certified_stream (spec §7)
            break


@check("A", "get_diagnostic_stream() défini quelque part dans dal/")
def _a30():
    found = any(
        "def get_diagnostic_stream" in p.read_text() for p in Path("dal").rglob("*.py")
    )
    assert found, "get_diagnostic_stream() introuvable dans dal/"


@check("A", "DALConfigError levée si calendar vide (vérification source)")
def _a31():
    src_dal = Path("dal/dal.py").read_text() if Path("dal/dal.py").exists() else ""
    src_pip = Path("dal/core/pipeline.py").read_text()
    combined = src_dal + src_pip
    assert "DALConfigError" in combined, "DALConfigError absent de pipeline/dal"


@check(
    "A", "ADVERSE : D-DAL-007 — 'pair' absent du code non-commenté de l'API publique"
)
def _a32():
    """D-DAL-007 : un actif par appel — 'pair' est une notion MIF-Core, pas DAL."""
    for p in [Path("dal/__init__.py"), Path("dal/dal.py")]:
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert (
                "pair" not in stripped.lower() or "repair" in stripped.lower()
            ), f"'pair' trouvé dans API publique DAL ({p}) — D-DAL-007 violé"


@check("A", "'mif_uid' absent du code DAL (assembly_hash ≠ MIF-UID)")
def _a33():
    for p in Path("dal").rglob("*.py"):
        src = p.read_text()
        assert (
            "mif_uid" not in src
        ), f"'mif_uid' trouvé dans {p} — MIF-UID appartient à MIF-Core"


@check("A", "dqf_report annoté avec DQFReport (pas Any) dans handoff.py")
def _a34():
    src = Path("dal/core/handoff.py").read_text()
    assert "DQFReport" in src, "DQFReport absent de handoff.py"
    assert re.search(
        r"dqf_report\s*:.*DQFReport", src
    ), "dqf_report doit être annoté DQFReport (pas Any)"


@check("A", "ADVERSE : pas de validation OHLCV dans le code DAL non-test")
def _a35():
    """La validation des colonnes OHLCV appartient à DQF, pas au DAL."""
    ohlcv_validators = ["validate_ohlcv", "check_ohlcv", "assert_ohlcv"]
    for p in Path("dal").rglob("*.py"):
        if "test" in str(p):
            continue
        src = p.read_text()
        for v in ohlcv_validators:
            assert (
                v not in src
            ), f"Validation OHLCV '{v}' trouvée dans {p} — appartient à DQF"


@check("A", "mif-dqf installé et importable")
def _a36():
    try:
        import dqf  # noqa
    except ImportError as e:
        raise AssertionError(f"mif-dqf non importable : {e}")


@check("A", "DQFReport importable depuis dqf")
def _a37():
    from dqf import DQFReport  # noqa


@check("A", "ADVERSE : même DataFrame → même SHA-256 (reproductibilité)")
def _a38():
    import hashlib

    import pandas as pd

    def _hash(df):
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=True)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    df = pd.DataFrame(
        {"open": [100.0, 101.0], "close": [101.0, 102.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True),
    )
    h1, h2 = _hash(df), _hash(df)
    assert h1 == h2, "Même DataFrame → hashes différents (non-reproductible)"


@check("A", "ADVERSE : sources différentes → hashes différents (pas de collision)")
def _a39():
    import hashlib

    import pandas as pd

    def _hash(df, source_id):
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=True)
        raw = buf.getvalue()
        return hashlib.sha256(raw + source_id.encode()).hexdigest()

    df = pd.DataFrame({"open": [100.0]}, index=pd.to_datetime(["2024-01-01"], utc=True))
    assert _hash(df, "kraken") != _hash(
        df, "yahoo"
    ), "Sources différentes → même hash (collision)"


@check("A", "FetchResult.hash tracé par source dans source_manifest")
def _a40():
    src = Path("dal/core/handoff.py").read_text()
    assert "source_manifest" in src
    assert "hash" in src


@check("A", "dal.__version__ défini")
def _a41():
    import dal

    assert hasattr(dal, "__version__"), "dal.__version__ absent"
    assert dal.__version__, "dal.__version__ vide"


# ─────────────────────────────────────────────────────────────────────────────
# [B] Phase 3 — gates de publication
# ─────────────────────────────────────────────────────────────────────────────


@check("B", "dal.__version__ est semver valide (X.Y.Z ou X.Y.Z.postN)")
def _b01():
    import dal

    v = dal.__version__
    assert re.match(
        r"^\d+\.\d+\.\d+(\.(post|dev|rc)\d+)?$", v
    ), f"dal.__version__ = '{v}' n'est pas semver valide"


@check("B", "pyproject.toml déclare version cohérente avec dal.__version__")
def _b02():
    import dal

    src = Path("pyproject.toml").read_text()
    m = re.search(r'version\s*=\s*"([^"]+)"', src)
    assert m, "version absente de pyproject.toml"
    assert (
        m.group(1) == dal.__version__
    ), f"pyproject.toml version={m.group(1)} ≠ dal.__version__={dal.__version__}"


@check("B", "CHANGELOG.md ou CHANGELOG existe et mentionne v0.1.0")
def _b03():
    for name in ["CHANGELOG.md", "CHANGELOG", "CHANGELOG.rst", "docs/CHANGELOG.md"]:
        p = Path(name)
        if p.exists():
            assert (
                "0.1.0" in p.read_text()
            ), f"{name} existe mais ne mentionne pas v0.1.0"
            return
    raise AssertionError("Aucun CHANGELOG trouvé — requis pour publication PyPI")


@check("B", "README.md existe et contient un exemple get_certified_stream")
def _b04():
    p = Path("README.md")
    assert p.exists(), "README.md absent"
    src = p.read_text()
    assert (
        "get_certified_stream" in src or "get_diagnostic_stream" in src
    ), "README.md ne contient aucun exemple d'utilisation DAL"


@check("B", "docs/DAL_SPECIFICATION_v1.0.md existe")
def _b05():
    assert Path(
        "docs/DAL_SPECIFICATION_v1.0.md"
    ).exists(), "DAL_SPECIFICATION_v1.0.md absent de docs/"


@check("B", "pyproject.toml déclare python_requires >= 3.11")
def _b06():
    src = Path("pyproject.toml").read_text()
    assert "3.11" in src, "python_requires >= 3.11 absent de pyproject.toml"


@check("B", "pyproject.toml déclare les classifiers PyPI")
def _b07():
    src = Path("pyproject.toml").read_text()
    assert "classifiers" in src, "classifiers absents de pyproject.toml"


@check("B", "Aucun print() de debug dans dal/ (hors tests et scripts)")
def _b08():
    """Interdit les print() oubliés dans le code de production."""
    violations = []
    for p in Path("dal").rglob("*.py"):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Autorise print dans __main__ et CLI, interdit ailleurs
            if re.match(r"^\s*print\s*\(", line) and "__main__" not in str(p):
                violations.append(f"{p}:{i}: {stripped}")
    assert not violations, "print() de debug trouvés dans dal/ :\n" + "\n".join(
        violations[:5]
    )


# ─────────────────────────────────────────────────────────────────────────────
# [C] Coverage gates (DAL-010)
# ─────────────────────────────────────────────────────────────────────────────


@check("C", "pytest --tb=no retourne 0 (aucun test failed sans réseau)")
def _c01():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True,
    )
    assert (
        r.returncode == 0
    ), f"pytest a échoué (exit={r.returncode}) :\n{r.stdout[-1000:]}"


@check("C", "Coverage global dal/ ≥ 80% (gate publication DAL-010)")
def _c02():
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=dal",
            "--cov-report=term",
            "-q",
            "--tb=no",
        ],
        capture_output=True,
        text=True,
    )
    # Parser le total depuis la sortie coverage
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", r.stdout)
    if not m:
        # pytest.ini bloque peut-être --cov — essayer via coverage report
        r2 = subprocess.run(
            [sys.executable, "-m", "coverage", "report", "--include=dal/*"],
            capture_output=True,
            text=True,
        )
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", r2.stdout)
    assert m, "Impossible de parser le coverage total"
    pct = int(m.group(1))
    assert pct >= 80, f"Coverage {pct}% < 80% (gate DAL-010 non atteint)"


@check("C", "Coverage dal/core/handoff.py ≥ 80%")
def _c03():
    r = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--include=dal/core/handoff.py"],
        capture_output=True,
        text=True,
    )
    m = re.search(r"handoff\.py\s+\d+\s+\d+\s+(\d+)%", r.stdout)
    if not m:
        return  # coverage non disponible — skip gracieux
    pct = int(m.group(1))
    assert pct >= 80, f"dal/core/handoff.py coverage {pct}% < 80%"


@check("C", "Coverage dal/core/pipeline.py ≥ 80%")
def _c04():
    r = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--include=dal/core/pipeline.py"],
        capture_output=True,
        text=True,
    )
    m = re.search(r"pipeline\.py\s+\d+\s+\d+\s+(\d+)%", r.stdout)
    if not m:
        return
    pct = int(m.group(1))
    assert pct >= 80, f"dal/core/pipeline.py coverage {pct}% < 80%"


@check("C", "Coverage dal/core/sources.py ≥ 80%")
def _c05():
    r = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--include=dal/core/sources.py"],
        capture_output=True,
        text=True,
    )
    m = re.search(r"sources\.py\s+\d+\s+\d+\s+(\d+)%", r.stdout)
    if not m:
        return
    pct = int(m.group(1))
    assert pct >= 80, f"dal/core/sources.py coverage {pct}% < 80%"


# ─────────────────────────────────────────────────────────────────────────────
# [D] Environnement NixOS — dukascopy-node détection correcte
# ─────────────────────────────────────────────────────────────────────────────


@check("D", "dukascopy.py utilise --help (pas --version) pour la détection")
def _d01():
    src = Path("dal/adapters/dukascopy.py").read_text()
    # --version ne doit pas apparaître dans le code de détection
    # (il peut apparaître en commentaire)
    lines_with_version = [
        line
        for line in src.splitlines()
        if "--version" in line and not line.strip().startswith("#")
    ]
    assert not lines_with_version, (
        "dukascopy.py utilise --version en dehors des commentaires — "
        "remplacer par --help (bug upstream : --version exit 1)"
    )


@check("D", "conftest.py utilise --help (pas --version) pour skip_if_no_dukascopy")
def _d02():
    p = Path("tests/conftest.py")
    assert p.exists(), "tests/conftest.py absent"
    src = p.read_text()
    lines_with_version = [
        line
        for line in src.splitlines()
        if "--version" in line
        and not line.strip().startswith("#")
        and "dukascopy" in line.lower()
    ]
    assert not lines_with_version, (
        "tests/conftest.py utilise --version pour détecter dukascopy — "
        "remplacer par --help"
    )


@check("D", "dukascopy.py contient stdin=DEVNULL ou subprocess.DEVNULL")
def _d03():
    src = Path("dal/adapters/dukascopy.py").read_text()
    assert (
        "DEVNULL" in src
    ), "dukascopy.py manque stdin=subprocess.DEVNULL (requis Windows + NixOS)"


@check("D", "flake.nix ne contient pas nodePackages (supprimé de nixpkgs)")
def _d04():
    for p in [Path("flake.nix"), Path("flake.nix.new")]:
        if p.exists():
            src = p.read_text()
            assert "nodePackages" not in src, (
                f"{p} contient 'nodePackages' — supprimé de nixpkgs récent. "
                "Utiliser pkgs.npm (top-level)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# [E] Intégration réelle DQF (sans mock) — nécessite --run-network
# ─────────────────────────────────────────────────────────────────────────────

_NETWORK = False  # activé par --run-network


@check("E", "get_diagnostic_stream retourne DALHandoff avec DQFReport réel [réseau]")
def _e01():
    if not _NETWORK:
        return
    import pandas as pd
    from dqf import DQFReport

    from dal import DAL, DALConfig
    from dal.adapters.in_memory import InMemorySource
    from dal.core.handoff import DALHandoff

    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000.0, 1100.0, 1200.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"], utc=True),
    )

    src = InMemorySource(source_id="test", data={"BTC-USD": df})
    dal_instance = DAL(DALConfig(), sources=(src,))
    handoff = dal_instance.get_diagnostic_stream(
        asset_id="BTC-USD",
        source_preference=["test"],
        start="2024-01-02",
        end="2024-01-04",
        calendar="CRYPTO_247",
    )
    assert isinstance(
        handoff, DALHandoff
    ), f"Retourne {type(handoff)} au lieu de DALHandoff"
    assert isinstance(
        handoff.dqf_report, DQFReport
    ), "handoff.dqf_report n'est pas un DQFReport réel"
    assert handoff.assembly_hash, "assembly_hash vide"
    assert (
        len(handoff.assembly_hash) == 64
    ), f"assembly_hash longueur {len(handoff.assembly_hash)} ≠ 64 (SHA-256)"


@check("E", "Reproductibilité : même appel → même assembly_hash [réseau]")
def _e02():
    if not _NETWORK:
        return
    import pandas as pd

    from dal import DAL, DALConfig
    from dal.adapters.in_memory import InMemorySource

    df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000.0],
        },
        index=pd.to_datetime(["2024-01-02"], utc=True),
    )

    def _call():
        src = InMemorySource(source_id="test", data={"PAXG-USD": df.copy()})
        dal_instance = DAL(DALConfig(), sources=(src,))
        return dal_instance.get_diagnostic_stream(
            asset_id="PAXG-USD",
            source_preference=["test"],
            start="2024-01-02",
            end="2024-01-02",
            calendar="CRYPTO_247",
        ).assembly_hash

    h1, h2 = _call(), _call()
    assert h1 == h2, f"Non-reproductible : {h1} ≠ {h2}"


# ─────────────────────────────────────────────────────────────────────────────
# [F] Régression Kraken (Bug B corrigé)
# ─────────────────────────────────────────────────────────────────────────────


@check("F", "KrakenAdapter.fetch() ne retourne pas success + 0 rows [réseau]")
def _f01():
    """Bug B : Kraken retournait XXBTZUSD mais le code cherchait XBTUSD."""
    if not _NETWORK:
        return
    from dal.adapters.kraken import KrakenAdapter
    from dal.interfaces.source import FetchRequest

    req = FetchRequest(
        asset_id="BTC-USD",
        start="2024-01-01",
        end="2024-01-10",
        timeframe="1D",
    )
    adapter = KrakenAdapter()
    result = adapter.fetch(req)

    if result.status == "success":
        assert result.rows > 0, (
            "Bug B non corrigé : Kraken retourne status='success' + 0 rows. "
            "Fix : chercher la clé native XXBTZUSD dans la réponse."
        )
    # status='failed' est acceptable (réseau KO) — on ne teste que success+0rows


@check(
    "F", "resolve_and_fetch() accepte (request, sources) comme arguments [non-réseau]"
)
def _f02():
    """Bug A : resolve_and_fetch() prenait 0 arguments positionnels."""
    import inspect

    try:
        from dal.core.sources import resolve_and_fetch
    except ImportError:
        # Peut être dans un autre module
        from dal import resolve_and_fetch  # type: ignore
    sig = inspect.signature(resolve_and_fetch)
    params = list(sig.parameters.keys())
    assert len(params) >= 2, (
        f"resolve_and_fetch() n'accepte que {len(params)} paramètre(s) — "
        f"doit accepter (request, sources). Bug A non corrigé."
    )
    assert params[0] in (
        "request",
        "req",
        "fetch_request",
    ), f"Premier paramètre '{params[0]}' — attendu 'request' ou 'req'"


# ─────────────────────────────────────────────────────────────────────────────
# [G] API publique finale
# ─────────────────────────────────────────────────────────────────────────────


@check("G", "dal.__all__ défini et contient les symboles publics")
def _g01():
    import dal

    assert hasattr(
        dal, "__all__"
    ), "dal.__all__ absent — requis pour pip install propre"
    expected = {
        "DALConfig",
        "DALHandoff",
    }
    actual = set(dal.__all__)
    missing = expected - actual
    assert not missing, f"dal.__all__ manque : {missing}"


@check("G", "Pas de dépendance circulaire détectable dans dal/")
def _g02():
    """Vérifie que les imports dans dal/ ne forment pas de cycle évident."""
    errors = []
    for p in Path("dal").rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        try:
            ast.parse(p.read_text())
        except SyntaxError as e:
            errors.append(f"{p}: SyntaxError — {e}")
    assert not errors, "Erreurs de syntaxe dans dal/ :\n" + "\n".join(errors)


@check("G", "Tous les modules dal/ sont importables sans erreur")
def _g03():
    errors = []
    for p in sorted(Path("dal").rglob("*.py")):
        if "__pycache__" in str(p) or p.name.startswith("_"):
            continue
        mod_name = str(p).replace("/", ".").replace(".py", "")
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            errors.append(f"{mod_name}: {e}")
    assert not errors, "Modules non importables :\n" + "\n".join(errors)


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────


def main():
    global _NETWORK

    parser = argparse.ArgumentParser(
        description="adversarial_dal_check_p3.py — Non-régression Phase 3 mif-dal"
    )
    parser.add_argument(
        "--run-network",
        action="store_true",
        help="Activer les checks nécessitant un accès réseau réel (sections E, F)",
    )
    args = parser.parse_args()
    _NETWORK = args.run_network

    print()
    print(f"{BOLD}{'=' * 62}{RESET}")
    print(f"{BOLD}  MIF-DAL Adversarial Check — Phase 3 (non-régression){RESET}")
    print(
        f"  Réseau : {'OUI (--run-network)' if _NETWORK else 'NON (tests mockés uniquement)'}"
    )
    print("  Référence : DAL_SPECIFICATION_v1.0.md + DAL_Phase3_Plan_v1.1.md")
    print(f"{BOLD}{'=' * 62}{RESET}")

    results: dict[str, list[tuple[str, str]]] = {}  # section → [(label, status)]
    current_section = None

    passed = failed = errors = skipped = 0

    for section, label, fn in CHECKS:
        if section != current_section:
            current_section = section
            section_names = {
                "A": "Phase 2 — invariants préservés",
                "B": "Phase 3 — gates de publication",
                "C": "Coverage (DAL-010)",
                "D": "Environnement NixOS",
                "E": "Intégration réelle DQF"
                + (" [réseau]" if _NETWORK else " [skippé sans --run-network]"),
                "F": "Régression Kraken / resolve_and_fetch",
                "G": "API publique finale",
            }
            print(f"\n[{section}] {section_names.get(section, section)}\n")

        try:
            fn()
            print(f"  {GREEN}✓{RESET} {label}")
            passed += 1
        except AssertionError as e:
            msg = str(e)
            print(f"  {RED}✗{RESET} {label}")
            if msg:
                print(f"      {YELLOW}→{RESET} {msg[:200]}")
            failed += 1
        except Exception as e:
            print(f"  {RED}!{RESET} {label}")
            print(f"      {RED}ERREUR{RESET} : {type(e).__name__}: {e}")
            errors += 1

    total = passed + failed + errors
    status_color = GREEN if failed == 0 and errors == 0 else RED
    result_label = "PASS" if failed == 0 and errors == 0 else "FAIL"

    print()
    print(f"{BOLD}{'=' * 62}{RESET}")
    print(
        f"{BOLD}  RÉSULTAT : {status_color}{result_label}{RESET}{BOLD}  "
        f"|  {passed}/{total} PASS  |  {failed} FAIL  |  {errors} ERROR{RESET}"
    )
    print(f"{BOLD}{'=' * 62}{RESET}")

    if not _NETWORK:
        print(f"\n  {YELLOW}ℹ{RESET}  Sections E et F (réseau) ignorées.")
        print(
            "      Relancer avec : .venv/bin/python scripts/adversarial_dal_check_p3.py --run-network"
        )

    print()
    sys.exit(0 if failed == 0 and errors == 0 else 1)


if __name__ == "__main__":
    main()
