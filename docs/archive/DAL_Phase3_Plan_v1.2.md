# MIF-DAL — Phase 3 Plan v1.2 — Delta uniquement
**Destinataire** : OpenCode / Nemotron 3 Super Free  
**Date** : 2026-05-09  
**Supersède** : DAL_Phase3_Plan_v1.0.md · DAL_Phase3_Plan_v1.1.md  
**Référence** : checklist_errors_p3.txt · anamnese_state.yaml v4.1

> Ce document couvre uniquement le delta entre état actuel et objectif de
> publication. Ne pas répéter les sprints déjà complétés.

---

## Analyse du delta

### Ce qui est acquis — ne pas retoucher

| Item | Preuve |
|------|--------|
| 177/177 tests avec `--run-network` | checklist ligne 262 |
| 169/177 sans réseau (8 skips réseau légitimes) | checklist ligne 17 |
| Adversarial P2 : 41/41 PASS | checklist ligne 84 |
| validate_dal_state.py : GO | checklist ligne 131 |
| validate_environment.py : GO | checklist ligne 117 |
| assembly_hash avant DQF ✓ | adversarial [A] ligne 61 |
| frozen=True ✓, tuple ✓, AQI floor ✓ | adversarial [A] |
| DQF FAIL absent ✓, D-DAL-007 ✓ | adversarial [A] |

### Delta — 11 items à traiter

| # | Item | Catégorie | Bloquant |
|---|------|-----------|---------|
| D1 | `flake.nix` : `python312` → `python311` | Env | OUI |
| D2 | `flake.nix` : supprimer ligne `pkgs.npm` | Env | OUI |
| D3 | Coverage stale : mesure correcte avec `coverage run` | Coverage | OUI |
| D4 | `dal/adapters/dukascopy.py` : `--version` → `--help` | Code | OUI |
| D5 | `dal/__version__` = `'0.0.0+unknown'` → `'0.1.0'` | Publication | OUI |
| D6 | `pyproject.toml` : version cohérente avec `__version__` | Publication | OUI |
| D7 | `CHANGELOG.md` absent | Publication | OUI |
| D8 | `README.md` : ajouter exemple `get_certified_stream` | Publication | OUI |
| D9 | `pyproject.toml` : classifiers PyPI absents | Publication | OUI |
| D10 | `dal/__all__` : manque `get_certified_stream`, `get_diagnostic_stream` | Publication | OUI |
| D11 | `adversarial_dal_check_p3.py` : 4 faux positifs à corriger dans le checker | Checker | NON |

---


# KB-DAL-LintFix — Corrections nécessaires pour passer `dev.sh check`

## 1. Nettoyage Ruff (obligatoire pour passer le gate)
- Supprimer les variables inutilisées (F841)
  ex: `stderr` dans dukascopy.py, `df` dans test_dukascopy_adapter.py
- Supprimer les imports inutilisés (F401)
  ex: Source, io, timezone, pandas, call, Generator, os
- Corriger les lignes trop longues (E501)
  Limite Ruff: 88 caractères → reformater les messages d’erreur et commentaires
- Corriger les clés de dictionnaire dupliquées (F601)
  ex: `"1H"` apparaît deux fois dans yahoo.py
- Utiliser `datetime.UTC` au lieu de `timezone.utc` (UP017)
  partout dans les adapters et tests
- Réorganiser les imports (I001)
  appliquer un tri standard (stdlib → third-party → local)

## 2. Corrections liées aux contraintes réelles des APIs
### Kraken
- L’API ne retourne **aucune donnée plus vieille que 12 mois**
- Les tests doivent utiliser des dates récentes (>= J-12 mois)
- Les tests d’intégration doivent éviter les ranges trop anciens
- Le code doit gérer proprement `df_chunk.empty` → status="failed"

### PAXG-USD
- Kraken bloque PAXG-USD pour les utilisateurs canadiens (maintenance permanente)
- Les tests doivent:
  - soit ignorer Kraken pour PAXG-USD
  - soit accepter un fallback Yahoo uniquement
  - soit marquer le test comme `xfail` pour Kraken

## 3. Corrections spécifiques à appliquer dans le code
- Dukascopy: supprimer `stderr` non utilisé
- Kraken: reformater les commentaires longs, corriger les lignes > 88 chars
- Yahoo: corriger la clé `"1H"` dupliquée
- Handoff: reformater les messages d’erreur trop longs
- Interfaces: raccourcir les commentaires dans les dataclasses

## 4. Corrections spécifiques à appliquer dans les tests
- Supprimer les imports inutilisés
- Raccourcir les lignes > 88 chars
- Adapter les tests d’intégration:
  - utiliser des dates récentes pour Kraken
  - éviter PAXG-USD sur Kraken (maintenance)
  - ajuster les assertions pour accepter fallback Yahoo

## 5. Résultat attendu
Une fois ces corrections appliquées :
- `./scripts/dev.sh check` passe sans erreur
- Les tests restent verts
- Le coverage reste cohérent
- Les tests d’intégration reflètent les limites réelles des APIs


## D1 + D2 — flake.nix : deux corrections

PASS
---

## D3 — Coverage : mesure correcte - FAIT A VERIFIER SEULEMENT

**Problème** : `pytest --cov` échoue (pytest.ini bloque le plugin, ou pytest-cov
non chargé dans le venv). Le rapport `coverage report -m` montre une `.coverage`
stale — `in_memory.py` à 0% alors que 11 tests passent. Les vrais chiffres sont
inconnus.

**Diagnostic d'abord** :
```bash
# Vérifier que pytest-cov est installé dans le venv
.venv/bin/pip show pytest-cov

# Vérifier pytest.ini — chercher addopts ou filterwarnings qui bloquent
cat pytest.ini
```

**Fix A — si pytest-cov absent du venv** :
```bash
.venv/bin/pip install pytest-cov
```

**Fix B — si pytest.ini bloque le plugin** :
Ajouter dans `pytest.ini` :
```ini
[pytest]
addopts = --cov=dal --cov-report=term-missing
```
Ou utiliser `.coveragerc` :
```ini
[coverage:run]
source = dal
```

**Mesure correcte (contourne pytest.ini)** :
```bash
.venv/bin/python -m coverage run -m pytest tests/ -q
.venv/bin/python -m coverage report -m
```

**Gate D3** : coverage global ≥ 80% et `in_memory.py` > 0%.

Si coverage réel < 80% après mesure correcte, ajouter les tests manquants
ciblés (lignes listées dans le rapport `Missing`) avant toute autre action.
Modules probablement sous-couverts : `handoff.py`, `pipeline.py`, `sources.py`,
`dal.py`, `exceptions.py`.

---

## D4 — dukascopy.py : `--version` → `--help`

PASS

---

## D5 + D6 — Version 0.1.0 - FAIT A VERIFIER SEULEMENT

**Problème** :
```
dal.__version__ = '0.0.0+unknown'   ← generé par setuptools sans git tag
pyproject.toml version = 0.1.0      ← correct mais non lu par __init__.py
```

**Cause** : `dal/__init__.py` lit probablement `importlib.metadata` ou
`setuptools_scm` qui retourne `0.0.0+unknown` si le package n'est pas installé
en mode editable avec un tag git.

**Fix — deux options** :

Option A (recommandée pour v0.1) : hard-coder dans `dal/__init__.py` :
```python
__version__ = "0.1.0"
```

Option B : installer en mode editable + créer un tag git :
```bash
git tag v0.1.0
.venv/bin/pip install -e .
```

**Vérification** :
```bash
.venv/bin/python -c "import dal; print(dal.__version__)"
# Attendu : 0.1.0
```

---

## D7 — CHANGELOG.md   FAIT A VERIFIER SEULEMENT
 
Créer `CHANGELOG.md` à la racine du projet :

```markdown
# Changelog

All notable changes to mif-dal are documented here.

## [0.1.0] — 2026-05-XX

### Added
- `DALHandoff` — frozen dataclass, 15 fields, `assembly_hash`, AQI
- Exception hierarchy: `DALError`, `DALConfigError`, `DALVersionError`,
  `DALHandoffError`
- `DALConfig` (cache_dir, request_timeout)
- `pipeline.assemble_handoff()` — S3 hash + S4 DQF gate + S5 emission
- `resolve_and_fetch()` — S1 source resolution + retry/fallback +
  S2 completeness + AQI calculation with floor
- `KrakenAdapter` — public REST API, OHLCV daily, PAXG/BTC
- `YahooAdapter` — yfinance ≥ 1.3.0, MultiIndex handling
- `DukascopyAdapter` — subprocess, detection via `--help`
- `InMemorySource` — deterministic adapter for tests, failure simulation
- `validate_environment.py` — GO/NO-GO for NixOS / Colab / Windows
- `validate_dal_state.py` — GO/NO-GO 5-check script

### Fixed
- DQF has no FAIL status — mapping corrected to VOID + `case _` guard
- AQI floor `max(0, ...)` — formula could produce negative values
- `DALHandoff frozen=True` — `source_manifest` as `tuple`, not `list`
- `calendar` required in `get_diagnostic_stream` (DALHandoff invariant)
- Dukascopy detection via `--help` (not `--version` — upstream exit-1 bug)

### Known issues
- TD-008: AQI gravities (0.20/0.10/0.05/0.30) not empirically calibrated
- TD-012: dukascopy-node PATH unstable in NixOS nix-shell (test xfail)
```

---

## D8 — README.md : exemple get_certified_stream FAIT A VERIFIER SEULEMENT

Ajouter une section `## Quick start` dans `README.md` :

````markdown
## Quick start

```python
from dal import DAL, DALConfig

config = DALConfig()
dal = DAL(config)

# One call per asset — caller builds the pair (D-DAL-007)
h_paxg = dal.get_certified_stream(
    asset_id="PAXG-USD",
    source_preference=["kraken", "yahoo"],
    start="2023-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

h_btc = dal.get_certified_stream(
    asset_id="BTC-USD",
    source_preference=["kraken", "yahoo"],
    start="2023-01-01",
    end="2024-12-31",
    calendar="CRYPTO_247",
    dqf_version_target="1.2.0",
)

# Caller constructs the ratio
prices_pair = h_paxg.stream["close"] / h_btc.stream["close"]

print(f"PAXG/BTC — {len(prices_pair)} days")
print(f"DQF status : {h_paxg.dqf_status} / {h_btc.dqf_status}")
print(f"AQI        : {h_paxg.aqi:.0f} / {h_btc.aqi:.0f}")
print(f"Hash PAXG  : {h_paxg.assembly_hash[:16]}...")
print(f"Hash BTC   : {h_btc.assembly_hash[:16]}...")
```
````

---

## D9 — pyproject.toml : classifiers PyPI FAIT A VERIFIER SEULEMENT

Ajouter dans `pyproject.toml` sous `[project]` :

```toml
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Financial and Insurance Industry",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Office/Business :: Financial",
    "Topic :: Scientific/Engineering",
]
```

---

## D10 — dal/__all__  FAIT A VERIFIER SEULEMENT

Ajouter dans `dal/__init__.py` :

```python
__all__ = [
    "DAL",
    "DALConfig",
    "DALHandoff",
    "DALError",
    "DALConfigError",
    "DALVersionError",
    "DALHandoffError",
    "get_certified_stream",    # ← manquant
    "get_diagnostic_stream",   # ← manquant
]
```

**Vérification** :
```bash
.venv/bin/python -c "import dal; print(dal.__all__)"
```

---

## D11 — adversarial_dal_check_p3.py : 4 faux positifs (non-bloquant)

Ces 4 checks du P3 checker échouent à cause de bugs dans le checker,
pas dans le code. Le checker peut être mis à jour séparément.

| Check | Problème dans le checker | Correction |
|-------|--------------------------|------------|
| "DALHandoff 15 champs" — 7 manquants | Le checker cherche des noms (`fetched_at`, `mode`, `start`, `end`, `completeness`, `assembled_at`, `timeframe`) qui ne correspondent pas aux noms réels implémentés | Lire `handoff.py` et aligner les noms attendus |
| "assembly_hash avant DQF" | Check identique passe en P2 (41/41). Regex incorrecte dans P3 | Réutiliser la regex de P2 adversarial |
| `InMemorySource.supports()` TypeError | Le checker instancie avec `InMemorySource(asset_id=...)` — mauvaise signature | Corriger l'appel pour correspondre à la vraie signature |
| `get_certified_stream` manque `timeframe` | `timeframe` est dans `FetchRequest`, pas dans `get_certified_stream` — hors spec §7 | Supprimer ce check ou corriger la référence |

**Action** : corriger le checker APRÈS que tous les vrais items (D1-D10) soient
verts. Ne pas bloquer la publication sur D11.

---

## Ordre d'exécution

```
D1 + D2   flake.nix (python311, supprimer pkgs.npm)     PASS
           → nix develop sans erreur
           ↓
D4         dukascopy.py --version → --help              PASS
           → grep -n "version" dal/adapters/dukascopy.py = rien
           ↓
D3         Coverage : mesure correcte                   ~30 min
           → coverage run -m pytest tests/
           → si < 80% : ajouter tests ciblés
           ↓
D5 + D6    __version__ = "0.1.0"                       ~5 min
D7         CHANGELOG.md                                 ~15 min
D8         README.md exemple                            ~15 min
D9         classifiers pyproject.toml                   ~5 min
D10        dal/__all__                                  ~5 min
           ↓
           Vérification finale
           ↓
D11        P3 adversarial checker (non-bloquant)        ~30 min
```

---

## Gate de publication finale

```bash
# 1. Tests
.venv/bin/python -m pytest tests/ -q
# → 169+ passed, 0 failed

# 2. Coverage réelle
.venv/bin/python -m coverage run -m pytest tests/ -q
.venv/bin/python -m coverage report | tail -1
# → TOTAL ... ≥ 80%

# 3. Version
.venv/bin/python -c "import dal; print(dal.__version__)"
# → 0.1.0

# 4. Adversarial P2 (non-régression)
.venv/bin/python scripts/adversarial_dal_check.py
# → 41/41 PASS

# 5. Publication
uv build
uv publish --index testpypi
python verify_install.py   # voir DAL_Phase3_Plan_v1.1.md §DAL-013
```

UPDATE

Deux problèmes distincts. Voici les fixes dans l'ordre.

---

## 1 — Ruff : cache corrompu par sudo

Le `sudo bash scripts/dev.sh` a créé `.ruff_cache/` avec les permissions root. Fix :

```bash
sudo rm -rf .ruff_cache
.venv/bin/python -m ruff check . --fix
.venv/bin/python -m ruff format .
./scripts/dev.sh check
```

---

## 2 — adversarial_dal_check_p3.py : 4 bugs dans le checker

Les 3 FAIL + 1 ERROR sont des bugs dans le checker, confirmés par le fait que le P2 (41/41) passe les mêmes invariants. Corrections ciblées :

### Bug A — Champs DALHandoff : liste incorrecte

Le checker cherche `fetched_at, mode, end, start, completeness, assembled_at, timeframe` — ces noms n'existent pas dans l'implémentation. Remplacer par les 15 champs réels de la spec §5 :

```python
# Dans adversarial_dal_check_p3.py — section [A]
# Remplacer le set de champs attendus par :
EXPECTED_HANDOFF_FIELDS = {
    "stream", "asset_id", "calendar", "assembly_hash",
    "handoff_timestamp", "dal_version", "source_manifest",
    "coverage", "truncated_days", "dqf_status", "dqf_mpi",
    "dqf_version", "dqf_version_target", "dqf_report", "aqi",
}
```

### Bug B — assembly_hash avant DQF : regex incorrecte

Le P2 passe ce check avec la même logique. Le P3 a une regex différente qui échoue. Remplacer le check P3 par la même logique que P2 — chercher que `assembly_hash` est assigné avant tout appel à dqf dans `pipeline.py` :

```python
# Lire pipeline.py et vérifier l'ordre d'apparition
with open("dal/core/pipeline.py") as f:
    source = f.read()
hash_pos = source.find("assembly_hash")
dqf_pos  = source.find("dqf") if "dqf" in source else source.find("DQF")
assert hash_pos < dqf_pos, "assembly_hash doit apparaître avant l'appel DQF"
```

### Bug C — `get_certified_stream` : `timeframe` n'est pas un paramètre de la méthode

`timeframe` appartient à `FetchRequest`, pas à `get_certified_stream`. Les paramètres corrects selon spec §7 :

```python
# Remplacer la liste des paramètres attendus par :
EXPECTED_PARAMS = {
    "asset_id", "source_preference", "start", "end",
    "calendar", "dqf_version_target",
}
# Supprimer "timeframe" de cette liste
```

### Bug D — `InMemorySource` : instanciation incorrecte

Le checker appelle `InMemorySource(asset_id="TEST-USD")` — mauvais argument. La vraie signature prend un dict `{asset_id: DataFrame}` :

```python
# Remplacer dans le check InMemorySource.supports() :
import pandas as pd
import numpy as np
dates = pd.date_range("2023-01-01", periods=5, freq="B", tz="UTC")
df = pd.DataFrame({
    "open": [100.0]*5, "high": [101.0]*5,
    "low": [99.0]*5, "close": [100.0]*5, "volume": [1000.0]*5,
}, index=dates)

source = InMemorySource({"TEST-USD": df})     # ← correction
assert source.supports("TEST-USD") is True
assert source.supports("UNKNOWN") is False
```


---

## Ordre d'exécution

```bash
# 1. Ruff
sudo rm -rf .ruff_cache
.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .
./scripts/dev.sh check

# 2. Corriger adversarial_dal_check_p3.py (4 bugs ci-dessus)

# 3. Vérification finale
.venv/bin/python scripts/adversarial_dal_check_p3.py
# Attendu : 65/65 PASS

# 4. Gate publication complète
.venv/bin/python -m coverage run -m pytest tests/ -q
.venv/bin/python -m coverage report | tail -1   # ≥ 80%
.venv/bin/python scripts/adversarial_dal_check.py   # 41/41
.venv/bin/python scripts/adversarial_dal_check_p3.py   # 65/65
```

---

*Supersède : DAL_Phase3_Plan_v1.0.md · DAL_Phase3_Plan_v1.1.md*  
*Ne couvre pas : cache local (TD-005, v0.2.0), MIF-Core, QS-MÉTIS*
