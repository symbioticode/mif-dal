# KB-DAL-001 — Initialisation de la gestion documentaire HALO pour MIF-DAL

**Type :** Document fondateur  
**Auteur :** Orchestratrice (Claude Sonnet 4.6) + Andrei  
**Date :** 2026-04-27  
**Statut :** Validé — référence permanente pour toutes les sessions DAL  
**Audience :** Toute instance Claude intervenant sur MIF-DAL, présente ou future

---

## 1. Pourquoi HALO existe

DQF a été développé en 3 mois par plusieurs instances Claude Sonnet 4.5
sans mémoire persistante, coordonnées par un humain qui servait de boucle
de feedback manuelle.

Le résultat est solide — 224/224 tests, publié sur PyPI. Mais le coût
de coordination a été disproportionné. L'analyse rétrospective (KB-001 à
KB-010) a révélé trois causes structurelles :

**Perte de contexte entre sessions.**
Chaque instance repartait de zéro. Les décisions architecturales validées,
les patterns d'échec documentés, les conventions établies — tout devait être
réinjecté manuellement à chaque session. Coût estimé : 200-300 tokens de
contexte perdu par session, et plus grave, des décisions parfois contredites
sans le savoir.

**Ambiguïté des rôles.**
L'humain alternait entre gouvernance (décisions architecturales), validation
(relecture de code), et boucle de feedback (copier-coller d'erreurs). Sans
séparation claire, chaque session mélangeait les trois. Les sessions longues
dégradaient la qualité des décisions.

**Absence de mémoire des patterns d'échec.**
Les bugs les plus coûteux de DQF (tuples dans YAML, ordre detect_calendar,
dépendances optionnelles sans skipif) ont été découverts tardivement et
n'étaient pas disponibles pour les instances suivantes au démarrage.

HALO est la réponse minimale à ces trois problèmes.

---

## 2. Philosophie

**HALO est de l'infrastructure, pas du contenu.**

La distinction est critique. HALO ne génère pas de code DAL, ne prend pas
de décisions architecturales, n'interprète pas les résultats de tests.
Il fait une seule chose : s'assurer que chaque instance qui arrive sur le
projet sait exactement où en est le projet, quelles décisions sont actives,
et quelles règles s'appliquent — en moins de 30 secondes de lecture.

**Principe de transparence maximale.**

HALO ne doit jamais interférer avec le développement de DAL. Si une instance
passe plus de 5 minutes à gérer HALO dans une session, quelque chose est mal
configuré. Les routines de début et de fin de session doivent être aussi
invisibles que possible — elles servent à ceux qui viendront après, pas à
celui qui est là maintenant.

**Sobriété délibérée.**

Quatre fichiers. Pas un système. Pas un dashboard. Pas une base de données.
Quatre fichiers YAML et Markdown, versionnés dans Git, lisibles en texte brut.
La complexité est l'ennemi de la continuité — si HALO devient difficile à
maintenir, il sera abandonné, et on reviendra au problème initial.

---

## 3. Structure des fichiers

```
halo/
├── anamnese_state.yaml     ← État vivant du projet
├── protocols.yaml          ← Règles de collaboration (quasi-permanent)
├── profil_stable.yaml      ← Patterns confirmés sur Andrei
└── project_instructions.md ← Instructions d'entrée pour toute instance
```

### 3.1 anamnese_state.yaml — le fichier central

C'est le seul fichier qui change fréquemment. Il contient :

- **etat_courant** : phase active, module, prochaine action, bloquants
- **decisions_immuables** : décisions architecturales validées par Andrei,
  non-modifiables par Claude Code
- **dette_technique** : placeholders ouverts avec version cible explicite
- **patterns_interdits** : bugs documentés transformés en règles préventives
- **interface_proposee** : specs en attente de validation
- **metriques_session** : mis à jour par Claude Code après chaque session

Qui met à jour quoi :

| Section | Orchestratrice | Claude Code | Andrei |
|---|---|---|---|
| etat_courant | ✓ | ✓ (metriques_session) | — |
| decisions_immuables | ✓ après validation | ✗ jamais | Valide |
| dette_technique | ✓ | ✗ | Valide |
| interface_proposee | ✓ | ✗ | Valide |
| metriques_session | — | ✓ | — |

### 3.2 protocols.yaml — quasi-permanent

Contient les rôles, le cycle de travail, les mindsets IA, les gates de
validation automatiques, et les critères d'intervention humaine.

Change seulement si le projet change de nature (nouveau module majeur,
nouveau collaborateur, changement de stack). Pas à chaque sprint.

### 3.3 profil_stable.yaml — connaissance accumulée sur Andrei

Contient les patterns de travail et de communication d'Andrei, confirmés
sur 3+ sessions distinctes. Permet aux instances de s'adapter sans
que l'humain ait à répéter ses préférences.

Entre sur une entrée quand le pattern a été observé 3 fois.
N'entre jamais par déduction ou extrapolation.

### 3.4 project_instructions.md — point d'entrée de session

Fichier court (< 60 lignes) lu en premier par toute instance.
Définit l'ordre de lecture des 4 fichiers, le contexte projet en 5 phrases,
ce qui est interdit sans instruction, et le format du rapport de fin de session.

---

## 4. Objectifs visés pour MIF-DAL

### 4.1 Objectif principal : continuité entre sessions

Chaque instance qui démarre une session DAL doit savoir en < 2 minutes :
- Où en est l'implémentation
- Quelles décisions ne sont pas à rediscuter
- Quels fichiers toucher et dans quel ordre
- Ce qui a échoué avant et pourquoi

Si cet objectif est atteint, le temps de "mise en chauffe" par session
passe de ~20 minutes (DQF) à < 5 minutes (DAL cible).

### 4.2 Objectif secondaire : libérer Andrei de la boucle de feedback

Dans DQF, Andrei copiait les erreurs du terminal, les collait dans Claude,
attendait un diagnostic, copiait la correction, l'appliquait, relançait.
Chaque cycle : 5-10 minutes pour une erreur de type, un import manquant,
une indentation incorrecte.

Avec Claude Code comme agent d'exécution lisant HALO, ces cycles sont
absorbés localement. Andrei n'intervient que sur les gates définis dans
protocols.yaml — décisions architecturales, merge vers main, pivots.

### 4.3 Objectif tertiaire : traçabilité des décisions

Chaque décision architecturale de DAL aura un ID (D-DAL-NNN), une raison
documentée, et une source. Quand DQF v1.3 devra absorber les statuts
PENDING et UNCERTIFIED, l'instance qui fera ce travail comprendra en 30
secondes pourquoi ces statuts n'existent pas encore et dans quelles
conditions ils doivent apparaître.

---

## 5. Routines de session

### 5.1 Routine de début (< 5 minutes, toute instance)

```
1. Lire project_instructions.md          [30 secondes]
2. Lire anamnese_state.yaml             [2 minutes]
3. Lire sections pertinentes protocols.yaml selon rôle [1 minute]
4. Si contexte manquant : signaler à Andrei avant toute action
5. Confirmer : "HALO chargé. Phase active : [X]. Prochaine action : [Y]."
```

La confirmation en fin de bootstrap sert deux buts : elle force une
lecture réelle (pas un survol), et elle donne à Andrei un signal
immédiat si l'état est incohérent.

### 5.2 Routine de fin (< 10 minutes, Claude Code)

```
1. Vérifier que tous les gates pre_commit passent
2. Mettre à jour metriques_session dans anamnese_state.yaml
3. Produire le SESSION_REPORT (format défini dans project_instructions.md)
4. Si intervention Andrei requise : formuler la question précisément
5. Committer anamnese_state.yaml mis à jour
```

La routine de fin est la contribution de l'instance aux sessions futures.
Si elle est bâclée, la continuité est dégradée pour la session suivante.

### 5.3 Routine de fin (Orchestratrice, après session de gouvernance)

```
1. Documenter les décisions prises dans anamnese_state.yaml (decisions_immuables)
2. Mettre à jour etat_courant.prochaine_action
3. Si nouvelle spec validée : l'ajouter à interface_proposee avec statut VALIDÉE
4. Committer et pusher
```

---

## 6. Scénario illustré — Sprint DAL-001

**Contexte :** Première session de code DAL. L'interface DALHandoff a été
validée par Andrei lors de la session de gouvernance du 2026-04-27.

---

**Étape 1 — Bootstrap (Claude Code, 3 minutes)**

Claude Code ouvre la session. Lit les 4 fichiers HALO.

Confirmation produite :

```
HALO chargé.
Phase active : DAL Phase 0 → Phase 1 (première implémentation).
Décision active : DALHandoff comme unique point de passage DAL → DQF (D-DAL-002).
Prochaine action : Créer dal/core/handoff.py avec dataclass DALHandoff.
Gate : 0 pytest failed + 0 mypy errors avant commit.
Intervention Andrei requise : NON (spec validée).
```

Andrei lit la confirmation. Si elle est correcte, répond "OK". Si non,
corrige avant que l'agent touche au code.

---

**Étape 2 — Implémentation (Claude Code, durée variable)**

Claude Code crée `dal/core/handoff.py` selon la spec de anamnese_state.yaml.
Il écrit les tests correspondants. Il fait tourner pytest et mypy.

Si mypy retourne une erreur de type sur `list[dict]` vs `List[Dict[str, Any]]` :
Claude Code corrige sans intervention. Pas de message à Andrei.

Si pytest retourne 3 tests en échec sur `assembly_hash` pour des raisons
qui révèlent une ambiguïté dans la spec (ex : SHA-256 du stream avant ou
après normalisation des types pandas ?) : Claude Code s'arrête. La question
dépasse une correction locale. Intervention Andrei requise.

---

**Étape 3 — Rapport de fin (Claude Code)**

```
SESSION_REPORT
---
Session ID     : DAL-001
Fichiers créés : dal/core/handoff.py, tests/test_handoff.py
Fichiers modifiés : anamnese_state.yaml (metriques_session)
Tests          : 18 passing / 0 failing
Coverage       : 94% (dal/core/handoff.py)
mypy           : 0 errors
Violations protocols : 0
Prochaine action : Implémenter dal/core/assembler.py (source Yahoo + Kraken)
Intervention Andrei requise : NON
```

---

**Étape 4 — Mise à jour Orchestratrice (si nécessaire)**

Si Claude Code a signalé une ambiguïté sur assembly_hash, l'Orchestratrice
présente 2 options à Andrei avec la recommandation. Andrei tranche.
L'Orchestratrice met à jour anamnese_state.yaml (decisions_immuables, D-DAL-005).
Claude Code reprend.

Total overhead HALO pour ce sprint : ~15 minutes.
Total overhead HALO pour DQF équivalent : ~2 heures (estimation rétrospective KB-004).

---

## 7. Critères de succès de HALO pour MIF-DAL

### 7.1 Critères quantitatifs

| Critère | Cible | Mesure |
|---|---|---|
| Temps de bootstrap par session | < 5 minutes | Estimé par Claude Code en SESSION_REPORT |
| Violations protocols par session | 0 | metriques_session.violations_protocols |
| Décisions contredites entre sessions | 0 | Revue Orchestratrice en fin de sprint |
| Gates pré-commit échoués au commit | 0 | Log Git |
| Durée totale développement DAL | < 3 semaines | vs 3 mois DQF |

### 7.2 Critères qualitatifs

**Transparence.** Si une instance passe plus de 5 minutes sur HALO dans
une session, HALO a un problème — pas l'instance. Un fichier trop long,
une structure trop complexe, des décisions ambiguës : diagnostiquer et
simplifier.

**Non-interférence.** Le développement de DAL prime sur la maintenance
de HALO. Si un choix doit être fait entre documenter HALO correctement
et avancer sur DAL, on avance sur DAL. La routine de fin suffit.

**Cohérence architecturale.** À la fin du développement de DAL,
les décisions dans anamnese_state.yaml doivent correspondre exactement
au code produit. Pas de divergence entre la spec documentée et
l'implémentation réelle.

### 7.3 Critère de survie

**HALO survit si et seulement si il est plus simple de le maintenir
que de ne pas le maintenir.**

Si à n'importe quel point du développement de DAL, Andrei estime que
HALO coûte plus qu'il ne rapporte, il est simplifié ou abandonné.
Ce n'est pas un échec — c'est le critère d'arrêt correct pour un
outil d'infrastructure.

---

## 8. Ce que HALO ne fait pas

Pour être explicite sur les limites :

- **HALO ne génère pas de code.** Il donne du contexte aux agents qui génèrent.
- **HALO ne prend pas de décisions.** Il conserve celles qui ont été prises.
- **HALO ne remplace pas la gouvernance.** Andrei valide toujours les décisions
  architecturales. HALO réduit le coût de cette validation en la rendant plus
  informée.
- **HALO n'est pas ANAMNÈSE.** HALO est la sous-couche minimale et opérationnelle.
  ANAMNÈSE est le protocole cognitif complet dont HALO implémente le minimum viable.
  La distinction compte : HALO peut invalider ANAMNÈSE par l'observation empirique.

---

## 9. Évolution prévue

**v1.0 (DAL Phase 0-1) :** Les 4 fichiers actuels. Routines manuelles.

**v1.1 (DAL Phase 2) :** Si les routines de session montrent des patterns
répétitifs, les automatiser dans un `justfile` ou un script `halo_bootstrap.py`.
Pas avant — pas de solution en avance d'un problème observé.

**v2.0 (post-DAL) :** Si MIF Core démarre avec une équipe plus large,
envisager un état HALO en base de données légère (SQLite). Pas maintenant.

---

*Ce document est la référence permanente pour comprendre pourquoi HALO
existe et comment l'utiliser. Il ne devrait pas avoir besoin d'être
modifié avant la fin du développement de DAL v1.0.*
