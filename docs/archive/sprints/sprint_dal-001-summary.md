## Résumé de session — À destination de l'instance MIF

**Période couverte** : Session du 2026-05-06  
**Sprints exécutés** : DAL-001 → DAL-006  
**État à la clôture** : 119/119 tests, 100% coverage sur `dal/dal.py`

---

## État cumulé des sprints

| Sprint | Module | Tests | Statut |
|--------|--------|-------|--------|
| DAL-001 | `DALHandoff` (15 champs, frozen=True) | 23 | ✓ |
| DAL-002 | Exceptions (`DALError`, `DALConfigError`, `DALVersionError`, `DALHandoffError`) | 51 | ✓ |
| DAL-003 | `DALConfig` (cache_dir, request_timeout) | 58 | ✓ |
| DAL-004 | `pipeline.assemble_handoff()` — S3+S4+S5 + version gate | 73 | ✓ |
| DAL-005 | `sources/` — S1+S2+AQI + Protocol Source + InMemorySource | 104 | ✓ |
| DAL-006 | Classe `DAL` publique — `get_certified_stream()` / `get_diagnostic_stream()` | 119 | ✓ |

---

## Décisions prises en session — à intégrer dans l'anamnèse

| ID | Décision | Statut |
|----|----------|--------|
| D-DAL-005 | DAL passe avec flag sur DQF WARNING (Option B) | FERMÉ |
| D-DAL-006 | `assembly_hash` calculé sur raw data avant toute transformation | FERMÉ |
| D-DAL-007 | Un actif par appel — caller assemble la paire (Option A) | FERMÉ |
| AM-003 | DAL retourne toujours un actif en USD, jamais un ratio — résolu par D-DAL-007 | RÉSOLU |
| DAL-006/calendar | `calendar` required dans `get_certified_stream()` ET `get_diagnostic_stream()` — Option (a) retenue | FERMÉ |

---

## Points bloquants soulevés par Claude Code — avec leur résolution

**1 — DQF n'a pas de statut FAIL**  
Découverte : DQF retourne `CERTIFIED | WARNING | VOID` uniquement. La spec §S4 mentionnait `FAIL` et `VOID` séparément.  
Résolution : mapping corrigé dans DAL-004.
```python
CERTIFIED → DALHandoff(dqf_status="PASS")
WARNING   → DALHandoff(dqf_status="WARNING")
VOID      → raise DALHandoffError(reason="DQF_VOID")
_         → raise DALHandoffError(reason="DQF_UNEXPECTED_STATUS")
```
`DALHandoffError.reason="DQF_FAIL"` retiré — terme fictif supprimé.

**2 — `DALHandoff` : `frozen=True` et `source_manifest` en tuple**  
Détecté dans DAL-001 : l'implémentation initiale avait 6 champs, non-frozen, `source_manifest` en list.  
Résolution : réécrit conforme à la spec (15 champs, `frozen=True`, `tuple[dict]`).

**3 — Responsabilité du hash dans `FetchResult`**  
Confusion possible entre hash par source (dans `FetchResult`) et `assembly_hash` (dans `DALHandoff`).  
Résolution : `FetchResult.hash` calculé par l'adaptateur sur les octets bruts de sa source. `assembly_hash` calculé par S3 dans le pipeline sur les données effectivement utilisées.

**4 — Distinction retry vs fallback dans l'AQI**  
Retry = même source, échec transitoire (−0.05/tentative). Fallback = changement de source (−0.20). Implémentés comme deux boucles distinctes dans `resolve_and_fetch()`.

**5 — Floor AQI manquant**  
La formule pouvait produire des valeurs négatives sous pénalités cumulées.  
Résolution : `aqi = max(0.0, 100.0 * (1.0 - total_penalties))` implémenté.

**6 — `calendar` en mode DIAGNOSTIC**  
Invariant `DALHandoff.calendar` non-vide vs auto-détection DQF.  
Vérification empirique : `report.calendar` retourne `'UNKNOWN'` si omis (pas de vraie auto-détection). `dqf.detect_calendar()` prend un `asset_symbol` string, pas un DataFrame.  
Résolution : Option (a) — `calendar` required dans les deux méthodes. Spec §7 à corriger.

---

## Corrections à apporter à la spec DAL_SPECIFICATION_v1.0

| Section | Correction requise |
|---------|-------------------|
| §S4 | Supprimer `FAIL`. Ajouter mapping `case _` (DQF_UNEXPECTED_STATUS) |
| §5 DALHandoff | Ajouter `frozen=True`. Changer `source_manifest: list[dict]` → `tuple[dict]` |
| §7 exemple `get_diagnostic_stream` | Ajouter `calendar` comme paramètre required. Supprimer note "Calendar auto-detection permitted" pour ce paramètre |
| §5 AM-003 | Reformuler : supprimer "ratio stream". DAL retourne toujours un actif USD. Marquer RÉSOLU |

---

## Dettes techniques créées en session

| ID | Description | Cible | Condition |
|----|-------------|-------|-----------|
| TD-008 | AQI gravities (0.20/0.10/0.05/0.30) calibrées à l'intuition | v0.2.0 | Après 3+ assets en production avec historique de fetch réel |
| TD-009 | `get_diagnostic_stream` : calendar devrait être dérivé de `DQFReport.detected_calendar` quand disponible | v0.2.0 | Si DQF expose un jour une vraie auto-détection depuis DataFrame |

---

## Ce qui reste à faire (prochains sprints)

**Dans mif-dal :**
- DAL-007+ : adaptateurs réels `YahooAdapter`, `KrakenAdapter`
- DAL-008 : couche cache locale (`DALConfig.cache_dir`)
- Corrections spec v1.0 (voir tableau ci-dessus)
- Mise à jour `anamnese_state.yaml` : métriques session (119 tests), TD-008/TD-009, D-DAL-005/006/007 FERMÉS si pas encore fait

**Hors mif-dal — non commencé :**
- `mif-core` : spécification à écrire (dépend de mif-dal stable)
- `test_strategy_fn_is_not_constant()` : premier test à écrire dans mif-core (AM-001)
- Signal oracle synthétique générique pour mif-core (AM-004)
- Protocole post-NON pour QS-MÉTIS (AM-005) — non bloquant pour DAL, bloquant pour QAAF Studio