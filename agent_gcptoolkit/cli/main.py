"""CLI entrypoint for agent-gcptoolkit."""
import sys
import os
import argparse
import subprocess
import logging
from pathlib import Path

from .validators import validate_secret_name

VERSION = "0.1.0"

# Configure logging to stderr
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def _get_package_root() -> Path:
    """
    Get the package root directory, trying multiple detection methods.

    Priority order:
    1. GCPTOOLKIT_ROOT environment variable (if set)
    2. Development mode (if pyproject.toml exists in expected location)
    3. Git worktree detection (if .git file exists)
    4. Current working directory
    5. Search parent directories for pyproject.toml

    Returns:
        Path to package root

    Raises:
        RuntimeError: If package root cannot be determined
    """
    # 1. Environment variable override
    env_root = os.getenv("GCPTOOLKIT_ROOT")
    if env_root:
        root = Path(env_root)
        if root.exists() and (root / "pyproject.toml").exists():
            logger.debug(f"Using GCPTOOLKIT_ROOT: {root}")
            return root
        logger.warning(f"GCPTOOLKIT_ROOT points to invalid path: {env_root}")

    # 2. Development mode detection (relative to this file)
    module_path = Path(__file__).parent.parent.parent
    if (module_path / "pyproject.toml").exists():
        logger.debug(f"Using development mode path: {module_path}")
        return module_path

    # 3. Git worktree detection
    git_file = module_path / ".git"
    if git_file.exists():
        # Read the worktree gitdir from .git file
        try:
            with open(git_file) as f:
                gitdir_line = f.read().strip()
                if gitdir_line.startswith("gitdir:"):
                    # This is a worktree, use the module path
                    logger.debug(f"Using git worktree path: {module_path}")
                    return module_path
        except Exception as e:
            logger.debug(f"Could not read .git file: {e}")

    # 4. Fallback to current directory
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        logger.debug(f"Using current working directory: {cwd}")
        return cwd

    # 5. Last resort: try to find pyproject.toml in parent directories
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() and (parent / "agent_gcptoolkit").exists():
            logger.debug(f"Found package root in parent directory: {parent}")
            return parent

    raise RuntimeError(
        "Could not determine package root. "
        "Please set GCPTOOLKIT_ROOT environment variable or run from package directory."
    )


# Detect package root
try:
    PACKAGE_ROOT = _get_package_root()
except RuntimeError as e:
    # If we can't determine the package root, set it to None and warn
    # This allows the CLI to still load, but build/update commands will fail gracefully
    PACKAGE_ROOT = None
    logger.warning(f"Warning: {e}")

BUILD_ARTIFACTS_DIR = PACKAGE_ROOT / "build-artifacts" if PACKAGE_ROOT else None


def cmd_version(args):
    """Show version information."""
    print(f"agent-gcptoolkit {VERSION}")
    if args.verbose:
        print(f"Package root: {PACKAGE_ROOT}")


def cmd_update(args):
    """Reinstall from latest build artifacts."""
    if PACKAGE_ROOT is None or BUILD_ARTIFACTS_DIR is None:
        print(
            "Error: Package root not found. "
            "Set GCPTOOLKIT_ROOT environment variable or run from package directory.",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"=== Updating agent-gcptoolkit from {BUILD_ARTIFACTS_DIR}/dist/ ===")

    # Find the wheel file
    dist_dir = BUILD_ARTIFACTS_DIR / "dist"
    if not dist_dir.exists():
        print(f"Error: {dist_dir} does not exist. Run build first.", file=sys.stderr)
        sys.exit(1)

    wheels = list(dist_dir.glob("agent_gcptoolkit-*.whl"))
    if not wheels:
        print(f"Error: No wheel found in {dist_dir}. Run build first.", file=sys.stderr)
        sys.exit(1)

    wheel_path = wheels[0]
    print(f"Installing: {wheel_path}")

    try:
        subprocess.run(
            ["uv", "pip", "install", "--force-reinstall", str(wheel_path)],
            check=True
        )
        print("=== Update complete ===")
    except subprocess.CalledProcessError as e:
        print(f"Error: Update failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_reinstall(args):
    """Reinstall from build artifacts (alias for update)."""
    cmd_update(args)


def cmd_build(args):
    """Build the package using uv build."""
    if PACKAGE_ROOT is None or BUILD_ARTIFACTS_DIR is None:
        print(
            "Error: Package root not found. "
            "Set GCPTOOLKIT_ROOT environment variable or run from package directory.",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"=== Building agent-gcptoolkit ===")

    try:
        # Run uv build from package root
        subprocess.run(
            ["uv", "build", "--out-dir", str(BUILD_ARTIFACTS_DIR / "dist")],
            cwd=PACKAGE_ROOT,
            check=True
        )
        print(f"=== Build complete. Artifacts in {BUILD_ARTIFACTS_DIR}/dist/ ===")
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'uv' command not found. Please install uv package manager.", file=sys.stderr)
        sys.exit(1)


def cmd_rebuild(args):
    """Build and reinstall the package."""
    print(f"=== Rebuilding agent-gcptoolkit (build + reinstall) ===")

    # First, run build
    cmd_build(args)

    # Then, run update/reinstall
    cmd_update(args)


def cmd_secrets_get(args):
    """Get a secret from GCP Secret Manager."""
    from agent_gcptoolkit.secrets.workflows.secret_operations import get_secret

    validate_secret_name(args.secret_name)
    secret_value = get_secret(args.secret_name, args.project_id, quiet=args.quiet)

    if secret_value:
        if args.quiet:
            # Quiet mode: output only value, no formatting
            print(secret_value)
        else:
            # Verbose mode: show secret name and value
            print(f"Secret '{args.secret_name}': {secret_value}")
        sys.exit(0)
    else:
        print(f"Error: Secret '{args.secret_name}' not found in GCP Secret Manager or environment variables", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entrypoint.

    Exit codes:
        0 - Success
        1 - Runtime errors (authentication, network, secret not found, etc.)
        2 - Usage errors (invalid arguments, invalid secret name format, etc.)
    """
    parser = argparse.ArgumentParser(
        prog="gcptoolkit",
        description="Agent-GCPtoolkit CLI - GCP Secret Manager toolkit",
        epilog="""
Exit codes:
  0 - Success
  1 - Runtime error (authentication, network, secret not found, etc.)
  2 - Usage error (invalid arguments, invalid secret name format, etc.)

Environment variables:
  GCP_PROJECT - GCP project ID (overrides config file)

Configuration:
  Service account authentication is configured in:
  /home/code/myagents/config/config_agent_gcptoolkit.yml

For more information, see the README.
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
        description="Display the current version of agent-gcptoolkit"
    )
    version_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show additional information (package root path)"
    )

    # update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update from latest build artifacts",
        description="""
Reinstall agent-gcptoolkit from the latest wheel in build-artifacts/dist/.

This is useful during development to test changes without manually
running build and install scripts.

Prerequisites:
  - Wheel must exist in build-artifacts/dist/ (run ./scripts/build.sh first)
  - UV package manager must be installed
        """
    )

    # reinstall command
    reinstall_parser = subparsers.add_parser(
        "reinstall",
        help="Reinstall from build artifacts (alias for update)",
        description="Alias for the 'update' command. Reinstalls from latest build artifacts."
    )

    # build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build the package",
        description="""
Build agent-gcptoolkit using uv build.

Creates wheel and source distribution in build-artifacts/dist/.

Prerequisites:
  - UV package manager must be installed
        """
    )

    # rebuild command
    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="Build and reinstall the package",
        description="""
Build and reinstall agent-gcptoolkit in one step.

This combines the 'build' and 'update' commands for convenience:
  1. Builds the package using uv build
  2. Reinstalls from the newly created wheel

Prerequisites:
  - UV package manager must be installed
        """
    )

    # secrets command
    secrets_parser = subparsers.add_parser(
        "secrets",
        help="Secret management operations",
        description="Manage secrets in GCP Secret Manager"
    )
    secrets_subparsers = secrets_parser.add_subparsers(dest="secrets_command")

    # secrets get command
    get_parser = secrets_subparsers.add_parser(
        "get",
        help="Get a secret value",
        description="""
Fetch a secret from GCP Secret Manager with automatic fallback to environment variables.

Behavior:
  1. Checks memory cache (within same process only)
  2. Fetches from GCP Secret Manager
  3. Falls back to environment variable if GCP fetch fails

The command will print the secret value to stdout. In quiet mode (-q),
only the value is printed. In normal mode, the secret name is also shown.

Exit codes:
  0 - Secret found and printed
  1 - Secret not found (not in GCP or environment)
  2 - Invalid secret name format
        """
    )
    get_parser.add_argument(
        "secret_name",
        help="Name of the secret (format: [a-zA-Z0-9_-]+, no dots or special chars)"
    )
    get_parser.add_argument(
        "--project-id",
        help="GCP project ID (auto-detected from GCP_PROJECT env var or config file if not provided)"
    )
    get_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Output only the secret value (suppresses warnings and formatting, useful for scripts)"
    )

    args = parser.parse_args()

    # If no command provided, show help and exit with usage error code
    if not args.command:
        parser.print_help()
        sys.exit(2)

    # Route to command handlers
    try:
        if args.command == "version":
            cmd_version(args)
        elif args.command == "update":
            cmd_update(args)
        elif args.command == "reinstall":
            cmd_reinstall(args)
        elif args.command == "build":
            cmd_build(args)
        elif args.command == "rebuild":
            cmd_rebuild(args)
        elif args.command == "secrets":
            if args.secrets_command == "get":
                cmd_secrets_get(args)
            else:
                secrets_parser.print_help()
                sys.exit(2)
        else:
            parser.print_help()
            sys.exit(2)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
