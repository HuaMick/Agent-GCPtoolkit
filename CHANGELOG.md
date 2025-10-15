# Changelog

All notable changes to Agent-GCPtoolkit will be documented in this file.

## [0.1.0] - 2025-10-15

### Added
- Backend restructuring following MyAgents standards
  - `backend/services/secrets/src/domains/` for models and GCP client
  - `backend/services/secrets/src/workflows/` for business logic
- CLI enhancements via `gcptoolkit` command
  - `gcptoolkit version` - Show version information
  - `gcptoolkit update` - Reinstall from latest build
  - `gcptoolkit reinstall` - Alias for update
  - `gcptoolkit secrets get SECRET_NAME` - Fetch secrets
- Build artifacts folder: `build-artifacts/`
  - `build-artifacts/dist/` - Distribution packages
  - `build-artifacts/build/` - Intermediate build files
- Development scripts
  - `scripts/build.sh` - Build wheel with UV
  - `scripts/install-global.sh` - Install with UV tool (RECOMMENDED)
  - `scripts/install.sh` - Install with UV pip (requires venv activation)
  - `scripts/clean.sh` - Clean build artifacts
- Integration tests in `tests/test_integration.sh`
- MyAgents Makefile targets for build/install
- Input validation for secret names and values
- Quiet mode for script-friendly output

### Improved
- **UV Tool Installation**: Global CLI access using `uv tool install` without venv activation
- **GCP_PROJECT Support**: Environment variable support (overrides gcloud config)
- **Standardized Exit Codes**: 0=success, 1=runtime errors, 2=usage errors
- **Quiet Mode**: `--quiet` flag to suppress stderr warnings in scripts
- **Clear Authentication**: Documented exactly what authentication is required
- **Accurate Troubleshooting**: Shows actual CLI output instead of exception names
- **Complete Help System**: Help text for all commands (version, update, reinstall, secrets get)
- **Secret Name Validation**: Format validation with clear error messages ([a-zA-Z0-9_-] only)
- **Empty Value Handling**: Validation with helpful guidance for GCP limitation
- **Cache Clarification**: Documented that memory caching is per-process, not per-CLI invocation

### Changed
- Moved core logic from `agent_gcptoolkit/secrets.py` to `backend/services/secrets/`
- Updated `pyproject.toml` to include all packages and CLI entrypoint
- Installation now uses wheels instead of editable mode
- README extensively updated with UV tool install documentation
- Help system now provides useful information for every command

### Deprecated
- `agent_gcptoolkit.secrets` module (use `backend.services.secrets.src.workflows.secret_operations` instead)

### Fixed
- CLI not accessible after installation (now uses UV tool install)
- GCP_PROJECT env var documented but not implemented (now works)
- Exit codes inconsistent (now standardized to 0/1/2)
- Stderr pollution on successful commands (now has quiet mode)
- Help output missing for version/update/reinstall commands (now complete)
- Invalid secret names cause confusing GCP errors (now validated at CLI level)
- Empty secret values cause confusing GCP errors (now validated with clear message)
- Documentation showed exception names users never see (now shows actual CLI output)

### Maintained
- Backward compatibility for `from agent_gcptoolkit.secrets import get_secret`
- Same caching and fallback behavior
- Same API surface
