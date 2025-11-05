"""Configuration loader for Agent-GCPtoolkit."""
import os
import logging
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)

# Support environment variable override with fallback to relative path
# This allows different environments to use different config locations
def _get_config_path() -> str:
    """
    Get config file path from environment variable or use default.

    Priority order:
    1. GCPTOOLKIT_CONFIG_PATH environment variable (absolute path)
    2. Default relative path: config/config_agent_gcptoolkit.yml (relative to git root)

    Returns:
        Absolute path to config file
    """
    env_path = os.getenv("GCPTOOLKIT_CONFIG_PATH")
    if env_path:
        return env_path

    # Default to relative path from worktree root
    # Agent-GCPtoolkit is at /home/code/myagents/Agent-GCPtoolkit
    # Config is at /home/code/myagents/config/
    # So we need to go up to the worktree root (one level above Agent-GCPtoolkit)
    package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    worktree_root = os.path.dirname(package_root)
    return os.path.join(
        worktree_root,
        "config",
        "config_agent_gcptoolkit.yml"
    )

CONFIG_PATH = _get_config_path()


class ConfigError(Exception):
    """Configuration error exception."""
    pass


def load_config() -> Dict[str, Any]:
    """
    Load and validate configuration from YAML file.

    Returns:
        Dict containing configuration with keys:
        - authentication: dict with type and service_account_path
        - gcp: dict with project_id

    Raises:
        ConfigError: If config file is missing, invalid, or service account file doesn't exist
    """
    # Check if config file exists
    if not os.path.exists(CONFIG_PATH):
        raise ConfigError(
            f"Configuration file not found at: {CONFIG_PATH}\n"
            f"Please create the config file with required authentication settings."
        )

    # Load YAML
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML config at {CONFIG_PATH}: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read config file at {CONFIG_PATH}: {e}")

    # Validate required fields
    if not config:
        raise ConfigError(f"Config file at {CONFIG_PATH} is empty")

    if 'authentication' not in config:
        raise ConfigError(
            f"Missing 'authentication' section in config at {CONFIG_PATH}\n"
            f"Required format:\n"
            f"authentication:\n"
            f"  type: service_account\n"
            f"  service_account_path: /path/to/service-account.json"
        )

    auth = config['authentication']

    if 'type' not in auth:
        raise ConfigError("Missing 'authentication.type' in config")

    if auth['type'] != 'service_account':
        raise ConfigError(
            f"Unsupported authentication type: {auth['type']}\n"
            f"Only 'service_account' is supported."
        )

    if 'service_account_path' not in auth:
        raise ConfigError(
            "Missing 'authentication.service_account_path' in config\n"
            "Please specify the absolute path to your service account JSON file."
        )

    service_account_path = auth['service_account_path']

    # Validate service account file exists
    if not os.path.exists(service_account_path):
        raise ConfigError(
            f"Service account file not found at: {service_account_path}\n"
            f"Please ensure the file exists or update the path in {CONFIG_PATH}"
        )

    if not os.path.isfile(service_account_path):
        raise ConfigError(
            f"Service account path is not a file: {service_account_path}"
        )

    # Validate GCP section
    if 'gcp' not in config:
        raise ConfigError(
            f"Missing 'gcp' section in config at {CONFIG_PATH}\n"
            f"Required format:\n"
            f"gcp:\n"
            f"  project_id: your-project-id"
        )

    if 'project_id' not in config['gcp']:
        raise ConfigError("Missing 'gcp.project_id' in config")

    logger.info(f"Configuration loaded successfully from {CONFIG_PATH}")
    logger.debug(f"Using service account: {service_account_path}")
    logger.debug(f"Using project ID: {config['gcp']['project_id']}")

    return config
