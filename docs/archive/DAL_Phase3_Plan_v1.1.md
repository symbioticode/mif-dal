# MIF-DAL — Mini-Phase 3 : Publication v0.1.0
**Version** : 1.1 — Ajout couverture multi-environnements  
**Destinataire** : OpenCode / Nemotron 3 Super Free  
**Date** : 2026-05-09  
**Sources KB** : DUKASCOPY_COMPLETE_GUIDE.md v1.1 · kb_kraken_bitget.md · KB-DAL-003  
**Supersède** : DAL_Phase3_Plan_v1.0.md

---

## Bootstrap obligatoire (lire avant toute action)

```
1. halo/project_instructions.md
2. halo/anamnese_state.yaml
3. halo/protocols.yaml
4. docs/DAL_SPECIFICATION_v1.0.md
```

Confirmation attendue :
```
HALO chargé.
Phase active     : DAL — Phase 3 (publication)
Module courant   : mif-dal v0.1.0
Prochaine action : §0 validate_environment.py
Modèle utilisé   : Nemotron 3 Super Free (OpenCode Zen)
Intervention Andrei requise : NON
```

---

## §0 — Matrice environnements

Trois environnements cibles. Chaque sprint doit passer sur les trois.

| Feature | NixOS (dev) | Google Colab | Windows |
|---------|------------|--------------|---------|
| Python cmd | `.venv/bin/python` | `python` | `python` |
| pytest cmd | `.venv/bin/python -m pytest` | `pytest` | `pytest` |
| npm global | `~/.npm-global` (nix store read-only) | `/usr/local` | `%APPDATA%\npm` |
| dukascopy-node | `PATH` export dans shellHook requis | global direct | global direct |
| Détection binaire | `--help` (exit 0) **jamais** `--version` (exit 1 — bug upstream) | idem | idem |
| Encoding logs | UTF-8 ok | UTF-8 ok | CP1252 — **pas d'emojis** |
| stdin subprocess | `DEVNULL` recommandé | `DEVNULL` | `DEVNULL` obligatoire |
| Réseau | disponible | disponible | disponible |
| Variables CI | `DUKASCOPY_DRY_RUN=1` si node absent | idem | idem |

### validate_environment.py — à créer dans `scripts/`

Ce script remplace le checklist manuel. Il vérifie les prérequis avant tout
sprint et produit un rapport GO/NO-GO par environnement.

```python
#!/usr/bin/env python3
"""
validate_environment.py — Pré-requis mif-dal v0.1.0
Usage : python scripts/validate_environment.py
"""
import sys
import subprocess
import importlib
import platform

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

@check("Node.js disponible")
def node_available():
    r = subprocess.run(["node", "--version"],
                       capture_output=True, timeout=10,
                       stdin=subprocess.DEVNULL)
    assert r.returncode == 0, "node non trouvé dans PATH"

@check("dukascopy-node installé (--help, pas --version)")
def dukascopy_available():
    # IMPORTANT : --version retourne exit code 1 même si installé (bug upstream)
    # Utiliser --help (exit 0) comme vérification — DUKASCOPY_COMPLETE_GUIDE §Installation
    for cmd in [["npx", "dukascopy-node", "--help"],
                ["dukascopy-node", "--help"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=10,
                               stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                return  # OK
        except FileNotFoundError:
            continue
    raise AssertionError(
        "dukascopy-node non accessible.\n"
        "NixOS  : export NPM_GLOBAL=$HOME/.npm-global && "
        "npm install --prefix $NPM_GLOBAL -g dukascopy-node\n"
        "Autres : npm install -g dukascopy-node"
    )

# ── Encodage (Windows) ────────────────────────────────────────────────────────

@check("Encoding stdout UTF-8 ou compatible")
def encoding_check():
    enc = sys.stdout.encoding or ""
    if platform.system() == "Windows" and enc.upper() == "CP1252":
        # Avertissement, pas un échec bloquant
        print("  WARN : Windows CP1252 — ne pas utiliser d'emojis dans les logs")

# ── mif-dal lui-même ──────────────────────────────────────────────────────────

@check("dal importable")
def dal_import():
    import dal  # noqa

@check("dal.__version__ défini")
def dal_version():
    import dal
    assert hasattr(dal, "__version__"), "dal.__version__ manquant"
    assert dal.__version__, "dal.__version__ vide"

# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Environnement : {platform.system()} / Python {sys.version.split()[0]}")
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
        print("RESULT: GO — environnement prêt")
```

**Exécution par environnement** :
```bash
# NixOS
.venv/bin/python scripts/validate_environment.py

# Colab / Windows
python scripts/validate_environment.py
```

---

## §1 — Bloquants à résoudre avant tout sprint

### Bug A — TypeError `resolve_and_fetch()` (tests/test_integration.py:42, 86)

**Symptôme** :
```
TypeError: resolve_and_fetch() takes 0 positional arguments but 2 were given
```

**Diagnostic** :
```bash
.venv/bin/python -c "
from dal.core.sources import resolve_and_fetch
import inspect; print(inspect.signature(resolve_and_fetch))
"
```

**Fix** : corriger l'appel dans `test_integration.py` pour correspondre
à la signature réelle. C'est un bug de test, pas de production.  
Ne pas modifier `resolve_and_fetch`.

---

### Bug B — Kraken retourne 0 lignes pour BTC-USD (test_integration.py:129)

**Symptôme** :
```
AssertionError: Kraken returned no data
FetchResult(..., status='success', rows=0, hash='...')
```

**Cause** : Kraken utilise ses propres identifiants internes.
`BTC-USD` en entrée ne map pas directement au ticker de réponse.
Source : kb_kraken_bitget.md §Mapping Symboles Incorrects.

```
Kraken reçoit  : pair=XBTUSD  (ou BTC/USD selon l'adaptateur)
Kraken retourne: clé XXBTZUSD dans le JSON de réponse
```

**Diagnostic** :
```bash
.venv/bin/python -c "
import requests
# Test avec la clé Kraken native
r = requests.get('https://api.kraken.com/0/public/OHLC',
    params={'pair': 'XBTUSD', 'interval': 1440,
            'since': 1704067200})  # 2024-01-01 UTC
d = r.json()
print('error :', d.get('error'))
result = d.get('result', {})
print('keys  :', list(result.keys()))
for k, v in result.items():
    if k != 'last':
        print(f'rows for {k}:', len(v))
"
```

**Fix attendu** — deux actions possibles :

Option A (recommandée) : corriger le mapping dans `KrakenAdapter` pour
gérer la réponse `XXBTZUSD` quand le symbole demandé est `BTC-USD` ou `XBTUSD`.

Option B : étendre le range de test à 7+ jours — la période 2024-01-01→03
(2 jours) peut retourner 0 lignes pour des données daily si le marché
était fermé. Utiliser 2024-01-01→2024-01-10.

```python
# Option B — fix test uniquement
req = FetchRequest(
    asset_id="BTC-USD",
    start="2024-01-01",
    end="2024-01-10",   # ← 9 jours au lieu de 2
    timeframe="1D",
)
```

**Remarque** : Kraken peut aussi déclencher un lockout temporaire si trop
de requêtes en peu de temps (`EGeneral:Temporary lockout`). Si l'erreur
change, attendre 15 min avant de réessayer. Source : kb_kraken_bitget.md.

---

### Bug C — Dukascopy retourne `status='failed'` (test_dukascopy_adapter.py:190)

**Symptôme** :
```
dukascopy-node absent (tests réseau skippés)  ← alors que le binaire est installé
FetchResult(..., status='failed', rows=0)
```


## Point 1 — Dukascopy : cause racine réelle

Le plan Phase 3 l'a correctement identifié. **Ce n'est pas un problème d'installation — c'est un bug upstream de `dukascopy-node`** : `--version` retourne toujours exit code 1 même quand le binaire est installé. Si `conftest.py` ou `DukascopyAdapter._node_available()` utilise `--version` pour détecter le binaire, il conclut toujours à l'absence.

Deux corrections à faire dans le code existant :

**Fix 1 — `conftest.py` : `_npx_dukascopy_available()`**

```python
# AVANT (mauvais) :
result = subprocess.run(
    ["npx", "dukascopy-node", "--version"],  # exit 1 même si installé
    ...
)
return result.returncode == 0  # toujours False

# APRÈS (correct) :
result = subprocess.run(
    ["npx", "dukascopy-node", "--help"],     # exit 0 si installé
    capture_output=True,
    timeout=10,
    stdin=subprocess.DEVNULL,
)
return result.returncode == 0
```

**Fix 2 — `dal/adapters/dukascopy.py` : `_node_available()`**

```python
# AVANT :
def _node_available(self) -> bool:
    return shutil.which(self.node_binary) is not None
# shutil.which fonctionne seulement si dukascopy-node est dans PATH

# APRÈS — tester via --help (exit 0), pas --version (exit 1) :
def _node_available(self) -> bool:
    for cmd in [
        [self.node_binary, "--help"],
        ["npx", "dukascopy-node", "--help"],
    ]:
        try:
            r = subprocess.run(
                cmd, capture_output=True, timeout=10,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                return True
        except FileNotFoundError:
            continue
    return False
```

Ces deux fixes sont la totalité de ce qu'il faut pour résoudre le problème dukascopy. 
Le TD-012 dans le plan Phase 3 doit être créé si les 30 minutes sont dépassées, mais avec ces deux corrections on ne devrait pas en avoir besoin.


**Si non résolu après 30 min** : marquer `test_fetch_real_btc_1d` comme
`xfail` avec raison explicite et créer TD-012.

```python
@pytest.mark.network
@pytest.mark.xfail(
    reason="TD-012 : dukascopy-node PATH instable en NixOS nix-shell — "
           "fix : exporter NPM_GLOBAL dans shellHook"
)
def test_fetch_real_btc_1d(adapter, skip_if_no_dukascopy, skip_if_no_network):
    ...
```

---

## §2 — Merge des branches

```bash
# Gate : bugs A et B résolus, test_dukascopy xfail si nécessaire
.venv/bin/python -m pytest tests/ --run-network -k "not dukascopy" -q
# Attendu : 0 failed

git checkout main
git merge feat/yfinance-1.3.0-pinning
git push origin main
```

---

## Sprint DAL-010 — Coverage core ≥ 80%

**Objectif** : couvrir les paths d'erreur des 5 modules core (33–50% → 80%+).

### Vérification initiale
```bash
.venv/bin/python -m pytest tests/ --cov=dal --cov-report=term-missing -q \
    | grep -E "(handoff|pipeline|sources|dal\.py|exceptions)"
```

### Tests à écrire par module

**dal/core/handoff.py** (39% → 85%+) — `tests/test_handoff.py`
```python
def test_handoff_rejects_nan_in_stream()
def test_handoff_rejects_non_utc_index()
def test_handoff_rejects_missing_ohlcv_columns()
def test_handoff_frozen_raises_on_mutation()
def test_source_manifest_is_tuple_not_list()
```

**dal/core/pipeline.py** (44% → 85%+) — `tests/test_pipeline.py`
```python
def test_assemble_raises_on_dqf_void()
def test_assemble_passes_with_warning_flag()
def test_assemble_raises_on_version_mismatch()
def test_assemble_raises_on_unexpected_dqf_status()   # case _
```

**dal/core/sources.py** (33% → 80%+) — `tests/test_sources.py`
```python
def test_fallback_triggered_on_primary_failure()
def test_retry_before_fallback()
def test_all_sources_fail_raises()
def test_coverage_degraded_below_80_pct()
def test_coverage_partial_start_truncated()
def test_aqi_floor_at_zero()           # cumul pénalités > 1.0 → aqi = 0.0
```

**dal/dal.py** (37% → 80%+) — `tests/test_dal.py`
```python
def test_get_diagnostic_stream_returns_handoff()
def test_get_certified_raises_without_calendar()
def test_get_certified_raises_on_version_mismatch()
def test_certified_propagates_handoff_error()
```

**dal/exceptions.py** (50% → 90%+) — `tests/test_exceptions.py`
```python
def test_handoff_error_carries_reason()
def test_handoff_error_carries_dqf_report()
def test_version_error_carries_versions()
def test_source_error_is_dal_error()
```

**Gate DAL-010** :
```bash
.venv/bin/python -m pytest tests/ --cov=dal --cov-report=term -q
# Attendu : coverage ≥ 80%, 0 failed
```

---

## Sprint DAL-011 — Test intégration réel DQF

**Objectif** : un test bout-en-bout sans mock DQF, reproductible sans réseau.

Créer `tests/test_integration_real_dqf.py` :

```python
"""
Intégration bout-en-bout DAL → DQF réel → DALHandoff.
Pas de mock. InMemorySource avec données synthétiques déterministes.
Toujours lancé (pas @network). Reproductible sur NixOS, Colab, Windows.
"""
import numpy as np
import pandas as pd
from dal import DAL, DALConfig
from dal.adapters.in_memory import InMemorySource


def make_clean_ohlcv(n: int = 252) -> pd.DataFrame:
    """OHLCV synthétique satisfaisant toutes les contraintes DQF."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-02", periods=n, freq="B", tz="UTC")
    close = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, n)))
    return pd.DataFrame({
        "open":   close * np.random.uniform(0.99, 1.01, n),
        "high":   close * np.random.uniform(1.001, 1.02, n),
        "low":    close * np.random.uniform(0.98, 0.999, n),
        "close":  close,
        "volume": np.random.uniform(1000, 5000, n),
    }, index=dates)


def test_pipeline_certified_pass():
    df = make_clean_ohlcv()
    dal = DAL(DALConfig(), sources=[InMemorySource({"PAXG-USD": df})])
    h = dal.get_certified_stream(
        "PAXG-USD", start="2023-01-02", end="2023-12-29",
        calendar="CRYPTO_247", dqf_version_target="1.2.0",
    )
    assert h.dqf_status == "PASS"
    assert len(h.assembly_hash) == 64
    assert h.aqi == 100.0
    assert h.stream.isna().sum().sum() == 0
    assert h.dqf_mpi >= 90.0


def test_pipeline_reproducible_hash():
    """Même données → même assembly_hash sur tout environnement."""
    df = make_clean_ohlcv()
    kwargs = dict(
        asset_id="PAXG-USD", start="2023-01-02", end="2023-12-29",
        calendar="CRYPTO_247", dqf_version_target="1.2.0",
    )
    h1 = DAL(DALConfig(), sources=[InMemorySource({"PAXG-USD": df.copy()})]) \
         .get_certified_stream(**kwargs)
    h2 = DAL(DALConfig(), sources=[InMemorySource({"PAXG-USD": df.copy()})]) \
         .get_certified_stream(**kwargs)
    assert h1.assembly_hash == h2.assembly_hash
    assert h1.dqf_mpi == h2.dqf_mpi
```

**Gate DAL-011** :
```bash
.venv/bin/python -m pytest tests/test_integration_real_dqf.py -v
# Attendu : 2/2 passed
```

---

## Sprint DAL-012 — README + CHANGELOG + version 0.1.0

### README.md — sections obligatoires

```markdown
## Installation
pip install mif-dal

## Requirements
- Python >= 3.11
- mif-dqf >= 1.2.0
- yfinance >= 1.3.0, < 2.0.0
- Node.js >= 20 (pour DukascopyAdapter uniquement)

## Quick start
# Deux appels DAL séparés — un par actif (D-DAL-007)
h_paxg = dal.get_certified_stream("PAXG-USD", ...)
h_btc  = dal.get_certified_stream("BTC-USD", ...)
prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]

## Windows
- Logging sans emojis (encodage CP1252)
- stdin=subprocess.DEVNULL sur tous les subprocess

## Dukascopy on NixOS
- Voir docs/KB-DAL-003.md
- Detection : npx dukascopy-node --help (pas --version — bug upstream)
- PATH : export NPM_GLOBAL=$HOME/.npm-global dans shellHook

## Known limitations
- TD-008 : AQI gravities non calibrées empiriquement
- TD-010 : Timestamp.utcnow() deprecated dans yfinance 1.3.x
- TD-012 : dukascopy-node PATH instable NixOS (xfail)
```

### CHANGELOG.md (entrée 0.1.0)

```markdown
## [0.1.0] — 2026-05-XX

### Added
- DALHandoff (frozen=True, 15 champs, assembly_hash, AQI)
- Exceptions hierarchy (DALConfigError, DALVersionError, DALHandoffError)
- pipeline.assemble_handoff() : S3 hash + S4 DQF gate + S5 emission
- resolve_and_fetch() : S1 résolution + retry/fallback + S2 completeness + AQI floor
- KrakenAdapter (REST public, pagination, PAXG/BTC)
- YahooAdapter (yfinance >= 1.3.0, MultiIndex, requests fallback)
- DukascopyAdapter (subprocess dukascopy-node, détection via --help)
- InMemorySource (tests déterministes, mode failure)
- validate_environment.py (NixOS / Colab / Windows)
- validate_dal_state.py (GO/NO-GO 5 checks)
- adversarial_dal_check.py (41 invariants structurels)

### Fixed
- DQF FAIL inexistant → mapping VOID + case _  (DQF_UNEXPECTED_STATUS)
- AQI floor max(0, ...) — valeurs négatives impossibles
- frozen=True sur DALHandoff — source_manifest en tuple
- calendar required dans get_diagnostic_stream (invariant DALHandoff)
- dukascopy-node détection via --help (--version exit 1 = bug upstream)

### Known issues
- TD-010 : Timestamp.utcnow() deprecated yfinance 1.3.x (non-bloquant)
- TD-012 : dukascopy-node PATH instable NixOS nix-shell (test xfail)
```

### Version bump
```bash
# pyproject.toml  : version = "0.1.0"
# dal/__init__.py : __version__ = "0.1.0"
git add pyproject.toml dal/__init__.py CHANGELOG.md README.md
git commit -m "chore: bump version 0.1.0"
```

---

## Sprint DAL-013 — Publication multi-environnements

### Build
```bash
uv build
ls dist/
# mif_dal-0.1.0-py3-none-any.whl
# mif_dal-0.1.0.tar.gz
```

### TestPyPI
```bash
uv publish --index testpypi

# Vérification dans venv propre
python -m venv /tmp/test_mif_dal
/tmp/test_mif_dal/bin/pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    mif-dal==0.1.0
/tmp/test_mif_dal/bin/python -c "import dal; print(dal.__version__)"
```

### Script de vérification post-install (universel)

Valide l'installation sur NixOS, Colab et Windows sans réseau.

```python
# verify_install.py — exécuter après pip install mif-dal
"""
Vérifie que mif-dal est fonctionnel après installation PyPI.
Reproductible : pas de réseau requis, pas de dépendances système.
"""
import sys, platform
import numpy as np
import pandas as pd

print(f"Platform : {platform.system()} / Python {sys.version.split()[0]}")

# 1. Import
from dal import DAL, DALConfig
from dal.adapters.in_memory import InMemorySource
print(f"mif-dal  : {__import__('dal').__version__}")

# 2. Données synthétiques
np.random.seed(42)
dates = pd.date_range("2023-01-02", periods=100, freq="B", tz="UTC")
close = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, 100)))
df = pd.DataFrame({
    "open": close, "high": close * 1.01,
    "low": close * 0.99, "close": close, "volume": 1000.0,
}, index=dates)

# 3. Pipeline complet sans réseau
h = DAL(DALConfig(), sources=[InMemorySource({"TEST-USD": df})]) \
    .get_certified_stream(
        "TEST-USD", start="2023-01-02", end="2023-05-31",
        calendar="NYSE", dqf_version_target="1.2.0",
    )

print(f"dqf_status : {h.dqf_status}")
print(f"assembly_hash : {h.assembly_hash[:16]}...")
print(f"aqi : {h.aqi}")
print(f"dqf_mpi : {h.dqf_mpi:.1f}")
assert h.dqf_status == "PASS"
assert len(h.assembly_hash) == 64
assert h.aqi == 100.0
print("RESULT: OK")
```

### PyPI final
```bash
uv publish
pip install mif-dal==0.1.0
python verify_install.py
```

---

## Guide d'exécution par environnement

### NixOS
```bash
# Entrée environnement
nix-shell  # pas nix develop — Python 3.11 dans .venv

# Pré-requis Dukascopy (si nécessaire)
export NPM_GLOBAL="$HOME/.npm-global"
export PATH="$NPM_GLOBAL/bin:$PATH"
npm install --prefix "$NPM_GLOBAL" -g dukascopy-node

# Validation environnement
.venv/bin/python scripts/validate_environment.py

# Tests complets
.venv/bin/python -m pytest tests/ -q                          # sans réseau
.venv/bin/python -m pytest tests/ --run-network -q            # avec réseau

# Publication
.venv/bin/python -m build && uv publish
```

### Google Colab
```python
# Cellule 1 — installation
!pip install mif-dal mif-dqf yfinance>=1.3.0

# Cellule 2 — Dukascopy (optionnel — DRY_RUN sinon)
!npm install -g dukascopy-node

# Cellule 3 — validation
!python scripts/validate_environment.py

# Cellule 4 — tests
!pip install pytest pytest-cov
!git clone https://github.com/dravitch/mif-dal /content/mif-dal
%cd /content/mif-dal
!pytest tests/ -q                     # sans réseau
!pytest tests/ --run-network -q       # avec réseau Colab

# Cellule 5 — vérification post-install
!python verify_install.py
```

### Windows (PowerShell)
```powershell
# Encodage console — éviter CP1252
$env:PYTHONIOENCODING = "utf-8"

# Installation
pip install mif-dal mif-dqf yfinance
npm install -g dukascopy-node

# Validation environnement
python scripts\validate_environment.py
# Note : WARN CP1252 attendu, pas un échec bloquant

# Tests
pip install pytest pytest-cov
pytest tests\ -q                            # sans réseau
pytest tests\ --run-network -q              # avec réseau

# Vérification post-install
python verify_install.py
```

**Note Windows spécifique** : si des tests de logging échouent avec
`UnicodeEncodeError`, c'est l'encodage CP1252. Fix : ajouter dans
`conftest.py` :

```python
# conftest.py — compatibilité Windows
import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

---

## Gates de publication récapitulatifs

| Gate | Commande | Attendu |
|------|----------|---------|
| Tests sans réseau | `pytest tests/ -q` | 169+ passed, 0 failed |
| Coverage global | `--cov=dal --cov-report=term` | ≥ 80% |
| Tests réseau (non-Dukascopy) | `--run-network -k "not dukascopy"` | 0 failed |
| Adversarial | `python adversarial_dal_check.py` | 41/41 PASS |
| Validate state | `python scripts/validate_dal_state.py` | GO |
| Validate environment | `python scripts/validate_environment.py` | GO |
| Intégration DQF réel | `pytest tests/test_integration_real_dqf.py` | 2/2 |
| Install TestPyPI | `pip install mif-dal==0.1.0` | import OK |
| Verify install (multi-env) | `python verify_install.py` | RESULT: OK |

---

## Dettes à ajouter dans anamnese_state.yaml

```yaml
dette_technique:
  - id: TD-012  # nouveau
    description: |
      dukascopy-node PATH non persisté dans nix-shell au démarrage.
      Symptôme : is_available() retourne False même après installation.
      Cause : NPM_GLOBAL/bin absent du PATH si shellHook non appliqué.
      Fix propre : ajouter export NPM_GLOBAL dans shell.nix shellHook.
      Détection correcte : --help (exit 0), jamais --version (exit 1 — bug upstream).
    cible: "mif-dal v0.2.0"
    condition: "Non bloquant pour v0.1.0 — test xfail"
```

---

## Ordre d'exécution recommandé

```
§0  validate_environment.py (NixOS en premier)
     ↓
§1  Bug A : fix resolve_and_fetch() TypeError
    Bug B : fix Kraken symbol mapping + range
    Bug C : fix dukascopy-node détection (--help) ou xfail + TD-012
     ↓
§2  Merge feat/yfinance-1.3.0-pinning → main
     ↓
DAL-010  Coverage core ≥ 80%
     ↓
DAL-011  test_integration_real_dqf.py (2 tests)
     ↓
DAL-012  README + CHANGELOG + version 0.1.0
         validate_environment.py finalisé
         verify_install.py créé
     ↓
DAL-013  TestPyPI → verify_install.py → PyPI
         Valider sur NixOS + Colab + Windows
     ↓
SESSION_REPORT → anamnese_state.yaml mis à jour (TD-012 ajouté)
```

---

## Hors scope de ce plan

- Cache local `dal/core/cache.py` (TD-005) → v0.2.0
- MIF-Core spécification → session dédiée
- Protocole post-NON QS-MÉTIS (AM-005) → QAAF Studio
- `test_strategy_fn_is_not_constant()` (AM-001) → premier test mif-core

*Supersède : DAL_Phase3_Plan_v1.0.md*  
*Sources : DUKASCOPY_COMPLETE_GUIDE.md v1.1 · kb_kraken_bitget.md · KB-DAL-003*
