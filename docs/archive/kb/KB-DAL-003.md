# KB-DAL-003 — Environnement NixOS pour mif-dal
**Tag** : `MIF-KB-DAL-003`  
**Période** : 2026-05-07 → 2026-05-08  
**D-SIG** : 72 / GOOD · STABLE  
**Applicabilité** : toute instance Claude/Open Code intervenant sur mif-dal sous NixOS

---

## Signal pivot

Ce document documente le problème d'environnement NixOS récurrent sur mif-dal,
sa cause racine, et la procédure de résolution définitive.

**Pattern observé** : `ModuleNotFoundError: No module named 'dqf'` malgré
`mif-dqf` déclaré dans `pyproject.toml`. Apparaît lors de tout `pytest` lancé
sans préfixe `.venv/bin/python`.

---

## 1. Architecture de l'environnement mif-dal

Il existe **deux environnements distincts** dans le repo, et ils ne sont pas interchangeables.

```
mif-dal/
├── flake.nix          ← Environnement A : nix develop (Python 3.12, nix store)
├── shell.nix          ← Environnement B : nix-shell alternatif (Python 3.12, QAAF Studio)
└── .venv/             ← Environnement C : venv Python 3.11, géré par uv ← CORRECT POUR MIF-DAL
```

### Environnement A — `nix develop` (flake.nix)
- Python 3.12.13 depuis le nix store
- `mif-dqf` disponible via `uv add mif-dqf` dans `.venv`
- **Problème** : si on lance `pytest` directement, il utilise Python 3.12 du store
  sans le `.venv` → `dqf` introuvable
- **Usage correct** : `.venv/bin/python -m pytest` toujours

### Environnement B — `nix-shell` (shell.nix de QAAF Studio)
- Python 3.12, packages pip dans `.pip_packages/`
- Conçu pour QAAF Studio (TA-Lib, krakenex, ccxt, dukascopy)
- **Ne pas utiliser pour mif-dal** — `mif-dqf` n'y est pas installé

### Environnement C — `.venv` (Python 3.11, géré par uv)
- Python 3.11.14
- `mif-dqf==1.2.0.post1` installé via `uv add mif-dqf`
- `yfinance>=1.3.0,<2.0.0` installé
- `pytest`, `pytest-cov` disponibles
- **C'est l'environnement correct pour tous les tests mif-dal**

---

## 2. Commandes correctes

```bash
# Toujours préfixer avec .venv/bin/python pour mif-dal :

# Tests standard (sans réseau) :
.venv/bin/python -m pytest tests/ -v

# Tests avec réseau (Kraken, Yahoo réels) :
.venv/bin/python -m pytest tests/ --run-network -v

# Tests adaptateurs seulement :
.venv/bin/python -m pytest tests/test_kraken_adapter.py tests/test_yahoo_adapter.py tests/test_dukascopy_adapter.py -v

# Script adversarial :
.venv/bin/python adversarial_dal_check.py

# Validate state :
.venv/bin/python scripts/validate_dal_state.py
```

---

## 3. Résolution `mif-dqf` non disponible

**Symptôme** :
```
ModuleNotFoundError: No module named 'dqf'
```

**Diagnostic** :
```bash
# Vérifier quelle version Python est active :
which python  # → /nix/store/... = mauvais | .venv/bin/python = correct

# Vérifier si dqf est dans le venv :
.venv/bin/python -c "import dqf; print(dqf.__version__)"
```

**Fix** :
```bash
# Depuis la racine du repo, dans nix-shell ou nix develop :
uv add mif-dqf

# Vérification :
.venv/bin/python -c "from dqf import DQFReport; print('OK')"
```

---

## 4. Résolution `dukascopy-node` non disponible

**Symptôme** :
```
dukascopy-node: command not found
```
ou test `test_fetch_real_btc_1d` qui passe en SKIPPED avec `--run-network`.

**Cause** : `npm install -g` échoue sur le nix store (read-only).

**Fix** :
```bash
# Installation dans ~/.npm-global (contourne le nix store read-only) :
bash setup_dukascopy_mif.sh

# Vérification :
dukascopy-node --version
# → dukascopy-node/x.x.x linux x64 node/v20.x.x

# Si dukascopy-node toujours absent après setup :
export NPM_GLOBAL="$HOME/.npm-global"
export PATH="$NPM_GLOBAL/bin:$PATH"
npm install --prefix "$NPM_GLOBAL" -g dukascopy-node
```

**Persistance dans flake.nix** — ajouter dans `shellHook` :
```nix
shellHook = ''
  # ... hooks existants ...

  # dukascopy-node via npm global local (contourne nix store read-only)
  export NPM_GLOBAL="$HOME/.npm-global"
  mkdir -p "$NPM_GLOBAL"
  npm config set prefix "$NPM_GLOBAL" 2>/dev/null || true
  export PATH="$NPM_GLOBAL/bin:$PATH"

  if ! command -v dukascopy-node &>/dev/null; then
    echo "⚠ dukascopy-node absent — exécuter : bash setup_dukascopy_mif.sh"
  else
    echo "✓ dukascopy-node: $(dukascopy-node --version 2>&1 | head -1)"
  fi
'';
```

---

## 5. Tests réseau — comportement attendu

```bash
# CI normal (sans --run-network) :
.venv/bin/python -m pytest tests/
# → X passed, 5 skipped ← CORRECT, pas d'erreur

# Avec réseau mais sans dukascopy-node :
.venv/bin/python -m pytest tests/ --run-network
# → X passed, 1 skipped (test_fetch_real_btc_1d) ← CORRECT

# Avec réseau ET dukascopy-node installé :
.venv/bin/python -m pytest tests/ --run-network
# → X passed, 0 skipped ← IDÉAL
```

Les tests `@pytest.mark.network` sont : `test_fetch_real_btc_usd` (Kraken),
`test_fetch_real_paxg_usd` (Kraken), `test_fetch_real_btc_1d` (Dukascopy),
`test_fetch_real_btc_usd` (Yahoo), `test_fetch_real_paxg_usd` (Yahoo).

---

## 6. Warning yfinance à ignorer (non-bloquant)

```
Pandas4Warning: Timestamp.utcnow is deprecated and will be removed in a future version.
```

Ce warning vient de `yfinance/scrapers/history.py:169` — interne à yfinance, pas dans
notre code. Non-bloquant. Tracé en TD-010, correction dans mif-dal v0.2.0 quand
yfinance le résoudra en amont.

Supprimer le warning des logs si gênant :
```bash
.venv/bin/python -m pytest tests/ -W ignore::FutureWarning
```

---

## 7. Checklist de vérification d'environnement (à lancer en début de session)

```bash
# 1. Bon Python :
.venv/bin/python --version
# Attendu : Python 3.11.14

# 2. mif-dqf disponible :
.venv/bin/python -c "from dqf import DQFReport; print('dqf OK')"

# 3. yfinance correct :
.venv/bin/python -c "import yfinance; print(yfinance.__version__)"
# Attendu : 1.3.x

# 4. dukascopy-node (optionnel) :
dukascopy-node --version 2>/dev/null || echo "dukascopy-node absent (tests réseau skippés)"

# 5. Tests OK :
.venv/bin/python -m pytest tests/ -q
# Attendu : X passed, 5 skipped, 0 failed

# 6. Adversarial :
.venv/bin/python adversarial_dal_check.py
# Attendu : 41/41 PASS

# 7. Validate state :
.venv/bin/python scripts/validate_dal_state.py
# Attendu : RESULT: GO - All checks passed
```

---

## 8. Anti-patterns à ne jamais reproduire

```
DUAL_ENV_CONFUSION : lancer pytest sans .venv/bin/python → dqf absent
NIX_STORE_GLOBAL : npm install -g sans prefix → permission denied
SHELL_NIX_QAAF : utiliser shell.nix QAAF Studio pour mif-dal → mauvaises dépendances
PYTEST_NU : pytest sans .venv/bin/python → Python 3.12 sans venv
```

---

## Métriques session (à la clôture Phase 2)

| Métrique | Valeur |
|----------|--------|
| Tests passing (sans réseau) | 169/169 |
| Tests skippés (réseau) | 5 |
| Coverage global | 61% |
| Coverage adaptateurs | 77-94% |
| Coverage core | 33-50% (gap Phase 3) |
| Adversarial | 41/41 |
| validate_dal_state.py | GO/GO/GO/GO/GO |

---

*KB-DAL-003 · MIF Ecosystem · 2026-05-08*  
*Auteurs : dravitch, Claude Sonnet 4.6*  
*Source : sessions Phase 2 DAL + résolution KB-DAL-002 (environnement Phase 1)*
