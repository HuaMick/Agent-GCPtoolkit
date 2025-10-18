"""GCP Secret Manager client wrapper."""
import os
import logging
from typing import Optional
from google.cloud import secretmanager
from .config_loader import load_config, ConfigError

logger = logging.getLogger(__name__)

# Load configuration at module init
try:
    _CONFIG = load_config()
    # Set GOOGLE_APPLICATION_CREDENTIALS from config
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = _CONFIG['authentication']['service_account_path']
    logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS from config: {_CONFIG['authentication']['service_account_path']}")
except ConfigError as e:
    logger.error(f"Failed to load configuration: {e}")
    raise


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
        Get GCP project ID from config or environment variable.

        Priority order:
        1. GCP_PROJECT environment variable (allows override)
        2. Config file (primary source)

        Returns:
            Project ID string, or None if not found

        Raises:
            ValueError: If project_id is not found in config or environment
        """
        # Check GCP_PROJECT env var first (allows override)
        gcp_project_env = os.getenv("GCP_PROJECT")
        if gcp_project_env:
            logger.debug(f"Using GCP_PROJECT from environment: {gcp_project_env}")
            return gcp_project_env

        # Use config file project_id
        if _CONFIG and 'gcp' in _CONFIG and 'project_id' in _CONFIG['gcp']:
            project_id = _CONFIG['gcp']['project_id']
            logger.debug(f"Using project_id from config: {project_id}")
            return project_id

        # No project ID found
        logger.error("Project ID not found. Please set GCP_PROJECT environment variable or configure project_id in /home/code/myagents/config/config_agent_gcptoolkit.yml")
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
