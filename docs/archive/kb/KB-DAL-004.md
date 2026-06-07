# KB-DAL-004 — Procédure d'initialisation/réinitialisation de l'environnement mif-dal
**Tag** : `MIF-KB-DAL-004`  
**Période** : 2026-05-09 → 2026-05-09  
**D-SIG** : 73 / GOOD · STABLE  
**Applicabilité** : toute instance intervenant sur mif-dal sous NixOS

---

## 1. Contexte

Cette procédure documente la méthode définitive pour configurer un environnement de développement fonctionnel pour mif-dal sous NixOS, en intégrant :
- Python 3.11 avec les dépendances requises (numpy, pandas, etc.)
- Dukascopy-node via npm global local (contournant la limitation du nix store en lecture seule)
- Les tests réseau optionnels pour Dukascopy

---

## 2. Prérequis

- NixOS installé et fonctionnel
- Accès au référentiel mif-dal cloné
- Connexion internet fonctionnelle

---

## 3. Procédure d'initialisation complète

### Étape 1 : Nettoyage éventuel de l'environnement existant

```bash
# Depuis la racine du référentiel mif-dal
exit                    # Si vous êtes dans un nix-shell
rm -rf .venv            # Supprime l'environnement virtuel existant
nix-store --gc          # Nettoyage du nix store (optionnel mais recommandé)
nix-collect-garbage     # Nettoyage supplémentaire (optionnel)
```

### Étape 2 : Lancement de l'environnement Nix avec prise en charge de Dukascopy

```bash
nix-shell
```

Ce commandement :
- Crée un environnement virtuel Python 3.11 dans `.venv/`
- Installe les dépendances Python de base (numpy, pandas, scipy, matplotlib, etc.)
- Installe spécifiquement yfinance>=1.3.0,<2.0.0 et mif-dqf
- Configure dukascopy-node via npm global local dans `$HOME/.npm-global`
- Vérifie que tous les composants sont fonctionnels

### Étape 3 : Vérification de l'environnement

À l'initialisation réussie, vous devriez voir :

```
📊 Dépendances :
   ✓ numpy: 2.4.4
   ✓ pandas: 3.0.2
   ✓ yfinance: 1.3.0
   ✓ mif-dqf: 1.2.0.post1
   ✓ node:           v20.19.6
   ✓ dukascopy-node: 1.46.4

✅ Environnement prêt — Python: Python 3.11.14
```

### Étape 4 : Vérification manuelle des composants (optionnel)

```bash
# Vérification Python et dépendances
.venv/bin/python -c "import numpy; print('NumPy:', numpy.__version__)"
.venv/bin/python -c "import pandas; print('Pandas:', pandas.__version__)"
.venv/bin/python -c "import dqf; print('MIF-DQF:', dqf.__version__)"

# Vérification de Dukascopy-node
dukascopy-node --help   # Doit retourner l'aide (exit 0)
# NE PAS utiliser --version car il retourne un code d'erreur 1 même quand installé (bug upstream)
```

---

## 4. Utilisation de l'environnement

Une fois l'environnement initialisé :

### Tests standards (sans réseau)

```bash
.venv/bin/python -m pytest tests/ -v
```

### Tests avec réseau (pour Kraken, Yahoo, Dukascopy réels)

```bash
.venv/bin/python -m pytest tests/ --run-network -v
```

### Tests spécifiques aux adaptateurs

```bash
.venv/bin/python -m pytest tests/test_dukascopy_adapter.py tests/test_kraken_adapter.py tests/test_yahoo_adapter.py -v
```

### Test spécifique Dukascopy avec réseau réel

```bash
.venv/bin/python -m pytest tests/test_dukascopy_adapter.py::test_fetch_real_btc_1d -v --run-network
```

### Scripts de validation

```bash
.venv/bin/python adversarial_dal_check.py
.venv/bin/python scripts/validate_dal_state.py
```

---

## 5. Résolution des problèmes connus

### Problème : `ImportError: libstdc++.so.6: cannot open shared object file`

**Cause** : Version incompatible de numpy installée dans le virtuel environment
**Solution** :
```bash
# Réinstaller numpy avec une version compatible
.venv/bin/python -m pip install --force-reinstall numpy==1.26.4
```

### Problème : `dukascopy-node: command not found`

**Cause** : L'installation npm global n'a pas été exécutée ou le PATH n'est pas configuré
**Solution** :
```bash
# Depuis nix-shell
bash dukascopy/setup_dukascopy_nixos_fixed.sh
```

### Problème : Les tests Dukascopy retournent systématiquement 'failed'

**Cause** : L'adaptateur Dukascopy utilise `--version` pour vérifier la disponibilité, mais dukascopy-node retourne toujours un code d'erreur 1 pour `--version` (bug upstream)
**Solution** : 
La correction a été appliquée dans le fichier `dal/adapters/dukascopy.py` à la ligne 278 :
```python
# Avant (incorrect)
["npx", "dukascopy-node", "--version"],

# Après (correct)
["npx", "dukascopy-node", "--help"],
```

---

## 6. Bonnes pratiques

1. **Toujours utiliser `.venv/bin/python`** pour exécuter Python dans ce référentiel
2. **Ne jamais utiliser `npm install -g` directement** - toujours passer par le script fourni ou la configuration nix
3. **Pour vérifier dukascopy-node, utilisez toujours `--help` et jamais `--version`**
4. **L'environnement nix-shell recrée automatiquement le virtuel environment si nécessaire**
5. **Les tests réseau sont skippés par défaut** - utiliser `--run-network` pour les activer

---

## 7. Validation de l'environnement

Après initialization, l'état suivant devrait être observé :
- 169 tests passant (sans réseau)
- 8 tests skippés (tests réseau sans --run-network)
- 0 tests failing
- Adversarial check : 41/41 PASS
- État de validation : GO/GO/GO/GO/GO

---
*KB-DAL-004 · MIF Ecosystem · 2026-05-09*  
*Auteur : Nemotron 3 Super Free (OpenCode Zen)*  
*Source : résolution environnement Phase 2 + intégration Dukascopy-node*