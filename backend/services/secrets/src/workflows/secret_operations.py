"""Workflow for secret operations with caching and fallback."""
import os
import logging
from typing import Optional
from ..domains.models import Secret, SecretRequest
from ..domains.gcp_client import GCPSecretClient

logger = logging.getLogger(__name__)

# Module-level cache: {project_id:secret_name -> Secret}
# BLIND TESTING FIX #10: Clarified - this is per-process cache, NOT per-CLI invocation
_secret_cache: dict[str, Secret] = {}


def get_secret(secret_name: str, project_id: Optional[str] = None, quiet: bool = False) -> Optional[str]:
    """
    Fetch secret from GCP Secret Manager with memory caching.

    Args:
        secret_name: Name of the secret to fetch
        project_id: GCP project ID (auto-detected if not provided)
        quiet: If True, suppress fallback warnings to stderr (BLIND TESTING FIX #4)

    Returns:
        Secret value as string, or None if not found

    Behavior:
        - Caches secrets in memory (per-process only, NOT across CLI invocations)
        - Auto-detects project_id from GCP_PROJECT env var or gcloud config
        - Falls back to os.getenv(secret_name) if GCP fetch fails
        - With quiet=False: Logs fallback warnings to stderr
        - With quiet=True: Silent fallback (for scripts/production use)
    """
    client = GCPSecretClient()

    # Auto-detect project_id if not provided
    if not project_id:
        project_id = client.get_project_id() or "unknown"

    # Check cache first
    cache_key = f"{project_id}:{secret_name}"
    if cache_key in _secret_cache:
        return _secret_cache[cache_key].value

    # Try fetching from GCP
    secret_value = client.fetch_secret(secret_name, project_id, quiet=quiet)

    if secret_value:
        secret = Secret(
            name=secret_name,
            value=secret_value,
            project_id=project_id,
            source="gcp"
        )
        _secret_cache[cache_key] = secret
        return secret_value

    # Fallback to environment variable
    # BLIND TESTING FIX #4: Only log if not quiet mode
    if not quiet:
        logger.warning(f"Falling back to environment variable for {secret_name}")

    env_value = os.getenv(secret_name)

    if env_value:
        secret = Secret(
            name=secret_name,
            value=env_value,
            project_id=project_id,
            source="env"
        )
        _secret_cache[cache_key] = secret

    return env_value
