"""Backward compatibility layer for agent_gcptoolkit.secrets.

DEPRECATED: This module is maintained for backward compatibility.
New code should use: from backend.services.secrets.src.workflows.secret_operations import get_secret
"""
import warnings
from backend.services.secrets.src.workflows.secret_operations import get_secret as _get_secret


def get_secret(secret_name: str, project_id: str = None) -> str:
    """
    Fetch secret from GCP Secret Manager with memory caching.

    DEPRECATED: Use backend.services.secrets.src.workflows.secret_operations.get_secret instead.

    Args:
        secret_name: Name of the secret to fetch
        project_id: GCP project ID (auto-detected if not provided)

    Returns:
        Secret value as string, or None if not found
    """
    warnings.warn(
        "agent_gcptoolkit.secrets is deprecated. "
        "Use backend.services.secrets.src.workflows.secret_operations instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_secret(secret_name, project_id)


# Re-export for backward compatibility
__all__ = ["get_secret"]
