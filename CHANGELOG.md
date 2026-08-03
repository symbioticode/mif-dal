# Changelog

All notable changes to mif-dal are documented here.

## [0.2.0] — 2026-08-03

### Added
- `DAL.get_certified_stream()` / `get_diagnostic_stream()` accept an optional
  `dqf_config: DQFConfig | None = None`, passed through to `assemble_handoff()`,
  exposing DQF threshold configuration (e.g. `c4_warn_threshold`) on the public
  API (#7)

### Fixed
- `resolve_and_fetch()` now falls back to the next source in
  `source_preference` when a source reports `status="failed"` without
  raising, instead of returning that empty/degraded result as if it were a
  success (#4)
- `start`/`end` are validated before reaching pandas or an adapter: an
  unparseable date or `start > end` now raises a clear `DALConfigError`
  instead of a raw pandas exception or an opaque `DALHandoffError(reason="DQF_VOID")` (#6)

### Documentation
- Fixed the broken README Quick Start example: `DAL(config)` →
  `DAL(config, sources=(KrakenAdapter(), YahooAdapter()))` (#3)
- Fixed the same broken `DAL(config)` example in `docs/API.md`, and the dead
  `docs/TROUBLESHOOTING.md` link → `TROUBLESHOOTING.md` (#5)
- Documented the hash-reproducibility trap when revalidating a certification
  manually outside mif-dal: `raw_data_hash=handoff.assembly_hash` is required
  to reproduce the original `MIF-UID` (#8)

## [0.1.0] — 2026-07-09

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