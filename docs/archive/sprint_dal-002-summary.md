## Résumé de session — À destination de l'instance MIF

**Période couverte** : Sessions 2026-05-07 → 2026-05-08  
**Sprints exécutés** : DAL-007 → DAL-009 (+ stabilisation environnement)  
**État à la clôture** : 169/169 tests · 99% coverage Phase 1 · 61% coverage global · 41/41 adversarial · validate_dal_state.py GO

---

## État cumulé des sprints

| Sprint | Module | Tests | Statut |
|--------|--------|-------|--------|
| DAL-001 | `DALHandoff` (15 champs, frozen=True) | 23 | ✓ |
| DAL-002 | Exceptions (`DALError` hierarchy) | 51 | ✓ |
| DAL-003 | `DALConfig` | 58 | ✓ |
| DAL-004 | `pipeline.assemble_handoff()` — S3+S4+S5 | 73 | ✓ |
| DAL-005 | `sources/` — S1+S2+AQI + InMemorySource | 104 | ✓ |
| DAL-006 | Classe `DAL` publique — `get_certified_stream()` / `get_diagnostic_stream()` | 119 | ✓ |
| DAL-007 | `KrakenAdapter` — API REST publique, pagination, PAXG/BTC | 19 tests (+2 network) | ✓ |
| DAL-008 | `DukascopyAdapter` — subprocess dukascopy-node, BTC/ETH | 13 tests (+1 network) | ✓ |
| DAL-009 | `YahooAdapter` — yfinance 1.3.0, fallback requests, MultiIndex | 22 tests (+2 network) | ✓ |

**Tests réseau** : 5 skippés par défaut, passent avec `--run-network` (54/55 avec réseau, 1 skip Dukascopy si node absent).

---

## Décisions prises en Phase 2

| ID | Décision | Statut |
|----|----------|--------|
| Ordre adaptateurs | Kraken → Dukascopy → Yahoo (pas l'inverse) | APPLIQUÉ |
| yfinance pin | `>=1.3.0,<2.0.0` — jamais 0.2.51 en production | FERMÉ — TD-009 résolu |
| Dukascopy PAXG | `supports("PAXG-USD") → False` — invariant critique | FERMÉ |
| Yahoo fallback | requests natif si yfinance < 30 lignes (résolution gate0) | APPLIQUÉ |
| Tests réseau | `@pytest.mark.network` + `--run-network` flag | APPLIQUÉ |

---

## Problèmes résolus en Phase 2

**1 — Import circulaire `dal/__init__.py`**  
`from dal.dal import DAL` cassait l'import de tout le package.  
Résolution : `dal/dal.py` créé comme façade, `__version__` déclaré directement dans `__init__.py`.

**2 — Environnement NixOS dual-shell**  
`nix develop` (Python 3.12, nix store) ≠ `nix-shell` (Python 3.11, `.venv`).  
`mif-dqf` installé dans `.venv` via `uv` — uniquement accessible via `.venv/bin/python -m pytest`.  
Résolution : toujours utiliser `.venv/bin/python -m pytest`, jamais `pytest` nu dans nix develop.  
Documenté dans KB-DAL-003 (ci-dessous).

**3 — `dukascopy-node` non accessible dans nix store**  
`npm install -g` échoue (read-only). Solution : `~/.npm-global` comme préfixe.  
`dukascopy-node` reste absent de l'env `.venv` par design — le test réseau se skipppe proprement.

**4 — `test_different_data_different_hash`**  
Test réseau qui comparait deux appels Yahoo réels sur le même actif → même hash.  
Résolution : remplacé par `test_different_data_different_hash_mocked` (mock contrôlé).

---

## Coverage — analyse des gaps

| Module | Coverage | Lignes non couvertes | Action |
|--------|----------|---------------------|--------|
| `dal/core/handoff.py` | 39% | 46-128 : constructeur + validations | Couvrir en DAL-010 |
| `dal/core/pipeline.py` | 44% | 52-112 : paths d'erreur DQF VOID/WARNING | Couvrir en DAL-010 |
| `dal/core/sources.py` | 33% | 65-206 : resolver, fallback chain | Couvrir en DAL-010 |
| `dal/dal.py` | 37% | 22-124 : get_diagnostic_stream, error paths | Couvrir en DAL-010 |
| `dal/exceptions.py` | 50% | 45-80 : attributs des exceptions | Couvrir en DAL-010 |
| `dal/adapters/in_memory.py` | 0% | Tous : jamais importé dans ces tests | Normal — couvert dans tests Phase 1 |
| `dal/adapters/kraken.py` | 94% | 173-288 : edge cases pagination | Acceptable |
| `dal/adapters/yahoo.py` | 85% | fallback paths | Acceptable |
| `dal/adapters/dukascopy.py` | 77% | subprocess error paths | Acceptable |

**Objectif DAL-010** : 80%+ coverage global avant publication PyPI.

---

## Phase 3 restante — DAL-010

| Tâche | Priorité | Estimé |
|-------|----------|--------|
| Coverage core modules (pipeline, sources, handoff) | HAUTE | 1 session |
| Cache local `dal/core/cache.py` (TD-005) | MOYENNE | 0.5 session |
| `validate_dal_state.py` versionné dans le repo | HAUTE | inclus dans coverage |
| Exemple README complet (get_certified_stream PAXG+BTC) | BASSE | 1h |
| Bump version → 0.1.0 + CHANGELOG | HAUTE | 0.5h |
| Publication PyPI (TestPyPI d'abord) | HAUTE | 0.5 session |

**Gate publication** : 80%+ coverage global · adversarial 41/41 · validate GO · `pip install mif-dal` fonctionnel.

---

## Dettes techniques créées en Phase 2

| ID | Description | Cible | Condition |
|----|-------------|-------|-----------|
| TD-009 | yfinance 0.2.51 éliminé — 1.3.0 adopté directement | FERMÉ | Résolu |
| TD-010 | `Timestamp.utcnow()` deprecated dans yfinance 1.3.x | mif-dal v0.2.0 | Warning non-bloquant, patch yfinance |
| TD-011 | Coverage core < 50% — paths d'erreur non testés | mif-dal v0.1.0 avant publication | Bloquant pour confiance 95%+ |

---

## Ce qui reste ouvert (non-bloquant pour publication)

- AM-001 : `test_strategy_fn_is_not_constant()` → MIF-Core
- AM-004 : `compute_n_effectif()` pour DSR → MIF-Core
- AM-005 : protocole post-NON QS-MÉTIS → QAAF Studio
- C1 Stream Integrity : toujours `c1_enabled: false` → v1.2 après DAL stable
