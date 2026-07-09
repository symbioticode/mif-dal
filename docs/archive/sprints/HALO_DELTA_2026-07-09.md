# HALO Delta — mif-dal — 2026-07-09
# À lire par Big Pickle (OpenCode) APRÈS project_instructions.md + anamnese_state.yaml + protocols.yaml
# Ce document corrige/complète anamnese_state.yaml v6.0.0 (daté 2026-05-16, obsolète sur plusieurs points).
# Source de vérité pour l'état réel : sorties `dev.sh check` + `adversarial_dal_check_p3.py`
# exécutées par Andrei le 2026-07-09 sur ~/Projects/51_MIF_DAL/mif-dal (= symbioticode/mif-dal, HEAD=origin/main).

---

## 0. Confirmation d'environnement (Andrei, pas l'agent)

- Répertoire de travail canonique : `~/Projects/51_MIF_DAL/mif-dal`
- Remote confirmé : `git@github.com:symbioticode/mif-dal.git`, `origin/main == HEAD` (commit `2167f1e "init"`, 2026-06-06)
- `09_MIF/02-DAL/mif-dal-en` et `09_MIF/02-DAL/mif-dal` (FR) sont des archives figées (remote `dravitch/mif-dal`, bloqué par conflit SSH résolu le 06-06). **Ne pas exécuter le sprint là-dessus.**
- `.gitignore` correct (halo/, *.nix exclus) — confirmé, aucune action requise.

---

## 1. Décision D1 (DAL.__init__ requires `sources`) — FERMÉE

**Choix : Option B** — `sources` reste un paramètre obligatoire de `DAL.__init__`. Aucun défaut ajouté.
Raison : zéro nouvelle logique non testée avant publication v0.1.0 (Delta-Only Refactoring). Les scripts qui appellent `DAL(config)` seul sont corrigés pour passer `sources` explicitement — voir §3.

**Note d'évolution (à revisiter en v0.2.0, pas maintenant)** : évaluer Option A (`sources=None` → adaptateurs par défaut) ou Option C (constructeur `DAL.from_config()`) une fois le premier retour d'usage réel disponible. Ne pas anticiper.

---

## 2. Dette technique — état réel vérifié (pas celui d'anamnese_state.yaml)

| ID | Statut réel | Preuve |
|---|---|---|
| TD-RUFF-ARCHIVE | **CLOSED** | `./scripts/dev.sh check` → `Ruff... All checks passed!` — `pyproject.toml` a déjà `exclude = ["docs/archive/", "dukascopy/"]` |
| TD-MYPY-1 (yahoo.py:329) | **CLOSED par Andrei** (manuel, hors périmètre agent) | `params: dict[str, Any]` ajouté |
| TD-MYPY-2/3 (kraken.py:173,174,259) | **CLOSED par Andrei** | renommage `start_ts/end_ts` (int, API Kraken) vs `req_start/req_end` (Timestamp, troncature). `end_ts` (int) supprimé — n'a jamais servi (Kraken n'a pas de paramètre "fin", seul `since` est utilisé) |
| TD-MYPY-4 (dukascopy.py:235,256) | **CLOSED par Andrei** | kwarg `error=` supprimé des deux appels `FetchResult(...)` |
| TD-014 / TD-VERIFY-API | **OUVERT — assigné à l'agent** | voir §3.1 |
| Bug `dal/__init__.py.__all__` | **NOUVEAU, non documenté avant ce jour — assigné à l'agent** | voir §3.2 |
| E01/E02 dans `adversarial_dal_check_p3.py` (réseau) | **NOUVEAU, confirmé par `--run-network`** | voir §3.3 |
| TD-CONTRIBUTING | OUVERT, priorité basse | voir §3.4 |
| Renommage `verify_install.py` → `test_install.py` | OUVERT, priorité basse | arborescence cible HALO_MIGRATION.md non atteinte |

**Règle pour l'agent : ne pas toucher aux fichiers `dal/adapters/yahoo.py`, `dal/adapters/kraken.py`, `dal/adapters/dukascopy.py` sur les points ci-dessus — déjà corrigés et validés manuellement par Andrei (mypy 0 erreur, ruff 0 erreur). Toute modification de ces 3 fichiers doit être justifiée par un besoin distinct et signalée avant commit.**

---

## 3. Tâches assignées à l'agent (ordre d'exécution)

### 3.1 — Fixer `scripts/verify_install.py` (bloquant, TD-014)

Trois checks échouent avec `TypeError: DAL.__init__() missing 1 required positional argument: 'sources'` et un avec `TypeError: InMemorySource.__init__() missing 1 required positional argument: 'data'`.

Signature réelle de `InMemorySource` : `InMemorySource(source_id: str, data: dict[str, pd.DataFrame], ...)` — positionnel, deux arguments requis.

Fix dans `check_dal_init()`, `check_signature()`, `check_diag_signature()` :
```python
dal_instance = DAL(config, sources=())
```
(un tuple vide suffit — `DAL.__init__` ne valide pas la non-vacuité à la construction, seulement `_resolve_sources()` au moment d'un appel réel)

Fix dans `check_in_memory()` :
```python
source = InMemorySource(source_id="test", data={"TEST-USD": df})
```
(actuellement `InMemorySource({"TEST-USD": df})` — un seul argument positionnel assigné à `source_id`, `data` manquant)

**Gate** : `python scripts/verify_install.py` → 7/7 PASS.

### 3.2 — Corriger `dal/__init__.py.__all__` (bloquant, bug non documenté)

```python
__all__ = [
    "DAL", "DALConfig", "DALConfigError", "DALError",
    "DALHandoff", "DALHandoffError", "DALVersionError",
    "get_certified_stream",   # ← n'existe nulle part dans dal/__init__.py
    "get_diagnostic_stream",  # ← idem — ce sont des méthodes de DAL, pas des noms de module
]
```
`from dal import get_certified_stream` lève `ImportError` — confirmé par Andrei via `adversarial_dal_check_p3.py --run-network` (section E, erreur `ImportError: cannot import name 'get_diagnostic_stream' from 'dal'`).

**Fix** : retirer ces deux noms de `__all__`.
```python
__all__ = [
    "DAL",
    "DALConfig",
    "DALConfigError",
    "DALError",
    "DALHandoff",
    "DALHandoffError",
    "DALVersionError",
]
```

**Effet de bord à corriger dans le même mouvement** : `scripts/adversarial_dal_check_p3.py` check `_g01` exige actuellement que `get_certified_stream`/`get_diagnostic_stream` soient dans `__all__` :
```python
expected = {
    "get_certified_stream",
    "get_diagnostic_stream",
    "DALConfig",
    "DALHandoff",
}
```
→ retirer les deux entrées erronées de `expected` dans `_g01`. Sinon le gate 65/65 se casse après le fix ci-dessus.

**Gate** : `python scripts/adversarial_dal_check_p3.py` → toujours 65/65 PASS après les deux changements combinés.

### 3.3 — Corriger les checks réseau E01/E02 de `adversarial_dal_check_p3.py` (priorité moyenne — ne bloque pas le gate par défaut, seulement `--run-network`)

Confirmé cassé par Andrei :
```
! ERREUR : TypeError: InMemorySource.__init__() got an unexpected keyword argument 'asset_id'
! ERREUR : ImportError: cannot import name 'get_diagnostic_stream' from 'dal'
```

`_e01`/`_e02` référencent une API imaginaire (`InMemorySource(asset_id=..., data=df)`, `DALConfig(asset_id=..., timeframe=..., sources=[...])`, `get_diagnostic_stream(config)` en fonction libre) qui ne correspond à aucune version réelle du code. Réécrire selon l'API actuelle :

```python
from dal import DAL, DALConfig
from dal.adapters.in_memory import InMemorySource

src = InMemorySource(source_id="test", data={"BTC-USD": df})
dal_instance = DAL(DALConfig(), sources=(src,))
handoff = dal_instance.get_diagnostic_stream(
    asset_id="BTC-USD",
    source_preference=["test"],
    start="2024-01-02",
    end="2024-01-04",
    calendar="CRYPTO_247",
)
```

**Gate** : `python scripts/adversarial_dal_check_p3.py --run-network` → 65/65 PASS (0 ERROR).

### 3.4 — Tâches secondaires (non bloquantes, à faire si le temps le permet)

- `CONTRIBUTING.md` absent — créer en miroir de celui de `mif-dqf`
- `scripts/verify_install.py` → renommer `scripts/test_install.py` (arborescence cible `HALO_MIGRATION.md` §4)
- `CHANGELOG.md` — remplacer le placeholder `2026-05-XX` par la date réelle de tag
- Vérifier que `scripts/` ne contient plus que `dev.sh`, `test_install.py` (renommé), `adversarial_dal_check_p3.py`, `final_commit.sh` — déjà quasi conforme à la cible

---

## 4. Ce que l'agent NE DOIT PAS faire

- Toucher `dal/adapters/yahoo.py`, `kraken.py`, `dukascopy.py` sur les points mypy déjà fermés (§2)
- Ajouter une valeur par défaut à `DAL.__init__(sources=...)` — D1=B est fermé pour cette version
- Modifier `decisions_immuables` dans `anamnese_state.yaml`
- Merger vers `main` sans gate `tests_passing` + `mypy` + `ruff` tous verts

---

## 5. Gate de publication final (à exécuter avant tag v0.1.0)

```bash
./scripts/dev.sh check                                    # Ruff + Mypy + Pytest — 0 erreur
python scripts/verify_install.py                          # 7/7 PASS (après §3.1)
python scripts/adversarial_dal_check_p3.py                # 65/65 PASS (après §3.2)
python scripts/adversarial_dal_check_p3.py --run-network  # 65/65 PASS (après §3.3)
.venv/bin/python -m coverage run -m pytest tests/ -q
.venv/bin/python -m coverage report -m                     # ≥ 80% global, confirmé 93% actuellement
```

Si les 5 commandes passent sans erreur → prêt pour `git tag v0.1.0` + `uv build` + `uv publish --index testpypi` (TestPyPI d'abord, comme pour mif-dqf).

---

## 6. SESSION_REPORT attendu de l'agent en fin de sprint

Format standard (`project_instructions.md`) :
```
SESSION_REPORT
--- SESSION_REPORT ---
Session ID       : DAL-PUB-001
Fichiers modifiés: dal/__init__.py, scripts/verify_install.py, scripts/adversarial_dal_check_p3.py, [...]
Tests            : N passing / N failing
Coverage         : N%
Mypy             : 0 errors (confirmé, ne pas retoucher yahoo/kraken/dukascopy)
Violations       : 0
Prochaine action : tag v0.1.0 + publication TestPyPI
Intervention Andrei requise : OUI — validation avant tag + avant uv publish (production)
```
