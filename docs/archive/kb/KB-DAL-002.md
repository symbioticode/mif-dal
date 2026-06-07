## Fichier 10 — `KB-DAL-002-howto.md` (complément à KB-DAL-001)

```markdown
# KB-DAL-002 — Guide pratique : déploiement MIF-DAL sur Proxmox/NixOS

**Type :** Guide opérationnel  
**Complément de :** KB-DAL-001.md  
**Date :** 2026-04-28  
**Audience :** Toute instance ou opérateur déployant MIF-DAL pour la première fois

---

## Prérequis

- VM Proxmox avec NixOS 25.11 installé (ISO minimal)
- `configuration.nix` v1.1 appliqué (`nixos-rebuild switch`)
- Clé SSH dans `users.users.mifdal.openssh.authorizedKeys.keys`
- Compte GitHub avec accès au repo `mif-dal`
- `ANTHROPIC_API_KEY` disponible en local (jamais dans git)

---

## Étape 1 — Appliquer la configuration NixOS (5 min)

```bash
# Sur la VM, en tant que root
cp configuration.nix /etc/nixos/configuration.nix
nixos-rebuild switch

# Vérifier les services critiques
systemctl status postgresql
systemctl status ollama
systemctl status nginx
```

**Ce que ça crée automatiquement :**
- `/var/lib/mif-dal/{halo,dal,logs,cache}` (via `systemd.tmpfiles`)
- Base PostgreSQL `mifdal` avec extension TimescaleDB
- Service `ollama` (CPU mode, port 11434)
- Utilisateur `mifdal` avec accès Docker et wheel

---

## Étape 2 — Cloner le repo et créer l'environnement (3 min)

```bash
# Se connecter en tant que mifdal
ssh mifdal@<ip-vm>

# Cloner
cd ~
git clone git@github.com:<org>/mif-dal.git
cd mif-dal

# Créer l'environnement Python avec uv
uv venv .venv
uv sync --extra dev

# Vérifier
uv run python -c "import dal; print('DAL importable')"
```

Section "numpy" à ajouter :
  numpy<2.0.0 obligatoire sur CPU sans X86_V2 (ex: PowerEdge T100)
  pyproject.toml : numpy>=1.24.0,<2.0.0 et pandas>=2.0.0,<3.0.0
  Pas de flake.nix nécessaire — uv suffit.

Section "Étape 5 — Gate pré-commit" à corriger :
  23 tests collectés (pas 0) — DAL-001 livré

---

## Étape 3 — Configurer les secrets (.env)

```bash
# Créer .env (jamais dans git, dans .gitignore)
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
DAL_DB_URL=postgresql://mifdal:mifdal@127.0.0.1:5432/mifdal
DAL_DB_NAME=mifdal
DQF_VERSION=1.2.0
EOF

chmod 600 .env
```

Le `.envrc` (si `direnv` est utilisé) charge `.env` automatiquement :

```bash
# .envrc
dotenv
```

---

## Étape 4 — Bootstrap HALO (2 min)

```bash
# Lecture de l'état courant
./scripts/dev.sh bootstrap
```

Sortie attendue :

```
=== HALO Bootstrap ===
Phase active     : Phase 0 — Initialisation infrastructure
Module courant   : HALO bootstrap + structure projet
Prochaine action : [...]
Bloquants        : aucun
[OK]   HALO bootstrap complet
```

Si la sortie est différente → lire `halo/anamnese_state.yaml` complet avant de continuer.

---

## Étape 5 — Lancer le gate pré-commit (1 min)

```bash
./scripts/dev.sh check
```

Sortie attendue (Phase 0, avant DAL-001) :

```
=== Gate pré-commit ===
1/3 Format...   [OK]
2/3 Types...    [OK]
3/3 Tests...    [OK] 0 tests collected (dal/ vide en Phase 0)
[OK]   Gate pré-commit : tout vert ✓
```

---

## Étape 6 — Démarrer Claude Code (premier sprint)

```bash
# S'assurer qu'Ollama tourne (pour backup local)
curl -s http://localhost:11434 && echo "Ollama OK"

# Lancer Claude Code dans le répertoire projet
cd ~/mif-dal
claude
```

Dans Claude Code, la première instruction est :

```
Lis halo/project_instructions.md et produis la confirmation de bootstrap.
```

Claude Code doit répondre avec le bloc `HALO chargé.` avant toute action de code.

---

## Structure complète des fichiers

```
mif-dal/
├── halo/                               ← infrastructure session (anamnese, protocols, profil, instructions)
│   ├── anamnese_state.yaml             ← état vivant (mis à jour par Orchestratrice + Claude Code)
│   ├── protocols.yaml                  ← règles quasi-permanentes
│   ├── profil_stable.yaml              ← patterns Andrei confirmés
│   └── project_instructions.md         ← lu en premier par toute instance
│
├── docs/
│   ├── kb/
│   │   ├── KB-DAL-001.md               ← document fondateur HALO
│   │   └── KB-DAL-002.md               ← guide opérationnel
│   └── decisions/                      ← historique décisions (futur)
│
├── dal/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── handoff.py                  ← Sprint DAL-001 (D-DAL-002)
│   │   ├── assembler.py                ← Sprint DAL-002 (dépend handoff.py testé)
│   │   └── utils.py                    ← helpers partagés (hash, datetime)
│   │
│   ├── interfaces/
│   │   └── __init__.py                 ← interfaces abstraites (Phase 1 : BaseSource)
│   │
│   └── adapters/
│       └── __init__.py                 ← adaptateurs concrets (Phase 2)
│
├── tests/
│   ├── conftest.py                     ← fixtures partagées
│   ├── test_handoff.py                 ← Sprint DAL-001 (18 tests)
│   └── test_assembler.py               ← Sprint DAL-002
│
├── scripts/
│   ├── dev.sh                          ← check | test | types | fmt | bootstrap | report
│   └── halo_bootstrap.py               ← (v1.1, optionnel — automatise la routine HALO)
│
├── pyproject.toml
├── README.md
├── uv.lock
│
├── .env                                ← secrets locaux (jamais git)
├── .envrc                              ← direnv (charge .env)
├── .gitignore
└── deploy.sh

```

---

## Ordre des sprints

| Sprint | Module | Gate | Dépendances |
|--------|--------|------|-------------|
| DAL-000 | Structure + HALO | structure présente | aucune |
| DAL-001 | `dal/core/handoff.py` | 18 tests verts, mypy clean | DAL-000 |
| DAL-002 | `dal/core/assembler.py` | tests verts, atomique | DAL-001 |
| DAL-003 | `dal/interfaces/base_source.py` | ABC définie | DAL-002 |
| DAL-004 | `dal/adapters/yahoo.py` | 1 source réelle testée | DAL-003 |
| DAL-005 | C1 activation + source_manifest multi-sources | C1 verte | DAL-004 |

La règle est stricte : **un sprint ne démarre que si le sprint précédent a
son gate vert.** Pas d'exception. C'est le mindset M2 (Exemple Minimal
d'Abord) appliqué au niveau des sprints.

---

## Commandes de diagnostic rapide

```bash
# Santé PostgreSQL + TimescaleDB
psql -U mifdal -d mifdal -c "SELECT extname, extversion FROM pg_extension;"

# Santé Ollama
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# Santé tests DAL
./scripts/dev.sh test

# État HALO courant
./scripts/dev.sh bootstrap

# Générer SESSION_REPORT squelette
./scripts/dev.sh report
```

---

## Ce qui est géré par Gemma 4 local

Gemma 4 peut prendre en charge (sans intervention Claude Code) :

- Validation syntaxique des fichiers YAML HALO après modification
- Résumés de SESSION_REPORT pour archivage
- Vérification que `.gitignore` couvre `.env`, `__pycache__`, `.venv`
- Génération de commentaires de documentation routiniers

Gemma 4 ne doit **pas** :
- Modifier `decisions_immuables` dans HALO
- Proposer des changements d'architecture DAL
- Valider des gates de code (ce rôle appartient à Claude Code + pytest)

---

*KB-DAL-002 — Guide pratique — Avril 2026*  
*Révision prévue après DAL-002 (assembler.py testé)*
