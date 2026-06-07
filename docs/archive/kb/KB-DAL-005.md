# KB-DAL-005: Lessons Learned from Kraken Adapter Integration and NixOS Environment Management

## Summary of Lessons Learned from ISSUE-DAL-P3-001 (Kraken Adapter)

### 1. Understanding Third-Party API Limitations
- Always investigate the actual data availability window of third-party APIs before writing tests or depending on historical data.
- Kraken's public OHLC API only provides approximately 2 years of historical data (as of 2026, this means data from ~mid-2024 onward for daily timeframes).
- When integrating with external APIs, document their limitations clearly in the adapter documentation and in the project knowledge base.

### 2. Test Data Selection Strategy
- Integration tests should use date ranges that are guaranteed to be available across all configured data sources.
- For multi-source fallback testing, select date ranges that work for the least capable source in the chain.
- Consider creating a test utility that validates date range availability against each adapter before running tests.

### 3. Adapter Robustness for Edge Cases
- Adapters should gracefully handle cases where requested data is outside the available range by returning appropriate status (failed/partial) rather than attempting futile pagination.
- The Kraken adapter was updated to detect when no overlapping data exists between the requested range and available data, terminating early rather than continuing to paginate.
- Always validate that an adapter's response makes sense for the given request before proceeding with further processing.

### 4. Test Mocking Best Practices
- When mocking adapter failures in tests, ensure that the mock correctly simulates the failure mode (raising SourceFetchError rather than returning a failed FetchResult).
- Tests should verify that the resolver properly handles the exception and moves to the next source in the chain.
- Assertions should work with the actual return types of functions (e.g., ResolutionResult from resolve_and_fetch, not FetchResult).

## Imperatives for NixOS Environment Management

### 1. Dukascopy-node Detection
- Never use `--version` to check for dukascopy-node availability due to an upstream bug where it returns exit code 1 even when installed.
- Always use `--help` (exit code 0) for detection, both in `conftest.py` and in `DukascopyAdapter._node_available()`.

### 2. PATH Management in NixOS
- In NixOS environments, the npm global bin directory (`$HOME/.npm-global/bin`) is not automatically in the PATH.
- The proper solution is to export `NPM_GLOBAL=$HOME/.npm-global` and add `$NPM_GLOBAL/bin` to PATH in the shellHook of shell.nix or flake.nix.
- This ensures that dukascopy-node (installed globally via npm) is discoverable by the DAL.

### 3. Dependency Version Pinning
- Maintain strict version pins in pyproject.toml for all dependencies to ensure reproducible builds.
- Specifically for yfinance, use `>=1.3.0,<2.0.0` to avoid breaking changes in the YahooAdapter.
- After updating dependencies, always reinstall the package in development mode (`pip install -e .`) to propagate changes to the virtual environment.

### 4. Environment Validation
- Use the provided `scripts/validate_environment.py` to verify that all prerequisites are met before running tests or development.
- This script checks:
  - Python >= 3.11
  - Required Python packages (mif-dqf, yfinance>=1.3.0, pandas)
  - Node.js availability
  - Dukascopy-node availability (via --help)
  - UTF-8 encoding compatibility (with warning for Windows CP1252)
  - DAL importability and version definition

### 5. Cross-Platform Testing Strategy
- Before considering a feature complete, test on all three target environments:
  1. NixOS (using nix-shell with .venv)
  2. Google Colab
  3. Windows (PowerShell)
- Document any environment-specific quirks or workarounds in the knowledge base.
- Update validation scripts and documentation as new platform-specific issues are discovered.

## Ongoing Practices

### Documentation Updates
- When resolving an issue that reveals a limitation or best practice, update both:
  1. The specific issue document (in docs/issues/)
  2. The relevant knowledge base article (in docs/kb/)
- This ensures that lessons learned are preserved and easily accessible.

### Test Maintenance
- After fixing an issue, verify that:
  1. The originally failing test now passes
  2. No regressions are introduced in related functionality
  3. Edge cases are covered by additional tests if appropriate

### Dependency Management
- Treat dependency updates as a deliberate process:
  1. Update version constraints in pyproject.toml
  2. Reinstall the package
  3. Run the full test suite to ensure compatibility
  4. Update validation scripts and documentation as needed

## References
- ISSUE-DAL-P3-001: Kraken Adapter Returns No Data for Historical Date Ranges
- DUKASCOPY_COMPLETE_GUIDE.md: Complete guide to DukascopyAdapter installation and usage
- KB-DAL-003.md: NixOS-specific setup instructions for dukascopy-node
- validate_environment.py: Environment validation script
- anamnese_state.yaml: Project state tracking (updated by automation)