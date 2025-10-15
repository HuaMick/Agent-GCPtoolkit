"""GCP Secret Manager client with memory caching and env var fallback."""

import os
import logging
import subprocess
from google.cloud import secretmanager

# Module-level cache: {project_id:secret_name -> secret_value}
_secret_cache = {}

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, project_id: str = None) -> str:
    """
    Fetch secret from GCP Secret Manager with memory caching.

    Args:
        secret_name: Name of the secret to fetch
        project_id: GCP project ID (auto-detected if not provided)

    Returns:
        Secret value as string, or None if not found

    Behavior:
        - Caches secrets in memory (fetched only once per process)
        - Auto-detects project_id from gcloud config if not provided
        - Falls back to os.getenv(secret_name) if GCP fetch fails
    """
    # Auto-detect project_id if not provided
    if not project_id:
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, check=True
            )
            project_id = result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to auto-detect project_id: {e}")
            project_id = "unknown"

    # Check cache first
    cache_key = f"{project_id}:{secret_name}"
    if cache_key in _secret_cache:
        return _secret_cache[cache_key]

    # Try fetching from GCP
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")

        # Cache the secret
        _secret_cache[cache_key] = secret_value
        return secret_value

    except Exception as e:
        logger.warning(f"GCP fetch failed for {secret_name}, falling back to env var: {e}")

        # Fallback to environment variable
        env_value = os.getenv(secret_name)
        if env_value:
            _secret_cache[cache_key] = env_value
        return env_value
