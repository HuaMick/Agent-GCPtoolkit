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

Install in editable mode from your worktrees:

```bash
pip install -e /home/code/myagents/Agent-GCPtoolkit/
```

Verify installation:
```bash
python -c "from agent_gcptoolkit.secrets import get_secret; print('Installation successful')"
```

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

### Authentication Failed

**Problem**: `google.auth.exceptions.DefaultCredentialsError`

**Solution**:
```bash
gcloud auth application-default login
```

### Permission Denied

**Problem**: `PermissionDenied: 403 Permission 'secretmanager.versions.access' denied`

**Solution**: Ensure your service account has the Secret Manager Secret Accessor role:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/secretmanager.secretAccessor"
```

### API Not Enabled

**Problem**: `FAILED_PRECONDITION: Secret Manager API has not been used`

**Solution**: Enable the Secret Manager API:
```bash
gcloud services enable secretmanager.googleapis.com
```

### Secret Not Found

**Problem**: `NotFound: 404 Secret [SECRET_NAME] not found`

**Solution**: Create the secret in GCP Secret Manager:
```bash
echo -n "your-secret-value" | gcloud secrets create SECRET_NAME --data-file=-
```

Or verify the secret exists:
```bash
gcloud secrets list
```

### Auto-Detection Fails

**Problem**: Project ID cannot be auto-detected

**Solution**: Either set the active project or pass it explicitly:
```bash
# Set active project
gcloud config set project YOUR_PROJECT_ID

# Or pass explicitly in code
get_secret("SECRET_NAME", project_id="YOUR_PROJECT_ID")
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

Current version: 0.1.0
