"""GCP Secret Manager client wrapper."""
import os
import logging
import subprocess
from typing import Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class GCPSecretClient:
    """Wrapper around GCP Secret Manager client."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> secretmanager.SecretManagerServiceClient:
        """Lazy-initialize client."""
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def get_project_id(self) -> Optional[str]:
        """
        Auto-detect GCP project ID from multiple sources.

        Priority order:
        1. GCP_PROJECT environment variable (NEW - BLIND TESTING FIX)
        2. gcloud config get-value project

        Returns:
            Project ID string, or None if not found
        """
        # BLIND TESTING FIX #2: Check GCP_PROJECT env var first
        gcp_project_env = os.getenv("GCP_PROJECT")
        if gcp_project_env:
            logger.debug(f"Using GCP_PROJECT from environment: {gcp_project_env}")
            return gcp_project_env

        # Fallback to gcloud config
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, check=True
            )
            project_id = result.stdout.strip()
            if project_id:
                logger.debug(f"Using project from gcloud config: {project_id}")
                return project_id
        except Exception as e:
            logger.warning(f"Failed to auto-detect project_id: {e}")

        return None

    def fetch_secret(self, secret_name: str, project_id: str, quiet: bool = False) -> Optional[str]:
        """
        Fetch secret from GCP Secret Manager.

        Args:
            secret_name: Name of the secret
            project_id: GCP project ID
            quiet: If True, suppress warning logs (BLIND TESTING FIX #4)

        Returns:
            Secret value or None if fetch fails
        """
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            if not quiet:
                logger.warning(f"GCP fetch failed for {secret_name}: {e}")
            return None
