# Agent-GCPtoolkit

Unified secret management for GCP-based agent worktrees. Provides a single source of truth for secrets via GCP Secret Manager with intelligent caching and fallback mechanisms.

## Why This Exists

When working with multiple agent worktrees, managing secrets becomes problematic:
- Duplicating .env files across worktrees creates inconsistency
- Hard-coding secrets is a security risk
- Environment variables don't scale across multiple processes

Agent-GCPtoolkit solves this by centralizing secrets in GCP Secret Manager while providing seamless local development support through environment variable fallback.

## Features

- **get_secret()** - Single function to fetch secrets from GCP Secret Manager
- **Memory caching** - Secrets fetched once per process, reducing API calls
- **Environment variable fallback** - Graceful degradation when GCP is unavailable
- **Config-based authentication** - Service account authentication via config file

## Quick Start (No GCP Required)

Test locally with environment variables:

```bash
# Build and install
./scripts/build.sh && ./scripts/install-global.sh

# Set a test secret
export MY_SECRET="test_value"

# Retrieve it
gcptoolkit secrets get MY_SECRET
# Output: test_value
# Note: May show GCP warning on stderr (safe to ignore when using env vars)
```

For production setup with GCP Secret Manager, see [Prerequisites](#prerequisites).

## Prerequisites

### 1. GCP Project Setup

```bash
gcloud services enable secretmanager.googleapis.com
```

### 2. Authentication

Authentication is configured via service account in `/home/code/myagents/config/config_agent_gcptoolkit.yml`:

```yaml
authentication:
  service_account_path: /path/to/service-account-key.json

gcp:
  project_id: your-gcp-project-id
```

### 3. Service Account Permissions

```bash
# Grant Secret Manager access to your service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Project ID Override (Optional)

Override config file project_id with environment variable:
```bash
export GCP_PROJECT="my-project-id"
```

## Installation

### Method 1: UV Tool (RECOMMENDED)

Globally accessible without venv activation. Reference: https://docs.astral.sh/uv/concepts/tools/

```bash
./scripts/build.sh && ./scripts/install-global.sh
gcptoolkit version
```

### Method 2: UV Pip (Requires venv activation)

```bash
./scripts/build.sh && ./scripts/install.sh
source .venv/bin/activate
gcptoolkit version
```

### Development Scripts

- `./scripts/build.sh` - Build wheel
- `./scripts/install-global.sh` - Install globally (recommended)
- `./scripts/install.sh` - Install in venv
- `./scripts/clean.sh` - Clean build artifacts

## Usage

> **Note**: For cross-worktree usage (e.g., MyAgents accessing Agent-GCPtoolkit secrets), use the CLI interface below. Python imports only work within the Agent-GCPtoolkit codebase itself due to worktree isolation.

### CLI Commands

```bash
gcptoolkit version                      # Show version
gcptoolkit secrets get MY_SECRET        # Get secret
gcptoolkit secrets get MY_SECRET -q     # Get secret in quiet mode (value only)
./scripts/build.sh && gcptoolkit update # Update from latest build
```

### Shell Script Integration

For using secrets in shell scripts, use the `-q` (quiet) flag for clean value capture:

```bash
#!/bin/bash
set -e

# Fetch secret with quiet mode (-q) and stderr suppression
API_TOKEN=$(gcptoolkit secrets get API_TOKEN -q 2>/dev/null)

# Verify value was retrieved
if [ -z "$API_TOKEN" ]; then
    echo "Error: Failed to fetch API_TOKEN" >&2
    exit 1
fi

# Use in API calls
curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/data
```

The `-q` flag ensures only the secret value is output to stdout, making it safe for variable assignment and piping to other commands.

See `/home/code/myagents/fetch_and_use_token.sh` for a complete working example.

### Secret Name Format

Must match: `[a-zA-Z0-9_-]+`

Valid: `MY_SECRET`, `api-key-prod`, `DATABASE_PASSWORD_123`
Invalid: `api.key`, `MY SECRET`, `test@prod`

Note: Invalid names rejected by GCP with "Secret not found" error. Empty values not allowed - use placeholder like `UNSET` or `TODO`.

### Exit Codes

- **0** - Success
- **1** - Runtime error (auth failed, secret not found, network error)
- **2** - Usage error (invalid arguments)

### Stderr Output

GCP failures fall back to environment variable. Warnings go to stderr, values to stdout. Suppress warnings:
```bash
SECRET_VALUE=$(gcptoolkit secrets get MY_SECRET 2>/dev/null)
```

## How It Works

1. **Environment Variable Priority**: Checks environment variables FIRST for fast local development. Only initializes GCP client if env var not found. This provides:
   - Fast local development (< 1ms when using env vars)
   - No GCP authentication delay during development
   - Production still uses GCP Secret Manager when env vars not set

2. **Memory Caching**: Secrets are cached in-memory per-process. CLI invocations spawn new processes, so caching only benefits multiple `get_secret()` calls within the same Python script.

3. **Project ID Resolution**: Uses config file or GCP_PROJECT environment variable to determine the GCP project

## Environment Variables

- **GCP_PROJECT** - GCP project ID (optional, overrides config file)

## Troubleshooting

### Secret not found

```bash
# Check if secret exists
gcloud secrets list | grep MY_SECRET

# Verify project ID in config
cat /home/code/myagents/config/config_agent_gcptoolkit.yml

# Override project ID if needed
export GCP_PROJECT="my-correct-project"

# Use env var fallback
export MY_SECRET="fallback-value"
```

### GCP fetch failed warning

Command succeeded using env var fallback. Verify authentication is configured correctly in `/home/code/myagents/config/config_agent_gcptoolkit.yml` or suppress stderr:

```bash
gcptoolkit secrets get MY_SECRET 2>/dev/null
```

### Permission denied

Verify your service account has the required role in Prerequisites section 3, or use env var fallback.

### Command not found

UV pip installation requires venv activation:
```bash
source .venv/bin/activate
```

UV tool installation requires shell reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

Recommended: Use UV tool installation for global access.

## Architecture

```
Agent-GCPtoolkit/
├── backend/services/secrets/src/
│   ├── domains/              # Models and GCP client
│   └── workflows/            # get_secret() with caching & fallback
├── frontend/cli/             # CLI entrypoint and validators
├── agent_gcptoolkit/         # Backward compatibility (DEPRECATED)
├── build-artifacts/          # Build outputs (git-ignored)
└── scripts/                  # Build and install scripts
```

### Design Principles

1. **Separation of Concerns**: Domains (models, clients) separate from workflows (business logic)
2. **Backward Compatibility**: Old imports work with deprecation warnings
3. **Build Artifacts Isolation**: All generated files in `build-artifacts/`
4. **UV Package Manager**: Build and install with UV, not pip
5. **Input Validation**: CLI validates before calling backend
6. **Standardized Exit Codes**: 0=success, 1=runtime, 2=usage

### Migration Path

> **Note**: Python imports are only for code within Agent-GCPtoolkit itself. For cross-worktree usage, use the CLI.

```python
# Old (works with deprecation warning, Agent-GCPtoolkit internal use only)
from agent_gcptoolkit.secrets import get_secret

# New (Agent-GCPtoolkit internal use only)
from backend.services.secrets.src.workflows.secret_operations import get_secret
```

## Development

Package built with UV and setuptools. Requires Python >= 3.10.

```bash
# Install dependencies
pip install google-cloud-secret-manager

# Test from source (within Agent-GCPtoolkit codebase)
python -c "from agent_gcptoolkit.secrets import get_secret; print(get_secret('TEST_SECRET'))"

# For cross-worktree usage, use CLI instead
gcptoolkit secrets get TEST_SECRET
```

## Version

Current version: 0.2.0
