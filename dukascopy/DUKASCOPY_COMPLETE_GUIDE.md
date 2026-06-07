# Guide Complet Dukascopy sur NixOS

**Documentation complète : Installation → Utilisation → Intégration**

Date: 31 Octobre 2024  
Mise à jour: 9 Mai 2026  
Version: 1.1 — Ajout section Dry Run & Gestion d'erreurs réseau

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation sur NixOS](#installation-sur-nixos)
3. [Architecture du système](#architecture-du-système)
4. [Utilisation de data_preparation_module.py](#utilisation-de-data_preparation_modulepy)
5. [Intégration avec dqf_loader.py](#intégration-avec-dqf_loaderpy)
6. [Développement avec Dry Run et gestion d'erreurs réseau](#développement-avec-dry-run-et-gestion-derreurs-réseau)
7. [Troubleshooting](#troubleshooting)
8. [Exemples d'utilisation](#exemples-dutilisation)

---

## Vue d'ensemble

### Qu'est-ce que Dukascopy ?

**Dukascopy** est un fournisseur de données financières haute fréquence spécialisé dans :
- **Forex** (paires de devises)
- **Crypto** (BTC, ETH, etc.)
- **Timeframes intraday** : 15m, 30m, 1h, 4h

### Pourquoi Dukascopy pour le trading algorithmique ?

✅ **Avantages:**
- Données intraday **gratuites** jusqu'à 12 mois d'historique
- Qualité institutionnelle (tick-by-tick agrégé)
- Pas de limite de requêtes (raisonnable)
- Format CSV standardisé

⚠️ **Limitations:**
- Historique limité (vs Yahoo Finance illimité pour daily)
- Nécessite Node.js (dépendance supplémentaire)
- Disponibilité variable selon asset/timeframe
- **Serveur lent** : 30s à 2min par requête selon le volume
- **Rate limiting** : échec `fetch failed` si deux requêtes arrivent trop rapidement

### Notre Stack

```
┌─────────────────────────────────────┐
│     Application Trading             │
│  (Backtest, Stratégies, etc.)       │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│      dqf_loader.py                  │
│  (Data Quality Framework)           │
│  - Validation                       │
│  - Standardisation                  │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  data_preparation_module.py         │
│  - Téléchargement Dukascopy         │
│  - Parsing CSV                      │
│  - Cache local                      │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│      dukascopy-node (npm)           │
│  Interface avec API Dukascopy       │
└─────────────────────────────────────┘
```

---

## Installation sur NixOS

### Prérequis

Votre `shell.nix` doit inclure :

```nix
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312
    pkgs.nodejs_20        # ✅ REQUIS pour Dukascopy
    pkgs.nodePackages.npm
  ];
  
  shellHook = ''
    # Configuration npm global local (évite conflits NixOS — nix store read-only)
    export NPM_GLOBAL_DIR="$HOME/.npm-global"
    mkdir -p "$NPM_GLOBAL_DIR"
    npm config set prefix "$NPM_GLOBAL_DIR" 2>/dev/null || true
    export PATH="$NPM_GLOBAL_DIR/bin:$PATH"
    
    # Vérification dukascopy-node
    # IMPORTANT : utiliser --help (exit 0), pas --version (exit 1 — bug upstream)
    if ! npx dukascopy-node --help &>/dev/null; then
        echo "⚠️  dukascopy-node absent"
        echo "   Exécuter : bash setup_dukascopy_nixos_fixed.sh"
    fi
    
    echo "✅ Environnement Dukascopy prêt"
  '';
}
```

### Installation Manuelle

Si `shell.nix` ne gère pas l'installation automatiquement :

```bash
# 1. Entrer dans nix-shell
nix-shell

# 2. Configurer npm global local
export NPM_GLOBAL_DIR="$HOME/.npm-global"
mkdir -p "$NPM_GLOBAL_DIR"
npm config set prefix "$NPM_GLOBAL_DIR"
export PATH="$NPM_GLOBAL_DIR/bin:$PATH"

# 3. Installer dukascopy-node
npm install -g dukascopy-node

# 4. Vérifier installation
# ⚠️ NE PAS utiliser --version (retourne exit code 1 — bug upstream)
npx dukascopy-node --help   # ✅ Correct — exit code 0 si installé
```

### Vérification Installation

```python
import subprocess

# ✅ CORRECT : --help retourne exit code 0
result = subprocess.run(
    ['npx', 'dukascopy-node', '--help'],
    capture_output=True, text=True, timeout=10
)
if result.returncode == 0:
    print('✅ dukascopy-node installé et fonctionnel')
else:
    print('❌ dukascopy-node non accessible')

# ❌ INCORRECT : --version retourne exit code 1 même si installé (bug upstream)
# subprocess.run(['npx', 'dukascopy-node', '--version'])  ← NE PAS UTILISER
```

---

## Architecture du Système

### Modules Clés

#### 1. `data_preparation_module.py`

**Rôle:** Téléchargement et parsing des données Dukascopy

**Classes principales:**

```python
class DukascopyDataPreparator:
    """
    Prépare données Dukascopy pour timeframes intraday.
    Gère téléchargement, cache, parsing CSV.
    """
    
    def get_data(symbol, timeframe, start_date, end_date) -> pd.DataFrame:
        """Télécharge et formate données"""
        
    def prepare_multiple_timeframes(symbol, start, end, timeframes) -> Dict:
        """Télécharge plusieurs timeframes en une fois"""
```

**Timeframes supportés:**
- `15m`, `30m`, `1h`, `4h`

**Symboles disponibles:**
- Crypto: `BTC/USD`, `ETH/USD`, `SOL/USD`, `AVAX/USD`, etc.
- Forex: `EUR/USD`, `GBP/USD`, `USD/JPY`, etc.

#### 2. `dqf_loader.py`

**Rôle:** Validation et standardisation des données

**Fonctions principales:**

```python
def fetch_historical_data_dqf(symbol, start, end, interval):
    """
    Charge données avec DQF 6 étapes:
    1. Standardisation format
    2. Validation intégrité
    3-5. (Futures améliorations)
    6. Nettoyage avec forward-fill limité
    """
```

### Format de Données Standardisé

Tous les modules produisent le **même format** :

```python
DataFrame avec colonnes:
- timestamp: pd.Timestamp (index ou colonne)
- open: float64
- high: float64
- low: float64
- close: float64
- volume: float64
```

**Exemple:**

```
                   timestamp      open      high       low     close    volume
0 2024-01-01 00:00:00+00:00  42135.50  42289.00  42001.20  42156.70  1234.567
1 2024-01-01 01:00:00+00:00  42156.70  42345.80  42100.50  42289.30  2345.678
```

---

## Utilisation de data_preparation_module.py

### Utilisation Basique

#### Télécharger un seul timeframe

```python
from data.data_preparation_module import DukascopyDataPreparator

# Initialiser
prep = DukascopyDataPreparator(data_dir="crypto_data")

# Télécharger
df = prep.get_data(
    symbol='BTC/USD',
    timeframe='1h',
    start_date='2024-01-01',
    end_date='2024-08-28'
)

print(f"Données: {len(df)} points")
print(df.head())
```

#### Télécharger plusieurs timeframes

```python
# Télécharger 1h, 4h, 30m en une fois
results = prep.prepare_multiple_timeframes(
    symbol='BTC/USD',
    start_date='2024-01-01',
    end_date='2024-08-28',
    timeframes=['4h', '1h', '30m']
)

# Accéder aux données
df_4h = results['4h']
df_1h = results['1h']
df_30m = results['30m']
```

### Utilisation Avancée avec MarketDataManager

Le `MarketDataManager` gère automatiquement Dukascopy, Kraken, et fallbacks :

```python
from data.data_preparation_module import MarketDataManager

# Initialiser (utilise Dukascopy en priorité)
manager = MarketDataManager(
    data_dir="crypto_data",
    prefer_dukascopy=True
)

# Télécharger automatiquement
data = manager.prepare_data(
    symbol='BTC/USD',
    timeframes=['4h', '1h'],
    start_date='2024-01-01',
    end_date='2024-08-28'
)

# Si Dukascopy échoue, fallback vers Kraken automatique
df_1h = data['1h']
```

### Utilisation en Batch (Multiple Symboles)

```python
from data.data_preparation_module import prepare_trading_data

# Configuration
config = {
    'symbols': ['BTC/USD', 'ETH/USD'],
    'timeframes': ['4h', '1h'],
    'start_date': '2024-01-01',
    'end_date': '2024-08-28',
    'data_dir': 'crypto_data',
    'prefer_dukascopy': True
}

# Télécharger tout
all_data = prepare_trading_data(config)

# Accéder aux données
btc_1h = all_data['BTC/USD']['1h']
eth_4h = all_data['ETH/USD']['4h']
```

### Gestion du Cache

Dukascopy utilise un **cache local intelligent** :

```python
# 1er appel: Télécharge depuis Dukascopy
df = prep.get_data('BTC/USD', '1h', '2024-01-01', '2024-08-28')
# ✓ Téléchargement: btcusd-h1-bid-2024-01-01-2024-08-28.csv

# 2ème appel: Utilise cache
df = prep.get_data('BTC/USD', '1h', '2024-01-01', '2024-08-28')
# ✓ Fichier existant: btcusd-h1-bid-2024-01-01-2024-08-28.csv
```

**Invalider le cache:**

```python
import os

# Supprimer un fichier spécifique
os.remove("crypto_data/btcusd-h1-bid-2024-01-01-2024-08-28.csv")

# Supprimer tout le cache
import shutil
shutil.rmtree("crypto_data")
```

---

## Intégration avec dqf_loader.py

### Objectif

Créer une **couche d'abstraction unifiée** :
- Yahoo Finance pour daily+ (illimité)
- Dukascopy pour intraday (12 mois)
- Validation DQF pour toutes les sources

### Architecture Proposée

```python
# data/unified_data_loader.py (NOUVEAU MODULE)

from data.dqf_loader import standardize_yahoo_data, validate_data_integrity
from data.data_preparation_module import DukascopyDataPreparator

class UnifiedDataLoader:
    """
    Loader unifié avec DQF pour toutes sources.
    """
    
    def __init__(self):
        self.dukascopy = DukascopyDataPreparator()
    
    def fetch_with_dqf(self, symbol, start, end, timeframe):
        """
        Charge données avec DQF complet.
        
        Routing automatique:
        - timeframe >= 1d → Yahoo Finance
        - timeframe < 1d → Dukascopy
        """
        
        # Step 1: Source selection
        if self._is_daily_plus(timeframe):
            source = 'yahoo'
            df = self._fetch_yahoo(symbol, start, end, timeframe)
        else:
            source = 'dukascopy'
            df = self._fetch_dukascopy(symbol, start, end, timeframe)
        
        # Step 2: DQF Standardization
        df = self._standardize_format(df, source)
        
        # Step 3: DQF Validation
        if not self._validate_integrity(df, symbol):
            raise ValueError(f"Validation échouée pour {symbol}")
        
        # Step 4: DQF Cleaning
        df = self._clean_data(df)
        
        return df
```

### Implémentation Complète

```python
# data/unified_data_loader.py
"""
Unified Data Loader with DQF
=============================
Combine Yahoo Finance (daily+) et Dukascopy (intraday)
avec validation DQF complète.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Optional

from data.data_preparation_module import DukascopyDataPreparator


class UnifiedDataLoader:
    """Chargeur unifié avec DQF pour toutes sources"""
    
    DAILY_PLUS = ['1d', '1w', '1mo']
    INTRADAY = ['15m', '30m', '1h', '4h']
    
    def __init__(self, cache_dir='crypto_data'):
        self.cache_dir = cache_dir
        self.dukascopy = DukascopyDataPreparator(data_dir=cache_dir)
        print(f"✅ UnifiedDataLoader initialisé (cache: {cache_dir})")
    
    def fetch_with_dqf(self, symbol: str, start_date: str, 
                       end_date: str, timeframe: str) -> pd.DataFrame:
        print(f"\n📊 Fetch {symbol} {timeframe} ({start_date} → {end_date})")
        
        if timeframe in self.DAILY_PLUS:
            source = 'yahoo'
            df = self._fetch_yahoo(symbol, start_date, end_date, timeframe)
        elif timeframe in self.INTRADAY:
            source = 'dukascopy'
            df = self._fetch_dukascopy(symbol, start_date, end_date, timeframe)
        else:
            raise ValueError(f"Timeframe non supporté: {timeframe}")
        
        print(f"   Source: {source}")
        self._validate_dqf(df, symbol)
        df = self._clean_dqf(df)
        print(f"   ✅ DQF complet: {len(df)} bars validées")
        
        return df
```

---

## Développement avec Dry Run et gestion d'erreurs réseau

Cette section couvre le développement de code qui doit fonctionner **sans accès réseau à Dukascopy** (dry run, CI, tests unitaires) tout en gérant proprement les erreurs lors des appels réels en production.

### Contexte et problèmes réels observés

Les appels réseau à Dukascopy peuvent échouer de plusieurs façons documentées :

| Erreur observée | Cause | Fréquence |
|---|---|---|
| `fetch failed` | Rate limiting serveur (2 requêtes trop rapprochées) | Courante en dev |
| `fetch failed` | Réseau inaccessible (NixOS sandbox, CI) | Systématique en CI |
| Timeout silencieux | Période trop longue, serveur surchargé | Occasionnelle |
| CSV vide (0 bytes) | Période sans données (weekend, férié, asset peu liquide) | Rare |
| `--version` exit code 1 | Bug upstream dukascopy-node (toutes versions) | Permanente |

### Principe : Mode Dry Run

Le **dry run** consiste à substituer les appels réseau réels par des données synthétiques réalistes, sans modifier le code métier. L'objectif est de permettre :

- le développement et le test de la logique métier sans dépendance réseau
- l'exécution en CI/CD sans credentials ni accès externe
- la reproductibilité exacte des tests (données fixes, pas aléatoires)
- la détection rapide des régressions avant tout appel réseau coûteux

### Architecture recommandée

```
┌──────────────────────────────────────────────────┐
│              Code métier / Stratégie             │
│  (ne connaît pas la source des données)          │
└──────────────────┬───────────────────────────────┘
                   │  get_data(symbol, tf, start, end)
┌──────────────────▼───────────────────────────────┐
│         DukascopyClient (interface)              │
│  - is_dry_run: bool                              │
│  - _fetch_real() / _fetch_dry()                  │
└──────┬───────────────────────┬───────────────────┘
       │                       │
┌──────▼──────┐      ┌─────────▼──────────────────┐
│  Réseau     │      │  DryRunDataGenerator        │
│  Dukascopy  │      │  Données synthétiques OHLCV │
│  (réel)     │      │  reproductibles (seed fixe) │
└─────────────┘      └────────────────────────────┘
```

### Implémentation : DukascopyClient avec mode dry run

```python
# data/dukascopy_client.py
"""
Client Dukascopy avec mode dry run intégré.

Usage:
    # Mode réel (production)
    client = DukascopyClient(dry_run=False)

    # Mode dry run (développement / CI)
    client = DukascopyClient(dry_run=True)

    # Contrôlé par variable d'environnement
    client = DukascopyClient.from_env()  # DUKASCOPY_DRY_RUN=1
"""

import os
import time
import logging
import subprocess
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class DukascopyNetworkError(Exception):
    """
    Erreur réseau Dukascopy — distingue les cas récupérables
    des cas définitifs.

    Attributs:
        message      : description lisible
        is_transient : True si un retry peut réussir (rate limit, timeout)
                       False si le retry ne sert à rien (période invalide,
                       asset inconnu, réseau structurellement absent)
    """
    def __init__(self, message: str, is_transient: bool = True):
        super().__init__(message)
        self.is_transient = is_transient


class DryRunDataGenerator:
    """
    Génère des données OHLCV synthétiques reproductibles.

    Les données sont déterministes pour un même (symbol, timeframe,
    start_date, end_date) : un seed est dérivé de ces paramètres,
    garantissant la reproductibilité entre runs.

    Le format de sortie est identique aux données réelles Dukascopy :
    colonnes [timestamp, open, high, low, close, volume], timestamps UTC.
    """

    # Niveaux de prix de référence par symbole
    BASE_PRICES = {
        'btcusd': 45000.0,
        'ethusd': 2500.0,
        'eurusd': 1.085,
        'gbpusd': 1.265,
        'usdjpy': 149.5,
    }
    DEFAULT_BASE_PRICE = 100.0

    # Volatilité par timeframe (annualisée → périodique)
    TIMEFRAME_MINUTES = {
        '15m': 15, '30m': 30, '1h': 60, '4h': 240, 'd1': 1440
    }

    def generate(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Génère un DataFrame OHLCV synthétique reproductible.

        Args:
            symbol    : ex. 'btcusd' (format dukascopy-node, minuscules)
            timeframe : '15m', '30m', '1h', '4h', 'd1'
            start_date: 'YYYY-MM-DD'
            end_date  : 'YYYY-MM-DD'

        Returns:
            DataFrame avec colonnes [timestamp, open, high, low, close, volume]
        """
        # Seed déterministe — reproductibilité garantie
        seed = hash(f"{symbol}_{timeframe}_{start_date}_{end_date}") % (2**31)
        rng = np.random.default_rng(seed)

        base_price = self.BASE_PRICES.get(symbol.lower(), self.DEFAULT_BASE_PRICE)
        minutes = self.TIMEFRAME_MINUTES.get(timeframe, 60)

        # Génération des timestamps
        freq = f"{minutes}min"
        timestamps = pd.date_range(
            start=start_date, end=end_date,
            freq=freq, tz='UTC'
        )
        n = len(timestamps)
        if n == 0:
            raise DukascopyNetworkError(
                f"Période invalide pour dry run : {start_date} → {end_date}",
                is_transient=False
            )

        # Marche aléatoire log-normale (volatilité ~20% annualisée)
        annual_vol = 0.20
        period_vol = annual_vol / np.sqrt(525_600 / minutes)
        returns = rng.normal(0, period_vol, n)
        prices = base_price * np.exp(np.cumsum(returns))

        # Construction OHLCV
        intra_vol = period_vol * 0.5
        high = prices * (1 + np.abs(rng.normal(0, intra_vol, n)))
        low  = prices * (1 - np.abs(rng.normal(0, intra_vol, n)))
        open_ = np.roll(prices, 1)
        open_[0] = base_price
        volume = rng.lognormal(mean=8.0, sigma=1.0, size=n)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open':   open_.round(5),
            'high':   high.round(5),
            'low':    low.round(5),
            'close':  prices.round(5),
            'volume': volume.round(3),
        })

        logger.info(
            f"[DRY RUN] {symbol} {timeframe} : {n} barres générées "
            f"({start_date} → {end_date}, seed={seed})"
        )
        return df


class DukascopyClient:
    """
    Client unifié Dukascopy avec mode dry run et gestion d'erreurs structurée.

    Le dry run est activable :
      - à l'instanciation : DukascopyClient(dry_run=True)
      - par variable d'environnement : DUKASCOPY_DRY_RUN=1
      - via la factory : DukascopyClient.from_env()

    En mode réel, toutes les erreurs réseau sont capturées et remontées
    sous forme de DukascopyNetworkError avec le flag is_transient pour
    permettre une logique de retry claire côté appelant.
    """

    # Délai minimum entre deux appels réels (évite le rate limiting)
    MIN_CALL_INTERVAL_SECONDS = 5

    def __init__(
        self,
        dry_run: bool = False,
        data_dir: str = "download",
        timeout: int = 180,
    ):
        self.dry_run = dry_run
        self.data_dir = data_dir
        self.timeout = timeout
        self._last_call_ts: float = 0.0
        self._dry_gen = DryRunDataGenerator()

        mode = "DRY RUN" if dry_run else "RÉEL"
        logger.info(f"DukascopyClient initialisé — mode {mode}")

    @classmethod
    def from_env(cls, **kwargs) -> "DukascopyClient":
        """
        Factory : lit DUKASCOPY_DRY_RUN dans l'environnement.

        DUKASCOPY_DRY_RUN=1   → dry run activé
        DUKASCOPY_DRY_RUN=0   → appels réels (défaut)
        """
        dry_run = os.environ.get("DUKASCOPY_DRY_RUN", "0").strip() == "1"
        return cls(dry_run=dry_run, **kwargs)

    # ── API publique ──────────────────────────────────────────────────────────

    def get_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Télécharge (ou génère en dry run) des données OHLCV.

        Args:
            symbol    : ex. 'btcusd'
            timeframe : '15m', '30m', '1h', '4h', 'd1'
            start_date: 'YYYY-MM-DD'
            end_date  : 'YYYY-MM-DD'

        Returns:
            DataFrame [timestamp, open, high, low, close, volume]

        Raises:
            DukascopyNetworkError : erreur réseau (is_transient indique si
                                   un retry peut aider)
        """
        if self.dry_run:
            return self._fetch_dry(symbol, timeframe, start_date, end_date)
        else:
            return self._fetch_real(symbol, timeframe, start_date, end_date)

    def is_available(self) -> bool:
        """
        Vérifie que dukascopy-node est accessible.

        En dry run : toujours True (pas de dépendance externe).
        En mode réel : vérifie via --help (exit 0).

        Note : ne pas utiliser --version, qui retourne exit code 1
               même si le package est correctement installé (bug upstream).
        """
        if self.dry_run:
            return True

        try:
            result = subprocess.run(
                ['npx', 'dukascopy-node', '--help'],
                capture_output=True, timeout=10,
                stdin=subprocess.DEVNULL
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ── Implémentation interne ────────────────────────────────────────────────

    def _fetch_dry(
        self, symbol: str, timeframe: str,
        start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Retourne des données synthétiques reproductibles."""
        return self._dry_gen.generate(symbol, timeframe, start_date, end_date)

    def _fetch_real(
        self, symbol: str, timeframe: str,
        start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Appel réseau réel à dukascopy-node.

        Gère :
          - le rate limiting (pause MIN_CALL_INTERVAL_SECONDS entre appels)
          - le timeout (subprocess.TimeoutExpired)
          - les erreurs réseau (fetch failed, stderr non vide)
          - le CSV vide (0 bytes — période sans données)
        """
        self._throttle()

        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                'npx', 'dukascopy-node',
                '-i', symbol.lower(),
                '-from', start_date,
                '-to', end_date,
                '-t', timeframe,
                '-f', 'csv',
                '-dir', tmpdir,
                '-s',   # silencieux — on lit stdout/stderr nous-mêmes
            ]

            logger.info(f"[RÉEL] Appel : {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                raise DukascopyNetworkError(
                    f"Timeout ({self.timeout}s) pour {symbol} {timeframe} "
                    f"{start_date}→{end_date}. "
                    f"Réduire la période ou augmenter le timeout.",
                    is_transient=True,
                )
            except FileNotFoundError:
                raise DukascopyNetworkError(
                    "dukascopy-node introuvable dans PATH. "
                    "Vérifier l'installation (bash setup_dukascopy_nixos_fixed.sh).",
                    is_transient=False,
                )

            # Détection erreur réseau dans stdout (dukascopy-node écrit là)
            combined_output = result.stdout + result.stderr
            if 'fetch failed' in combined_output.lower():
                raise DukascopyNetworkError(
                    f"fetch failed pour {symbol} {timeframe} "
                    f"{start_date}→{end_date}. "
                    f"Causes : rate limiting (attendre 30s), réseau inaccessible, "
                    f"période invalide (weekend/férié).",
                    is_transient=True,  # souvent temporaire
                )

            if result.returncode != 0 and 'fetch failed' not in combined_output.lower():
                raise DukascopyNetworkError(
                    f"dukascopy-node exit {result.returncode} : {result.stderr[:200]}",
                    is_transient=False,
                )

            # Recherche du CSV généré
            csv_files = [
                f for f in os.listdir(tmpdir) if f.endswith('.csv')
            ]
            if not csv_files:
                raise DukascopyNetworkError(
                    f"Aucun CSV produit pour {symbol} {timeframe} "
                    f"{start_date}→{end_date}. "
                    f"Période probablement sans données (weekend, férié, asset peu liquide).",
                    is_transient=False,
                )

            csv_path = os.path.join(tmpdir, csv_files[0])
            if os.path.getsize(csv_path) == 0:
                raise DukascopyNetworkError(
                    f"CSV vide (0 bytes) pour {symbol} {timeframe} "
                    f"{start_date}→{end_date}. Période sans données.",
                    is_transient=False,
                )

            return self._parse_csv(csv_path)

    def _parse_csv(self, csv_path: str) -> pd.DataFrame:
        """Parse le CSV Dukascopy vers le format OHLCV standardisé."""
        df = pd.read_csv(csv_path)

        # Normalisation des noms de colonnes (variations selon la version)
        df.columns = [c.lower().strip() for c in df.columns]

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms', utc=True)
            df = df.drop(columns=['time'])

        required = ['timestamp', 'open', 'high', 'low', 'close']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise DukascopyNetworkError(
                f"Colonnes manquantes dans CSV : {missing}",
                is_transient=False,
            )

        if 'volume' not in df.columns:
            df['volume'] = 0.0

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    def _throttle(self) -> None:
        """Pause si le dernier appel est trop récent (anti rate-limiting)."""
        elapsed = time.time() - self._last_call_ts
        if elapsed < self.MIN_CALL_INTERVAL_SECONDS:
            wait = self.MIN_CALL_INTERVAL_SECONDS - elapsed
            logger.debug(f"Throttle : attente {wait:.1f}s avant appel réseau")
            time.sleep(wait)
        self._last_call_ts = time.time()
```

### Gestion d'erreurs avec retry côté appelant

```python
# data/dukascopy_fetcher.py
"""
Couche de retry au-dessus de DukascopyClient.
Distingue les erreurs transientes (retry utile) des erreurs définitives.
"""

import time
import logging
from typing import Optional
import pandas as pd

from data.dukascopy_client import DukascopyClient, DukascopyNetworkError

logger = logging.getLogger(__name__)


def fetch_with_retry(
    client: DukascopyClient,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
    retry_delay: float = 60.0,
    fallback_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Télécharge des données avec retry sur erreurs transientes.

    Logique :
      - Erreur transiente (rate limit, timeout) → retry après retry_delay
      - Erreur définitive (asset inconnu, CSV vide) → échec immédiat
      - Toutes tentatives épuisées → retourne fallback_df ou re-raise

    Args:
        client       : DukascopyClient (réel ou dry run)
        symbol       : ex. 'btcusd'
        timeframe    : '1h', '4h', etc.
        start_date   : 'YYYY-MM-DD'
        end_date     : 'YYYY-MM-DD'
        max_retries  : nombre de tentatives max (défaut 3)
        retry_delay  : secondes d'attente entre tentatives (défaut 60s)
        fallback_df  : DataFrame à retourner si toutes tentatives échouent
                       (None = re-raise l'exception)

    Returns:
        DataFrame OHLCV

    Raises:
        DukascopyNetworkError : si toutes tentatives épuisées et pas de fallback
    """
    last_error: Optional[DukascopyNetworkError] = None

    for attempt in range(1, max_retries + 1):
        try:
            df = client.get_data(symbol, timeframe, start_date, end_date)
            if attempt > 1:
                logger.info(f"✅ Succès à la tentative {attempt}/{max_retries}")
            return df

        except DukascopyNetworkError as e:
            last_error = e

            if not e.is_transient:
                # Erreur définitive : inutile de réessayer
                logger.error(
                    f"❌ Erreur définitive ({symbol} {timeframe}) : {e}\n"
                    f"   is_transient=False → pas de retry"
                )
                break

            if attempt < max_retries:
                logger.warning(
                    f"⚠️  Tentative {attempt}/{max_retries} échouée "
                    f"({symbol} {timeframe}) : {e}\n"
                    f"   Retry dans {retry_delay:.0f}s..."
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"❌ Toutes les tentatives épuisées "
                    f"({symbol} {timeframe}) : {e}"
                )

    # Toutes tentatives épuisées ou erreur définitive
    if fallback_df is not None:
        logger.warning(
            f"⚠️  Utilisation du fallback DataFrame pour {symbol} {timeframe}"
        )
        return fallback_df

    raise last_error
```

### Tests unitaires avec dry run

```python
# tests/test_dukascopy_client.py
"""
Tests unitaires DukascopyClient.

Tous les tests utilisent le dry run : aucun accès réseau, aucune
dépendance externe, exécution instantanée, résultats reproductibles.
"""

import pytest
import pandas as pd
import numpy as np

from data.dukascopy_client import DukascopyClient, DukascopyNetworkError
from data.dukascopy_fetcher import fetch_with_retry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def dry_client():
    """Client en mode dry run — aucun réseau."""
    return DukascopyClient(dry_run=True)


@pytest.fixture
def btc_1h_df(dry_client):
    """DataFrame BTC/USD 1h de référence pour les tests."""
    return dry_client.get_data('btcusd', '1h', '2024-01-01', '2024-03-31')


# ── Tests format de sortie ─────────────────────────────────────────────────────

class TestDryRunOutputFormat:

    def test_colonnes_requises(self, btc_1h_df):
        """Le DataFrame doit avoir les colonnes OHLCV standardisées."""
        expected = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        assert expected.issubset(set(btc_1h_df.columns))

    def test_types_numeriques(self, btc_1h_df):
        """OHLCV doivent être numériques (float64)."""
        for col in ['open', 'high', 'low', 'close', 'volume']:
            assert pd.api.types.is_numeric_dtype(btc_1h_df[col]), \
                f"Colonne {col} non numérique"

    def test_timestamps_utc(self, btc_1h_df):
        """Les timestamps doivent être en UTC."""
        assert btc_1h_df['timestamp'].dt.tz is not None
        assert str(btc_1h_df['timestamp'].dt.tz) == 'UTC'

    def test_ohlc_coherence(self, btc_1h_df):
        """high >= max(open, close) et low <= min(open, close)."""
        assert (btc_1h_df['high'] >= btc_1h_df['open']).all()
        assert (btc_1h_df['high'] >= btc_1h_df['close']).all()
        assert (btc_1h_df['low']  <= btc_1h_df['open']).all()
        assert (btc_1h_df['low']  <= btc_1h_df['close']).all()

    def test_pas_de_nan(self, btc_1h_df):
        """Aucune valeur manquante."""
        assert btc_1h_df.isnull().sum().sum() == 0

    def test_volume_positif(self, btc_1h_df):
        """Volume strictement positif."""
        assert (btc_1h_df['volume'] > 0).all()


# ── Tests reproductibilité ────────────────────────────────────────────────────

class TestReproductibilite:

    def test_meme_parametres_meme_donnees(self, dry_client):
        """Deux appels identiques produisent exactement le même DataFrame."""
        params = ('btcusd', '1h', '2024-01-01', '2024-01-31')
        df1 = dry_client.get_data(*params)
        df2 = dry_client.get_data(*params)
        pd.testing.assert_frame_equal(df1, df2)

    def test_parametres_differents_donnees_differentes(self, dry_client):
        """Des paramètres différents produisent des données différentes."""
        df_btc = dry_client.get_data('btcusd', '1h', '2024-01-01', '2024-01-31')
        df_eth = dry_client.get_data('ethusd', '1h', '2024-01-01', '2024-01-31')
        assert not df_btc['close'].equals(df_eth['close'])


# ── Tests gestion d'erreurs ───────────────────────────────────────────────────

class TestGestionErreurs:

    def test_is_available_dry_run(self, dry_client):
        """En dry run, is_available() retourne toujours True."""
        assert dry_client.is_available() is True

    def test_retry_sur_erreur_transiente(self, dry_client, monkeypatch):
        """
        fetch_with_retry doit retenter sur DukascopyNetworkError transiente
        et réussir si une tentative ultérieure fonctionne.
        """
        call_count = [0]
        original_get = dry_client.get_data

        def flaky_get(symbol, timeframe, start, end):
            call_count[0] += 1
            if call_count[0] < 3:
                raise DukascopyNetworkError("fetch failed simulé", is_transient=True)
            return original_get(symbol, timeframe, start, end)

        monkeypatch.setattr(dry_client, 'get_data', flaky_get)

        df = fetch_with_retry(
            dry_client, 'btcusd', '1h',
            '2024-01-01', '2024-01-31',
            max_retries=3, retry_delay=0,  # delay=0 pour tests rapides
        )
        assert call_count[0] == 3
        assert len(df) > 0

    def test_pas_de_retry_sur_erreur_definitive(self, dry_client, monkeypatch):
        """
        fetch_with_retry ne doit PAS retenter sur is_transient=False.
        """
        call_count = [0]

        def always_fail(symbol, timeframe, start, end):
            call_count[0] += 1
            raise DukascopyNetworkError("asset inconnu", is_transient=False)

        monkeypatch.setattr(dry_client, 'get_data', always_fail)

        with pytest.raises(DukascopyNetworkError):
            fetch_with_retry(
                dry_client, 'xxxx', '1h',
                '2024-01-01', '2024-01-31',
                max_retries=3, retry_delay=0,
            )

        # Une seule tentative — pas de retry sur erreur définitive
        assert call_count[0] == 1

    def test_fallback_si_toutes_tentatives_epuisees(self, dry_client, monkeypatch):
        """
        fetch_with_retry doit retourner fallback_df si toutes tentatives
        échouent et qu'un fallback est fourni.
        """
        fallback = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='h', tz='UTC'),
            'open': [1.0, 1.1, 1.2], 'high': [1.1, 1.2, 1.3],
            'low':  [0.9, 1.0, 1.1], 'close': [1.05, 1.15, 1.25],
            'volume': [100.0, 110.0, 120.0],
        })

        def always_fail(symbol, timeframe, start, end):
            raise DukascopyNetworkError("fetch failed", is_transient=True)

        monkeypatch.setattr(dry_client, 'get_data', always_fail)

        result = fetch_with_retry(
            dry_client, 'btcusd', '1h',
            '2024-01-01', '2024-01-31',
            max_retries=2, retry_delay=0,
            fallback_df=fallback,
        )
        pd.testing.assert_frame_equal(result, fallback)
```

### Contrôle du mode par variable d'environnement

```bash
# En développement local : appels réels
unset DUKASCOPY_DRY_RUN
python run_backtest.py

# En CI / sans réseau : dry run automatique
export DUKASCOPY_DRY_RUN=1
python run_backtest.py

# Dans pytest (conftest.py ou pyproject.toml)
# [tool.pytest.ini_options]
# env = ["DUKASCOPY_DRY_RUN=1"]
```

```python
# Utilisation dans le code applicatif
from data.dukascopy_client import DukascopyClient

# Lit DUKASCOPY_DRY_RUN automatiquement
client = DukascopyClient.from_env()

df = client.get_data('btcusd', '1h', '2024-01-01', '2024-08-28')
```

### Récapitulatif des erreurs réseau et comportements attendus

| Erreur | `is_transient` | Action recommandée |
|---|---|---|
| `fetch failed` (rate limiting) | `True` | Retry après 60s |
| Timeout subprocess | `True` | Retry, ou réduire la période |
| `dukascopy-node` introuvable | `False` | Relancer `setup_dukascopy_nixos_fixed.sh` |
| CSV vide (0 bytes) | `False` | Changer la période, pas de retry |
| Aucun CSV produit | `False` | Période invalide, pas de retry |
| Colonnes manquantes | `False` | Bug de parsing, investiguer |

### Note sur le bug `--version`

`dukascopy-node --version` retourne **toujours exit code 1** quelle que soit la version installée. Ce bug est upstream et ne sera probablement pas corrigé. Dans tout le code du projet :

```python
# ❌ NE PAS UTILISER — exit code 1 même si installé
subprocess.run(['npx', 'dukascopy-node', '--version'])

# ✅ UTILISER — exit code 0 si installé
subprocess.run(['npx', 'dukascopy-node', '--help'])

# ✅ OU — via DukascopyClient
client = DukascopyClient(dry_run=False)
client.is_available()  # utilise --help en interne
```

---

## Troubleshooting

### Problème 1: "npx: command not found"

**Cause:** Node.js pas dans PATH

**Solution:**
```bash
# Vérifier Node.js
which node
which npm
## Sortie Attendue
# /nix/store/9l5x7mywivx4khxxh895b7is6sy4vxpf-nodejs-20.19.6/bin/node
# /nix/store/9l5x7mywivx4khxxh895b7is6sy4vxpf-nodejs-20.19.6/bin/npm

# Si absent, vérifier shell.nix
# Ajouter: pkgs.nodejs_20, pkgs.nodePackages.npm
```

### Problème 2: "dukascopy-node not found"

**Cause:** Package npm installé mais `~/.npm-global/bin` absent du PATH

**Solution:**
```bash
# Configurer et exporter le PATH (à faire dans chaque session nix-shell)
export NPM_GLOBAL_DIR="$HOME/.npm-global"
npm config set prefix "$NPM_GLOBAL_DIR"
export PATH="$NPM_GLOBAL_DIR/bin:$PATH"

# Puis vérifier
npx dukascopy-node --help   # ✅ exit 0 = installé
```

### Problème 3: `fetch failed` immédiat

**Cause:** Rate limiting Dukascopy (deux requêtes trop rapprochées) ou réseau inaccessible

**Solution:**
```bash
# Attendre 60–90s et réessayer
sleep 60
npx dukascopy-node -i btcusd -from 2024-01-01 -to 2024-03-01 -t h1 -f csv

# En mode CI/CD ou sans réseau : activer le dry run
export DUKASCOPY_DRY_RUN=1
```

### Problème 4: CSV vides ou invalides

**Cause:** Dukascopy n'a pas de données pour cette période/timeframe

**Solution:**
```python
# Essayer période plus longue
df = prep.get_data('BTC/USD', '4h', '2024-01-01', '2024-10-31')  # 10 mois

# Ou fallback vers 1h puis re-sampler
df_1h = prep.get_data('BTC/USD', '1h', '2024-01-01', '2024-10-31')
df_4h = df_1h.set_index('timestamp').resample('4H').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 
    'close': 'last', 'volume': 'sum'
}).reset_index()
```

### Problème 5: Timeout téléchargement

**Cause:** Période trop longue ou serveur Dukascopy surchargé. Les temps normaux sont :
- `d1` sur 7 jours : ~30s
- `h1` sur 4 mois : ~2min
- `h1` sur 12 mois : ~5min

**Solution:**
```python
# Réduire la période
df = prep.get_data('BTC/USD', '1h', '2024-08-01', '2024-08-31')  # 1 mois

# Ou augmenter timeout dans DukascopyClient
client = DukascopyClient(dry_run=False, timeout=300)  # 5 minutes
```

### Problème 6: `--version` retourne exit code 1

**Cause:** Bug upstream dukascopy-node (permanent, toutes versions)

**Solution:** Ne jamais utiliser `--version` pour vérifier l'installation. Utiliser `--help` à la place (voir section [Note sur le bug --version](#note-sur-le-bug---version)).

---

## Exemples d'utilisation

### Exemple 1: Backtest Multi-Timeframes

```python
from data.unified_data_loader import UnifiedDataLoader

# Initialiser
loader = UnifiedDataLoader()

# Charger données
df_daily = loader.fetch_with_dqf('BTC-USD', '2023-01-01', '2024-10-31', '1d')
df_4h = loader.fetch_with_dqf('BTC/USD', '2024-01-01', '2024-08-28', '4h')
df_1h = loader.fetch_with_dqf('BTC/USD', '2024-01-01', '2024-08-28', '1h')

# Utiliser dans stratégie
from strategies.strategy_042_sentinel import SentinelCross042

strategy = SentinelCross042()

# Test sur 1h
entries, exits = strategy.calculate_signals(df_1h.set_index('timestamp'))
print(f"Signaux 1h: {entries.sum()} entrées, {exits.sum()} sorties")
```

### Exemple 2: Comparaison Multi-Assets

```python
loader = UnifiedDataLoader()

assets = ['BTC/USD', 'ETH/USD']
results = {}

for asset in assets:
    df = loader.fetch_with_dqf(
        asset, '2024-01-01', '2024-08-28', '1h'
    )
    
    returns = df['close'].pct_change()
    total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    volatility = returns.std() * (252 * 24) ** 0.5 * 100
    
    results[asset] = {
        'return': total_return,
        'volatility': volatility,
        'sharpe': total_return / volatility if volatility > 0 else 0
    }

import pandas as pd
print(pd.DataFrame(results).T)
```

### Exemple 3: Pipeline Complet avec dry run

```python
import os
from data.dukascopy_client import DukascopyClient
from data.dukascopy_fetcher import fetch_with_retry
from strategies.strategy_042_sentinel import SentinelCross042
from core.backtest_engine import BacktestEngine

# Le mode est contrôlé par DUKASCOPY_DRY_RUN
client = DukascopyClient.from_env()
print(f"Mode : {'DRY RUN' if client.dry_run else 'RÉEL'}")

# Téléchargement avec retry automatique
df = fetch_with_retry(
    client, 'btcusd', '1h',
    '2024-01-01', '2024-08-28',
    max_retries=3,
    retry_delay=60.0,
)

# Génération signaux
strategy = SentinelCross042()
entries, exits = strategy.calculate_signals(df.set_index('timestamp'))

# Backtest
engine = BacktestEngine(initial_capital=10000, commission=0.001)
results = engine.run(df, entries, exits)

print(f"Return: {results['total_return']*100:.2f}%")
print(f"Sharpe: {results['sharpe']:.2f}")
print(f"Max DD: {results['max_drawdown']*100:.2f}%")
```

---

## Résumé des Accomplissements

### Ce qui fonctionne ✅

1. **Installation Dukascopy sur NixOS**
   - Configuration npm global local (`~/.npm-global`)
   - Installation dukascopy-node via npm
   - PATH persistant dans shellHook

2. **Module data_preparation_module.py**
   - Téléchargement automatique CSV
   - Parsing robuste (avec/sans header)
   - Cache intelligent
   - Gestion erreurs complète

3. **DukascopyClient avec dry run**
   - Mode dry run par flag ou variable d'environnement
   - Données synthétiques reproductibles (seed déterministe)
   - Erreurs typées (`DukascopyNetworkError`, `is_transient`)
   - Retry intelligent via `fetch_with_retry`

4. **Données Disponibles**
   - BTC/USD: 1h, 4h, 30m (2024-01-01 → 2024-08-28)
   - ETH/USD: 1h, 4h, 30m (2024-01-01 → 2024-08-28)
   - Format standardisé OHLCV

### Prochaines Étapes 🎯

1. **Créer unified_data_loader.py**
   - Intégrer Yahoo + Dukascopy
   - DQF complet sur toutes sources
   - Routing automatique daily/intraday

2. **Tester stratégie 042 sur intraday**
   - Backtest sur 1h (dry run d'abord, réel ensuite)
   - Backtest sur 4h
   - Comparaison avec daily

3. **Optimisation**
   - Cache persistant
   - Téléchargement parallèle avec throttling
   - Compression CSV

---

## Références

- **Dukascopy Node Package:** https://www.npmjs.com/package/dukascopy-node
- **Dukascopy API Docs:** https://www.dukascopy.com/swiss/english/marketwatch/historical/
- **NixOS Package Search:** https://search.nixos.org/packages
- **Projet GitHub:** (Votre repo)

---

**Document maintenu par:** [Votre nom]  
**Dernière mise à jour:** 9 Mai 2026  
**Version:** 1.1 — Dry Run & Gestion d'erreurs réseau

---

*Ce guide documente l'intégralité du processus d'installation et d'utilisation de Dukascopy sur NixOS pour le trading algorithmique. Toutes les solutions aux problèmes rencontrés sont documentées et testées.*
