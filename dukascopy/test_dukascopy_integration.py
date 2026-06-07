#!/usr/bin/env python3
"""
Test d'intégration Dukascopy sur NixOS
 ======================================
Vérifie que data_preparation_module.py fonctionne correctement
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from data.data_preparation_module import DukascopyDataPreparator, MarketDataManager


def test_dukascopy_installation():
    """Test 1: Vérification installation Dukascopy"""
    print("=" * 80)
    print("TEST 1: VÉRIFICATION INSTALLATION DUKASCOPY")
    print("=" * 80)

    try:
        prep = DukascopyDataPreparator(data_dir="test_data")
        print("✅ DukascopyDataPreparator initialisé")
        return True
    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        return False


def test_simple_download():
    """Test 2: Téléchargement simple (7 jours)"""
    print("\n" + "=" * 80)
    print("TEST 2: TÉLÉCHARGEMENT SIMPLE (7 jours)")
    print("=" * 80)

    try:
        prep = DukascopyDataPreparator(data_dir="test_data")

        # 7 derniers jours
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        print("\n📊 Paramètres:")
        print("   Symbole: BTC/USD")
        print("   Timeframe: 1h")
        print(f"   Période: {start_date.date()} → {end_date.date()}")

        df = prep.get_data(
            symbol="BTC/USD", timeframe="1h", start_date=start_date, end_date=end_date
        )

        print("\n✅ Téléchargement réussi:")
        print(f"   Points: {len(df)}")
        print(f"   Colonnes: {list(df.columns)}")
        print(f"   Période réelle: {df['timestamp'].min()} → {df['timestamp'].max()}")

        # Validation basique
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        if all(col in df.columns for col in required_cols):
            print("   ✅ Format OHLCV complet")
        else:
            print("   ❌ Colonnes manquantes")
            return False

        # Check NaN
        nan_count = df.isnull().sum().sum()
        if nan_count == 0:
            print("   ✅ Aucune valeur manquante")
        else:
            print(f"   ⚠️  {nan_count} valeurs manquantes")

        return True

    except Exception as e:
        print(f"❌ Erreur téléchargement: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_multiple_timeframes():
    """Test 3: Plusieurs timeframes"""
    print("\n" + "=" * 80)
    print("TEST 3: MULTI-TIMEFRAMES")
    print("=" * 80)

    try:
        prep = DukascopyDataPreparator(data_dir="test_data")

        # 30 derniers jours
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        timeframes = ["4h", "1h"]

        print(f"\n📊 Test timeframes: {timeframes}")

        results = prep.prepare_multiple_timeframes(
            symbol="BTC/USD",
            start_date=start_date,
            end_date=end_date,
            timeframes=timeframes,
        )

        success_count = 0
        for tf, df in results.items():
            if df is not None:
                print(f"   ✅ {tf}: {len(df)} points")
                success_count += 1
            else:
                print(f"   ❌ {tf}: Échec")

        if success_count == len(timeframes):
            print("\n✅ Tous les timeframes téléchargés")
            return True
        else:
            print(f"\n⚠️  {success_count}/{len(timeframes)} timeframes réussis")
            return False

    except Exception as e:
        print(f"❌ Erreur multi-timeframes: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_market_data_manager():
    """Test 4: MarketDataManager (abstraction complète)"""
    print("\n" + "=" * 80)
    print("TEST 4: MARKET DATA MANAGER")
    print("=" * 80)

    try:
        manager = MarketDataManager(data_dir="test_data", prefer_dukascopy=True)

        print("✅ Manager initialisé")
        print(f"   Sources disponibles: {manager.get_available_sources()}")
        print(f"   Source par défaut: {manager.default_source}")

        # Test download
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)

        data = manager.prepare_data(
            symbol="BTC/USD",
            timeframes=["1h"],
            start_date=start_date,
            end_date=end_date,
        )

        if "1h" in data and data["1h"] is not None:
            print("\n✅ Téléchargement via Manager:")
            print(f"   Timeframe 1h: {len(data['1h'])} points")
            return True
        else:
            print("❌ Échec téléchargement via Manager")
            return False

    except Exception as e:
        print(f"❌ Erreur Manager: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_strategy_042_signals():
    """Test 5: Génération signaux Sentinel 042 sur données Dukascopy"""
    print("\n" + "=" * 80)
    print("TEST 5: SIGNAUX STRATÉGIE 042")
    print("=" * 80)

    try:
        from strategies.strategy_042_sentinel import SentinelCross042

        # Download data
        prep = DukascopyDataPreparator(data_dir="test_data")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 3 mois pour avoir assez de données

        df = prep.get_data("BTC/USD", "1h", start_date, end_date)

        # Renommer timestamp → index
        df_indexed = df.set_index("timestamp")

        print(f"✅ Données: {len(df_indexed)} points")

        # Stratégie
        strategy = SentinelCross042()
        entries, exits = strategy.calculate_signals(df_indexed)

        print("\n📊 Signaux:")
        print(f"   Entrées: {entries.sum()}")
        print(f"   Sorties: {exits.sum()}")

        if entries.sum() > 0 and exits.sum() > 0:
            print("✅ Signaux générés avec succès")
            return True
        else:
            print("⚠️  Peu/pas de signaux (peut être normal)")
            return True  # Pas une erreur

    except Exception as e:
        print(f"❌ Erreur signaux: {e}")
        import traceback

        traceback.print_exc()
        return False


def cleanup():
    """Nettoyage fichiers de test"""
    import shutil

    test_dir = Path("test_data")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("\n🧹 Fichiers de test nettoyés")


def main():
    print("=" * 80)
    print("SUITE DE TESTS DUKASCOPY INTEGRATION")
    print("=" * 80)

    tests = [
        ("Installation", test_dukascopy_installation),
        ("Download Simple", test_simple_download),
        ("Multi-Timeframes", test_multiple_timeframes),
        ("Market Manager", test_market_data_manager),
        ("Signaux 042", test_strategy_042_signals),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Exception non gérée dans {name}: {e}")
            results.append((name, False))

    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {name}")

    print(f"\n📊 Score: {passed}/{total} tests réussis")

    if passed == total:
        print("\n✅ TOUS LES TESTS PASSÉS")
        print("   Dukascopy est prêt pour utilisation en production")
    elif passed >= total * 0.8:
        print("\n⚠️  TESTS MAJORITAIREMENT RÉUSSIS")
        print("   Quelques ajustements peuvent être nécessaires")
    else:
        print("\n❌ ÉCHEC DES TESTS")
        print("   Investigation requise avant utilisation")

    # Nettoyage
    cleanup()

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
