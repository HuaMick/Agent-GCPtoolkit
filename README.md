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

## Prerequisites

1. **GCP Project** with Secret Manager API enabled:
   ```bash
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Authentication** via gcloud CLI:
   ```bash
   gcloud auth application-default login
   ```

3. **Permissions** - Service account needs `roles/secretmanager.secretAccessor` role:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

## Installation

### Prerequisites

**Authentication Setup:**

Agent-GCPtoolkit requires GCP authentication. You MUST complete ONE of the following:

**Option 1: Service Account Key (Recommended for automation)**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**Option 2: Application Default Credentials (Recommended for development)**
```bash
gcloud auth application-default login
```

If you're unsure which to use:
- Development/testing: Use Option 2 (gcloud auth)
- Production/CI/CD: Use Option 1 (service account key)

**Project ID Configuration:**

Agent-GCPtoolkit auto-detects your GCP project ID using (in priority order):

1. `GCP_PROJECT` environment variable
2. `gcloud config get-value project`

Example:
```bash
export GCP_PROJECT="my-project-id"  # Optional, overrides gcloud config
```

### Installation Methods

**Method 1: UV Tool Install (RECOMMENDED)**

This makes `gcptoolkit` globally accessible without needing virtual environment activation.

Reference: https://docs.astral.sh/uv/concepts/tools/

```bash
# Build the package
./scripts/build.sh

# Install globally with UV
./scripts/install-global.sh

# Verify installation
gcptoolkit version
```

After installation, `gcptoolkit` is available in your PATH from any directory.

**Method 2: UV Pip (Alternative, requires venv activation)**

```bash
# Build the package
./scripts/build.sh

# Install with UV pip
./scripts/install.sh

# IMPORTANT: Activate virtual environment
source .venv/bin/activate

# Verify installation
gcptoolkit version
```

**Note:** With UV pip installation, you must activate the venv before each use.

## Development Workflow

### Build and Install Flow

Agent-GCPtoolkit uses a wheel-based installation (no dev mode).

**1. Build the package:**
```bash
./scripts/build.sh
```
This creates a wheel in `build-artifacts/dist/`.

**2. Install from wheel:**
```bash
./scripts/install-global.sh  # Recommended
# OR
./scripts/install.sh  # Alternative (requires venv activation)
```

**3. Verify installation:**
```bash
gcptoolkit version
```

### CLI Commands

**Version:**
```bash
gcptoolkit version              # Show version
gcptoolkit version --verbose    # Show version + package path
gcptoolkit version --help       # Show help for version command
```

**Update (reinstall from latest build):**
```bash
./scripts/build.sh && gcptoolkit update
```

**Get secret:**
```bash
# Basic usage
gcptoolkit secrets get MY_SECRET

# Specify project ID
gcptoolkit secrets get MY_SECRET --project-id my-project

# Quiet mode - output only value
gcptoolkit secrets get MY_SECRET --quiet

# In scripts - suppress stderr warnings
gcptoolkit secrets get MY_SECRET --quiet 2>/dev/null
```

**Secret Name Format Requirements**

Secret names must match the format: `[a-zA-Z0-9_-]+`

Valid examples:
- `MY_SECRET`
- `api-key-prod`
- `DATABASE_PASSWORD_123`

Invalid examples:
- `api.key` (dots not allowed)
- `MY SECRET` (spaces not allowed)
- `test@prod` (special characters not allowed)

**Secret Value Limitations**

- Secret values cannot be empty
- GCP Secret Manager rejects empty payloads
- If you need a placeholder, use a special value like `UNSET` or `TODO`

### Exit Codes

Agent-GCPtoolkit CLI uses standard exit codes:

- **0** - Success (secret found, command completed)
- **1** - Runtime error (authentication failed, secret not found, network error)
- **2** - Usage error (invalid arguments, invalid secret name format, missing required arguments)

Example usage in scripts:
```bash
if gcptoolkit secrets get MY_SECRET --quiet; then
    echo "Secret found (exit 0)"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "Runtime error - check authentication"
    elif [ $exit_code -eq 2 ]; then
        echo "Usage error - check command syntax"
    fi
fi
```

### Stderr Output Behavior

**Normal mode (default):**
```bash
$ gcptoolkit secrets get MY_SECRET
# If GCP fails, falls back to environment variable
# Stderr: GCP fetch failed for MY_SECRET: <error details>
# Stdout: Secret 'MY_SECRET': value123
# Exit code: 0 (success)
```

**Quiet mode (recommended for scripts):**
```bash
$ gcptoolkit secrets get MY_SECRET --quiet
# Suppresses all stderr warnings
# Stdout: value123
# Exit code: 0 (success)
```

**Production pattern:**
```bash
# Suppress all warnings, capture only value
SECRET_VALUE=$(gcptoolkit secrets get MY_SECRET --quiet 2>/dev/null)
```

### Memory Caching Behavior

**Important:** Caching is per-process, NOT per-CLI invocation.

```bash
# Each command spawns a new process - NO cache benefit
gcptoolkit secrets get MY_SECRET  # Takes ~1.5s (fetches from GCP)
gcptoolkit secrets get MY_SECRET  # Takes ~1.5s (fetches again, new process)
gcptoolkit secrets get MY_SECRET  # Takes ~1.5s (fetches again, new process)
```

Cache only benefits internal calls within the same Python process:
```python
# Within a Python script - cache DOES work
from backend.services.secrets.src.workflows.secret_operations import get_secret

val1 = get_secret("MY_SECRET")  # Fetches from GCP (~1.5s)
val2 = get_secret("MY_SECRET")  # Returns from cache (~0.001s)
val3 = get_secret("MY_SECRET")  # Returns from cache (~0.001s)
```

### Development Scripts

- `./scripts/build.sh` - Build wheel in build-artifacts/dist/
- `./scripts/install-global.sh` - Install with UV tool (RECOMMENDED)
- `./scripts/install.sh` - Install with UV pip (requires venv activation)
- `./scripts/clean.sh` - Clean all build artifacts and caches

## Usage

### Basic Usage

```python
from agent_gcptoolkit.secrets import get_secret

# Fetch secret from GCP Secret Manager
api_key = get_secret("GEMINI_API_KEY")
```

### With Explicit Project ID

```python
from agent_gcptoolkit.secrets import get_secret

# Specify project ID explicitly
api_key = get_secret("GEMINI_API_KEY", project_id="my-gcp-project")
```

### Real-World Example

```python
from agent_gcptoolkit.secrets import get_secret
import google.generativeai as genai

# Configure Gemini with secret from GCP
genai.configure(api_key=get_secret("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
```

## How It Works

1. **Memory Caching**: Secrets are cached in-memory after first fetch, eliminating redundant API calls within the same process
2. **Fallback Mechanism**: If GCP Secret Manager is unavailable, automatically falls back to `os.getenv(secret_name)`
3. **Project ID Auto-Detection**: Uses `gcloud config get-value project` to determine the active GCP project

## Environment Variables

- **GOOGLE_APPLICATION_CREDENTIALS** - Path to service account JSON key (optional if using `gcloud auth application-default`)
- **GCP_PROJECT** - GCP project ID (optional, auto-detected from gcloud config)

## Troubleshooting

### Issue: "Secret not found" error

**What you see:**
```bash
$ gcptoolkit secrets get MY_SECRET
Error: Secret 'MY_SECRET' not found
```

**Possible causes:**
1. Secret doesn't exist in GCP Secret Manager
2. Secret doesn't exist as environment variable
3. Authentication not configured
4. Wrong project ID

**Solutions:**
```bash
# Check if secret exists in GCP
gcloud secrets list | grep MY_SECRET

# Check project ID being used
echo $GCP_PROJECT
gcloud config get-value project

# Try with explicit project ID
gcptoolkit secrets get MY_SECRET --project-id my-correct-project

# Check authentication
gcloud auth list
gcloud auth application-default login

# Fall back to environment variable
export MY_SECRET="fallback-value"
gcptoolkit secrets get MY_SECRET
```

### Issue: "GCP fetch failed, falling back to env var" warning

**What you see:**
```bash
$ gcptoolkit secrets get MY_SECRET
GCP fetch failed for MY_SECRET: Your default credentials were not found...
Secret 'MY_SECRET': value123
```

**What this means:**
- The command succeeded (exit 0) by using the environment variable fallback
- GCP authentication is not configured or failed
- The warning goes to stderr, the value goes to stdout

**Solutions:**

Option 1: Use quiet mode to suppress warnings
```bash
gcptoolkit secrets get MY_SECRET --quiet
```

Option 2: Fix authentication
```bash
gcloud auth application-default login
# OR
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

Option 3: Suppress stderr in scripts
```bash
gcptoolkit secrets get MY_SECRET 2>/dev/null
```

### Issue: "Invalid secret name" error

**What you see:**
```bash
$ gcptoolkit secrets get api.key
Error: Invalid secret name 'api.key'

Allowed characters: letters, numbers, underscores (_), hyphens (-)
Not allowed: dots (.), spaces, special characters (@, $, !, etc.)
```

**Solution:**
Use only allowed characters: `[a-zA-Z0-9_-]`
```bash
# Change dots to underscores or hyphens
gcptoolkit secrets get api_key
gcptoolkit secrets get api-key
```

### Issue: "Secret value cannot be empty" error

**What you see:**
```bash
$ gcptoolkit secrets set MY_SECRET ""
Error: Secret value cannot be empty

GCP Secret Manager does not allow empty secret payloads.
```

**Solution:**
Use a placeholder value instead of empty string
```bash
gcptoolkit secrets set MY_SECRET "UNSET"
gcptoolkit secrets set MY_SECRET "TODO"
```

### Issue: Command not found after installation

**What you see:**
```bash
$ gcptoolkit version
bash: gcptoolkit: command not found
```

**If you used UV pip installation (./scripts/install.sh):**
```bash
# You must activate the virtual environment first
source .venv/bin/activate
gcptoolkit version
```

**If you used UV tool installation (./scripts/install-global.sh):**
```bash
# Restart your shell or reload config
source ~/.bashrc  # or ~/.zshrc
gcptoolkit version

# Or add UV bin directory to PATH manually
export PATH="$PATH:~/.local/bin"
```

**Recommended solution:**
Use UV tool installation for global access without venv activation.

## Architecture

Agent-GCPtoolkit follows MyAgents backend standards:

```
Agent-GCPtoolkit/
├── backend/services/secrets/src/
│   ├── domains/              # Domain models and GCP client
│   │   ├── models.py        # Secret, SecretRequest dataclasses
│   │   └── gcp_client.py    # GCP Secret Manager wrapper
│   └── workflows/            # Business logic
│       └── secret_operations.py  # get_secret() with caching & fallback
├── frontend/cli/
│   ├── main.py              # CLI entrypoint (gcptoolkit command)
│   └── validators.py        # Input validation (secret names, values)
├── agent_gcptoolkit/        # Backward compatibility layer (DEPRECATED)
│   └── secrets.py           # Delegates to backend.services.secrets
├── build-artifacts/         # Generated build outputs (git-ignored)
│   ├── dist/                # Wheels and tarballs
│   └── build/               # Intermediate build files
├── scripts/
│   ├── build.sh            # Build wheel to build-artifacts/
│   ├── install-global.sh   # Install with UV tool (RECOMMENDED)
│   ├── install.sh          # Install with UV pip (requires venv activation)
│   └── clean.sh            # Clean build artifacts
└── pyproject.toml          # Package configuration
```

### Design Principles

1. **Separation of Concerns**: Domains (models, clients) separate from workflows (business logic)
2. **Backward Compatibility**: Old imports still work with deprecation warnings
3. **Build Artifacts Isolation**: All generated files in `build-artifacts/`, fully git-ignored
4. **No Dev Mode**: Install from wheel, not `pip install -e`
5. **UV Package Manager**: Use UV for builds and installations
6. **Input Validation**: CLI validates secret names and values before calling backend
7. **Quiet Mode**: Support for script-friendly output without stderr pollution
8. **Standardized Exit Codes**: 0=success, 1=runtime errors, 2=usage errors

### Migration Path

**Old code:**
```python
from agent_gcptoolkit.secrets import get_secret
```

**New code:**
```python
from backend.services.secrets.src.workflows.secret_operations import get_secret
```

Both work, but old import shows deprecation warning.

### Key Improvements

This version incorporates the following enhancements:

1. **Global CLI Access** - UV tool installation makes `gcptoolkit` available without venv activation
2. **GCP_PROJECT Support** - Environment variable override for project ID
3. **Exit Code Standards** - Consistent 0/1/2 exit codes for script usage
4. **Quiet Mode** - Suppress stderr warnings in production scripts
5. **Clear Auth Setup** - Documented exactly what authentication is required
6. **Accurate Troubleshooting** - Shows actual CLI output, not internal exceptions
7. **Complete Help System** - Every command has useful --help output
8. **Secret Name Validation** - Clear errors for invalid formats
9. **Empty Value Handling** - Helpful error message for GCP limitation
10. **Cache Clarification** - Explained per-process scope, not per-CLI

## Development

Package built with UV and setuptools. Requires Python >= 3.10.

```bash
# Install dependencies
pip install google-cloud-secret-manager

# Run from source
python -c "from agent_gcptoolkit.secrets import get_secret; print(get_secret('TEST_SECRET'))"
```

## Version

Current version: 0.1.0
