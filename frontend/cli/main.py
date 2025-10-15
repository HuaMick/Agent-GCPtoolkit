"""CLI entrypoint for agent-gcptoolkit."""
import sys
import argparse
import subprocess
import logging
from pathlib import Path

# BLIND TESTING FIX #4: Import validators
from .validators import validate_secret_name

VERSION = "0.1.0"  # BLIND TESTING FIX #8: No 'v' prefix for consistency
PACKAGE_ROOT = Path(__file__).parent.parent.parent
BUILD_ARTIFACTS_DIR = PACKAGE_ROOT / "build-artifacts"

# Configure logging to stderr for fallback warnings
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    stream=sys.stderr
)


def cmd_version(args):
    """Show version information."""
    print(f"agent-gcptoolkit {VERSION}")
    if args.verbose:
        print(f"Package root: {PACKAGE_ROOT}")


def cmd_update(args):
    """Reinstall from latest build artifacts."""
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


def cmd_secrets_get(args):
    """Get a secret from GCP Secret Manager."""
    from backend.services.secrets.src.workflows.secret_operations import get_secret

    # BLIND TESTING FIX #8: Validate secret name format
    validate_secret_name(args.secret_name)

    # BLIND TESTING FIX #4: Pass quiet flag to suppress stderr warnings
    secret_value = get_secret(args.secret_name, args.project_id, quiet=args.quiet)

    if secret_value:
        if args.quiet:
            # Quiet mode: output only value, no formatting
            print(secret_value)
        else:
            # Verbose mode: show secret name and value
            print(f"Secret '{args.secret_name}': {secret_value}")
        sys.exit(0)  # BLIND TESTING FIX #3: Explicit exit code 0
    else:
        print(f"Error: Secret '{args.secret_name}' not found", file=sys.stderr)
        sys.exit(1)  # BLIND TESTING FIX #3: Exit code 1 for runtime errors


def main():
    """Main CLI entrypoint."""
    # BLIND TESTING FIX #3: Standardized exit codes
    # Exit codes: 0 = success, 1 = runtime errors, 2 = usage errors (argparse)

    parser = argparse.ArgumentParser(
        prog="gcptoolkit",
        description="Agent-GCPtoolkit CLI - GCP Secret Manager toolkit",
        epilog="""
Exit codes:
  0 - Success
  1 - Runtime error (authentication, network, secret not found, etc.)
  2 - Usage error (invalid arguments, invalid secret name format, etc.)

Environment variables:
  GCP_PROJECT              - GCP project ID (overrides gcloud config)
  GOOGLE_APPLICATION_CREDENTIALS - Path to service account key JSON

For more information, see the README.
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # version command - BLIND TESTING FIX #7: Add proper help
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

    # update command - BLIND TESTING FIX #7: Add proper help
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

    # reinstall command - BLIND TESTING FIX #7: Add proper help
    reinstall_parser = subparsers.add_parser(
        "reinstall",
        help="Reinstall from build artifacts (alias for update)",
        description="Alias for the 'update' command. Reinstalls from latest build artifacts."
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
        help="GCP project ID (auto-detected from GCP_PROJECT env var or gcloud config if not provided)"
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
        sys.exit(2)  # BLIND TESTING FIX #3: Exit code 2 for usage errors

    # Route to command handlers
    try:
        if args.command == "version":
            cmd_version(args)
        elif args.command == "update":
            cmd_update(args)
        elif args.command == "reinstall":
            cmd_reinstall(args)
        elif args.command == "secrets":
            if args.secrets_command == "get":
                cmd_secrets_get(args)
            else:
                secrets_parser.print_help()
                sys.exit(2)  # BLIND TESTING FIX #3: Exit code 2 for usage errors
        else:
            parser.print_help()
            sys.exit(2)  # BLIND TESTING FIX #3: Exit code 2 for usage errors
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
