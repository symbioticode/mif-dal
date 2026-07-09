# MIF-DAL — Instructions d'entrée de session

**Lu en premier. Toujours. Par toute instance.**

## Contexte projet (5 phrases)

MIF-DAL est la couche d'abstraction de données du Metric Integrity Framework.
Son rôle : assembler des streams multi-sources, les soumettre à DQF pour
certification, et exposer un résultat atomique `(DataFrame, DQFReport)`.
DQF v1.2.0.post1 est stable sur PyPI (224/224 tests). DAL est en Phase 0→1.
Le projet tourne sur NixOS 25.11 / Proxmox, Nemotron 3 Super Free comme agent d'exécution,
l'Orchestratrice (Claude Sonnet 4.x) comme gouvernance, GitHub comme source de vérité.

## Ordre de lecture obligatoire

```
1. project_instructions.md     ← ce fichier        [vous êtes ici]
2. anamnese_state.yaml          ← état courant      [2 min]
3. protocols.yaml               ← rôles et règles   [1 min]
4. profil_stable.yaml           ← préférences Andrei [30 sec]
```

## Confirmation de bootstrap obligatoire

```
HALO chargé.
Phase active     : [etat_courant.phase]
Module courant   : [etat_courant.module]
Prochaine action : [etat_courant.prochaine_action]
Bloquants        : [etat_courant.bloquants]
Gate actif       : [gate de la phase courante]
Modèle utilisé   : Nemotron 3 Super Free (OpenCode Zen)
Intervention Andrei requise : OUI/NON
```

## Interdit sans instruction explicite d'Andrei

- Modifier `decisions_immuables` dans `anamnese_state.yaml`
- Modifier `protocols.yaml` ou `profil_stable.yaml`
- Créer des fichiers dans `dal/` sans gate `architecture_validee`
- Merger vers `main` sans gate `tests_passing`
- Contredire une décision D-DAL-NNN sans escalader à l'Orchestratrice

## Format SESSION_REPORT

```
SESSION_REPORT
--- SESSION_REPORT ---
Session ID       : DAL-NNN
Fichiers créés   : [liste]
Fichiers modifiés: [liste]
Tests            : N passing / N failing
Coverage         : N%
Mypy             : N errors
Violations       : 0
Prochaine action : [phrase courte]
Intervention Andrei requise : OUI/NON
```

## Règle d'or

Si HALO prend plus de 5 minutes → signaler à l'Orchestratrice.
