# Troubleshooting — mif-dal

## Kraken: data only available for ~12 months

**Symptom:** Integration tests fail with `0 rows` or `status='failed'`
for date ranges starting more than 12 months ago.

**Cause:** Kraken's OHLCV API returns data for approximately the last
12 months (rolling window). This is an API constraint, not a mif-dal bug.

**Fix:** Use `start >= (today - 11 months)` for Kraken integration tests.
For historical data beyond 12 months, use Yahoo Finance or Dukascopy.

```python
from datetime import date, timedelta
start = (date.today() - timedelta(days=330)).isoformat()
```

---

## PAXG-USD unavailable on Kraken (regional restriction)

**Symptom:** `KrakenAdapter.fetch("PAXG-USD")` returns `status='failed'`
despite valid date range.

**Cause:** PAXG-USD trading is blocked for users in certain regions
(including Canada) on Kraken. This is a Kraken policy, not a mif-dal bug.

**Fix:** Use Yahoo Finance as fallback:

```python
h = dal.get_certified_stream(
    asset_id="PAXG-USD",
    source_preference=["yahoo"],  # skip Kraken for PAXG
    ...
)
```

---

## dukascopy-node not found

**Symptom:**

```
DukascopyAdapter: dukascopy-node not available — skipping
```

or tests marked as skipped with `skip_if_no_dukascopy`.

**Cause:** `dukascopy-node` is a Node.js package required by `DukascopyAdapter`.
It is not installed by default.

**Fix:**

```bash
npm install -g dukascopy-node
```

Verify detection:

```bash
dukascopy-node --help  # must succeed
```

Note: detection uses `--help`, not `--version` (NixOS compatibility).

---

## NixOS: dukascopy-node not available via nodePackages

**Symptom:** `nix-shell` with `nodePackages.dukascopy-node` fails —
package removed from nixpkgs.

**Fix:** Install via npm inside the nix-shell:

```bash
nix-shell  # enter the environment
npm install -g dukascopy-node
```

Or add to `flake.nix` as a shellHook:

```nix
shellHook = ''
  npm install -g dukascopy-node 2>/dev/null || true
'';
```

See `dukascopy/DUKASCOPY_COMPLETE_GUIDE.md` for the full NixOS setup.

---

## NixOS: pytest-cov not functional

**Symptom:**

```
ERROR: Failed to load plugin 'cov': No module named 'pytest_cov'
```

or coverage commands fail silently.

**Cause:** `pytest-cov` may be importable but not loadable as a pytest
plugin in some NixOS + Python 3.12/3.13 environments.

**Fix:** Run pytest without coverage:

```bash
pytest tests/ -q --tb=short
# instead of: pytest tests/ --cov=dal
```

The adversarial suite (`scripts/validate_dal_state.py --full`) does not
require coverage and is the primary quality gate.

---

## mypy not available in venv

**Symptom:**

```
[SKIP] Mypy not installed — run: uv add --dev mypy
```

**Cause:** `mypy` is an optional dev dependency not installed by default
in some environments.

**Fix:**

```bash
uv add --dev mypy
# or
pip install mypy
```

The `dev.sh` gate skips mypy gracefully if absent — Ruff and pytest
are the mandatory checks.

---

## verify_install.py: DAL(config) raises TypeError

**Symptom:**

```
TypeError: DAL.__init__() missing 1 required positional argument: 'sources'
```

**Cause:** `DAL.__init__` requires explicit `sources` in v0.1.0.
`verify_install.py` must pass sources explicitly.

**Fix:** See `scripts/test_install.py` for the corrected version.

---

## SettingWithCopyWarning from YahooAdapter

**Symptom:**

```
SettingWithCopyWarning: A value is trying to be set on a copy of a slice
```

**Cause:** pandas >= 2.0 changed slice behavior. Fixed in v0.1.0 by
replacing `df.rename(inplace=True)` with `df = df.rename(...)`.

If you see this warning, ensure you are on `mif-dal >= 0.1.0`.

---

## assembly_hash differs between calls

**Symptom:** Two calls with the same parameters produce different `assembly_hash`.

**Expected causes (not bugs):**

1. **Different source used:** If Kraken was unavailable and Yahoo was used
   as fallback, the hash will differ — two sources are two different facts.
   Check `source_manifest` to identify which source was used.

2. **Date range truncated:** If the source delivered a different range
   (partial data), the raw bytes differ. Check `coverage` and `truncated_days`.

3. **Source data changed:** Yahoo Finance occasionally revises historical
   data. A call today may return different bytes than a call last month.

**Not an expected cause:** mif-dal's hash computation is deterministic
(`to_parquet()` on the same DataFrame always produces the same bytes).
If you suspect non-determinism in hashing, run the adversarial suite:

```bash
python scripts/validate_dal_state.py --full
```

The adversarial suite verifies: same DataFrame → same hash, different
DataFrames → different hashes.

---

## VIRTUAL_ENV warning from uv

**Symptom:**

```
warning: `VIRTUAL_ENV=/path/to/other/.venv` does not match the project
environment path `.venv` and will be ignored
```

**Cause:** A different project's venv is activated. uv ignores it and
uses the project's `.venv`.

**Fix:** Deactivate the other venv first, or ignore the warning — it is
informational only.

```bash
deactivate  # deactivate current venv
uv sync --extra dev
```
