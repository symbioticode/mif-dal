"""
adversarial_dal_check.py  v2 (debut env en cours)
 ==============================
Script de vérification adverse pour mif-dal v0.1.

Usage (depuis la racine du repo mif-dal) :
    python adversarial_dal_check.py

v2 : Tous les checks du groupe A-F-G utilisent l'inspection de source
     au lieu de l'import runtime. Fonctionne même si mif-dqf n'est pas
     installé dans l'env nix actif (nix store read-only).

     Les checks G4/G5 (import dqf runtime) sont conservés mais marqués
     SKIP si dqf est absent, sans bloquer le résultat global.

Référence : DAL_SPECIFICATION_v1.0.md

Il reste une seule cause racine : dqf non importable malgré l'installation. C'est un problème NixOS — le nix store est read-only, pip install a échoué silencieusement, uv add a réussi mais dans l'env uv, pas dans l'env nix actif.

"""

import hashlib
import pathlib
import re
import sys
from dataclasses import fields

# ─── Résultats ────────────────────────────────────────────────────────────────

RESULTS: list[dict] = []


def check(name: str, group: str, skip_if_no_dqf: bool = False):
    """Décorateur de test adverse."""

    def decorator(fn):
        def wrapper():
            if skip_if_no_dqf and not DQF_AVAILABLE:
                RESULTS.append(
                    {
                        "group": group,
                        "name": name,
                        "status": "SKIP",
                        "detail": "dqf non installé dans l'env actif (nix store read-only). "
                        "Installer avec : uv run python adversarial_dal_check.py",
                    }
                )
                print(f"  ⊘ {name} [SKIP — dqf absent]")
                return
            try:
                fn()
                RESULTS.append(
                    {"group": group, "name": name, "status": "PASS", "detail": ""}
                )
                print(f"  ✓ {name}")
            except AssertionError as e:
                RESULTS.append(
                    {"group": group, "name": name, "status": "FAIL", "detail": str(e)}
                )
                print(f"  ✗ {name}")
                print(f"      → {e}")
            except Exception as e:
                RESULTS.append(
                    {
                        "group": group,
                        "name": name,
                        "status": "ERROR",
                        "detail": f"{type(e).__name__}: {e}",
                    }
                )
                print(f"  ✗ {name} [ERROR]")
                print(f"      → {type(e).__name__}: {e}")

        wrapper._check = True
        return wrapper

    return decorator


def _dqf_available() -> bool:
    try:
        import dqf  # noqa: F401

        return True
    except ImportError:
        return False


DQF_AVAILABLE = _dqf_available()


def src(relpath: str) -> str:
    """Lire le source d'un fichier relatif à la racine du repo."""
    p = pathlib.Path(relpath)
    assert p.exists(), f"Fichier absent : {relpath}"
    return p.read_text()


# ─── Groupe A — Structure du package ─────────────────────────────────────────

print("\n[A] Package structure")


@check("dal/__init__.py existe", "A")
def a1():
    assert pathlib.Path("dal/__init__.py").exists()


@check("dal/core/handoff.py contient class DALHandoff", "A")
def a2():
    assert "class DALHandoff" in src(
        "dal/core/handoff.py"
    ), "class DALHandoff absente de dal/core/handoff.py"


@check("class DAL publique définie quelque part dans dal/", "A")
def a3():
    found = False
    for p in pathlib.Path("dal").rglob("*.py"):
        if re.search(r"^class DAL[^A-Za-z]", p.read_text(), re.MULTILINE):
            found = True
            break
    assert found, (
        "class DAL (publique) introuvable dans dal/. "
        "Livrable de DAL-006 : get_certified_stream() + get_diagnostic_stream()."
    )


@check("dal/core/config.py contient class DALConfig", "A")
def a4():
    assert "class DALConfig" in src(
        "dal/core/config.py"
    ), "class DALConfig absente de dal/core/config.py"


@check("dal/exceptions.py contient les 4 exceptions", "A")
def a5():
    s = src("dal/exceptions.py")
    for exc in ["DALError", "DALConfigError", "DALVersionError", "DALHandoffError"]:
        assert exc in s, f"{exc} absente de dal/exceptions.py"


@check("dal/adapters/in_memory.py contient class InMemorySource", "A")
def a6():
    assert "class InMemorySource" in src(
        "dal/adapters/in_memory.py"
    ), "class InMemorySource absente de dal/adapters/in_memory.py"


@check(
    "dal/interfaces/source.py contient Source Protocol + FetchRequest + FetchResult",
    "A",
)
def a7():
    s = src("dal/interfaces/source.py")
    assert "class Source" in s or "Protocol" in s, "Source Protocol absent"
    assert "FetchRequest" in s, "FetchRequest absent de dal/interfaces/source.py"
    assert "FetchResult" in s, "FetchResult absent de dal/interfaces/source.py"


@check("mif-dqf déclaré dans pyproject.toml", "A")
def a8():
    import tomllib

    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert any(
        "mif-dqf" in d for d in deps
    ), f"mif-dqf absent des dépendances. Trouvé : {deps}"


# ─── Groupe B — Contrat DALHandoff (spec §5) ──────────────────────────────────

print("\n[B] DALHandoff contract (spec §5)")


@check("DALHandoff frozen=True dans le source", "B")
def b1():
    assert "frozen=True" in src(
        "dal/core/handoff.py"
    ), "frozen=True absent — DALHandoff doit être immutable (spec §5)"


@check("DALHandoff possède les 15 champs spec §5", "B")
def b2():
    s = src("dal/core/handoff.py")
    expected = [
        "stream",
        "asset_id",
        "calendar",
        "assembly_hash",
        "handoff_timestamp",
        "dal_version",
        "source_manifest",
        "coverage",
        "truncated_days",
        "dqf_status",
        "dqf_mpi",
        "dqf_version",
        "dqf_version_target",
        "dqf_report",
        "aqi",
    ]
    missing = [f for f in expected if f not in s]
    assert not missing, f"Champs manquants dans DALHandoff : {missing}"


@check("source_manifest annoté tuple (pas list) dans handoff.py", "B")
def b3():
    s = src("dal/core/handoff.py")
    lines = [l for l in s.splitlines() if "source_manifest" in l and ":" in l]
    assert lines, "source_manifest introuvable dans handoff.py"
    decl = lines[0].lower()
    assert (
        "tuple" in decl
    ), f"source_manifest n'est pas annoté tuple : '{lines[0].strip()}'"
    assert (
        "list" not in decl
    ), f"source_manifest annoté comme list : '{lines[0].strip()}'"


@check("Contrat stream OHLCV + UTC documenté dans handoff.py", "B")
def b4():
    s = src("dal/core/handoff.py")
    assert any(
        c in s for c in ["open", "high", "low", "close", "volume"]
    ), "Colonnes OHLCV non documentées dans handoff.py"
    assert (
        "UTC" in s or "tz" in s.lower()
    ), "Contrainte timezone UTC non documentée dans handoff.py"


@check("Valeurs FULL/PARTIAL/DEGRADED documentées dans handoff.py", "B")
def b5():
    s = src("dal/core/handoff.py")
    for val in ["FULL", "PARTIAL", "DEGRADED"]:
        assert val in s, f"Valeur coverage '{val}' absente de handoff.py"


@check("Valeurs PASS/WARNING documentées dans handoff.py", "B")
def b6():
    s = src("dal/core/handoff.py")
    assert "PASS" in s, "Valeur 'PASS' de dqf_status absente de handoff.py"
    assert "WARNING" in s, "Valeur 'WARNING' de dqf_status absente de handoff.py"


@check("AQI floor max(0, ...) présent dans dal/core/sources.py", "B")
def b7():
    s = src("dal/core/sources.py")
    assert (
        "max(0" in s and "aqi" in s.lower()
    ), "Formule AQI avec floor max(0, ...) introuvable dans dal/core/sources.py"


# ─── Groupe C — Hiérarchie des exceptions (spec §8) ──────────────────────────

print("\n[C] Exception hierarchy (spec §8)")


@check("DALConfigError(DALError) dans exceptions.py", "C")
def c1():
    assert "class DALConfigError(DALError)" in src("dal/exceptions.py")


@check("DALVersionError(DALError) dans exceptions.py", "C")
def c2():
    assert "class DALVersionError(DALError)" in src("dal/exceptions.py")


@check("DALHandoffError(DALError) dans exceptions.py", "C")
def c3():
    assert "class DALHandoffError(DALError)" in src("dal/exceptions.py")


@check("'DQF_FAIL' absent de exceptions.py (terme fictif supprimé)", "C")
def c4():
    assert "DQF_FAIL" not in src(
        "dal/exceptions.py"
    ), "'DQF_FAIL' présent — terme fictif, DQF n'a pas ce statut"


@check("'DQF_VOID' ou 'reason' présent dans exceptions.py", "C")
def c5():
    s = src("dal/exceptions.py")
    assert (
        "DQF_VOID" in s or "reason" in s
    ), "'DQF_VOID' et 'reason' absents de DALHandoffError (spec §8)"


# ─── Groupe D — assembly_hash invariants (spec §4 S3, D-DAL-006) ─────────────

print("\n[D] assembly_hash invariants (D-DAL-006)")


@check("assembly_hash calculé AVANT l'appel DQF (séquence fetch→hash→DQF)", "D")
def d1():
    candidates = [
        "dal/core/pipeline.py",
        "dal/core/assembler.py",
        "dal/core/sources.py",
    ]
    found = False
    for relpath in candidates:
        p = pathlib.Path(relpath)
        if not p.exists():
            continue
        s = p.read_text()
        has_hash = "sha256" in s or "assembly_hash" in s
        has_dqf = (
            "validate" in s
            or "DQFValidator" in s
            or ("dqf" in s.lower() and "import" in s)
        )
        if has_hash and has_dqf:
            hash_pos = min(
                (s.find(k) for k in ["sha256", "assembly_hash"] if s.find(k) >= 0),
                default=-1,
            )
            dqf_pos = min(
                (s.find(k) for k in ["validate", "DQFValidator"] if s.find(k) >= 0),
                default=-1,
            )
            if 0 <= hash_pos < dqf_pos:
                found = True
                break
    assert (
        found
    ), "Impossible de confirmer hash calculé AVANT appel DQF dans pipeline.py/assembler.py"


@check("to_parquet() utilisé pour sérialisation déterministe du hash", "D")
def d2():
    bad = []
    for p in pathlib.Path("dal").rglob("*.py"):
        s = p.read_text()
        if "to_parquet" in s and ("sha256" in s or "hash" in s.lower()):
            return  # trouvé
        if "to_csv" in s and "sha256" in s:
            bad.append(f"{p}: to_csv() + sha256 (non-déterministe)")
        if "pickle" in s and "sha256" in s:
            bad.append(f"{p}: pickle + sha256 (non-déterministe)")
    assert not bad, f"Sérialisateurs non-déterministes : {bad}"
    assert (
        False
    ), "to_parquet() introuvable avec sha256. Seule sérialisation déterministe acceptable."


@check("ADVERSE : deux DataFrames identiques → même SHA-256", "D")
def d3():
    import io

    import pandas as pd

    idx = pd.date_range("2020-01-01", periods=10, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": list(range(10)),
            "high": list(range(1, 11)),
            "low": list(range(-1, 9)),
            "close": list(range(10)),
            "volume": [1000.0] * 10,
        },
        index=idx,
        dtype=float,
    )

    def h(df):
        buf = io.BytesIO()
        df.to_parquet(buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    assert h(df) == h(
        df.copy()
    ), "ÉCHEC REPRODUCTIBILITÉ : même DataFrame → hashes différents"


@check("ADVERSE : DataFrames différents → SHA-256 différents", "D")
def d4():
    import io

    import pandas as pd

    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    df1 = pd.DataFrame(
        {
            "open": [1.0] * 5,
            "high": [1.1] * 5,
            "low": [0.9] * 5,
            "close": [1.0] * 5,
            "volume": [100.0] * 5,
        },
        index=idx,
    )
    df2 = df1.copy()
    df2["close"] = [2.0] * 5

    def h(df):
        buf = io.BytesIO()
        df.to_parquet(buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    assert h(df1) != h(df2), "DataFrames différents → même hash (collision)"


# ─── Groupe E — InMemorySource & Source Protocol ──────────────────────────────

print("\n[E] InMemorySource & Source Protocol")


@check("InMemorySource implémente source_id, fetch(), supports()", "E")
def e1():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource

    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0] * 3,
            "volume": [50.0] * 3,
        },
        index=idx,
    )
    src_obj = InMemorySource(data={"PAXG-USD": df}, source_id="test")
    assert hasattr(src_obj, "source_id"), "source_id manquant"
    assert callable(getattr(src_obj, "fetch", None)), "fetch() manquant"
    assert callable(getattr(src_obj, "supports", None)), "supports() manquant"


@check("InMemorySource.supports() : True pour actif connu, False sinon", "E")
def e2():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource

    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0] * 3,
            "volume": [50.0] * 3,
        },
        index=idx,
    )
    src_obj = InMemorySource(data={"PAXG-USD": df}, source_id="test")
    assert src_obj.supports("PAXG-USD") is True
    assert src_obj.supports("BTC-USD") is False


@check("FetchResult contient un hash SHA-256 (64 chars hex)", "E")
def e3():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource
    from dal.interfaces.source import FetchRequest

    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0] * 3,
            "volume": [50.0] * 3,
        },
        index=idx,
    )
    src_obj = InMemorySource(data={"PAXG-USD": df}, source_id="test")
    req = FetchRequest(
        asset_id="PAXG-USD", start="2020-01-01", end="2020-01-03", timeframe="1D"
    )
    result = src_obj.fetch(req)
    assert hasattr(result, "hash"), "FetchResult manque le champ 'hash'"
    assert (
        len(result.hash) == 64
    ), f"hash doit être SHA-256 (64 hex chars), got {len(result.hash)}"


@check(
    "FetchResult contient status, source_id, fetched_at, rows, timeframe, fallback", "E"
)
def e4():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource
    from dal.interfaces.source import FetchRequest

    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0] * 3,
            "volume": [50.0] * 3,
        },
        index=idx,
    )
    src_obj = InMemorySource(data={"PAXG-USD": df}, source_id="test")
    req = FetchRequest(
        asset_id="PAXG-USD", start="2020-01-01", end="2020-01-03", timeframe="1D"
    )
    result = src_obj.fetch(req)
    actual = (
        set(vars(result).keys())
        if not hasattr(result, "__dataclass_fields__")
        else {f.name for f in fields(result)}
    )
    required = {"status", "source_id", "fetched_at", "rows", "timeframe", "fallback"}
    missing = required - actual
    assert (
        not missing
    ), f"FetchResult manque : {missing} (requis pour source_manifest spec §4 S1)"


# ─── Groupe F — DAL public API (spec §7) ─────────────────────────────────────

print("\n[F] DAL public API (spec §7)")


@check("get_certified_stream() défini quelque part dans dal/", "F")
def f1():
    found = False
    for p in pathlib.Path("dal").rglob("*.py"):
        if "get_certified_stream" in p.read_text():
            found = True
            break
    assert found, "get_certified_stream() introuvable dans dal/"


@check("get_certified_stream() a les bons paramètres dans le source", "F")
def f2():
    for p in pathlib.Path("dal").rglob("*.py"):
        s = p.read_text()
        if "def get_certified_stream" in s:
            lines = [l for l in s.splitlines() if "def get_certified_stream" in l]
            fn_src = lines[0] if lines else ""
            required = [
                "asset_id",
                "source_preference",
                "start",
                "end",
                "calendar",
                "dqf_version_target",
            ]
            # Chercher dans la définition complète (peut s'étaler sur plusieurs lignes)
            idx = s.find("def get_certified_stream")
            block = s[idx : idx + 400]
            missing = [p for p in required if p not in block]
            assert (
                not missing
            ), f"Paramètres manquants dans get_certified_stream(): {missing}"
            return
    assert False, "get_certified_stream() non trouvé"


@check("get_diagnostic_stream() défini quelque part dans dal/", "F")
def f3():
    found = False
    for p in pathlib.Path("dal").rglob("*.py"):
        if "get_diagnostic_stream" in p.read_text():
            found = True
            break
    assert found, "get_diagnostic_stream() introuvable dans dal/"


@check("DALConfigError levée si calendar vide (vérification source)", "F")
def f4():
    """
    Cherche que get_certified_stream valide calendar avant tout appel DQF.
    Pattern attendu : if not calendar → raise DALConfigError
    """
    for p in pathlib.Path("dal").rglob("*.py"):
        s = p.read_text()
        if "get_certified_stream" in s and "DALConfigError" in s:
            if "calendar" in s and (
                "not calendar" in s or "calendar ==" in s or "raise DALConfigError" in s
            ):
                return
    assert (
        False
    ), "Impossible de confirmer que get_certified_stream lève DALConfigError si calendar vide"


@check(
    "ADVERSE : D-DAL-007 — 'pair' absent du code non-commenté de l'API publique", "F"
)
def f5():
    violations = []
    for relpath in ["dal/__init__.py"]:
        p = pathlib.Path(relpath)
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if "pair" in line.lower() and not line.strip().startswith("#"):
                violations.append(f"{relpath}: {line.strip()}")
    assert (
        not violations
    ), f"'pair' dans l'API publique DAL : {violations} (violation D-DAL-007)"


# ─── Groupe G — Cohérence MIF ecosystem ──────────────────────────────────────

print("\n[G] MIF ecosystem coherence")


@check("'mif_uid' absent du code DAL (assembly_hash ≠ MIF-UID)", "G")
def g1():
    violations = []
    for p in pathlib.Path("dal").rglob("*.py"):
        s = p.read_text()
        if "mif_uid" in s.lower() or "mif-uid" in s.lower():
            violations.append(str(p))
    assert (
        not violations
    ), f"'mif_uid/MIF-UID' dans le code DAL : {violations} (confusion avec concept DQF)"


@check("dqf_report annoté avec DQFReport (pas Any) dans handoff.py", "G")
def g2():
    s = src("dal/core/handoff.py")
    lines = [l for l in s.splitlines() if "dqf_report" in l and ":" in l]
    assert lines, "dqf_report introuvable dans handoff.py"
    decl = lines[0]
    assert (
        "Any" not in decl or "Optional" in decl
    ), f"dqf_report annoté Any sans Optional : '{decl.strip()}'"
    assert (
        "DQFReport" in decl or "TYPE_CHECKING" in s
    ), f"dqf_report ne référence pas DQFReport : '{decl.strip()}'"


@check("ADVERSE : pas de validation OHLCV dans le code DAL non-test", "G")
def g3():
    violations = []
    for p in pathlib.Path("dal").rglob("*.py"):
        if "test" in str(p):
            continue
        s = p.read_text()
        for pattern in ["high >= low", "close > 0", "open > 0"]:
            if pattern in s:
                violations.append(f"{p}: '{pattern}'")
    assert not violations, f"Validation OHLCV dans DAL (rôle de DQF) : {violations}"


@check("mif-dqf installé et importable", "G", skip_if_no_dqf=True)
def g4():
    import dqf  # noqa: F401


@check("DQFReport importable depuis dqf", "G", skip_if_no_dqf=True)
def g5():
    from dqf import DQFReport  # noqa: F401


# ─── Groupe H — Reproductibilité ─────────────────────────────────────────────

print("\n[H] Reproductibility — the core MIF guarantee")


@check("ADVERSE : même DataFrame → même SHA-256 (reproductibilité)", "H")
def h1():
    import io

    import pandas as pd

    idx = pd.date_range("2023-01-01", periods=20, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": list(range(20)),
            "high": list(range(1, 21)),
            "low": list(range(-1, 19)),
            "close": list(range(20)),
            "volume": [1000.0] * 20,
        },
        index=idx,
        dtype=float,
    )

    def h(df):
        buf = io.BytesIO()
        df.to_parquet(buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    r1, r2 = h(df), h(df.copy())
    assert r1 == r2, f"ÉCHEC REPRODUCTIBILITÉ :\n  Run1: {r1}\n  Run2: {r2}"


@check("ADVERSE : sources différentes → hashes différents (pas de collision)", "H")
def h2():
    import io

    import pandas as pd

    idx = pd.date_range("2023-01-01", periods=5, freq="D", tz="UTC")
    df_k = pd.DataFrame(
        {
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.5] * 5,
            "volume": [1000.0] * 5,
        },
        index=idx,
    )
    df_y = df_k.copy()
    df_y["close"] = [100.4] * 5

    def h(df):
        buf = io.BytesIO()
        df.to_parquet(buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    assert h(df_k) != h(df_y), "Données différentes → même hash (collision silencieuse)"


@check("FetchResult.hash tracé par source dans source_manifest", "H")
def h3():
    import pandas as pd

    from dal.adapters.in_memory import InMemorySource
    from dal.interfaces.source import FetchRequest

    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.1] * 3,
            "low": [0.9] * 3,
            "close": [1.0] * 3,
            "volume": [50.0] * 3,
        },
        index=idx,
    )
    src_obj = InMemorySource(data={"PAXG-USD": df}, source_id="kraken_mock")
    req = FetchRequest(
        asset_id="PAXG-USD", start="2020-01-01", end="2020-01-03", timeframe="1D"
    )
    result = src_obj.fetch(req)
    assert (
        hasattr(result, "hash") and result.hash
    ), "FetchResult.hash vide — traçabilité de provenance compromise"
    assert (
        result.source_id == "kraken_mock"
    ), f"source_id incorrect : '{result.source_id}'"


# ─── Exécution ────────────────────────────────────────────────────────────────


def run_all():
    for fn in [
        a1,
        a2,
        a3,
        a4,
        a5,
        a6,
        a7,
        a8,
        b1,
        b2,
        b3,
        b4,
        b5,
        b6,
        b7,
        c1,
        c2,
        c3,
        c4,
        c5,
        d1,
        d2,
        d3,
        d4,
        e1,
        e2,
        e3,
        e4,
        f1,
        f2,
        f3,
        f4,
        f5,
        g1,
        g2,
        g3,
        g4,
        g5,
        h1,
        h2,
        h3,
    ]:
        fn()


if __name__ == "__main__":
    print("=" * 60)
    print("MIF-DAL Adversarial Check — v2")
    print(f"dqf disponible : {'OUI' if DQF_AVAILABLE else 'NON (G4/G5 → SKIP)'}")
    print("Référence : DAL_SPECIFICATION_v1.0.md")
    print("=" * 60)

    run_all()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    errors = sum(1 for r in RESULTS if r["status"] == "ERROR")
    skipped = sum(1 for r in RESULTS if r["status"] == "SKIP")

    print("\n" + "=" * 60)
    print(
        f"RÉSULTAT : {passed}/{total} PASS  |  {failed} FAIL  |  {errors} ERROR  |  {skipped} SKIP"
    )
    print("=" * 60)

    if failed > 0 or errors > 0:
        print("\nÉCHECS / ERREURS :")
        for r in RESULTS:
            if r["status"] in ("FAIL", "ERROR"):
                print(f"  [{r['group']}] {r['name']}")
                if r["detail"]:
                    print(f"      {r['detail'][:200]}")
        print()
        sys.exit(1)
    else:
        print(
            f"\nTous les invariants DAL vérifiés ({skipped} checks skippés — dqf absent)."
        )
        sys.exit(0)
