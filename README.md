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
- **Auto-detect project ID** - No configuration needed when gcloud is configured

## Quick Start (No GCP Required)

Test locally with environment variables:

```bash
# Build and install
./scripts/build.sh && ./scripts/install-global.sh

# Set a test secret
export MY_SECRET="test_value"

# Retrieve it
gcptoolkit secrets get MY_SECRET
# Output: Secret 'MY_SECRET': test_value
```

For production setup with GCP Secret Manager, see [Prerequisites](#prerequisites).

## Prerequisites

### 1. GCP Project Setup

```bash
gcloud services enable secretmanager.googleapis.com
```

### 2. Authentication (Choose ONE)

**Option 1: Service Account (CI/CD)**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**Option 2: User Account (Development)**
```bash
gcloud auth application-default login
```

### 3. Permissions

```bash
# For service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# For user account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Verify Setup

```bash
gcloud auth application-default print-access-token  # Should output token
```

### 5. Project ID (Optional)

Auto-detected from `gcloud config get-value project` or override:
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

### Python API

```python
from agent_gcptoolkit.secrets import get_secret

# Basic usage
api_key = get_secret("GEMINI_API_KEY")

# With explicit project ID
api_key = get_secret("GEMINI_API_KEY", project_id="my-gcp-project")

# Real-world example
import google.generativeai as genai
genai.configure(api_key=get_secret("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
```

### CLI Commands

```bash
gcptoolkit version                      # Show version
gcptoolkit secrets get MY_SECRET        # Get secret
./scripts/build.sh && gcptoolkit update # Update from latest build
```

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

1. **Memory Caching**: Secrets are cached in-memory per-process. CLI invocations spawn new processes, so caching only benefits multiple `get_secret()` calls within the same Python script.

2. **Fallback Mechanism**: If GCP Secret Manager is unavailable, automatically falls back to `os.getenv(secret_name)`

3. **Project ID Auto-Detection**: Uses `gcloud config get-value project` to determine the active GCP project

## Environment Variables

- **GOOGLE_APPLICATION_CREDENTIALS** - Path to service account JSON (optional if using gcloud auth)
- **GCP_PROJECT** - GCP project ID (optional, auto-detected from gcloud config)

## Troubleshooting

### Secret not found

```bash
# Check if secret exists
gcloud secrets list | grep MY_SECRET

# Check/set project ID
gcloud config get-value project
export GCP_PROJECT="my-correct-project"

# Verify authentication
gcloud auth application-default login

# Use env var fallback
export MY_SECRET="fallback-value"
```

### GCP fetch failed warning

Command succeeded using env var fallback. Fix authentication or suppress stderr:

```bash
gcloud auth application-default login
# OR
gcptoolkit secrets get MY_SECRET 2>/dev/null
```

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

```python
# Old (works with deprecation warning)
from agent_gcptoolkit.secrets import get_secret

# New
from backend.services.secrets.src.workflows.secret_operations import get_secret
```

## Development

Package built with UV and setuptools. Requires Python >= 3.10.

```bash
# Install dependencies
pip install google-cloud-secret-manager

# Run from source
python -c "from agent_gcptoolkit.secrets import get_secret; print(get_secret('TEST_SECRET'))"
```

## Version

Current version: 0.2.0
