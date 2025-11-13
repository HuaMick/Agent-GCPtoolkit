"""CLI entrypoint for agent-gcptoolkit."""
import sys
import os
import argparse
import subprocess
import logging
import re
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


def _validate_pyproject_name(pyproject_path: Path, expected_name: str = "agent-gcptoolkit") -> bool:
    """
    Validate that pyproject.toml contains the expected package name.

    Args:
        pyproject_path: Path to pyproject.toml file
        expected_name: Expected package name (default: "agent-gcptoolkit")

    Returns:
        True if package name matches, False otherwise
    """
    try:
        with open(pyproject_path) as f:
            for line in f:
                # Match: name = "agent-gcptoolkit" or name = 'agent-gcptoolkit'
                if match := re.match(r'^name\s*=\s*["\']([^"\']+)["\']', line.strip()):
                    return match.group(1) == expected_name
        return False
    except Exception as e:
        logger.debug(f"Could not validate pyproject.toml: {e}")
        return False


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
    pyproject = module_path / "pyproject.toml"
    if pyproject.exists() and _validate_pyproject_name(pyproject):
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
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists() and _validate_pyproject_name(pyproject):
        logger.debug(f"Using current working directory: {cwd}")
        return cwd

    # 5. Last resort: try to find pyproject.toml in parent directories
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        pyproject = parent / "pyproject.toml"
        if pyproject.exists() and _validate_pyproject_name(pyproject):
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


def cmd_config_set_path(args):
    """Set config file path preference."""
    from agent_gcptoolkit.secrets.domains.preferences import set_preference

    config_path = Path(args.path).resolve()

    # Validate that the path exists
    if not config_path.exists():
        print(f"Error: Config file does not exist: {config_path}", file=sys.stderr)
        sys.exit(1)

    if not config_path.is_file():
        print(f"Error: Path is not a file: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Store absolute path in preferences
    set_preference("config_path", str(config_path))
    print(f"Config path set to: {config_path}")


def cmd_config_show(args):
    """Show current config file path."""
    from agent_gcptoolkit.secrets.domains.preferences import get_preference

    config_path_pref = get_preference("config_path")

    if config_path_pref:
        config_path = Path(config_path_pref)
        if config_path.exists():
            print(f"Config path: {config_path}")
            print("Source: preference")
        else:
            print(f"Config path (from preference, but file not found): {config_path}")
            print("Source: preference")
    else:
        default_config = Path.home() / ".config" / "agent-gcptoolkit" / "config.yml"
        if default_config.exists():
            print(f"Config path: {default_config}")
            print("Source: default")
        else:
            print(f"Config path: {default_config}")
            print("Source: default (file not found)")


def cmd_config_clear(args):
    """Clear config path preference."""
    from agent_gcptoolkit.secrets.domains.preferences import clear_preference

    clear_preference("config_path")
    default_config = Path.home() / ".config" / "agent-gcptoolkit" / "config.yml"
    print(f"Config path preference cleared. Will use default: {default_config}")


def cmd_config_init(args):
    """Interactive config setup."""
    from agent_gcptoolkit.secrets.domains.preferences import set_preference

    default_config = Path.home() / ".config" / "agent-gcptoolkit" / "config.yml"

    print("=== Agent-GCPtoolkit Configuration Setup ===\n")
    print(f"Default config location: {default_config}\n")

    # Check if config already exists
    if default_config.exists():
        print(f"Configuration file already exists at: {default_config}")
        response = input("Do you want to use a different config file? (y/N): ").strip().lower()
        if response != 'y':
            print(f"\nUsing existing config at: {default_config}")
            return
    else:
        # Ask if user wants to copy existing config or use default location
        print("Choose an option:")
        print("1. Copy an existing config file to default location")
        print("2. Point to an existing config file at a different location")
        print("3. Cancel (manually create config file later)")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            source_path = input("Enter path to existing config file: ").strip()
            source = Path(source_path).expanduser().resolve()

            if not source.exists():
                print(f"Error: File not found: {source}", file=sys.stderr)
                sys.exit(1)

            # Create directory and copy file
            default_config.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(source, default_config)
            print(f"\nConfig copied to: {default_config}")
            return

        elif choice == "2":
            config_path = input("Enter path to config file: ").strip()
            config_file = Path(config_path).expanduser().resolve()

            if not config_file.exists():
                print(f"Error: File not found: {config_file}", file=sys.stderr)
                sys.exit(1)

            set_preference("config_path", str(config_file))
            print(f"\nConfig path set to: {config_file}")
            return

        elif choice == "3":
            print("\nSetup cancelled.")
            print(f"Create your config file at: {default_config}")
            print("Or use: myagents config set-path <path>")
            return

        else:
            print("Invalid choice.", file=sys.stderr)
            sys.exit(2)


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
        prog="myagents",
        description="Agent-GCPtoolkit CLI - GCP Secret Manager toolkit (accessed via myagents)",
        epilog="""
Exit codes:
  0 - Success
  1 - Runtime error (authentication, network, secret not found, etc.)
  2 - Usage error (invalid arguments, invalid secret name format, etc.)

Environment variables:
  GCP_PROJECT - GCP project ID (overrides config file)

Configuration:
  Default location: ~/.config/agent-gcptoolkit/config.yml
  Custom path: Set with 'myagents config set-path <path>'
  View current: Run 'myagents config show'

Note: As of v0.2.0, use the unified 'myagents' CLI (e.g., 'myagents secrets get', 'myagents config show').
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

    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Manage agent-gcptoolkit configuration"
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    # config set-path command
    config_set_path_parser = config_subparsers.add_parser(
        "set-path",
        help="Set config file path",
        description="""
Set the configuration file path preference.

This stores the absolute path to your config file in:
~/.config/agent-gcptoolkit/preferences.json

The path will be validated before storing.
        """
    )
    config_set_path_parser.add_argument(
        "path",
        help="Path to config file"
    )

    # config show command
    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Show current config path",
        description="""
Display the current configuration file path and its source.

Sources:
  - preference: Path set via 'config set-path'
  - default: Default XDG location (~/.config/agent-gcptoolkit/config.yml)
        """
    )

    # config clear command
    config_clear_parser = config_subparsers.add_parser(
        "clear",
        help="Clear config path preference",
        description="""
Remove the config path preference.

After clearing, the default location will be used:
~/.config/agent-gcptoolkit/config.yml
        """
    )

    # config init command
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Interactive config setup",
        description="""
Interactive setup wizard for agent-gcptoolkit configuration.

Options:
  1. Copy existing config to default location
  2. Point to existing config at different location
  3. Cancel and set up manually
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
        elif args.command == "config":
            if args.config_command == "set-path":
                cmd_config_set_path(args)
            elif args.config_command == "show":
                cmd_config_show(args)
            elif args.config_command == "clear":
                cmd_config_clear(args)
            elif args.config_command == "init":
                cmd_config_init(args)
            else:
                config_parser.print_help()
                sys.exit(2)
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
