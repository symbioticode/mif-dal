# Changelog

All notable changes to mif-dal are documented here.

## [0.1.0] — 2026-05-XX

### Added
- `DALHandoff` — frozen dataclass, 15 fields, `assembly_hash`, AQI
- Exception hierarchy: `DALError`, `DALConfigError`, `DALVersionError`,
  `DALHandoffError`
- `DALConfig` (cache_dir, request_timeout)
- `pipeline.assemble_handoff()` — S3 hash + S4 DQF gate + S5 emission
- `resolve_and_fetch()` — S1 source resolution + retry/fallback +
  S2 completeness + AQI calculation with floor
- `KrakenAdapter` — public REST API, OHLCV daily, PAXG/BTC
- `YahooAdapter` — yfinance ≥ 1.3.0, MultiIndex handling
- `DukascopyAdapter` — subprocess, detection via `--help`
- `InMemorySource` — deterministic adapter for tests, failure simulation
- `validate_environment.py` — GO/NO-GO for NixOS / Colab / Windows
- `validate_dal_state.py` — GO/NO-GO 5-check script

### Fixed
- DQF has no FAIL status — mapping corrected to VOID + `case _` guard
- AQI floor `max(0, ...)` — formula could produce negative values
- `DALHandoff frozen=True` — `source_manifest` as `tuple`, not `list`
- `calendar` required in `get_diagnostic_stream` (DALHandoff invariant)
- Dukascopy detection via `--help` (not `--version` — upstream exit-1 bug)

### Known issues
- TD-008: AQI gravities (0.20/0.10/0.05/0.30) not empirically calibrated
- TD-012: dukascopy-node PATH unstable in NixOS nix-shell (test xfail)