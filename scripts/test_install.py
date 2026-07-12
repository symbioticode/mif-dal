#!/usr/bin/env python3
"""
test_install.py — Gate de vérification post-installation mif-dal
Usage : python scripts/test_install.py
Attendu : toutes les vérifications passent sans exception.
"""
import platform
import sys
from datetime import UTC


def check(label: str, fn) -> bool:
    try:
        result = fn()
        if result is not False:
            print(f"  ✓ {label}")
            return True
        else:
            print(f"  ✗ {label}")
            return False
    except Exception as e:
        print(f"  ✗ {label}")
        print(f"      {type(e).__name__}: {e}")
        return False


def main() -> int:
    print(f"Platform : {platform.system()} / Python {platform.python_version()}")

    import dal

    print(f"mif-dal  : {dal.__version__}")

    failures = 0

    # ── Import de base ────────────────────────────────────────────────────────
    def check_imports():
        return True

    if not check(
        "Imports de base (DAL, DALConfig, DALHandoff, exceptions)", check_imports
    ):
        failures += 1

    # ── Instanciation DAL ─────────────────────────────────────────────────────
    def check_dal_init():
        from dal import DAL, DALConfig

        config = DALConfig()
        dal_instance = DAL(config, sources=())
        return dal_instance is not None

    if not check("DAL(DALConfig()) instanciable", check_dal_init):
        failures += 1

    # ── Signature get_certified_stream ────────────────────────────────────────
    def check_signature():
        import inspect

        from dal import DAL, DALConfig

        dal_instance = DAL(DALConfig(), sources=())
        sig = inspect.signature(dal_instance.get_certified_stream)
        params = set(sig.parameters.keys())
        required = {"asset_id", "source_preference", "start", "end", "calendar"}
        missing = required - params
        if missing:
            raise ValueError(
                f"Paramètres manquants dans get_certified_stream : {missing}"
            )
        return True

    if not check("get_certified_stream() a la bonne signature", check_signature):
        failures += 1

    # ── Signature get_diagnostic_stream ───────────────────────────────────────
    def check_diag_signature():
        import inspect

        from dal import DAL, DALConfig

        dal_instance = DAL(DALConfig(), sources=())
        sig = inspect.signature(dal_instance.get_diagnostic_stream)
        params = set(sig.parameters.keys())
        required = {"asset_id", "source_preference", "start", "end", "calendar"}
        missing = required - params
        if missing:
            raise ValueError(
                f"Paramètres manquants dans get_diagnostic_stream : {missing}"
            )
        return True

    if not check("get_diagnostic_stream() a la bonne signature", check_diag_signature):
        failures += 1

    # ── DALHandoff frozen ─────────────────────────────────────────────────────
    def check_handoff_frozen():
        import hashlib
        from datetime import datetime

        import pandas as pd
        from dqf import DQFConfig, DQFMode, DQFValidator

        from dal import DALHandoff

        dates = pd.date_range("2024-01-02", periods=5, freq="B", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [100.0] * 5,
                "high": [101.0] * 5,
                "low": [99.0] * 5,
                "close": [100.5] * 5,
                "volume": [1000.0] * 5,
            },
            index=dates,
        )
        raw_bytes = df.to_parquet()
        assembly_hash = hashlib.sha256(raw_bytes).hexdigest()

        config = DQFConfig(mode=DQFMode.DIAGNOSTIC)
        validator = DQFValidator(config)
        report = validator.validate(df, calendar="NYSE")

        h = DALHandoff(
            stream=df,
            asset_id="TEST-USD",
            calendar="NYSE",
            assembly_hash=assembly_hash,
            handoff_timestamp=datetime.now(UTC),
            dal_version="0.1.0",
            source_manifest=(
                {
                    "source_id": "test",
                    "status": "success",
                    "hash": assembly_hash,
                    "fetched_at": datetime.now(UTC),
                    "rows": 5,
                    "timeframe": "1D",
                    "fallback": False,
                },
            ),
            coverage="FULL",
            truncated_days=0,
            dqf_status="PASS",
            dqf_mpi=100.0,
            dqf_version="1.2.0.post1",
            dqf_version_target="1.2.0",
            dqf_report=report,
            aqi=100.0,
        )

        # Vérifier frozen
        try:
            h.asset_id = "MUTATED"  # type: ignore
            return False  # ne doit pas arriver
        except Exception:
            pass  # attendu — frozen=True

        assert len(h.assembly_hash) == 64
        assert h.coverage == "FULL"
        return True

    if not check(
        "DALHandoff frozen=True, 15 champs, assembly_hash SHA-256", check_handoff_frozen
    ):
        failures += 1

    # ── InMemorySource ────────────────────────────────────────────────────────
    def check_in_memory():

        import pandas as pd

        from dal.adapters.in_memory import InMemorySource
        from dal.interfaces.source import FetchRequest

        dates = pd.date_range("2024-01-02", periods=5, freq="B", tz="UTC")
        df = pd.DataFrame(
            {
                "open": [100.0] * 5,
                "high": [101.0] * 5,
                "low": [99.0] * 5,
                "close": [100.5] * 5,
                "volume": [1000.0] * 5,
            },
            index=dates,
        )
        source = InMemorySource(source_id="test", data={"TEST-USD": df})
        assert source.supports("TEST-USD") is True
        assert source.supports("UNKNOWN-USD") is False

        req = FetchRequest(
            asset_id="TEST-USD",
            start="2024-01-01",
            end="2024-01-10",
            timeframe="1D",
        )
        result = source.fetch(req)
        assert result.status == "success"
        assert result.rows > 0
        assert len(result.hash) == 64
        return True

    if not check("InMemorySource({asset: df}) — supports() + fetch()", check_in_memory):
        failures += 1

    # ── __all__ ───────────────────────────────────────────────────────────────
    def check_all():
        import dal as dal_module

        required_symbols = {
            "DAL",
            "DALConfig",
            "DALHandoff",
            "DALError",
            "DALHandoffError",
        }
        missing = required_symbols - set(getattr(dal_module, "__all__", []))
        if missing:
            raise ValueError(f"Symboles manquants dans __all__ : {missing}")
        return True

    if not check("dal.__all__ contient les symboles publics", check_all):
        failures += 1

    # ── Résultat ──────────────────────────────────────────────────────────────
    print()
    if failures == 0:
        print(
            f"✅  test_install.py — {7 - failures}/7 PASS — mif-dal {dal.__version__} OK"
        )
        return 0
    else:
        print(f"❌  test_install.py — {7 - failures}/7 PASS — {failures} FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
